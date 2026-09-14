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
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from canonical_fixtures import CanonicalCompletions
from conftest import route_fault
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import BaseModel
from test_canonical_execution import _accept, _node, _run, harness, route
from test_execution_freshness import _Harness

from server.api import app as app_module
from server.api.app import (
    app,
    blob_store,
    methodology_bundle,
    read_case_events,
    store_connection,
)
from server.api.deps import actor_from_request
from server.api.reads import analysis as analysis_read
from server.api.reads import directory as directory_read
from server.api.reads import model as model_read
from server.api.reads import reports as reports_read
from server.api.reads import run as run_read
from server.api.reads import upload as upload_read
from server.api.reads.run import _node_view, read_run_section
from server.api.wire import CLEARS, EdgeView, NodeView, RefusalBody, RunSectionDocument
from server.blobs import BlobStore
from server.engine.route import (
    EdgeType,
    NodeResult,
    node_states,
    readiness_from,
    resolve_route,
)
from server.methodology.bundle import Bundle
from server.methodology.handoff import _decoded_record, record_bytes
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.members import Standing, grant, revoke
from server.store.routes import pin_route, pinned_route
from server.store.runs import block_run, start_run

__all__ = ["harness", "route"]

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"
# Every run that accepts an artifact here is a canonical LITE run (§42): its
# gate verdicts are read from CP-0's host record, never from a claims body.
LITE = ("LITE_CREDIT_22", "LITE_EARNINGS_UPDATE")


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
    _serve(conn, blobs)
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


@pytest.fixture
def lite(harness: _Harness, client: TestClient) -> tuple[_Harness, UUID]:
    """An approved canonical LITE run on the client's store, and a READER of it.

    The harness shares the `case` connection and the `tmp_path / "blobs"` root
    the client serves, and its bundle is the one records are verified under.
    """
    _serve(bundle=harness.bundle)
    viewer = uuid4()
    grant(
        harness.conn, case_id=harness.case_id, user_id=viewer, standing=Standing.READER
    )
    harness.conn.commit()
    return harness, viewer


def _answer(
    harness: _Harness, module_id: str, readiness: dict[str, str] | None = None
) -> None:
    """One node called through the canonical executor and accepted with its
    record; the run stays RUNNING."""
    answers = CanonicalCompletions(harness.source_id, readiness=readiness or {})
    attempt, result = _run(harness, module_id, answers)
    _accept(harness, attempt, result)


def _serve(
    conn: StoreConnection | None = None,
    blobs: BlobStore | None = None,
    bundle: Bundle | None = None,
) -> None:
    """Override the app's shared dependencies: every section read declares the
    same `server.api.deps` functions, so overriding them here reaches every
    route that depends on one, section reads included."""
    pairs = (
        (conn, store_connection),
        (blobs, blob_store),
        (bundle, methodology_bundle),
    )
    for value, dependency in pairs:
        if value is not None:
            # A closure, not a default argument: FastAPI reads an override's
            # parameters as request inputs and copies their defaults.
            app.dependency_overrides[dependency] = _constant(value)


def _constant(value: object) -> Callable[[], object]:
    return lambda: value


def _section(
    client: TestClient, case_id: UUID, run_id: UUID | None, user: UUID | None
) -> Response:
    """The Run section for `run_id` (or the latest run) as `user` would ask."""
    query = "" if run_id is None else f"?run={run_id}"
    headers = {} if user is None else _as(user)
    response: Response = client.get(
        f"/api/v1/cases/{case_id}/run{query}", headers=headers
    )
    return response


def _view(response: Response) -> dict[str, Any]:
    """The displayed run of a Run section that validated as its model."""
    assert response.status_code == 200, response.json()
    document = RunSectionDocument.model_validate(response.json())
    assert document.body.run is not None
    view: dict[str, Any] = document.body.run.model_dump(mode="json")
    return view


