"""The journey's test edge, deterministic worker, pack and orchestrator (4.5e1).

The edge is where the brief's edge contract (decision 2) is pinned on the test
side: the backend cannot detect an edge that fails to strip client identity, so
this suite is what says the one the journey uses does.

The upstream here is a handler behind a bare `httpx.AsyncBaseTransport` rather
than an ASGI app behind `httpx.ASGITransport` (or an `httpx.MockTransport`):
both of those read the whole body before answering, so a gated event stream
would deadlock and a streaming test could not tell whether the edge buffers.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import subprocess
import time
from collections.abc import AsyncIterator
from pathlib import Path
from threading import Event
from uuid import UUID

import httpx
import pytest
from conftest import approve_run
from journey import edge, pack, run, worker
from lite_route_fixtures import RealisticLiteCompletions
from starlette.types import ASGIApp, Message
from test_runtime import blobs, bundle, route

from server.api.edge import (
    EDGE_ASSERTION_HEADER,
    Asserted,
    NonceRegister,
    verify_assertion,
)
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute
from server.engine.worker import WorkerConfig, work_once
from server.evidence.extract import dispatch_by_content
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import Bundle
from server.pricing import worst_case
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.runs import run_status, start_run
from server.store.work import enqueue_run

__all__ = ["blobs", "bundle", "route"]

KEY = "t" * 40
UPSTREAM = "http://upstream.invalid"
# The edge's own origin is TLS (§93): its `Secure` cookie is only ever sent
# back over https, so the clients here say so, and `ASGITransport` never
# opens a socket either way.
EDGE_ORIGIN = "https://127.0.0.1:18080"
JOURNEY = Path(__file__).resolve().parent / "journey"


class _Upstream:
    """Records every request it receives; `/events` streams two SSE events,
    the second only once the test opens `gate`."""

    def __init__(self) -> None:
        self.seen: list[httpx.Request] = []
        self.bodies: list[bytes] = []
        self.gate = asyncio.Event()

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        self.bodies.append(await request.aread())
        if request.url.path == "/api/v1/events":
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=self._events(),
            )
        return httpx.Response(
            200, headers={"content-type": "application/json"}, content=self._ok()
        )

    async def _ok(self) -> AsyncIterator[bytes]:
        yield b'{"ok":true}'

    async def _events(self) -> AsyncIterator[bytes]:
        yield b"id: 1\ndata: first\n\n"
        await self.gate.wait()
        yield b"id: 2\ndata: second\n\n"


class _Unbuffered(httpx.AsyncBaseTransport):
    def __init__(self, upstream: _Upstream) -> None:
        self.upstream = upstream

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self.upstream(request)


def _edge(upstream: _Upstream) -> ASGIApp:
    return edge.make_edge(UPSTREAM, KEY, transport=_Unbuffered(upstream))


async def _logged_in(client: httpx.AsyncClient, persona: str) -> None:
    answer = await client.get("/_edge/login", params={"persona": persona})
    assert answer.status_code == 200
    cookie = answer.headers["set-cookie"].lower()
    # The contract's cookie, whole: `__Host-` needs `Secure` and `path=/`.
    assert cookie.startswith("__host-")
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "path=/" in cookie and "domain=" not in cookie


def _asserted(request: httpx.Request) -> Asserted:
    """What the edge's assertion on `request` proves, verified as the API
    verifies it: under the key, for this method and target, now."""
    [presented] = [
        value
        for name, value in request.headers.multi_items()
        if name.lower() == EDGE_ASSERTION_HEADER
    ]
    target = request.url.raw_path.decode("latin-1")
    verdict = verify_assertion(
        KEY.encode(),
        presented.encode(),
        method=request.method,
        target=target,
        now=time.time(),
        nonces=NonceRegister(),
    )
    assert verdict is not None, "the edge's assertion did not verify"
    return verdict


def test_the_test_edge_strips_every_client_identity_header_and_sets_one_of_each() -> (
    None
):
    upstream = _Upstream()

    async def scenario() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=_edge(upstream))
        async with httpx.AsyncClient(
            transport=transport, base_url=EDGE_ORIGIN
        ) as client:
            anonymous = await client.get("/api/v1/cases")
            await _logged_in(client, "analyst")
            forged = [
                ("x-caos-user", "00000000-0000-0000-0000-000000000666"),
                ("X-CAOS-USER", "00000000-0000-0000-0000-000000000667"),
                ("x-forwarded-groups", "caos-admins"),
                ("x-caos-role", "ADMIN"),
                ("x-caos-edge-token", "forged"),
                ("x-caos-edge-assertion", "forged"),
                ("origin", EDGE_ORIGIN),
                ("sec-fetch-site", "same-origin"),
                ("idempotency-key", "key-1"),
                ("content-type", "application/json"),
            ]
            posted = await client.post(
                "/api/v1/cases", headers=httpx.Headers(forged), content=b'{"a":1}'
            )
            await _logged_in(client, "intruder")
            intruder = await client.get("/api/v1/cases")
            return [anonymous, posted, intruder]

    anonymous, posted, intruder = asyncio.run(scenario())

    assert anonymous.status_code == 401, "no session: the edge answers itself"
    assert posted.status_code == 200 and intruder.status_code == 200
    assert len(upstream.seen) == 2, "the anonymous request never left the edge"
    first, second = upstream.seen
    names = [name.lower() for name, _ in first.headers.multi_items()]
    assert names.count(EDGE_ASSERTION_HEADER) == 1
    # No identity header at all: the subject and groups travel inside the
    # assertion, and the forged ones never left the edge.
    for header in (
        "x-caos-user",
        "x-forwarded-groups",
        "x-caos-role",
        "x-caos-edge-token",
    ):
        assert header not in names, header
    analyst = edge.PERSONAS["analyst"]
    assert _asserted(first) == Asserted(str(analyst.user_id), (analyst.groups,))
    for passed in ("origin", "sec-fetch-site", "idempotency-key", "content-type"):
        assert names.count(passed) == 1, passed
    assert first.headers["idempotency-key"] == "key-1"
    assert upstream.bodies[0] == b'{"a":1}'
    assert _asserted(second).subject == str(edge.PERSONAS["intruder"].user_id)
    assert len({p.user_id for p in edge.PERSONAS.values()}) == len(edge.PERSONAS)


def test_the_test_edge_forwards_no_cookie_or_underscore_header_and_streams_sse() -> (
    None
):
    upstream = _Upstream()
    app = _edge(upstream)

    async def login() -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url=EDGE_ORIGIN
        ) as client:
            answer = await client.get("/_edge/login", params={"persona": "approver"})
            bad = await client.get("/_edge/login", params={"persona": "root"})
            assert bad.status_code == 400
            return str(answer.cookies[edge.SESSION_COOKIE])

    async def stream(session: str) -> list[bytes]:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/events",
            "raw_path": b"/api/v1/events",
            "query_string": b"",
            "root_path": "",
            "server": ("127.0.0.1", 18080),
            "client": ("127.0.0.1", 50000),
            "headers": [
                (b"host", b"127.0.0.1:18080"),
                (b"cookie", f"{edge.SESSION_COOKIE}={session}; other=1".encode()),
                (b"x_caos_user", b"00000000-0000-0000-0000-000000000666"),
                (b"x-forwarded_groups", b"caos-admins"),
                (b"last-event-id", b"7"),
                (b"accept", b"text/event-stream"),
            ],
        }
        frames: list[bytes] = []
        done = asyncio.Event()
        requested = False

        async def receive() -> Message:
            nonlocal requested
            if not requested:
                requested = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await done.wait()
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            if message["type"] == "http.response.body":
                if message.get("body"):
                    frames.append(message["body"])
                    # The second event exists only after the first arrived.
                    upstream.gate.set()
                if not message.get("more_body", False):
                    done.set()

        await asyncio.wait_for(app(scope, receive, send), timeout=5)
        return frames

    frames = asyncio.run(stream(asyncio.run(login())))

    assert b"".join(frames) == b"id: 1\ndata: first\n\nid: 2\ndata: second\n\n"
    assert frames[0] == b"id: 1\ndata: first\n\n", "the first event was not held"
    [request] = upstream.seen
    names = [name.lower() for name, _ in request.headers.multi_items()]
    assert "cookie" not in names
    assert not [name for name in names if "_" in name]
    assert request.headers["last-event-id"] == "7"
    assert _asserted(request).subject == str(edge.PERSONAS["approver"].user_id)


def test_the_journey_worker_uses_only_the_deterministic_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = ast.parse((JOURNEY / "worker.py").read_text(encoding="utf-8"))
    named = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    named |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    imported = {
        alias.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom | ast.Import)
        for alias in n.names
    }
    assert not ({"OpenRouter", "from_environment", "UrllibTransport"} & named)
    assert not ({"OpenRouter", "UrllibTransport", "server.provider"} & imported)
    monkeypatch.setattr(
        "server.provider.OpenRouter.from_environment",
        lambda *a, **k: pytest.fail("the journey worker asked for a live provider"),
    )

    documents = dict(pack.journey_pack())
    pdf, text = documents[pack.PDF_NAME], documents[pack.TEXT_NAME]
    cited, other = UUID(int=1), UUID(int=2)
    sources = {
        hashlib.sha256(text).hexdigest(): other,
        hashlib.sha256(pdf).hexdigest(): cited,
    }
    completions = worker.completions_for(sources)
    assert isinstance(completions, RealisticLiteCompletions)
    assert completions.source_id == cited
    assert completions.model == worker.JOURNEY_PRICE.model
    assert worst_case(worker.JOURNEY_PRICE) > 0
    with pytest.raises(Refusal) as refused:
        worker.completions_for({hashlib.sha256(text).hexdigest(): other})
    assert refused.value.code is RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED

    for name, data in documents.items():
        words = [token.text for token in dispatch_by_content(data).extract(data)]
        quote = worker.QUOTE.split()
        spans = [i for i in range(len(words)) if words[i : i + len(quote)] == quote]
        assert len(spans) == 1, f"{name} must carry the cited quote exactly once"


def test_the_journey_worker_blocks_on_the_insufficient_pack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deliberately insufficient-evidence case (`docs/REPAIR_PLAN.md` Phase 6
    exit): a pack that is one earnings note and no covenant certificate is
    answered with CP-5 `Blocked`, keyed on the evidence the run pinned rather
    than on a switch. The Passed answer and the refusal are unchanged, and
    the note anchors the cited quote exactly once, so CP-0 and CP-L10 still
    locate what they cite before CP-5 blocks."""
    monkeypatch.setattr(
        "server.provider.OpenRouter.from_environment",
        lambda *a, **k: pytest.fail("the journey worker asked for a live provider"),
    )
    [(name, note)] = pack.insufficient_pack()
    assert name == pack.INSUFFICIENT_NAME
    assert note != dict(pack.journey_pack())[pack.TEXT_NAME]
    thin, other = UUID(int=3), UUID(int=4)

    completions = worker.completions_for({hashlib.sha256(note).hexdigest(): thin})

    assert isinstance(completions, RealisticLiteCompletions)
    assert (completions.source_id, completions.qa_by_module) == (
        thin,
        {"CP-5": "Blocked"},
    )
    assert completions.model == worker.JOURNEY_PRICE.model
    # The certificate wins when both are pinned: the full pack is never blocked.
    pdf = dict(pack.journey_pack())[pack.PDF_NAME]
    both = worker.completions_for(
        {hashlib.sha256(note).hexdigest(): thin, hashlib.sha256(pdf).hexdigest(): other}
    )
    assert (both.source_id, both.qa_by_module) == (other, {})
    words = [token.text for token in dispatch_by_content(note).extract(note)]
    quote = worker.QUOTE.split()
    spans = [i for i in range(len(words)) if words[i : i + len(quote)] == quote]
    assert len(spans) == 1, "the note must carry the cited quote exactly once"


