"""The journey's test edge: a reverse proxy that plays the operator's OIDC edge.

It implements the brief's edge contract (Task 4.5 decision 2, and §93's
signed assertion) and nothing more, so the real-stack journey reaches the API
the way production would:

- only `origin`, `sec-fetch-*`, `idempotency-key`, `last-event-id`,
  `content-type`, `content-length` and `accept` pass through, with the body --
  so inbound `x-caos-user`, `x-forwarded-groups`, `x-caos-role`,
  `x-caos-edge-assertion`, every header whose name contains `_`, and the
  cookie header (its own session cookie; the API issues and reads none) are
  dropped by construction, never by a deny list;
- exactly one `x-caos-edge-assertion` is set, signed under the configured key
  over the logged-in persona's subject and groups, this request's method and
  raw target, the current second and a fresh nonce -- a retried connect signs
  again, so no nonce is ever sent twice;
- responses stream frame by frame, so SSE is unbuffered, with no read timeout.

It serves TLS (`tests/journey/run.py` mints a throwaway certificate per run),
so its session cookie is the contract's: `__Host-` prefixed, `Secure`,
`HttpOnly`, `SameSite=Lax`.

An event stream is certain to be cut -- the browser navigates away from the
page tailing it, the API's tail deadline or the stack's teardown closes it --
and that is logged as one line naming the class, never as a traceback: an
unhandled `Exception in ASGI application` on every green run teaches a reader
to scroll past tracebacks. Only an event stream the upstream cuts ends early
quietly -- a cut JSON body presented as complete would be an answer nobody
sent -- and any other failure still raises. A browser that has gone is logged
the same way whatever it was reading, since nobody is left to mislead.

`GET /_edge/login?persona=analyst|approver|filer|reader|intruder` stands in for
the OIDC login; any other request without a valid session is answered 401
here and never reaches the API. Run with
`python -m uvicorn --factory journey.edge:from_environment --host 127.0.0.1
--port 18080 --ssl-keyfile ... --ssl-certfile ...` and `JOURNEY_UPSTREAM` /
`CAOS_EDGE_TOKEN` set.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from uuid import UUID

import httpx
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect, Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from server.api.edge import EDGE_ASSERTION_HEADER, NONCE_HEX_CHARS, sign_assertion

SESSION_COOKIE = "__Host-caos_edge_session"
LOGIN_PATH = "/_edge/login"
UPSTREAM_ENV = "JOURNEY_UPSTREAM"
KEY_ENV = "CAOS_EDGE_TOKEN"
# How long a GET waits for an unreachable upstream (a restarting API) before
# the edge answers 502, as an operator's proxy retries a refused connect.
UPSTREAM_WAIT_SECONDS = 30.0

PASSED = frozenset(
    {
        "origin",
        "idempotency-key",
        "last-event-id",
        "content-type",
        "content-length",
        "accept",
    }
)
LOGGER = logging.getLogger("journey.edge")
EVENT_STREAM = "text/event-stream"

# Hop-by-hop response headers (RFC 9110 §7.6.1) are this hop's, not the client's.
HOP_BY_HOP = frozenset(
    {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade"}
)


@dataclass(frozen=True, slots=True)
class Persona:
    """A fixed identity the edge asserts after its stand-in login."""

    user_id: UUID
    groups: str


PERSONAS = {
    "analyst": Persona(UUID("6a0e1c2d-0000-4000-8000-00000000a001"), "caos-analysts"),
    "approver": Persona(UUID("6a0e1c2d-0000-4000-8000-00000000a002"), "caos-analysts"),
    "reader": Persona(UUID("6a0e1c2d-0000-4000-8000-00000000a004"), "caos-readers"),
    "intruder": Persona(UUID("6a0e1c2d-0000-4000-8000-00000000a003"), "caos-analysts"),
    # The filing chain needs three independent approvers
    # (`APPROVER_NOT_INDEPENDENT`), and Task 12.5's journey drives it through
    # this edge: the analyst signs, the approver freezes, and this third
    # identity files. Deliberately not the intruder -- that persona's whole
    # point is holding no standing on the journey's case, and granting it
    # standing to file would take that proof away from the test above it.
    "filer": Persona(UUID("6a0e1c2d-0000-4000-8000-00000000a005"), "caos-analysts"),
}


def assertion_for(request: Request, persona: Persona, key: bytes) -> str:
    """This request's assertion: the persona, the method and raw target, now,
    and a nonce minted here and nowhere else."""
    return sign_assertion(
        key,
        subject=str(persona.user_id),
        groups=persona.groups.split(","),
        method=request.method,
        target=raw_target(request),
        issued_at=int(time.time()),
        nonce=secrets.token_hex(NONCE_HEX_CHARS // 2),
    )


def forwarded_headers(
    request: Request, persona: Persona, key: bytes
) -> list[tuple[str, str]]:
    """The allow-listed client headers, then exactly one signed assertion."""
    kept = [
        (name, value)
        for name, value in request.headers.items()
        if "_" not in name and (name in PASSED or name.startswith("sec-fetch-"))
    ]
    return [*kept, (EDGE_ASSERTION_HEADER, assertion_for(request, persona, key))]


def raw_target(request: Request) -> str:
    """The raw target, so a percent-escape reaches the API as the client sent it."""
    target = (request.scope.get("raw_path") or request.url.path.encode()).decode(
        "latin-1"
    )
    if request.scope["query_string"]:
        target += "?" + request.scope["query_string"].decode("latin-1")
    return target


def response_headers(answer: httpx.Response) -> dict[str, str]:
    """The upstream's headers without the hop-by-hop ones."""
    return {
        name: value
        for name, value in answer.headers.multi_items()
        if name.lower() not in HOP_BY_HOP
    }


