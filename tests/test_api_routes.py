"""The two request paths: the run document, the tail over a socket, and privacy.

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
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel

from server.api import app as app_module
from server.api.app import (
    IO_BUDGET,
    TAIL_DEADLINE,
    EdgeView,
    NodeView,
    RefusalBody,
    RunDocument,
    app,
    blob_store,
    read_run,
    read_run_events,
    store_connection,
)
from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, resolve_route
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.members import Standing, grant, revoke, standing_of
from server.store.routes import pin_route, pinned_route
from server.store.runs import (
    Accepted,
    accept_attempt,
    complete_attempt,
    start_attempt,
    start_run,
)

# The producer the store records beside every accepted artifact: what the
# host configured, and the provider's own handle for the call.
MODEL = "a-model/for-the-test"
GENERATION = "gen-for-the-test"

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"
ARTIFACT = "e" * 64
CHARGE = Decimal("0.01")


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return loaded


@pytest.fixture
def client(
    case: tuple[StoreConnection, UUID],
    empty_database: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """The app served against the test's own database and blob root.

    `CAOS_DATABASE_URL` is set because startup reads it: entering the client runs
    the real lifespan, so every test here also proves the process can boot. The
    per-request connection is then overridden onto the fixture's own, which is
    the one holding the case these tests set up.
    """
    conn, _case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)
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


@pytest.mark.parametrize(
    "database_url",
    [None, "postgresql://caos@127.0.0.1:1/caos?connect_timeout=2"],
    ids=["unconfigured", "unreachable"],
)
def test_an_anonymous_request_is_401_whatever_the_store_is_doing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, database_url: str | None
) -> None:
    """The answer to a stranger does not depend on the database being up.

    Identity checked in the route body is identity checked after FastAPI has
    already resolved `Store`, so a process that had lost its database answered
    a caller whose actual problem was that it had not said who it was with a
    refusal about the store. Both shapes of that refusal are asked for, because
    they are separate codes and either would do as the wrong answer: the store
    unconfigured is STORE_NOT_CONFIGURED, the store not answering is
    STORE_UNAVAILABLE, and 503 tells a caller to come back later when no amount
    of later will help them.
    """
    app.dependency_overrides.pop(store_connection)
    if database_url is None:
        monkeypatch.delenv(app_module.DATABASE_URL, raising=False)
    else:
        monkeypatch.setenv(app_module.DATABASE_URL, database_url)

    for path in (f"/api/runs/{uuid4()}", f"/api/runs/{uuid4()}/events"):
        response = client.get(path)

        assert (response.status_code, response.json()) == (
            401,
            {"refusal": "NOT_AUTHENTICATED"},
        ), path


def test_an_anonymous_request_opens_no_store_connection(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """`actor_from_request` is declared before `Store`, and FastAPI solves a
    route's dependencies in the order its parameters declare them.

    The connection is one per request and unpooled, so a stranger asking in a
    loop for a connection opened before identity is known is a cheap way to
    exhaust the database. The run here exists and is somebody's, so a 401 alone
    would not say where the refusal came from -- the count is what does. It is
    the dependency's own call that is counted rather than the queries it then
    serves, because opening the connection is the cost.
    """
    conn, _case_id = case
    run_id, _viewer = run
    opened: list[str] = []

    def counted() -> StoreConnection:
        opened.append(store_connection.__name__)
        return conn

    app.dependency_overrides[store_connection] = counted

    for path in (f"/api/runs/{run_id}", f"/api/runs/{run_id}/events"):
        assert client.get(path).status_code == 401, path
    assert opened == [], (
        "an anonymous request resolved the store dependency; identity is "
        "declared before it so that it does not"
    )


def test_store_connection_refuses_without_a_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dependency the test client overrides in every other test. A
    deployment missing `CAOS_DATABASE_URL` should fail this way, not with a
    connection error from whatever `connect(None)` happens to do."""
    monkeypatch.delenv("CAOS_DATABASE_URL", raising=False)

    with pytest.raises(Refusal) as caught:
        next(store_connection())

    # Not STORE_NOT_TRANSACTIONAL, which it used to be: that code names an
    # autocommit connection, and a reader chasing it would look for the wrong
    # misconfiguration.
    assert caught.value.code is RefusalCode.STORE_NOT_CONFIGURED


