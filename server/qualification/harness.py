"""The harness: a qualification set performed, then reported.

`docs/REBUILD_PLAN.md` Phase 10 names three things — the harness, the answer
keys, and the matrix. This is the first: it admits each case's documents, runs
the route that case declares, and hands `build_matrix` the runs it produced.

**Not a second execution path.** Every case goes through `admit_pack`,
`resolve_route`, `pin_route` and `run_route` — the same calls any other caller
makes, through the same provider seam, under the same reservations and the same
attempt ledger. A qualification run that took a shortcut would be qualifying a
system nobody ships, and the shortcut would be invisible in the matrix it
produced.

**One case, one case row, one run.** Cases are admitted separately rather than
into a shared case, because evidence is delivered per case: two cases in one
would let the first one's documents answer the second one's key, and the matrix
would report a pass nobody earned.

**Refused before anything is spent.** The set is checked whole — every case
answerable, every label distinct — before the first provider call. A set with an
unanswerable key is a defect in the set, and finding it after paying for the
runs tells you the same thing later and more expensively.

**What only the harness can report.** `assert_orchestration_proof` re-derives
its three claims over the artifacts a run *accepted*. That is the strongest true
statement it can make from a run id alone, and it is narrower than "the route
ran": a run that accepted CP-0 and then stopped proves what it accepted, and the
matrix row it feeds reads `proven`. The harness resolved and pinned the route,
so it holds the node list the proof is silent about — a `Performed` carries the
run's own status and the pinned nodes that produced nothing, beside the proof
rather than folded into it.

**A case that stops is recorded, and the set stops.** A change of mind from this
module's first draft, which let a refusal inside a run propagate — but only half
of one. The objection to catching a refusal was that it turns a broken run into
a quiet miss, and that is answered by *where* the refusal goes rather than by
re-raising it: `Performed.stopped` carries the typed code. What re-raising costs
is everything already bought — the records, the proofs, the provider calls
behind them — and the paragraph above with it, since a route that ran to its end
has no unrun nodes to report.

Carrying on past it would be the opposite mistake. The refusals that end a run
are mostly not the case's: a missing credential, a ceiling reached, a moved
bundle recur on every case after it, and each one costs another run, another
reservation `server/store/budget.py` never releases, and — for the refusals that
may have reached the provider — another charge. So the set stops at the first
one and returns what it performed, and `matrix` is None, because a comparison
that omits the cases after the stop reads as complete.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from typing import Any
from uuid import UUID

import psycopg

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import (
    NodeResult,
    NodeState,
    ResolvedRoute,
    node_states,
    resolve_route,
)
from server.engine.runtime import Execution, accepted_artifacts, run_route
from server.evidence.ingest import admit_pack
from server.methodology import CANONICAL_ADAPTER_VERSION, adapter_for
from server.methodology.bundle import Bundle
from server.methodology.runner import ModuleProvider
from server.pricing import ModelPrice, worst_case
from server.provider import CompletionProvider
from server.qualification.matrix import (
    Matrix,
    QualificationCase,
    QualificationSet,
    assert_measurable,
    build_matrix,
)
from server.qualification.proof import OrchestrationProof, assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, rollback_or_close
from server.store.budget import CEILING, validate_spend
from server.store.gates import execution_input
from server.store.outcomes import execution_reads, require_idle
from server.store.routes import pin_route, resolved_route
from server.store.run_inputs import RunInput, pin_run_input, valid_subject
from server.store.runs import create_case, run_status, start_run
from server.store.source_sets import snapshot_source_set

# The label a case is admitted under. A qualification case is a case like any
# other in the store, which is what lets the proof read it like any other.
_LABEL_LIMIT = 128


@dataclass(frozen=True, slots=True)
class Harness:
    """What every case of a set is run under.

    One thing rather than four loose arguments, for the reason `Execution` is
    one thing rather than two: none of these is meaningful without the others.
    A catalog with no provider resolves routes nobody runs; a provider with no
    price is a call invariant 8 forbids; and a bundle that differed between
    cases would make the matrix a comparison of two systems.
    """

    bundle: Bundle
    catalog: Mapping[str, Any]
    completions: CompletionProvider
    price: ModelPrice
    # What the whole set may cost. Each run has its own ceiling (invariant 8);
    # nothing bounded the set until this, and two hundred cases were two
    # hundred routes' worth of calls, each individually within budget.
    ceiling: Decimal


@dataclass(frozen=True, slots=True)
class Attempted:
    """One stored attempt at a node, exactly as the store recorded it.

    `reserved` without `outcome` is a call that may have been made and left no
    record: possible spend. Without a reservation no call was possible. `charged`
    is a known charge on the ledger; an outcome without one is unknown exposure,
    and a charge without an outcome is a record older than `call_outcomes`.
    `model` and `generation_id` are what the call recorded, None when it
    recorded none -- read from the store, never from `Harness`.
    """

    attempt_id: UUID
    reserved: bool
    outcome: bool
    charged: bool
    model: str | None
    generation_id: str | None


@dataclass(frozen=True, slots=True)
class Unrun:
    """A pinned node that produced no artifact, the state explaining it, and
    what was tried.

    The state matters as much as the name: BLOCKED is the route's own rules
    being applied, RUNNABLE is a run that stopped with work still in front of
    it. `attempts` separates a node never reached (empty) from one whose calls
    were attempted, with or without a record or a known charge.
    """

    route_node_id: str
    state: NodeState
    attempts: tuple[Attempted, ...]


@dataclass(frozen=True, slots=True)
class Performed:
    """One case, performed: what the run did and what the host can say about it.

    Four facts, deliberately not summed:

    - `status` — the run's own, read from the store. The proof does not check
      that a run reached COMPLETE, and this is where that is answered.
    - `stopped` — the refusal that ended execution short of the route's end.
      Apart from `refusal` because they fail at different moments: one is the
      run, the other is the host's later reading of what the run left behind.
    - `proof` / `refusal` — exactly one is set. The proof is taken over whatever
      was accepted, whether or not the run finished.
    - `unrun` — the pinned nodes with no accepted artifact.

    A run that stopped after CP-0 with a sound proof is a different thing to a
    reviewer than a run that finished with an unprovable one, and one combined
    flag would tell them apart by losing both.
    """

    case_label: str
    run_id: UUID
    status: RunStatus
    stopped: RefusalCode | None
    proof: OrchestrationProof | None
    refusal: RefusalCode | None
    unrun: tuple[Unrun, ...]


@dataclass(frozen=True, slots=True)
class PerformedSet:
    """A set performed: each case's run, and the matrix over the runs it made.

    The set digest and the build are on the matrix and are not repeated here:
    two copies of one binding are two things that can disagree, and the matrix
    is what a reviewer is handed.

    `matrix` is None when the set stopped before its last case. A matrix is a
    comparison across the whole set, and one built over the cases that happened
    to run before a provider went away would read as complete. The records are
    still here: what was performed is worth keeping even when what it adds up
    to is not yet a measurement.
    """

    performed: tuple[Performed, ...]
    matrix: Matrix | None


@dataclass(frozen=True, slots=True)
class PreparedCase:
    """Expected stored identity; this carrier grants no execution authority."""

    case_label: str
    input: RunInput


def prepare(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    *,
    qualification: QualificationSet,
) -> tuple[PreparedCase, ...]:
    """Prepare committed inputs for external exact-preview gate approval.

    Preparation never provisions actors, approves gates or executes a run.
    Existing helpers commit separately; earlier preparations survive later failure.
    """
    assert_measurable(qualification)
    _distinct(qualification)
    _answerable(qualification)
    routes = [
        resolve_route(harness.catalog, case.profile_id, case.selection_id)
        for case in qualification.cases
    ]
    titles = [
        BoundaryText.of(case.label, limit=_LABEL_LIMIT) for case in qualification.cases
    ]
    _affordable(qualification, harness, routes)
    if not isinstance(harness.bundle, Bundle):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    _subjects(qualification, routes)
    require_idle(conn)
    prepared = []
    try:
        with execution_reads(conn):
            pass  # Verify READ COMMITTED before any durable setup.
        for case, title, route in zip(qualification.cases, titles, routes, strict=True):
            case_id = create_case(conn, title)
            admit_pack(conn, blobs, case_id=case_id, documents=list(case.documents))
            run_id = start_run(conn, case_id)
            conn.commit()
            source = snapshot_source_set(conn, case_id)
            pin_route(conn, run_id, route)
            prepared.append(
                PreparedCase(
                    case.label,
                    pin_run_input(
                        conn,
                        run_id,
                        source.version,
                        harness.bundle,
                        subject=case.subject,
                    ),
                )
            )
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    return tuple(prepared)


def perform(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    *,
    qualification: QualificationSet,
    prepared: tuple[PreparedCase, ...] | None = None,
) -> PerformedSet:
    """Execute externally approved prepared inputs, then report their runs."""
    if (
        prepared is None
        or type(prepared) is not tuple
        or not isinstance(harness.bundle, Bundle)
    ):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    # Measurable first: a case with no documents is unanswerable *because* it
    # is empty, and "it has no documents" is the more useful of two true
    # answers about the same defect.
    assert_measurable(qualification)
    _distinct(qualification)
    _answerable(qualification)
    if len(prepared) != len(qualification.cases) or any(
        type(item) is not PreparedCase
        or type(item.input) is not RunInput
        or type(item.case_label) is not str
        or item.case_label != case.label
        or type(item.input.run_id) is not UUID
        or type(item.input.case_id) is not UUID
        for case, item in zip(qualification.cases, prepared, strict=True)
    ):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    if len({item.input.run_id for item in prepared}) != len(prepared) or len(
        {item.input.case_id for item in prepared}
    ) != len(prepared):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    routes = []
    for case, item in zip(qualification.cases, prepared, strict=True):
        with execution_reads(conn):
            routes.append(_eligible(conn, harness, case, item))
    _affordable(qualification, harness, routes)

    # Each turn can purchase work; preserve its stopped record before returning.
    performed: list[Performed] = []
    for case, item in zip(qualification.cases, prepared, strict=True):
        record = _perform_one(conn, blobs, harness, case=case, prepared=item)
        performed.append(record)
        if record.stopped is not None:
            # Stop, having recorded it. Carrying on would be a bet that the
            # refusal was this case's, and the ones that end a run are mostly
            # not: a missing credential, a ceiling reached, a moved bundle all
            # recur on the next case, and each retry costs another run, another
            # reservation `server/store/budget.py` never releases, and — for
            # the refusals that are billable — another charge.
            break

    if any(record.stopped is not None for record in performed):
        return PerformedSet(tuple(performed), None)
    with execution_reads(conn):
        matrix = build_matrix(
            conn,
            blobs,
            harness.bundle,
            qualification=qualification,
            runs={record.case_label: record.run_id for record in performed},
        )
    return PerformedSet(tuple(performed), matrix)


def _eligible(
    conn: StoreConnection,
    harness: Harness,
    case: QualificationCase,
    prepared: PreparedCase,
) -> ResolvedRoute:
    """Compare expectations with current authority inside the caller's owned unit."""
    pin, route = execution_input(conn, prepared.input.run_id, harness.bundle)
    if (
        any(
            type(getattr(pin, f.name)) is not type(getattr(prepared.input, f.name))
            for f in fields(RunInput)
        )
        or pin != prepared.input
    ):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    owner = conn.execute(
        "SELECT c.title,r.budget_ceiling FROM runs r JOIN cases c USING(case_id)"
        " WHERE r.run_id=%s AND c.case_id=%s",
        (pin.run_id, pin.case_id),
    ).fetchone()
    members = conn.execute(
        "SELECT m.filename,m.document_sha256 FROM source_set_members m"
        " WHERE m.case_id=%s AND m.version=%s",
        (pin.case_id, pin.source_version),
    ).fetchall()
    if (
        owner != (BoundaryText.of(case.label, limit=_LABEL_LIMIT).value, CEILING)
        or (route.profile_id, route.selection_id)
        != (case.profile_id, case.selection_id)
        or pin.research_json is not None
        or sorted(members)
        != sorted(
            (d.filename.value, sha256(d.data).hexdigest()) for d in case.documents
        )
    ):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    return route


