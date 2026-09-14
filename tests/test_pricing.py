"""F06: a reservation is priced from the configured model, conservatively.

The reservation covers the worst case the transport allows (§38): every byte of
the largest request as an input token, and the output cap as output tokens.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from test_runtime import _approved_run, _Provider, blobs, bundle, route

from server.blobs import BlobStore
from server.engine.route import ResolvedRoute
from server.engine.runtime import Execution, run_route
from server.methodology.bundle import Bundle
from server.pricing import ModelPrice, worst_case
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


def test_reservation_is_the_worst_case_charge_for_the_configured_model(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(_Provider(blobs), PRICE, bundle),
    )
    attempts = conn.execute(
        "SELECT attempt_id FROM run_attempts WHERE run_id = %s", (run_id,)
    ).fetchall()
    assert attempts
    assert {reserved_for(conn, row[0]) for row in attempts} == {worst_case(PRICE)}


def test_a_price_for_another_model_refuses_before_any_attempt(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    provider = _Provider(blobs)
    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, replace(PRICE, model="other/model"), bundle),
        )
    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED
    assert provider.calls == []
    assert conn.execute(
        "SELECT count(*) FROM run_attempts WHERE run_id = %s", (run_id,)
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
    run_id = _approved_run(conn, case_id, route, bundle, blobs, ceiling=Decimal("1.05"))
    provider = _Provider(blobs, charge=Decimal("1.00"))
    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, small, bundle),
        )
    assert caught.value.code is RefusalCode.BUDGET_CEILING_REACHED
    assert provider.calls == ["CP-0"]
