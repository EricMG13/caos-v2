"""Opinion, freeze, filing, receipt -- the host's own chain around the page.

`SYSTEM_SPEC.md` §7. The analyst signs an opinion on the exact saved revision;
freeze refuses without a current sign-off and refuses a narrative asserting an
uncited figure; filing refuses the opinion signer *and* the freeze actor, and
writes an immutable detached receipt.

The independence rule is the reason this module exists rather than being three
store calls. `APPROVER_NOT_INDEPENDENT` is not a permission check -- the filer
may well have ADMIN standing. It is a check that the person filing is not the
person who signed or the person who froze, because a chain where one actor can
occupy every role records a decision nobody independently reviewed. Freeze holds
the signers to the same rule, so a receipt always names three people -- the only
receipt a package verifies.

Every check that reads the chain runs inside the governed write, under the
case's chain lock each of these writes takes. Read before it, a signature
committed in between -- the freezer's or the filer's own -- was one the check
never saw. For the same reason a frozen revision takes no further signature: the
signatures a freeze was checked against are the ones filing reads.

The opinion binds an exact revision by digest. Signing "the current draft" would
bind whatever the draft became, which is the failure invariant 5 names for
digest-bound gates and which applies here for the same reason.

The revision id is `BoundaryText` because it is a label somebody approves, not
bytes somebody compares. NFC-normalised at the boundary, an accented label is
one revision however the caller's keyboard spelled it; as a bare `str` its two
normal forms were two revisions, with a publication row each and "a revision is
frozen once" holding per byte string rather than per label somebody signed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import GovernedAction, governed_write
from server.store.members import Standing


@dataclass(frozen=True, slots=True)
class Opinion:
    """One analyst's signature on one exact revision."""

    revision_id: BoundaryText
    payload_sha256: str
    signed_by: UUID


@dataclass(frozen=True, slots=True)
class Receipt:
    """What filing leaves behind: detached, immutable, and enough to verify."""

    revision_id: BoundaryText
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
    revision_id: BoundaryText,
    payload_sha256: str,
) -> None:
    """Sign an opinion on an exact revision, as a governed write.

    The digest is part of the signature. An opinion on "the current draft" binds
    whatever the draft becomes, which is the thing digest-binding exists to stop.
    A revision this case has frozen refuses `DELIVERABLE_ALREADY_FROZEN`: a
    signature added afterwards signs nothing the freeze was checked against.
    """
    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="OPINION_SIGNED",
        requires=Standing.APPROVER,
        payload={"revision_id": revision_id.value, "payload_sha256": payload_sha256},
    )

    def write(connection: StoreConnection) -> None:
        if _frozen(connection, case_id, revision_id) is not None:
            raise Refusal(RefusalCode.DELIVERABLE_ALREADY_FROZEN)
        connection.execute(
            "INSERT INTO deliverable_opinions"
            " (revision_id, case_id, payload_sha256, signed_by)"
            " VALUES (%s, %s, %s, %s)",
            (revision_id.value, case_id, payload_sha256, actor_id),
        )

    governed_write(conn, action, write)


def freeze(
    conn: StoreConnection,
    *,
    case_id: UUID,
    actor_id: UUID,
    revision_id: BoundaryText,
    payload: bytes,
) -> str:
    """Freeze the signed revision. Returns the payload digest that was frozen.

    Refuses without a current sign-off, and refuses one whose digest is not the
    digest that was signed -- a freeze of different bytes than the ones reviewed
    is the signature applied to something nobody read. Refuses anyone who signed
    the revision (`APPROVER_NOT_INDEPENDENT`), and a revision this case has
    already frozen (`DELIVERABLE_ALREADY_FROZEN`).
    """
    digest = sha256(payload).hexdigest()
    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="DELIVERABLE_FROZEN",
        requires=Standing.APPROVER,
        payload={"revision_id": revision_id.value, "payload_sha256": digest},
    )

    def write(connection: StoreConnection) -> None:
        signatures = _signatures(connection, case_id, revision_id)
        if not signatures:
            raise Refusal(RefusalCode.DELIVERABLE_NOT_SIGNED)
        if signatures[0][1] != digest:
            raise Refusal(RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING)
        if actor_id in {who for who, _digest in signatures}:
            raise Refusal(RefusalCode.APPROVER_NOT_INDEPENDENT)
        frozen = connection.execute(
            "INSERT INTO deliverable_publications"
            " (revision_id, case_id, payload_sha256, frozen_by)"
            " VALUES (%s, %s, %s, %s)"
            " ON CONFLICT (case_id, revision_id) DO NOTHING",
            (revision_id.value, case_id, digest, actor_id),
        ).rowcount
        if not frozen:
            # Raising rolls the transaction back, so the chain holds the one
            # freeze that happened -- not a second entry, and not an untyped
            # UniqueViolation carrying the statement.
            raise Refusal(RefusalCode.DELIVERABLE_ALREADY_FROZEN)

    governed_write(conn, action, write)
    return digest