def test_store_connection_opens_a_real_connection_from_the_environment(
    empty_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The success path the override in every other test bypasses entirely.
    Advanced twice, the way FastAPI itself drives a dependency generator: once
    for the connection, once past the `yield` to run the `with` block's exit."""
    monkeypatch.setenv("CAOS_DATABASE_URL", empty_database)

    generator = store_connection()
    conn = next(generator)

    assert conn.execute("SELECT 1").fetchone() == (1,)
    with pytest.raises(StopIteration):
        next(generator)


def test_blob_store_refuses_without_a_blob_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAOS_BLOB_ROOT", raising=False)

    with pytest.raises(Refusal) as caught:
        blob_store()

    assert caught.value.code is RefusalCode.STORE_NOT_CONFIGURED


def test_a_misconfigured_store_is_a_server_fault_not_a_bad_request(
    case: tuple[StoreConnection, UUID],
    empty_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the blob root unset every run read failed 400 BLOB_NOT_FOUND --
    telling the client its request was bad, and answering an unknown run with
    something other than the 404 a stranger always gets. A store the process
    cannot reach is the server's fault, the same for every caller."""
    conn, _case_id = case
    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)
    monkeypatch.delenv("CAOS_BLOB_ROOT", raising=False)
    app.dependency_overrides[store_connection] = lambda: conn
    try:
        with TestClient(app) as opened:
            response = opened.get(f"/api/runs/{uuid4()}", headers=_as(uuid4()))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"refusal": "STORE_NOT_CONFIGURED"}


