"""Post-transport authority is fresh before analysis or acceptance."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from conftest import _url_for, approve_run
from psycopg.pq import TransactionStatus
from test_loop_charges import (
    ESTIMATE,
    MODEL,
    REPORT,
    REPORTED,
    VENDORED,
    _Completions,
    _every_block,
    route,
)

from server import methodology
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute
from server.engine.runtime import Execution, ProviderResult, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import MANIFEST_NAME, Authority, Bundle
from server.methodology.envelope import Envelope
from server.methodology.executor import Assignment
from server.methodology.runner import ModuleProvider
from server.provider import Completion
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, connect
from server.store.budget import reserve
from server.store.gates import (
    Gate,
    GateApproval,
    approve_gate,
    gate_preview,
    withdraw_source,
)
from server.store.members import Standing, grant, revoke
from server.store.runs import complete_run, fail_run, start_attempt, start_run

__all__ = ["route"]


@dataclass(frozen=True, slots=True)
class _Harness:
    conn: StoreConnection
    case_id: UUID
    run_id: UUID
    source_id: UUID
    witness_id: UUID
    blobs: BlobStore
    route: ResolvedRoute
    bundle: Bundle
    approver: UUID

    @property
    def url(self) -> str:
        return _url_for(self.conn.info.dbname)


@pytest.fixture
def harness(
    case: tuple[StoreConnection, UUID], tmp_path: Path, route: ResolvedRoute
) -> _Harness:
    conn, case_id = case
    root = tmp_path / "bundle"
    shutil.copytree(VENDORED, root)
    bundle = Bundle(root)
    blobs = BlobStore(tmp_path / "blobs")
    source_id, witness_id = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[
            Document(filename=BoundaryText.of("report.txt"), data=REPORT),
            Document(
                filename=BoundaryText.of("uncited.txt"),
                data=b"Captured but deliberately not delivered.\n",
            ),
        ],
    )
    run_id = start_run(conn, case_id)
    conn.commit()
    approver = approve_run(
        conn, case_id=case_id, run_id=run_id, route=route, bundle=bundle
    )
    return _Harness(
        conn,
        case_id,
        run_id,
        source_id,
        witness_id,
        blobs,
        route,
        bundle,
        approver,
    )


def _revoke_during_transport(harness: _Harness) -> None:
    with connect(harness.url) as other:
        revoke(other, case_id=harness.case_id, user_id=harness.approver)
        other.commit()
        assert other.execute(
            "SELECT revoked_at IS NOT NULL FROM case_members"
            " WHERE case_id=%s AND user_id=%s",
            (harness.case_id, harness.approver),
        ).fetchone() == (True,)


@dataclass
class _DuringCompletion:
    delegate: _Completions
    mutate: Callable[[], None]
    calls: int = 0
    model: str = MODEL

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        assert json_object
        assert self.delegate.model == self.model
        assert self.calls == 0
        self.calls += 1
        self.mutate()
        return self.delegate.complete(prompt, json_object=json_object)


def _counts(harness: _Harness) -> tuple[int, list[Decimal], int, int, int]:
    with connect(harness.url) as observer:
        outcomes = observer.execute("SELECT count(*) FROM call_outcomes").fetchone()
        charges = observer.execute("SELECT amount FROM budget_ledger").fetchall()
        artifacts = observer.execute("SELECT count(*) FROM artifacts").fetchone()
        attempts = observer.execute("SELECT count(*) FROM run_attempts").fetchone()
        reservations = observer.execute(
            "SELECT count(*) FROM budget_reservations"
        ).fetchone()
    assert outcomes is not None and artifacts is not None
    assert attempts is not None and reservations is not None
    return (
        int(outcomes[0]),
        [row[0] for row in charges],
        int(artifacts[0]),
        int(attempts[0]),
        int(reservations[0]),
    )


def test_module_provider_rechecks_authority_after_transport_before_envelope_or_blob(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OLD-API RED: current code analyzes and stores after a real revocation."""
    from server.methodology import executor

    node = harness.route.nodes[0]
    attempt = start_attempt(harness.conn, harness.run_id, node.route_node_id)
    reserve(harness.conn, attempt, ESTIMATE)
    completion = _DuringCompletion(
        _Completions(harness.source_id), lambda: _revoke_during_transport(harness)
    )
    provider = ModuleProvider(
        harness.conn,
        harness.bundle,
        harness.blobs,
        completion,
        _every_block(harness.conn, harness.source_id),
        harness.route,
        harness.run_id,
    )
    before = {path for path in harness.blobs.root.rglob("*") if path.is_file()}
    envelopes = 0
    original = executor._envelope

    def counted_envelope(
        conn: StoreConnection,
        assignment: Assignment,
        authority: Authority,
        content: str,
    ) -> Envelope:
        nonlocal envelopes
        envelopes += 1
        return original(conn, assignment, authority, content)

    monkeypatch.setattr(executor, "_envelope", counted_envelope)
    code = None
    try:
        provider.execute(node.route_node_id, node.module_id, attempt_id=attempt)
    except Refusal as refused:
        code = refused.code
    added = {path for path in harness.blobs.root.rglob("*") if path.is_file()} - before

    assert (
        code,
        completion.calls,
        envelopes,
        len(added),
        _counts(harness),
    ) == (
        RefusalCode.GATE_APPROVAL_MISMATCH,
        1,
        0,
        0,
        (1, [REPORTED], 0, 1, 1),
    )


