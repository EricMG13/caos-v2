"""The qualification set, its answer keys, and the matrix a reviewer reads.

`docs/REBUILD_PLAN.md` Phase 10. A **qualification set** is the immutable cases
and answer keys one verdict is measured against (`CONTEXT.md`); its digest is
one of the six bindings `read_verdict` requires, and this module is where that
digest is computed.

**The matrix reports; it does not conclude.** Comparing a run against an answer
key is mechanical, and the host may do it. Deciding that the comparison is good
enough is a reviewer's signature — `QUALIFIED` is their word, not the host's
(`server/qualification/__init__.py`). So nothing here carries a verdict, a pass
flag or a score: a row states what the host could prove on its own and which
expected citations the run produced, and a reviewer reads the rows.

That is also why a row survives its own failure. An unprovable case is a row
carrying its refusal code, not an exception that ends the matrix: stopping at
the first one would hand a reviewer less than the host knows, and what the
remaining cases did is the next thing they would ask.

**What an answer key can express, and what it cannot.** A key names citations —
which quote, from which document, under which module. That is the strongest key
the canonical handoff's record can be checked against today, because a record
carries projections and citations and not typed figures. A key saying "net
leverage is 4.2x" has nothing to compare against until the record carries the
figure as a number, which is the known-gaps entry this module ships with.

**A canonical run is scored on its records** (`docs/DECISIONS.md` §42.4), and
only on what the proof proved: the proof returns the citations it re-anchored
under the pinned modules, and those are the run's -- nothing is read again, so
an artifact accepted after the proof is not scored, and a source withdrawn since
refuses the row. An unproven canonical run cites nothing. The matrix reports no
status a record projects, so a SCREENING_ONLY record can never reach a reviewer
through it as committee clearance.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.ingest import Document
from server.methodology.bundle import Bundle
from server.qualification.proof import OrchestrationProof, assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import resolved_route
from server.store.run_inputs import RunSubject
from server.store.source_sets import pinned_live_sources

# A case label is authored and reaches a digest; it is a name, not prose.
_LABEL_LIMIT = 128


@dataclass(frozen=True, slots=True)
class ExpectedCitation:
    """One thing a correct run of this case must have cited.

    The document is named by digest rather than by filename, because a
    qualification set outlives any one case's admission of it and a filename is
    not an identity.
    """

    module_id: str
    document_sha256: str
    matched_text: str


@dataclass(frozen=True, slots=True)
class QualificationCase:
    """One case of the set: its inputs, its route, and its answer key.

    Both halves in one object, because `CONTEXT.md` defines a qualification set
    as "the immutable cases and answer keys" and they are useless apart. The
    first draft of this module carried the keys alone, which is why
    `build_matrix` had to be handed a `runs` mapping it could not produce: there
    was nothing here to run.

    `expects` is this case's answer key — the citations a correct run must
    produce.
    """

    label: str
    documents: tuple[Document, ...]
    profile_id: str
    selection_id: str
    expects: tuple[ExpectedCitation, ...]
    # Who and when the run is about. A canonical-adapter route requires one
    # (`pin_run_input`); a claims route leaves it None, as every case did before.
    subject: RunSubject | None = None


@dataclass(frozen=True, slots=True)
class QualificationSet:
    """The immutable cases and answer keys one verdict is measured against."""

    cases: tuple[QualificationCase, ...]


@dataclass(frozen=True, slots=True)
class MatrixRow:
    """One case: what the host proved, and what the run did or did not cite.

    `proven` and `refusal` are the host's own claim about the run (invariant
    terms). `met` and `missed` are the mechanical comparison. Neither is a
    verdict, and there is deliberately no field that combines them into one.
    """

    case_label: str
    proven: bool
    refusal: RefusalCode | None
    met: tuple[ExpectedCitation, ...]
    missed: tuple[ExpectedCitation, ...]


@dataclass(frozen=True, slots=True)
class Matrix:
    """Every case of the set, and what the set and build were when it was built."""

    qualification_set_sha256: str
    build_id: str
    rows: tuple[MatrixRow, ...]


def qualification_set_digest(qualification: QualificationSet) -> str:
    """The digest a verdict binds. Moves when any case or key moves.

    `read_verdict` takes `qualification_set_sha256` on trust — it checks the
    shape, not the contents. What stops a signature outliving the answer keys it
    was given is this: edit any key and the digest no longer names the set in
    front of the reader.

    Order-independent, because two people assembling the same body of cases must
    bind the same digest; a digest that moved with authorship would make the
    set's identity an accident. Labels cross the boundary here, which is where
    they become pinned state.
    """
    assert_measurable(qualification)
    canonical = sorted(_digested(case) for case in qualification.cases)
    return sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _digested(case: QualificationCase) -> list[object]:
    """One case's digested form. A subject is appended only when declared, so a
    set of subject-free cases binds exactly the digest it bound before cases
    could carry one."""
    entry: list[Any] = [
        BoundaryText.of(case.label.strip(), limit=_LABEL_LIMIT).value,
        [case.profile_id, case.selection_id],
        # The inputs, not only the answers. Two sets with identical keys
        # over different documents are different sets, and a verdict binding
        # one must not read as binding the other.
        sorted(
            [document.filename.value, sha256(document.data).hexdigest()]
            for document in case.documents
        ),
        sorted(
            [expect.module_id, expect.document_sha256, expect.matched_text]
            for expect in case.expects
        ),
    ]
    if case.subject is not None:
        subject = case.subject
        entry.append(
            [
                subject.issuer_id,
                subject.issuer_name,
                subject.reporting_period,
                subject.analysis_date,
            ]
        )
    return entry


def build_matrix(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    qualification: QualificationSet,
    runs: Mapping[str, UUID],
) -> Matrix:
    """Every case of the set against the run that covered it.

    Refuses before it reports rather than reporting a matrix nobody can rely on:
    an empty set measures nothing, two keys for one case make "the answer"
    depend on read order, and a case with no run is the vacuous pass in its
    purest form — the row that would have failed is simply not there.
    """
    assert_measurable(qualification)
    labels = [case.label for case in qualification.cases]
    if len(set(labels)) != len(labels):
        raise Refusal(RefusalCode.QUALIFICATION_SET_AMBIGUOUS)
    for label in labels:
        if label not in runs:
            raise Refusal(RefusalCode.QUALIFICATION_RUN_MISSING)

    return Matrix(
        qualification_set_sha256=qualification_set_digest(qualification),
        rows=tuple(
            _row(conn, blobs, bundle, case=case, run_id=runs[case.label])
            for case in qualification.cases
        ),
        # Validate the same manifest again after all proofs and citation reads.
        build_id=bundle.build_id,
    )


def _row(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case: QualificationCase,
    run_id: UUID,
) -> MatrixRow:
    """One case. The proof may fail; the comparison is made either way.

    What a run cited is knowable whether or not the host can vouch for how it
    was produced, and a reviewer looking at an unprovable case still wants to
    see whether it found the right evidence.
    """
    refusal: RefusalCode | None = None
    proof: OrchestrationProof | None = None
    try:
        proof = assert_orchestration_proof(conn, blobs, bundle, run_id=run_id)
    except Refusal as failed:
        refusal = failed.code

    try:
        cited = _cited(conn, run_id, proof=proof)
    except Refusal as unattributed:
        if unattributed.code not in _ROW_REFUSALS:
            raise
        refusal = unattributed.code
        cited = set()
    met = tuple(expect for expect in case.expects if _matches(expect, cited))
    return MatrixRow(
        case_label=case.label,
        proven=refusal is None,
        refusal=refusal,
        met=met,
        missed=tuple(expect for expect in case.expects if expect not in met),
    )


def _matches(expect: ExpectedCitation, cited: set[tuple[str, str, str]]) -> bool:
    """An expectation is met by the same quote, from the same document, under the
    same module. The right quote under the wrong module answers a different
    question and is not this key's answer."""
    return (expect.module_id, expect.document_sha256, expect.matched_text) in cited


