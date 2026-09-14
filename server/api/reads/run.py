"""The Run section read (Task 4.1, slice 4.1d).

`GET /api/v1/cases/{case_id}/run?run=` replaces the retired
`GET /api/runs/{run_id}` (decision 4). The case is the authorisation resource:
an unknown, malformed, unauthorised or revoked case is one private
`CASE_NOT_FOUND`, and a `run` this case does not own -- unknown, malformed or
another case's -- is one `RUN_NOT_FOUND`, asked only once the case is visible.

The displayed run and the latest run are separate identities on the wire
(REPAIR_PLAN Phase 4 item 1). Node states are recomputed from the pinned route
and the accepted artifacts, never stored; each carries the reason for it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter

from server.api.deps import Blobs, Caller, Methodology, Store
from server.api.identity import Actor
from server.api.wire import (
    ATTEMPTS_MAX,
    RUNS_MAX,
    AttemptView,
    Chrome,
    EdgeView,
    GateView,
    NodeView,
    RunBody,
    RunSectionDocument,
    RunSubjectView,
    RunSummary,
    RunView,
    SectionNote,
    ServedRole,
    Subject,
)
from server.blobs import BlobStore
from server.engine.route import (
    Edge,
    EdgeType,
    NamedObjects,
    NodeResult,
    NodeState,
    ResolvedRoute,
    RouteNode,
    lite_object_unmet,
    node_states,
    readiness_from,
    route_digest,
    waiting_on,
)
from server.engine.runtime import accepted_artifacts
from server.methodology.bundle import Bundle
from server.methodology.invocation import named_objects
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.gates import Gate, gate_state
from server.store.members import Standing, satisfies
from server.store.routes import resolved_route
from server.store.run_inputs import load_run_input

# The case, the caller's standing and the store's `now()` in one row; the
# bounded run list; the attempts; the pinned route; the accepted artifacts.
_FIXED_IO = 5
# Of those, the accepted artifacts are read only once a route is pinned.
ACCEPTED_IO = 1
# The displayed run, read by id only when the bounded list does not hold it.
BEYOND_LIST_IO = 1
# The pinned input, as `load_run_input` verifies it: its row, the run, the
# source set's header and members, and the route it binds.
PINNED_INPUT_IO = 5
# `gate_state` per gate over a pinned input: the input again, the approval, the
# approver's standing and the live-source check.
GATE_IO = PINNED_INPUT_IO + 3
# Before an input is pinned, the input read and each gate's find no row.
UNPINNED_INPUT_IO = _FIXED_IO + 1 + len(Gate)
SECTION_READ_IO = _FIXED_IO + PINNED_INPUT_IO + len(Gate) * GATE_IO
# A canonical readiness row (§42.4) is read from its record under the host
# identity the store rebuilds: the run input, the pinned route, the attempt's
# owner and ordinal, the accepted digests, and the call-time narrowing's
# artifact read. Measured on a LITE run (`tests/test_canonical_readers.py`),
# per such row. A row without its record refuses `ARTIFACT_RECORD_MISMATCH`
# (503) at no further cost.
CANONICAL_READINESS_IO = 10
# Readiness rows are the gate's and each QA_GATE source's. The catalog carries
# one QA_GATE (`CP-5 -> CP-6`), so a route holds at most two -- the bound is a
# constant, not a function of route length.
READINESS_ROWS = 2
IO_BUDGET = SECTION_READ_IO + BEYOND_LIST_IO + READINESS_ROWS * CANONICAL_READINESS_IO

# Reading the Run section is reading its case; holding it grants nothing more.
READ_REQUIRES = Standing.READER

router = APIRouter()


@router.get("/api/v1/cases/{case_id}/run", response_model=RunSectionDocument)
def read_run_section(  # noqa: PLR0913 -- identity, store, blobs, bundle, two ids
    case_id: str,
    actor: Caller,
    conn: Store,
    blobs: Blobs,
    bundle: Methodology,
    run: str | None = None,
) -> RunSectionDocument:
    """The case's runs and the displayed run with each node's state.

    Both ids are taken as text and read here, after identity: a malformed case
    is `CASE_NOT_FOUND` and a malformed run `RUN_NOT_FOUND`, never FastAPI's
    422 quoting the input back.
    """
    case = _uuid(case_id, RefusalCode.CASE_NOT_FOUND)
    title, standing, observed_at = _visible_case(conn, case, actor)
    wanted = None if run is None else _uuid(run, RefusalCode.RUN_NOT_FOUND)

    rows = conn.execute(
        "SELECT r.run_id, r.status, r.created_at, p.profile_id, p.selection_id"
        " FROM runs r LEFT JOIN run_routes p ON p.run_id = r.run_id"
        " WHERE r.case_id = %s ORDER BY r.created_at DESC, r.run_id DESC LIMIT %s",
        (case, RUNS_MAX + 1),
    ).fetchall()
    notes = [SectionNote.LIST_TRUNCATED] if len(rows) > RUNS_MAX else []
    runs = [_summary(row) for row in rows[:RUNS_MAX]]
    displayed = runs[0] if wanted is None and runs else None
    if wanted is not None:
        displayed = next((s for s in runs if s.run_id == wanted), None)
        displayed = displayed or _displayed_beyond_the_list(conn, case, wanted)

    view = None
    if displayed is not None:
        view, run_notes = _run_view(conn, blobs, bundle, displayed)
        notes.extend(run_notes)
    return RunSectionDocument(
        chrome=Chrome(
            subject=Subject(case_id=case, title=title),
            served_role=ServedRole(global_role=actor.role, standing=standing),
        ),
        body=RunBody(
            case_id=case,
            latest_run_id=runs[0].run_id if runs else None,
            displayed_run_id=None if displayed is None else displayed.run_id,
            runs=runs,
            run=view,
        ),
        observed_at=observed_at,
        observed_empty=not runs,
        status="partial" if notes else "complete",
        notes=notes,
    )


def _uuid(value: str, code: RefusalCode) -> UUID:
    """An id read from the request, or the refusal a missing one gets. Raised
    outside the `except`, so nothing of the input is chained behind it."""
    try:
        parsed: UUID | None = UUID(value)
    except ValueError:
        parsed = None
    if parsed is None:
        raise Refusal(code)
    return parsed


def _visible_case(
    conn: StoreConnection, case_id: UUID, actor: Actor
) -> tuple[str, Standing, Any]:
    """The case's title, the caller's live standing and the store's `now()`.

    One query. An unknown case and a case the caller may not read are the same
    refusal, or the difference between them is the disclosure.
    """
    row = conn.execute(
        "SELECT c.title, m.standing, now() FROM cases c"
        " LEFT JOIN case_members m ON m.case_id = c.case_id"
        " AND m.user_id = %s AND m.revoked_at IS NULL"
        " WHERE c.case_id = %s",
        (actor.user_id, case_id),
    ).fetchone()
    standing = None if row is None or row[1] is None else Standing(row[1])
    if row is None or standing is None or not satisfies(standing, READ_REQUIRES):
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    return str(row[0]), standing, row[2]


def _summary(row: tuple[Any, ...]) -> RunSummary:
    return RunSummary(
        run_id=row[0],
        status=row[1],
        created_at=row[2],
        profile_id=row[3],
        selection_id=row[4],
    )


def _displayed_beyond_the_list(
    conn: StoreConnection, case_id: UUID, run_id: UUID
) -> RunSummary:
    """A run of this case older than the bounded list, or `RUN_NOT_FOUND` --
    the same answer for an unknown run and another case's."""
    row = conn.execute(
        "SELECT r.run_id, r.status, r.created_at, p.profile_id, p.selection_id"
        " FROM runs r LEFT JOIN run_routes p ON p.run_id = r.run_id"
        " WHERE r.run_id = %s AND r.case_id = %s",
        (run_id, case_id),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    return _summary(row)


def _run_view(
    conn: StoreConnection, blobs: BlobStore, bundle: Bundle, summary: RunSummary
) -> tuple[RunView, list[SectionNote]]:
    run_id = summary.run_id
    pin = load_run_input(conn, run_id)
    gates = [GateView(gate=gate, state=gate_state(conn, run_id, gate)) for gate in Gate]
    attempts = conn.execute(
        "SELECT a.attempt_id, a.route_node_id, a.ordinal, a.started_at,"
        " f.attempt_id IS NOT NULL FROM run_attempts a"
        " LEFT JOIN artifacts f ON f.attempt_id = a.attempt_id"
        " WHERE a.run_id = %s ORDER BY a.started_at, a.attempt_id LIMIT %s",
        (run_id, ATTEMPTS_MAX + 1),
    ).fetchall()
    notes = [SectionNote.LIST_TRUNCATED] if len(attempts) > ATTEMPTS_MAX else []
    route = resolved_route(conn, run_id)
    nodes: list[NodeView] = []
    if route is None:
        notes.append(SectionNote.ROUTE_NOT_PINNED)
    else:
        nodes = _node_views(conn, blobs, bundle, route, summary)
    view = RunView(
        run_id=run_id,
        status=summary.status,
        created_at=summary.created_at,
        # Recomputed from the route just read, not read from its own column: it
        # is then the digest of the thing this document describes, and a
        # stored digest that had drifted would show up here.
        route_digest=None if route is None else route_digest(route),
        build_id=None if pin is None else pin.build_id,
        source_set_version=None if pin is None else pin.source_version,
        subject=None
        if pin is None or pin.subject is None
        else RunSubjectView(
            issuer_id=pin.subject.issuer_id,
            issuer_name=pin.subject.issuer_name,
            reporting_period=pin.subject.reporting_period,
            analysis_date=pin.subject.analysis_date,
        ),
        gates=gates,
        nodes=nodes,
        attempts=[
            AttemptView(
                attempt_id=row[0],
                route_node_id=row[1],
                ordinal=row[2],
                started_at=row[3],
                accepted=row[4],
            )
            for row in attempts[:ATTEMPTS_MAX]
        ],
    )
    return view, list(dict.fromkeys(notes))


def _node_views(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    route: ResolvedRoute,
    summary: RunSummary,
) -> list[NodeView]:
    # The bundle is what reads a canonical run's gate and QA records (§42.4).
    accepted = accepted_artifacts(conn, blobs, route, summary.run_id, bundle=bundle)
    # The runtime's named-object boundary, so the document shows its states.
    named = named_objects(bundle, route)
    states = node_states(route, accepted, named)
    # `accepted` already carries CP-0's readiness, so the verdict costs no
    # further round trip.
    readiness = readiness_from(route, accepted)
    views = (
        _node_view(route, accepted, node, states, readiness, named)
        for node in route.nodes
    )
    # Nothing is awaited on a run that is no longer running.
    return [
        view
        if summary.status == "RUNNING"
        else view.model_copy(update={"awaiting_gate": False})
        for view in views
    ]


def node_readiness(  # noqa: PLR0913 -- one node of one run document
    route: ResolvedRoute,
    accepted: Mapping[str, NodeResult],
    node: RouteNode,
    states: Mapping[str, NodeState],
    readiness: Mapping[str, str],
    named: NamedObjects | None = None,
) -> tuple[Sequence[Edge], bool, str | None]:
    """The unmet edges, `awaiting_gate` and `gate_verdict`: shared by the v1
    wire (`_node_view` below) and the legacy run document (`server/api/app.py`)
    until that document is retired. Each wire builds its own `EdgeView` from
    the raw edges, since the two documents do not share that model.

    The one QA_GATE in the catalog is `CP-5 -> CP-6`. `awaiting_gate` is true
    while the node waits for the QA source's verdict. Once CP-5 answered
    anything but `Passed`, nothing is awaited: the node is BLOCKED by that
    verdict and the unmet edges still name it (F03).
    """
    done = states[node.route_node_id] is NodeState.COMPLETE
    unmet = () if done else waiting_on(route, accepted, node.route_node_id)
    if not done and named is not None and node.module_id in named.accepted_ids:
        # A node held for its named object names the edges that could meet it.
        extra = lite_object_unmet(route, accepted, node.module_id, named)
        unmet = (*unmet, *(edge for edge in extra if edge not in unmet))
    answered = {n.module_id for n in route.nodes if n.route_node_id in accepted}
    awaiting_gate = any(
        edge.type is EdgeType.QA_GATE and edge.source not in answered for edge in unmet
    )
    # `.get`, not `[]`: a module the gate has not ruled on has no verdict
    # rather than a false one, and None is that absence on the wire.
    return unmet, awaiting_gate, readiness.get(node.module_id)


def _node_view(  # noqa: PLR0913 -- one node of one run document
    route: ResolvedRoute,
    accepted: Mapping[str, NodeResult],
    node: RouteNode,
    states: Mapping[str, NodeState],
    readiness: Mapping[str, str],
    named: NamedObjects | None = None,
) -> NodeView:
    unmet, awaiting_gate, gate_verdict = node_readiness(
        route, accepted, node, states, readiness, named
    )
    return NodeView(
        route_node_id=node.route_node_id,
        module_id=node.module_id,
        stage=node.stage,
        state=states[node.route_node_id],
        waiting_on=[EdgeView(source=edge.source, type=edge.type) for edge in unmet],
        awaiting_gate=awaiting_gate,
        gate_verdict=gate_verdict,
    )
