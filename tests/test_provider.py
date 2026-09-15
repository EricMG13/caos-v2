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

import http.client
import json
import os
import socket
import traceback
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from email.message import Message
from io import BytesIO
from typing import cast

import pytest

import server.provider as provider_module
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
        self.requests: list[bytes] = []

    def post(
        self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
    ) -> tuple[int, bytes]:
        self.calls += 1
        self.requests.append(body)
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


@pytest.mark.parametrize("status", [200, 400, 429, 500, 302])
@pytest.mark.parametrize(
    "finish,code",
    [
        ("length", RefusalCode.PROVIDER_OUTPUT_TRUNCATED),
        ("content_filter", RefusalCode.PROVIDER_REFUSED),
        *[
            (value, RefusalCode.PROVIDER_RESPONSE_INVALID)
            for value in cast(
                tuple[object, ...], (None, {}, [], "", "tool_calls", "unexpected")
            )
        ],
    ],
)
def test_billing_facts_survive_finish_and_http_refusal(
    status: int, finish: object, code: RefusalCode
) -> None:
    body = json.loads(_body(content=SECRET_ECHO))
    body["choices"][0]["finish_reason"] = finish
    transport = _Transport(status=status, payload=json.dumps(body).encode())
    result = _provider(transport).complete(PROMPT)
    expected = {
        400: RefusalCode.PROVIDER_CALL_INVALID,
        429: RefusalCode.PROVIDER_UNAVAILABLE,
        500: RefusalCode.PROVIDER_UNAVAILABLE,
        302: RefusalCode.PROVIDER_RESPONSE_INVALID,
    }.get(status, code)
    assert result.refusal is expected
    assert result.content is None and SECRET_ECHO not in repr(result)
    assert result.charge == Decimal("0.0000033")
    assert result.generation_id == "gen-abc123"
    assert transport.calls == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("choices", []),
        ("choices", [{}]),
        ("choices", [None]),
        ("choices", [{"finish_reason": "stop", "message": {"content": {}}}]),
        *[
            ("id", value)
            for value in cast(
                tuple[object, ...], (None, {}, True, "", "bad\n", "x" * 513)
            )
        ],
    ],
)
def test_malformed_response_fields_do_not_erase_known_charge(
    field: str, value: object
) -> None:
    body = json.loads(_body())
    body[field] = value
    result = _provider(_Transport(payload=json.dumps(body).encode())).complete(PROMPT)
    assert result.refusal is RefusalCode.PROVIDER_RESPONSE_INVALID
    assert result.charge == Decimal("0.0000033")
    assert result.content is None
    assert result.generation_id == (None if field == "id" else "gen-abc123")


@pytest.mark.parametrize(
    "cost,known",
    [
        (b"true", None),
        (b'"0.1"', None),
        (b"-1", None),
        (b"NaN", None),
        (b"Infinity", None),
        (b"1e131072", None),
        (b"1e-16384", None),
        (b"0e-16384", None),
        (b"1e9999999999999999999999999", None),
        (b"0", Decimal("0")),
        (b"0.0100", Decimal("0.0100")),
    ],
)
def test_response_cost_is_exact_known_money_or_unknown(
    cost: bytes, known: Decimal | None
) -> None:
    transport = _Transport(
        payload=_body(cost=0).replace(b'"cost": 0', b'"cost": ' + cost)
    )
    result = _provider(transport).complete(PROMPT)
    assert result.charge == known
    assert result.refusal is (
        None if known is not None else RefusalCode.PROVIDER_RESPONSE_INVALID
    )
    assert transport.calls == 1


@pytest.mark.parametrize(
    "members",
    [
        b'"cost": 0.5, "cost": 0',
        b'"cost": 0, "cost": 0.5',
        b'"cost": 0.5, "cost": 0.5',
        b'"cost": null, "cost": 0.5',
        b'"cost": 0.5, "cost": 0, "cost": 1',
        b'"co\\u0073t": 0.5, "cost": 0',
    ],
)
def test_decoding_makes_duplicate_members_unknown_without_erasing_siblings(
    members: bytes,
) -> None:
    decoded = provider_module._decode(
        b'{"usage": {' + members + b', "tokens": 12}, "id": "gen-abc123"}'
    )
    assert decoded == {
        "usage": {"cost": None, "tokens": 12},
        "id": "gen-abc123",
    }


