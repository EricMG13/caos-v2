"""The real-stack journey, end to end (Task 4.5 decision 11).

Brings the disposable smoke stack up with the journey worker, starts the test
edge on 127.0.0.1:18080, runs the Playwright journey through it, and always
takes the stack down with its volumes. The stack and journey files arrive in
slices 4.5c and 4.5e2; until both exist this refuses with exit 2 and runs
nothing.
"""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMPOSE_FILE = "compose.smoke.yaml"
PLAYWRIGHT_CONFIG = "playwright.journey.config.ts"
PROJECT = "caos-workbench-smoke"
API_HOST, API_PORT = "127.0.0.1", 18000  # `compose.smoke.yaml` publishes it
API_ORIGIN = f"http://{API_HOST}:{API_PORT}"
EDGE_HOST, EDGE_PORT = "127.0.0.1", 18080
# Every fixed host port a run binds: the edge this runner starts and the API
# port the compose file publishes (the smoke database publishes none). An edge
# orphaned by a stopped run kept 18080 with its old token, the new edge could
# not bind, and every engine failed `EDGE_NOT_TRUSTED` against the orphan.
HOST_PORTS = (
    (EDGE_HOST, EDGE_PORT, "the test edge"),
    (API_HOST, API_PORT, f"the API port {COMPOSE_FILE} publishes"),
)
REFUSED = 2
BROWSER_PROJECTS = ("chromium", "firefox", "webkit")
# What `compose.smoke.yaml` bind-mounts into `journey-worker`, relative to the
# repository root. Docker Desktop on macOS shares only the host paths its File
# Sharing list names -- on the development machine `/Users` and not
# `/private/tmp` -- and a bind mount from anywhere else comes up *empty*, so
# the worker exits `ModuleNotFoundError: No module named 'journey'`, naming
# neither the mount nor the path. Declared here, overridable per machine by
# `JOURNEY_DOCKER_SHARED` (os.pathsep-separated), and checked only on macOS: a
# Linux daemon, CI's included, sees the whole host filesystem.
MOUNTED = "./tests"
DOCKER_SHARED = (Path("/Users"),)
SHARED_ENV = "JOURNEY_DOCKER_SHARED"


def _compose(*args: str) -> list[str]:
    return ["docker", "compose", "-p", PROJECT, "-f", str(REPO / COMPOSE_FILE), *args]


def _environment() -> dict[str, str]:
    """A per-run edge token and the journey's switches; no provider credential."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("OPENROUTER_") and key != "CAOS_REQUIRE_PROVIDER"
    }
    env.update(
        CAOS_EDGE_TOKEN=secrets.token_urlsafe(48),
        CAOS_PUBLIC_ORIGIN=f"http://{EDGE_HOST}:{EDGE_PORT}",
        JOURNEY_UPSTREAM=API_ORIGIN,
        JOURNEY_EXIT_AFTER_FIRST_ACCEPT="1",
    )
    return env


def compose_up(env: dict[str, str]) -> None:
    subprocess.run(
        _compose("--profile", "journey", "up", "--detach", "--wait"),
        env=env,
        check=True,
    )


def compose_down(env: dict[str, str]) -> None:
    subprocess.run(
        _compose("--profile", "journey", "down", "--volumes"),
        env=env,
        check=True,
    )


def stop_edge(edge: subprocess.Popen[bytes]) -> None:
    edge.terminate()
    try:
        edge.wait(timeout=10)
    except subprocess.TimeoutExpired:
        edge.kill()
        edge.wait(timeout=10)


def start_edge(env: dict[str, str]) -> subprocess.Popen[bytes]:
    """The test edge on the host, from the locked uvicorn, with tests on the path."""
    env = {**env, "PYTHONPATH": os.pathsep.join([str(REPO / "tests"), str(REPO)])}
    edge = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--factory",
            "journey.edge:from_environment",
            "--host",
            EDGE_HOST,
            "--port",
            str(EDGE_PORT),
            "--no-server-header",
        ],
        env=env,
    )
    ready_url = f"http://{EDGE_HOST}:{EDGE_PORT}/"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(ready_url, timeout=1):
                return edge
        except urllib.error.HTTPError:
            return edge  # the edge answered (401 without a session)
        except OSError:
            time.sleep(0.25)
    stop_edge(edge)
    raise TimeoutError


def run_playwright(env: dict[str, str], project: str) -> int:
    cmd = ["npx", "playwright", "test", "-c", PLAYWRIGHT_CONFIG, "--project", project]
    return subprocess.run(
        cmd,
        cwd=REPO / "frontend",
        env=env,
        check=False,
    ).returncode


def shared_prefixes() -> tuple[Path, ...]:
    """The host paths Docker shares: the declared default, or this machine's."""
    declared = os.environ.get(SHARED_ENV)
    if not declared:
        return DOCKER_SHARED
    return tuple(Path(part) for part in declared.split(os.pathsep) if part)


