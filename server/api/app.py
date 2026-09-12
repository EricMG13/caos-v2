"""The HTTP surface. Two request paths, and one answer for a stranger.

`SYSTEM_SPEC.md` §9 and `docs/DECISIONS.md` §22. The run document is what
`/run/` will draw in Phase 9: each node's state with the reason for it, and the
one QA_GATE reading as a gate. The events path is the socket
`server/api/stream.py`'s contract is served over -- that module already answers
every rule §9 states, and this is where those answers meet a connection.

The privacy rule is the load-bearing one. A run somebody may not see and a run
that does not exist get the same status and the same body, because 403 is the
informative answer and that is exactly its problem: it confirms the id names
something real. `NOT_AUTHENTICATED` is different in kind -- "I do not know who
you are" discloses nothing about any case -- so it is answered plainly, and a
client that got a 404 for it would retry the wrong thing forever.

Responses are named models with `extra="forbid"` in both directions. A response
shape that let an extra key through is how a store column reaches a browser
because somebody widened a SELECT.

FastAPI's own `/docs` and `/openapi.json` are left served. They describe route
shapes and disclose no case, and the proxy in front of this process
authenticates every path it forwards -- so they are not a public surface. The
privacy rule above is about an authenticated stranger, which is a different
person from an anonymous one.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from json import dumps
from os import environ
from pathlib import Path
from time import monotonic, sleep
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from psycopg import OperationalError
from pydantic import BaseModel, ConfigDict

from server.api.identity import Actor, actor_from_headers
from server.api.stream import IO_BUDGET as TAIL_IO_BUDGET
from server.api.stream import TERMINAL, StreamEvent, tail
from server.blobs import BlobStore
from server.engine.route import (
    EdgeType,
    NodeState,
    ResolvedRoute,
    RouteNode,
    node_states,
    readiness_from,
    route_digest,
    waiting_on,
)
from server.engine.runtime import accepted_artifacts
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, apply_schema, connect
from server.store.members import Standing, satisfies, standing_of
from server.store.routes import resolved_route

# `GET /api/runs/{run_id}`: the run and its case in one row, the caller's
# standing, the pinned route, the accepted attempts. Four, and it does not grow
# with the size of the route -- which is the shape the predecessor got wrong.
IO_BUDGET = 4

# `GET /api/runs/{run_id}/events`: the same two authority reads, then whatever
# the tail costs -- and that again on every poll. Named separately because it is
# a different request path, and a budget that averaged two paths would describe
# neither.
EVENTS_IO_BUDGET = 2 + TAIL_IO_BUDGET

# Reading a run is reading its case. Anything either path shows, a reader of the
# case may see; holding it grants nothing further.
READ_REQUIRES = Standing.READER

# §9: a tail closes so the edge can reauthenticate. Five minutes, and it lives
# here rather than in `stream.py` because it is a property of the connection
# being held open, which is a thing only the route has.
TAIL_DEADLINE = 300.0
# How long the loop waits before asking again. Short enough that a run finishing
# closes the stream promptly, long enough that an idle watcher is not a query a
# second (CLAUDE.md known gaps -- `LISTEN`/`NOTIFY` is the upgrade).
POLL_INTERVAL = 0.5

DATABASE_URL = "CAOS_DATABASE_URL"
BLOB_ROOT = "CAOS_BLOB_ROOT"

# The status for each refusal that can leave a route here. Unauthorised is
# absent on purpose: it is answered as RUN_NOT_FOUND before it can be raised.
# The store's own faults are 503: the server cannot answer, whoever asks, and a
# 400 would tell the caller their request was the problem.
_STATUS = {
    RefusalCode.NOT_AUTHENTICATED: 401,
    RefusalCode.RUN_NOT_FOUND: 404,
    RefusalCode.CASE_NOT_FOUND: 404,
    RefusalCode.STORE_NOT_CONFIGURED: 503,
    RefusalCode.STORE_UNAVAILABLE: 503,
    RefusalCode.STORE_NOT_TRANSACTIONAL: 503,
    RefusalCode.STORE_SCHEMA_DRIFT: 503,
    RefusalCode.BLOB_NOT_FOUND: 503,
    RefusalCode.BLOB_DIGEST_MISMATCH: 503,
    RefusalCode.BLOB_ADDRESS_INVALID: 503,
    # The gate's map is read out of a stored artifact, so a map the host cannot
    # bound is bytes this server wrote -- a store fault like the three above it,
    # and nothing the caller holds could be corrected to avoid it.
    RefusalCode.READINESS_INVALID: 503,
    RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE: 503,
}


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Apply the declared schema before the first request, and refuse to start
    without a database.

    "Postgres schema in full at startup" is the store's rule, and `apply_schema`
    is idempotent -- it applies to an empty database, checks the digest against
    an applied one, and refuses `STORE_SCHEMA_DRIFT` when they disagree. Doing it
    here rather than lazily means a process pointed at the wrong database dies at
    boot instead of serving 500s that look like a bug in the route.
    """
    with connect(_database_url()) as conn:
        apply_schema(conn)
    yield


