"""A reservation priced from the configured model (F06, §16).

The provider is asked at most `MAX_REQUEST_BYTES` of request and
`MAX_COMPLETION_TOKENS` of completion (§38). With no tokenizer, the conservative
input bound is one token per request byte, so the worst case of one call is
`MAX_REQUEST_BYTES * input + MAX_COMPLETION_TOKENS * output`. That is what a run
reserves before every call: never the caller's guess at the likely charge. An
application price cannot guarantee a vendor bill; the known charge is still
reconciled after the call, and an overrun consumes the remaining capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    Context,
    Decimal,
    DecimalException,
    Inexact,
    InvalidOperation,
    Overflow,
)

from server.provider import MAX_COMPLETION_TOKENS, MAX_REQUEST_BYTES
from server.refusals import Refusal, RefusalCode
from server.store.budget import validate_spend


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """A dated per-token price for one configured model identity."""

    model: str
    input_per_token: Decimal
    output_per_token: Decimal
    as_of: date


def worst_case(price: ModelPrice) -> Decimal:
    """The most one call can cost at this price, exactly, or a typed refusal."""
    if not isinstance(price.model, str) or not price.model:
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    validate_spend(price.input_per_token)
    validate_spend(price.output_per_token)
    # An explicit context, not the caller's: exact or refused, never rounded.
    exact = Context(
        prec=1000,
        Emax=MAX_EMAX,
        Emin=MIN_EMIN,
        traps=[Inexact, Overflow, InvalidOperation],
    )
    try:
        amount = exact.add(
            exact.multiply(price.input_per_token, MAX_REQUEST_BYTES),
            exact.multiply(price.output_per_token, MAX_COMPLETION_TOKENS),
        )
    except DecimalException:
        raise Refusal(RefusalCode.MONEY_INVALID) from None
    validate_spend(amount)
    # A free price would reserve nothing, and a ceiling spent to exactly zero
    # admits a zero reservation: the call it pays for could overspend.
    if not amount:
        raise Refusal(RefusalCode.MONEY_INVALID)
    return amount