def _refused(code: str) -> dict[str, str]:
    """The one refusal body: the code and its host-constant clearance."""
    return {"code": code, "clears": CLEARS[RefusalCode(code)]}


def _as(user_id: UUID) -> dict[str, str]:
    """Headers for an authenticated caller with no asserted groups."""
    return {"x-caos-user": str(user_id)}


def test_unauthorised_case_is_private_404(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """A named test.

    A stranger asking about somebody else's run gets the answer they would get
    for a run that does not exist. 403 is the informative answer and that is the
    problem with it: it confirms the id names something real, which for a case
    id is the fact worth protecting.
    """
    _conn, case_id = case
    run_id, _viewer = run
    stranger = uuid4()

    response = _section(client, case_id, run_id, stranger)
    unknown = _section(client, uuid4(), run_id, stranger)

    assert response.status_code == unknown.status_code == 404
    assert response.json() == unknown.json() == _refused("CASE_NOT_FOUND")


def test_an_unknown_run_is_the_same_404(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """The other half of the pair. The two answers have to be identical, or the
    difference between them is the disclosure."""
    _run_id, viewer = run
    response = _section(client, case[1], uuid4(), viewer)

    assert response.status_code == 404
    assert response.json() == _refused("RUN_NOT_FOUND")


def test_a_revoked_reader_stops_being_able_to_read_it(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """Standing is read at the request, not cached in a session."""
    conn, case_id = case
    run_id, viewer = run
    assert _section(client, case_id, run_id, viewer).status_code == 200

    revoke(conn, case_id=case_id, user_id=viewer)
    conn.commit()

    assert _section(client, case_id, run_id, viewer).status_code == 404


def test_a_request_with_no_identity_is_401_not_404(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """Unauthenticated and unauthorised are different questions. "I do not know
    who you are" discloses nothing about the run, so it can be said plainly --
    and a client that got a 404 would retry the wrong thing forever."""
    run_id, _viewer = run

    response = _section(client, case[1], run_id, None)

    assert response.status_code == 401
    assert response.json() == _refused("NOT_AUTHENTICATED")


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

    for path in (f"/api/v1/cases/{uuid4()}/run", f"/api/v1/cases/{uuid4()}/events"):
        response = client.get(path)

        assert (response.status_code, response.json()) == (
            401,
            _refused("NOT_AUTHENTICATED"),
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
    conn, case_id = case
    run_id, _viewer = run
    opened: list[str] = []

    def counted() -> StoreConnection:
        opened.append(store_connection.__name__)
        return conn

    def counted_bundle() -> Bundle:
        opened.append(methodology_bundle.__name__)
        raise AssertionError  # never reached before identity

    app.dependency_overrides[store_connection] = counted
    app.dependency_overrides[methodology_bundle] = counted_bundle

    for path in (
        f"/api/v1/cases/{case_id}/run",
        f"/api/v1/cases/{case_id}/events?run={run_id}",
    ):
        assert client.get(path).status_code == 401, path
    del app.dependency_overrides[methodology_bundle]
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
    _serve(conn)
    try:
        with TestClient(app) as opened:
            response = _section(opened, uuid4(), None, uuid4())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == _refused("STORE_NOT_CONFIGURED")


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
        document = _section(opened, uuid4(), None, uuid4())
        tail = opened.get(f"/api/v1/cases/{uuid4()}/events", headers=_as(uuid4()))

    for response in (document, tail):
        assert (response.status_code, response.json()) == (
            503,
            _refused("STORE_UNAVAILABLE"),
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
        _refused("NOT_AUTHENTICATED"),
    )


def test_blob_store_is_rooted_at_the_environment_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAOS_BLOB_ROOT", str(tmp_path))

    store = blob_store()

    assert store.root == tmp_path


def test_a_node_the_gate_blocked_says_so_on_the_run_surface(
    client: TestClient, lite: tuple[_Harness, UUID]
) -> None:
    """Phase 6 asked for "node states with their reasons", and after Phase 11 a
    node can be BLOCKED by the gate rather than by an edge. `waiting_on` cannot
    carry that cause -- there is no edge to name -- so the verdict travels
    beside it, read from CP-0's canonical T8 readiness, or the surface reports a
    state with no reason at all."""
    harness, viewer = lite
    _answer(harness, "CP-0", readiness={"CP-L10": "BLOCKED"})

    body = _view(_section(client, harness.case_id, harness.run_id, viewer))

    assert body["status"] == "RUNNING"
    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert by_module["CP-0"]["state"] == "COMPLETE"
    assert by_module["CP-L10"]["state"] == "BLOCKED"
    assert by_module["CP-L10"]["waiting_on"] == []
    assert by_module["CP-L10"]["gate_verdict"] == "BLOCKED"
    assert by_module["CP-5"]["gate_verdict"] == "READY"


def test_a_stored_gate_record_the_markdown_does_not_bind_is_a_server_fault(
    client: TestClient, lite: tuple[_Harness, UUID]
) -> None:
    """The verdict is read out of a record this server wrote, so readiness the
    Markdown does not say is the server's own fault. A 400 would tell the caller
    their request was the problem, about bytes they do not hold."""
    harness, viewer = lite
    _answer(harness, "CP-0")
    attempt, record = _gate_record(harness)
    stored = _decoded_record(harness.blobs.get(record))
    lying = replace(
        stored,
        projections=replace(stored.projections, readiness=(("CP-5", "READY"),)),
    )
    harness.conn.execute(
        "UPDATE artifacts SET record_sha256 = %s WHERE attempt_id = %s",
        (harness.blobs.put(record_bytes(lying)), attempt),
    )
    harness.conn.commit()

    response = _section(client, harness.case_id, harness.run_id, viewer)

    assert (response.status_code, response.json()) == (
        503,
        _refused("ARTIFACT_RECORD_MISMATCH"),
    )


def _gate_record(harness: _Harness) -> tuple[UUID, str]:
    row = harness.conn.execute(
        "SELECT attempt_id, record_sha256 FROM artifacts WHERE route_node_id = %s",
        (_node(harness, "CP-0").route_node_id,),
    ).fetchone()
    harness.conn.rollback()
    assert row is not None and row[1] is not None
    return UUID(str(row[0])), str(row[1])


def test_the_one_qa_gate_reads_as_a_gate(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    """The catalog holds exactly one QA_GATE edge, `CP-5 -> CP-6`. A node held by
    it waits for the QA verdict; every other BLOCKED node is waiting for a
    module, and a surface that rendered both the same way would hide it."""
    conn, case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT"))

    body = _view(_section(client, case_id, run_id, viewer))

    by_module = {node["module_id"]: node for node in body["nodes"]}
    assert by_module["CP-6"]["awaiting_gate"] is True
    assert by_module["CP-1"]["awaiting_gate"] is False
    assert sum(node["awaiting_gate"] for node in body["nodes"]) == 1


@pytest.mark.parametrize(
    ("qa_status", "held"), [("Blocked", True), ("Restricted", True), ("Passed", False)]
)
def test_a_qa_verdict_other_than_passed_blocks_without_awaiting(
    catalog: dict[str, Any], qa_status: str, held: bool
) -> None:
    """F03: CP-5 answered something other than `Passed`, so CP-6 is blocked by
    that verdict and nothing is awaited -- not a wait for a person.

    The one QA_GATE is on a route the canonical adapter does not yet execute
    (§42.2), so the view is asked directly over the typed result the reader
    reduces any accepted record to; `test_canonical_readers` serves a record's
    readiness over HTTP.
    """
    full = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    cp5 = next(n.route_node_id for n in full.nodes if n.module_id == "CP-5")
    accepted = {cp5: NodeResult(qa_status=qa_status)}
    states = node_states(full, accepted)
    readiness = readiness_from(full, accepted)

    by_module = {
        node.module_id: _node_view(full, accepted, node, states, readiness)
        for node in full.nodes
    }

    cp6 = by_module["CP-6"]
    assert (cp6.state, cp6.awaiting_gate) == ("BLOCKED", False)
    gate = EdgeView(source="CP-5", type=EdgeType.QA_GATE)
    assert (gate in cp6.waiting_on) is held
    assert by_module["CP-5"].waiting_on == []


def test_nothing_is_awaited_on_a_run_that_is_no_longer_running(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    conn, case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT"))
    block_run(conn, run_id)

    body = _view(_section(client, case_id, run_id, viewer))

    assert body["status"] == "BLOCKED"
    assert not any(node["awaiting_gate"] for node in body["nodes"])


@pytest.mark.parametrize("which", [0, 1], ids=["markdown", "record"])
def test_an_unreadable_gate_artifact_is_a_typed_server_fault(
    client: TestClient, lite: tuple[_Harness, UUID], which: int
) -> None:
    harness, viewer = lite
    _answer(harness, "CP-0")
    row = harness.conn.execute(
        "SELECT artifact_sha256, record_sha256 FROM artifacts WHERE run_id = %s",
        (harness.run_id,),
    ).fetchone()
    harness.conn.rollback()
    assert row is not None
    path = harness.blobs.path_of(str(row[which]))
    path.chmod(0o644)
    path.write_bytes(b"not a handoff")

    response = _section(client, harness.case_id, harness.run_id, viewer)

    assert (response.status_code, response.json()) == (
        503,
        _refused("ARTIFACT_RECORD_MISMATCH"),
    )


def test_the_run_document_refuses_an_undeclared_field(
    client: TestClient, case: tuple[StoreConnection, UUID], run: tuple[UUID, UUID]
) -> None:
    """§9's closed shape, on the way out as well as in. A response model that
    let an extra key through would let a store column reach a browser because
    somebody widened a SELECT."""
    run_id, viewer = run
    body = _section(client, case[1], run_id, viewer).json()

    assert set(body) == set(RunSectionDocument.model_fields)
    with pytest.raises(ValueError, match="extra_forbidden"):
        RunSectionDocument.model_validate({**body, "budget_ceiling": "40.00"})
    widened = {**body["body"]["run"], "budget_ceiling": "40.00"}
    with pytest.raises(ValueError, match="extra_forbidden"):
        RunSectionDocument.model_validate(
            {**body, "body": {**body["body"], "run": widened}}
        )


@pytest.mark.parametrize("model", [RunSectionDocument, NodeView, EdgeView, RefusalBody])
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
    assert set(NodeView.model_fields) == {
        "route_node_id",
        "module_id",
        "stage",
        "state",
        "waiting_on",
        "awaiting_gate",
        "gate_verdict",
    }
    assert set(EdgeView.model_fields) == {"source", "type"}
    assert set(RefusalBody.model_fields) == {"code", "clears"}


def test_every_refusal_body_is_code_and_clears_and_nothing_else(
    client: TestClient,
) -> None:
    """The typed refusal, on the wire (brief 4.1, decision 3). A body that also
    carried a message would be the one place a document's contents could still
    get out, so `clears` is the host's constant for the code and never text
    from the request, whichever answer the route gave."""
    answers = {
        RefusalCode.RUN_NOT_FOUND: client.get(
            f"/api/v1/cases/{uuid4()}/events?run=not-a-run", headers=_as(uuid4())
        ),
        RefusalCode.CASE_NOT_FOUND: _section(client, uuid4(), None, uuid4()),
        RefusalCode.NOT_AUTHENTICATED: _section(client, uuid4(), None, None),
        RefusalCode.ENDPOINT_NOT_FOUND: client.get("/api/runs-not-declared"),
    }

    for code, response in answers.items():
        body = response.json()
        assert set(body) == {"code", "clears"} == set(RefusalBody.model_fields)
        assert RefusalBody.model_validate(body) == RefusalBody(
            code=code, clears=CLEARS[code]
        )
        assert body["clears"] == CLEARS[code]
    assert RefusalBody.model_config.get("frozen") is True
    with pytest.raises(ValueError, match="extra_forbidden"):
        RefusalBody.model_validate(
            {"code": "RUN_NOT_FOUND", "clears": "x", "refusal": "RUN_NOT_FOUND"}
        )


def test_every_refusal_code_has_a_constant_clearance() -> None:
    """`CLEARS` is total over `RefusalCode`, and each entry is a finished
    sentence: nothing in it could be filled in from a request or a document."""
    assert set(CLEARS) == set(RefusalCode)
    for code in RefusalCode:
        clears = CLEARS[code]
        assert isinstance(clears, str) and clears.strip(), code
        assert "{" not in clears and "}" not in clears and "%" not in clears, code


def test_an_undeclared_api_path_or_method_answers_endpoint_not_found_in_the_refusal_body(  # noqa: E501 -- the brief's name
    client: TestClient,
) -> None:
    """Starlette's own `{"detail": ...}` is a second refusal body, and two
    cannot coexist under `/api/`. An undeclared path is 404 and an undeclared
    method on a declared path is 405, both `ENDPOINT_NOT_FOUND`; nothing
    outside `/api/` is this contract's to answer."""
    missing = client.get("/api/not-declared", headers=_as(uuid4()))
    anonymous = client.get("/api/not-declared")
    wrong_method = client.post(f"/api/v1/cases/{uuid4()}/run", headers=_as(uuid4()))

    for response, status in ((missing, 404), (anonymous, 404), (wrong_method, 405)):
        assert (response.status_code, response.json()) == (
            status,
            _refused("ENDPOINT_NOT_FOUND"),
        )
    assert client.get("/not-api").json() == {"detail": "Not Found"}


def test_the_surface_is_exactly_the_routes_it_declares(
    client: TestClient,
) -> None:
    """A route added without a test is a request path nobody agreed to. Listing
    them here means a new one has to be written down before it can ship."""
    # A section's router is included as a whole, so its routes sit one level
    # down in the app's list.
    routes = [
        inner
        for route in app.routes
        for inner in getattr(getattr(route, "original_router", None), "routes", [route])
    ]
    declared = {
        route.path: route.endpoint.__name__
        for route in routes
        if isinstance(route, APIRoute)
    }

    assert declared == {
        "/api/v1/directory": "read_directory",
        "/api/v1/cases/{case_id}/upload": "read_upload",
        "/api/v1/cases/{case_id}/run": read_run_section.__name__,
        "/api/v1/cases/{case_id}/analysis": "read_analysis",
        "/api/v1/cases/{case_id}/model": "read_model",
        "/api/v1/cases/{case_id}/report": "read_report",
        "/api/v1/cases/{case_id}/committee": "read_committee",
        "/api/v1/cases/{case_id}/runs/{run_id}/sources/{source_id}/pages/{page}": (
            "read_evidence_page"
        ),
        "/api/v1/cases/{case_id}/events": read_case_events.__name__,
        "/api/health": "read_health",
        "/api/v1/cases/{case_id}/runs/{run_id}/start": "start_run",
        "/api/v1/cases/{case_id}/runs/{run_id}/retry": "retry_run",
        "/api/v1/cases/{case_id}/runs/{run_id}/cancel": "cancel_run",
        "/api/v1/cases": "create_case_command",
        "/api/v1/cases/{case_id}/sources": "admit_sources",
        "/api/v1/cases/{case_id}/runs": "create_run",
        "/api/v1/cases/{case_id}/runs/{run_id}/input": "pin_input",
        "/api/v1/cases/{case_id}/runs/{run_id}/gates/{gate}/preview": (
            "read_gate_preview"
        ),
        "/api/v1/cases/{case_id}/runs/{run_id}/gates/{gate}/approval": "approve",
    }


def test_every_section_read_depends_on_the_shared_dependencies() -> None:
    """Each section route calls the `server.api.deps` functions directly, in
    the order identity, then any path/query parser, then the store, blobs and
    bundle -- never a per-module wrapper that resolves them lazily.

    A dependency's own path parser (`case_path`, `run_query`) stays: those are
    parameter parsers, not copies of `app.py`'s dependencies, so they are
    named here rather than in `server.api.deps`.
    """
    routes = {
        route.path: route
        for router in (
            directory_read,
            upload_read,
            run_read,
            analysis_read,
            model_read,
            reports_read,
        )
        for route in router.router.routes
        if isinstance(route, APIRoute)
    }
    calls = {
        path: [d.call for d in route.dependant.dependencies]
        for path, route in routes.items()
    }
    assert calls["/api/v1/directory"] == [actor_from_request, store_connection]
    assert calls["/api/v1/cases/{case_id}/upload"] == [
        actor_from_request,
        upload_read.case_path,
        store_connection,
    ]
    assert calls["/api/v1/cases/{case_id}/run"] == [
        actor_from_request,
        store_connection,
        blob_store,
        methodology_bundle,
    ]
    events = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/v1/cases/{case_id}/events"
    )
    assert [d.call for d in events.dependant.dependencies] == [
        actor_from_request,
        upload_read.case_path,
        analysis_read.run_query,
        store_connection,
    ]
    assert calls["/api/v1/cases/{case_id}/analysis"] == [
        actor_from_request,
        upload_read.case_path,
        analysis_read.run_query,
        store_connection,
        blob_store,
        methodology_bundle,
    ]
    assert (
        calls["/api/v1/cases/{case_id}/model"]
        == calls["/api/v1/cases/{case_id}/analysis"]
    )
    report_dependencies = [
        actor_from_request,
        upload_read.case_path,
        analysis_read.run_query,
        reports_read.revision_query,
        store_connection,
        blob_store,
        methodology_bundle,
    ]
    assert calls["/api/v1/cases/{case_id}/report"] == report_dependencies
    assert calls["/api/v1/cases/{case_id}/committee"] == report_dependencies


def test_the_reported_digest_is_the_one_that_was_pinned(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    """The document recomputes the digest from the route it read back. That is
    only sound while it still equals the digest execution reads."""
    conn, case_id = case
    run_id, viewer = run
    pinned = pin_route(
        conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    )

    body = _view(_section(client, case_id, run_id, viewer))

    assert body["route_digest"] == pinned == pinned_route(conn, run_id)


def test_corrupt_route_is_a_sanitized_store_failure(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    run: tuple[UUID, UUID],
    catalog: dict[str, Any],
) -> None:
    conn, case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW"))
    with route_fault(conn):
        conn.execute("UPDATE run_routes SET route_digest = 'synthetic-corruption'")
    conn.commit()
    response = _section(client, case_id, run_id, viewer)
    assert response.status_code == 503
    assert response.json() == _refused("ROUTE_IDENTITY_INVALID")


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
    conn, case_id = case
    run_id, viewer = run
    pin_route(conn, run_id, resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT"))
    counter = _CountingConnection(conn)
    app.dependency_overrides[store_connection] = lambda: counter

    assert _section(client, case_id, run_id, viewer).status_code == 200

    assert counter.executed == run_read.UNPINNED_INPUT_IO <= run_read.IO_BUDGET, (
        "the run document costs what it says it costs; a read that grew with "
        "the size of the route would show up here first"
    )


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


class _CountingConnection:
    """Counts store round trips, so the declared budget is measured."""

    def __init__(self, conn: StoreConnection) -> None:
        self._conn = conn
        self.executed = 0

    def execute(self, *args: object, **kwargs: object) -> object:
        self.executed += 1
        return self._conn.execute(*args, **kwargs)  # type: ignore[arg-type]
