"""The provider: one POST, one JSON body, and a closed set of refusals.

`docs/DECISIONS.md` §16. The standard library rather than a vendor SDK, for three
stated reasons: retries are unwanted (a retry is a new reservation, not a second
chance at the same one), a non-streaming call returns one JSON body, and the
chat-completions shape is stable.

Nothing here quotes the response. A completion echoes the prompt and the prompt
carries evidence, so a refusal that included the body -- or the vendor's error
string, which often contains it -- would be the leak `server/refusals.py` exists
to prevent. Every raise is `from None` for the same reason: an exception chain is
a log line waiting to happen.

The charge is `usage.cost` read with `parse_float=Decimal`. Reading it as a float
first and converting after has already lost the cent (invariant 7).
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, DecimalException
from typing import Any, Protocol

from server.refusals import Refusal, RefusalCode
from server.store.budget import validate_spend
from server.store.outcomes import producer_identifier

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 120.0
# Host resource ceilings, not guarantees that every canonical handoff fits.
# Oversized requests/responses refuse; no prefix is accepted as a whole answer.
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 4_194_304
MAX_COMPLETION_TOKENS = 32_768

# A call that cannot succeed by being repeated. Retrying one of these spends a
# second reservation on the same certain failure.
NEVER_RETRIED = frozenset({400, 401, 402, 403, 404, 413, 422})
# A call whose outcome is unknown. The attempt stays indeterminate and keeps its
# reservation, because it may have reached the provider and may be billed.
TRANSIENT = frozenset({408, 429})

_FINISH_REFUSALS = {
    "length": RefusalCode.PROVIDER_OUTPUT_TRUNCATED,
    "content_filter": RefusalCode.PROVIDER_REFUSED,
}


@dataclass(frozen=True, slots=True)
class Completion:
    """Independent call facts beside usable content or an analytical refusal.

    None is unknown, never zero. Failed analytical content is discarded.
    A returned refusal describes a call; pre-send rejection raises Refusal.
    """

    content: str | None = field(repr=False)
    charge: Decimal | None
    generation_id: str | None = field(repr=False)
    refusal: RefusalCode | None = None


class Transport(Protocol):
    """The network, behind one method, so the refusal table can be tested
    without one. The default implementation is `urllib`, as §16 requires."""

    def post(
        self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
    ) -> tuple[int, bytes]: ...


# HTTPS only. The prompt carries evidence and the header carries the key, so
# there is no request this makes that may cross a network in clear text -- and
# `http` in this set is the whole of what "clear-text protocol" findings are
# about. A self-hosted endpoint that speaks only `http` is a decision entry, not
# a default.
ALLOWED_SCHEMES = frozenset({"https"})


def _check_url(url: str) -> None:
    if any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    try:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme in ALLOWED_SCHEMES and parts.hostname and parts.port != 0:
            return
    except ValueError:
        pass
    raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED) from None


def _opener() -> urllib.request.OpenerDirector:
    """An opener that can only speak HTTPS.

    `urllib.request.urlopen` uses the default opener, which also handles
    `file:`, `ftp:`, `data:` and plain `http:` -- so a base URL that ever came
    from configuration could read a local file, or send the key and the prompt
    across a network in clear text, instead of calling a provider. This director
    is built from nothing and given one transport handler, so the other schemes
    are not merely discouraged, they are absent.

    No redirect handler either: a provider that answers 3xx is not one this code
    understands, and following the redirect is how a permitted scheme turns into
    a forbidden one.

    `HTTPDefaultErrorHandler` is the one that is easy to leave out, and it is not
    optional. `HTTPErrorProcessor` does not raise on a non-2xx; it hands the
    response to this director's error machinery, which raises `HTTPError` only
    because this handler is registered to do it. Without it that lookup is a bare
    `KeyError`, `post`'s `except urllib.error.HTTPError` below never runs, and
    every 401, 429 and 5xx leaves this boundary as an untyped crash carrying the
    vendor's message -- which is the whole of what §16 says must not travel. It
    raises and opens nothing, so the scheme set above is unchanged.
    """
    director = urllib.request.OpenerDirector()
    director.add_handler(urllib.request.HTTPSHandler())
    director.add_handler(urllib.request.HTTPErrorProcessor())
    director.add_handler(urllib.request.HTTPDefaultErrorHandler())
    return director


@dataclass(frozen=True, slots=True)
class UrllibTransport:
    """`urllib.request`, and no vendor SDK."""

    def post(
        self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
    ) -> tuple[int, bytes]:
        if not isinstance(body, bytes) or len(body) > MAX_REQUEST_BYTES:
            raise Refusal(RefusalCode.PROVIDER_CALL_INVALID)
        try:
            _check_url(url)
            request = urllib.request.Request(
                url, data=body, headers=dict(headers), method="POST"
            )
        except ValueError:
            raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED) from None
        try:
            with _opener().open(request, timeout=timeout) as response:
                return int(response.status), _read_body(response)
        except urllib.error.HTTPError as error:
            with error:
                return int(error.code), _read_body(error)


def _read_body(response: http.client.HTTPResponse | urllib.error.HTTPError) -> bytes:
    body = _response_bytes(response.read(MAX_RESPONSE_BYTES + 1))
    # HTTPResponse.read(size) tolerates early EOF with Content-Length remaining.
    # HTTPError delegates this native framing state to its underlying response.
    remaining = getattr(response, "length", None)
    if remaining is not None and remaining > 0:
        raise Refusal(RefusalCode.PROVIDER_UNAVAILABLE) from None
    return body


def _response_bytes(body: bytes) -> bytes:
    if not isinstance(body, bytes) or len(body) > MAX_RESPONSE_BYTES:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID) from None
    return body


class CompletionProvider(Protocol):
    """Anything that can answer a prompt with a `Completion`.

    Named for what it returns rather than for who implements it: the module
    executor depends on this, and `server/engine/runtime.py`'s `Provider` is a
    different shape for a different job -- one takes a prompt, the other takes a
    route node. Keeping them apart is what stops a test double for one being
    accepted where the other was meant.
    """

    @property
    def model(self) -> str:
        """The identity the host configured, which with fallbacks off is the
        identity that answers.

        Read from here rather than from the response body: a model naming
        itself is a claim, and invariant 3 says the host owns identity.

        A property rather than a plain annotation, so a frozen implementer
        satisfies it. `model: str` on a Protocol is a read-write member, and
        `OpenRouter` is frozen — declaring the mutable form would have made the
        real provider fail to satisfy its own protocol, which the type checker
        caught before a caller did.
        """

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion: ...


@dataclass(frozen=True, slots=True)
class OpenRouter:
    """One model, one identity, no fallbacks."""

    # Out of the repr, which is what a failed assertion, a debugger and a log
    # line all print (§16: the key never appears in a log).
    api_key: str = field(repr=False)
    model: str
    base_url: str = DEFAULT_BASE_URL
    transport: Transport = field(default_factory=UrllibTransport)

    @classmethod
    def from_environment(cls) -> OpenRouter:
        """The provider the environment configures, or `PROVIDER_NOT_CONFIGURED`.

        §16's three names and nothing else: no dotenv library, no profile on
        disk. Read at the call rather than at import, so a process started
        before the key was set picks it up once it is. A missing key is refused
        here rather than left to the provider's 401, which costs a round trip to
        say the same thing.
        """
        key = os.environ.get("OPENROUTER_API_KEY", "")
        model = os.environ.get("OPENROUTER_MODEL", "")
        if not key or not model:
            raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
        return cls(
            api_key=key,
            model=model,
            base_url=os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL,
        )

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        """Ask once. Never twice: a retry is the caller's decision and its own
        reservation (`server/store/budget.py`).

        `json_object` asks the provider to constrain its own output to a JSON
        object. It is a narrowing, never a guarantee: the envelope is still
        parsed and validated by the host, because a module's claim about its own
        output is exactly what invariant 3 says never survives.
        """
        if producer_identifier(self.model, limit=256) is None:
            raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)

        try:
            status, body = self._post(prompt, json_object=json_object)
        except Refusal as failed:
            if failed.code not in {
                RefusalCode.PROVIDER_UNAVAILABLE,
                RefusalCode.PROVIDER_RESPONSE_INVALID,
            }:
                raise
            return Completion(None, None, None, failed.code)

        refusal = None
        if status in NEVER_RETRIED:
            refusal = RefusalCode.PROVIDER_CALL_INVALID
        elif status in TRANSIENT or status >= 500:
            refusal = RefusalCode.PROVIDER_UNAVAILABLE
        elif status != 200:
            refusal = RefusalCode.PROVIDER_RESPONSE_INVALID
        try:
            decoded = _decode(body)
        except Refusal as failed:
            return Completion(None, None, None, refusal or failed.code)
        return _completion(decoded, refusal=refusal)

    def _post(self, prompt: str, *, json_object: bool = False) -> tuple[int, bytes]:
        if not isinstance(prompt, str) or len(prompt) > MAX_REQUEST_BYTES:
            raise Refusal(RefusalCode.PROVIDER_CALL_INVALID)
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            # One run, one provider identity. A fallback would move the run
            # to a model its charges were never priced against.
            "provider": {"allow_fallbacks": False, "require_parameters": True},
        }
        if json_object:
            request["response_format"] = {"type": "json_object"}
        payload = json.dumps(request).encode("utf-8")
        if len(payload) > MAX_REQUEST_BYTES:
            raise Refusal(RefusalCode.PROVIDER_CALL_INVALID)
        try:
            url = f"{self.base_url}/chat/completions"
            _check_url(url)
            status, body = self.transport.post(
                url,
                payload,
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                TIMEOUT_SECONDS,
            )
        except (OSError, http.client.HTTPException):
            # Everything a socket can do: refused, reset, timed out, DNS gone,
            # a truncated chunked body. `urllib.error.URLError` and
            # `TimeoutError` are both `OSError`, so this is the whole surface
            # without catching the blind `Exception` CLAUDE.md forbids.
            #
            # Indeterminate, not failed: the request may have been delivered, so
            # the attempt keeps its reservation. The exception is dropped rather
            # than wrapped, because its string carries the URL and sometimes the
            # body.
            raise Refusal(RefusalCode.PROVIDER_UNAVAILABLE) from None
        except ValueError:
            # A request `http.client` will not build: a key with a line ending
            # attached is the one a configuration produces. Certain rather than
            # indeterminate -- nothing was sent -- and the message is the header
            # itself, `Bearer` and the key.
            raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED) from None
        return status, _response_bytes(body)


def _decode(body: bytes) -> Mapping[str, Any]:
    try:
        decoded = json.loads(
            body, parse_float=Decimal, object_pairs_hook=_unambiguous_object
        )
    except (ValueError, UnicodeDecodeError, DecimalException, RecursionError):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID) from None
    if not isinstance(decoded, Mapping):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    return decoded


def _unambiguous_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Duplicate members are unknown; independent sibling facts survive."""
    members: dict[str, Any] = {}
    for name, value in pairs:
        members[name] = None if name in members else value
    return members


