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
from server.engine.runtime import ProviderResult
from server.methodology.bundle import Bundle
from server.methodology.envelope import Envelope
from server.methodology.executor import deliver, execute_module
from server.provider import CompletionProvider
from server.store import StoreConnection


@dataclass(frozen=True)
class ModuleProvider:
    """A `runtime.Provider` that runs a real module.

    Holds the four things a module execution needs and the loop does not know
    about: the store to read evidence through, the bundle that is authority, the
    blob store the envelope is written to, and the provider that answers.
    """

    conn: StoreConnection
    bundle: Bundle
    blobs: BlobStore
    completions: CompletionProvider
    delivered: list[tuple[UUID, str]]

    def execute(self, route_node_id: str, module_id: str) -> ProviderResult:
        outcome = execute_module(
            self.conn,
            self.bundle,
            module_id=module_id,
            delivered=deliver(self.conn, self.delivered),
            provider=self.completions,
        )
        return ProviderResult(
            artifact_sha256=self.blobs.put(canonical(outcome.envelope)),
            # What the call reported, not what the run set aside for it.
            charge=outcome.charge,
            model=outcome.model,
            generation_id=outcome.generation_id,
        )


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
            "claims_refused": envelope.claims_refused,
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
