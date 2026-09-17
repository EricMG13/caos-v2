"""Prove exact stored filing receipts; no reconstructed or latest-draft receipt."""

from hashlib import sha256
from uuid import UUID

from server.blobs import BlobStore
from server.deliverable.filing import (
    Receipt,
    _filing_payload,
    receipt_bytes,
    revision_signatures,
)
from server.deliverable.revisions import prove_revision
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import _digest_of, audit_head, audit_trail, verify_chain


def read_filed_receipt(  # noqa: PLR0913 -- proof authority and exact selection
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case_id: UUID,
    run_id: UUID,
    revision_id: UUID,
) -> bytes:
    """Return proven canonical bytes in the caller's authorized, case-locked unit.

    The caller owns authorization, locking and transaction cleanup, as for
    `prove_revision`. Historical renderer pins remain valid; live source and
    saved-payload authority must still prove. Legacy filings without bytes refuse.
    """
    row = conn.execute(
        "SELECT r.payload_sha256,p.payload_sha256,p.frozen_by,p.filed_by,"
        " p.filed_at,c.receipt_sha256,c.renderer_sha256,c.filed_event_sha256"
        " FROM deliverable_receipts c JOIN deliverable_publications p"
        " USING (case_id,revision_id) JOIN deliverable_revisions r"
        " ON r.case_id=c.case_id AND r.revision_key=c.revision_id"
        " WHERE c.case_id=%s AND c.revision_id=%s AND r.run_id=%s",
        (case_id, str(revision_id), run_id),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FOUND)
    invalid = Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    digest, frozen_digest, freezer, filer, filed_at, receipt_digest, renderer, event = (
        row
    )
    signatures = revision_signatures(conn, case_id, revision_id)
    signers = {who for who, _ in signatures}
    if (
        digest != frozen_digest
        or filer is None
        or filed_at is None
        or not signatures
        or any(signed_digest != digest for _, signed_digest in signatures)
        or freezer in signers
        or filer in signers | {freezer}
    ):
        raise invalid
    receipt = Receipt(
        case_id,
        run_id,
        revision_id,
        digest,
        signatures[0][0],
        freezer,
        filer,
        renderer,
        event,
    )
    data = blobs.get(receipt_digest)
    if data != receipt_bytes(receipt):
        raise invalid
    trail = audit_trail(conn, case_id)
    filed = next((entry for entry in trail if entry.entry_sha256 == event), None)
    if (
        filed is None
        or filed.action != "DELIVERABLE_FILED"
        or filed.actor_id != filer
        or filed.payload_sha256 != _digest_of(_filing_payload(receipt))
        or not verify_chain(conn, case_id)
        or trail[-1].entry_sha256 != audit_head(conn, case_id)
    ):
        raise invalid
    payload = prove_revision(
        conn, blobs, bundle, case_id=case_id, revision_id=revision_id
    )
    if sha256(payload).hexdigest() != digest:
        raise invalid
    return data
