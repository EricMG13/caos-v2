"""Phase 7 exit: the forecast is complete, honest about its residual, and finite.

`docs/REBUILD_PLAN.md` Phase 7 names three:
`test_forecast_complete_requires_every_requested_period`,
`test_forecast_residual_is_not_forced_to_zero` and
`test_forecast_unavailability_propagates`.

The one worth reading twice is the residual. The model states what it believes a
period closes at; the host computes the same thing from the two identities in
`SYSTEM_SPEC.md` §6.1. The residual is the difference between them. Computing the
closing balance and calling that the answer would make the residual zero by
construction and the reconciliation vacuous -- which is the failure §6.1 exists
to prevent, not a tidier implementation of it.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from server.calculators.cash_flow import (
    MAX_FORECAST_CASES,
    MAX_FORECAST_PERIODS,
    Period,
    cash_flow_forecast,
)
from server.refusals import Refusal, RefusalCode

OPENING_DEBT = Decimal("1000")
OPENING_CASH = Decimal("100")


def _driver(period_id: str, case: str = "BASE", **overrides: str) -> dict[str, Any]:
    """A period that balances: every movement stated, and the closing balances
    the identities produce from them."""
    row: dict[str, Any] = {
        "period_id": period_id,
        "case": case,
        "status": "READY",
        "revenue": "500",
        "ebitda": "100",
        "cfo": "80",
        "capex": "20",
        "cash_interest": "10",
        "cash_taxes": "5",
        "distributions": "0",
        "issuance": "0",
        "optional_repayment": "0",
        "pik": "0",
        "capitalised_interest": "0",
        "fx_perimeter": "0",
        "financing_investing": "0",
        # opening 1000, amortisation 50 -> 950; opening 100 + 80 - 20 - 10 - 5 -> 145
        "stated_closing_debt": "950",
        "stated_closing_cash": "145",
    }
    row.update(overrides)
    return row


def _request(
    periods: list[tuple[str, str]],
    drivers: list[dict[str, Any]],
    amortisation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "opening": {
            "debt_by_facility": {"TLB": str(OPENING_DEBT)},
            "cash": str(OPENING_CASH),
            "as_of_period_id": "FY25",
        },
        "periods": [
            {
                "period_id": period_id,
                "fiscal_year": period_id[2:],
                "case": case,
                "days": "365",
            }
            for period_id, case in periods
        ],
        "drivers": drivers,
        "contractual": {
            "amortisation": amortisation
            if amortisation is not None
            else [
                {"case": case, "period_id": period_id, "amount": "50"}
                for period_id, case in periods
            ]
        },
        "policy": {"cash_sweep_pct": "0", "min_cash": "0", "revolver_limit": "0"},
        "tolerance": "0.001",
    }


def test_a_balancing_period_computes_both_identities() -> None:
    result = cash_flow_forecast(_request([("FY26", "BASE")], [_driver("FY26")]))

    [row] = result["periods"]
    assert result["status"] == "complete"
    assert row["debt"]["closing"] == "950"
    assert row["cash"]["closing"] == "145"
    assert row["residual"] == "0"
    assert row["unavailable_reason"] is None


def test_forecast_residual_is_not_forced_to_zero() -> None:
    """A named exit test. The model's stated close disagrees with the identity,
    and the answer is that it disagrees -- not a balancing figure.

    The stated debt is 900 where the identities give 950. A calculator that
    computed the close and reported it would show a residual of zero and a
    period that reconciled, which is exactly the reassurance this must not give.
    """
    result = cash_flow_forecast(
        _request(
            [("FY26", "BASE")],
            [_driver("FY26", stated_closing_debt="900")],
        )
    )

    [row] = result["periods"]
    assert row["residual"] == "50"
    assert row["unavailable_reason"] is not None
    assert "residual" in row["unavailable_reason"]
    assert result["status"] == "incomplete"


def test_a_residual_inside_the_tolerance_is_reported_and_survives() -> None:
    """Reported either way. Under tolerance it does not make the period
    unavailable, which is what a tolerance is for."""
    result = cash_flow_forecast(
        _request(
            [("FY26", "BASE")],
            [_driver("FY26", stated_closing_cash="145.0005")],
        )
    )

    [row] = result["periods"]
    assert Decimal(row["residual"]) > 0
    assert row["unavailable_reason"] is None
    assert result["status"] == "complete"


def test_forecast_unavailability_propagates() -> None:
    """A named exit test. A period that could not be computed makes every later
    period in that case unavailable -- never read as zero growth."""
    result = cash_flow_forecast(
        _request(
            [("FY26", "BASE"), ("FY27", "BASE"), ("FY28", "BASE")],
            [
                _driver("FY26", stated_closing_debt="1"),  # breaks here
                _driver("FY27"),
                _driver("FY28"),
            ],
        )
    )

    first, second, third = result["periods"]
    assert first["unavailable_reason"] is not None
    assert second["unavailable_reason"] is not None
    assert third["unavailable_reason"] is not None
    assert "FY26" in second["unavailable_reason"], "it says which period broke"
    assert second["cash"]["closing"] is None, "not zero, and not carried forward"
    assert result["status"] == "incomplete"


def test_unavailability_does_not_cross_into_another_case() -> None:
    """Cases are independent horizons. A DOWNSIDE that cannot be computed says
    nothing about BASE."""
    result = cash_flow_forecast(
        _request(
            [("FY26", "BASE"), ("FY26", "DOWNSIDE")],
            [
                _driver("FY26", case="BASE"),
                _driver("FY26", case="DOWNSIDE", stated_closing_cash="1"),
            ],
        )
    )

    rows = {row["case"]: row for row in result["periods"]}
    assert rows["BASE"]["unavailable_reason"] is None
    assert rows["DOWNSIDE"]["unavailable_reason"] is not None


def test_forecast_complete_requires_every_requested_period() -> None:
    """A named exit test. One successful period cannot stand in for the horizon.

    Every requested pair appears exactly once, and an unavailable one keeps its
    place with its reason -- a horizon that dropped its failures would read as a
    shorter horizon that worked.
    """
    requested = [("FY26", "BASE"), ("FY27", "BASE")]
    result = cash_flow_forecast(
        _request(
            requested,
            [_driver("FY26"), _driver("FY27", stated_closing_cash="0")],
        )
    )

    pairs = [(row["period_id"], row["case"]) for row in result["periods"]]
    assert pairs == requested, "every requested pair, exactly once, in order"
    assert result["status"] == "incomplete", "one good period is not the horizon"
    assert result["periods"][0]["unavailable_reason"] is None
    assert result["periods"][1]["unavailable_reason"] is not None


def test_a_period_carries_its_case_so_two_horizons_cannot_be_confused() -> None:
    """`Period` is the unit the whole calculation is keyed on. The case is part
    of its identity, not a label beside it -- FY26 BASE and FY26 DOWNSIDE are
    two different periods, and a chain that mixed them would carry one case's
    closing balance into the other's opening."""
    base = Period(period_id="FY26", fiscal_year="2026", case="BASE", days=Decimal(365))
    downside = Period(
        period_id="FY26", fiscal_year="2026", case="DOWNSIDE", days=Decimal(365)
    )

    assert base != downside
    assert base.days == Decimal(365)


