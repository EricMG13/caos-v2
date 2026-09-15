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

**Every run is canonical** (`docs/DECISIONS.md` §42): an artifact is proven
through its host record and nothing else -- an artifact without one refuses
`ARTIFACT_RECORD_MISMATCH`, and none is parsed as claims. Both blobs are read,
the record must bind this Markdown and the identity rebuilt from the store, its
adapter, build, manifest and authority must be the pin's and the bundle's, the
Markdown re-validated must project exactly what the record says, and every
recorded citation must re-anchor in the run's pinned, live sources on exactly
the recorded rectangles. The
sources (`pinned_live_sources`) and the call-time identity (`call_time_identity`)
are the ones `server/deliverable/canonical.py` reads, so both reach the same
verdict, under the proof's codes.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from server import methodology
from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, RouteNode
from server.evidence.citations import (
    AnchoredCitation,
    Citation,
    TokenIndex,
    verify_citations,
)
from server.methodology.bundle import Bundle, verified_bytes
from server.methodology.executor import captured_blocks
from server.methodology.handoff import GATE_MODULE, read_record, validate_markdown
from server.methodology.invocation import (
    accepted_lineage,
    call_time_identity,
    host_identity,
    record_authority_matches,
)
from server.methodology.vendor import VENDOR_MODULE, load_vendor_contract
from server.qualification import Assurance
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import resolved_route
from server.store.run_inputs import load_run_input
from server.store.source_sets import pinned_live_sources


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
    # A canonical run's re-anchored `(module_id, document_sha256, matched_text)`,
    # the module taken from the pin: exactly what this proof proved, so the
    # matrix scores it without a second read the proof never saw.
    anchored: frozenset[tuple[str, str, str]] = frozenset()

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
        "SELECT a.artifact_sha256, t.route_node_id, (a.model, a.generation_id),"
        " (o.model, o.generation_id), o.attempt_id IS NOT NULL,"
        " a.attempt_id, a.record_sha256"
        " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
        " LEFT JOIN call_outcomes o ON o.attempt_id = a.attempt_id"
        " WHERE a.run_id = %s ORDER BY a.created_at",
        (run_id,),
    ).fetchall()
    if not accepted:
        raise Refusal(RefusalCode.ORCHESTRATION_NOTHING_TO_PROVE)

    route = resolved_route(conn, run_id)
    if route is None:
        raise Refusal(RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED)
    module_of = {node.route_node_id: node.module_id for node in route.nodes}
    if any(str(row[1]) not in module_of for row in accepted):
        # Execution reached a node the pin does not carry: the one thing
        # invariant 10 exists to make impossible.
        raise Refusal(RefusalCode.ORCHESTRATION_NODE_NOT_IN_ROUTE)
    pin = load_run_input(conn, run_id)
    if pin is None:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    if (pin.build_id, pin.manifest_sha256, pin.adapter_version) != (
        bundle.build_id,
        bundle.manifest_sha256,
        methodology.CANONICAL_ADAPTER_VERSION,
    ):
        raise Refusal(RefusalCode.ORCHESTRATION_BUILD_MOVED)

    live = pinned_live_sources(conn, run_id)
    captured = captured_blocks(conn, run_id)
    delivered = {s: captured.get(s, frozenset()) for s in live.values()}
    reader = _CanonicalReader(conn, blobs, bundle, route, run_id, live, delivered)
    nodes = {node.route_node_id: node for node in route.nodes}
    citations = 0
    anchored: set[tuple[str, str, str]] = set()
    for row in accepted:
        artifact_sha256, route_node_id, produced, called, recorded = row[:5]
        module_id = module_of[str(route_node_id)]
        _produced_by_its_call(recorded=recorded, produced=produced, called=called)
        attempt_id, record_sha256 = row[5], row[6]
        proven = reader.proven(
            nodes[str(route_node_id)],
            UUID(str(attempt_id)),
            str(artifact_sha256),
            None if record_sha256 is None else str(record_sha256),
        )
        citations += len(proven)
        anchored |= {(module_id, c.document_sha256, c.matched_text) for c in proven}

    # No second vacuity guard here: a record without citations does not
    # decode, so by this line the count cannot be zero. A guard that can never
    # fire reads like a check and is not one.
    return OrchestrationProof(
        run_id=run_id,
        route_digest=_pinned_digest(conn, run_id),
        build_id=bundle.build_id,
        artifacts=len(accepted),
        citations=citations,
        anchored=frozenset(anchored),
    )


def _produced_by_its_call(*, recorded: bool, produced: object, called: object) -> None:
    """The producer is the stored call's, never a configured name."""
    if not recorded:
        raise Refusal(RefusalCode.CALL_OUTCOME_LEGACY)
    if produced != called:
        raise Refusal(RefusalCode.CALL_OUTCOME_CONFLICT)


