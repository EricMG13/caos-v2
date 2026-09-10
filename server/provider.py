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


@dataclass(frozen=True, slots=True)
class UrllibTransport:
    """`urllib.request`, and no vendor SDK."""

    def post(
        self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
    ) -> tuple[int, bytes]:
        request = urllib.request.Request(
            url, data=body, headers=dict(headers), method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
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
