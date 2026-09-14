"""The edge guard: what a request must prove before anything else reads it.

Phase 4 Task 4.5, decisions 2 to 6 (recorded in `docs/DECISIONS.md` §53).

**The edge contract.** The operator's edge authenticates with OIDC and forwards
only to a private API listener. It strips every inbound `x-caos-user`,
`x-forwarded-groups`, `x-caos-role` and `x-caos-edge-token`, every header whose
name contains `_`, and its own session cookie; it then sets exactly one
`x-caos-user` (a UUID), one `x-forwarded-groups` and one `x-caos-edge-token`. It
passes `origin`, `sec-fetch-*`, `idempotency-key`, `last-event-id`,
`content-type` and `content-length` through. Its session cookie is
`__Host-`-prefixed, `Secure; HttpOnly; SameSite=Lax`, and SSE is unbuffered with
an idle timeout above 300 s. This process cannot detect an edge that fails to
strip a client's header; the duplicate and lookalike refusals below are what it
can do about one that appends instead of replacing.

**Two modes, decided by the environment on every use.**

- *Edge mode* (`CAOS_EDGE_TOKEN` set): the token must be at least 32 bytes,
  `CAOS_PUBLIC_ORIGIN` a bare `scheme://host[:port]`, and the development trust
  switch absent, or boot refuses `EDGE_CONFIG_INVALID` (and a request meeting
  such a configuration later is not trusted). Every request but `GET|HEAD
  /api/health` carries exactly one token equal in constant time, or it is
  answered 403 `EDGE_NOT_TRUSTED` before routing, identity or body.
- *Dev mode* (no token): served only when both socket ends are loopback
  addresses and `Host` is `localhost`, `127.0.0.1` or `[::1]`. A published port
  on a tokenless image therefore answers health and nothing else, and a DNS
  rebinding page is refused by its `Host`.

In both modes the token header is removed from the scope, so no application,
log or refusal downstream can hold it; a repeated or lookalike identity header
is 401 `NOT_AUTHENTICATED`; `/api` is checked for Origin and `Sec-Fetch-Site`
(the second half of Task 4.2's CSRF split); and every response carries the
security headers and policy, with no cookie and no CORS header.

No header value is ever logged, formatted into a body or compared outside
`hmac.compare_digest`: the refusal bodies are constants.
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from server.api.identity import (
    EDGE_TOKEN_ENV,
    GROUPS_HEADER,
    ROLE_HEADER,
    SUBJECT_HEADER,
    TRUST_SWITCH,
)
from server.api.wire import CLEARS, RefusalBody
from server.refusals import Refusal, RefusalCode

# Pure: the guard reads the environment and the scope, never the store.
IO_BUDGET = 0

PUBLIC_ORIGIN_ENV = "CAOS_PUBLIC_ORIGIN"
EDGE_TOKEN_HEADER = "x-caos-edge-token"  # nosec B105 -- a header name, not a secret
MIN_TOKEN_BYTES = 32

HEALTH_PATH = "/api/health"
_SAFE = frozenset({"GET", "HEAD"})
_IDENTITY = frozenset({SUBJECT_HEADER, GROUPS_HEADER, ROLE_HEADER})
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
_HOST = re.compile(r"^(?P<name>localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?$")
# Loopback only, and only when no public origin is configured (`_origin_allowed`):
# these never leave the machine, so there is no transport to secure. A production
# deployment sets `CAOS_PUBLIC_ORIGIN` and this set is not consulted at all.
DEV_ORIGINS = frozenset(
    f"http://{host}:{port}"  # NOSONAR S5332 -- loopback, never a network hop
    for host in _LOOPBACK_HOSTS
    for port in (5173, 8000)
)

SECURITY_HEADERS: Mapping[str, str] = {
    "content-security-policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'; object-src 'none'; "
        "require-trusted-types-for 'script'; trusted-types 'none'"
    ),
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
}
_STRIPPED = (b"set-cookie", b"cache-control")
_ASSET_CACHE = "public, max-age=31536000, immutable"


@dataclass(frozen=True, slots=True)
class EdgeMode:
    """Edge mode when `token` is set; dev mode when both are `None`."""

    token: bytes | None
    public_origin: str | None


def resolve_mode(environ: Mapping[str, str] | None = None) -> EdgeMode:
    """The mode this environment declares, or `EDGE_CONFIG_INVALID`."""
    env = os.environ if environ is None else environ
    token = env.get(EDGE_TOKEN_ENV)
    if token is None:
        return EdgeMode(token=None, public_origin=None)
    encoded = token.encode()
    origin = env.get(PUBLIC_ORIGIN_ENV)
    if (
        len(encoded) < MIN_TOKEN_BYTES
        or TRUST_SWITCH in env
        or origin is None
        or not _bare_origin(origin)
    ):
        raise Refusal(RefusalCode.EDGE_CONFIG_INVALID)
    return EdgeMode(token=encoded, public_origin=origin)


def _bare_origin(value: str) -> bool:
    """`scheme://host[:port]` exactly as a browser serialises an Origin."""
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if parts.username is not None or parts.password is not None:
        return False
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    rebuilt = f"{parts.scheme}://{host}" + (f":{port}" if port is not None else "")
    return rebuilt == value


def _loopback(address: object) -> bool:
    if not isinstance(address, (list, tuple)) or not address:
        return False
    try:
        return ipaddress.ip_address(str(address[0])).is_loopback
    except ValueError:
        return False


def _all(headers: list[tuple[bytes, bytes]], name: str) -> list[bytes]:
    wanted = name.encode()
    return [value for key, value in headers if key.lower() == wanted]


class EdgeGuard:
    """Pure ASGI middleware in front of the API and the static site."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(scope, receive, send)
            return
        if scope["type"] != "http" or scope.get("caos.edge_guarded"):
            # Nothing here serves a websocket; the guard never wraps twice.
            if scope["type"] == "http":
                await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        refusal = self._refusal(scope, path)
        # The token is gone before any other code -- a refusal included -- runs.
        token_name = EDGE_TOKEN_HEADER.encode()
        scope["headers"] = [
            (key, value)
            for key, value in scope.get("headers", [])
            if key.lower() != token_name
        ]
        scope["caos.edge_guarded"] = True
        guarded = _secured(send, path)
        if refusal is not None:
            code, status = refusal
            await _refuse(guarded, code, status)
            return
        started = False

        async def tracked(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await guarded(message)

        try:
            await self.app(scope, receive, tracked)
        except Exception:
            # Starlette's error middleware sits outside this one, so its 500
            # would skip the policy. Answer here first; it sees the response
            # started, sends nothing, and still logs the fault.
            if not started:
                await _refuse(guarded, RefusalCode.INTERNAL_FAULT, 500)
            raise

    async def _lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Refuse to start under an invalid edge configuration.

        The failure is sent as `lifespan.startup.failed` before raising, because
        a server whose lifespan mode is "auto" treats a bare exception as a
        missing lifespan protocol and serves anyway.
        """
        if scope.get("caos.edge_guarded"):
            await self.app(scope, receive, send)
            return
        try:
            resolve_mode()
        except Refusal:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send(
                    {
                        "type": "lifespan.startup.failed",
                        "message": RefusalCode.EDGE_CONFIG_INVALID.value,
                    }
                )
            raise
        scope["caos.edge_guarded"] = True
        await self.app(scope, receive, send)

    def _refusal(self, scope: Scope, path: str) -> tuple[RefusalCode, int] | None:
        method = scope.get("method", "")
        headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []))
        health = path == HEALTH_PATH and method in _SAFE
        try:
            mode = resolve_mode()
        except Refusal:
            return None if health else (RefusalCode.EDGE_NOT_TRUSTED, 403)
        if health:
            return None
        if not self._trusted(mode, scope, headers):
            return RefusalCode.EDGE_NOT_TRUSTED, 403
        if not _hygienic(headers):
            return RefusalCode.NOT_AUTHENTICATED, 401
        if (path == "/api" or path.startswith("/api/")) and not _origin_allowed(
            mode, method, headers
        ):
            return RefusalCode.ORIGIN_REFUSED, 403
        return None

    @staticmethod
    def _trusted(
        mode: EdgeMode, scope: Scope, headers: list[tuple[bytes, bytes]]
    ) -> bool:
        if mode.token is not None:
            presented = _all(headers, EDGE_TOKEN_HEADER)
            return len(presented) == 1 and hmac.compare_digest(presented[0], mode.token)
        if not (_loopback(scope.get("client")) and _loopback(scope.get("server"))):
            return False
        hosts = _all(headers, "host")
        return len(hosts) == 1 and _HOST.match(hosts[0].decode("latin-1")) is not None


def _hygienic(headers: list[tuple[bytes, bytes]]) -> bool:
    """At most one of each identity header, and no lookalike of any."""
    seen: dict[str, int] = {}
    for raw, _ in headers:
        name = raw.decode("latin-1")
        canonical = name.lower().replace("_", "-")
        if canonical not in _IDENTITY:
            continue
        if name != canonical:
            return False
        seen[canonical] = seen.get(canonical, 0) + 1
        if seen[canonical] > 1:
            return False
    return True


def _origin_allowed(
    mode: EdgeMode, method: str, headers: list[tuple[bytes, bytes]]
) -> bool:
    allowed = DEV_ORIGINS if mode.public_origin is None else {mode.public_origin}
    sites = _all(headers, "sec-fetch-site")
    origins = _all(headers, "origin")
    if len(sites) > 1 or len(origins) > 1:
        return False
    site = sites[0].decode("latin-1") if sites else None
    origin = origins[0].decode("latin-1") if origins else None
    if origin is not None and origin not in allowed:
        return False
    # `cross-site`, `same-site` and any unknown value fall through both rules.
    if method in _SAFE:
        return site in (None, "none", "same-origin")
    return site == "same-origin" or (site is None and origin is not None)


def _secured(send: Send, path: str) -> Send:
    """Every response start gains the policy and loses any cookie or CORS."""
    if path == "/api" or path.startswith("/api/"):
        cache = "no-store"
    elif path.startswith("/assets/"):
        cache = _ASSET_CACHE
    else:
        cache = "no-cache"

    async def wrapped(message: Message) -> None:
        if message["type"] == "http.response.start":
            kept = [
                (key, value)
                for key, value in message.get("headers", [])
                if key.lower() not in _STRIPPED
                and key.lower() not in SECURITY_HEADERS_BYTES
                and not key.lower().startswith(b"access-control-")
            ]
            kept.extend(SECURITY_HEADER_PAIRS)
            kept.append((b"cache-control", cache.encode()))
            message = {**message, "headers": kept}
        await send(message)

    return wrapped


SECURITY_HEADER_PAIRS = tuple(
    (name.encode(), value.encode()) for name, value in SECURITY_HEADERS.items()
)
SECURITY_HEADERS_BYTES = frozenset(name for name, _ in SECURITY_HEADER_PAIRS)


async def _refuse(send: Send, code: RefusalCode, status: int) -> None:
    body = RefusalBody(code=code, clears=CLEARS[code]).model_dump_json().encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