@dataclass
class _ArbitraryProvider:
    harness: _Harness
    mutate: Callable[[], None]
    calls: int = 0

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        assert self.harness.conn.info.transaction_status is TransactionStatus.IDLE
        assert (route_node_id, module_id) == (
            self.harness.route.nodes[0].route_node_id,
            self.harness.route.nodes[0].module_id,
        )
        assert isinstance(attempt_id, UUID)
        self.calls += 1
        body: dict[str, Any] = {
            "content_to_module_map": [
                {
                    "module_id": "CP-DR",
                    "readiness_status": "READY",
                    "readiness_effect": "ready",
                }
            ]
        }
        digest = self.harness.blobs.put(json.dumps(body).encode())
        self.mutate()
        return ProviderResult(digest, REPORTED, MODEL, "gen-arbitrary")


def test_runtime_rechecks_authority_after_transport_before_acceptance(
    harness: _Harness,
) -> None:
    """OLD-API RED: current runtime accepts the stale arbitrary result."""
    provider = _ArbitraryProvider(harness, lambda: _revoke_during_transport(harness))
    code = None
    try:
        run_route(
            harness.conn,
            harness.blobs,
            run_id=harness.run_id,
            route=harness.route,
            execution=Execution(provider, ESTIMATE, harness.bundle),
        )
    except Refusal as refused:
        code = refused.code

    with connect(harness.url) as observer:
        accepted = observer.execute(
            "SELECT count(*) FROM run_events WHERE name='ATTEMPT_ACCEPTED'"
        ).fetchone()
        completed = observer.execute(
            "SELECT count(*) FROM run_events WHERE name='RUN_COMPLETE'"
        ).fetchone()
    assert accepted is not None and completed is not None
    assert (
        code,
        provider.calls,
        _counts(harness),
        int(accepted[0]),
        int(completed[0]),
    ) == (
        RefusalCode.GATE_APPROVAL_MISMATCH,
        1,
        (1, [REPORTED], 0, 1, 1),
        0,
        0,
    )


@contextmanager
def _guard_disabled(
    conn: StoreConnection,
    table: str,
    trigger: str,
) -> Iterator[None]:
    assert re.fullmatch(r"caos_test_[0-9a-f]{32}", conn.info.dbname)
    enabled = conn.execute(
        "SELECT tgenabled FROM pg_trigger WHERE tgrelid=%s::regclass AND tgname=%s",
        (table, trigger),
    ).fetchone()
    assert enabled == ("O",)
    conn.execute(
        psycopg.sql.SQL("ALTER TABLE {} DISABLE TRIGGER {}").format(
            psycopg.sql.Identifier(table), psycopg.sql.Identifier(trigger)
        )
    )
    try:
        yield
    finally:
        conn.execute(
            psycopg.sql.SQL("ALTER TABLE {} ENABLE TRIGGER {}").format(
                psycopg.sql.Identifier(table), psycopg.sql.Identifier(trigger)
            )
        )
    assert conn.execute(
        "SELECT tgenabled FROM pg_trigger WHERE tgrelid=%s::regclass AND tgname=%s",
        (table, trigger),
    ).fetchone() == ("O",)


