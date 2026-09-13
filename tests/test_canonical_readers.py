"""Canonical runs read back by the API and the harness (Task 3.1 slice d-1).

The route engine reads typed `NodeResult`s, and both readers now hand
`accepted_artifacts` the bundle, so a LITE run's gate verdicts and QA status
come from its records (§42.4) rather than refusing -- or, in the harness,
falling back to presence, which would read a gate-BLOCKED module as RUNNABLE.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from canonical_fixtures import CanonicalCompletions
from conftest import priced
from fastapi.testclient import TestClient
from test_api_routes import _CountingConnection
from test_canonical_execution import harness, route
from test_execution_freshness import _Harness
from test_loop_charges import ESTIMATE

from server.api import app as app_module
from server.api.app import (
    CANONICAL_READINESS_IO,
    IO_BUDGET,
    READINESS_ROWS,
    RUN_READ_IO,
    VENDORED_BUNDLE,
    app,
    blob_store,
    methodology_bundle,
    store_connection,
)
from server.engine.route import GATE_MODULE, EdgeType, NodeState
from server.engine.runtime import Execution, run_route
from server.methodology.runner import ModuleProvider
from server.qualification.harness import _unrun
from server.store.members import Standing, grant
from server.store.outcomes import execution_reads

__all__ = ["harness", "route"]


def _run(harness: _Harness, answers: CanonicalCompletions) -> None:
    provider = ModuleProvider(
        harness.conn,
        harness.bundle,
        harness.blobs,
        answers,
        harness.route,
        harness.run_id,
    )
    run_route(
        harness.conn,
        harness.blobs,
        run_id=harness.run_id,
        route=harness.route,
        execution=Execution(provider, priced(ESTIMATE), harness.bundle),
    )


@pytest.fixture
def client(
    harness: _Harness, empty_database: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)
    app.dependency_overrides[store_connection] = lambda: harness.conn
    app.dependency_overrides[blob_store] = lambda: harness.blobs
    app.dependency_overrides[methodology_bundle] = lambda: harness.bundle
    try:
        with TestClient(app) as opened:
            yield opened
    finally:
        app.dependency_overrides.clear()


def _reader(harness: _Harness) -> dict[str, str]:
    viewer = uuid4()
    grant(
        harness.conn, case_id=harness.case_id, user_id=viewer, standing=Standing.READER
    )
    harness.conn.commit()
    return {"x-caos-user": str(viewer)}


def test_the_run_document_reads_a_completed_lite_run_from_its_records(
    harness: _Harness, client: TestClient
) -> None:
    _run(harness, CanonicalCompletions(harness.source_id))
    headers = _reader(harness)
    counter = _CountingConnection(harness.conn)
    app.dependency_overrides[store_connection] = lambda: counter

    response = client.get(f"/api/runs/{harness.run_id}", headers=headers)

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["status"] == "COMPLETE"
    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert sorted(by_module) == ["CP-0", "CP-5", "CP-L10"]
    assert {m: n["state"] for m, n in by_module.items()} == dict.fromkeys(
        by_module, "COMPLETE"
    )
    assert {m: n["gate_verdict"] for m, n in by_module.items()} == {
        "CP-0": None,
        "CP-5": "READY",
        "CP-L10": "READY",
    }
    # Measured: one identity rebuild per canonical readiness row, within budget.
    qa_sources = {e.source for e in harness.route.edges if e.type is EdgeType.QA_GATE}
    rows = sum(
        n.module_id == GATE_MODULE or n.module_id in qa_sources
        for n in harness.route.nodes
    )
    assert 1 <= rows <= READINESS_ROWS
    assert counter.executed == RUN_READ_IO + rows * CANONICAL_READINESS_IO
    assert counter.executed <= IO_BUDGET


def test_a_gate_blocked_module_reads_as_blocked_by_its_verdict(
    harness: _Harness, client: TestClient
) -> None:
    _run(
        harness,
        CanonicalCompletions(harness.source_id, readiness={"CP-L10": "BLOCKED"}),
    )
    headers = _reader(harness)

    body = client.get(f"/api/runs/{harness.run_id}", headers=headers).json()

    assert body["status"] == "BLOCKED"
    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert (
        by_module["CP-L10"]["state"],
        by_module["CP-L10"]["waiting_on"],
        by_module["CP-L10"]["gate_verdict"],
    ) == ("BLOCKED", [], "BLOCKED")


def test_the_harness_keeps_gate_readiness_on_a_canonical_run(harness: _Harness) -> None:
    """Presence alone would leave CP-L10 RUNNABLE: its only blocking edge is
    from the accepted gate. BLOCKED is the gate's verdict, read from its record."""
    _run(
        harness,
        CanonicalCompletions(harness.source_id, readiness={"CP-L10": "BLOCKED"}),
    )
    with execution_reads(harness.conn):
        unrun = _unrun(harness.conn, harness.blobs, harness.bundle, harness.run_id)

    screen = next(n for n in harness.route.nodes if n.module_id == "CP-L10")
    assert [(u.route_node_id, u.state, u.attempts) for u in unrun] == [
        (screen.route_node_id, NodeState.BLOCKED, ())
    ]


def test_the_api_verifies_records_under_the_vendored_bundle() -> None:
    assert methodology_bundle().root == VENDORED_BUNDLE
    assert methodology_bundle() is methodology_bundle()