app = FastAPI(title="CAOS", version="2", lifespan=_lifespan)


class EdgeView(BaseModel):
    """One dependency a node is still waiting for, with its type."""

    model_config = ConfigDict(extra="forbid")

    source: str
    type: EdgeType


class NodeView(BaseModel):
    """A node's state and the reason for it."""

    model_config = ConfigDict(extra="forbid")

    route_node_id: str
    module_id: str
    state: str
    waiting_on: list[EdgeView]
    # The one QA_GATE in the catalog is `CP-5 -> CP-6`. A node held by it is
    # waiting for a person, not a module, and that is the only thing on this
    # page a reviewer can act on -- so it is said, not left to be inferred from
    # an edge type in a list.
    awaiting_gate: bool
    # The gate's own verdict on this module, when the gate has given one. After
    # Phase 11 a node can be BLOCKED because CP-0 did not clear it, and no edge
    # names that cause -- `waiting_on` would be empty and the state would read
    # as unexplained.
    gate_verdict: str | None


class RunDocument(BaseModel):
    """What `/run/` draws. Node states are recomputed, never stored."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    status: str
    route_digest: str | None
    nodes: list[NodeView]


class RefusalBody(BaseModel):
    """Everything a declined request says. The code, and nothing else."""

    model_config = ConfigDict(extra="forbid")

    refusal: RefusalCode


def _database_url() -> str:
    url = environ.get(DATABASE_URL)
    if not url:
        raise Refusal(RefusalCode.STORE_NOT_CONFIGURED)
    return url


def store_connection() -> Iterator[StoreConnection]:
    """One connection per request, from the environment.

    A store that does not answer is refused like any other store fault. The
    refusal is raised outside the `except`, so psycopg's message -- the host,
    the port and the role -- is neither chained behind it nor logged with it.
    """
    conn: StoreConnection | None
    try:
        conn = connect(_database_url())
    except OperationalError:
        conn = None
    if conn is None:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE)
    with conn:
        yield conn


def blob_store() -> BlobStore:
    root = environ.get(BLOB_ROOT)
    if not root:
        raise Refusal(RefusalCode.STORE_NOT_CONFIGURED)
    return BlobStore(Path(root))


def actor_from_request(request: Request) -> Actor:
    """Who is asking. A dependency rather than a line in a route body.

    FastAPI builds a route's dependency list in the order its parameters declare
    them and solves it sequentially, so declaring this one before `Store` is
    what keeps identity ahead of the connection. Two things rest on that. An
    anonymous request is refused without opening one -- a connection is per
    request and unpooled, and asking in a loop costs the asker nothing. And the
    answer to a stranger does not depend on the store being reachable: a process
    that has lost its database still says "I do not know who you are", which is
    the only one of the two answers that is about the caller.

    It closes the anonymous half and not the whole of it. A request asserting
    any well-formed subject still reaches the connection, because whether that
    subject is real is the edge's question rather than this process's
    (`server/api/identity.py`).
    """
    return actor_from_headers(request.headers)


Caller = Annotated[Actor, Depends(actor_from_request)]
Store = Annotated[StoreConnection, Depends(store_connection)]
Blobs = Annotated[BlobStore, Depends(blob_store)]


@app.exception_handler(Refusal)
def _refused(_request: Request, refusal: Refusal) -> Response:
    """A refusal on the wire: the code, and no part of what caused it."""
    return JSONResponse(
        status_code=_STATUS.get(refusal.code, 400),
        content=RefusalBody(refusal=refusal.code).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def _malformed_run_id(
    request: Request, error: RequestValidationError
) -> Response:
    """A run id that cannot be read names no run.

    FastAPI's own 422 answered it before identity, in a body that is not the
    declared refusal and that quotes the input back. So it is answered as
    `_visible` answers any run it cannot show: NOT_AUTHENTICATED to a caller
    with no identity, RUN_NOT_FOUND to everyone else. Only for `run_id` -- any
    other path parameter, a query or a body is not a missing run, and gets the
    default until the route that takes one says what it should get instead.
    """
    unreadable = {tuple(detail.get("loc") or ())[:2] for detail in error.errors()}
    if unreadable != {("path", "run_id")}:
        return await request_validation_exception_handler(request, error)
    try:
        actor_from_headers(request.headers)
    except Refusal as refusal:
        return _refused(request, refusal)
    return _refused(request, Refusal(RefusalCode.RUN_NOT_FOUND))


@app.get("/api/runs/{run_id}", response_model=RunDocument)
def read_run(run_id: UUID, actor: Caller, conn: Store, blobs: Blobs) -> RunDocument:
    """The run, its pinned route, and each node's state with its reason.

    `actor` is declared first, and the order is load-bearing: see
    `actor_from_request`.
    """
    _case_id, status = _visible(conn, run_id, actor)

    route = resolved_route(conn, run_id)
    if route is None:
        return RunDocument(run_id=run_id, status=status, route_digest=None, nodes=[])

    accepted = accepted_artifacts(conn, blobs, route, run_id)
    states = node_states(route, accepted)
    # `accepted` already carries CP-0's body -- `accepted_artifacts` fetches it
    # for exactly this reason -- so reading the verdict out of it here costs no
    # further round trip and `IO_BUDGET` does not move.
    readiness = readiness_from(route, accepted)
    return RunDocument(
        run_id=run_id,
        status=status,
        # Recomputed from the route just read, not read from its own column: it
        # is then the digest of the thing this document actually describes, and
        # a stored digest that had drifted from the stored route would show up
        # here rather than being reported over the top of it.
        route_digest=route_digest(route),
        nodes=[
            _node_view(route, accepted, node, states, readiness) for node in route.nodes
        ],
    )


@app.get("/api/runs/{run_id}/events")
def read_run_events(
    run_id: UUID, actor: Caller, request: Request, conn: Store
) -> StreamingResponse:
    """The run's events as `text/event-stream`, resuming after `Last-Event-ID`.

    The authority read happens here, before the first byte, so that an
    unauthorised watcher gets the same 404 the run document gives rather than an
    empty 200 -- which would still confirm the id names a run somebody watches.
    `actor` is declared before `conn` for the reason `actor_from_request` gives;
    `request` is still taken, for the resume marker alone.
    """
    case_id, _status = _visible(conn, run_id, actor)

    return StreamingResponse(
        _frames(conn, run_id, case_id, actor, _marker(request.headers)),
        media_type="text/event-stream",
        # No store, and no proxy buffering: a tail that arrived in one block when
        # the run ended would not be a tail.
        headers={"cache-control": "no-store", "x-accel-buffering": "no"},
    )


def _frames(
    conn: StoreConnection,
    run_id: UUID,
    case_id: UUID,
    actor: Actor,
    last_event_id: int,
) -> Iterator[bytes]:
    """Frames until the run is terminal, the actor loses standing, or the
    deadline passes.

    `TAIL_DEADLINE` is read here rather than bound as a default, so a process
    does not have to restart to pick up a corrected value.
    """
    started = monotonic()
    marker = last_event_id
    while True:
        for event in tail(
            conn, run_id=run_id, actor_id=actor.user_id, last_event_id=marker
        ):
            marker = event.id
            yield _frame(event)
            if event.name in TERMINAL:
                return

        # The tail is silent both when it is caught up and when standing was
        # revoked mid-stream. Asking directly is what tells those apart -- an SSE
        # connection is exactly the thing that stays open across a revocation,
        # and a loop that idled to the deadline instead would keep a revoked
        # reader's socket alive for five minutes.
        if not satisfies(
            standing_of(conn, case_id=case_id, user_id=actor.user_id), READ_REQUIRES
        ):
            return
        if monotonic() - started >= TAIL_DEADLINE:
            return
        sleep(POLL_INTERVAL)


def _frame(event: StreamEvent) -> bytes:
    """One SSE frame. The name triggers a refetch; `data` is a placeholder
    because the spec dispatches no event without one, and a real payload would be
    a second copy of state the client is about to fetch properly."""
    return f"id: {event.id}\nevent: {event.name}\ndata: {dumps({})}\n\n".encode()


def _marker(headers: object) -> int:
    """The client's resume position, or the beginning.

    A browser-supplied string. Refusing the connection would strand a client that
    can only fix it by clearing storage, and re-delivering from the start is what
    the contract already tolerates.
    """
    get = getattr(headers, "get", None)
    value = get("last-event-id") if get is not None else None
    if not isinstance(value, str) or not value.isdigit():
        return 0
    return int(value)


def _node_view(
    route: ResolvedRoute,
    accepted: Mapping[str, Any],
    node: RouteNode,
    states: Mapping[str, NodeState],
    readiness: Mapping[str, str],
) -> NodeView:
    unmet = waiting_on(route, accepted, node.route_node_id)
    return NodeView(
        route_node_id=node.route_node_id,
        module_id=node.module_id,
        state=states[node.route_node_id].value,
        waiting_on=[EdgeView(source=edge.source, type=edge.type) for edge in unmet],
        awaiting_gate=any(edge.type is EdgeType.QA_GATE for edge in unmet),
        # `.get`, not `[]`: a module the gate has not ruled on -- every module,
        # until CP-0's own artifact is accepted -- has no verdict rather than a
        # false one, and None is that absence on the wire.
        gate_verdict=readiness.get(node.module_id),
    )


def _visible(conn: StoreConnection, run_id: UUID, actor: Actor) -> tuple[UUID, str]:
    """The run's case and status, if this actor may see it at all.

    One query: a second round trip to learn the status of a run the caller turns
    out not to be able to see would be a round trip spent on a 404.
    """
    row = conn.execute(
        "SELECT case_id, status FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)

    case_id = UUID(str(row[0]))
    if not satisfies(
        standing_of(conn, case_id=case_id, user_id=actor.user_id), READ_REQUIRES
    ):
        # Deliberately the refusal a missing run gets. The two answers have to be
        # identical, or the difference between them is the disclosure.
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    return case_id, str(row[1])
