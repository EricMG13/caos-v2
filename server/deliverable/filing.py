"""§57: sign, freeze and file immutable saved revisions under the case lock."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from server.blobs import BlobStore
from server.deliverable.revisions import prove_revision
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import GovernedAction, governed_write
from server.store.members import Standing


@dataclass(frozen=True, slots=True)
class Receipt:
    """Detached identity of the revision, three actors, renderer and filing event."""

    case_id: UUID
    run_id: UUID
    revision_id: UUID
    payload_sha256: str
    signed_by: UUID
    frozen_by: UUID
    filed_by: UUID
    renderer_sha256: str
    filed_event_sha256: str


def _revision(
    conn: StoreConnection, case_id: UUID, revision_id: UUID
) -> tuple[UUID, str]:
    row = conn.execute(
        "SELECT run_id,payload_sha256 FROM deliverable_revisions"
        " WHERE case_id=%s AND revision_id=%s",
        (case_id, revision_id),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FOUND)
    return UUID(str(row[0])), str(row[1])


def sign_opinion(
    conn: StoreConnection, *, case_id: UUID, actor_id: UUID, revision_id: UUID
) -> None:
    """Sign the stored digest; a frozen revision takes no further signature."""
    payload = {"revision_id": str(revision_id)}
    action = GovernedAction(
        case_id, actor_id, "OPINION_SIGNED", Standing.APPROVER, payload
    )

    def write(unit: StoreConnection) -> None:
        _, digest = _revision(unit, case_id, revision_id)
        if _frozen(unit, case_id, revision_id) is not None:
            raise Refusal(RefusalCode.DELIVERABLE_ALREADY_FROZEN)
        payload["payload_sha256"] = digest
        unit.execute(
            "INSERT INTO deliverable_opinions"
            " (revision_id,case_id,payload_sha256,signed_by) VALUES (%s,%s,%s,%s)",
            (str(revision_id), case_id, digest, actor_id),
        )

    governed_write(conn, action, write)


def freeze(  # noqa: PLR0913 -- exact revision and authority for its re-proof
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case_id: UUID,
    actor_id: UUID,
    revision_id: UUID,
) -> str:
    """Re-prove under the write lock, then freeze exactly the signed stored bytes."""
    payload = {"revision_id": str(revision_id)}
    action = GovernedAction(
        case_id, actor_id, "DELIVERABLE_FROZEN", Standing.APPROVER, payload
    )

    def write(unit: StoreConnection) -> None:
        _, digest = _revision(unit, case_id, revision_id)
        if _frozen(unit, case_id, revision_id) is not None:
            raise Refusal(RefusalCode.DELIVERABLE_ALREADY_FROZEN)
        signatures = revision_signatures(unit, case_id, revision_id)
        if not signatures:
            raise Refusal(RefusalCode.DELIVERABLE_NOT_SIGNED)
        if signatures[0][1] != digest:
            raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)
        if actor_id in {who for who, _ in signatures}:
            raise Refusal(RefusalCode.APPROVER_NOT_INDEPENDENT)
        data = prove_revision(
            unit, blobs, bundle, case_id=case_id, revision_id=revision_id
        )
        if sha256(data).hexdigest() != digest:
            raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)
        payload["payload_sha256"] = digest
        unit.execute(
            "INSERT INTO deliverable_publications"
            " (revision_id,case_id,payload_sha256,frozen_by) VALUES (%s,%s,%s,%s)",
            (str(revision_id), case_id, digest, actor_id),
        )

    governed_write(conn, action, write)
    return payload["payload_sha256"]


def file_deliverable(
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    case_id: UUID,
    actor_id: UUID,
    revision_id: UUID,
) -> Receipt:
    """File once, independently of every signer and the freezer, naming this event."""
    payload = {"revision_id": str(revision_id)}
    action = GovernedAction(
        case_id, actor_id, "DELIVERABLE_FILED", Standing.APPROVER, payload
    )
    receipts: list[Receipt] = []
    renderer = sha256(Path(__file__).with_name("render.py").read_bytes()).hexdigest()

    def write(unit: StoreConnection) -> None:
        run_id, digest = _revision(unit, case_id, revision_id)
        frozen = _frozen(unit, case_id, revision_id)
        if frozen is None:
            raise Refusal(RefusalCode.DELIVERABLE_NOT_FROZEN)
        frozen_by, frozen_digest = frozen
        if frozen_digest != digest:
            raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)
        signatures = revision_signatures(unit, case_id, revision_id)
        if not signatures or any(
            signed_digest != digest for _, signed_digest in signatures
        ):
            raise Refusal(RefusalCode.DELIVERABLE_NOT_SIGNED)
        signers = {who for who, _ in signatures}
        if frozen_by in signers or actor_id in signers | {frozen_by}:
            raise Refusal(RefusalCode.APPROVER_NOT_INDEPENDENT)
        filed = unit.execute(
            "UPDATE deliverable_publications SET filed_by=%s,filed_at=now()"
            " WHERE case_id=%s AND revision_id=%s AND filed_by IS NULL",
            (actor_id, case_id, str(revision_id)),
        ).rowcount
        if not filed:
            raise Refusal(RefusalCode.DELIVERABLE_ALREADY_FILED)
        receipt = Receipt(
            case_id,
            run_id,
            revision_id,
            digest,
            signatures[0][0],
            frozen_by,
            actor_id,
            renderer,
            "",
        )
        payload.update(_filing_payload(receipt))
        receipts.append(receipt)

    def persist(unit: StoreConnection, event: str) -> None:
        receipts[0] = replace(receipts[0], filed_event_sha256=event)
        digest = blobs.put(receipt_bytes(receipts[0]))
        unit.execute(
            "INSERT INTO deliverable_receipts"
            " (case_id,revision_id,receipt_sha256,renderer_sha256,filed_event_sha256)"
            " VALUES (%s,%s,%s,%s,%s)",
            (case_id, str(revision_id), digest, renderer, event),
        )

    governed_write(conn, action, write, after_event=persist)
    return receipts[0]


def _filing_payload(receipt: Receipt) -> dict[str, str]:
    """The event binds every receipt field except its own resulting link."""
    return {
        key: str(value)
        for key, value in asdict(receipt).items()
        if key != "filed_event_sha256"
    }


def receipt_bytes(receipt: Receipt) -> bytes:
    """Canonical detached receipt bytes; UUIDs have one wire representation."""
    return json.dumps(
        {key: str(value) for key, value in asdict(receipt).items()},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def revision_signatures(
    conn: StoreConnection, case_id: UUID, revision_id: UUID
) -> list[tuple[UUID, str]]:
    rows = conn.execute(
        "SELECT signed_by,payload_sha256 FROM deliverable_opinions"
        " WHERE revision_id=%s AND case_id=%s ORDER BY signed_at DESC,signed_by",
        (str(revision_id), case_id),
    ).fetchall()
    return [(UUID(str(row[0])), str(row[1])) for row in rows]


def _frozen(
    conn: StoreConnection, case_id: UUID, revision_id: UUID
) -> tuple[UUID, str] | None:
    row = conn.execute(
        "SELECT frozen_by,payload_sha256 FROM deliverable_publications"
        " WHERE revision_id=%s AND case_id=%s",
        (str(revision_id), case_id),
    ).fetchone()
    return None if row is None else (UUID(str(row[0])), str(row[1]))