def file_deliverable(
    conn: StoreConnection, *, case_id: UUID, actor_id: UUID, revision_id: BoundaryText
) -> Receipt:
    """File a frozen deliverable, refusing anyone already in its chain.

    `APPROVER_NOT_INDEPENDENT` is not about standing: the filer may hold ADMIN.
    It is about a chain in which one actor occupied every role, which records a
    decision nobody independently reviewed.

    Refuses `DELIVERABLE_ALREADY_FILED` for a revision somebody has filed. A
    receipt is the record of who filed, so returning one to a second caller
    whose write changed no row names somebody the store does not.
    """
    frozen = _frozen(conn, case_id, revision_id)
    if frozen is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FROZEN)
    # A freeze row is written once and never rewritten, so its digest can be
    # read before the lock. The signatures are read under it, below.
    frozen_by, payload_sha256 = frozen

    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="DELIVERABLE_FILED",
        requires=Standing.APPROVER,
        payload={"revision_id": revision_id.value, "payload_sha256": payload_sha256},
    )
    # The signer the write settles on, handed out of it for the receipt.
    signed_by: list[UUID] = []

    def write(connection: StoreConnection) -> None:
        # One read answers both questions below, so the two cannot disagree.
        signatures = _signatures(connection, case_id, revision_id)
        # Every signature predates the freeze, and the freeze bound the latest:
        # the latest signer of the frozen bytes is the signer it bound.
        signer = next(
            (who for who, digest in signatures if digest == payload_sha256), None
        )
        if signer is None:
            raise Refusal(RefusalCode.DELIVERABLE_NOT_SIGNED)
        # Everyone who signed this revision, not only whoever signed last:
        # checked against the latest signature alone, an earlier signer could
        # file.
        if actor_id in {who for who, _digest in signatures} | {frozen_by}:
            raise Refusal(RefusalCode.APPROVER_NOT_INDEPENDENT)
        filed = connection.execute(
            "UPDATE deliverable_publications SET filed_by = %s, filed_at = now()"
            " WHERE revision_id = %s AND case_id = %s AND filed_by IS NULL",
            (actor_id, revision_id.value, case_id),
        ).rowcount
        if not filed:
            # Somebody filed first. Inside the write rather than as a read
            # beforehand, because the row is only settled under this
            # transaction: two independent filers both pass a precondition and
            # exactly one of them changes a row. Raising here rolls the
            # transaction back, so the chain records the one filing that
            # happened rather than one entry per actor who tried.
            raise Refusal(RefusalCode.DELIVERABLE_ALREADY_FILED)
        signed_by.append(signer)

    governed_write(conn, action, write)

    from server.store.audit import audit_head

    return Receipt(
        revision_id=revision_id,
        payload_sha256=payload_sha256,
        signed_by=signed_by[0],
        frozen_by=frozen_by,
        filed_by=actor_id,
        audit_head=audit_head(conn, case_id),
    )


def receipt_bytes(receipt: Receipt) -> bytes:
    """The detached receipt, canonical so it can be compared byte for byte."""
    return json.dumps(
        {
            "revision_id": receipt.revision_id.value,
            "payload_sha256": receipt.payload_sha256,
            "signed_by": str(receipt.signed_by),
            "frozen_by": str(receipt.frozen_by),
            "filed_by": str(receipt.filed_by),
            "audit_head": receipt.audit_head,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _signatures(
    conn: StoreConnection, case_id: UUID, revision_id: BoundaryText
) -> list[tuple[UUID, str]]:
    """Every signature on this revision of this case, newest first: who signed,
    and the payload digest they signed.

    Scoped to the case, because a revision id is a caller's string rather than
    a key this host minted. Looked up on the string alone, one case's signature
    released another case's freeze -- and the publication row, the audit entry
    and every later filing landed in a case whose members never signed
    anything.
    """
    rows = conn.execute(
        "SELECT signed_by, payload_sha256 FROM deliverable_opinions"
        " WHERE revision_id = %s AND case_id = %s ORDER BY signed_at DESC",
        (revision_id.value, case_id),
    ).fetchall()
    return [(UUID(str(row[0])), str(row[1])) for row in rows]


def _frozen(
    conn: StoreConnection, case_id: UUID, revision_id: BoundaryText
) -> tuple[UUID, str] | None:
    """This case's freeze of this revision. Scoped for the reason `_signatures`
    is."""
    row = conn.execute(
        "SELECT frozen_by, payload_sha256 FROM deliverable_publications"
        " WHERE revision_id = %s AND case_id = %s",
        (revision_id.value, case_id),
    ).fetchone()
    return None if row is None else (UUID(str(row[0])), str(row[1]))