def _affordable(
    qualification: QualificationSet,
    harness: Harness,
    routes: Sequence[ResolvedRoute],
) -> None:
    """The set's ceiling against the sum of the per-run ceilings.

    Invariant 8 one level up, and the same shape: a ceiling refuses the
    operation that would breach it *before* it happens. Each run opened here
    takes `server.store.budget.CEILING`, so what the set may spend is that times
    the number of cases.

    Compared against the worst case rather than an estimate of the likely one.
    A set admitted because it would *probably* come in under would be a
    forecast, and a budget that fails closed cannot rest on one — the whole
    reason the reservation exists is that the call is billable whether or not
    the guess was good.
    """
    validate_spend(harness.ceiling)
    if Fraction(CEILING) * len(qualification.cases) > Fraction(harness.ceiling):
        raise Refusal(RefusalCode.QUALIFICATION_SET_OVER_CEILING)
    # Every node of a case's route reserves one worst case against that run's
    # ceiling; a route that cannot fit would pay for calls it cannot finish.
    # A floor, not a bound: a refused analysis reserves again.
    call = Fraction(worst_case(harness.price))
    if any(call * len(route.nodes) > Fraction(CEILING) for route in routes):
        raise Refusal(RefusalCode.QUALIFICATION_SET_OVER_CEILING)


