"""Reservations. Invariant 8: every ceiling refuses the next operation.

No provider call without a reservation, and the reservation is taken *before* the
call. A ceiling checked afterwards is an invoice.

Two properties are deliberate and both cost money on purpose:

*The reservation commits on its own.* It does not ride the transaction that later
accepts the artifact. A process that died after the provider completed would
otherwise roll back the record of money that was really spent, and the retry
would reserve against a ceiling that had forgotten it.

*Nothing is released.* An indeterminate call may have reached the provider and
may be billed (`docs/DECISIONS.md` §16: `PROVIDER_UNAVAILABLE` leaves the attempt
indeterminate with its reservation). Releasing it would let the retry spend money
the run has already committed. A retry is a new attempt and a new reservation --
the price of a provider with no idempotency key, paid knowingly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import psycopg

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, committed_unit

if TYPE_CHECKING:
    from server.store.work import Lease

# What a run may spend when its caller names no ceiling. A run with no ceiling
# at all would be invariant 8 with the number left out.
CEILING = Decimal("5.00")


def validate_spend(amount: Decimal) -> None:
    """Exact nonnegative spend within PostgreSQL's native numeric envelope.

    These are representation bounds, not economic ceilings. Check before
    adaptation, without rounding or normalizing even zero's supplied exponent.
    """
    if not isinstance(amount, Decimal):
        raise Refusal(RefusalCode.MONEY_NOT_DECIMAL)
    if (
        not amount.is_finite()
        or amount < 0
        or amount.adjusted() >= 131072
        or int(amount.as_tuple().exponent) < -16383
    ):
        raise Refusal(RefusalCode.MONEY_INVALID)


def reserve(
    conn: StoreConnection,
    attempt_id: UUID,
    amount: Decimal,
    *,
    lease: Lease | None = None,
) -> None:
    """Set `amount` aside for this attempt, or refuse `BUDGET_CEILING_REACHED`.

    Taken under the run row lock, which is what makes two connections reserving
    at once resolve to one: without it both read the same remaining balance and
    both believe they fit. Under the same lock the run's lease must be held and
    no cancel requested (brief 4.3 D3).
    """
    with committed_unit(conn):
        _reserve(conn, attempt_id, amount, lease)


def _reserve(
    conn: StoreConnection, attempt_id: UUID, amount: Decimal, lease: Lease | None
) -> None:
    # Both import this module at their top: `outcomes` directly, `work` through it.
    from server.store.outcomes import _require_attempt
    from server.store.work import require_running

    validate_spend(amount)
    if conn.autocommit:
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)
    run_id = _run_of(conn, attempt_id)
    require_running(conn, run_id, lease)
    _require_attempt(conn, attempt_id, run_id)
    if (
        reserved_for(conn, attempt_id) is not None
        or conn.execute(
            "SELECT 1 FROM budget_ledger WHERE attempt_id = %s", (attempt_id,)
        ).fetchone()
    ):
        raise Refusal(RefusalCode.BUDGET_ALREADY_RESERVED)
    if amount > _remaining(conn, run_id):
        raise Refusal(RefusalCode.BUDGET_CEILING_REACHED)
    conn.execute(
        "INSERT INTO budget_reservations (attempt_id, run_id, amount)"
        " VALUES (%s, %s, %s)",
        (attempt_id, run_id, amount),
    )


def remaining(conn: StoreConnection, run_id: UUID) -> Decimal:
    """Ceiling less per-attempt max(reserved, charged); caller owns transaction."""
    try:
        return _remaining(conn, run_id)
    except psycopg.Error:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None


def reserved_for(conn: StoreConnection, attempt_id: UUID) -> Decimal | None:
    """What this attempt has set aside, or None if it never reserved."""
    try:
        row = conn.execute(
            "SELECT amount FROM budget_reservations WHERE attempt_id = %s",
            (attempt_id,),
        ).fetchone()
    except psycopg.Error:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    if row is None:
        return None
    reserved: Decimal = row[0]
    return reserved


def _remaining(conn: StoreConnection, run_id: UUID) -> Decimal:
    row = conn.execute(
        "SELECT runs.budget_ceiling"
        " - coalesce(sum(greatest(reservations.amount, ledger.amount)), 0)"
        " FROM runs"
        " LEFT JOIN run_attempts USING (run_id)"
        " LEFT JOIN budget_reservations AS reservations USING (run_id, attempt_id)"
        " LEFT JOIN budget_ledger AS ledger USING (run_id, attempt_id)"
        " WHERE runs.run_id = %s"
        " GROUP BY runs.budget_ceiling",
        (run_id,),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    left: Decimal = row[0]
    return left


def _run_of(conn: StoreConnection, attempt_id: UUID) -> UUID:
    row = conn.execute(
        "SELECT run_id FROM run_attempts WHERE attempt_id = %s", (attempt_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    return UUID(str(row[0]))
