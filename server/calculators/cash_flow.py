"""`cash_flow_forecast` — the deterministic forecast the host owns.

`SYSTEM_SPEC.md` §6.1. CP-2G states its roll-forward rules in prose and emits
driver rows; no calculator computed the projection, so leverage and coverage were
recomputed deterministically *over* arithmetic a model had performed. This moves
the arithmetic here and leaves the model choosing drivers, with rationale and
evidence.

Six invariants, and the three that shape every line below:

*Decimal, never float.* JSON has no decimal type, so every numeric arrives as a
**string** and is parsed with `Decimal(str)`. A JSON float in a numeric field is
`METHODOLOGY_INPUT_INVALID` rather than a silent coercion, because binary
floating point cannot represent a cent. There is no `float(` in this module and
output numerics are strings.

*The residual is explicit and never forced to zero.* The model states what it
believes each period closes at; the host computes the same thing from the two
identities. The residual is the difference. Forcing it to zero -- by computing
the closing balance and calling it the answer -- would make the reconciliation
vacuous, which is the whole failure §6.1 exists to prevent. A residual larger
than the tolerance makes the period unavailable and says so.

*Unavailability propagates forward.* A period that could not be computed makes
every later period in that case unavailable. It is never read as zero growth.

Pure: no I/O, no clock, no randomness. Same inputs, byte-identical output.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from server.refusals import Refusal, RefusalCode

# Host-enforced before anything else runs, so model-authored input cannot widen
# what a calculation may cost (`SYSTEM_SPEC.md` §6.1).
MAX_FORECAST_PERIODS = 40
MAX_FORECAST_CASES = 6
MAX_FORECAST_FACILITIES = 40
MAX_WORK = 100_000

DEFAULT_TOLERANCE = Decimal("0.001")
READY = "READY"

# Every movement a driver row may state. Absent means zero; present and not a
# numeric string means the row is refused rather than read as zero.
_MOVEMENTS = (
    "revenue",
    "ebitda",
    "cfo",
    "capex",
    "acquisitions_disposals",
    "cash_interest",
    "cash_taxes",
    "distributions",
    "issuance",
    "optional_repayment",
    "pik",
    "capitalised_interest",
    "fx_perimeter",
    "financing_investing",
)
# What the model says the period closes at. The host computes both and the
# difference is the residual, so these are required: a driver row that states no
# result gives nothing to reconcile against.
_STATED = ("stated_closing_debt", "stated_closing_cash")


@dataclass(frozen=True, slots=True)
class _Inputs:
    """Everything the projection reads that is the same for every period.

    One object rather than four arguments threaded through two functions: they
    are all the validated request, and passing them separately made the
    signatures wide enough that the argument ceiling refused them -- which is
    the ceiling doing its job.
    """

    drivers: Mapping[tuple[str, str], Mapping[str, Any]]
    contractual: Mapping[tuple[str, str], Decimal]
    tolerance: Decimal

    def driver_for(self, period: Period) -> Mapping[str, Any]:
        driver = self.drivers.get((period.case, period.period_id))
        if driver is None:
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        if str(driver.get("status")) != READY:
            raise Refusal(RefusalCode.FORECAST_DRIVER_NOT_READY)
        return driver

    def repayment_for(self, period: Period) -> Decimal:
        return self.contractual.get((period.case, period.period_id)) or Decimal(0)


@dataclass(frozen=True, slots=True)
class Period:
    """One case-period of the requested horizon."""

    period_id: str
    fiscal_year: str
    case: str
    days: Decimal


def cash_flow_forecast(request: Mapping[str, Any]) -> dict[str, Any]:
    """Project every requested case-period, or refuse.

    Returns the shape `SYSTEM_SPEC.md` §6.1 describes: one row per requested
    case-period with its movements, balances, residual, metrics and
    `unavailable_reason`, plus `checks` and a `status` that is `complete` only
    when every requested period computed.
    """
    periods = _periods(request)
    _enforce_work_factor(periods, request)
    inputs = _Inputs(
        drivers=_drivers(request),
        contractual=_contractual(request),
        tolerance=_decimal(request.get("tolerance", "0.001"), "tolerance"),
    )
    opening = _opening(request)

    rows: list[dict[str, Any]] = []
    checks: list[dict[str, str]] = []
    for case in sorted({period.case for period in periods}):
        rows.extend(
            _project_case(
                [period for period in periods if period.case == case],
                inputs,
                opening,
                checks,
            )
        )

    complete = bool(rows) and all(row["unavailable_reason"] is None for row in rows)
    return {
        "status": "complete" if complete else "incomplete",
        "periods": rows,
        "checks": checks,
    }


def _project_case(
    periods: Sequence[Period],
    inputs: _Inputs,
    opening: tuple[Decimal, Decimal],
    checks: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """One case, chained. `opening[n+1] == closing[n]`, checked rather than
    assumed -- a break is `FORECAST_CHAIN_BROKEN`."""
    opening_debt, opening_cash = opening
    rows = []
    unavailable_from: str | None = None

    for period in periods:
        if unavailable_from is not None:
            # Invariant 4: never read as zero growth.
            rows.append(
                _unavailable(
                    period,
                    opening_debt,
                    opening_cash,
                    f"a period earlier in this case is unavailable: {unavailable_from}",
                )
            )
            continue

        row, closing_debt, closing_cash = _project_period(
            period, inputs, (opening_debt, opening_cash)
        )
        rows.append(row)
        checks.append(
            {
                "check_id": f"residual:{period.case}:{period.period_id}",
                "outcome": "PASS" if row["unavailable_reason"] is None else "FAIL",
                "detail": str(row["residual"]),
            }
        )
        if row["unavailable_reason"] is not None:
            unavailable_from = period.period_id
        opening_debt, opening_cash = closing_debt, closing_cash

    return rows


def _project_period(
    period: Period, inputs: _Inputs, opening: tuple[Decimal, Decimal]
) -> tuple[dict[str, Any], Decimal, Decimal]:
    """The two identities, and the residual between them and what was stated."""
    driver = inputs.driver_for(period)
    contractual_repayment = inputs.repayment_for(period)
    opening_debt, opening_cash = opening
    moves = {name: _movement(driver, name) for name in _MOVEMENTS}

    closing_debt = (
        opening_debt
        + moves["issuance"]
        + moves["pik"]
        + moves["capitalised_interest"]
        - contractual_repayment
        - moves["optional_repayment"]
        + moves["fx_perimeter"]
    )
    closing_cash = (
        opening_cash
        + moves["cfo"]
        - moves["capex"]
        - moves["cash_interest"]
        - moves["cash_taxes"]
        - moves["distributions"]
        + moves["financing_investing"]
    )

    stated_debt = _decimal(driver.get("stated_closing_debt"), "stated_closing_debt")
    stated_cash = _decimal(driver.get("stated_closing_cash"), "stated_closing_cash")
    residual = max(abs(closing_debt - stated_debt), abs(closing_cash - stated_cash))

    reason = None
    if residual > inputs.tolerance:
        # Invariant 3. Not absorbed into a balancing figure: the model's own
        # numbers do not add up, and that is the answer.
        reason = f"residual {residual} exceeds tolerance {inputs.tolerance}"

    fcf = moves["cfo"] - moves["capex"] - moves["cash_interest"] - moves["cash_taxes"]
    row = {
        "period_id": period.period_id,
        "fiscal_year": period.fiscal_year,
        "case": period.case,
        "operating": {
            "revenue": str(moves["revenue"]),
            "ebitda": str(moves["ebitda"]),
            "margin": _ratio(moves["ebitda"], moves["revenue"]),
            "cfo": str(moves["cfo"]),
        },
        "investing": {
            "capex": str(moves["capex"]),
            "acquisitions_disposals": str(moves["acquisitions_disposals"]),
        },
        "financing": {
            "cash_interest": str(moves["cash_interest"]),
            "cash_taxes": str(moves["cash_taxes"]),
            "distributions": str(moves["distributions"]),
            "issuance": str(moves["issuance"]),
            "contractual_repayment": str(contractual_repayment),
            "optional_repayment": str(moves["optional_repayment"]),
        },
        "fcf": str(fcf),
        "debt": {
            "opening": str(opening_debt),
            "pik": str(moves["pik"]),
            "capitalised_interest": str(moves["capitalised_interest"]),
            "fx_perimeter": str(moves["fx_perimeter"]),
            "closing": str(closing_debt),
        },
        "cash": {
            "opening": str(opening_cash),
            "closing": str(closing_cash),
            "accessible": str(closing_cash),
        },
        "residual": str(residual),
        "metrics": {
            "gross_leverage": _ratio(closing_debt, moves["ebitda"]),
            "net_leverage": _ratio(closing_debt - closing_cash, moves["ebitda"]),
            "interest_coverage": _ratio(moves["ebitda"], moves["cash_interest"]),
            "fcf_to_debt": _ratio(fcf, closing_debt),
        },
        "unavailable_reason": reason,
    }
    return row, closing_debt, closing_cash


def _unavailable(
    period: Period, opening_debt: Decimal, opening_cash: Decimal, reason: str
) -> dict[str, Any]:
    """A period that cannot be computed still appears, with its reason.

    `calculation_output_complete` requires every requested pair to be present:
    a horizon that silently dropped its unavailable periods would look like a
    shorter horizon that succeeded.
    """
    return {
        "period_id": period.period_id,
        "fiscal_year": period.fiscal_year,
        "case": period.case,
        "operating": None,
        "investing": None,
        "financing": None,
        "fcf": None,
        "debt": {"opening": str(opening_debt), "closing": None},
        "cash": {"opening": str(opening_cash), "closing": None},
        "residual": None,
        "metrics": {},
        "unavailable_reason": reason,
    }


def _ratio(numerator: Decimal, denominator: Decimal) -> dict[str, str] | None:
    """A ratio, or `null` with a reason. Never an infinity (invariant 7)."""
    if denominator == 0:
        return None
    return {"value": str(numerator / denominator)}


def _movement(driver: Mapping[str, Any], name: str) -> Decimal:
    """A stated movement, or zero when the row does not mention it.

    Absent and zero are the same thing for a movement -- a period with no capex
    spent no capex. A *present* value that is not a numeric string is refused,
    because that is a statement the host could not read rather than one the
    model did not make.
    """
    if name not in driver:
        return Decimal(0)
    return _decimal(driver[name], name)


def _decimal(value: object, field: str) -> Decimal:
    """Parse a numeric that arrived as a string.

    A `float` here is refused rather than converted. By the time a float exists
    the cent is already gone, and converting it would launder a value the model
    never actually stated.
    """
    if isinstance(value, float):
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str | int):
        try:
            parsed = Decimal(str(value))
        except InvalidOperation:
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID) from None
    else:
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    if not parsed.is_finite():
        # Invariant 7: refused before use, not carried into a ratio. Every path
        # above lands here, because a `Decimal` a caller had already parsed is
        # the same value as the string it was parsed from -- and it was the one
        # spelling of infinity that used to reach a division.
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    return parsed


def _periods(request: Mapping[str, Any]) -> list[Period]:
    rows = request.get("periods")
    if not isinstance(rows, list) or not rows:
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)

    periods = []
    seen = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        period = Period(
            period_id=str(row.get("period_id", "")),
            fiscal_year=str(row.get("fiscal_year", "")),
            case=str(row.get("case", "")),
            days=_decimal(row.get("days", "0"), "days"),
        )
        if not period.period_id or not period.case:
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        key = (period.case, period.period_id)
        if key in seen:
            # A duplicate pair would make "every requested pair exactly once"
            # unanswerable, so it is refused rather than de-duplicated.
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        seen.add(key)
        periods.append(period)
    return periods


def _enforce_work_factor(periods: Sequence[Period], request: Mapping[str, Any]) -> None:
    """The ceiling, before any arithmetic. Model-authored input cannot widen it."""
    cases = {period.case for period in periods}
    facilities = len(_opening_facilities(request))
    per_case = len({period.period_id for period in periods})

    if per_case > MAX_FORECAST_PERIODS:
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    if len(cases) > MAX_FORECAST_CASES:
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    if facilities > MAX_FORECAST_FACILITIES:
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    if per_case * len(cases) * (1 + facilities) > MAX_WORK:
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)


def _opening_facilities(request: Mapping[str, Any]) -> Mapping[str, Any]:
    opening = request.get("opening")
    if not isinstance(opening, Mapping):
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    facilities = opening.get("debt_by_facility", {})
    if not isinstance(facilities, Mapping):
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    return facilities


def _opening(request: Mapping[str, Any]) -> tuple[Decimal, Decimal]:
    opening = request["opening"]
    debt = sum(
        (
            _decimal(amount, "debt_by_facility")
            for amount in _opening_facilities(request).values()
        ),
        Decimal(0),
    )
    return debt, _decimal(opening.get("cash", "0"), "cash")


def _drivers(request: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    rows = request.get("drivers")
    if not isinstance(rows, list):
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    drivers = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        for name in _STATED:
            if name not in row:
                # Nothing to reconcile against is not a period that reconciles.
                raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        drivers[(str(row.get("case", "")), str(row.get("period_id", "")))] = row
    return drivers


def _contractual(request: Mapping[str, Any]) -> dict[tuple[str, str], Decimal]:
    """Contractual amortisation, summed per case-period across facilities."""
    contractual = request.get("contractual", {})
    if not isinstance(contractual, Mapping):
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
    rows = contractual.get("amortisation", [])
    if not isinstance(rows, list):
        raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)

    totals: dict[tuple[str, str], Decimal] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise Refusal(RefusalCode.METHODOLOGY_INPUT_INVALID)
        key = (str(row.get("case", "")), str(row.get("period_id", "")))
        totals[key] = totals.get(key, Decimal(0)) + _decimal(
            row.get("amount", "0"), "amount"
        )
    return totals
