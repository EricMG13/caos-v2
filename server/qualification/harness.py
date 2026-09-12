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

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import UUID

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import NodeState, ResolvedRoute, node_states, resolve_route
from server.engine.runtime import Execution, accepted_artifacts, run_route
from server.evidence.ingest import admit_pack
from server.methodology.bundle import Bundle
from server.methodology.runner import ModuleProvider
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
from server.store import RunStatus, StoreConnection
from server.store.budget import CEILING
from server.store.routes import pin_route, resolved_route
from server.store.runs import create_case, run_status, start_run

# The label a case is admitted under. A qualification case is a case like any
# other in the store, which is what lets the proof read it like any other.
_LABEL_LIMIT = 128


@dataclass(frozen=True, slots=True)
class Harness:
    """What every case of a set is run under.

    One thing rather than four loose arguments, for the reason `Execution` is
    one thing rather than two: none of these is meaningful without the others.
    A catalog with no provider resolves routes nobody runs; a provider with no
    estimate is a call invariant 8 forbids; and a bundle that differed between
    cases would make the matrix a comparison of two systems.
    """

    bundle: Bundle
    catalog: Mapping[str, Any]
    completions: CompletionProvider
    estimate: Decimal
    # What the whole set may cost. Each run has its own ceiling (invariant 8);
    # nothing bounded the set until this, and two hundred cases were two
    # hundred routes' worth of calls, each individually within budget.
    ceiling: Decimal


@dataclass(frozen=True, slots=True)
class Unrun:
    """A pinned node that produced no artifact, and the state explaining it.

    The state matters as much as the name: BLOCKED is the route's own rules
    being applied, RUNNABLE is a run that stopped with work still in front of
    it. A list of bare node ids would read the same either way.
    """

    route_node_id: str
    state: NodeState


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


def perform(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    *,
    qualification: QualificationSet,
) -> PerformedSet:
    """Run every case of the set and report what each run did, and the matrix.

    The order is the contract: the set is checked whole, then each case is
    admitted and run, then the matrix is built over the runs this call made.
    Building the matrix from anything else would let a stale run answer for a
    case this set never performed.
    """
    # Measurable first: a case with no documents is unanswerable *because* it
    # is empty, and "it has no documents" is the more useful of two true
    # answers about the same defect.
    assert_measurable(qualification)
    _distinct(qualification)
    _answerable(qualification)
    # Routes too. Resolution is pure and reads no store (invariant 10), so
    # nothing made it wait for a case's turn — and resolving inside the loop
    # meant a bad pathway on the last case of ten was found after nine had been
    # admitted, run and paid for, then discarded with the refusal. Knowable from
    # the catalog and the set alone, so it is answered before anything is spent.
    routes = {
        case.label: resolve_route(harness.catalog, case.profile_id, case.selection_id)
        for case in qualification.cases
    }
    _affordable(qualification, harness)

    # A loop rather than a comprehension: every turn of it admits documents,
    # opens a run and calls a provider, and a line that spends money should
    # look like one.
    performed: list[Performed] = []
    for case in qualification.cases:
        record = _perform_one(conn, blobs, harness, case=case, route=routes[case.label])
        performed.append(record)
        if record.stopped is not None:
            # Stop, having recorded it. Carrying on would be a bet that the
            # refusal was this case's, and the ones that end a run are mostly
            # not: a missing credential, a ceiling reached, a moved bundle all
            # recur on the next case, and each retry costs another run, another
            # reservation `server/store/budget.py` never releases, and — for
            # the refusals that are billable — another charge.
            break

    return PerformedSet(
        performed=tuple(performed),
        # Only over a set that finished — which means every case, and every one
        # of them to the end of its route. A matrix missing the cases after the
        # one that stopped reads as complete; so does a row that says `proven`
        # and `met` about a run that accepted CP-0 and went no further, which is
        # the very confusion `Performed` exists to undo.
        matrix=None
        if any(record.stopped is not None for record in performed)
        else build_matrix(
            conn,
            blobs,
            harness.bundle,
            qualification=qualification,
            runs={record.case_label: record.run_id for record in performed},
        ),
    )


