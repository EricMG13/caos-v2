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
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from server.refusals import Refusal, RefusalCode

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 120.0

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
    """What one provider call returned, with nothing of the body kept."""

    content: str
    charge: Decimal
    generation_id: str


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
        if urllib.parse.urlsplit(url).scheme not in ALLOWED_SCHEMES:
            raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
        request = urllib.request.Request(
            url, data=body, headers=dict(headers), method="POST"
        )
        try:
            with _opener().open(request, timeout=timeout) as response:
                return int(response.status), bytes(response.read())
        except urllib.error.HTTPError as error:
            return int(error.code), bytes(error.read())


@dataclass(frozen=True, slots=True)
class OpenRouter:
    """One model, one identity, no fallbacks."""

    api_key: str
    model: str
    base_url: str = DEFAULT_BASE_URL
    transport: Transport = field(default_factory=UrllibTransport)

    def complete(self, prompt: str) -> Completion:
        """Ask once. Never twice: a retry is the caller's decision and its own
        reservation (`server/store/budget.py`)."""
        if not self.model:
            raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)

        status, body = self._post(prompt)
        if status in NEVER_RETRIED:
            raise Refusal(RefusalCode.PROVIDER_CALL_INVALID)
        if status in TRANSIENT or status >= 500:
            raise Refusal(RefusalCode.PROVIDER_UNAVAILABLE)
        if status != 200:
            raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
        return _completion(_decode(body))

    def _post(self, prompt: str) -> tuple[int, bytes]:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                # One run, one provider identity. A fallback would move the run
                # to a model its charges were never priced against.
                "provider": {"allow_fallbacks": False},
            }
        ).encode("utf-8")
        try:
            return self.transport.post(
                f"{self.base_url}/chat/completions",
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


def _decode(body: bytes) -> Mapping[str, Any]:
    try:
        decoded = json.loads(body, parse_float=Decimal)
    except (ValueError, UnicodeDecodeError):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID) from None
    if not isinstance(decoded, Mapping):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    return decoded


def _completion(body: Mapping[str, Any]) -> Completion:
    choice = _first_choice(body)
    finish_reason = str(choice.get("finish_reason", ""))
    refusal = _FINISH_REFUSALS.get(finish_reason)
    if refusal is not None:
        raise Refusal(refusal)

    message = choice.get("message")
    usage = body.get("usage")
    if not isinstance(message, Mapping) or not isinstance(usage, Mapping):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)

    cost = usage.get("cost")
    if not isinstance(cost, Decimal | int):
        # No cost is nothing to reconcile the reservation against, and a run
        # that cannot be charged cannot be stopped at its ceiling.
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)

    return Completion(
        content=str(message.get("content", "")),
        charge=Decimal(cost),
        generation_id=str(body.get("id", "")),
    )


def _first_choice(body: Mapping[str, Any]) -> Mapping[str, Any]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    first = choices[0]
    if not isinstance(first, Mapping):
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    return first
