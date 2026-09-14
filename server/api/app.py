"""The HTTP surface: the section reads, the run tail, and one answer for a
stranger.

`SYSTEM_SPEC.md` §9 and `docs/DECISIONS.md` §22. Each section read lives in its
own module under `server/api/reads/` (Task 4.1); the retired run document is now
the Run section. The events path is the socket `server/api/stream.py`'s
contract is served over -- that module already answers every rule §9 states,
and this is where those answers meet a connection.

The privacy rule is the load-bearing one. A run somebody may not see and a run
that does not exist get the same status and the same body, because 403 is the
informative answer and that is exactly its problem: it confirms the id names
something real. `NOT_AUTHENTICATED` is different in kind -- "I do not know who
you are" discloses nothing about any case -- so it is answered plainly, and a
client that got a 404 for it would retry the wrong thing forever.

Responses are named models with `extra="forbid"` in both directions. A response
shape that let an extra key through is how a store column reaches a browser
because somebody widened a SELECT.

FastAPI's own `/docs`, `/redoc` and `/openapi.json` are not served (Task 4.5
decision 6): Swagger loads a script from a CDN the policy refuses, and a route
map is nothing a browser of this workspace needs. Every request passes
`server/api/edge.py`'s guard first -- the edge token or the loopback rule, the
identity-header hygiene, the Origin check -- before routing or identity.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, suppress
from json import dumps
from time import monotonic, sleep
from uuid import UUID

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.api import health
from server.api.commands import cases as cases_command
from server.api.commands import execution as execution_command
from server.api.commands import runs as runs_command
from server.api.deps import BLOB_ROOT as BLOB_ROOT
from server.api.deps import DATABASE_URL as DATABASE_URL
from server.api.deps import VENDORED_BUNDLE as VENDORED_BUNDLE
from server.api.deps import Blobs as Blobs
from server.api.deps import Caller as Caller
from server.api.deps import Methodology as Methodology
from server.api.deps import Store as Store
from server.api.deps import _database_url as _database_url
from server.api.deps import _vendored_bundle as _vendored_bundle
from server.api.deps import actor_from_request as actor_from_request
from server.api.deps import blob_store as blob_store
from server.api.deps import methodology_bundle as methodology_bundle
from server.api.deps import store_connection as store_connection
from server.api.edge import EdgeGuard
from server.api.identity import Actor, actor_from_headers
from server.api.reads import analysis as analysis_read
from server.api.reads import directory as directory_read
from server.api.reads import evidence as evidence_read
from server.api.reads import run as run_read
from server.api.reads import upload as upload_read
from server.api.reads.analysis import RunQuery
from server.api.reads.upload import CasePath
from server.api.stream import (
    CONNECT_IO,
    POLL_IO,
    TERMINAL,
    StreamEvent,
    _CaseEvent,
    case_tail,
    tail,
)
from server.api.stream import IO_BUDGET as TAIL_IO_BUDGET
from server.api.wire import CLEARS, RefusalBody
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, apply_schema, connect
from server.store.members import Standing, satisfies, standing_of

# `GET /api/v1/cases/{case_id}/events`, the one path this module serves: the
# caller's standing and the run's case, the heads, the cursor frame's recheck,
# then the first poll -- after which each poll costs `POLL_IO` again and each
# frame one recheck. Measured in `tests/test_case_events.py`. The section reads
# declare their own budgets.
EVENTS_IO_BUDGET = 2 + CONNECT_IO + 1 + POLL_IO
# The retired `GET /api/runs/{run_id}/events`, until p3 removes it.
RUN_EVENTS_IO_BUDGET = 2 + TAIL_IO_BUDGET
IO_BUDGET = EVENTS_IO_BUDGET

# Tailing a case is reading it. Anything the tail shows, a reader of the
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

# The status for each refusal that can leave a route here. Unauthorised is
# absent on purpose: it is answered as RUN_NOT_FOUND before it can be raised.
# The store's own faults are 503: the server cannot answer, whoever asks, and a
# 400 would tell the caller their request was the problem.
_STATUS = {
    RefusalCode.NOT_AUTHENTICATED: 401,
    RefusalCode.RUN_NOT_FOUND: 404,
    RefusalCode.CASE_NOT_FOUND: 404,
    # Every unavailable evidence page is one private answer (decision 7).
    RefusalCode.PAGE_NOT_AVAILABLE: 404,
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
    RefusalCode.ROUTE_IDENTITY_INVALID: 503,
    RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE: 503,
    # A canonical record that no longer binds its Markdown, pin or bundle is
    # likewise the server's own bytes failing verification.
    RefusalCode.ARTIFACT_RECORD_MISMATCH: 503,
    RefusalCode.RUN_INPUT_INVALID: 503,
    RefusalCode.SOURCE_IDENTITY_INVALID: 503,
    RefusalCode.AUTHORITY_BYTES_MISMATCH: 503,
    # Re-validating an accepted handoff: it passed these under the same pin,
    # so failing now is stored bytes or authority moving, never the request.
    RefusalCode.HANDOFF_MALFORMED: 503,
    RefusalCode.HANDOFF_BLOCKED: 503,
    RefusalCode.HANDOFF_IDENTITY_MISMATCH: 503,
    RefusalCode.HANDOFF_INCOMPLETE: 503,
    RefusalCode.HANDOFF_UNDECLARED_FIELD: 503,
    RefusalCode.HANDOFF_MODULE_UNSUPPORTED: 503,
    RefusalCode.ATTEMPT_NOT_FOUND: 503,
    RefusalCode.AUTHORITY_MODULE_UNKNOWN: 503,
    # Commands (Task 4.2 decision 8). A member below a command's floor is told
    # so; a stranger never reaches this, being answered CASE_NOT_FOUND first.
    RefusalCode.NOT_AUTHORISED: 403,
    # Answered by the edge guard before routing; listed so a route cannot give
    # either a different status.
    RefusalCode.EDGE_NOT_TRUSTED: 403,
    RefusalCode.ORIGIN_REFUSED: 403,
    RefusalCode.SOURCE_TOO_LARGE: 413,
    # The request was sound and the state it expected has moved: a conflict.
    RefusalCode.IDEMPOTENCY_KEY_REUSED: 409,
    RefusalCode.RUN_NOT_RUNNING: 409,
    RefusalCode.GATE_APPROVAL_MISMATCH: 409,
    RefusalCode.EVIDENCE_NOT_AVAILABLE: 409,
    RefusalCode.ROUTE_ALREADY_PINNED: 409,
    RefusalCode.ROUTE_PIN_TOO_LATE: 409,
    RefusalCode.RUN_INPUT_ALREADY_PINNED: 409,
    RefusalCode.RUN_INPUT_TOO_LATE: 409,
    RefusalCode.RUN_INPUT_NOT_PINNED: 409,
    RefusalCode.RUN_ALREADY_STARTED: 409,
    RefusalCode.RUN_NOT_STOPPED: 409,
    RefusalCode.RUN_CANCEL_REQUESTED: 409,
    RefusalCode.COMMAND_EXPECTATION_STALE: 409,
    RefusalCode.ORCHESTRATION_BUILD_MOVED: 409,
}


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Apply the declared schema before the first request, and refuse to start
    without a database.

    "Postgres schema in full at startup" is the store's rule, and `apply_schema`
    is idempotent -- it advances a verified migration prefix on this fresh
    connection and refuses `STORE_SCHEMA_DRIFT` for unknown or edited history.
    It commits the migration transaction before requests begin. Doing it
    here rather than lazily means a process pointed at the wrong database dies at
    boot instead of serving 500s that look like a bug in the route.
    """
    with connect(_database_url()) as conn:
        apply_schema(conn)
    # The one health probe task (slice 4.5b); the route reads what it leaves.
    _app.state.health = health.ProbeState()
    probes = asyncio.create_task(health.probe_loop(_app.state.health))
    try:
        yield
    finally:
        probes.cancel()
        with suppress(asyncio.CancelledError):
            await probes


