"""Where the frontier loop meets a real module.

Phase 4 built a loop that asked a `Provider` for an artifact and a charge. Phase 5
built the thing that actually produces one: verified authority, a provider call,
a canonical envelope, citations anchored in the host's token index. This is the
join `docs/REBUILD_PLAN.md` owes as
`test_the_loop_charges_what_the_provider_reported`.

The charge is the one the provider reported, never the estimate. They are
different numbers answering different questions: the estimate is what the run set
aside before the call so the ceiling could be checked (invariant 8), and the
charge is what the call cost. A ledger recording the estimate would reconcile
perfectly against itself and tell nobody what was spent.

What is stored as the artifact is the *host's* envelope, serialised canonically
and addressed by its digest -- not the provider's body, which was untrusted JSON
the host has already replaced (invariant 3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from server.blobs import BlobStore
from server.engine.route import GATE_MODULE, ResolvedRoute, predecessors
from server.engine.runtime import ProviderResult, artifact_digests
from server.methodology.bundle import Bundle
from server.methodology.envelope import Envelope
from server.methodology.executor import (
    Assignment,
    Upstream,
    UpstreamClaim,
    deliver,
    execute_module,
)
from server.provider import CompletionProvider
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection


@dataclass(frozen=True)
class ModuleProvider:
    """A `runtime.Provider` that runs a real module.

    Holds the seven things a module execution needs and the loop does not know
    about: the store to read evidence through, the bundle that is authority,
    the blob store the envelope is written to, the provider that answers, the
    (source_id, block_id) pairs this node is to receive, the pinned route --
    which is what tells the gate every other module it must cover -- and the
    run the node belongs to.
    """

    conn: StoreConnection
    bundle: Bundle
    blobs: BlobStore
    completions: CompletionProvider
    delivered: list[tuple[UUID, str]]
    # The pin. The gate needs the module ids it must cover, and Phase 11's
    # chain needs each node's predecessors from the same object.
    route: ResolvedRoute
    # The run whose accepted artifacts are this node's upstream. The provider
    # seam is (route_node_id, module_id), so the run the node belongs to has to
    # be held rather than passed.
    run_id: UUID

    def execute(self, route_node_id: str, module_id: str) -> ProviderResult:
        # Only the gate is asked about the rest of the pinned route; deciding
        # so is this method's job because it is the one holding `route` --
        # `execute_module` only ever reads what the assignment already says.
        gate_expects = (
            frozenset(node.module_id for node in self.route.nodes) - {module_id}
            if module_id == GATE_MODULE
            else frozenset()
        )
        assignment = Assignment(
            module_id=module_id,
            delivered=deliver(self.conn, self.delivered),
            gate_expects=gate_expects,
            upstream=self._upstream(module_id),
        )
        outcome = execute_module(
            self.conn, self.bundle, assignment=assignment, provider=self.completions
        )
        return ProviderResult(
            artifact_sha256=self.blobs.put(canonical(outcome.envelope)),
            # What the call reported, not what the run set aside for it.
            charge=outcome.charge,
            model=outcome.model,
            generation_id=outcome.generation_id,
        )

    def _upstream(self, module_id: str) -> tuple[Upstream, ...]:
        """Each direct predecessor's accepted envelope, as the host stored it.

        Read from the store rather than carried in memory: the host owns
        identity (invariant 3), and a run resumed in another process has only
        the store to read -- a caller's copy of what a predecessor said is a
        claim, not the fact this method needs.

        One round trip regardless of how many predecessors this node has:
        `artifact_digests` (`server/engine/runtime.py`) reads every accepted
        artifact of the run in one query -- the same query, and the same row
        set, `accepted_artifacts` reads for the frontier itself, factored into
        one function so the two readers cannot drift out of step with the
        schema under them -- and which rows answer *this* module's
        predecessors is decided in Python against
        `predecessors(self.route, module_id)`. A query per predecessor is
        exactly the shape `docs/AI_CODE_QUALITY.md` measures at ~8x.
        """
        wanted = predecessors(self.route, module_id)
        if not wanted:
            return ()
        # Built once, not once per node: the membership test is inside a
        # comprehension over every node of the route.
        named = set(wanted)
        nodes = {
            node.module_id: node.route_node_id
            for node in self.route.nodes
            if node.module_id in named
        }
        digests = artifact_digests(self.conn, self.run_id)
        upstream: list[Upstream] = []
        for predecessor in wanted:
            # Not every predecessor has run: a soft edge's source may never
            # have been accepted, and that is not an error here -- it is the
            # same "unmet" this route already tolerates for a RESTRICTED node.
            digest = digests.get(nodes.get(predecessor, ""))
            if digest is None:
                continue
            upstream.append(
                Upstream(
                    module_id=predecessor, claims=_stored_claims(self.blobs, digest)
                )
            )
        return tuple(upstream)


def _stored_claims(blobs: BlobStore, artifact_sha256: str) -> tuple[UpstreamClaim, ...]:
    """One predecessor's accepted claims, read the way a proof reads one.

    The same shape as `server/qualification/proof.py`'s `_envelope`, and for the
    same reason: these are bytes the host wrote, and bare indexing into them
    raised `KeyError` or `TypeError` on valid JSON of another shape -- an
    untyped exception crossing the provider seam from inside `_run_node`, after
    the reservation. "This artifact cannot be read" is already named
    `ORCHESTRATION_ARTIFACT_UNREADABLE`, including when the bytes will not load
    at all, so the two readers of one artifact refuse it with one code. Nothing
    document-derived reaches the refusal (`CLAUDE.md`: log the typed code).

    An empty claim list is not refused here, unlike in the proof: this function
    assembles context rather than proving anything, and a predecessor with
    nothing to carry forward is an empty upstream section, not a fault.
    """
    try:
        decoded = json.loads(blobs.get(artifact_sha256))
    except (ValueError, Refusal):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE) from None
    if not isinstance(decoded, dict):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    claims = decoded.get("claims")
    if not isinstance(claims, list):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    return tuple(_stored_claim(claim) for claim in claims)


def _stored_claim(claim: object) -> UpstreamClaim:
    if not isinstance(claim, dict):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    statement = claim.get("statement")
    citations = claim.get("citations")
    if not isinstance(statement, str) or not isinstance(citations, list):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)

    quotes = []
    for citation in citations:
        quote = citation.get("matched_text") if isinstance(citation, dict) else None
        if not isinstance(quote, str):
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        quotes.append(quote)
    return UpstreamClaim(statement=statement, quotes=tuple(quotes))


def canonical(envelope: Envelope) -> bytes:
    """The envelope as stored: sorted keys, no incidental whitespace.

    Content-addressed, so the same envelope has to serialise to the same bytes.
    A dict iteration order that varied would give one artifact two digests and
    make a replay look like a different answer.
    """
    return json.dumps(
        {
            "module_id": envelope.module_id,
            "build_id": envelope.build_id,
            "authority_digest": envelope.authority_digest,
            "content_to_module_map": [
                {
                    "module_id": row.module_id,
                    "readiness_status": row.readiness_status,
                    "readiness_effect": row.readiness_effect.value,
                }
                for row in sorted(envelope.readiness, key=lambda row: row.module_id)
            ],
            "claims": [
                {
                    "statement": claim.statement.value,
                    "citations": [
                        {
                            "document_sha256": citation.document_sha256,
                            "page": citation.page,
                            "matched_text": citation.matched_text,
                            "bboxes": [
                                [box.page, box.x0, box.y0, box.x1, box.y1]
                                for box in citation.bboxes
                            ],
                        }
                        for citation in claim.citations
                    ],
                }
                for claim in envelope.claims
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