def _subjects(qualification: QualificationSet, routes: Sequence[ResolvedRoute]) -> None:
    """Every case's subject is one its pin would accept, checked before any write.

    `pin_run_input` refuses a canonical-adapter route without a subject, and an
    invalid subject, but only as the last step of each case -- after the cases
    ahead of it were created, admitted and pinned. Asked here of the whole set,
    so a set that cannot be pinned writes nothing.
    """
    for case, route in zip(qualification.cases, routes, strict=True):
        canonical = adapter_for(route) == CANONICAL_ADAPTER_VERSION
        # A subject on a claims route would be signed and never used.
        if (case.subject is None) == canonical or (
            case.subject is not None and not valid_subject(case.subject)
        ):
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)


def _distinct(qualification: QualificationSet) -> None:
    """Two cases under one label make "the answer" depend on read order.

    `build_matrix` refuses this too, and only once every case has been paid
    for — which is what the paragraph above promises does not happen. Checked
    here so that promise is true.
    """
    labels = [case.label for case in qualification.cases]
    if len(set(labels)) != len(labels):
        raise Refusal(RefusalCode.QUALIFICATION_SET_AMBIGUOUS)


def _perform_one(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    *,
    case: QualificationCase,
    prepared: PreparedCase,
) -> Performed:
    """Recheck one prepared case, execute it, and retain its typed stopped record."""
    run_id = prepared.input.run_id
    stopped: RefusalCode | None = None
    try:
        with execution_reads(conn):
            route = _eligible(conn, harness, case, prepared)
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(
                ModuleProvider(
                    conn=conn,
                    bundle=harness.bundle,
                    blobs=blobs,
                    completions=harness.completions,
                    route=route,
                    run_id=run_id,
                ),
                harness.price,
                harness.bundle,
            ),
        )
    except Refusal as failed:
        # Every durable step of an attempt commits on its own
        # (`server/engine/runtime.py`), so there is nothing half-written here to
        # keep, and the next case starts on a clean transaction.
        rollback_or_close(conn)
        if conn.closed:
            raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
        stopped = failed.code

    with execution_reads(conn):
        return _record(conn, blobs, harness, prepared, stopped)


