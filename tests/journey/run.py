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
import tempfile
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


def _compose(*args: str) -> list[str]:
    return ["docker", "compose", "-p", PROJECT, "-f", str(REPO / COMPOSE_FILE), *args]


def _environment(state_dir: str) -> dict[str, str]:
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
        JOURNEY_STATE_DIR=state_dir,
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
        check=False,
    )


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
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://{EDGE_HOST}:{EDGE_PORT}/", timeout=1)
        except urllib.error.HTTPError:
            return edge  # the edge answered (401 without a session)
        except OSError:
            time.sleep(0.25)
    edge.terminate()
    raise TimeoutError


def run_playwright(env: dict[str, str]) -> int:
    return subprocess.run(
        ["npx", "playwright", "test", "-c", PLAYWRIGHT_CONFIG],
        cwd=REPO / "frontend",
        env=env,
        check=False,
    ).returncode


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
    with tempfile.TemporaryDirectory(prefix="caos-journey-") as state_dir:
        env = _environment(state_dir)
        edge: subprocess.Popen[bytes] | None = None
        try:
            compose_up(env)
            edge = start_edge(env)
            return run_playwright(env)
        finally:
            if edge is not None:
                edge.terminate()
                edge.wait(timeout=10)
            compose_down(env)


if __name__ == "__main__":
    sys.exit(main())
