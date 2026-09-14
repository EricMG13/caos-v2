"""The journey's test edge: a reverse proxy that plays the operator's OIDC edge.

It implements the brief's edge contract (Task 4.5 decision 2) and nothing more,
so the real-stack journey reaches the API the way production would:

- inbound `x-caos-user`, `x-forwarded-groups`, `x-caos-role` and
  `x-caos-edge-token`, every header whose name contains `_`, and the cookie
  header (its own session cookie; the API issues and reads none) are dropped;
- exactly one `x-caos-user`, `x-forwarded-groups` and `x-caos-edge-token` are
  set from the logged-in persona and the configured token;
- only `origin`, `sec-fetch-*`, `idempotency-key`, `last-event-id`,
  `content-type`, `content-length` and `accept` pass through, with the body;
- responses stream frame by frame, so SSE is unbuffered, with no read timeout.

`GET /_edge/login?persona=analyst|approver|intruder` stands in for the OIDC
login; any other request without a valid session is answered 401 here and
never reaches the API. Run with
`python -m uvicorn --factory journey.edge:from_environment --host 127.0.0.1
--port 18080` and `JOURNEY_UPSTREAM` / `CAOS_EDGE_TOKEN` set.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from uuid import UUID

import httpx
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send

SESSION_COOKIE = "caos_edge_session"
LOGIN_PATH = "/_edge/login"
EDGE_TOKEN_HEADER = "x-caos-edge-token"
UPSTREAM_ENV = "JOURNEY_UPSTREAM"
TOKEN_ENV = "CAOS_EDGE_TOKEN"

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
    "intruder": Persona(UUID("6a0e1c2d-0000-4000-8000-00000000a003"), "caos-analysts"),
}


def forwarded_headers(
    request: Request, persona: Persona, token: str
) -> list[tuple[str, str]]:
    """The allow-listed client headers, then exactly one of each identity header."""
    kept = [
        (name, value)
        for name, value in request.headers.items()
        if "_" not in name and (name in PASSED or name.startswith("sec-fetch-"))
    ]
    return [
        *kept,
        ("x-caos-user", str(persona.user_id)),
        ("x-forwarded-groups", persona.groups),
        (EDGE_TOKEN_HEADER, token),
    ]


def make_edge(
    upstream: str, token: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> ASGIApp:
    """The edge in front of `upstream`, proving itself with `token`."""
    sessions: dict[str, Persona] = {}
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
        # Recorded deviation (brief decision 11): over http://127.0.0.1 the
        # cookie cannot be `Secure`, so it also drops the `__Host-` prefix the
        # production contract names. HttpOnly and SameSite=Lax are kept.
        answer.set_cookie(
            SESSION_COOKIE, session, httponly=True, samesite="lax", path="/"
        )
        return answer

    async def proxy(request: Request, persona: Persona) -> Response:
        body = await request.body()
        # The raw target, so a percent-escape reaches the API as the client sent it.
        target = (request.scope.get("raw_path") or request.url.path.encode()).decode(
            "latin-1"
        )
        if request.scope["query_string"]:
            target += "?" + request.scope["query_string"].decode("latin-1")
        outbound = client.build_request(
            request.method,
            target,
            headers=forwarded_headers(request, persona, token),
            content=body or None,
        )
        answer = await client.send(outbound, stream=True)
        headers = {
            name: value
            for name, value in answer.headers.multi_items()
            if name.lower() not in HOP_BY_HOP
        }
        return StreamingResponse(
            answer.aiter_raw(),
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
        await response(scope, receive, send)

    return app


def from_environment() -> ASGIApp:
    """The uvicorn factory: upstream and token from the environment."""
    return make_edge(os.environ[UPSTREAM_ENV], os.environ[TOKEN_ENV])
