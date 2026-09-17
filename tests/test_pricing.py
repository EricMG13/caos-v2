"""F06: a reservation is priced from the configured model, conservatively.

Each call's reservation covers that call: the bytes the provider will be sent
as input tokens -- a token is at least one byte, so the bound holds -- and the
output cap as output tokens (Task 8.2, §38). `worst_case`, the same arithmetic
at `MAX_REQUEST_BYTES`, stays as the run's admission check.
Runtime-driven cases run the canonical LITE route (Task 3.1 slice e-2).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from test_runtime import _approved_run, blobs, bundle, route

from server.blobs import BlobStore
from server.engine.route import ResolvedRoute
from server.engine.runtime import Execution, run_route
from server.methodology.bundle import Bundle
from server.pricing import ModelPrice, priced_request, worst_case
from server.provider import MAX_COMPLETION_TOKENS, MAX_REQUEST_BYTES
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserved_for

__all__ = ["blobs", "bundle", "route"]

MODEL = "a-model/for-the-test"
PRICE = ModelPrice(MODEL, Decimal("0.0000001"), Decimal("0.000002"), date(2026, 9, 13))


def test_worst_case_covers_the_request_and_completion_ceilings() -> None:
    assert worst_case(PRICE) == (
        Decimal("0.0000001") * MAX_REQUEST_BYTES
        + Decimal("0.000002") * MAX_COMPLETION_TOKENS
    )


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("input_per_token", Decimal("NaN"), RefusalCode.MONEY_INVALID),
        ("output_per_token", Decimal("-0.1"), RefusalCode.MONEY_INVALID),
        ("output_per_token", 0.1, RefusalCode.MONEY_NOT_DECIMAL),
        ("input_per_token", True, RefusalCode.MONEY_NOT_DECIMAL),
        ("model", "", RefusalCode.PROVIDER_NOT_CONFIGURED),
        ("input_per_token", Decimal("0." + "1" * 1200), RefusalCode.MONEY_INVALID),
    ],
)
def test_invalid_prices_refuse(field: str, value: object, code: RefusalCode) -> None:
    with pytest.raises(Refusal) as caught:
        worst_case(replace(PRICE, **{field: value}))  # type: ignore[arg-type]
    assert caught.value.code is code


def test_a_free_price_refuses_rather_than_reserving_nothing() -> None:
    free = replace(PRICE, input_per_token=Decimal(0), output_per_token=Decimal(0))
    with pytest.raises(Refusal, match=r"^MONEY_INVALID$"):
        worst_case(free)


def test_a_price_for_another_model_refuses_before_any_attempt(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run = _approved_run(conn, case_id, route, bundle, blobs)
    provider = run.provider()
    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run.run_id,
            route=route,
            execution=Execution(provider, replace(PRICE, model="other/model"), bundle),
        )
    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED
    assert provider.calls == []
    assert provider.answers.prompts == []
    assert conn.execute(
        "SELECT count(*) FROM run_attempts WHERE run_id = %s", (run.run_id,)
    ).fetchone() == (0,)


def test_an_overrun_charge_stops_the_next_node_before_its_call(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """A charge above the reservation consumes capacity (Phase 2 budget exit)."""
    conn, case_id = case
    small = ModelPrice(
        MODEL, Decimal(0), Decimal("0.10") / MAX_COMPLETION_TOKENS, PRICE.as_of
    )
    run = _approved_run(conn, case_id, route, bundle, blobs, ceiling=Decimal("1.05"))
    provider = run.provider(charge=Decimal("1.00"))
    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run.run_id,
            route=route,
            execution=Execution(provider, small, bundle),
        )
    assert caught.value.code is RefusalCode.BUDGET_CEILING_REACHED
    assert provider.calls == ["CP-0"]
    assert len(provider.answers.prompts) == 1
    assert conn.execute(
        "SELECT amount FROM budget_ledger WHERE run_id = %s", (run.run_id,)
    ).fetchall() == [(Decimal("1.00"),)]


def test_a_run_ceiling_below_one_worst_case_still_refuses_before_any_attempt(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """Task 8.2 prices each reservation on its own request, so the ceiling is
    no longer met by the first reservation. `worst_case` stays as the run's
    admission check: a run that could not afford one call at the price's worst
    case is refused before an attempt row exists, spending nothing.
    """
    conn, case_id = case
    run = _approved_run(
        conn, case_id, route, bundle, blobs, ceiling=worst_case(PRICE) - Decimal("0.01")
    )
    provider = run.provider()

    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run.run_id,
            route=route,
            execution=Execution(provider, PRICE, bundle),
        )

    assert caught.value.code is RefusalCode.BUDGET_CEILING_REACHED
    assert provider.calls == [] and provider.answers.prompts == []
    assert conn.execute(
        "SELECT count(*) FROM run_attempts WHERE run_id = %s", (run.run_id,)
    ).fetchone() == (0,)
    assert conn.execute(
        "SELECT count(*) FROM budget_reservations WHERE run_id = %s", (run.run_id,)
    ).fetchone() == (0,)


def test_a_reservation_is_priced_on_the_request_not_on_the_byte_ceiling(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """What Task 8.2 replaces `worst_case` per call with (completion O09).

    `PRICE` charges for input, so the byte ceiling and the request diverge:
    each reservation is the priced cost of the bytes the provider was sent,
    strictly below one worst case, and carries the dated price that produced it.
    """
    conn, case_id = case
    run = _approved_run(conn, case_id, route, bundle, blobs)
    provider = run.provider()
    run_route(
        conn,
        blobs,
        run_id=run.run_id,
        route=route,
        execution=Execution(provider, PRICE, bundle),
    )
    attempts = [
        row[0]
        for row in conn.execute(
            "SELECT attempt_id FROM run_attempts WHERE run_id = %s", (run.run_id,)
        ).fetchall()
    ]
    taken = [reserved_for(conn, attempt) for attempt in attempts]

    assert len(attempts) == len(provider.calls) == len(route.nodes)
    assert all(row is not None for row in taken)
    assert {row.price for row in taken if row is not None} == {PRICE}
    assert sorted(row.amount for row in taken if row is not None) == sorted(
        priced_request(
            PRICE, len(provider.answers.request_bytes(prompt, json_object=True))
        )
        for prompt in provider.answers.prompts
    )
    assert all(
        row is not None and Decimal(0) < row.amount < worst_case(PRICE) for row in taken
    )
