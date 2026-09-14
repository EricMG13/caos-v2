"""The deliverable's canonical payload, read from the store and bound to it.

`docs/DECISIONS.md` §41.2 and §42.4. A canonical artifact's identity is the pair
(`artifact_sha256`, `record_sha256`), and the record is never read back as fact.
Every accepted artifact of the pinned route is read in route order through
`read_record` against the identity the host rebuilds from its pins; its Markdown
is re-validated and must project exactly what the record says; every recorded
citation is re-anchored in the run's pinned evidence and must land on exactly
the recorded rectangles.

The payload carries each pair beside the exact Markdown and record text, so its
digest -- what an opinion signs and a freeze binds -- binds both hashes, and
`verify_package` checks each pair with the standard library alone. Freezing and
verifying re-derive the payload from the store, so a moved hash refuses. The
render stays pure: nothing here is reachable from it.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext, suppress
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import MODEL_MODULE, ResolvedRoute, RouteNode
from server.evidence.citations import Citation, verify_citations
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
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.outcomes import execution_reads
from server.store.routes import resolved_route
from server.store.source_sets import pinned_live_sources

_CATALOG = "references/CREDIT_OS_V_MODULE_CATALOG_v2.json"


@dataclass(frozen=True, slots=True)
class Revision:
    """What the payload says beyond the store: the case, run and analyst text."""

    case_id: UUID
    run_id: UUID
    case_title: BoundaryText
    revision_id: BoundaryText
    narrative: BoundaryText | None = None


def payload_bytes(payload: dict[str, Any]) -> bytes:
    """The payload's one canonical serialisation; its digest is what is signed."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_payload(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    revision: Revision,
    *,
    _in_unit: bool = False,
) -> dict[str, Any]:
    """Every accepted canonical artifact of the run, proven, in route order.

    Owns one read unit. Refuses `RUN_NOT_FOUND` for a run of another case;
    `DELIVERABLE_PAYLOAD_INVALID` for an unpinned route or a pinned node with no
    accepted artifact; `ARTIFACT_RECORD_MISMATCH` when a blob, the binding, the
    lineage, a projection or a rectangle disagrees, or a citation names a
    document that is not among `pinned_live_sources` (withdrawn, re-extracted,
    admitted after the pin, or captured twice with two extractions); a
    citation's own code when it no longer anchors; and whatever `host_identity`
    refuses (`ROUTE_IDENTITY_INVALID` for a node without its CP-0 anchor). No
    refusal carries text.
    """
    run_id = revision.run_id
    with nullcontext() if _in_unit else execution_reads(conn):
        owner = conn.execute("SELECT case_id FROM runs WHERE run_id = %s", (run_id,))
        if owner.fetchone() != (revision.case_id,):
            raise Refusal(RefusalCode.RUN_NOT_FOUND)
        route = resolved_route(conn, run_id)
        rows = {
            str(node): (UUID(str(attempt)), str(artifact), record)
            for node, attempt, artifact, record in conn.execute(
                "SELECT route_node_id, attempt_id, artifact_sha256, record_sha256"
                " FROM artifacts WHERE run_id = %s",
                (run_id,),
            ).fetchall()
        }
        if route is None or any(n.route_node_id not in rows for n in route.nodes):
            raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
        pinned = pinned_live_sources(conn, run_id)
        captured = captured_blocks(conn, run_id)
        reader = _Reader(conn, blobs, bundle, route, pinned, captured)
        # One reading of the accepted pairs for every record's lineage.
        reader.pairs = {
            node: (artifact, None if record is None else str(record))
            for node, (_attempt, artifact, record) in rows.items()
        }
        artifacts = []
        for node in route.nodes:
            attempt, artifact, record_sha = rows[node.route_node_id]
            if record_sha is None:
                raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
            markdown, record = reader.proven(
                run_id, node, attempt, artifact, str(record_sha)
            )
            artifacts.append(
                {
                    "route_node_id": node.route_node_id,
                    "artifact_sha256": artifact,
                    "record_sha256": str(record_sha),
                    "markdown": markdown.decode("utf-8"),
                    "record": record.decode("utf-8"),
                }
            )
    payload: dict[str, Any] = {
        "case_title": revision.case_title.value,
        "revision_id": revision.revision_id.value,
        "run_id": str(run_id),
        "artifacts": artifacts,
    }
    if revision.narrative is not None:
        payload["narrative"] = revision.narrative.value
    return payload


