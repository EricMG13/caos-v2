"""Post-transport authority is fresh before analysis or acceptance."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
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
from server.methodology.executor import Assignment, execute_module
from server.methodology.runner import ModuleProvider
from server.provider import Completion, CompletionProvider
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, connect
from server.store.budget import reserve
from server.store.gates import (
    Gate,
    GateApproval,
    approve_gate,
    execution_input,
    gate_preview,
    withdraw_source,
)
from server.store.members import Standing, grant, revoke
from server.store.outcomes import (
    CallOutcome,
    check_attempt,
    execution_reads,
    record_outcome,
)
from server.store.runs import (
    Accepted,
    accept_attempt,
    complete_run,
    fail_run,
    start_attempt,
    start_run,
)

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
    # Fixed at setup: an observer must still reach a connection closed by the
    # code under test.
    url: str


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
        _url_for(conn.info.dbname),
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
    # F02: a post-call refusal never manufactures a completion of its own.
    assert _events(harness, "RUN_COMPLETE") == (1 if change == "complete" else 0)


def _events(harness: _Harness, name: str) -> int:
    with connect(harness.url) as observer:
        row = observer.execute(
            "SELECT count(*) FROM run_events WHERE name=%s", (name,)
        ).fetchone()
    assert row is not None
    return int(row[0])


def _free(harness: _Harness, table: str) -> bool:
    """Whether an independent connection can lock this case or run row now."""
    column = {"cases": "case_id", "runs": "run_id"}[table]
    key = harness.case_id if table == "cases" else harness.run_id
    with connect(harness.url) as other:
        try:
            other.execute(
                psycopg.sql.SQL(
                    "SELECT 1 FROM {} WHERE {}=%s FOR UPDATE NOWAIT"
                ).format(psycopg.sql.Identifier(table), psycopg.sql.Identifier(column)),
                (key,),
            )
        except psycopg.errors.LockNotAvailable:
            return False
        finally:
            other.rollback()
    return True


def _lockable(harness: _Harness) -> tuple[bool, bool]:
    """(case lock free, run lock free), each probed on its own connection."""
    return _free(harness, "cases"), _free(harness, "runs")


def _still_running(harness: _Harness) -> None:
    """F02: a refused post-call path leaves the run RUNNING, never COMPLETE."""
    with connect(harness.url) as observer:
        status = observer.execute(
            "SELECT status FROM runs WHERE run_id=%s", (harness.run_id,)
        ).fetchone()
    assert (status, _events(harness, "RUN_COMPLETE")) == (("RUNNING",), 0)


def _provider(
    harness: _Harness,
    completions: CompletionProvider,
    route: ResolvedRoute | None = None,
) -> ModuleProvider:
    return ModuleProvider(
        harness.conn,
        harness.bundle,
        harness.blobs,
        completions,
        _every_block(harness.conn, harness.source_id),
        route or harness.route,
        harness.run_id,
    )


def _reserved(harness: _Harness) -> UUID:
    node = harness.route.nodes[0]
    attempt = start_attempt(harness.conn, harness.run_id, node.route_node_id)
    reserve(harness.conn, attempt, ESTIMATE)
    return attempt


def _blob_files(harness: _Harness) -> set[Path]:
    return {path for path in harness.blobs.root.rglob("*") if path.is_file()}


def test_module_provider_control_analyzes_in_one_locked_read_committed_unit(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unmutated control: transport idle and unlocked; bill committed, then one
    READ COMMITTED unit holds the lock through identity, input and envelope."""
    from server.methodology import executor

    stamps: list[tuple[str, object]] = []
    during: list[tuple[object, ...]] = []

    def stamp(name: str, wrapped: Callable[..., object]) -> Callable[..., object]:
        def inner(conn: StoreConnection, *args: object, **kwargs: object) -> object:
            result = wrapped(conn, *args, **kwargs)
            row = conn.execute("SELECT transaction_timestamp()").fetchone()
            stamps.append((name, row))
            return result

        return inner

    def envelope(
        conn: StoreConnection,
        assignment: Assignment,
        authority: Authority,
        content: str,
    ) -> Envelope:
        during.append(
            (
                conn.info.transaction_status,
                conn.execute("SHOW transaction_isolation").fetchone(),
                _counts(harness)[:2],
                _lockable(harness),
            )
        )
        return original(conn, assignment, authority, content)

    original = executor._envelope
    monkeypatch.setattr(executor, "check_attempt", stamp("check", check_attempt))
    monkeypatch.setattr(executor, "execution_input", stamp("input", execution_input))
    monkeypatch.setattr(executor, "_envelope", envelope)
    idle_unlocked: list[tuple[object, tuple[bool, bool]]] = []
    completion = _DuringCompletion(
        _Completions(harness.source_id),
        lambda: idle_unlocked.append(
            (harness.conn.info.transaction_status, _lockable(harness))
        ),
    )
    attempt = _reserved(harness)
    before = _blob_files(harness)
    node = harness.route.nodes[0]

    result = _provider(harness, completion).execute(
        node.route_node_id, node.module_id, attempt_id=attempt
    )

    assert (result.charge, result.model, len(_blob_files(harness) - before)) == (
        REPORTED,
        MODEL,
        1,
    )
    assert idle_unlocked == [(TransactionStatus.IDLE, (True, True))]
    # Pre-call input read, then one post-billing unit: check and input share a
    # transaction the pre-call read did not.
    assert [name for name, _ in stamps] == ["input", "check", "input"]
    assert stamps[1][1] == stamps[2][1] != stamps[0][1]
    assert during == [
        (
            TransactionStatus.INTRANS,
            ("read committed",),
            (1, [REPORTED]),
            (False, False),
        )
    ]
    assert (harness.conn.info.transaction_status, _lockable(harness)) == (
        TransactionStatus.IDLE,
        (True, True),
    )
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)