def _affordable(qualification: QualificationSet, harness: Harness) -> None:
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
    if CEILING * len(qualification.cases) > harness.ceiling:
        raise Refusal(RefusalCode.QUALIFICATION_SET_OVER_CEILING)


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
    route: ResolvedRoute,
) -> Performed:
    """One case: admitted, pinned, run, and recorded.

    The route arrives resolved, from the pass `perform` makes over the whole set
    before it spends anything — so by here an unknown pathway has already been
    refused, and refused without a case row or a run behind it.

    A refusal inside the run is recorded rather than raised, so the cases after
    it are still performed. It is not swallowed: it lands in `stopped` as a
    typed code, and the run it left behind is as recoverable and as fully
    attempted as it would be for any other caller.
    """
    case_id = create_case(conn, BoundaryText.of(case.label, limit=_LABEL_LIMIT))
    source_ids = admit_pack(
        conn, blobs, case_id=case_id, documents=list(case.documents)
    )
    run_id = start_run(conn, case_id)
    conn.commit()

    # Pinned from that same object, then executed from it: resolving twice
    # would make the pin and the execution two answers that merely happen to
    # agree.
    pin_route(conn, run_id, route)

    stopped: RefusalCode | None = None
    try:
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
                    delivered=_delivered(conn, source_ids),
                    route=route,
                    run_id=run_id,
                ),
                harness.estimate,
            ),
        )
    except Refusal as failed:
        # Every durable step of an attempt commits on its own
        # (`server/engine/runtime.py`), so there is nothing half-written here to
        # keep, and the next case starts on a clean transaction.
        conn.rollback()
        stopped = failed.code

    proof: OrchestrationProof | None = None
    refusal: RefusalCode | None = None
    try:
        proof = assert_orchestration_proof(conn, blobs, harness.bundle, run_id=run_id)
    except Refusal as unprovable:
        refusal = unprovable.code

    return Performed(
        case_label=case.label,
        run_id=run_id,
        status=run_status(conn, run_id),
        stopped=stopped,
        proof=proof,
        refusal=refusal,
        unrun=_unrun(conn, blobs, run_id),
    )


def _unrun(conn: StoreConnection, blobs: BlobStore, run_id: UUID) -> tuple[Unrun, ...]:
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
    travels with the name.
    """
    route = resolved_route(conn, run_id)
    if route is None:
        return ()
    states = node_states(route, _accepted(conn, blobs, route, run_id))
    return tuple(
        Unrun(route_node_id=node.route_node_id, state=states[node.route_node_id])
        for node in route.nodes
        if states[node.route_node_id] is not NodeState.COMPLETE
    )


def _accepted(
    conn: StoreConnection, blobs: BlobStore, route: ResolvedRoute, run_id: UUID
) -> dict[str, Any]:
    """What the run accepted, and never a reason to end the set.

    `accepted_artifacts` reads CP-0's body out of the blob store to recover the
    readiness a soft edge turns on, and bytes that will not load raise — which,
    left unguarded here, would take down the whole set from inside the function
    added to keep one bad case from doing that. A run whose artifacts cannot be
    read has already refused its proof; the fallback keeps which nodes are
    COMPLETE exact and gives up only the readiness that separates a BLOCKED
    node from a RESTRICTED one.
    """
    try:
        return accepted_artifacts(conn, blobs, route, run_id)
    except (Refusal, ValueError):
        rows = conn.execute(
            "SELECT t.route_node_id FROM artifacts a"
            " JOIN run_attempts t ON t.attempt_id = a.attempt_id"
            " WHERE a.run_id = %s",
            (run_id,),
        ).fetchall()
        return {str(row[0]): {} for row in rows}


def _delivered(conn: StoreConnection, source_ids: list[UUID]) -> list[tuple[UUID, str]]:
    """Every block of every document this case was admitted with.

    The whole case, because a qualification case is assembled to be answerable
    and withholding part of it would measure the harness rather than the system.
    """
    rows = conn.execute(
        "SELECT source_id, block_id FROM source_blocks"
        " WHERE source_id = ANY(%s) ORDER BY source_id, block_id",
        (source_ids,),
    ).fetchall()
    return [(UUID(str(row[0])), str(row[1])) for row in rows]


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