@pytest.mark.parametrize("status", [200, 400, 500])
@pytest.mark.parametrize(
    "member,duplicate,unknown_charge,unknown_generation",
    [
        (b'"cost":', b'"cost": 0, ', True, False),
        (b'"usage":', b'"usage": {"cost": 0}, ', True, False),
        (b'"id":', b'"id": "gen-other", ', False, True),
        (b'"choices":', b'"choices": [], ', False, False),
        (b'"message":', b'"message": {}, ', False, False),
        (b'"finish_reason":', b'"finish_reason": "stop", ', False, False),
        (b'"content":', b'"content": "duplicate", ', False, False),
    ],
)
def test_duplicate_response_fields_preserve_only_unambiguous_facts(
    status: int,
    member: bytes,
    duplicate: bytes,
    unknown_charge: bool,
    unknown_generation: bool,
) -> None:
    payload = _body(content=SECRET_ECHO, cost=0.5)
    assert payload.count(member) == 1
    transport = _Transport(
        status=status, payload=payload.replace(member, duplicate + member, 1)
    )
    result = _provider(transport).complete(PROMPT)
    _assert_failed(
        result,
        {
            200: RefusalCode.PROVIDER_RESPONSE_INVALID,
            400: RefusalCode.PROVIDER_CALL_INVALID,
            500: RefusalCode.PROVIDER_UNAVAILABLE,
        }[status],
    )
    assert result.charge == (None if unknown_charge else Decimal("0.5"))
    assert result.generation_id == (None if unknown_generation else "gen-abc123")
    assert transport.calls == 1


def test_duplicate_unused_metadata_does_not_erase_valid_response_facts() -> None:
    payload = _body(cost=0.5).replace(
        b'"prompt_tokens":', b'"prompt_tokens": null, "prompt_tokens":', 1
    )
    transport = _Transport(payload=payload)
    result = _provider(transport).complete(PROMPT)
    assert result == Completion("ok", Decimal("0.5"), "gen-abc123")
    assert transport.calls == 1


@pytest.mark.parametrize("model", [True, {"model": "x"}, "bad model", "x" * 257])
def test_invalid_host_model_prevents_transport(model: object) -> None:
    transport = _Transport()
    with pytest.raises(Refusal, match=r"^PROVIDER_NOT_CONFIGURED$"):
        OpenRouter(api_key="k", model=cast(str, model), transport=transport).complete(
            PROMPT
        )
    assert transport.calls == 0


def test_completion_repr_does_not_include_analytical_text() -> None:
    result = _provider(_Transport(payload=_body(content=SECRET_ECHO))).complete(PROMPT)
    assert SECRET_ECHO not in repr(result)


def test_failed_completion_repr_does_not_quote_a_provider_generation_handle() -> None:
    body = json.loads(_body(content=SECRET_ECHO))
    body["id"] = "not-a-real-key"
    result = _provider(
        _Transport(status=400, payload=json.dumps(body).encode())
    ).complete(PROMPT)
    _assert_failed(result, RefusalCode.PROVIDER_CALL_INVALID)
    assert result.generation_id == "not-a-real-key"


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

    assert sent["provider"] == {"allow_fallbacks": False, "require_parameters": True}
    assert sent["max_completion_tokens"] == 32_768
    assert "max_tokens" not in sent
    assert sent["stream"] is False
    assert str(sent["_url"]).endswith("/chat/completions")


def _assert_safe(refusal: Refusal) -> None:
    public = f"{refusal!s} {refusal!r} {refusal.__cause__!r}"
    public += "".join(traceback.format_exception(refusal))
    assert SECRET_ECHO not in public
    assert "not-a-real-key" not in public
    assert refusal.__cause__ is None


def _assert_failed(result: Completion, code: RefusalCode) -> None:
    assert result.refusal is code
    assert result.content is None
    assert SECRET_ECHO not in repr(result)
    assert "not-a-real-key" not in repr(result)


@pytest.mark.parametrize(
    "prompt",
    [
        SECRET_ECHO + "x" * 1_048_576,
        "\U0001f642" * 100_000,
        '"' * 600_000,
        None,
        17,
        {},
    ],
    ids=["raw-overflow", "unicode-expansion", "escaping", "none", "int", "dict"],
)
def test_an_invalid_or_oversized_prompt_costs_no_transport_call(prompt: object) -> None:
    transport = _Transport()
    with pytest.raises(Refusal) as caught:
        _provider(transport).complete(cast(str, prompt))
    assert caught.value.code is RefusalCode.PROVIDER_CALL_INVALID
    assert transport.calls == 0
    _assert_safe(caught.value)