def test_runtime_control_accepts_every_node_without_duplicating_outcomes(
    harness: _Harness,
) -> None:
    """The outer record of a ModuleProvider result is an exact replay."""
    completions = _Completions(harness.source_id)
    run_route(
        harness.conn,
        harness.blobs,
        run_id=harness.run_id,
        route=harness.route,
        execution=Execution(_provider(harness, completions), ESTIMATE, harness.bundle),
    )

    nodes = len(harness.route.nodes)
    assert _counts(harness) == (nodes, [REPORTED] * nodes, nodes, nodes, nodes)
    assert [
        _events(harness, name)
        for name in ("CALL_OUTCOME_RECORDED", "ATTEMPT_ACCEPTED", "RUN_COMPLETE")
    ] == [nodes, nodes, 1]


def test_whole_route_mismatch_keeping_the_node_is_refused(
    harness: _Harness,
) -> None:
    """A different route holding the same node never becomes analysis."""
    other = replace(harness.route, predicates=(("changed", "route"),))
    assert harness.route.nodes[0] in other.nodes and other != harness.route

    completion = _DuringCompletion(_Completions(harness.source_id), lambda: None)
    node = harness.route.nodes[0]
    attempt = _reserved(harness)
    with pytest.raises(Refusal) as module:
        _provider(harness, completion, other).execute(
            node.route_node_id, node.module_id, attempt_id=attempt
        )
    assert (module.value.code, completion.calls) == (
        RefusalCode.ROUTE_IDENTITY_INVALID,
        0,
    )
    assert _counts(harness) == (0, [], 0, 1, 1)

    arbitrary = _ArbitraryProvider(harness, lambda: None)
    with pytest.raises(Refusal) as runtime:
        run_route(
            harness.conn,
            harness.blobs,
            run_id=harness.run_id,
            route=other,
            execution=Execution(arbitrary, ESTIMATE, harness.bundle),
        )
    assert (runtime.value.code, arbitrary.calls) == (
        RefusalCode.ROUTE_IDENTITY_INVALID,
        0,
    )
    assert _counts(harness) == (0, [], 0, 1, 1)
    _still_running(harness)


def _assignment(harness: _Harness, provider: ModuleProvider) -> Assignment:
    with execution_reads(harness.conn):
        return provider._assignment(harness.route.nodes[0])


def test_direct_executor_refuses_a_mismatched_module_before_any_call(
    harness: _Harness,
) -> None:
    completion = _DuringCompletion(_Completions(harness.source_id), lambda: None)
    provider = _provider(harness, completion)
    assignment = _assignment(harness, provider)
    attempt = _reserved(harness)

    with pytest.raises(Refusal) as module:
        execute_module(
            harness.conn,
            harness.bundle,
            attempt_id=attempt,
            assignment=replace(assignment, module_id="CP-DR"),
            provider=completion,
        )
    assert (module.value.code, completion.calls) == (
        RefusalCode.ROUTE_IDENTITY_INVALID,
        0,
    )
    assert _counts(harness) == (0, [], 0, 1, 1)
    assert harness.conn.info.transaction_status is TransactionStatus.IDLE
    _still_running(harness)


