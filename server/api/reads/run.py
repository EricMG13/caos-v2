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

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import APIRouter

from server import methodology
from server.api.commands.availability import RunFacts, run_actions
from server.api.deps import (
    Blobs,
    Caller,
    CasePath,
    Methodology,
    RunQuery,
    Store,
    readable,
)
from server.api.identity import Actor
from server.api.wire import (
    ATTEMPTS_MAX,
    RUNS_MAX,
    AttemptView,
    BlockedByView,
    Chrome,
    EdgeView,
    GateView,
    NodeView,
    RouteChoice,
    RunBody,
    RunSectionDocument,
    RunSubjectView,
    RunSummary,
    RunView,
    SectionNote,
    ServedRole,
    Subject,
    WorkView,
)
from server.blobs import BlobStore
from server.engine.route import (
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
from server.methodology.handoff import ADAPTER_ROUTES
from server.methodology.invocation import named_objects
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.gates import (
    Gate,
    GateState,
    gate_state,
    require_adapter_route,
    sources_live,
)
from server.store.members import Standing
from server.store.routes import resolved_route
from server.store.run_inputs import load_run_input

# The case, the caller's standing, its live-source count and the store's
# `now()` in one row; the bounded run list; the attempts; the pinned route; the
# accepted artifacts.
_FIXED_IO = 5
# The displayed run's `run_work` row (Task 4.2 decision 14).
WORK_IO = 1
# Whether the pinned sources are still live, read once a pin exists.
LIVE_IO = 1
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
UNPINNED_INPUT_IO = _FIXED_IO + WORK_IO + 1 + len(Gate)
SECTION_READ_IO = _FIXED_IO + WORK_IO + LIVE_IO + PINNED_INPUT_IO + len(Gate) * GATE_IO
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
# The attempt whose validated Blocked verdict ended the run, as the transition
# recorded it (§68): one row, read only on a BLOCKED run with a pinned route.
BLOCKED_BY_IO = 1
IO_BUDGET = (
    SECTION_READ_IO
    + BEYOND_LIST_IO
    + READINESS_ROWS * CANONICAL_READINESS_IO
    + BLOCKED_BY_IO
)

router = APIRouter()


@router.get("/api/v1/cases/{case_id}/run", response_model=RunSectionDocument)
def read_run_section(  # noqa: PLR0913 -- identity, two ids, store, blobs, bundle
    actor: Caller,
    case_id: CasePath,
    run: RunQuery,
    conn: Store,
    blobs: Blobs,
    bundle: Methodology,
) -> RunSectionDocument:
    """The case's runs and the displayed run with each node's state.

    The order of the parameters is load-bearing: identity, then the path and
    the query, then the store. Both ids are parsed by `deps`, so a malformed
    case is `CASE_NOT_FOUND` and a malformed run `RUN_NOT_FOUND`, never
    FastAPI's 422 quoting the input back, and neither opens a connection.
    """
    title, standing, live_sources, observed_at = _visible_case(conn, case_id, actor)

    rows = conn.execute(
        "SELECT r.run_id, r.status, r.created_at, p.profile_id, p.selection_id"
        " FROM runs r LEFT JOIN run_routes p ON p.run_id = r.run_id"
        " WHERE r.case_id = %s ORDER BY r.created_at DESC, r.run_id DESC LIMIT %s",
        (case_id, RUNS_MAX + 1),
    ).fetchall()
    notes = [SectionNote.LIST_TRUNCATED] if len(rows) > RUNS_MAX else []
    runs = [_summary(row) for row in rows[:RUNS_MAX]]
    displayed = runs[0] if run is None and runs else None
    if run is not None:
        displayed = next((s for s in runs if s.run_id == run), None)
        displayed = displayed or _displayed_beyond_the_list(conn, case_id, run)

    view = facts = None
    if displayed is not None:
        view, facts, run_notes = _run_view(conn, blobs, bundle, displayed)
        notes.extend(run_notes)
    return RunSectionDocument(
        chrome=Chrome(
            subject=Subject(case_id=case_id, title=title),
            served_role=ServedRole(global_role=actor.role, standing=standing),
            actions=run_actions(actor.role, standing, facts, live_sources),
        ),
        body=RunBody(
            case_id=case_id,
            latest_run_id=runs[0].run_id if runs else None,
            displayed_run_id=None if displayed is None else displayed.run_id,
            runs=runs,
            run=view,
            route_choices=[
                RouteChoice(profile_id=profile, selection_id=selection)
                for profile, selection in sorted(ADAPTER_ROUTES)
            ],
        ),
        observed_at=observed_at,
        observed_empty=not runs,
        status="partial" if notes else "complete",
        notes=notes,
    )


def _visible_case(
    conn: StoreConnection, case_id: UUID, actor: Actor
) -> tuple[str, Standing, int, Any]:
    """The case's title, the caller's live standing, the case's live sources
    and the store's `now()`.

    One query: the membership join is folded into the projection row, so
    visibility costs no round trip of its own, and the rule applied to it is
    `deps.readable`'s. An unknown case and a case the caller may not read are
    the same refusal, or the difference between them is the disclosure.
    """
    row = conn.execute(
        "SELECT c.title, m.standing, now(),"
        " (SELECT count(*) FROM live_sources s WHERE s.case_id = c.case_id)"
        " FROM cases c"
        " LEFT JOIN case_members m ON m.case_id = c.case_id"
        " AND m.user_id = %s AND m.revoked_at IS NULL"
        " WHERE c.case_id = %s",
        (actor.user_id, case_id),
    ).fetchone()
    if row is None:  # no such case: the same private answer as no standing
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    standing = readable(None if row[1] is None else Standing(row[1]))
    return str(row[0]), standing, int(row[3]), row[2]


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
) -> tuple[RunView, RunFacts, list[SectionNote]]:
    run_id = summary.run_id
    pin = load_run_input(conn, run_id)
    gates = [GateView(gate=gate, state=gate_state(conn, run_id, gate)) for gate in Gate]
    work_row = conn.execute(
        "SELECT state, stop_code, cancel_requested_at IS NOT NULL FROM run_work"
        " WHERE run_id = %s",
        (run_id,),
    ).fetchone()
    work = (
        None
        if work_row is None
        else WorkView.model_validate(
            {
                "state": work_row[0],
                "stop_code": work_row[1],
                "cancel_requested": work_row[2],
            }
        )
    )
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
    blocked_by = None
    if route is None:
        notes.append(SectionNote.ROUTE_NOT_PINNED)
    else:
        nodes = _node_views(conn, blobs, bundle, route, summary)
        if summary.status == RunStatus.BLOCKED:
            blocked_by = _blocked_by(conn, route, run_id)
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
        work=work,
        blocked_by=blocked_by,
    )
    facts = RunFacts(
        running=summary.status == "RUNNING",
        route_pinned=route is not None,
        input_pinned=pin is not None,
        this_build=pin is not None
        and (pin.build_id, pin.manifest_sha256, pin.adapter_version)
        == (
            bundle.build_id,
            bundle.manifest_sha256,
            methodology.CANONICAL_ADAPTER_VERSION,
        ),
        # The very predicate approval and start refuse on, so the advertised
        # EVIDENCE_NOT_AVAILABLE cannot drift from the commands'.
        sources_live=pin is not None and sources_live(conn, run_id),
        gates_released=all(g.state is GateState.RELEASED for g in gates),
        adapter_route=route is not None and _adapter_route(route),
        work_state=None if work is None else work.state,
        cancel_requested=work is not None and work.cancel_requested,
    )
    return view, facts, list(dict.fromkeys(notes))


