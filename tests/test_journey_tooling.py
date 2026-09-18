"""The journey's own tooling, where it fails in ways that name nothing.

Driven without Docker: each check here is one the tooling makes before a stack
exists, or inside a loop a fake upstream can drive.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from journey import edge, run
from starlette.types import Message, Scope


def test_a_macos_root_docker_cannot_mount_is_refused_naming_the_mount() -> None:
    """`compose.smoke.yaml` bind-mounts `./tests`, and Docker Desktop shares
    `/Users` and not `/private/tmp`: the mount comes up empty and the worker
    dies `ModuleNotFoundError: No module named 'journey'`, naming neither."""
    shared = (Path("/Users"),)
    refusal = run.mount_refusal(
        Path("/private/tmp/caos-wt/r-e"), platform="darwin", shared=shared
    )

    assert refusal is not None
    assert "/private/tmp/caos-wt/r-e/tests" in refusal
    assert run.MOUNTED in refusal and "/Users" in refusal
    assert run.SHARED_ENV in refusal


@pytest.mark.parametrize(
    ("root", "platform"),
    [
        (Path("/Users/someone/caos"), "darwin"),
        (Path("/home/runner/work/caos/caos"), "linux"),
        (Path("/private/tmp/caos"), "linux"),
    ],
)
def test_a_mountable_root_or_a_linux_host_is_not_refused(
    root: Path, platform: str
) -> None:
    """Only Docker Desktop on macOS shares a declared subset of the host, so
    CI -- Linux, where the daemon sees the whole filesystem -- is never refused."""
    assert run.mount_refusal(root, platform=platform, shared=(Path("/Users"),)) is None


def test_the_shared_prefixes_are_declared_and_overridable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(run.SHARED_ENV, raising=False)
    assert run.shared_prefixes() == run.DOCKER_SHARED == (Path("/Users"),)

    monkeypatch.setenv(run.SHARED_ENV, "/Users:/private/tmp")
    assert run.shared_prefixes() == (Path("/Users"), Path("/private/tmp"))
    shared = run.shared_prefixes()
    assert (
        run.mount_refusal(Path("/private/tmp/c"), platform="darwin", shared=shared)
        is None
    )


def test_the_orchestrator_refuses_an_unmountable_root_before_building_anything(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "repo"
    (root / "frontend").mkdir(parents=True)
    (root / run.COMPOSE_FILE).write_text("", encoding="utf-8")
    (root / "frontend" / run.PLAYWRIGHT_CONFIG).write_text("", encoding="utf-8")
    monkeypatch.setattr(run, "REPO", root)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv(run.SHARED_ENV, "/nowhere-shared")
    built: list[str] = []
    monkeypatch.setattr(run, "run_project", built.append)

    assert run.main() == run.REFUSED
    assert built == []
    assert "journey refused" in capsys.readouterr().err


# The fixed host ports. An edge orphaned by a stopped run kept 18080 with its
# old token, the new run's edge could not bind, and every engine then failed
# `EDGE_NOT_TRUSTED` against the old one -- a refusal that named neither the
# port nor the orphan.


def test_a_host_port_something_is_listening_on_is_refused_naming_it() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind(("127.0.0.1", 0))
        held.listen()
        port = held.getsockname()[1]

        refusal = run.port_refusal((("127.0.0.1", port, "the test edge"),))

    assert refusal is not None
    assert f"127.0.0.1:{port}" in refusal
    assert "the test edge" in refusal
    assert "listening" in refusal


def test_a_free_host_port_is_not_refused() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    assert run.port_refusal((("127.0.0.1", port, "the test edge"),)) is None


def test_the_runner_checks_every_port_the_stack_publishes_on_the_host() -> None:
    """The edge the runner starts and the API port `compose.smoke.yaml`
    publishes; the smoke database publishes none. Read from the compose file,
    so a port moved there without the runner fails here, not at `up`."""
    compose = (run.REPO / run.COMPOSE_FILE).read_text(encoding="utf-8")
    published = set(re.findall(r'"(127\.0\.0\.1):(\d+):\d+"', compose))

    checked = {(host, port) for host, port, _ in run.HOST_PORTS}
    assert (run.EDGE_HOST, run.EDGE_PORT) in checked
    assert {(host, int(port)) for host, port in published} <= checked
    assert run.API_ORIGIN == f"http://{run.API_HOST}:{run.API_PORT}"


def test_the_orchestrator_refuses_a_taken_port_before_building_anything(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "repo"
    (root / "frontend").mkdir(parents=True)
    (root / run.COMPOSE_FILE).write_text("", encoding="utf-8")
    (root / "frontend" / run.PLAYWRIGHT_CONFIG).write_text("", encoding="utf-8")
    monkeypatch.setattr(run, "REPO", root)
    monkeypatch.setattr(sys, "platform", "linux")
    built: list[str] = []
    monkeypatch.setattr(run, "run_project", built.append)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind(("127.0.0.1", 0))
        held.listen()
        port = held.getsockname()[1]
        monkeypatch.setattr(run, "HOST_PORTS", (("127.0.0.1", port, "the test edge"),))

        assert run.main() == run.REFUSED

    assert built == []
    assert f"127.0.0.1:{port}" in capsys.readouterr().err


# The test edge's disconnect. An SSE tail proxied to the API is certain to be
# cut -- the browser navigates away, the tail's deadline ends it, the stack is
# taken down -- and the edge used to let that surface as an unhandled
# `Exception in ASGI application` on every green smoke run.

_TAIL = "/api/v1/cases/0/events"
_FIRST = b"id: 1\ndata: first\n\n"


class _Cut(httpx.AsyncBaseTransport):
    """An upstream whose body yields one frame and then fails with `error`."""

    def __init__(self, content_type: str, error: Exception) -> None:
        self.content_type = content_type
        self.error = error

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": self.content_type}, content=self._body()
        )

    async def _body(self) -> AsyncIterator[bytes]:
        yield _FIRST
        raise self.error


def _scope(session: str, spec_version: str) -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": spec_version},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": _TAIL,
        "raw_path": _TAIL.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("127.0.0.1", 18080),
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", b"127.0.0.1:18080"),
            (b"cookie", f"{edge.SESSION_COOKIE}={session}".encode()),
        ],
    }


def _drive(
    transport: httpx.AsyncBaseTransport,
    *,
    spec_version: str = "2.3",
    client_gone: bool = False,
) -> list[Message]:
    """One logged-in GET of the tail through the edge; the messages it sent.
    `client_gone` makes every body send fail as a vanished browser's does."""
    app = edge.make_edge("http://upstream.invalid", "t" * 40, transport=transport)
    sent: list[Message] = []

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:18080"
        ) as client:
            login = await client.get(edge.LOGIN_PATH, params={"persona": "analyst"})
            session = str(login.cookies[edge.SESSION_COOKIE])
        requested = False

        async def receive() -> Message:
            nonlocal requested
            if not requested:
                requested = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await asyncio.Event().wait()  # the browser never says goodbye first
            raise AssertionError

        async def send(message: Message) -> None:
            if client_gone and message["type"] == "http.response.body":
                raise OSError  # the browser went away
            sent.append(message)

        await asyncio.wait_for(app(_scope(session, spec_version), receive, send), 5)

    asyncio.run(scenario())
    return sent


