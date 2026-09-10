"""Phase 4: no provider call without a reservation, and every ceiling fails closed.

Invariant 8 (CLAUDE.md): budgets fail closed. Every ceiling refuses the next
operation *before* overspend, and no provider call happens without a reservation
behind it.

`docs/DECISIONS.md` §12 adopts CAOS-Final §21 with this phase: the attempt row is
the call identity, and a retry is a new reservation rather than a reuse of the
old one. That is the price of a provider with no idempotency key, and it is
charged deliberately -- the alternative is a second call believed to be the first.

The reservation commits on its own, before the call. Sharing the acceptance
transaction would mean a crash after the provider completed rolled back the
record of money that was actually spent.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, apply_schema, connect
from server.store.budget import CEILING, remaining, reserve, reserved_for
from server.store.runs import create_case, start_attempt, start_run

CEILING_FOR_TEST = Decimal("1.00")
HALF = Decimal("0.60")


def _run_with_ceiling(conn: StoreConnection, case_id: UUID) -> UUID:
    return start_run(conn, case_id, budget_ceiling=CEILING_FOR_TEST)


def test_a_reservation_reduces_what_remains(
    case: tuple[StoreConnection, UUID],
) -> None:
    conn, case_id = case
    run_id = _run_with_ceiling(conn, case_id)
    conn.commit()
    attempt_id = start_attempt(conn, run_id, "CP-1")

    reserve(conn, attempt_id, Decimal("0.25"))

    assert remaining(conn, run_id) == Decimal("0.75")
    assert reserved_for(conn, attempt_id) == Decimal("0.25")


def test_a_reservation_past_the_ceiling_is_refused_before_it_is_taken(
    case: tuple[StoreConnection, UUID],
) -> None:
    """Refuse *before* overspend, not after. A ceiling checked afterwards is an
    invoice, not a budget."""
    conn, case_id = case
    run_id = _run_with_ceiling(conn, case_id)
    conn.commit()
    first = start_attempt(conn, run_id, "CP-1")
    reserve(conn, first, HALF)
    second = start_attempt(conn, run_id, "CP-2")

    with pytest.raises(Refusal) as caught:
        reserve(conn, second, HALF)

    assert caught.value.code is RefusalCode.BUDGET_CEILING_REACHED
    assert remaining(conn, run_id) == CEILING_FOR_TEST - HALF
    assert reserved_for(conn, second) is None, "a refused reservation is not taken"


def test_a_reservation_of_exactly_what_remains_is_allowed(
    case: tuple[StoreConnection, UUID],
) -> None:
    """The ceiling is a ceiling, not a wall one short of it."""
    conn, case_id = case
    run_id = _run_with_ceiling(conn, case_id)
    conn.commit()
    attempt_id = start_attempt(conn, run_id, "CP-1")

    reserve(conn, attempt_id, CEILING_FOR_TEST)

    assert remaining(conn, run_id) == Decimal("0")


def test_a_float_reservation_is_refused(case: tuple[StoreConnection, UUID]) -> None:
    """Invariant 7 on the other money path. Binary floating point cannot
    represent a cent, and a ceiling compared against one is not a ceiling."""
    conn, case_id = case
    run_id = _run_with_ceiling(conn, case_id)
    conn.commit()
    attempt_id = start_attempt(conn, run_id, "CP-1")

    with pytest.raises(Refusal) as caught:
        reserve(conn, attempt_id, 0.25)  # type: ignore[arg-type]

    assert caught.value.code is RefusalCode.MONEY_NOT_DECIMAL


def test_a_reservation_for_an_unknown_attempt_is_refused(
    case: tuple[StoreConnection, UUID],
) -> None:
    conn, _case_id = case

    with pytest.raises(Refusal) as caught:
        reserve(conn, uuid4(), Decimal("0.25"))

    assert caught.value.code is RefusalCode.ATTEMPT_NOT_FOUND


def test_crash_after_remote_completion_keeps_its_reservation(
    case: tuple[StoreConnection, UUID], empty_database: str
) -> None:
    """The reservation commits before the call, on its own.

    Sharing the acceptance transaction would mean a process that died after the
    provider completed rolled back the record of money that was really spent --
    and the retry would reserve against a ceiling that had forgotten it.
    """
    conn, case_id = case
    run_id = _run_with_ceiling(conn, case_id)
    conn.commit()
    attempt_id = start_attempt(conn, run_id, "CP-1")
    reserve(conn, attempt_id, HALF)

    # The provider completed; the process dies before accepting the artifact.
    with connect(empty_database) as dying:
        dying.execute(
            "INSERT INTO artifacts (attempt_id, artifact_sha256, run_id, case_id)"
            " VALUES (%s, %s, %s, %s)",
            (attempt_id, "d" * 64, run_id, case_id),
        )
        dying.close()

    with connect(empty_database) as restarted:
        assert reserved_for(restarted, attempt_id) == HALF
        assert remaining(restarted, run_id) == CEILING_FOR_TEST - HALF


def test_a_retry_without_provider_idempotency_reserves_again(
    case: tuple[StoreConnection, UUID],
) -> None:
    """`docs/DECISIONS.md` §16: the provider is called with no idempotency key
    and retries are unwanted, so a retry is a new attempt and a new reservation.

    The old one is not released. An indeterminate call may have reached the
    provider and may be billed; releasing its reservation would let the retry
    spend money the run has already committed.
    """
    conn, case_id = case
    run_id = _run_with_ceiling(conn, case_id)
    conn.commit()
    first = start_attempt(conn, run_id, "CP-1")
    reserve(conn, first, Decimal("0.30"))

    # The call was indeterminate -- PROVIDER_UNAVAILABLE. The node is retried.
    retry = start_attempt(conn, run_id, "CP-1")
    reserve(conn, retry, Decimal("0.30"))

    assert first != retry, "a retry is a new attempt row, not a reused one"
    assert reserved_for(conn, first) == Decimal("0.30")
    assert remaining(conn, run_id) == Decimal("0.40"), "both reservations stand"


def test_concurrent_reservations_at_the_ceiling_refuse(
    empty_database: str,
) -> None:
    """Two connections, one ceiling. The run row lock is what makes exactly one
    of them right; without it both read the same remaining and both reserve."""
    with connect(empty_database) as setup:
        apply_schema(setup)
        case_id = create_case(setup, BoundaryText.of("Acme 2026 refinancing"))
        run_id = start_run(setup, case_id, budget_ceiling=CEILING_FOR_TEST)
        setup.commit()
        attempts = [start_attempt(setup, run_id, f"CP-{n}") for n in (1, 2)]

    def take(attempt_id: UUID) -> bool:
        with connect(empty_database) as conn:
            try:
                reserve(conn, attempt_id, HALF)
            except Refusal as refusal:
                assert refusal.code is RefusalCode.BUDGET_CEILING_REACHED
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(take, attempts))

    assert outcomes == [False, True], "exactly one reservation fits under the ceiling"
    with connect(empty_database) as conn:
        assert remaining(conn, run_id) == CEILING_FOR_TEST - HALF


def test_a_run_without_a_stated_ceiling_gets_the_declared_default(
    case: tuple[StoreConnection, UUID],
) -> None:
    """A run with no ceiling at all would be invariant 8 with the number left
    out, so the default is declared beside the code rather than left to a
    caller who may not pass one."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()

    assert remaining(conn, run_id) == CEILING