def _actor_change(
    harness: _Harness, gate: Gate, *, downgrade: bool
) -> Callable[[], None]:
    actor = uuid4()
    grant(
        harness.conn,
        case_id=harness.case_id,
        user_id=actor,
        standing=Standing.APPROVER,
    )
    harness.conn.commit()
    preview = gate_preview(harness.conn, harness.run_id, gate)
    harness.conn.rollback()
    approve_gate(
        harness.conn,
        GateApproval(
            harness.run_id,
            gate,
            actor,
            preview.preview_sha256,
            preview.input_fingerprint,
        ),
    )

    def change() -> None:
        with connect(harness.url) as other:
            if downgrade:
                grant(
                    other,
                    case_id=harness.case_id,
                    user_id=actor,
                    standing=Standing.READER,
                )
            else:
                revoke(other, case_id=harness.case_id, user_id=actor)
            other.commit()
            assert other.execute(
                "SELECT standing,revoked_at IS NOT NULL FROM case_members"
                " WHERE case_id=%s AND user_id=%s",
                (harness.case_id, actor),
            ).fetchone() == (("READER", False) if downgrade else ("APPROVER", True))

    return change


def _corrupt_input(harness: _Harness, *, remove: bool) -> None:
    with connect(harness.url) as other:
        with _guard_disabled(other, "run_inputs", "input_immutable"):
            if remove:
                changed = other.execute(
                    "DELETE FROM run_inputs WHERE run_id=%s", (harness.run_id,)
                ).rowcount
            else:
                changed = other.execute(
                    "UPDATE run_inputs SET research_json='{}' WHERE run_id=%s",
                    (harness.run_id,),
                ).rowcount
            assert changed == 1
        other.commit()


def _corrupt_route(harness: _Harness) -> None:
    with connect(harness.url) as other:
        with _guard_disabled(other, "run_routes", "route_immutable"):
            assert (
                other.execute(
                    "UPDATE run_routes SET resolved='{}' WHERE run_id=%s",
                    (harness.run_id,),
                ).rowcount
                == 1
            )
        other.commit()


def _mutation(  # noqa: C901
    harness: _Harness, name: str, monkeypatch: pytest.MonkeyPatch
) -> Callable[[], None]:
    if name.startswith("actor_"):
        state, gate = name.removeprefix("actor_").split("_", 1)
        return _actor_change(harness, Gate(gate), downgrade=state == "downgraded")

    def change() -> None:  # noqa: C901
        if name == "bundle_moved":
            manifest = harness.bundle.root / MANIFEST_NAME
            manifest.write_bytes(manifest.read_bytes() + b" ")
            return
        if name == "adapter_mismatch":
            monkeypatch.setattr(methodology, "CLAIMS_ADAPTER_VERSION", "changed")
            return
        if name == "input_missing":
            _corrupt_input(harness, remove=True)
            return
        if name == "input_corrupt":
            _corrupt_input(harness, remove=False)
            return
        if name == "route_corrupt":
            _corrupt_route(harness)
            return
        with connect(harness.url) as other:
            if name.startswith("gate_"):
                state, gate = name.removeprefix("gate_").split("_", 1)
                if state == "missing":
                    changed = other.execute(
                        "DELETE FROM run_gates WHERE run_id=%s AND gate=%s",
                        (harness.run_id, gate),
                    ).rowcount
                else:
                    changed = other.execute(
                        "UPDATE run_gates SET preview_sha256=%s"
                        " WHERE run_id=%s AND gate=%s",
                        ("0" * 64, harness.run_id, gate),
                    ).rowcount
                assert changed == 1
                other.commit()
            elif name.startswith("withdraw_"):
                source = (
                    harness.source_id if name.endswith("cited") else harness.witness_id
                )
                withdraw_source(
                    other,
                    case_id=harness.case_id,
                    source_id=source,
                    actor_id=harness.approver,
                )
            elif name.startswith("identity_"):
                source = (
                    harness.source_id if name.endswith("cited") else harness.witness_id
                )
                assert (
                    other.execute(
                        "UPDATE sources SET document_sha256=%s WHERE case_id=%s"
                        " AND source_id=%s",
                        ("0" * 64, harness.case_id, source),
                    ).rowcount
                    == 1
                )
                other.commit()
            elif name == "failed":
                assert fail_run(other, harness.run_id)
            else:
                assert name == "complete"
                assert complete_run(other, harness.run_id)

    return change