class _Reader:
    """One payload's shared authority: contract, catalog and pinned evidence."""

    def __init__(  # noqa: PLR0913 -- one payload's store, bundle, pin and blocks
        self,
        conn: StoreConnection,
        blobs: BlobStore,
        bundle: Bundle,
        route: ResolvedRoute,
        pinned: dict[str, UUID],
        captured: dict[UUID, frozenset[str]],
    ) -> None:
        self.conn, self.blobs, self.bundle, self.route = conn, blobs, bundle, route
        self.contract = load_vendor_contract(bundle)
        self.catalog = json.loads(verified_bytes(bundle, VENDOR_MODULE, _CATALOG))
        self.pinned = pinned
        self.pairs: dict[str, tuple[str, str | None]] = {}
        # The captured blocks of the pinned live sources: what any node was handed.
        self.delivered = {
            source: captured.get(source, frozenset()) for source in pinned.values()
        }

    def proven(
        self, run_id: UUID, node: RouteNode, attempt: UUID, artifact: str, sha: str
    ) -> tuple[bytes, bytes]:
        """The proven Markdown and record bytes."""
        bundle, route, pinned = self.bundle, self.route, self.pinned
        host = host_identity(
            self.conn, bundle, run_id=run_id, route=route, node=node, attempt_id=attempt
        )
        stored = None
        with suppress(Refusal):  # an unreadable record is `read_record`'s refusal
            stored = self.blobs.get(sha)
        expected = call_time_identity(
            self.conn, route, host, attempt_id=attempt, record=stored
        )
        record = read_record(
            self.blobs, artifact_sha256=artifact, record_sha256=sha, expected=expected
        )
        mismatch = Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        if not record_authority_matches(
            record, bundle=bundle, module_id=node.module_id, verify=True
        ) or any(c.document_sha256 not in pinned for c in record.citations):
            raise mismatch
        upstream = record.identity.upstream
        if record.lineage != accepted_lineage(
            self.conn, self.blobs, run_id=run_id, upstream=upstream, accepted=self.pairs
        ):
            raise mismatch
        markdown = self.blobs.get(artifact)
        gate = frozenset(n.module_id for n in route.nodes) - {
            GATE_MODULE,
            MODEL_MODULE,
        }
        projections = None
        with suppress(Refusal):  # a stored handoff that no longer validates
            projections = validate_markdown(
                self.contract,
                self.catalog,
                verified_bytes(bundle, node.module_id, "SKILL.md"),
                markdown,
                identity=expected,
                gate_expects=gate if node.module_id == GATE_MODULE else frozenset(),
            )
        # Raised outside the handler, so the refusal's context is empty.
        if projections is None or projections != record.projections:
            raise mismatch
        anchored = verify_citations(
            self.conn,
            delivered=self.delivered,
            citations=[
                Citation(pinned[c.document_sha256], c.page, c.matched_text)
                for c in record.citations
            ],
        )
        if tuple(anchored) != record.citations or stored is None:
            raise mismatch
        return markdown, stored


def freeze_canonical(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    revision: Revision,
    *,
    actor_id: UUID,
) -> str:
    """Freeze the payload the store proves now, never a caller's bytes.

    A pair moved since signing re-derives other bytes, so `freeze` refuses
    `DELIVERABLE_MOVED_SINCE_SIGNING` (or the read refuses with its own code).
    """
    from server.deliverable.filing import freeze

    return freeze(
        conn,
        blobs,
        bundle,
        case_id=revision.case_id,
        actor_id=actor_id,
        revision_id=UUID(revision.revision_id.value),
    )


def verify_frozen(  # noqa: PLR0913 -- the revision and the bytes held for it
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case_id: UUID,
    revision_id: UUID,
    payload: bytes,
) -> None:
    """Refuse unless `payload` is this frozen revision and the store still proves it.

    `DELIVERABLE_NOT_FROZEN` without a freeze; `DELIVERABLE_MOVED_SINCE_SIGNING`
    when the bytes are not the frozen digest or no longer re-derive; the read's
    own code when a pair it binds has moved.
    """
    from server.deliverable.revisions import prove_revision

    with execution_reads(conn):
        row = conn.execute(
            "SELECT payload_sha256 FROM deliverable_publications"
            " WHERE case_id = %s AND revision_id = %s",
            (case_id, str(revision_id)),
        ).fetchone()
        if row is None:
            raise Refusal(RefusalCode.DELIVERABLE_NOT_FROZEN)
        if hashlib.sha256(payload).hexdigest() != row[0]:
            raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)
        if (
            prove_revision(
                conn, blobs, bundle, case_id=case_id, revision_id=revision_id
            )
            != payload
        ):
            raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)