# A row's own uncertainty, not a reason to end the matrix: a pin that no longer
# reads, or a proven source withdrawn before its quotes were scored.
_ROW_REFUSALS = frozenset(
    {RefusalCode.ROUTE_IDENTITY_INVALID, RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED}
)


def _cited(
    conn: StoreConnection, run_id: UUID, *, proof: OrchestrationProof | None
) -> set[tuple[str, str, str]]:
    """Every (module, document, quote) this run's proof re-anchored.

    The module is taken from the route pin, as `proof.py` takes it (invariant
    3: the host owns identity). A run with no pin cites nothing, which is a row
    that misses every key; an invalid pin refuses so `_row` records uncertainty.
    A run cites exactly what its `proof` re-anchored, and nothing without one:
    no artifact is read as a claims envelope (§42.1).
    """
    if resolved_route(conn, run_id) is None:
        return set()
    return _proven(conn, run_id, proof)


def _proven(
    conn: StoreConnection, run_id: UUID, proof: OrchestrationProof | None
) -> set[tuple[str, str, str]]:
    """A proven canonical run's anchored quotes, each document still live now.

    Scoring is a use, so a source withdrawn since the proof refuses the row
    `ORCHESTRATION_SOURCE_NOT_PINNED`, as the proof itself would (invariant 1).
    """
    if proof is None:
        return set()
    live = pinned_live_sources(conn, run_id)
    if any(document not in live for _module, document, _quote in proof.anchored):
        raise Refusal(RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED)
    return set(proof.anchored)


def assert_measurable(qualification: QualificationSet) -> None:
    """A set with no cases, a case expecting nothing, or a case with no
    documents: each measures nothing.

    Public because the harness has to apply it *before* it performs a single
    case, and a copy of the rule there would be a second place to keep in step
    with this one.

    It would also match everything, which is the shape of a qualification that
    reads as a pass because it asked no question.
    """
    if not qualification.cases:
        raise Refusal(RefusalCode.QUALIFICATION_SET_EMPTY)
    if any(not case.expects or not case.documents for case in qualification.cases):
        # A case expecting nothing measures nothing; a case with no documents
        # cannot be run and cannot be cited. Both are the same hole.
        raise Refusal(RefusalCode.QUALIFICATION_SET_EMPTY)