def _reported_charge(value: object) -> Decimal | None:
    if type(value) is int:
        value = Decimal(value)
    if isinstance(value, Decimal):
        try:
            validate_spend(value)
        except Refusal:
            return None
        return value
    return None


def _completion(
    body: Mapping[str, Any], *, refusal: RefusalCode | None = None
) -> Completion:
    usage = body.get("usage")
    charge = _reported_charge(usage.get("cost") if isinstance(usage, Mapping) else None)
    generation = producer_identifier(body.get("id"), limit=512)
    if refusal is not None:
        return Completion(None, charge, generation, refusal)
    try:
        content = _content(body)
    except Refusal as failed:
        return Completion(None, charge, generation, failed.code)
    if charge is None or generation is None:
        return Completion(
            None, charge, generation, RefusalCode.PROVIDER_RESPONSE_INVALID
        )
    return Completion(content, charge, generation)


def _content(body: Mapping[str, Any]) -> str:
    choice = _first_choice(body)
    finish_reason = choice.get("finish_reason")
    if not isinstance(finish_reason, str):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    refusal = _FINISH_REFUSALS.get(finish_reason)
    if refusal is not None:
        raise Refusal(refusal)
    message = choice.get("message")
    if finish_reason != "stop" or not isinstance(message, Mapping):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    content = message.get("content")
    if not isinstance(content, str):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    return content


def _first_choice(body: Mapping[str, Any]) -> Mapping[str, Any]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    first = choices[0]
    if not isinstance(first, Mapping):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    return first