def test_a_store_that_does_not_answer_is_a_server_fault(
    empty_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured store that does not answer -- the commonest store fault --
    reached every caller as a bare 500, and the server's log as psycopg's
    message naming the host, port and role. It is refused like any other store
    fault: 503, and the code alone, with nothing chained behind it.

    Both callers are named. A caller with no identity never reaches the store
    at all, and gets 401 --
    `test_an_anonymous_request_is_401_whatever_the_store_is_doing` is where that
    is asserted. What this keeps from the arm that used to be anonymous is the
    tail route, which is the half of it that was about the route rather than
    about the caller.
    """
    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)
    monkeypatch.setenv(app_module.BLOB_ROOT, str(tmp_path))
    with TestClient(app) as opened:
        monkeypatch.setenv(
            app_module.DATABASE_URL,
            "postgresql://caos@127.0.0.1:1/caos?connect_timeout=2",
        )
        document = opened.get(f"/api/runs/{uuid4()}", headers=_as(uuid4()))
        tail = opened.get(f"/api/runs/{uuid4()}/events", headers=_as(uuid4()))

    for response in (document, tail):
        assert (response.status_code, response.json()) == (
            503,
            {"refusal": "STORE_UNAVAILABLE"},
        )
    with pytest.raises(Refusal) as caught:
        next(store_connection())
    assert caught.value.code == "STORE_UNAVAILABLE"
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_only_a_run_id_that_cannot_be_read_is_answered_as_a_missing_run() -> None:
    """Registered for the whole app, the handler answered every malformed path
    parameter as a missing run, so the first route to take a case id would have
    said RUN_NOT_FOUND about it. Any other path keeps FastAPI's default until
    its route says what it should get."""
    other = FastAPI()
    other.add_exception_handler(
        RequestValidationError, app.exception_handlers[RequestValidationError]
    )

    @other.get("/api/cases/{case_id}")
    def read_case(case_id: UUID) -> str:
        return str(case_id)

    assert TestClient(other).get("/api/cases/not-a-case").status_code == 422


def test_the_malformed_id_handler_derives_identity_of_its_own() -> None:
    """The handler answers a caller with no identity itself, and this app's
    routes no longer let it: `actor_from_request` refuses an anonymous caller
    before FastAPI validates the path, so the anonymous arm of
    `test_a_malformed_run_id_is_answered_like_any_unknown_run` now passes
    through the dependency rather than through here.

    The contract belongs to the handler and not to the route, so it is asserted
    against a route that does not carry the dependency -- which is what the
    first route to take a run id and forget it would be. Without this the two
    lines that answer it are reachable from no test at all.
    """
    other = FastAPI()
    other.add_exception_handler(
        RequestValidationError, app.exception_handlers[RequestValidationError]
    )

    @other.get("/api/runs/{run_id}")
    def read_run_without_identity(run_id: UUID) -> str:
        return str(run_id)

    response = TestClient(other).get("/api/runs/not-a-run")

    assert (response.status_code, response.json()) == (
        401,
        {"refusal": "NOT_AUTHENTICATED"},
    )


def test_a_malformed_run_id_is_answered_like_any_unknown_run(
    client: TestClient, run: tuple[UUID, UUID]
) -> None:
    """A path that cannot name a run names no run. FastAPI's own 422 answered
    it instead -- before identity, in a body that is not the declared refusal
    and that quotes the input back.

    The anonymous arm is now answered by `actor_from_request`, which resolves
    before FastAPI validates the path; the handler's own answer to it is the
    same, and is asserted directly in
    `test_the_malformed_id_handler_derives_identity_of_its_own`."""
    _run_id, viewer = run
    unknown = client.get(f"/api/runs/{uuid4()}", headers=_as(viewer))

    for path in ("/api/runs/not-a-run", "/api/runs/not-a-run/events"):
        named = client.get(path, headers=_as(viewer))
        anonymous = client.get(path)

        assert (named.status_code, named.json()) == (404, unknown.json())
        assert (anonymous.status_code, anonymous.json()) == (
            401,
            {"refusal": "NOT_AUTHENTICATED"},
        )


def test_blob_store_is_rooted_at_the_environment_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAOS_BLOB_ROOT", str(tmp_path))

    store = blob_store()

    assert store.root == tmp_path


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
    # No CP-0 artifact is accepted in this run, so the gate has not spoken for
    # any module -- `gate_verdict` is the absence of a verdict, not a state
    # this test happens not to exercise.
    assert by_module["CP-1"]["gate_verdict"] is None


def _accept_gate(
    conn: StoreConnection,
    run_id: UUID,
    route: ResolvedRoute,
    tmp_path: Path,
    verdicts: object,
) -> None:
    """Accept a CP-0 artifact whose readiness map is `verdicts`. The blob store
    is on the same root the `client` fixture points the app's injected one at --
    not a second store, but the one the request is about to read from."""
    cp0 = next(node.route_node_id for node in route.nodes if node.module_id == "CP-0")
    digest = BlobStore(tmp_path / "blobs").put(
        json.dumps({"content_to_module_map": verdicts}).encode("utf-8")
    )
    accept_attempt(
        conn,
        attempt_id=start_attempt(conn, run_id, cp0),
        accepted=Accepted(
            artifact_sha256=digest, charge=CHARGE, model=MODEL, generation_id=GENERATION
        ),
    )


def test_a_node_the_gate_blocked_says_so_on_the_run_surface(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Phase 6 asked for "node states with their reasons", and after Phase 11 a
    node can be BLOCKED by the gate rather than by an edge. `waiting_on` cannot
    carry that cause -- there is no edge to name -- so the verdict travels
    beside it, or the surface reports a state with no reason at all."""
    conn, _case_id = case
    run_id, viewer = run
    route = resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW")
    pin_route(conn, run_id, route)
    _accept_gate(
        conn,
        run_id,
        route,
        tmp_path,
        [
            {"module_id": "CP-1", "readiness_status": "BLOCKED"},
            {"module_id": "CP-2", "readiness_status": "READY"},
            {"module_id": "CP-2D", "readiness_status": "READY"},
        ],
    )

    body = client.get(f"/api/runs/{run_id}", headers=_as(viewer)).json()

    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert by_module["CP-1"]["state"] == "BLOCKED"
    assert by_module["CP-1"]["waiting_on"] == []
    assert by_module["CP-1"]["gate_verdict"] == "BLOCKED"
    assert by_module["CP-2"]["gate_verdict"] == "READY"


def test_a_stored_gate_map_the_host_cannot_bound_is_a_server_fault(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
    tmp_path: Path,
) -> None:
    """`READINESS_INVALID` became reachable here in Phase 11: the verdict is read
    out of an artifact this server wrote, so a map it cannot bound is the
    server's own fault. Absent from `_STATUS` it answered 400 -- telling the
    caller their request was the problem, about bytes they do not hold."""
    conn, _case_id = case
    run_id, viewer = run
    route = resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW")
    pin_route(conn, run_id, route)
    _accept_gate(conn, run_id, route, tmp_path, "READY")

    response = client.get(f"/api/runs/{run_id}", headers=_as(viewer))

    assert (response.status_code, response.json()) == (
        503,
        {"refusal": "READINESS_INVALID"},
    )


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
        "gate_verdict",
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

    assert declared == {
        "/api/runs/{run_id}": read_run.__name__,
        "/api/runs/{run_id}/events": read_run_events.__name__,
    }


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


def test_the_tail_is_served_as_an_event_stream(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """The transport half of `server/api/stream.py`: the same contract, now over
    a socket."""
    conn, _case_id = case
    run_id, viewer = run
    _finish(conn, run_id)

    response = client.get(f"/api/runs/{run_id}/events", headers=_as(viewer))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"
    assert [name for _, name in _sse(response.text)] == [
        "ATTEMPT_STARTED",
        "ATTEMPT_ACCEPTED",
        "RUN_COMPLETE",
    ]


def test_every_frame_carries_an_id_and_a_name_and_no_state(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """The client never reads a payload -- a name triggers a refetch. A payload
    on the wire would be a second copy of state the client is about to fetch
    properly, and the first thing to go stale."""
    conn, _case_id = case
    run_id, viewer = run
    _finish(conn, run_id)

    text = client.get(f"/api/runs/{run_id}/events", headers=_as(viewer)).text

    assert [line for line in text.splitlines() if line.startswith("data:")] == [
        "data: {}"
    ] * 3
    assert [event_id for event_id, _ in _sse(text)] == ["1", "2", "3"]


def test_last_event_id_resumes_after_the_marker(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """`Last-Event-ID` is the last event the client actually received, so
    delivery starts strictly after it. Re-delivering it would make a client that
    refetches on every name do the work twice."""
    conn, _case_id = case
    run_id, viewer = run
    _finish(conn, run_id)

    text = client.get(
        f"/api/runs/{run_id}/events", headers={**_as(viewer), "last-event-id": "2"}
    ).text

    assert [name for _, name in _sse(text)] == ["RUN_COMPLETE"]


def test_a_last_event_id_that_is_not_a_number_starts_from_the_beginning(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """A resume marker is a browser-supplied string. Refusing the connection
    would strand a client that can only fix it by clearing storage; starting
    over re-delivers, which is what the contract already tolerates."""
    conn, _case_id = case
    run_id, viewer = run
    _finish(conn, run_id)

    text = client.get(
        f"/api/runs/{run_id}/events",
        headers={**_as(viewer), "last-event-id": "; DROP TABLE runs"},
    ).text

    assert len(_sse(text)) == 3


def test_an_unauthorised_tail_is_the_same_private_404(
    client: TestClient, run: tuple[UUID, UUID]
) -> None:
    """The stream cannot be the one surface that answers differently. An empty
    200 would still say the id is a well-formed run somebody could watch."""
    run_id, _viewer = run

    response = client.get(f"/api/runs/{run_id}/events", headers=_as(uuid4()))

    assert response.status_code == 404
    assert response.json() == {"refusal": "RUN_NOT_FOUND"}


def test_the_tail_closes_at_its_deadline(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§9 wants a tail that closes so the edge can reauthenticate. This run never
    goes terminal, so the deadline is the only thing that ends the stream --
    without it this test does not fail, it hangs."""
    conn, _case_id = case
    run_id, viewer = run
    start_attempt(conn, run_id, "CP-1")
    conn.commit()
    monkeypatch.setattr(app_module, "TAIL_DEADLINE", 0.0)

    text = client.get(f"/api/runs/{run_id}/events", headers=_as(viewer)).text

    assert [name for _, name in _sse(text)] == ["ATTEMPT_STARTED"]
    assert TAIL_DEADLINE == 300.0, "five minutes is the shipped value"


def test_a_watcher_revoked_mid_stream_closes_rather_than_idling(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An SSE connection is exactly the thing that stays open across a
    revocation. The tail goes quiet for a revoked reader and for a caught-up one
    alike, so the loop asks directly -- otherwise a revoked reader's socket stays
    alive until the deadline.

    Standing is taken away by making the route's own read say so from the second
    call on: the first is the request's own check, the second is the poll.
    """
    conn, _case_id = case
    run_id, viewer = run
    start_attempt(conn, run_id, "CP-1")
    conn.commit()
    answers = iter([True])

    def revoked_after_the_request(
        conn: StoreConnection, *, case_id: UUID, user_id: UUID
    ) -> Standing | None:
        if next(answers, False):
            return standing_of(conn, case_id=case_id, user_id=user_id)
        return None

    monkeypatch.setattr(app_module, "standing_of", revoked_after_the_request)

    text = client.get(f"/api/runs/{run_id}/events", headers=_as(viewer)).text

    assert [name for _, name in _sse(text)] == ["ATTEMPT_STARTED"]


def test_the_idle_loop_actually_waits_between_polls(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The genuinely idle pass: no new event, standing still holds, the
    deadline has not yet passed. `test_the_tail_closes_at_its_deadline` and
    `test_a_watcher_revoked_mid_stream_closes_rather_than_idling` each engineer
    an exit on the very first pass and never reach the wait between them --
    without it, an idle connection would ask again as fast as the loop could
    spin rather than once per `POLL_INTERVAL`."""
    conn, _case_id = case
    run_id, viewer = run
    start_attempt(conn, run_id, "CP-1")
    conn.commit()
    monkeypatch.setattr(app_module, "POLL_INTERVAL", 0.01)
    monkeypatch.setattr(app_module, "TAIL_DEADLINE", 0.03)

    text = client.get(f"/api/runs/{run_id}/events", headers=_as(viewer)).text

    assert [name for _, name in _sse(text)] == ["ATTEMPT_STARTED"]


def test_a_process_with_no_database_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail at boot, not at the first request. A process that started without a
    database would answer every request with a 500 that reads like a bug in the
    route rather than a deployment pointed at nothing."""
    monkeypatch.delenv(app_module.DATABASE_URL, raising=False)

    with pytest.raises(Refusal) as caught, TestClient(app):
        pass  # pragma: no cover -- entering the client is what raises

    assert caught.value.code is RefusalCode.STORE_NOT_CONFIGURED


def test_startup_applies_the_declared_schema(
    empty_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "Postgres schema in full at startup". The database here has had nothing
    applied to it, and after the app has started it holds the store's tables."""
    from server.store import connect

    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)

    with TestClient(app):
        pass

    with connect(empty_database) as conn:
        applied = conn.execute(
            "SELECT count(*) FROM information_schema.tables"
            " WHERE table_schema = 'public' AND table_name IN"
            " ('runs', 'run_events', 'case_members', 'audit_events')"
        ).fetchone()
    assert applied is not None
    assert applied[0] == 4


def _finish(conn: StoreConnection, run_id: UUID) -> None:
    """Three events: started, accepted, complete."""
    attempt_id = start_attempt(conn, run_id, "CP-1")
    complete_attempt(
        conn,
        attempt_id=attempt_id,
        accepted=Accepted(
            artifact_sha256=ARTIFACT,
            charge=CHARGE,
            model=MODEL,
            generation_id=GENERATION,
        ),
    )
    conn.commit()


def _sse(text: str) -> list[tuple[str, str]]:
    """Each frame's id and event name, in order."""
    frames = []
    for block in text.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1) for line in block.splitlines() if ": " in line
        )
        frames.append((fields["id"], fields["event"]))
    return frames


class _CountingConnection:
    """Counts store round trips, so the declared budget is measured."""

    def __init__(self, conn: StoreConnection) -> None:
        self._conn = conn
        self.executed = 0

    def execute(self, *args: object, **kwargs: object) -> object:
        self.executed += 1
        return self._conn.execute(*args, **kwargs)  # type: ignore[arg-type]