def _blocked_by(
    conn: StoreConnection, route: ResolvedRoute, run_id: UUID
) -> BlockedByView | None:
    """The node whose validated Blocked verdict ended this run, as the
    transition recorded it (§68), or None: a run the frontier emptied (§39) has
    no row, and the document says so by carrying nothing.

    Read, not re-derived -- the store refuses to judge an ended run's answer
    again (`check_attempt`). The module is resolved through the pinned route,
    which is immutable; an attempt at a node the route does not carry is a
    store the pins do not describe, refused as a server fault rather than
    served under a guessed module.
    """
    row = conn.execute(
        "SELECT v.attempt_id, a.route_node_id FROM run_blocking_verdicts v"
        " JOIN run_attempts a USING (attempt_id) WHERE v.run_id = %s",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    node = next((n for n in route.nodes if n.route_node_id == str(row[1])), None)
    if node is None:
        raise Refusal(RefusalCode.ORCHESTRATION_NODE_NOT_IN_ROUTE)
    return BlockedByView(
        route_node_id=node.route_node_id,
        module_id=node.module_id,
        attempt_id=UUID(str(row[0])),
    )


def _adapter_route(route: ResolvedRoute) -> bool:
    """Whether `execution_input` would accept the route's modules and pathway."""
    try:
        require_adapter_route(route)
    except Refusal:
        return False
    return True


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


def _node_view(  # noqa: PLR0913 -- one node of one run document
    route: ResolvedRoute,
    accepted: Mapping[str, NodeResult],
    node: RouteNode,
    states: Mapping[str, NodeState],
    readiness: Mapping[str, str],
    named: NamedObjects | None = None,
) -> NodeView:
    done = states[node.route_node_id] is NodeState.COMPLETE
    unmet = () if done else waiting_on(route, accepted, node.route_node_id)
    if not done and named is not None and node.module_id in named.accepted_ids:
        # A node held for its named object names the edges that could meet it.
        extra = lite_object_unmet(route, accepted, node.module_id, named)
        unmet = (*unmet, *(edge for edge in extra if edge not in unmet))
    answered = {n.module_id for n in route.nodes if n.route_node_id in accepted}
    return NodeView(
        route_node_id=node.route_node_id,
        module_id=node.module_id,
        stage=node.stage,
        state=states[node.route_node_id],
        waiting_on=[EdgeView(source=edge.source, type=edge.type) for edge in unmet],
        # The one QA_GATE in the catalog is `CP-5 -> CP-6`. True while the node
        # waits for the QA source's verdict. Once CP-5 answered anything but
        # `Passed`, nothing is awaited: the node is BLOCKED by that verdict and
        # `waiting_on` still names the edge (F03).
        awaiting_gate=any(
            edge.type is EdgeType.QA_GATE and edge.source not in answered
            for edge in unmet
        ),
        # `.get`, not `[]`: a module the gate has not ruled on has no verdict
        # rather than a false one, and None is that absence on the wire.
        gate_verdict=readiness.get(node.module_id),
    )