def test_the_request_ceiling_counts_the_complete_encoded_body() -> None:
    transport = _Transport()
    provider = _provider(transport)
    provider.complete('\U0001f642"')
    room = 1_048_576 - len(transport.requests[-1])
    prompt = '\U0001f642"' + "x" * room
    provider.complete(prompt)
    assert len(transport.requests[-1]) == 1_048_576
    assert json.loads(transport.requests[-1])["messages"][0]["content"] == prompt
    with pytest.raises(Refusal) as caught:
        provider.complete(prompt + "x")
    assert caught.value.code is RefusalCode.PROVIDER_CALL_INVALID
    assert transport.calls == 2


@pytest.mark.parametrize(
    "body",
    [None, "text", bytearray(b"x"), b"x" * 1_048_577],
    ids=["none", "text", "bytearray", "overflow"],
)
def test_the_native_transport_refuses_bad_request_bytes_before_opening(
    monkeypatch: pytest.MonkeyPatch, body: object
) -> None:
    monkeypatch.setattr(
        provider_module, "_opener", lambda: pytest.fail("unexpected native opener")
    )
    with pytest.raises(Refusal) as caught:
        UrllibTransport().post(DEFAULT_BASE_URL, cast(bytes, body), {}, 120.0)
    assert caught.value.code is RefusalCode.PROVIDER_CALL_INVALID


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid",
        "file:///example",
        "https://[" + SECRET_ECHO,
        "https://",
        "https:///path",
        "https://example.invalid:bad",
        "https://bad host",
        "https://example.invalid/\nprivate",
    ],
)
def test_an_injected_transport_cannot_bypass_https_configuration(url: str) -> None:
    transport = _Transport()
    provider = OpenRouter(
        api_key="not-a-real-key", model="m", base_url=url, transport=transport
    )
    with pytest.raises(Refusal) as caught:
        provider.complete(PROMPT)
    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED
    assert transport.calls == 0
    _assert_safe(caught.value)


def test_native_url_configuration_errors_do_not_quote_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_module, "_opener", lambda: pytest.fail("unexpected native opener")
    )
    url = "https://[not-a-real-key]"
    with pytest.raises(Refusal) as caught:
        UrllibTransport().post(url, b"{}", {}, 120.0)
    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED
    _assert_safe(caught.value)


@pytest.mark.parametrize("status", [200, 429, 500])
@pytest.mark.parametrize(
    "body",
    [
        None,
        _body(content=SECRET_ECHO).decode(),
        bytearray(_body()),
        _body() + b" " * 4_194_304,
    ],
    ids=["none", "text", "bytearray", "overflow"],
)
def test_injected_response_bytes_are_checked_before_parsing(
    status: int, body: object
) -> None:
    """_response_bytes checks the transport seam before JSON can accept a string."""
    transport = _Transport(status=status, payload=cast(bytes, body))
    result = _provider(transport).complete(PROMPT)
    _assert_failed(result, RefusalCode.PROVIDER_RESPONSE_INVALID)
    assert result.charge is None and result.generation_id is None
    assert transport.calls == 1


def test_an_injected_response_at_the_byte_ceiling_is_not_truncated() -> None:
    body = _body(content=SECRET_ECHO)
    transport = _Transport(payload=body + b" " * (4_194_304 - len(body)))
    assert _provider(transport).complete(PROMPT).content == SECRET_ECHO
    assert transport.calls == 1


class _ReadStream(BytesIO):
    status = 200

    def __init__(self, body: bytes, *, fails: bool) -> None:
        super().__init__(body)
        self.sizes: list[int | None] = []
        self.fails = fails
        self.consumed = 0

    def read(self, size: int | None = -1, /) -> bytes:
        self.sizes.append(size)
        if self.fails:
            raise TimeoutError(SECRET_ECHO)
        body = super().read(size)
        self.consumed += len(body)
        return body