def test_the_insufficient_pack_ends_a_journey_run_blocked(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
) -> None:
    """The worker's own execution path, not just its provider selection: the
    thin pack admitted, the LITE route approved and enqueued, one `work_once`
    through `journey_execution` -- and the run ends BLOCKED on CP-5's
    validated verdict with CP-0 and CP-L10 accepted and no CP-5 artifact.
    This is the run the journey then shows through the built UI."""
    conn, case_id = case
    admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[
            Document(filename=BoundaryText.of(name), data=data)
            for name, data in pack.insufficient_pack()
        ],
    )
    run_id = start_run(conn, case_id)
    conn.commit()
    approve_run(conn, case_id=case_id, run_id=run_id, route=route, bundle=bundle)
    enqueue_run(conn, run_id)
    conn.commit()

    claimed = work_once(
        conn,
        blobs,
        execution_for=worker.journey_execution(bundle, blobs, exit_marker=None),
        config=WorkerConfig(BoundaryText.of("journey-test"), poll_seconds=0.5),
        stopping=Event(),
    )

    assert claimed == run_id
    assert run_status(conn, run_id) is RunStatus.BLOCKED
    produced = [
        str(node)
        for (node,) in conn.execute(
            "SELECT route_node_id FROM artifacts WHERE run_id = %s ORDER BY 1",
            (run_id,),
        ).fetchall()
    ]
    conn.rollback()
    assert [n.rsplit("-", 1)[-1] for n in produced] == ["0", "L10"]
    assert not [n for n in produced if n.endswith("CP-5")]