def test_direct_executor_refuses_a_moved_node_before_any_call(
    harness: _Harness,
) -> None:
    completion = _DuringCompletion(_Completions(harness.source_id), lambda: None)
    assignment = _assignment(harness, _provider(harness, completion))
    moved = replace(assignment.node, stage=assignment.node.stage + 7)
    attempt = _reserved(harness)
    with pytest.raises(Refusal) as node:
        execute_module(
            harness.conn,
            harness.bundle,
            attempt_id=attempt,
            assignment=replace(assignment, node=moved),
            provider=completion,
        )
    assert (node.value.code, completion.calls, _counts(harness)) == (
        RefusalCode.ROUTE_IDENTITY_INVALID,
        0,
        (0, [], 0, 1, 1),
    )


@dataclass
class _RefusedCompletion:
    mutate: Callable[[], None]
    model: str = MODEL
    calls: int = 0

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.calls += 1
        self.mutate()
        return Completion(
            content=None,
            charge=REPORTED,
            generation_id="gen-refused",
            refusal=RefusalCode.PROVIDER_REFUSED,
        )


def test_known_provider_refusal_keeps_precedence_over_stale_authority(
    harness: _Harness,
) -> None:
    completion = _RefusedCompletion(lambda: _revoke_during_transport(harness))
    node = harness.route.nodes[0]
    attempt = _reserved(harness)
    with pytest.raises(Refusal) as refused:
        _provider(harness, completion).execute(
            node.route_node_id, node.module_id, attempt_id=attempt
        )
    assert (refused.value.code, refused.value.__cause__, completion.calls) == (
        RefusalCode.PROVIDER_REFUSED,
        None,
        1,
    )
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)
    _still_running(harness)


def _fail_in_analysis(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch, failure: Callable[[], None]
) -> Refusal | BaseException:
    from server.methodology import executor

    original = execution_input

    reads = 0

    def failing(conn: StoreConnection, run_id: UUID, bundle: Bundle) -> object:
        nonlocal reads
        reads += 1
        result = original(conn, run_id, bundle)
        if reads == 2:  # The post-billing read, not the pre-call one.
            failure()
        return result

    monkeypatch.setattr(executor, "execution_input", failing)
    completion = _DuringCompletion(_Completions(harness.source_id), lambda: None)
    node = harness.route.nodes[0]
    attempt = _reserved(harness)
    provider = _provider(harness, completion)
    with pytest.raises(BaseException) as caught:
        provider.execute(node.route_node_id, node.module_id, attempt_id=attempt)
    assert completion.calls == 1
    return caught.value


