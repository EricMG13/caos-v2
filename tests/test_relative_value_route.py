"""The one added pathway completes/proves/freezes or blocks without more calls."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from canonical_fixtures import BUNDLE, CATALOG, fields_from_prompt
from canonical_route_fixtures import (
    LIMITATION,
    MODULES,
    PACK,
    ROUTE,
    SELECTION,
    RouteCompletions,
)
from conftest import _url_for, priced
from test_canonical_runtime import _module_provider, _run_route, _status
from test_execution_freshness import _counts, _events, _Harness
from test_gates import _approval
from test_lite_route_e2e_positive import _revision
from test_loop_charges import ESTIMATE

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.deliverable.canonical import canonical_payload
from server.deliverable.render import render
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import Execution, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.handoff import ADAPTER_ROUTES
from server.provider import MAX_REQUEST_BYTES
from server.qualification.proof import assert_orchestration_proof
from server.refusals import RefusalCode
from server.store import StoreConnection
from server.store.gates import Gate, approve_gate
from server.store.members import Standing, grant
from server.store.routes import pin_route
from server.store.run_inputs import RunSubject, pin_run_input
from server.store.runs import start_run
from server.store.source_sets import snapshot_source_set


@pytest.fixture
def route(request: pytest.FixtureRequest) -> ResolvedRoute:
    return resolve_route(CATALOG, *getattr(request, "param", SELECTION))


@pytest.fixture
def harness(
    case: tuple[StoreConnection, UUID], tmp_path: Path, route: ResolvedRoute
) -> _Harness:
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    [source] = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[Document(filename=BoundaryText.of("issuer-pack.txt"), data=PACK)],
    )
    run_id = start_run(conn, case_id)
    conn.commit()
    source_set = snapshot_source_set(conn, case_id)
    pin_route(conn, run_id, route)
    pin_run_input(
        conn,
        run_id,
        source_set.version,
        BUNDLE,
        subject=RunSubject("ACME", "Acme Holdings plc", "FY2025", "2026-09-08"),
    )
    approver = uuid4()
    grant(conn, case_id=case_id, user_id=approver, standing=Standing.APPROVER)
    conn.commit()
    for gate in Gate:
        approve_gate(conn, _approval(conn, run_id, approver, gate))
    return _Harness(
        conn,
        case_id,
        run_id,
        source,
        source,
        blobs,
        route,
        BUNDLE,
        approver,
        _url_for(conn.info.dbname),
    )


def run_completed(
    harness: _Harness, answers: RouteCompletions | None = None
) -> RouteCompletions:
    answers = answers or RouteCompletions(harness.source_id)
    run_route(
        harness.conn,
        harness.blobs,
        run_id=harness.run_id,
        route=harness.route,
        execution=Execution(
            _module_provider(harness, answers), priced(ESTIMATE), BUNDLE
        ),
    )
    assert _status(harness) == "COMPLETE"
    assert [fields_from_prompt(p)["module_id"] for p in answers.prompts] == list(
        MODULES
    )
    return answers


def test_relative_value_route_completes_proves_and_freezes(harness: _Harness) -> None:
    import hashlib
    from dataclasses import replace
    from uuid import uuid4

    from server.boundary_text import BoundaryText
    from server.deliverable.canonical import (
        freeze_canonical,
        payload_bytes,
        verify_frozen,
    )
    from server.deliverable.filing import sign_opinion
    from server.deliverable.revisions import read_revision, save_revision
    from server.store.members import Standing, grant

    answers = run_completed(harness)
    proof = assert_orchestration_proof(
        harness.conn, harness.blobs, BUNDLE, run_id=harness.run_id
    )
    harness.conn.rollback()
    assert proof.artifacts == proof.citations == 9
    assert {m for m, _, _ in proof.anchored} == set(MODULES)
    saved = save_revision(
        harness.conn,
        harness.blobs,
        BUNDLE,
        case_id=harness.case_id,
        run_id=harness.run_id,
        actor_id=harness.approver,
        narrative=[],
    )
    revision = replace(_revision(harness), revision_id=BoundaryText.of(str(saved)))
    payload = read_revision(
        harness.conn, harness.blobs, case_id=harness.case_id, revision_id=saved
    )
    harness.conn.rollback()
    assert [a["route_node_id"] for a in payload["artifacts"]] == [
        n.route_node_id for n in ROUTE.nodes
    ]
    data = payload_bytes(payload)
    sign_opinion(
        harness.conn,
        case_id=harness.case_id,
        actor_id=harness.approver,
        revision_id=saved,
    )
    freezer = uuid4()
    grant(
        harness.conn,
        case_id=harness.case_id,
        user_id=freezer,
        standing=Standing.APPROVER,
    )
    harness.conn.commit()
    assert (
        freeze_canonical(
            harness.conn, harness.blobs, BUNDLE, revision, actor_id=freezer
        )
        == hashlib.sha256(data).hexdigest()
    )
    verify_frozen(
        harness.conn,
        harness.blobs,
        BUNDLE,
        case_id=harness.case_id,
        revision_id=saved,
        payload=data,
    )
    cp3 = fields_from_prompt(answers.prompts[-1])
    assert {r["module_id"] for r in cp3["upstream_artifacts_used"]} == {
        e.source for e in ROUTE.edges if e.target == "CP-3"
    }


def test_relative_value_requests_fit_the_request_ceiling(harness: _Harness) -> None:
    answers = run_completed(harness)
    assert len(answers.prompts) == 9
    assert all(
        len(answers.request_bytes(p, json_object=True)) <= MAX_REQUEST_BYTES
        for p in answers.prompts
    )


def test_a_blocked_cp1_holds_every_dependent_and_calls_nothing_after(
    harness: _Harness,
) -> None:
    answers = RouteCompletions(harness.source_id, qa_by_module={"CP-1": "Blocked"})
    assert _run_route(harness, _module_provider(harness, answers)) is None
    assert [fields_from_prompt(p)["module_id"] for p in answers.prompts] == [
        "CP-0",
        "CP-1",
    ]
    assert _status(harness) == "BLOCKED"
    assert _events(harness, "RUN_BLOCKED") == 1
    assert _events(harness, "RUN_COMPLETE") == 0
    assert _counts(harness) == (2, [answers.charge] * 2, 1, 2, 2)


def test_a_restricted_owner_keeps_its_limitations_downstream(harness: _Harness) -> None:
    answers = run_completed(
        harness,
        RouteCompletions(harness.source_id, qa_by_module={"CP-1": "Restricted"}),
    )
    assert LIMITATION in answers.prompts[-1]
    payload = canonical_payload(harness.conn, harness.blobs, BUNDLE, _revision(harness))
    assert LIMITATION in render(payload).decode()


def test_missing_optional_peer_input_restricts_cp3_but_does_not_complete_the_route(
    harness: _Harness,
) -> None:
    from server.engine.route import NodeState, node_states
    from server.engine.runtime import accepted_artifacts

    answers = RouteCompletions(harness.source_id, readiness={"CP-1C": "BLOCKED"})
    assert _run_route(harness, _module_provider(harness, answers)) is None
    assert _status(harness) == "BLOCKED"
    called = [fields_from_prompt(p) for p in answers.prompts]
    assert "CP-1C" not in {p["module_id"] for p in called}
    cp3 = next(p for p in called if p["module_id"] == "CP-3")
    assert "CP-1C" not in {r["module_id"] for r in cp3["upstream_artifacts_used"]}
    accepted = accepted_artifacts(
        harness.conn, harness.blobs, ROUTE, harness.run_id, bundle=BUNDLE
    )
    before_cp3 = {
        n: r for n, r in accepted.items() if n != ROUTE.nodes[-1].route_node_id
    }
    assert (
        node_states(ROUTE, before_cp3)[ROUTE.nodes[-1].route_node_id]
        is NodeState.RESTRICTED
    )
    harness.conn.rollback()


# Every catalog pathway of every profile that `ADAPTER_ROUTES` does not enable.
# Read from the catalog and the constant rather than listed, so enabling a
# pathway moves it out of this guard and into its own contract test instead of
# leaving a pathway nothing covers -- and so a pathway the catalog gains is
# driven here from the day it exists.
DISABLED = [
    (profile, selection)
    for profile, declared in CATALOG["profiles"].items()
    for selection in declared["pathways"]
    if (profile, selection) not in ADAPTER_ROUTES
]
# The exact enabled set, asserted here and in each pathway's own contract test.
ENABLED = frozenset(
    {
        SELECTION,
        ("LITE_CREDIT_22", "LITE_EARNINGS_UPDATE"),
        ("LITE_CREDIT_22", "LITE_PORTFOLIO_DECISION"),
    }
)


@pytest.mark.parametrize("route", DISABLED, indirect=True)
def test_relative_value_is_the_only_newly_enabled_route(harness: _Harness) -> None:
    assert ADAPTER_ROUTES == ENABLED
    assert len(DISABLED) + len(ENABLED) == sum(
        len(declared["pathways"]) for declared in CATALOG["profiles"].values()
    )
    answers = RouteCompletions(harness.source_id)
    assert (
        _run_route(harness, _module_provider(harness, answers))
        is RefusalCode.HANDOFF_MODULE_UNSUPPORTED
    )
    assert answers.prompts == []
    assert _counts(harness) == (0, [], 0, 0, 0)
