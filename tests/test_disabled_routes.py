"""Only the canonical adapter executes, and only on its own modules (§42.2).

REPAIR_PLAN Phase 3 work item 6: "Keep other routes disabled until equivalent
contract tests exist." Task 3.1 slice f-1c makes the adapter one constant, so a
route whose modules the adapter does not own is refused at execution -- before
any attempt, reservation or provider call -- and at acceptance, while pinning,
gates and resolution stay general. No reader takes an artifact without its
host record.
Both refusal points share `require_adapter_route`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

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
from test_loop_charges import ESTIMATE, MODEL, REPORTED

from server.api.app import app, store_connection
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import (
    Execution,
    ProviderResult,
    accepted_artifacts,
    run_route,
)
from server.methodology.executor import Assignment, ModuleOutcome, execute_module
from server.qualification.proof import assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store.budget import reserve
from server.store.gates import approved_run_input, execution_input
from server.store.outcomes import execution_reads
from server.store.run_inputs import RunInput
from server.store.runs import Accepted, accept_attempt, start_attempt

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
    """Approved end to end, the route still never executes."""
    _pin, _route = _authority(harness)
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


@dataclass
class _NeverCompletes:
    model: str = MODEL
    prompts: list[str] = field(default_factory=list)

    def complete(self, prompt: str, *, json_object: bool = False) -> object:
        self.prompts.append(prompt)
        raise AssertionError(prompt[:0])


@pytest.mark.parametrize(
    ("route", "code"),
    [
        (LITE, RefusalCode.RUN_INPUT_INVALID),
        (DEEP, RefusalCode.HANDOFF_MODULE_UNSUPPORTED),
    ],
    indirect=["route"],
)
def test_the_retired_claims_executor_is_unreachable_from_any_pin(
    harness: _Harness, code: RefusalCode
) -> None:
    """Every pin is canonical, so `execute_module` refuses under its own read
    unit before any prompt: no `ModuleOutcome` can be produced (f-2b deletes
    it)."""
    node = harness.route.nodes[0]
    attempt = start_attempt(harness.conn, harness.run_id, node.route_node_id)
    reserve(harness.conn, attempt, ESTIMATE)
    never = _NeverCompletes()
    outcome: ModuleOutcome | None = None
    with pytest.raises(Refusal) as refused:
        outcome = execute_module(
            harness.conn,
            harness.bundle,
            harness.blobs,
            assignment=Assignment(
                node.module_id, harness.run_id, node, harness.route, attempt
            ),
            provider=never,  # type: ignore[arg-type]
        )
    assert refused.value.code is code and outcome is None
    assert never.prompts == []


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