def _record(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    prepared: PreparedCase,
    stopped: RefusalCode | None,
) -> Performed:
    run_id = prepared.input.run_id
    proof: OrchestrationProof | None = None
    refusal: RefusalCode | None = None
    try:
        proof = assert_orchestration_proof(conn, blobs, harness.bundle, run_id=run_id)
    except Refusal as unprovable:
        refusal = unprovable.code

    try:
        unrun = _unrun(conn, blobs, harness.bundle, run_id)
    except Refusal as unattributed:
        if unattributed.code is not RefusalCode.ROUTE_IDENTITY_INVALID:
            raise
        proof, refusal, unrun = None, unattributed.code, ()

    return Performed(
        case_label=prepared.case_label,
        run_id=run_id,
        status=run_status(conn, run_id),
        stopped=stopped,
        proof=proof,
        refusal=refusal,
        unrun=unrun,
    )


def _unrun(
    conn: StoreConnection, blobs: BlobStore, bundle: Bundle, run_id: UUID
) -> tuple[Unrun, ...]:
    """The pinned nodes that produced no accepted artifact, in route order.

    The route comes from the pin rather than from the object this module just
    resolved, for the reason `proof.py` and `matrix.py` both re-read it: the
    host owns identity (invariant 3), and a caller's copy of what the store
    said is a claim. No pin means no pinned nodes, which is the literal reading
    and the one the proof has already refused this run for.

    `node_states` is the single source of truth for which nodes are done —
    asking it, and separately asking which `route_node_id` has an artifact,
    is two definitions of "complete" that agree only while no route runs one
    module twice.

    Empty is the whole route having run. A node here is not a failure by itself
    — BLOCKED is the route's own rules being applied — which is why the state
    travels with the name. Invalid route identity means unknown attribution.
    """
    route = resolved_route(conn, run_id)
    if route is None:
        return ()
    states = node_states(route, _accepted(conn, blobs, bundle, route, run_id))
    tried: dict[str, list[Attempted]] = {}
    for node_id, *fact in conn.execute(
        "SELECT t.route_node_id, t.attempt_id, r.attempt_id IS NOT NULL,"
        " o.attempt_id IS NOT NULL, l.attempt_id IS NOT NULL, o.model,"
        " o.generation_id FROM run_attempts t"
        " LEFT JOIN budget_reservations r ON r.attempt_id = t.attempt_id"
        " LEFT JOIN call_outcomes o ON o.attempt_id = t.attempt_id"
        " LEFT JOIN budget_ledger l ON l.attempt_id = t.attempt_id"
        " WHERE t.run_id = %s ORDER BY t.started_at, t.attempt_id",
        (run_id,),
    ).fetchall():
        tried.setdefault(str(node_id), []).append(Attempted(*fact))
    return tuple(
        Unrun(
            route_node_id=node.route_node_id,
            state=states[node.route_node_id],
            attempts=tuple(tried.get(node.route_node_id, ())),
        )
        for node in route.nodes
        if states[node.route_node_id] is not NodeState.COMPLETE
    )


