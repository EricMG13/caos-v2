"""The run document, and privacy.

`docs/REBUILD_PLAN.md` Phase 6: "The run endpoint serves node states with their
reasons, and the one QA_GATE reads as a gate". The one QA_GATE in the catalog is
`CP-5 -> CP-6`, and a node held by it is not in the same situation as a node held
by an ordinary REQUIRED edge: one is waiting for a person, the other for a
module. A surface that rendered both as "BLOCKED" would leave a reviewer with no
way to see that the run is waiting on them.

`test_unauthorised_case_is_private_404` is the second of the named pair from the
plan's standing rules. The first, identity derivation, is in
`tests/test_actor_matrix.py`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel

from server.api.app import (
    IO_BUDGET,
    EdgeView,
    NodeView,
    RefusalBody,
    RunDocument,
    app,
    blob_store,
    read_run,
    store_connection,
)
from server.blobs import BlobStore
from server.engine.route import resolve_route
from server.refusals import RefusalCode
from server.store import StoreConnection
from server.store.members import Standing, grant, revoke
from server.store.routes import pin_route, pinned_route
from server.store.runs import start_run

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return loaded


@pytest.fixture
def client(case: tuple[StoreConnection, UUID], tmp_path: Path) -> Iterator[TestClient]:
    """The app served against the test's own database and blob root.

    Overriding the two dependencies rather than pointing environment variables at
    the fixture keeps the production path -- open a connection per request from
    `CAOS_DATABASE_URL` -- the only path the process itself has.
    """
    conn, _case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    app.dependency_overrides[store_connection] = lambda: conn
    app.dependency_overrides[blob_store] = lambda: blobs
    try:
        with TestClient(app) as opened:
            yield opened
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def run(case: tuple[StoreConnection, UUID]) -> tuple[UUID, UUID]:
    """A run, and a READER entitled to see it."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    viewer = uuid4()
    grant(conn, case_id=case_id, user_id=viewer, standing=Standing.READER)
    conn.commit()
    return run_id, viewer


def _as(user_id: UUID) -> dict[str, str]:
    """Headers for an authenticated caller with no asserted groups."""
    return {"x-caos-user": str(user_id)}


def test_unauthorised_case_is_private_404(
    client: TestClient, run: tuple[UUID, UUID]
) -> None:
    """A named test.

    A stranger asking about somebody else's run gets the answer they would get
    for a run that does not exist. 403 is the informative answer and that is the
    problem with it: it confirms the id names something real, which for a case
    id is the fact worth protecting.
    """
    run_id, _viewer = run
    stranger = uuid4()

    response = client.get(f"/api/runs/{run_id}", headers=_as(stranger))

    assert response.status_code == 404
    assert response.json() == {"refusal": "RUN_NOT_FOUND"}


def test_an_unknown_run_is_the_same_404(client: TestClient) -> None:
    """The other half of the pair. The two answers have to be identical, or the
    difference between them is the disclosure."""
    response = client.get(f"/api/runs/{uuid4()}", headers=_as(uuid4()))

    assert response.status_code == 404
    assert response.json() == {"refusal": "RUN_NOT_FOUND"}


