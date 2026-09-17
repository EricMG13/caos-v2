"""Idempotent governed commands: one receipt per `(actor, scope, key)`.

Task 4.2 decision 6. A command is a governed write (`server/store/audit.py`)
whose unit also records the receipt it answered with, as the unit's last
domain statement. Four predicates decide every retry:

- **Same key, same request** -- `find_receipt` before the unit finds the
  committed receipt and replays its status and body, writing nothing.
- **Same key, different request** -- the stored `request_sha256` differs:
  `IDEMPOTENCY_KEY_REUSED`, committing nothing.
- **Concurrent twins** -- under a case scope the twin waits at the case lock
  and the in-unit lookup finds the first commit's receipt. Under the nil scope
  (create case) nothing is shared but the primary key: the twin's
  `INSERT ... ON CONFLICT DO NOTHING` waits for the first transaction, then
  inserts zero rows. Either way the twin's whole unit is rolled back and it
  replays or refuses.
- **A lost commit acknowledgement** -- the unit either committed with its
  receipt or did not; the client's retry finds out which through the lookup.

Refusals commit nothing, so a key is never burned by a refused request. A
revoked member's receipts are kept; the route's visibility check answers their
replay before the lookup is reached.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from server.digest import canonical_digest
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, rollback_or_close
from server.store.audit import GovernedAction, governed_write

# The scope of a command that has no case yet: create case.
NIL_SCOPE = UUID(int=0)
_SUCCESS = frozenset({200, 201, 202})


@dataclass(frozen=True, slots=True)
class StoredReceipt:
    """A committed command's receipt row."""

    command: str
    request_sha256: str
    status: int
    receipt: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CommandResult:
    """What the route answers: the status, the receipt body, and whether this
    request replayed an earlier commit rather than making one."""

    status: int
    receipt: dict[str, Any]
    replayed: bool


class _Twin(Exception):
    """Inside the unit: another request already committed this key."""


def request_digest(
    command: str,
    *,
    case_id: UUID | None,
    run_id: UUID | None,
    gate: str | None,
    body: object,
) -> str:
    """SHA-256 of the canonical JSON of what the request asked for.

    `body` is the validated request in JSON mode (for admission, the
    `[{filename_nfc, sha256}]` list in part order). Keys sorted, no spaces,
    UTF-8, and no NaN, so equal requests digest equally.
    """
    return canonical_digest(
        {
            "command": command,
            "case_id": None if case_id is None else str(case_id),
            "run_id": None if run_id is None else str(run_id),
            "gate": gate,
            "body": body,
        }
    )


def find_receipt(
    conn: StoreConnection, *, actor_id: UUID, scope: UUID, key: UUID
) -> StoredReceipt | None:
    """The committed receipt for this key, if any. One round trip."""
    row = conn.execute(
        "SELECT command, request_sha256, status, receipt FROM command_requests"
        " WHERE actor_id = %s AND scope = %s AND idempotency_key = %s",
        (actor_id, scope, key),
    ).fetchone()
    if row is None:
        return None
    return StoredReceipt(str(row[0]), str(row[1]), int(row[2]), dict(row[3]))


def record_receipt(  # noqa: PLR0913 -- one receipt row, keyword-only
    conn: StoreConnection,
    *,
    actor_id: UUID,
    scope: UUID,
    key: UUID,
    command: str,
    request_sha256: str,
    status: int,
    receipt: Mapping[str, Any],
) -> bool:
    """Insert the receipt in the caller's unit; False when the key is taken.

    `ON CONFLICT DO NOTHING` waits for an in-flight twin holding the same key
    and answers zero rows once it commits. The caller must then roll back its
    whole unit.
    """
    cursor = conn.execute(
        "INSERT INTO command_requests (actor_id, scope, idempotency_key, command,"
        " request_sha256, status, receipt) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT DO NOTHING",
        (actor_id, scope, key, command, request_sha256, status, Jsonb(dict(receipt))),
    )
    return cursor.rowcount == 1