def _cut(target: str, cause: type[BaseException]) -> None:
    """The one line a cut event stream costs: the class and the target, never
    the exception's text."""
    LOGGER.warning("edge: event stream %s ended by %s", target, cause.__name__)


def is_event_stream(answer: httpx.Response) -> bool:
    media: str = answer.headers.get("content-type", "")
    return media.split(";")[0].strip().lower() == EVENT_STREAM


async def relay(answer: httpx.Response, target: str) -> AsyncIterator[bytes]:
    """The upstream body frame by frame. An event stream the upstream closes
    mid-body ends here; anything else it raises is raised."""
    stream = is_event_stream(answer)
    try:
        async for frame in answer.aiter_raw():
            yield frame
    except httpx.RemoteProtocolError:
        if not stream:
            raise
        _cut(target, httpx.RemoteProtocolError)


async def answer_client(
    response: Response, target: str, scope: Scope, receive: Receive, send: Send
) -> None:
    """Send `response`; a browser gone mid-stream ends it with one line."""
    try:
        await response(scope, receive, send)
    except ClientDisconnect:
        # An ASGI 2.4 server raises into `send` once the browser has gone, and
        # Starlette turns that into this. Nothing is left to answer.
        if not isinstance(response, StreamingResponse):
            raise
        _cut(target, ClientDisconnect)


async def send_upstream(
    client: httpx.AsyncClient, build: Callable[[], httpx.Request], *, retry: bool
) -> httpx.Response:
    """Send upstream; a GET waits out a refused connect (a restarting API).

    Only a connect that never reached the API is retried, so nothing is sent
    twice, and an unsafe method is never retried. `build` is called per
    attempt, so each carries its own nonce and second.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (UPSTREAM_WAIT_SECONDS if retry else 0.0)
    while True:
        try:
            return await client.send(build(), stream=True)
        except httpx.ConnectError:
            if loop.time() >= deadline:
                raise
            await asyncio.sleep(0.25)


def make_edge(
    upstream: str, key: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> ASGIApp:
    """The edge in front of `upstream`, signing each request under `key`."""
    sessions: dict[str, Persona] = {}
    signing_key = key.encode()
    client = httpx.AsyncClient(
        base_url=upstream,
        transport=transport,
        timeout=httpx.Timeout(10.0, read=None),
        follow_redirects=False,
    )

    async def login(request: Request) -> Response:
        persona = PERSONAS.get(request.query_params.get("persona", ""))
        if persona is None:
            return PlainTextResponse("unknown persona", status_code=400)
        session = secrets.token_urlsafe(32)
        sessions[session] = persona
        answer = PlainTextResponse("logged in")
        # The contract's cookie (decision 2): `__Host-` needs Secure, path=/
        # and no domain, which the TLS edge `tests/journey/run.py` starts can
        # now satisfy.
        answer.set_cookie(
            SESSION_COOKIE,
            session,
            secure=True,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return answer

    async def proxy(request: Request, persona: Persona) -> Response:
        body = await request.body()
        target = raw_target(request)

        def outbound() -> httpx.Request:
            return client.build_request(
                request.method,
                target,
                headers=forwarded_headers(request, persona, signing_key),
                content=body or None,
            )

        try:
            answer = await send_upstream(
                client, outbound, retry=request.method == "GET"
            )
        except httpx.ConnectError:
            return PlainTextResponse("upstream unreachable", status_code=502)
        headers = response_headers(answer)
        return StreamingResponse(
            relay(answer, request.url.path),
            status_code=answer.status_code,
            headers=headers,
            background=BackgroundTask(answer.aclose),
        )

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        request = Request(scope, receive)
        if request.method == "GET" and request.url.path == LOGIN_PATH:
            response = await login(request)
        else:
            persona = sessions.get(request.cookies.get(SESSION_COOKIE, ""))
            if persona is None:
                response = PlainTextResponse("no session", status_code=401)
            else:
                response = await proxy(request, persona)
        await answer_client(response, request.url.path, scope, receive, send)

    return app


def from_environment() -> ASGIApp:
    """The uvicorn factory: upstream and key from the environment."""
    return make_edge(os.environ[UPSTREAM_ENV], os.environ[KEY_ENV])