def _unless_refused[T](call: Callable[[], T]) -> T | None:
    """`call`'s answer, or None when it refused.

    The caller raises its own code outside this handler, so the proof's refusal
    carries no context and no text from the one it replaced.
    """
    try:
        return call()
    except Refusal:
        return None


_CATALOG = "references/CREDIT_OS_V_MODULE_CATALOG_v2.json"


class _CanonicalReader:
    """One canonical run's shared authority: contract, catalog, pinned sources."""

    def __init__(  # noqa: PLR0913 -- one run's store, bundle, pin and sources
        self,
        conn: StoreConnection,
        blobs: BlobStore,
        bundle: Bundle,
        route: ResolvedRoute,
        run_id: UUID,
        live: dict[str, UUID],
        delivered: dict[UUID, frozenset[str]],
    ) -> None:
        self.conn, self.blobs, self.bundle = conn, blobs, bundle
        self.route, self.run_id, self.live = route, run_id, live
        self.delivered = delivered
        # One reading of the token index for the whole proof: records cluster
        # on the same pages of the same sources.
        self.index = TokenIndex()
        self.contract = load_vendor_contract(bundle)
        self.catalog = json.loads(verified_bytes(bundle, VENDOR_MODULE, _CATALOG))

    def proven(
        self,
        node: RouteNode,
        attempt_id: UUID,
        artifact_sha256: str,
        record_sha256: str | None,
    ) -> tuple[AnchoredCitation, ...]:
        """Prove one accepted canonical artifact; the citations it re-anchored.

        `ORCHESTRATION_ARTIFACT_UNREADABLE` for a blob whose bytes no longer
        hash to their address; `ORCHESTRATION_BUILD_MOVED` for a record written
        under another adapter, build, manifest or authority;
        `ORCHESTRATION_SOURCE_NOT_PINNED` and `ORCHESTRATION_CITATION_LOST` as
        for claims; `host_identity`'s own code when the store cannot rebuild the
        identity at all (`ATTEMPT_NOT_FOUND` for an attempt without its ordinal,
        `ROUTE_IDENTITY_INVALID` for a blocking input with no accepted artifact),
        raised by it outside any handler and meaning what it means at the call;
        `ARTIFACT_RECORD_MISMATCH` for everything else that does not bind -- a
        missing record, a rebuilt identity the record does not carry, a lineage
        that is not the accepted chain now (an ancestor's record rewritten
        after its consumer was accepted), the projections.
        """
        mismatch = Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        if record_sha256 is None:
            raise mismatch
        markdown = _unless_refused(lambda: self.blobs.get(artifact_sha256))
        stored = _unless_refused(lambda: self.blobs.get(record_sha256))
        if markdown is None or stored is None:
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        bundle, route = self.bundle, self.route
        host = host_identity(
            self.conn,
            bundle,
            run_id=self.run_id,
            route=route,
            node=node,
            attempt_id=attempt_id,
        )
        expected = call_time_identity(
            self.conn, route, host, attempt_id=attempt_id, record=stored
        )
        record = _unless_refused(
            lambda: read_record(
                self.blobs,
                artifact_sha256=artifact_sha256,
                record_sha256=record_sha256,
                expected=expected,
            )
        )
        if record is None:
            raise mismatch
        if not record_authority_matches(
            record, bundle=bundle, module_id=node.module_id
        ):
            raise Refusal(RefusalCode.ORCHESTRATION_BUILD_MOVED)
        upstream = record.identity.upstream
        lineage = _unless_refused(
            lambda: accepted_lineage(
                self.conn, self.blobs, run_id=self.run_id, upstream=upstream
            )
        )
        if lineage is None or lineage != record.lineage:
            raise mismatch
        skill = verified_bytes(bundle, node.module_id, "SKILL.md")
        gate = frozenset(n.module_id for n in route.nodes) - {GATE_MODULE}
        projections = _unless_refused(
            lambda: validate_markdown(
                self.contract,
                self.catalog,
                skill,
                markdown,
                identity=expected,
                gate_expects=gate if node.module_id == GATE_MODULE else frozenset(),
            )
        )
        if projections is None or projections != record.projections:
            raise mismatch
        requests = []
        for citation in record.citations:
            source_id = self.live.get(citation.document_sha256)
            if source_id is None:
                raise Refusal(RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED)
            requests.append(Citation(source_id, citation.page, citation.matched_text))
        anchored = _unless_refused(
            lambda: verify_citations(
                self.conn,
                delivered=self.delivered,
                citations=requests,
                index=self.index,
            )
        )
        # Same quotes, same rectangles, inside the captured blocks; any one
        # refusal loses the record.
        if anchored != list(record.citations):
            raise Refusal(RefusalCode.ORCHESTRATION_CITATION_LOST)
        return tuple(record.citations)


def _pinned_digest(conn: StoreConnection, run_id: UUID) -> str:
    row = conn.execute(
        "SELECT route_digest FROM run_routes WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is None:  # pragma: no cover - read once above, under the same lock
        raise Refusal(RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED)
    return str(row[0])
