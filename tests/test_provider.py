"""The provider call: a closed set of refusals, and a body that never travels.

`docs/DECISIONS.md` §16 is the contract. Two things it insists on are easy to get
wrong and are what most of this file is about.

*The body is never quoted.* A completion echoes the prompt, and the prompt
carries evidence. So no refusal here may carry the response body, the model's
text, or the vendor's error string -- only a code from the closed set.

*The charge is a Decimal.* `usage.cost` arrives as a JSON number, and reading it
as a float loses the cent invariant 7 exists to keep. It is parsed with
`json.loads(..., parse_float=Decimal)` and asserted here to be one.

The live call is one test, skipped with its reason when the credential is absent
and turned into a failure by `CAOS_REQUIRE_PROVIDER=1` -- because a provider
suite that never called the provider is the vacuous pass
`docs/AI_CODE_QUALITY.md` §4 forbids.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from server.provider import Completion, OpenRouter, Transport, UrllibTransport
from server.refusals import Refusal, RefusalCode

PROMPT = "Total debt at 31 December 2026 was USD 1,240.0m. Summarise."
SECRET_ECHO = "Total debt at 31 December 2026 was USD 1,240.0m"

LIVE_KEY = os.environ.get("OPENROUTER_API_KEY")
LIVE_MODEL = os.environ.get("OPENROUTER_MODEL")
PROVIDER_REQUIRED = os.environ.get("CAOS_REQUIRE_PROVIDER") == "1"
_NO_CREDENTIAL = "OPENROUTER_API_KEY is unset: there is no live provider to call"


def _body(
    *,
    content: str = "ok",
    finish_reason: str = "stop",
    cost: float | None = 0.000_003_3,
) -> bytes:
    usage: dict[str, object] = {"prompt_tokens": 12, "completion_tokens": 3}
    if cost is not None:
        usage["cost"] = cost
    return json.dumps(
        {
            "id": "gen-abc123",
            "model": "openai/gpt-4o-mini",
            "choices": [
                {"message": {"content": content}, "finish_reason": finish_reason}
            ],
            "usage": usage,
        }
    ).encode("utf-8")


@dataclass
class _Transport:
    """A stand-in for the network. Returns what it was told to."""

    status: int = 200
    payload: bytes = field(default_factory=_body)
    raises: Exception | None = None

    def __post_init__(self) -> None:
        self.calls = 0

    def post(
        self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
    ) -> tuple[int, bytes]:
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return self.status, self.payload


def _provider(transport: _Transport) -> OpenRouter:
    return OpenRouter(
        api_key="not-a-real-key",
        model="openai/gpt-4o-mini",
        transport=transport,
    )


def test_a_completion_carries_its_text_charge_and_generation_id() -> None:
    completion = _provider(_Transport()).complete(PROMPT)

    assert isinstance(completion, Completion)
    assert completion.content == "ok"
    assert completion.generation_id == "gen-abc123"
    assert completion.charge == Decimal("0.0000033")


def test_the_charge_is_a_decimal_not_a_float() -> None:
    """Invariant 7. `usage.cost` is a JSON number; read as a float it has
    already lost the cent before anything can add it up."""
    completion = _provider(_Transport()).complete(PROMPT)

    assert isinstance(completion.charge, Decimal)
    assert not isinstance(completion.charge, float)


def test_the_call_forbids_provider_fallbacks() -> None:
    """§16: one run has one provider identity. A fallback would silently move
    the run to a different model than the one its charges were priced against."""
    sent: dict[str, object] = {}

    @dataclass
    class _Recorder(_Transport):
        def post(
            self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
        ) -> tuple[int, bytes]:
            sent.update(json.loads(body))
            sent["_headers"] = dict(headers)
            sent["_url"] = url
            return 200, self.payload

    _provider(_Recorder()).complete(PROMPT)

    assert sent["provider"] == {"allow_fallbacks": False}
    assert sent["stream"] is False
    assert str(sent["_url"]).endswith("/chat/completions")


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 413, 422])
def test_a_client_error_is_call_invalid_and_never_retried(status: int) -> None:
    transport = _Transport(status=status, payload=b'{"error":{"message":"nope"}}')

    with pytest.raises(Refusal) as caught:
        _provider(transport).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_CALL_INVALID
    assert transport.calls == 1, "a call that cannot succeed is not tried again"


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_a_transient_status_is_unavailable(status: int) -> None:
    """The attempt stays indeterminate with its reservation: the call may have
    reached the provider and may be billed."""
    with pytest.raises(Refusal) as caught:
        _provider(_Transport(status=status)).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_UNAVAILABLE


def test_a_transport_error_is_unavailable() -> None:
    with pytest.raises(Refusal) as caught:
        _provider(_Transport(raises=TimeoutError("timed out"))).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_UNAVAILABLE


def test_a_truncated_completion_is_refused() -> None:
    """A module's envelope cut off mid-object is not a shorter answer; it is a
    different one, and it would fail schema validation later with a worse code."""
    with pytest.raises(Refusal) as caught:
        _provider(_Transport(payload=_body(finish_reason="length"))).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_OUTPUT_TRUNCATED


def test_a_content_filtered_completion_is_refused() -> None:
    with pytest.raises(Refusal) as caught:
        _provider(_Transport(payload=_body(finish_reason="content_filter"))).complete(
            PROMPT
        )

    assert caught.value.code is RefusalCode.PROVIDER_REFUSED


def test_a_body_that_is_not_json_is_refused() -> None:
    with pytest.raises(Refusal) as caught:
        _provider(_Transport(payload=b"<html>gateway</html>")).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_RESPONSE_INVALID


def test_a_body_without_a_cost_is_refused() -> None:
    """No cost means nothing to reconcile the reservation against, and a run
    that cannot be charged cannot be stopped at its ceiling."""
    with pytest.raises(Refusal) as caught:
        _provider(_Transport(payload=_body(cost=None))).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_RESPONSE_INVALID


@pytest.mark.parametrize(
    "transport",
    [
        _Transport(status=400, payload=SECRET_ECHO.encode()),
        _Transport(status=500, payload=SECRET_ECHO.encode()),
        _Transport(payload=b"<html>" + SECRET_ECHO.encode() + b"</html>"),
        _Transport(payload=_body(content=SECRET_ECHO, finish_reason="length")),
        _Transport(payload=_body(content=SECRET_ECHO, cost=None)),
    ],
)
def test_no_refusal_carries_any_of_the_body(transport: _Transport) -> None:
    """A completion echoes the prompt, and the prompt carries evidence. So the
    refusal carries the code and nothing else -- not in the message, not in the
    chain (`CLAUDE.md`: never log document-derived text)."""
    with pytest.raises(Refusal) as caught:
        _provider(transport).complete(PROMPT)

    leaked = str(caught.value) + repr(caught.value) + repr(caught.value.__cause__)
    assert "Total debt" not in leaked
    assert "1,240.0m" not in leaked
    assert leaked.count(caught.value.code.value) >= 1


def test_the_default_transport_is_urllib_and_satisfies_the_protocol() -> None:
    """§16 chose the standard library over a vendor SDK. The seam exists so the
    refusal table above can be driven without a network, not so the real client
    can be swapped for something else by default."""
    transport: Transport = OpenRouter(api_key="k", model="m").transport

    assert isinstance(transport, UrllibTransport)


def test_a_provider_without_a_model_is_refused() -> None:
    """§16: `OPENROUTER_MODEL` has no default. Unset means there is no live
    provider, not that some other model should be picked."""
    with pytest.raises(Refusal) as caught:
        OpenRouter(api_key="k", model="", transport=_Transport()).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED


def test_the_live_provider_returns_a_completion() -> None:
    """The one call that really leaves the machine.

    A provider suite that never called the provider would be the vacuous pass
    `docs/AI_CODE_QUALITY.md` §4 forbids, so this skips loudly rather than
    quietly, and CAOS_REQUIRE_PROVIDER=1 turns the skip into a failure.
    """
    if LIVE_KEY is None or LIVE_MODEL is None:
        if PROVIDER_REQUIRED:
            pytest.fail(_NO_CREDENTIAL)
        pytest.skip(_NO_CREDENTIAL)

    completion = OpenRouter(api_key=LIVE_KEY, model=LIVE_MODEL).complete(
        "Reply with the single word: ready"
    )

    assert completion.content.strip()
    assert isinstance(completion.charge, Decimal)
    assert completion.charge >= 0
    assert completion.generation_id