@pytest.mark.parametrize("status", [200, 429])
@pytest.mark.parametrize(
    "extra,fails", [(0, False), (1, False), (1024, False), (0, True)]
)
def test_native_success_and_error_streams_are_bounded_and_always_closed(
    monkeypatch: pytest.MonkeyPatch, status: int, extra: int, fails: bool
) -> None:
    body = _body(content=SECRET_ECHO)
    stream = _ReadStream(body + b" " * (4_194_304 + extra - len(body)), fails=fails)
    calls: list[tuple[bytes, float]] = []
    errors: list[urllib.error.HTTPError] = []

    class _Director:
        def open(
            self, request: urllib.request.Request, *, timeout: float
        ) -> _ReadStream:
            assert isinstance(request.data, bytes)
            calls.append((request.data, timeout))
            if status != 200:
                error = urllib.error.HTTPError(
                    request.full_url, status, SECRET_ECHO, Message(), stream
                )
                errors.append(error)
                raise error
            return stream

    monkeypatch.setattr(provider_module, "_opener", _Director)
    provider = OpenRouter(api_key="not-a-real-key", model="m")
    capture = _Transport()
    OpenRouter(api_key="k", model="m", transport=capture).complete("")
    prompt = "x" * (1_048_576 - len(capture.requests[0]))
    if status == 200 and not extra and not fails:
        assert provider.complete(prompt).content == SECRET_ECHO
    else:
        result = provider.complete(prompt)
        expected = (
            RefusalCode.PROVIDER_RESPONSE_INVALID
            if extra
            else RefusalCode.PROVIDER_UNAVAILABLE
        )
        _assert_failed(result, expected)
    assert len(calls) == 1
    assert len(calls[0][0]) == 1_048_576
    assert calls[0][1] == 120.0
    assert stream.closed
    assert stream.sizes == [4_194_305]
    assert stream.consumed <= 4_194_305


@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize(
    "framing,expected",
    [
        ("fixed", None),
        ("short", RefusalCode.PROVIDER_UNAVAILABLE),
        ("zero", RefusalCode.PROVIDER_RESPONSE_INVALID),
        ("close", None),
        ("chunked", None),
        ("chunked-short", RefusalCode.PROVIDER_UNAVAILABLE),
        ("chunked-no-end", RefusalCode.PROVIDER_UNAVAILABLE),
    ],
)
def test_read_body_preserves_native_http_framing(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    framing: str,
    expected: RefusalCode | None,
) -> None:
    """_read_body must reject a JSON-valid prefix when HTTP promises more bytes."""
    body = _body(content=SECRET_ECHO)
    length = {"fixed": len(body), "short": len(body) + 10, "zero": 0}.get(framing)
    header = f"Content-Length: {length}\r\n".encode() if length is not None else b""
    if framing.startswith("chunked"):
        header = b"Transfer-Encoding: chunked\r\n"
        size = len(body) + (10 if framing == "chunked-short" else 0)
        body = f"{size:x}\r\n".encode() + body + b"\r\n"
        if framing != "chunked-no-end":
            body += b"0\r\n\r\n"
    if framing == "zero":
        body = b""
    wire = BytesIO(
        f"HTTP/1.1 {status} synthetic\r\n".encode() + header + b"\r\n" + body
    )

    class _Socket:
        def makefile(self, mode: str) -> BytesIO:
            assert mode == "rb"
            return wire

    response = http.client.HTTPResponse(cast(socket.socket, _Socket()))
    response.begin()
    calls: list[float] = []
    errors: list[urllib.error.HTTPError] = []

    class _Director:
        def open(
            self, request: urllib.request.Request, *, timeout: float
        ) -> http.client.HTTPResponse:
            calls.append(timeout)
            if status != 200:
                error = urllib.error.HTTPError(
                    request.full_url, status, SECRET_ECHO, response.headers, response
                )
                errors.append(error)
                raise error
            return response

    monkeypatch.setattr(provider_module, "_opener", _Director)
    if status == 400 and expected is not RefusalCode.PROVIDER_UNAVAILABLE:
        expected = RefusalCode.PROVIDER_CALL_INVALID
    provider = OpenRouter(api_key="not-a-real-key", model="m")
    if expected is None:
        assert provider.complete(PROMPT).content == SECRET_ECHO
    else:
        _assert_failed(provider.complete(PROMPT), expected)
    assert calls == [120.0]
    assert response.closed and wire.closed


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

    _assert_failed(
        _provider(transport).complete(PROMPT), RefusalCode.PROVIDER_CALL_INVALID
    )
    assert transport.calls == 1, "a call that cannot succeed is not tried again"


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_a_transient_status_is_unavailable(status: int) -> None:
    """The attempt stays indeterminate with its reservation: the call may have
    reached the provider and may be billed."""
    _assert_failed(
        _provider(_Transport(status=status)).complete(PROMPT),
        RefusalCode.PROVIDER_UNAVAILABLE,
    )


def test_a_transport_error_is_unavailable() -> None:
    result = _provider(_Transport(raises=TimeoutError(SECRET_ECHO))).complete(PROMPT)
    _assert_failed(result, RefusalCode.PROVIDER_UNAVAILABLE)
    assert result.charge is None and result.generation_id is None