def _accepted(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    route: ResolvedRoute,
    run_id: UUID,
) -> dict[str, NodeResult]:
    """What the run accepted, and never a reason to end the set.

    `accepted_artifacts` reads CP-0's readiness -- a claims body, or a canonical
    record verified under the harness's bundle -- to recover the
    readiness a soft edge turns on, and bytes that will not load raise — which,
    left unguarded here, would take down the whole set from inside the function
    added to keep one bad case from doing that. A run whose artifacts cannot be
    read has already refused its proof; the fallback keeps which nodes are
    COMPLETE exact and gives up only the readiness that separates a BLOCKED
    node from a RESTRICTED one.
    """
    try:
        return accepted_artifacts(conn, blobs, route, run_id, bundle=bundle)
    except (Refusal, ValueError):
        rows = conn.execute(
            "SELECT t.route_node_id FROM artifacts a"
            " JOIN run_attempts t ON t.attempt_id = a.attempt_id"
            " WHERE a.run_id = %s",
            (run_id,),
        ).fetchall()
        return {str(row[0]): NodeResult() for row in rows}


def _answerable(qualification: QualificationSet) -> None:
    """Every key names a document its own case carries.

    Only checkable now that the set holds both halves. Before, a key could name
    any digest at all and the row would simply always miss — indistinguishable
    from a system that failed to find it. A set that no correct run could
    satisfy is a defect in the set, and it is refused before the first call
    rather than after paying for every one of them.
    """
    for case in qualification.cases:
        carried = {sha256(document.data).hexdigest() for document in case.documents}
        if any(expect.document_sha256 not in carried for expect in case.expects):
            raise Refusal(RefusalCode.QUALIFICATION_KEY_UNANSWERABLE)