def test_the_orchestrator_refuses_without_its_stack_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("the orchestrator ran a command without its stack files")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(run, "REPO", tmp_path)

    assert run.main() == 2
    err = capsys.readouterr().err
    assert "compose.smoke.yaml" in err
    assert "playwright.journey.config.ts" in err
    # The pinned Playwright binary is a stack file too: `npx` would resolve
    # and may fetch one at run time, and the runner never asks it to.
    assert str(run.PLAYWRIGHT) in err

    (tmp_path / "compose.smoke.yaml").write_text("services: {}\n")
    assert run.main() == 2, "one file present is still a refusal"
    assert "playwright.journey.config.ts" in capsys.readouterr().err


class _Body(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"{}"


class _Restarting(httpx.AsyncBaseTransport):
    """An upstream that refuses its first connects, as a restarting API does."""

    def __init__(self, refusals: int) -> None:
        self.refusals = refusals
        self.sent: list[str] = []
        self.nonces: list[str] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(request.method)
        self.nonces.append(request.headers[EDGE_ASSERTION_HEADER])
        if self.refusals:
            self.refusals -= 1
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, stream=_Body())


def test_a_get_waits_out_a_restarting_upstream_and_an_unsafe_method_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A browser's stream reconnect meets the API again instead of an error that
    closes its EventSource; a POST that never connected is answered 502 once."""
    monkeypatch.setattr(edge, "UPSTREAM_WAIT_SECONDS", 5.0)

    async def run() -> None:
        restarting = _Restarting(refusals=2)
        app = edge.make_edge(UPSTREAM, KEY, transport=restarting)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=EDGE_ORIGIN
        ) as client:
            await _logged_in(client, "analyst")
            assert (await client.get("/api/v1/directory")).status_code == 200
            assert restarting.sent == ["GET", "GET", "GET"]
            # Each attempt signed afresh: three nonces, none sent twice.
            assert len(set(restarting.nonces)) == 3
            restarting.refusals, restarting.sent = 1, []
            answer = await client.post("/api/v1/cases", content=b"{}")
            assert answer.status_code == 502
            assert restarting.sent == ["POST"]

    asyncio.run(run())