def _bodies(sent: list[Message]) -> list[tuple[bytes, bool]]:
    return [
        (message.get("body", b""), message.get("more_body", False))
        for message in sent
        if message["type"] == "http.response.body"
    ]


def _edge_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == edge.LOGGER.name]


def test_an_event_stream_the_upstream_cuts_ends_with_one_line_not_a_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    peer = httpx.RemoteProtocolError(
        "peer closed connection without sending complete message body"
    )
    with caplog.at_level(logging.INFO):
        sent = _drive(_Cut("text/event-stream; charset=utf-8", peer))

    assert _bodies(sent) == [(_FIRST, True), (b"", False)]
    [line] = _edge_lines(caplog)
    assert "RemoteProtocolError" in line and _TAIL in line
    assert "peer closed" not in line, "the exception's own text is not logged"


def test_a_browser_that_leaves_a_tail_ends_it_with_one_line_not_a_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ASGI 2.4 servers raise into `send` when the client has gone, which
    Starlette turns into `ClientDisconnect` out of the response."""
    peer = httpx.RemoteProtocolError("unreached")
    with caplog.at_level(logging.INFO):
        sent = _drive(
            _Cut("text/event-stream", peer), spec_version="2.4", client_gone=True
        )

    assert _bodies(sent) == []
    [line] = _edge_lines(caplog)
    assert "ClientDisconnect" in line and _TAIL in line


@pytest.mark.parametrize(
    ("content_type", "error"),
    [
        # A truncated JSON body presented as complete would be a lie the
        # journey could read as an answer: only an event stream may end early.
        ("application/json", httpx.RemoteProtocolError("cut")),
        # Any other failure of the upstream is not the disconnect, and stays loud.
        ("text/event-stream", httpx.ReadError("reset")),
        ("text/event-stream", RuntimeError("a bug in the edge")),
    ],
)
def test_nothing_but_an_event_streams_disconnect_is_swallowed(
    content_type: str, error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(type(error)), caplog.at_level(logging.INFO):
        _drive(_Cut(content_type, error))
    assert _edge_lines(caplog) == []
