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
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.events import lock_run

# What a run may spend when its caller names no ceiling. A run with no ceiling
# at all would be invariant 8 with the number left out.
CEILING = Decimal("5.00")


def reserve(conn: StoreConnection, attempt_id: UUID, amount: Decimal) -> None:
    """Set `amount` aside for this attempt, or refuse `BUDGET_CEILING_REACHED`.

    Taken under the run row lock, which is what makes two connections reserving
    at once resolve to one: without it both read the same remaining balance and
    both believe they fit.
    """
    if not isinstance(amount, Decimal):
        raise Refusal(RefusalCode.MONEY_NOT_DECIMAL)

    run_id = _run_of(conn, attempt_id)
    lock_run(conn, run_id)
    if amount > _remaining(conn, run_id):
        conn.commit()  # nothing taken; the lock is not worth holding
        raise Refusal(RefusalCode.BUDGET_CEILING_REACHED)

    conn.execute(
        "INSERT INTO budget_reservations (attempt_id, run_id, amount)"
        " VALUES (%s, %s, %s)",
        (attempt_id, run_id, amount),
    )
    conn.commit()


def remaining(conn: StoreConnection, run_id: UUID) -> Decimal:
    """The run's ceiling less everything reserved against it."""
    return _remaining(conn, run_id)


def reserved_for(conn: StoreConnection, attempt_id: UUID) -> Decimal | None:
    """What this attempt has set aside, or None if it never reserved."""
    row = conn.execute(
        "SELECT amount FROM budget_reservations WHERE attempt_id = %s", (attempt_id,)
    ).fetchone()
    if row is None:
        return None
    reserved: Decimal = row[0]
    return reserved


def _remaining(conn: StoreConnection, run_id: UUID) -> Decimal:
    row = conn.execute(
        "SELECT runs.budget_ceiling"
        " - coalesce(sum(reservations.amount), 0)"
        " FROM runs"
        " LEFT JOIN budget_reservations AS reservations USING (run_id)"
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
