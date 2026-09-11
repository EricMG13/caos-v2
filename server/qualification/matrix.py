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
the canonical envelope can be checked against today, because an envelope carries
statements and citations and not typed figures (`server/methodology/envelope.py`).
A key saying "net leverage is 4.2x" has nothing to compare against until the
envelope carries the figure as a number, which is the known-gaps entry this
module ships with.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.methodology.bundle import Bundle
from server.qualification.proof import assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import resolved_route

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
class AnswerKey:
    """What one case of the set expects, and the label the matrix reports it by."""

    case_label: str
    expects: tuple[ExpectedCitation, ...]


@dataclass(frozen=True, slots=True)
class QualificationSet:
    """The immutable cases and answer keys one verdict is measured against."""

    keys: tuple[AnswerKey, ...]


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
    _not_empty(qualification)
    canonical = sorted(
        [
            BoundaryText.of(key.case_label.strip(), limit=_LABEL_LIMIT).value,
            sorted(
                [
                    [expect.module_id, expect.document_sha256, expect.matched_text]
                    for expect in key.expects
                ]
            ),
        ]
        for key in qualification.keys
    )
    return sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    _not_empty(qualification)
    labels = [key.case_label for key in qualification.keys]
    if len(set(labels)) != len(labels):
        raise Refusal(RefusalCode.QUALIFICATION_SET_AMBIGUOUS)
    for label in labels:
        if label not in runs:
            raise Refusal(RefusalCode.QUALIFICATION_RUN_MISSING)

    return Matrix(
        qualification_set_sha256=qualification_set_digest(qualification),
        build_id=bundle.build_id,
        rows=tuple(
            _row(conn, blobs, bundle, key=key, run_id=runs[key.case_label])
            for key in qualification.keys
        ),
    )


def _row(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    key: AnswerKey,
    run_id: UUID,
) -> MatrixRow:
    """One case. The proof may fail; the comparison is made either way.

    What a run cited is knowable whether or not the host can vouch for how it
    was produced, and a reviewer looking at an unprovable case still wants to
    see whether it found the right evidence.
    """
    refusal: RefusalCode | None = None
    try:
        assert_orchestration_proof(conn, blobs, bundle, run_id=run_id)
    except Refusal as failed:
        refusal = failed.code

    cited = _cited(conn, blobs, run_id)
    met = tuple(expect for expect in key.expects if _matches(expect, cited))
    return MatrixRow(
        case_label=key.case_label,
        proven=refusal is None,
        refusal=refusal,
        met=met,
        missed=tuple(expect for expect in key.expects if expect not in met),
    )


def _matches(expect: ExpectedCitation, cited: set[tuple[str, str, str]]) -> bool:
    """An expectation is met by the same quote, from the same document, under the
    same module. The right quote under the wrong module answers a different
    question and is not this key's answer."""
    return (expect.module_id, expect.document_sha256, expect.matched_text) in cited


def _cited(
    conn: StoreConnection, blobs: BlobStore, run_id: UUID
) -> set[tuple[str, str, str]]:
    """Every (module, document, quote) this run's accepted artifacts carry.

    The module is taken from the route pin, not from the envelope that claims it
    — the same reason `proof.py` does (invariant 3: the host owns identity). A
    run with no pin cites nothing this function can attribute, which is a row
    that misses every key rather than one that raises.
    """
    route = resolved_route(conn, run_id)
    module_of = (
        {} if route is None else {n.route_node_id: n.module_id for n in route.nodes}
    )
    rows = conn.execute(
        "SELECT a.artifact_sha256, t.route_node_id"
        " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
        " WHERE a.run_id = %s",
        (run_id,),
    ).fetchall()

    cited: set[tuple[str, str, str]] = set()
    for artifact_sha256, route_node_id in rows:
        module_id = module_of.get(str(route_node_id))
        if module_id is None:
            continue
        cited |= _quotes(blobs, str(artifact_sha256), module_id)
    return cited


def _quotes(
    blobs: BlobStore, artifact_sha256: str, module_id: str
) -> set[tuple[str, str, str]]:
    """One artifact's citations. Unreadable bytes cite nothing rather than
    raising: `assert_orchestration_proof` is what judges an artifact, and it has
    already run for this row."""
    try:
        envelope = json.loads(blobs.get(artifact_sha256))
    except (ValueError, Refusal):
        return set()
    if not isinstance(envelope, dict) or not isinstance(envelope.get("claims"), list):
        return set()

    found: set[tuple[str, str, str]] = set()
    for claim in envelope["claims"]:
        if not isinstance(claim, dict) or not isinstance(claim.get("citations"), list):
            continue
        for citation in claim["citations"]:
            if not isinstance(citation, dict):
                continue
            document = citation.get("document_sha256")
            quote = citation.get("matched_text")
            if isinstance(document, str) and isinstance(quote, str):
                found.add((module_id, document, quote))
    return found


def _not_empty(qualification: QualificationSet) -> None:
    """A set with no cases, or a case expecting nothing, measures nothing.

    It would also match everything, which is the shape of a qualification that
    reads as a pass because it asked no question.
    """
    if not qualification.keys:
        raise Refusal(RefusalCode.QUALIFICATION_SET_EMPTY)
    if any(not key.expects for key in qualification.keys):
        raise Refusal(RefusalCode.QUALIFICATION_SET_EMPTY)