def test_a_duplicate_case_period_is_refused() -> None:
    """ "Exactly once" is unanswerable if the request asks twice."""
    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(
            _request(
                [("FY26", "BASE"), ("FY26", "BASE")],
                [_driver("FY26")],
            )
        )

    assert caught.value.code is RefusalCode.METHODOLOGY_INPUT_INVALID


def test_a_period_with_no_driver_is_refused() -> None:
    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(_request([("FY26", "BASE")], []))

    assert caught.value.code is RefusalCode.METHODOLOGY_INPUT_INVALID


def test_a_driver_that_is_not_ready_is_refused() -> None:
    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(
            _request([("FY26", "BASE")], [_driver("FY26", status="DRAFT")])
        )

    assert caught.value.code is RefusalCode.FORECAST_DRIVER_NOT_READY


def test_a_float_in_a_numeric_field_is_refused() -> None:
    """Invariant 1. By the time a float exists the cent is already gone, so
    converting it would launder a value the model never stated."""
    request = _request([("FY26", "BASE")], [_driver("FY26")])
    request["drivers"][0]["ebitda"] = 100.5

    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(request)

    assert caught.value.code is RefusalCode.METHODOLOGY_INPUT_INVALID


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_a_non_finite_numeric_is_refused_before_use(value: str) -> None:
    request = _request([("FY26", "BASE")], [_driver("FY26")])
    request["drivers"][0]["ebitda"] = value

    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(request)

    assert caught.value.code is RefusalCode.METHODOLOGY_INPUT_INVALID


def test_a_zero_denominator_is_null_with_no_infinity() -> None:
    """Invariant 7. Leverage against zero EBITDA is `null`, never an infinity --
    and a null ratio is not itself a missing period."""
    result = cash_flow_forecast(
        _request(
            [("FY26", "BASE")],
            [_driver("FY26", ebitda="0", cfo="80")],
        )
    )

    [row] = result["periods"]
    assert row["metrics"]["gross_leverage"] is None
    assert row["metrics"]["net_leverage"] is None
    assert row["unavailable_reason"] is None, "a null ratio is not a failure"
    assert result["status"] == "complete"


def test_the_chain_carries_each_close_into_the_next_open() -> None:
    """Invariant 2: `opening[n+1] == closing[n]`, per case."""
    result = cash_flow_forecast(
        _request(
            [("FY26", "BASE"), ("FY27", "BASE")],
            [
                _driver("FY26"),
                # opening 950 - 50 -> 900; opening 145 + 45 -> 190
                _driver("FY27", stated_closing_debt="900", stated_closing_cash="190"),
            ],
        )
    )

    first, second = result["periods"]
    assert second["debt"]["opening"] == first["debt"]["closing"]
    assert second["cash"]["opening"] == first["cash"]["closing"]
    assert result["status"] == "complete"


def test_the_work_factor_refuses_a_horizon_past_the_ceiling() -> None:
    """Host-enforced before any arithmetic, so model-authored input cannot widen
    what a calculation may cost."""
    periods = [(f"FY{n:02d}", "BASE") for n in range(MAX_FORECAST_PERIODS + 1)]

    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(
            _request(periods, [_driver(period_id) for period_id, _ in periods])
        )

    assert caught.value.code is RefusalCode.METHODOLOGY_INPUT_INVALID


def test_the_work_factor_refuses_too_many_cases() -> None:
    cases = [f"CASE{n}" for n in range(MAX_FORECAST_CASES + 1)]
    periods = [("FY26", case) for case in cases]

    with pytest.raises(Refusal) as caught:
        cash_flow_forecast(
            _request(periods, [_driver("FY26", case=case) for case in cases])
        )

    assert caught.value.code is RefusalCode.METHODOLOGY_INPUT_INVALID


def test_the_same_request_twice_is_the_same_answer() -> None:
    """Invariant 6: pure. No clock, no randomness, byte-identical output."""
    request = _request([("FY26", "BASE")], [_driver("FY26")])

    first = cash_flow_forecast(request)
    second = cash_flow_forecast(request)

    assert first == second