def test_a_truncated_completion_is_refused() -> None:
    """A module's envelope cut off mid-object is not a shorter answer; it is a
    different one, and it would fail schema validation later with a worse code."""
    _assert_failed(
        _provider(_Transport(payload=_body(finish_reason="length"))).complete(PROMPT),
        RefusalCode.PROVIDER_OUTPUT_TRUNCATED,
    )


def test_a_content_filtered_completion_is_refused() -> None:
    _assert_failed(
        _provider(_Transport(payload=_body(finish_reason="content_filter"))).complete(
            PROMPT
        ),
        RefusalCode.PROVIDER_REFUSED,
    )


@pytest.mark.parametrize(
    "status,code",
    [
        (200, RefusalCode.PROVIDER_RESPONSE_INVALID),
        (400, RefusalCode.PROVIDER_CALL_INVALID),
        (500, RefusalCode.PROVIDER_UNAVAILABLE),
    ],
)
@pytest.mark.parametrize("body", [b"<html>gateway</html>", b"\xff", b"[]"])
def test_a_body_that_is_not_json_is_refused(
    status: int, code: RefusalCode, body: bytes
) -> None:
    transport = _Transport(status=status, payload=body)
    result = _provider(transport).complete(PROMPT)
    _assert_failed(result, code)
    assert result.charge is None and result.generation_id is None
    assert transport.calls == 1


def test_a_body_without_a_cost_is_refused() -> None:
    """No cost means nothing to reconcile the reservation against, and a run
    that cannot be charged cannot be stopped at its ceiling."""
    result = _provider(_Transport(payload=_body(cost=None))).complete(PROMPT)
    _assert_failed(result, RefusalCode.PROVIDER_RESPONSE_INVALID)
    assert result.charge is None


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
    result = _provider(transport).complete(PROMPT)
    assert result.refusal is not None
    _assert_failed(result, result.refusal)
    leaked = str(result) + repr(result)
    assert "Total debt" not in leaked
    assert "1,240.0m" not in leaked
    assert leaked.count(result.refusal.value) >= 1


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


def test_the_provider_is_configured_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§16: the repository reads these three names. Until `from_environment`
    only the tests did, so a live test proved the test's wiring rather than the
    application's."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://gateway.example/api/v1")

    provider = OpenRouter.from_environment()

    assert provider.api_key == "not-a-real-key"
    assert provider.model == "openai/gpt-4o-mini"
    assert provider.base_url == "https://gateway.example/api/v1"


def test_the_base_url_defaults_when_the_environment_names_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    assert OpenRouter.from_environment().base_url == DEFAULT_BASE_URL


@pytest.mark.parametrize("unset", ["OPENROUTER_API_KEY", "OPENROUTER_MODEL"])
def test_an_environment_missing_the_key_or_the_model_configures_no_provider(
    monkeypatch: pytest.MonkeyPatch, unset: str
) -> None:
    """The model has no default, and a missing key is a 401 the provider would
    take a round trip to report. Both are refused before any call -- with the
    code alone, never the key that was present."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.delenv(unset)

    with pytest.raises(Refusal) as caught:
        OpenRouter.from_environment()

    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED
    assert "sk-or-v1" not in f"{caught.value!r} {caught.value}"


def test_the_key_never_appears_in_the_providers_repr() -> None:
    """A repr is what a failed assertion, a debugger and a log line all print,
    and the provider is the one object carrying §16's secret."""
    provider = OpenRouter(api_key="sk-or-v1-not-a-real-key", model="openai/gpt-4o-mini")

    assert "sk-or-v1" not in repr(provider)


def test_a_key_no_header_can_carry_is_refused_without_quoting_it() -> None:
    """A key read with its line ending attached. `http.client` refuses the
    header with a `ValueError` whose message is the header itself -- the key --
    and that is no transport failure, so it left the boundary untyped. Nothing
    is sent; the address is this machine's discard port in case it ever is."""
    provider = OpenRouter(
        api_key="sk-or-v1-not-a-real-key\r\n",
        model="openai/gpt-4o-mini",
        base_url="https://127.0.0.1:9",
    )

    with pytest.raises(Refusal) as caught:
        provider.complete(PROMPT)

    assert caught.value.code is RefusalCode.PROVIDER_NOT_CONFIGURED
    leaked = str(caught.value) + repr(caught.value) + repr(caught.value.__cause__)
    assert "sk-or-v1" not in leaked


@pytest.mark.live_provider
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

    assert isinstance(completion.content, str) and completion.content.strip()
    assert isinstance(completion.charge, Decimal)
    assert completion.charge >= 0
    assert completion.generation_id