def mount_refusal(root: Path, *, platform: str, shared: tuple[Path, ...]) -> str | None:
    """Why Docker could not mount `root`'s tests, or None when it can."""
    if platform != "darwin":
        return None
    source = (root / MOUNTED).resolve()
    if any(source.is_relative_to(prefix.resolve()) for prefix in shared):
        return None
    names = ", ".join(str(prefix) for prefix in shared)
    return (
        f"journey refused: {COMPOSE_FILE} bind-mounts {MOUNTED} from {source}, "
        f"which is not under a path Docker Desktop shares ({names}); the "
        "journey worker would start with an empty /app/tests. Run from a "
        f"checkout under one of them, or name this machine's shared paths in "
        f"{SHARED_ENV}."
    )


def _taken(host: str, port: int) -> str | None:
    """Why `host:port` cannot be bound, or None when it can.

    Connected to first, which names a listener -- a wildcard one included,
    which does not always stop a specific bind on BSD sockets; then bound with
    `SO_REUSEADDR` as uvicorn binds, so a previous run's TIME_WAIT is not
    mistaken for a holder."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        if probe.connect_ex((host, port)) == 0:
            return "something is already listening on it"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError as exc:
            return f"it cannot be bound ({exc.strerror or exc.errno})"
    return None


def port_refusal(ports: tuple[tuple[str, int, str], ...]) -> str | None:
    """Why a fixed host port the run needs is already taken, or None."""
    for host, port, role in ports:
        reason = _taken(host, port)
        if reason is not None:
            return (
                f"journey refused: {host}:{port}, {role}, is taken: {reason}. "
                "An orphaned test edge from a stopped run holds its old token "
                "and answers every engine EDGE_NOT_TRUSTED; stop whatever "
                "holds the port and run again."
            )
    return None


def browser_projects() -> tuple[str, ...]:
    """Each browser gets its own crash-once worker and disposable stack."""
    selected = os.environ.get("JOURNEY_PLAYWRIGHT_PROJECT")
    return (selected,) if selected else BROWSER_PROJECTS


def run_project(project: str) -> int:
    env = _environment()
    edge: subprocess.Popen[bytes] | None = None
    try:
        compose_up(env)
        edge = start_edge(env)
        return run_playwright(env, project)
    finally:
        try:
            if edge is not None:
                stop_edge(edge)
        finally:
            compose_down(env)


def main() -> int:
    missing = [
        path
        for path in (REPO / COMPOSE_FILE, REPO / "frontend" / PLAYWRIGHT_CONFIG)
        if not path.is_file()
    ]
    if missing:
        names = ", ".join(str(path.relative_to(REPO)) for path in missing)
        print(f"journey refused: missing stack files: {names}", file=sys.stderr)
        return REFUSED
    refusal = mount_refusal(REPO, platform=sys.platform, shared=shared_prefixes())
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return REFUSED
    refusal = port_refusal(HOST_PORTS)
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return REFUSED
    # Every engine runs, whatever an earlier one did. Returning on the first
    # failure discarded the other two engines' evidence, so one flake in one
    # browser cost the whole three-engine gate and left nobody able to say
    # whether the other two would have passed -- which is what happened once
    # while Task 12.5's gate was being run. This weakens nothing: any engine
    # failing still fails the gate, by the first non-zero status. It only stops
    # throwing away the runs that were already paid for.
    statuses = {project: run_project(project) for project in browser_projects()}
    for project, status in statuses.items():
        print(f"journey {project}: {'ok' if status == 0 else f'exit {status}'}")
    return next((status for status in statuses.values() if status), 0)


if __name__ == "__main__":
    sys.exit(main())
