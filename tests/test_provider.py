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
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from email.message import Message
from io import BytesIO

import pytest

from server.provider import (
    DEFAULT_BASE_URL,
    Completion,
    CompletionProvider,
    OpenRouter,
    Transport,
    UrllibTransport,
    _opener,
)
from server.refusals import Refusal, RefusalCode

PROMPT = "Total debt at 31 December 2026 was USD 1,240.0m. Summarise."
SECRET_ECHO = "Total debt at 31 December 2026 was USD 1,240.0m"
# What a vendor puts in an error body. It reaches the transport and stops there.
VENDOR_ERROR = b'{"error":{"message":"rate limited by upstream"}}'

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


def test_json_object_mode_is_asked_for_only_when_wanted() -> None:
    """A narrowing of the provider's output, never a guarantee about it. The
    host still parses and validates: what a module claims about its own output
    is what invariant 3 says never survives."""
    sent: dict[str, object] = {}

    @dataclass
    class _Recorder(_Transport):
        def post(
            self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
        ) -> tuple[int, bytes]:
            sent.update(json.loads(body))
            return 200, self.payload

    _provider(_Recorder()).complete(PROMPT)
    assert "response_format" not in sent

    _provider(_Recorder()).complete(PROMPT, json_object=True)
    assert sent["response_format"] == {"type": "json_object"}


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


@pytest.mark.parametrize(
    "base_url",
    [
        "file:///etc",
        "ftp://example.invalid",
        "data:text/plain,hello",
        "/etc",
        # Clear text. The header carries the key and the body carries evidence.
        "http://openrouter.ai/api/v1",
    ],
)
def test_a_base_url_that_is_not_http_is_refused(base_url: str) -> None:
    """bandit B310 and the clear-text finding, both fixed rather than
    suppressed. The default `urlopen` speaks `file:`, `ftp:`, `data:` and plain
    `http:`, so a base URL from configuration could read a local file or put the
    key and the prompt on the wire unencrypted. The transport refuses the
    scheme, and its opener has no handler that could serve one."""
    with pytest.raises(Refusal) as caught:
        OpenRouter(api_key="k", model="m", base_url=base_url).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED


def test_openrouter_is_a_completion_provider() -> None:
    """The protocol the module executor depends on. `runtime.Provider` is a
    different shape for a different job, and the two are kept apart so a double
    for one cannot be accepted where the other was meant."""
    provider: CompletionProvider = OpenRouter(api_key="k", model="m")

    assert callable(provider.complete)


def test_a_provider_without_a_model_is_refused() -> None:
    """§16: `OPENROUTER_MODEL` has no default. Unset means there is no live
    provider, not that some other model should be picked."""
    with pytest.raises(Refusal) as caught:
        OpenRouter(api_key="k", model="", transport=_Transport()).complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED


def test_an_error_status_arrives_as_an_http_error_the_transport_can_type() -> None:
    """The refusal table above is reachable only if a non-2xx arrives as an
    `HTTPError`, and this is the wiring that decides whether it does.

    `_opener()` is built from nothing, so it holds exactly the handlers it is
    given. `HTTPErrorProcessor` does not raise; it hands a non-2xx to the
    director's error machinery, and *that* raises `HTTPError` only if something
    is registered under `http` to do it. With nothing registered the lookup is a
    bare `KeyError`, `UrllibTransport`'s `except urllib.error.HTTPError` never
    runs, and every 401, 429 and 5xx leaves the provider boundary as an untyped
    crash rather than a code from the closed set -- with the vendor's message
    attached to it, which is the one thing §16 says must not travel.

    `_Transport` cannot catch this: that double hands back a status, which is
    the layer above. Driving it end to end would take a TLS fixture and a new
    dependency to sign one, for a defect that is entirely in which handlers the
    director holds -- so the director is asked directly.
    """
    director = _opener()
    request = urllib.request.Request(f"{DEFAULT_BASE_URL}/chat/completions")

    with pytest.raises(urllib.error.HTTPError) as caught:
        director.error(
            "http", request, BytesIO(VENDOR_ERROR), 429, "Too Many Requests", Message()
        )

    assert caught.value.code == 429
    assert caught.value.read() == VENDOR_ERROR, "the body the transport returns"


@pytest.mark.parametrize(
    "url",
    ["file:///etc/hostname", "ftp://example.invalid/x", "data:text/plain,hello"],
)
def test_the_error_handler_adds_no_scheme_the_opener_did_not_have(url: str) -> None:
    """The opener's other promise, still kept. Being able to raise on an error
    status is not a reason to be able to *open* anything new -- these three are
    what bandit B310 was about.

    Asked of the director rather than of the scheme guard above it: the guard is
    the first refusal and has its own test, and this is the second one behind it.
    Plain `http:` is not here because it never reaches the director -- the guard
    refuses the scheme, which is the point of having both.
    """
    director = _opener()

    assert director.open(urllib.request.Request(url)) is None, "no handler served it"


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
