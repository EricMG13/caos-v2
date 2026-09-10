"""The HTTP surface, and one answer for a stranger.

`SYSTEM_SPEC.md` §9 and `docs/DECISIONS.md` §22. This is the run document
`/run/` will draw in Phase 9: each node's state with the reason for it, and the
one QA_GATE reading as a gate.

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

from collections.abc import Iterator, Mapping
from os import environ
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from server.api.identity import Actor, actor_from_headers
from server.blobs import BlobStore
from server.engine.route import (
    EdgeType,
    NodeState,
    ResolvedRoute,
    RouteNode,
    node_states,
    route_digest,
    waiting_on,
)
from server.engine.runtime import accepted_artifacts
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, connect
from server.store.members import Standing, satisfies, standing_of
from server.store.routes import resolved_route

# `GET /api/runs/{run_id}`: the run and its case in one row, the caller's
# standing, the pinned route, the accepted attempts. Four, and it does not grow
# with the size of the route -- which is the shape the predecessor got wrong.
IO_BUDGET = 4

# Reading a run is reading its case. Anything this document shows, a reader of
# the case may see; holding it grants nothing further.
READ_REQUIRES = Standing.READER

DATABASE_URL = "CAOS_DATABASE_URL"
BLOB_ROOT = "CAOS_BLOB_ROOT"

# The status for each refusal that can leave a route here. Unauthorised is
# absent on purpose: it is answered as RUN_NOT_FOUND before it can be raised.
_STATUS = {
    RefusalCode.NOT_AUTHENTICATED: 401,
    RefusalCode.RUN_NOT_FOUND: 404,
    RefusalCode.CASE_NOT_FOUND: 404,
}

app = FastAPI(title="CAOS", version="2")


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


def store_connection() -> Iterator[StoreConnection]:
    """One connection per request, from the environment."""
    url = environ.get(DATABASE_URL)
    if not url:
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)
    with connect(url) as conn:
        yield conn


def blob_store() -> BlobStore:
    root = environ.get(BLOB_ROOT)
    if not root:
        raise Refusal(RefusalCode.BLOB_NOT_FOUND)
    return BlobStore(Path(root))


Store = Annotated[StoreConnection, Depends(store_connection)]
Blobs = Annotated[BlobStore, Depends(blob_store)]


@app.exception_handler(Refusal)
def _refused(_request: Request, refusal: Refusal) -> Response:
    """A refusal on the wire: the code, and no part of what caused it."""
    return JSONResponse(
        status_code=_STATUS.get(refusal.code, 400),
        content=RefusalBody(refusal=refusal.code).model_dump(mode="json"),
    )


@app.get("/api/runs/{run_id}", response_model=RunDocument)
def read_run(run_id: UUID, request: Request, conn: Store, blobs: Blobs) -> RunDocument:
    """The run, its pinned route, and each node's state with its reason."""
    actor = actor_from_headers(request.headers)
    _case_id, status = _visible(conn, run_id, actor)

    route = resolved_route(conn, run_id)
    if route is None:
        return RunDocument(run_id=run_id, status=status, route_digest=None, nodes=[])

    accepted = accepted_artifacts(conn, blobs, route, run_id)
    states = node_states(route, accepted)
    return RunDocument(
        run_id=run_id,
        status=status,
        # Recomputed from the route just read, not read from its own column: it
        # is then the digest of the thing this document actually describes, and
        # a stored digest that had drifted from the stored route would show up
        # here rather than being reported over the top of it.
        route_digest=route_digest(route),
        nodes=[_node_view(route, accepted, node, states) for node in route.nodes],
    )


def _node_view(
    route: ResolvedRoute,
    accepted: Mapping[str, Any],
    node: RouteNode,
    states: Mapping[str, NodeState],
) -> NodeView:
    unmet = waiting_on(route, accepted, node.route_node_id)
    return NodeView(
        route_node_id=node.route_node_id,
        module_id=node.module_id,
        state=states[node.route_node_id].value,
        waiting_on=[EdgeView(source=edge.source, type=edge.type) for edge in unmet],
        awaiting_gate=any(edge.type is EdgeType.QA_GATE for edge in unmet),
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
