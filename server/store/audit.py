"""Governed writes: authority at the commit, and an audit event beside the state.

Two rules meet here.

*`SYSTEM_SPEC.md` §8 — commit time.* The gap between checking standing and
committing is a real window: a request arrives, the actor is a WRITER, work
happens, their membership is revoked, and the commit lands anyway. So the check
is inside the store call that writes, not in the route that called it.

*`SYSTEM_SPEC.md` §2 — transactional pairing.* A governed write commits its state
and its audit event in one transaction, or neither. The caller's write runs
inside this function's transaction for exactly that reason: it cannot commit on
its own, so it cannot land without its event.

`audit_events` is hash-chained per case under an `audit_chain_heads` lock row.
The chain has no external anchor, so what it gives is *detection*: an entry
edited in place no longer hashes to what the next one says came before it, and a
retained package's head no longer matches the live one.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.members import Standing, satisfies, standing_of

# The first entry's predecessor. A fixed, obviously-not-a-hash value, so the
# start of a chain cannot be confused with a link into one.
GENESIS = "0" * 64


@dataclass(frozen=True, slots=True)
class GovernedAction:
    """What is being done, by whom, on what, and what standing it needs."""

    case_id: UUID
    actor_id: UUID
    action: str
    requires: Standing
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """One link in a case's chain."""

    seq: int
    actor_id: UUID
    action: str
    payload_sha256: str
    previous_sha256: str
    entry_sha256: str
    at: datetime


def governed_write(
    conn: StoreConnection,
    action: GovernedAction,
    write: Callable[[StoreConnection], None],
) -> None:
    """Run `write` and record it, under the actor's live standing.

    `write` receives this transaction and must not commit: the whole point is
    that its state and this function's audit event are one commit or none.
    """
    previous, seq = _lock_head(conn, action.case_id)

    # Inside the transaction that will commit, not at the request that started
    # it. This is the line SYSTEM_SPEC.md section 8 is about.
    if not satisfies(
        standing_of(conn, case_id=action.case_id, user_id=action.actor_id),
        action.requires,
    ):
        conn.rollback()
        raise Refusal(RefusalCode.NOT_AUTHORISED)

    try:
        write(conn)
    except BaseException:
        # Any failure at all, cancellation included. Letting this propagate with
        # the transaction still open leaves the state `write` managed to make
        # sitting in it, ready to be committed by whatever the caller does next
        # -- state that landed without the event recording it, which is the one
        # thing transactional pairing exists to prevent.
        conn.rollback()
        raise

    payload_sha256 = _digest_of(action.payload)
    entry_sha256 = _link(action, seq, previous, payload_sha256)
    conn.execute(
        "INSERT INTO audit_events (case_id, seq, actor_id, action, payload_sha256,"
        " previous_sha256, entry_sha256) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            action.case_id,
            seq,
            action.actor_id,
            action.action,
            payload_sha256,
            previous,
            entry_sha256,
        ),
    )
    conn.execute(
        "INSERT INTO audit_chain_heads (case_id, seq, head_sha256)"
        " VALUES (%s, %s, %s) ON CONFLICT (case_id) DO UPDATE"
        " SET seq = EXCLUDED.seq, head_sha256 = EXCLUDED.head_sha256",
        (action.case_id, seq, entry_sha256),
    )
    conn.commit()


def audit_trail(conn: StoreConnection, case_id: UUID) -> list[AuditEntry]:
    """The case's chain in order."""
    rows = conn.execute(
        "SELECT seq, actor_id, action, payload_sha256, previous_sha256,"
        " entry_sha256, at FROM audit_events WHERE case_id = %s ORDER BY seq",
        (case_id,),
    ).fetchall()
    return [
        AuditEntry(
            seq=int(row[0]),
            actor_id=UUID(str(row[1])),
            action=str(row[2]),
            payload_sha256=str(row[3]),
            previous_sha256=str(row[4]),
            entry_sha256=str(row[5]),
            at=row[6],
        )
        for row in rows
    ]


def audit_head(conn: StoreConnection, case_id: UUID) -> str:
    """The chain's current head, or `GENESIS` for a case with no history."""
    row = conn.execute(
        "SELECT head_sha256 FROM audit_chain_heads WHERE case_id = %s", (case_id,)
    ).fetchone()
    return GENESIS if row is None else str(row[0])


def verify_chain(conn: StoreConnection, case_id: UUID) -> bool:
    """Whether every link still hashes to what the next one expects.

    What detection means without an external anchor: this cannot prove the chain
    was never rewritten wholesale, only that it was not edited in place. The
    other half is comparing a retained package's head against `audit_head`.
    """
    previous = GENESIS
    for entry in audit_trail(conn, case_id):
        if entry.previous_sha256 != previous:
            return False
        recomputed = _hash(
            (
                previous,
                str(case_id),
                str(entry.seq),
                str(entry.actor_id),
                entry.action,
                entry.payload_sha256,
            )
        )
        if recomputed != entry.entry_sha256:
            return False
        previous = entry.entry_sha256
    return True


def _lock_head(conn: StoreConnection, case_id: UUID) -> tuple[str, int]:
    """Take the case's chain lock and return (head, next seq).

    `FOR UPDATE` on the head row is what serialises two governed writes to one
    case: without it both read the same head and both chain onto it, and one of
    the two entries is orphaned from the sequence it claims to extend.
    """
    row = conn.execute(
        "SELECT head_sha256, seq FROM audit_chain_heads WHERE case_id = %s FOR UPDATE",
        (case_id,),
    ).fetchone()
    if row is None:
        return GENESIS, 1
    return str(row[0]), int(row[1]) + 1


def _digest_of(payload: Mapping[str, Any]) -> str:
    """The payload's digest, never the payload. An audit event records that a
    decision was made and what it bound to -- not the document behind it."""
    canonical = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _link(action: GovernedAction, seq: int, previous: str, payload_sha256: str) -> str:
    return _hash(
        (
            previous,
            str(action.case_id),
            str(seq),
            str(action.actor_id),
            action.action,
            payload_sha256,
        )
    )


def _hash(parts: Sequence[str]) -> str:
    """The link. Every part is followed by a separator no part can contain, so
    two different field splits cannot hash to the same value."""
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()
