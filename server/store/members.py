"""Case standing: who may do what, on which case.

`SYSTEM_SPEC.md` §8. Case standing and global role are separate and both are
rechecked at commit time. This module answers the first question; the recheck
happens inside `server/store/audit.py`'s `governed_write`, because a check
anywhere else is a check at request time wearing a different name.

Standing is ordered. An ADMIN can do what a WRITER can, which is why `requires`
is a floor rather than an equality -- an authority model that demanded the exact
standing would refuse an administrator doing an ordinary thing.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from server.store import StoreConnection


class Standing(StrEnum):
    """What a member may do on one case, least to most."""

    READER = "READER"
    WRITER = "WRITER"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"


# The order the floor is measured against. Written out rather than derived from
# the enum's definition order, so re-ordering the class cannot silently
# re-order authority.
_RANK = {
    Standing.READER: 0,
    Standing.WRITER: 1,
    Standing.APPROVER: 2,
    Standing.ADMIN: 3,
}


def grant(
    conn: StoreConnection, *, case_id: UUID, user_id: UUID, standing: Standing
) -> None:
    """Give a user standing on a case, or replace what they had."""
    conn.execute(
        "INSERT INTO case_members (case_id, user_id, standing)"
        " VALUES (%s, %s, %s)"
        " ON CONFLICT (case_id, user_id) DO UPDATE"
        " SET standing = EXCLUDED.standing, revoked_at = NULL",
        (case_id, user_id, standing.value),
    )


def revoke(conn: StoreConnection, *, case_id: UUID, user_id: UUID) -> None:
    """End a membership. The row stays: a run that already cited this actor's
    approval has to remain explicable."""
    conn.execute(
        "UPDATE case_members SET revoked_at = now()"
        " WHERE case_id = %s AND user_id = %s AND revoked_at IS NULL",
        (case_id, user_id),
    )


def standing_of(
    conn: StoreConnection, *, case_id: UUID, user_id: UUID
) -> Standing | None:
    """Live standing, or None for a stranger and for a revoked member alike."""
    row = conn.execute(
        "SELECT standing FROM case_members"
        " WHERE case_id = %s AND user_id = %s AND revoked_at IS NULL",
        (case_id, user_id),
    ).fetchone()
    return None if row is None else Standing(row[0])


def satisfies(held: Standing | None, required: Standing) -> bool:
    """Whether `held` clears the floor `required` sets."""
    return held is not None and _RANK[held] >= _RANK[required]
