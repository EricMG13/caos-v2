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
from server.engine.route import resolve_route
from server.engine.runtime import Execution, run_route
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
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import pin_route
from server.store.runs import create_case, start_run

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


def perform(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    *,
    qualification: QualificationSet,
) -> Matrix:
    """Run every case of the set and report the matrix.

    The order is the contract: the set is checked whole, then each case is
    admitted and run, then the matrix is built over the runs this call made.
    Building the matrix from anything else would let a stale run answer for a
    case this set never performed.
    """
    # Measurable first: a case with no documents is unanswerable *because* it
    # is empty, and "it has no documents" is the more useful of two true
    # answers about the same defect.
    assert_measurable(qualification)
    _answerable(qualification)

    runs: dict[str, UUID] = {
        case.label: _run_one(conn, blobs, harness, case=case)
        for case in qualification.cases
    }
    return build_matrix(
        conn, blobs, harness.bundle, qualification=qualification, runs=runs
    )


def _run_one(
    conn: StoreConnection,
    blobs: BlobStore,
    harness: Harness,
    *,
    case: QualificationCase,
) -> UUID:
    """One case: admitted, pinned, run. Returns the run the matrix will read.

    A refusal inside the run is not caught here. It leaves the run recoverable
    and the attempt recorded, exactly as it would for any other caller, and the
    matrix would report the row as unproven — but a harness that swallowed it
    would turn a broken run into a quiet miss.
    """
    case_id = create_case(conn, BoundaryText.of(case.label, limit=_LABEL_LIMIT))
    source_ids = admit_pack(
        conn, blobs, case_id=case_id, documents=list(case.documents)
    )
    run_id = start_run(conn, case_id)
    conn.commit()

    # Resolved once and pinned, then executed from that same object: invariant
    # 10 is that the route is resolved once, and resolving twice would make the
    # pin and the execution two answers that merely happen to agree.
    route = resolve_route(harness.catalog, case.profile_id, case.selection_id)
    pin_route(conn, run_id, route)
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
            ),
            harness.estimate,
        ),
    )
    return run_id


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