def run_command(  # noqa: PLR0913 -- one command's identity and unit, keyword-only
    conn: StoreConnection,
    *,
    scope: UUID,
    key: UUID,
    command: str,
    request_sha256: str,
    action: GovernedAction,
    write: Callable[[StoreConnection], tuple[int, BaseModel]],
    prepare: Callable[[StoreConnection], None] | None = None,
) -> CommandResult:
    """Replay, refuse, or commit `write` with its audit event and receipt.

    The actor is `action.actor_id`; `scope` is `action.case_id`, or
    `NIL_SCOPE` for create case. `prepare` runs first in the same transaction,
    before the case lock -- create case inserts its case and the creator's
    standing there, so the governed write can lock and check them. `write`
    runs under the case lock and live standing and returns the success status
    and receipt; the receipt is inserted after it and the audit link after
    that, in one commit. A `NOT_AUTHORISED` from the unit (standing lost by
    commit time) answers `CASE_NOT_FOUND`, as every unseen case does.
    """
    if scope not in (action.case_id, NIL_SCOPE):
        raise _Misuse
    row = _Row(action.actor_id, scope, key, command, request_sha256)
    stored = _lookup(conn, row)
    if stored is not None:
        return _replay(conn, stored, request_sha256)

    answered: list[tuple[int, dict[str, Any]]] = []
    governed = replace(
        action, payload={**action.payload, "request_sha256": request_sha256}
    )
    try:
        if prepare is not None:
            _prepare(conn, prepare)
        governed_write(conn, governed, _unit(row, write, answered))
    except _Twin:
        stored = _lookup(conn, row)
        if stored is None:
            rollback_or_close(conn)
            raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
        return _replay(conn, stored, request_sha256)
    except Refusal as refusal:
        if refusal.code is RefusalCode.NOT_AUTHORISED:
            raise Refusal(RefusalCode.CASE_NOT_FOUND) from None
        raise
    [(status, body)] = answered
    return CommandResult(status, body, replayed=False)


@dataclass(frozen=True, slots=True)
class _Row:
    actor_id: UUID
    scope: UUID
    key: UUID
    command: str
    request_sha256: str


class _Misuse(ValueError):
    """A caller bug: a scope other than the action's case or the nil scope, or
    a success status other than 200, 201 or 202."""


def _unit(
    row: _Row,
    write: Callable[[StoreConnection], tuple[int, BaseModel]],
    answered: list[tuple[int, dict[str, Any]]],
) -> Callable[[StoreConnection], None]:
    """The governed write's body: a twin check under the case lock, the domain
    write, then the receipt as its last statement."""

    def unit(inner: StoreConnection) -> None:
        taken = find_receipt(inner, actor_id=row.actor_id, scope=row.scope, key=row.key)
        if taken is not None:
            raise _Twin
        status, receipt = write(inner)
        if status not in _SUCCESS:
            raise _Misuse
        body = receipt.model_dump(mode="json")
        if not record_receipt(
            inner,
            actor_id=row.actor_id,
            scope=row.scope,
            key=row.key,
            command=row.command,
            request_sha256=row.request_sha256,
            status=status,
            receipt=body,
        ):
            raise _Twin
        answered.append((status, body))

    return unit


def _lookup(conn: StoreConnection, row: _Row) -> StoredReceipt | None:
    """`find_receipt` outside a unit: a store fault is refused, never raised
    with psycopg's message."""
    try:
        return find_receipt(conn, actor_id=row.actor_id, scope=row.scope, key=row.key)
    except psycopg.Error:
        rollback_or_close(conn)
    raise Refusal(RefusalCode.STORE_UNAVAILABLE)


def _prepare(conn: StoreConnection, prepare: Callable[[StoreConnection], None]) -> None:
    """Run the pre-lock step; any failure leaves no open unit behind."""
    try:
        prepare(conn)
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise


def _replay(
    conn: StoreConnection, stored: StoredReceipt, request_sha256: str
) -> CommandResult:
    """The stored answer for the same request; a conflict for another. Both
    end the read unit, so a replay commits nothing."""
    rollback_or_close(conn)
    if stored.request_sha256 != request_sha256:
        raise Refusal(RefusalCode.IDEMPOTENCY_KEY_REUSED)
    return CommandResult(stored.status, stored.receipt, replayed=True)
