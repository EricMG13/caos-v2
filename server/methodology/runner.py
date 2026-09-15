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
from server.engine.route import ResolvedRoute
from server.engine.runtime import ProviderResult
from server.methodology import CANONICAL_ADAPTER_VERSION
from server.methodology.bundle import Bundle
from server.methodology.canonical import execute_handoff
from server.methodology.envelope import Envelope
from server.methodology.executor import Assignment, execute_module
from server.provider import CompletionProvider
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.outcomes import check_call, execution_reads
from server.store.run_inputs import load_run_input


@dataclass(frozen=True)
class ModuleProvider:
    """A `runtime.Provider` that runs a real module.

    Holds what a module execution needs and the loop does not know about: the
    store, the bundle that is authority, the blob store artifacts are read from
    and written to, the provider that answers, the pinned route and the run.
    What the module reads is derived from the run's pins by `execute_module`,
    never chosen here.
    """

    conn: StoreConnection
    bundle: Bundle
    blobs: BlobStore
    completions: CompletionProvider
    route: ResolvedRoute
    run_id: UUID

    @property
    def model(self) -> str:
        """The configured model identity this provider's calls are billed as."""
        return self.completions.model

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        """Check attempt identity, name the pinned node; `execute_module` checks
        again and derives what the module reads."""
        with execution_reads(self.conn):
            check_call(
                self.conn,
                attempt_id=attempt_id,
                run_id=self.run_id,
                route_node_id=route_node_id,
            )
            pin = load_run_input(self.conn, self.run_id)
        nodes = [
            n
            for n in self.route.nodes
            if (n.route_node_id, n.module_id) == (route_node_id, module_id)
        ]
        if len(nodes) != 1 or pin is None:
            raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
        assignment = Assignment(
            module_id, self.run_id, nodes[0], self.route, attempt_id
        )
        # The pinned adapter chooses the executor (§42.1); each executor
        # refuses a pin of the other adapter again under its own read unit.
        if pin.adapter_version == CANONICAL_ADAPTER_VERSION:
            handoff = execute_handoff(
                self.conn,
                self.bundle,
                self.blobs,
                assignment=assignment,
                provider=self.completions,
            )
            # Billed before analysis; a write failing here accepts nothing.
            stored: tuple[str, str] | None = None
            try:
                markdown = self.blobs.put(handoff.markdown)
                stored = markdown, self.blobs.put(handoff.record)
            except (OSError, Refusal):
                pass  # raised below, outside the handler: no context carried
            if stored is None:
                raise Refusal(RefusalCode.STORE_UNAVAILABLE)
            artifact, record = stored
            return ProviderResult(
                artifact_sha256=artifact,
                charge=handoff.charge,
                model=handoff.model,
                generation_id=handoff.generation_id,
                record_sha256=record,
                diagnostic_sha256=handoff.diagnostic_sha256,
            )
        outcome = execute_module(
            self.conn,
            self.bundle,
            self.blobs,
            assignment=assignment,
            provider=self.completions,
        )
        return ProviderResult(
            artifact_sha256=self.blobs.put(canonical(outcome.envelope)),
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
            "content_to_module_map": [
                {
                    "module_id": row.module_id,
                    "readiness_status": row.readiness_status,
                    "readiness_effect": row.readiness_effect.value,
                }
                for row in sorted(envelope.readiness, key=lambda row: row.module_id)
            ],
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
        }
        # Only the QA gate source carries it, so every other artifact's bytes
        # (and digest) are unchanged.
        | ({} if envelope.qa_status is None else {"qa_status": envelope.qa_status}),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