app = FastAPI(
    title="CAOS",
    version="2",
    lifespan=_lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(EdgeGuard)
# One router per section read (Task 4.1), so each slice adds its route in its
# own module and none edits this one.
for _section in (directory_read, upload_read, run_read, analysis_read, evidence_read):
    app.include_router(_section.router)
app.include_router(health.router)
for _commands in (cases_command, runs_command, execution_command):
    app.include_router(_commands.router)


def _body(code: RefusalCode, status: int) -> Response:
    return JSONResponse(
        status_code=status,
        content=RefusalBody(code=code, clears=CLEARS[code]).model_dump(mode="json"),
    )


@app.exception_handler(Refusal)
def _refused(_request: Request, refusal: Refusal) -> Response:
    """A refusal on the wire: the code, its constant clearance, and no part of
    what caused it."""
    return _body(refusal.code, _STATUS.get(refusal.code, 400))


@app.exception_handler(StarletteHTTPException)
async def _undeclared(request: Request, error: StarletteHTTPException) -> Response:
    """Routing's own 404 and 405 under `/api/` answer in the one refusal body.

    Routing decides before any dependency runs, so this discloses no case and
    needs no identity. Outside `/api/`, and for any other status, the default
    stands: that surface is not this contract's.
    """
    under_api = request.url.path == "/api" or request.url.path.startswith("/api/")
    if under_api and error.status_code in (404, 405):
        return _body(RefusalCode.ENDPOINT_NOT_FOUND, error.status_code)
    return await http_exception_handler(request, error)


@app.exception_handler(RequestValidationError)
async def _malformed_run_id(
    request: Request, error: RequestValidationError
) -> Response:
    """A run id that cannot be read names no run, and a body that cannot be
    read is an invalid request.

    FastAPI's own 422 answered them before identity, in a body that is not the
    declared refusal and that quotes the input back. So a run id is answered as
    `_visible` answers any run it cannot show: NOT_AUTHENTICATED to a caller
    with no identity, RUN_NOT_FOUND to everyone else. A body (Task 4.2
    decision 5) is REQUEST_INVALID after the same identity check. Any other
    path parameter or a query gets the default until the route that takes one
    says what it should get instead.
    """
    unreadable = {tuple(detail.get("loc") or ())[:2] for detail in error.errors()}
    if unreadable == {("path", "run_id")}:
        code = RefusalCode.RUN_NOT_FOUND
    elif unreadable and all(loc[:1] == ("body",) for loc in unreadable):
        code = RefusalCode.REQUEST_INVALID
    else:
        return await request_validation_exception_handler(request, error)
    try:
        actor_from_headers(request.headers)
    except Refusal as refusal:
        return _refused(request, refusal)
    return _refused(request, Refusal(code))


@app.get("/api/v1/cases/{case_id}/events")
def read_case_events(
    actor: Caller, case_id: CasePath, run: RunQuery, request: Request, conn: Store
) -> StreamingResponse:
    """The case's events as `text/event-stream`, resuming after `Last-Event-ID`.

    The authority read happens here, before the first byte, so an unauthorised
    watcher gets the private 404 a missing case gets rather than an empty 200.
    Identity, then the path and query parsers, then the store: the order is
    what keeps an anonymous or malformed request off a connection.
    """
    _case_visible(conn, case_id, run, actor)
    # Read at request time rather than bound as defaults, so a corrected value
    # needs no restart (and a test can shorten them).
    events = case_tail(
        conn,
        case_id=case_id,
        run_id=run,
        actor_id=actor.user_id,
        after=request.headers.get("last-event-id"),
        deadline=TAIL_DEADLINE,
        poll=POLL_INTERVAL,
    )
    return StreamingResponse(
        (_case_frame(event) for event in events),
        media_type="text/event-stream",
        # No store, and no proxy buffering: a tail that arrived in one block
        # when the deadline passed would not be a tail.
        headers={"cache-control": "no-store", "x-accel-buffering": "no"},
    )


def _case_frame(event: _CaseEvent) -> bytes:
    """One SSE frame. The cursor frame is `id` alone, which sets the browser's
    `lastEventId` and dispatches nothing. A named frame's `data` is a
    placeholder because the spec dispatches no event without one."""
    if event.name is None:
        return f"id: {event.id}\n\n".encode()
    return f"id: {event.id}\nevent: {event.name}\ndata: {dumps({})}\n\n".encode()


def _case_visible(
    conn: StoreConnection, case_id: UUID, run_id: UUID | None, actor: Actor
) -> None:
    """Refuse a case this actor may not read, then a run that is not the case's.

    Standing first: a stranger learns nothing about which runs a case holds.
    """
    if not satisfies(
        standing_of(conn, case_id=case_id, user_id=actor.user_id), READ_REQUIRES
    ):
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    if run_id is None:
        return
    row = conn.execute(
        "SELECT 1 FROM runs WHERE run_id = %s AND case_id = %s", (run_id, case_id)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)


@app.get("/api/runs/{run_id}/events")
def read_run_events(
    run_id: UUID, actor: Caller, request: Request, conn: Store
) -> StreamingResponse:
    """The run's events as `text/event-stream`, resuming after `Last-Event-ID`.

    The authority read happens here, before the first byte, so that an
    unauthorised watcher gets a private 404 rather than an
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
