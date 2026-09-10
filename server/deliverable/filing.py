"""Opinion, freeze, filing, receipt -- the host's own chain around the page.

`SYSTEM_SPEC.md` §7. The analyst signs an opinion on the exact saved revision;
freeze refuses without a current sign-off and refuses a narrative asserting an
uncited figure; filing refuses the opinion signer *and* the freeze actor, and
writes an immutable detached receipt.

The independence rule is the reason this module exists rather than being three
store calls. `APPROVER_NOT_INDEPENDENT` is not a permission check -- the filer
may well have ADMIN standing. It is a check that the person filing is not the
person who signed or the person who froze, because a chain where one actor can
occupy every role records a decision nobody independently reviewed.

The opinion binds an exact revision by digest. Signing "the current draft" would
bind whatever the draft became, which is the failure invariant 5 names for
digest-bound gates and which applies here for the same reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import GovernedAction, governed_write
from server.store.members import Standing


@dataclass(frozen=True, slots=True)
class Opinion:
    """One analyst's signature on one exact revision."""

    revision_id: str
    payload_sha256: str
    signed_by: UUID


@dataclass(frozen=True, slots=True)
class Receipt:
    """What filing leaves behind: detached, immutable, and enough to verify."""

    revision_id: str
    payload_sha256: str
    signed_by: UUID
    frozen_by: UUID
    filed_by: UUID
    audit_head: str


def sign_opinion(
    conn: StoreConnection,
    *,
    case_id: UUID,
    actor_id: UUID,
    revision_id: str,
    payload_sha256: str,
) -> None:
    """Sign an opinion on an exact revision, as a governed write.

    The digest is part of the signature. An opinion on "the current draft" binds
    whatever the draft becomes, which is the thing digest-binding exists to stop.
    """
    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="OPINION_SIGNED",
        requires=Standing.APPROVER,
        payload={"revision_id": revision_id, "payload_sha256": payload_sha256},
    )

    def write(connection: StoreConnection) -> None:
        connection.execute(
            "INSERT INTO deliverable_opinions"
            " (revision_id, case_id, payload_sha256, signed_by)"
            " VALUES (%s, %s, %s, %s)",
            (revision_id, case_id, payload_sha256, actor_id),
        )

    governed_write(conn, action, write)


def freeze(
    conn: StoreConnection,
    *,
    case_id: UUID,
    actor_id: UUID,
    revision_id: str,
    payload: bytes,
) -> str:
    """Freeze the signed revision. Returns the payload digest that was frozen.

    Refuses without a current sign-off, and refuses one whose digest is not the
    digest that was signed -- a freeze of different bytes than the ones reviewed
    is the signature applied to something nobody read.
    """
    digest = sha256(payload).hexdigest()
    opinion = _opinion(conn, revision_id)
    if opinion is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_SIGNED)
    if opinion.payload_sha256 != digest:
        raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)

    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="DELIVERABLE_FROZEN",
        requires=Standing.APPROVER,
        payload={"revision_id": revision_id, "payload_sha256": digest},
    )

    def write(connection: StoreConnection) -> None:
        connection.execute(
            "INSERT INTO deliverable_publications"
            " (revision_id, case_id, payload_sha256, frozen_by)"
            " VALUES (%s, %s, %s, %s)",
            (revision_id, case_id, digest, actor_id),
        )

    governed_write(conn, action, write)
    return digest


def file_deliverable(
    conn: StoreConnection, *, case_id: UUID, actor_id: UUID, revision_id: str
) -> Receipt:
    """File a frozen deliverable, refusing anyone already in its chain.

    `APPROVER_NOT_INDEPENDENT` is not about standing: the filer may hold ADMIN.
    It is about a chain in which one actor occupied every role, which records a
    decision nobody independently reviewed.
    """
    opinion = _opinion(conn, revision_id)
    frozen = _frozen(conn, revision_id)
    if opinion is None or frozen is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FROZEN)

    frozen_by, payload_sha256 = frozen
    if actor_id in {opinion.signed_by, frozen_by}:
        raise Refusal(RefusalCode.APPROVER_NOT_INDEPENDENT)

    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="DELIVERABLE_FILED",
        requires=Standing.APPROVER,
        payload={"revision_id": revision_id, "payload_sha256": payload_sha256},
    )

    def write(connection: StoreConnection) -> None:
        connection.execute(
            "UPDATE deliverable_publications SET filed_by = %s, filed_at = now()"
            " WHERE revision_id = %s AND filed_by IS NULL",
            (actor_id, revision_id),
        )

    governed_write(conn, action, write)

    from server.store.audit import audit_head

    return Receipt(
        revision_id=revision_id,
        payload_sha256=payload_sha256,
        signed_by=opinion.signed_by,
        frozen_by=frozen_by,
        filed_by=actor_id,
        audit_head=audit_head(conn, case_id),
    )


def receipt_bytes(receipt: Receipt) -> bytes:
    """The detached receipt, canonical so it can be compared byte for byte."""
    return json.dumps(
        {
            "revision_id": receipt.revision_id,
            "payload_sha256": receipt.payload_sha256,
            "signed_by": str(receipt.signed_by),
            "frozen_by": str(receipt.frozen_by),
            "filed_by": str(receipt.filed_by),
            "audit_head": receipt.audit_head,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _opinion(conn: StoreConnection, revision_id: str) -> Opinion | None:
    row = conn.execute(
        "SELECT revision_id, payload_sha256, signed_by FROM deliverable_opinions"
        " WHERE revision_id = %s ORDER BY signed_at DESC LIMIT 1",
        (revision_id,),
    ).fetchone()
    if row is None:
        return None
    return Opinion(
        revision_id=str(row[0]),
        payload_sha256=str(row[1]),
        signed_by=UUID(str(row[2])),
    )


def _frozen(conn: StoreConnection, revision_id: str) -> tuple[UUID, str] | None:
    row = conn.execute(
        "SELECT frozen_by, payload_sha256 FROM deliverable_publications"
        " WHERE revision_id = %s",
        (revision_id,),
    ).fetchone()
    return None if row is None else (UUID(str(row[0])), str(row[1]))
