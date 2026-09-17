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
API_ORIGIN = "http://127.0.0.1:18000"
EDGE_HOST, EDGE_PORT = "127.0.0.1", 18080
REFUSED = 2
BROWSER_PROJECTS = ("chromium", "firefox", "webkit")


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
    for project in browser_projects():
        if status := run_project(project):
            return status
    return 0


if __name__ == "__main__":
    sys.exit(main())