def _invoke_after_transport(
    harness: _Harness, entry: str, mutate: Callable[[], None]
) -> tuple[Refusal | None, int]:
    if entry == "module":
        node = harness.route.nodes[0]
        attempt = start_attempt(harness.conn, harness.run_id, node.route_node_id)
        reserve(harness.conn, attempt, ESTIMATE)
        completion = _DuringCompletion(_Completions(harness.source_id), mutate)
        provider = ModuleProvider(
            harness.conn,
            harness.bundle,
            harness.blobs,
            completion,
            _every_block(harness.conn, harness.source_id),
            harness.route,
            harness.run_id,
        )
        try:
            provider.execute(node.route_node_id, node.module_id, attempt_id=attempt)
        except Refusal as refused:
            return refused, completion.calls
        return None, completion.calls
    arbitrary = _ArbitraryProvider(harness, mutate)
    try:
        run_route(
            harness.conn,
            harness.blobs,
            run_id=harness.run_id,
            route=harness.route,
            execution=Execution(arbitrary, ESTIMATE, harness.bundle),
        )
    except Refusal as refused:
        return refused, arbitrary.calls
    return None, arbitrary.calls


_CHANGES = [
    ("gate_missing_SOURCE_SET", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("gate_mismatch_SOURCE_SET", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("gate_missing_RESEARCH_PLAN", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("gate_mismatch_RESEARCH_PLAN", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("actor_revoked_SOURCE_SET", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("actor_downgraded_SOURCE_SET", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("actor_revoked_RESEARCH_PLAN", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("actor_downgraded_RESEARCH_PLAN", RefusalCode.GATE_APPROVAL_MISMATCH),
    ("withdraw_cited", RefusalCode.EVIDENCE_NOT_AVAILABLE),
    ("withdraw_uncited", RefusalCode.EVIDENCE_NOT_AVAILABLE),
    ("identity_cited", RefusalCode.EVIDENCE_NOT_AVAILABLE),
    ("identity_uncited", RefusalCode.EVIDENCE_NOT_AVAILABLE),
    ("input_missing", RefusalCode.RUN_INPUT_INVALID),
    ("input_corrupt", RefusalCode.RUN_INPUT_INVALID),
    ("route_corrupt", RefusalCode.ROUTE_IDENTITY_INVALID),
    ("failed", RefusalCode.RUN_NOT_RUNNING),
    ("complete", RefusalCode.RUN_NOT_RUNNING),
    ("bundle_moved", RefusalCode.AUTHORITY_BYTES_MISMATCH),
    ("adapter_mismatch", RefusalCode.RUN_INPUT_INVALID),
]


@pytest.mark.parametrize("entry", ["module", "runtime"])
@pytest.mark.parametrize("change,expected", _CHANGES)
def test_check_attempt_and_runtime_recheck_transport_authority_before_use(
    harness: _Harness,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
    change: str,
    expected: RefusalCode,
) -> None:
    """`check_attempt` and the runtime boundary reject stale returned work."""
    refused, calls = _invoke_after_transport(
        harness, entry, _mutation(harness, change, monkeypatch)
    )
    assert refused is not None
    assert (refused.code, str(refused), refused.__cause__, calls) == (
        expected,
        expected.value,
        None,
        1,
    )
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)
    with connect(harness.url) as observer:
        accepted = observer.execute(
            "SELECT count(*) FROM run_events WHERE name='ATTEMPT_ACCEPTED'"
        ).fetchone()
        status = observer.execute(
            "SELECT status FROM runs WHERE run_id=%s", (harness.run_id,)
        ).fetchone()
    assert accepted == (0,)
    expected_status = {"failed": "FAILED", "complete": "COMPLETE"}.get(
        change, "RUNNING"
    )
    assert status == (expected_status,)
