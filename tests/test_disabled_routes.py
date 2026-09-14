"""Only the canonical adapter executes, and only on its own modules (§42.2).

REPAIR_PLAN Phase 3 work item 6: "Keep other routes disabled until equivalent
contract tests exist." Task 3.1 slice f-1c makes the adapter one constant, so a
route whose modules the adapter does not own is refused at execution -- before
any attempt, reservation or provider call -- and at acceptance, while pinning,
gates and resolution stay general. A claims pin written before the switch
refuses execution, and no reader takes an artifact without its host record.
Both refusal points share `require_adapter_route`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from canonical_fixtures import (
    CATALOG,
    LITE_PROFILE,
    LITE_SELECTION,
    CanonicalCompletions,
)
from conftest import priced
from fastapi.testclient import TestClient
from test_accepted_owner import _billed, _count
from test_canonical_readers import _reader, _run, client
from test_execution_freshness import _Harness, harness
from test_gates import _approval
from test_loop_charges import ESTIMATE, MODEL, REPORTED
from test_run_inputs import SUBJECT, pin_version_one
from test_source_sets import _admit

from server import methodology
from server.api.app import app, store_connection
from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import (
    Execution,
    ProviderResult,
    accepted_artifacts,
    run_route,
)
from server.methodology.bundle import Bundle
from server.qualification.proof import assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.gates import Gate, approve_gate, approved_run_input, execution_input
from server.store.members import Standing, grant
from server.store.outcomes import execution_reads
from server.store.routes import pin_route
from server.store.run_inputs import RunInput, pin_run_input
from server.store.runs import Accepted, accept_attempt, start_run
from server.store.source_sets import snapshot_source_set

__all__ = ["client", "harness"]

LITE = (LITE_PROFILE, LITE_SELECTION)
FULL = ("FULL_CREDIT_32", "FULL_CREDIT_ASSESSMENT")
DEEP = ("FULL_CREDIT_32", "DEEP_RESEARCH")
_WORK = ("run_attempts", "budget_reservations", "call_outcomes", "artifacts")


@pytest.fixture
def route(request: pytest.FixtureRequest) -> ResolvedRoute:
    return resolve_route(CATALOG, *getattr(request, "param", LITE))


@dataclass
class _Counting:
    """A provider that must never be asked: every call is recorded."""

    model: str = MODEL
    calls: list[str] = field(default_factory=list)

    def check_context(self, route_node_id: str, module_id: str) -> None:
        self.calls.append(module_id)
        raise AssertionError(module_id)

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        self.calls.append(module_id)
        raise AssertionError(module_id)


def _refusal(call: object) -> RefusalCode:
    assert callable(call)
    with pytest.raises(Refusal) as refused:
        call()
    assert refused.value.__cause__ is None
    return refused.value.code


def _no_work(harness: _Harness) -> None:
    for table in _WORK:
        assert _count(harness, table) == 0, table


@pytest.mark.parametrize("route", [FULL, DEEP], indirect=True)
def test_a_disabled_route_pins_and_governs_but_makes_no_attempt(
    harness: _Harness,
) -> None:
    """Approved end to end with a subject, the route still never executes."""
    pin, _route = _authority(harness)
    assert pin.adapter_version == "canonical-markdown-v1"
    with pytest.raises(Refusal) as refused:
        with execution_reads(harness.conn):
            execution_input(harness.conn, harness.run_id, harness.bundle)
    assert refused.value.code is RefusalCode.HANDOFF_MODULE_UNSUPPORTED
    provider = _Counting()
    with pytest.raises(Refusal) as run:
        run_route(
            harness.conn,
            harness.blobs,
            run_id=harness.run_id,
            route=harness.route,
            execution=Execution(provider, priced(ESTIMATE), harness.bundle),
        )
    assert run.value.code is RefusalCode.HANDOFF_MODULE_UNSUPPORTED
    assert run.value.__cause__ is None and run.value.__context__ is None
    assert provider.calls == []
    _no_work(harness)


def _authority(harness: _Harness) -> tuple[RunInput, ResolvedRoute]:
    with execution_reads(harness.conn):
        pin, stored = approved_run_input(harness.conn, harness.run_id)
    assert stored == harness.route
    return pin, stored


@pytest.mark.parametrize("route", [FULL, DEEP], indirect=True)
def test_acceptance_refuses_a_disabled_route(harness: _Harness) -> None:
    attempt = _billed(harness)
    accepted = Accepted(
        harness.blobs.put(b"artifact"),
        REPORTED,
        MODEL,
        f"g{attempt.hex}",
        record_sha256=harness.blobs.put(b"record"),
    )
    with pytest.raises(Refusal) as refused:
        accept_attempt(harness.conn, attempt_id=attempt, accepted=accepted)
    assert refused.value.code is RefusalCode.HANDOFF_MODULE_UNSUPPORTED
    assert _count(harness, "artifacts") == 0


def test_every_route_pins_the_one_adapter_and_a_subject(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    conn, case_id = case
    _admit(conn, case_id, tmp_path)
    conn.commit()
    source = snapshot_source_set(conn, case_id)
    bundle = Bundle(Path(__file__).resolve().parents[1] / "vendor/deploy-v")
    assert not hasattr(methodology, "adapter_for")
    assert not hasattr(methodology, "CLAIMS_ADAPTER_VERSION")
    for selection in (LITE, FULL, DEEP):
        run = start_run(conn, case_id)
        pin_route(conn, run, resolve_route(CATALOG, *selection))
        conn.commit()
        assert _refusal(
            lambda run=run: pin_run_input(conn, run, source.version, bundle)
        ) is (RefusalCode.RUN_INPUT_INVALID)
        pin = pin_run_input(conn, run, source.version, bundle, subject=SUBJECT)
        assert pin.adapter_version == methodology.CANONICAL_ADAPTER_VERSION


@pytest.mark.parametrize("selection", [LITE, DEEP])
def test_an_existing_claims_pin_refuses_execution(
    case: tuple[StoreConnection, UUID], tmp_path: Path, selection: tuple[str, str]
) -> None:
    """A version-1 `claims-json-v1` pin, fully approved, is authority no longer
    executable: the build/adapter check refuses it before any attempt."""
    conn, case_id = case
    _admit(conn, case_id, tmp_path)
    conn.commit()
    source = snapshot_source_set(conn, case_id)
    bundle = Bundle(Path(__file__).resolve().parents[1] / "vendor/deploy-v")
    route = resolve_route(CATALOG, *selection)
    run = start_run(conn, case_id)
    pin_route(conn, run, route)
    pin = pin_version_one(conn, run, source, bundle, route)
    assert pin.adapter_version == "claims-json-v1"
    approver = uuid4()
    grant(conn, case_id=case_id, user_id=approver, standing=Standing.APPROVER)
    conn.commit()
    for gate in Gate:
        approve_gate(conn, _approval(conn, run, approver, gate))
    with execution_reads(conn):
        assert approved_run_input(conn, run) == (pin, route)
    with pytest.raises(Refusal) as refused:
        with execution_reads(conn):
            execution_input(conn, run, bundle)
    assert refused.value.code is RefusalCode.RUN_INPUT_INVALID
    provider = _Counting()
    with pytest.raises(Refusal) as ran:
        run_route(
            conn,
            BlobStore(tmp_path / "blobs"),
            run_id=run,
            route=route,
            execution=Execution(provider, priced(ESTIMATE), bundle),
        )
    assert ran.value.code is RefusalCode.RUN_INPUT_INVALID
    assert provider.calls == []
    assert conn.execute(
        "SELECT count(*) FROM run_attempts WHERE run_id = %s", (run,)
    ).fetchone() == (0,)


def _strip_record(harness: _Harness, module_id: str) -> None:
    node = next(n for n in harness.route.nodes if n.module_id == module_id)
    harness.conn.execute(
        "UPDATE artifacts SET record_sha256 = NULL WHERE run_id = %s"
        " AND route_node_id = %s",
        (harness.run_id, node.route_node_id),
    )
    harness.conn.commit()


@pytest.mark.parametrize("module_id", ["CP-0", "CP-L10"])
def test_readers_refuse_an_artifact_without_its_record(
    harness: _Harness, client: TestClient, module_id: str
) -> None:
    """No reader takes a row as a claims body: a NULL record refuses, whether
    or not the engine needs that node's readiness."""
    _run(harness, CanonicalCompletions(harness.source_id))
    headers = _reader(harness)
    _strip_record(harness, module_id)
    args = (harness.conn, harness.blobs, harness.route, harness.run_id)
    with pytest.raises(Refusal) as runtime:
        with execution_reads(harness.conn):
            accepted_artifacts(*args, bundle=harness.bundle)
    assert runtime.value.code is RefusalCode.ARTIFACT_RECORD_MISMATCH
    with pytest.raises(Refusal) as proof:
        with execution_reads(harness.conn):
            assert_orchestration_proof(
                harness.conn, harness.blobs, harness.bundle, run_id=harness.run_id
            )
    assert proof.value.code is RefusalCode.ARTIFACT_RECORD_MISMATCH
    app.dependency_overrides[store_connection] = lambda: harness.conn
    response = client.get(f"/api/runs/{harness.run_id}", headers=headers)
    assert response.status_code == 503
    assert response.json() == {"refusal": "ARTIFACT_RECORD_MISMATCH"}
