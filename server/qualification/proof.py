"""`ORCHESTRATION_PROOF`: the one thing the host may assert about itself.

`docs/REBUILD_PLAN.md` Phase 10 defines it as three claims — the pinned
methodology ran as pinned, against the pinned sources, and every citation
re-located. Every one of those is a fact this repository holds the records for,
which is exactly why it is the word the host is allowed to say. The other word
(`QUALIFIED`) is a reviewer's, and nothing here reaches it.

**Re-derived, never read back.** Each claim was already checked once, when the
artifact was written: the route was pinned before execution, the authority was
verified on the bytes at use, the citations were anchored before they reached
the envelope. The value of checking them again is that the store may have moved
since — a source withdrawn, a bundle replaced, a token index rebuilt. A proof
that trusted the recorded answer would attest that something was recorded, which
is not the claim anybody needs.

So the digests the artifacts carry are treated as *expectations*, re-verified
against the store (invariant 3), and the module each node ran is read from the
route pin rather than from the artifact that claims it.

**A proof over nothing is refused.** Three claims about a run with no accepted
artifacts all hold vacuously, and the strongest-looking proof this module could
ever return would be one about a run that never ran. `CLAUDE.md`: a change that
makes an invariant pass vacuously is wrong even with a green suite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from server.blobs import BlobStore
from server.evidence.citations import AnchoredCitation, Citation, verify_citations
from server.methodology.bundle import Bundle, assemble_authority, authority_digest
from server.qualification import Assurance
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import resolved_route


@dataclass(frozen=True, slots=True)
class OrchestrationProof:
    """What the host proved, and how much of it there was to prove.

    The counts are part of the claim rather than decoration: "every citation
    re-located" means nothing without how many there were, and a reader handed
    this needs to see that the proof covered a run that did something.
    """

    run_id: UUID
    route_digest: str
    build_id: str
    artifacts: int
    citations: int

    @property
    def assurance(self) -> Assurance:
        """`ORCHESTRATION_PROOF`, and never the other word.

        Not a field, because a field could be set. This module has no branch
        that returns anything else and no argument that would select one.
        """
        return Assurance.ORCHESTRATION_PROOF


def assert_orchestration_proof(
    conn: StoreConnection, blobs: BlobStore, bundle: Bundle, *, run_id: UUID
) -> OrchestrationProof:
    """Prove the three claims for one run against the store as it is now.

    Refuses with the claim that failed. The codes are kept apart because their
    remedies are: a moved build is a deployment problem, a withdrawn source is a
    governance decision that did what it was supposed to, and a quote that no
    longer locates is a corrupted index.
    """
    # The vacuity guard is the outermost check on purpose. A run that accepted
    # nothing satisfies all three claims trivially, and "it has no pin" would be
    # the less useful of two true answers about a run that never ran.
    accepted = conn.execute(
        "SELECT a.artifact_sha256, t.route_node_id, a.case_id"
        " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
        " WHERE a.run_id = %s ORDER BY a.created_at",
        (run_id,),
    ).fetchall()
    if not accepted:
        raise Refusal(RefusalCode.ORCHESTRATION_NOTHING_TO_PROVE)

    route = resolved_route(conn, run_id)
    if route is None:
        raise Refusal(RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED)
    module_of = {node.route_node_id: node.module_id for node in route.nodes}

    live = _live_sources(conn, UUID(str(accepted[0][2])))
    citations = 0
    for artifact_sha256, route_node_id, _ in accepted:
        module_id = module_of.get(str(route_node_id))
        if module_id is None:
            # Execution reached a node the pin does not carry: the one thing
            # invariant 10 exists to make impossible.
            raise Refusal(RefusalCode.ORCHESTRATION_NODE_NOT_IN_ROUTE)
        envelope = _envelope(blobs, str(artifact_sha256))
        _ran_as_pinned(envelope, bundle, module_id)
        citations += _citations_relocate(conn, envelope, live)

    # No second vacuity guard here: `_citations_relocate` refuses a claim list
    # that is empty and a claim carrying no citations, so by this line the count
    # cannot be zero. A guard that can never fire reads like a check and is not
    # one.
    return OrchestrationProof(
        run_id=run_id,
        route_digest=_pinned_digest(conn, run_id),
        build_id=bundle.build_id,
        artifacts=len(accepted),
        citations=citations,
    )


def _ran_as_pinned(envelope: dict[str, Any], bundle: Bundle, module_id: str) -> None:
    """Claim one: this artifact was produced under the methodology that is here.

    `module_id` comes from the route pin, never from the envelope — an artifact
    naming its own module could name one whose authority happens to match
    (invariant 3: the host owns identity).
    """
    expected = authority_digest(assemble_authority(bundle, module_id))
    if envelope.get("build_id") != bundle.build_id:
        raise Refusal(RefusalCode.ORCHESTRATION_BUILD_MOVED)
    if envelope.get("authority_digest") != expected:
        raise Refusal(RefusalCode.ORCHESTRATION_BUILD_MOVED)


def _citations_relocate(
    conn: StoreConnection, envelope: dict[str, Any], live: dict[str, UUID]
) -> int:
    """Claims two and three: pinned sources, and every quote re-located.

    They are one pass because they are one lookup. A citation names its document
    by digest; resolving that digest through `live_sources` is what makes a
    withdrawn source unprovable, and the resolved id is what the token index is
    then asked to find the quote in.
    """
    claims = envelope.get("claims")
    if not isinstance(claims, list) or not claims:
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)

    found = 0
    for claim in claims:
        if not isinstance(claim, dict):
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        recorded = claim.get("citations")
        if not isinstance(recorded, list) or not recorded:
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        for citation in recorded:
            _relocates(conn, citation, live)
            found += 1
    return found


def _relocates(conn: StoreConnection, citation: object, live: dict[str, UUID]) -> None:
    """One citation, re-derived and compared with what the artifact carries."""
    if not isinstance(citation, dict):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    document_sha256 = citation.get("document_sha256")
    matched_text = citation.get("matched_text")
    page = citation.get("page")
    if not isinstance(document_sha256, str) or not isinstance(matched_text, str):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    if not isinstance(page, int):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)

    source_id = live.get(document_sha256)
    if source_id is None:
        # Withdrawn, or never this case's. Invariant 1 is checked live at every
        # use, and a proof is a use.
        raise Refusal(RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED)

    try:
        [anchored] = verify_citations(
            conn,
            delivered={source_id},
            citations=[
                Citation(source_id=source_id, page=page, matched_text=matched_text)
            ],
        )
    except Refusal:
        # The quote no longer sits where the index can find it. The typed code
        # travels; the quote does not (`CLAUDE.md`: never log document text).
        raise Refusal(RefusalCode.ORCHESTRATION_CITATION_LOST) from None

    if _rectangles(anchored) != citation.get("bboxes"):
        # Located, but not where the artifact says. A proof that stopped at
        # "the quote is on this page" would accept a rectangle drawn over
        # different text, which is invariant 11 with the coordinates removed.
        raise Refusal(RefusalCode.ORCHESTRATION_CITATION_LOST)


def _rectangles(anchored: AnchoredCitation) -> list[list[float]]:
    """The re-derived rectangles in the shape the stored envelope uses."""
    return [[box.page, box.x0, box.y0, box.x1, box.y1] for box in anchored.bboxes]


def _live_sources(conn: StoreConnection, case_id: UUID) -> dict[str, UUID]:
    """Document digest to source id, for the sources this case still holds.

    Read through `live_sources`, so a withdrawn source is simply absent rather
    than something this function has to remember to exclude.
    """
    rows = conn.execute(
        "SELECT document_sha256, source_id FROM live_sources WHERE case_id = %s",
        (case_id,),
    ).fetchall()
    return {str(row[0]): UUID(str(row[1])) for row in rows}


def _pinned_digest(conn: StoreConnection, run_id: UUID) -> str:
    row = conn.execute(
        "SELECT route_digest FROM run_routes WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is None:  # pragma: no cover - read once above, under the same lock
        raise Refusal(RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED)
    return str(row[0])


def _envelope(blobs: BlobStore, artifact_sha256: str) -> dict[str, Any]:
    """The stored artifact, as the host wrote it. Bytes that are not an envelope
    prove nothing, and their content never reaches the refusal."""
    try:
        decoded = json.loads(blobs.get(artifact_sha256))
    except (ValueError, Refusal):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE) from None
    if not isinstance(decoded, dict):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    return decoded