def test_a_revoked_reader_stops_being_able_to_read_it(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """Standing is read at the request, not cached in a session."""
    conn, case_id = case
    run_id, viewer = run
    assert client.get(f"/api/runs/{run_id}", headers=_as(viewer)).status_code == 200

    revoke(conn, case_id=case_id, user_id=viewer)
    conn.commit()

    assert client.get(f"/api/runs/{run_id}", headers=_as(viewer)).status_code == 404


def test_a_request_with_no_identity_is_401_not_404(
    client: TestClient, run: tuple[UUID, UUID]
) -> None:
    """Unauthenticated and unauthorised are different questions. "I do not know
    who you are" discloses nothing about the run, so it can be said plainly --
    and a client that got a 404 would retry the wrong thing forever."""
    run_id, _viewer = run

    response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 401
    assert response.json() == {"refusal": "NOT_AUTHENTICATED"}


def test_the_run_document_carries_node_states_with_their_reasons(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    """Phase 6: "node states with their reasons". A state with no cause attached
    tells a reader the run is stuck without telling them what it is stuck on."""
    conn, _case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW"))

    body = client.get(f"/api/runs/{run_id}", headers=_as(viewer)).json()

    assert body["status"] == "RUNNING"
    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert by_module["CP-0"]["state"] == "RUNNABLE"
    assert by_module["CP-0"]["waiting_on"] == []
    assert by_module["CP-1"]["state"] == "BLOCKED"
    assert {
        (edge["source"], edge["type"]) for edge in by_module["CP-1"]["waiting_on"]
    } == {("CP-0", "REQUIRED")}


def test_the_one_qa_gate_reads_as_a_gate(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    """The catalog holds exactly one QA_GATE edge, `CP-5 -> CP-6`. A node held by
    it is waiting for a person; every other BLOCKED node is waiting for a
    module, and a surface that rendered both the same way would hide the one
    thing a reviewer can act on."""
    conn, _case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT"))

    body = client.get(f"/api/runs/{run_id}", headers=_as(viewer)).json()

    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert by_module["CP-6"]["awaiting_gate"] is True
    assert by_module["CP-1"]["awaiting_gate"] is False
    assert sum(node["awaiting_gate"] for node in body["nodes"]) == 1


def test_a_run_with_no_pinned_route_has_no_nodes(
    client: TestClient, run: tuple[UUID, UUID]
) -> None:
    """A run before its plan gate. Not an error -- there is simply no route to
    report states from yet, and inventing one would be the surface guessing."""
    run_id, viewer = run

    body = client.get(f"/api/runs/{run_id}", headers=_as(viewer)).json()

    assert body["nodes"] == []
    assert body["route_digest"] is None


def test_the_run_document_refuses_an_undeclared_field(
    client: TestClient, run: tuple[UUID, UUID]
) -> None:
    """§9's closed shape, on the way out as well as in. A response model that
    let an extra key through would let a store column reach a browser because
    somebody widened a SELECT."""
    run_id, viewer = run
    body = client.get(f"/api/runs/{run_id}", headers=_as(viewer)).json()

    assert set(body) == set(RunDocument.model_fields)
    with pytest.raises(ValueError, match="extra_forbidden"):
        RunDocument.model_validate({**body, "budget_ceiling": "40.00"})


@pytest.mark.parametrize("model", [RunDocument, NodeView, EdgeView, RefusalBody])
def test_every_wire_model_forbids_an_undeclared_field(
    model: type[BaseModel],
) -> None:
    """The standing rule: every JSON success serves a named model,
    `extra="forbid"` both ways. One model left open is the hole, so the property
    is asserted of each rather than of the one that happens to be on top."""
    assert model.model_config.get("extra") == "forbid"


def test_the_wire_key_sets_are_pinned() -> None:
    """ "A new field means a model change plus an updated pinned key set". This
    is the pinned key set: a field added to a response without a decision about
    it fails here first."""
    assert set(RunDocument.model_fields) == {
        "run_id",
        "status",
        "route_digest",
        "nodes",
    }
    assert set(NodeView.model_fields) == {
        "route_node_id",
        "module_id",
        "state",
        "waiting_on",
        "awaiting_gate",
    }
    assert set(EdgeView.model_fields) == {"source", "type"}
    assert set(RefusalBody.model_fields) == {"refusal"}


def test_a_refusal_says_the_code_and_nothing_else(client: TestClient) -> None:
    """The typed refusal, on the wire. A body that also carried a message would
    be the one place a document's contents could still get out."""
    response = client.get(f"/api/runs/{uuid4()}", headers=_as(uuid4()))

    assert set(response.json()) == set(RefusalBody.model_fields)
    assert RefusalBody.model_validate(response.json()).refusal is (
        RefusalCode.RUN_NOT_FOUND
    )


def test_the_surface_is_exactly_the_routes_it_declares(
    client: TestClient,
) -> None:
    """A route added without a test is a request path nobody agreed to. Listing
    them here means a new one has to be written down before it can ship."""
    declared = {
        route.path: route.endpoint.__name__
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    assert declared == {"/api/runs/{run_id}": read_run.__name__}


def test_the_reported_digest_is_the_one_that_was_pinned(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    """The document recomputes the digest from the route it read back. That is
    only sound while it still equals the digest execution reads."""
    conn, _case_id = case
    run_id, viewer = run
    pinned = pin_route(
        conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    )

    body = client.get(f"/api/runs/{run_id}", headers=_as(viewer)).json()

    assert body["route_digest"] == pinned == pinned_route(conn, run_id)


def test_each_request_path_declares_what_it_costs_the_store(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    """`scripts/io_budget.py`. A request path with no stated round-trip cost is
    how the predecessor's ~8x read amplification went unnoticed -- so the number
    is counted here, not asserted from memory.
    """
    conn, _case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT"))
    counter = _CountingConnection(conn)
    app.dependency_overrides[store_connection] = lambda: counter

    assert client.get(f"/api/runs/{run_id}", headers=_as(viewer)).status_code == 200

    assert counter.executed == IO_BUDGET, (
        "the run document costs what it says it costs; a read that grew with "
        "the size of the route would show up here first"
    )


class _CountingConnection:
    """Counts store round trips, so the declared budget is measured."""

    def __init__(self, conn: StoreConnection) -> None:
        self._conn = conn
        self.executed = 0

    def execute(self, *args: object, **kwargs: object) -> object:
        self.executed += 1
        return self._conn.execute(*args, **kwargs)  # type: ignore[arg-type]