def test_native_sql_error_after_billing_is_sanitized_and_leaves_the_bill(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    def divide() -> None:
        harness.conn.execute("SELECT 1/0")

    raised = _fail_in_analysis(harness, monkeypatch, divide)
    assert isinstance(raised, Refusal)
    assert (raised.code, raised.__cause__, harness.conn.info.transaction_status) == (
        RefusalCode.STORE_UNAVAILABLE,
        None,
        TransactionStatus.IDLE,
    )
    assert (_counts(harness), _lockable(harness)) == (
        (1, [REPORTED], 0, 1, 1),
        (True, True),
    )
    _still_running(harness)


def test_cancellation_in_analysis_propagates_and_leaves_the_bill(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    def cancel() -> None:
        raise KeyboardInterrupt

    raised = _fail_in_analysis(harness, monkeypatch, cancel)
    assert type(raised) is KeyboardInterrupt
    assert harness.conn.info.transaction_status is TransactionStatus.IDLE
    assert (_counts(harness), _lockable(harness)) == (
        (1, [REPORTED], 0, 1, 1),
        (True, True),
    )
    _still_running(harness)


def test_rollback_failure_closes_and_keeps_the_typed_refusal(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse_and_break_rollback() -> None:
        def broken() -> None:
            raise psycopg.OperationalError

        monkeypatch.setattr(harness.conn, "rollback", broken)
        raise Refusal(RefusalCode.ENVELOPE_INVALID)

    raised = _fail_in_analysis(harness, monkeypatch, refuse_and_break_rollback)
    assert isinstance(raised, Refusal)
    assert (raised.code, harness.conn.closed) == (RefusalCode.ENVELOPE_INVALID, True)
    assert (_counts(harness), _lockable(harness)) == (
        (1, [REPORTED], 0, 1, 1),
        (True, True),
    )
    _still_running(harness)


@dataclass
class _Charged:
    """An arbitrary Provider answering every node with one fixed call fact."""

    harness: _Harness
    charge: Decimal | None
    mutate: Callable[[], None] = lambda: None

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        assert self.harness.conn.info.transaction_status is TransactionStatus.IDLE
        body = {
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
        return ProviderResult(digest, self.charge, MODEL, f"gen-{route_node_id}")  # type: ignore[arg-type]


def _run(harness: _Harness, provider: _Charged) -> RefusalCode | None:
    try:
        run_route(
            harness.conn,
            harness.blobs,
            run_id=harness.run_id,
            route=harness.route,
            execution=Execution(provider, ESTIMATE, harness.bundle),
        )
    except Refusal as refused:
        assert refused.__cause__ is None
        return refused.code
    return None


def test_unknown_charge_is_recorded_without_spend_and_never_accepted(
    harness: _Harness,
) -> None:
    assert _run(harness, _Charged(harness, None)) is RefusalCode.MONEY_NOT_DECIMAL
    assert _counts(harness) == (1, [], 0, 1, 1)
    assert [_events(harness, n) for n in ("ATTEMPT_ACCEPTED", "RUN_COMPLETE")] == [
        0,
        0,
    ]


def test_zero_charge_is_known_spend_and_replay_never_duplicates(
    harness: _Harness,
) -> None:
    assert _run(harness, _Charged(harness, Decimal("0"))) is None
    nodes = len(harness.route.nodes)
    assert _counts(harness) == (nodes, [Decimal("0")] * nodes, nodes, nodes, nodes)

    attempt = harness.conn.execute(
        "SELECT attempt_id FROM run_attempts ORDER BY started_at LIMIT 1"
    ).fetchone()
    harness.conn.rollback()
    assert attempt is not None
    first = harness.route.nodes[0].route_node_id
    replay = CallOutcome(Decimal("0"), MODEL, f"gen-{first}")
    assert record_outcome(harness.conn, attempt_id=attempt[0], outcome=replay) is False
    with pytest.raises(Refusal) as conflict:
        record_outcome(
            harness.conn,
            attempt_id=attempt[0],
            outcome=replace(replay, charge=REPORTED),
        )
    assert conflict.value.code is RefusalCode.CALL_OUTCOME_CONFLICT
    assert _counts(harness) == (nodes, [Decimal("0")] * nodes, nodes, nodes, nodes)
    assert _events(harness, "CALL_OUTCOME_RECORDED") == nodes


def test_outcome_persistence_failure_accepts_nothing_and_keeps_the_reservation(
    harness: _Harness,
) -> None:
    def hide_outcomes() -> None:
        with connect(harness.url) as other:
            assert re.fullmatch(r"caos_test_[0-9a-f]{32}", other.info.dbname)
            other.execute("ALTER TABLE call_outcomes RENAME TO call_outcomes_hidden")
            other.commit()

    try:
        code = _run(harness, _Charged(harness, REPORTED, hide_outcomes))
    finally:
        with connect(harness.url) as other:
            other.execute("ALTER TABLE call_outcomes_hidden RENAME TO call_outcomes")
            other.commit()

    assert (code, harness.conn.info.transaction_status) == (
        RefusalCode.STORE_UNAVAILABLE,
        TransactionStatus.IDLE,
    )
    assert _counts(harness) == (0, [], 0, 1, 1)
    assert [
        _events(harness, n) for n in ("CALL_OUTCOME_RECORDED", "ATTEMPT_ACCEPTED")
    ] == [0, 0]
    _still_running(harness)


def test_guard_is_restored_when_the_guarded_change_fails(harness: _Harness) -> None:
    with connect(harness.url) as other:
        with pytest.raises(ValueError):
            with _guard_disabled(other, "run_routes", "route_immutable"):
                raise ValueError
        assert other.execute(
            "SELECT tgenabled FROM pg_trigger"
            " WHERE tgrelid='run_routes'::regclass AND tgname='route_immutable'"
        ).fetchone() == ("O",)
        other.rollback()
        with pytest.raises(psycopg.errors.RaiseException):
            other.execute(
                "UPDATE run_routes SET resolved='{}' WHERE run_id=%s",
                (harness.run_id,),
            )


def test_accept_boundary_refuses_authority_revoked_after_the_runtime_check(
    harness: _Harness,
) -> None:
    """Task17d3a RED: acceptance inserts after a committed revocation."""
    attempt = _reserved(harness)
    node = harness.route.nodes[0]
    record_outcome(
        harness.conn,
        attempt_id=attempt,
        outcome=CallOutcome(REPORTED, MODEL, "gen-accept"),
    )
    _revoke_during_transport(harness)
    digest = harness.blobs.put(b"{}")
    with pytest.raises(Refusal) as refused:
        accept_attempt(
            harness.conn,
            attempt_id=attempt,
            accepted=Accepted(digest, REPORTED, MODEL, "gen-accept"),
        )
    assert (refused.value.code, refused.value.__cause__) == (
        RefusalCode.GATE_APPROVAL_MISMATCH,
        None,
    )
    assert node.route_node_id in {n.route_node_id for n in harness.route.nodes}
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)
    assert _events(harness, "ATTEMPT_ACCEPTED") == 0
    _still_running(harness)
