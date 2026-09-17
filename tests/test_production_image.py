"""The production image: what it serves, what it refuses, and what it never
contains.

Marked `production_image` (Task 4.5 decision 11); deselected by `make test`
and `make test-fast`, run by `make smoke-production` after that target's own
`docker build` has already produced `$IMAGE`. Nothing here builds the image:
a missing one skips with its reason, and `CAOS_REQUIRE_IMAGE=1` -- set by
`make smoke-production` -- turns that skip into a failure, the same rule
`CAOS_REQUIRE_POSTGRES` gives the store suite (`tests/conftest.py`).

Every container this suite starts is removed (`docker run --rm` or a
`docker compose down --volumes` in a `finally`), and each compose stack runs
under its own project name so a run never collides with a real
`make smoke-production` invocation using the same fixed ports.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.production_image

REPO = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("IMAGE", "caos-workbench:local")
REQUIRE_IMAGE = os.environ.get("CAOS_REQUIRE_IMAGE") == "1"
COMPOSE_FILE = REPO / "compose.smoke.yaml"
SECTIONS = (
    "directory",
    "upload",
    "analysis",
    "book",
    "run",
    "model",
    "report",
    "committee",
    "admin",
)


def _skip_or_fail(reason: str) -> None:
    if REQUIRE_IMAGE:
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def built_image() -> str:
    """`IMAGE`, once its presence is confirmed; skip (or fail) otherwise."""
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        _skip_or_fail(
            f"{IMAGE} is not built; run `make smoke-production` or `docker build`"
        )
    return IMAGE


def _docker_run(image: str, options: list[str], command: list[str]) -> str:
    """`docker run --rm OPTIONS image COMMAND`; stdout."""
    result = subprocess.run(
        ["docker", "run", "--rm", *options, image, *command],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def _wait_for_answer(
    url: str, deadline: float, headers: dict[str, str] | None = None
) -> tuple[int, bytes]:
    """Poll `url` until it answers with a status code, or raise past `deadline`."""
    end = time.monotonic() + deadline
    last: Exception | None = None
    while time.monotonic() < end:
        request = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()
        except (urllib.error.URLError, ConnectionError) as error:
            last = error
            time.sleep(0.5)
    raise TimeoutError(str(last))


class _Container:
    """One detached `docker run` container, removed on exit."""

    def __init__(self, image: str, *args: str) -> None:
        self.name = f"caos-production-image-test-{uuid4().hex[:12]}"
        subprocess.run(
            ["docker", "run", "-d", "--rm", "--name", self.name, *args, image],
            check=True,
            capture_output=True,
        )

    def stop(self) -> None:
        subprocess.run(["docker", "stop", self.name], capture_output=True, check=False)


class _Database:
    """A disposable Postgres container on its own network, reachable as `db`.

    Boot (`server/api/app.py`'s lifespan) refuses to start without a reachable
    database, so a test proving anything about a *booted* app -- even one
    proving what an absent edge token does -- needs a real one.
    """

    URL = "postgresql://caos_smoke:local-smoke-only@db:5432/caos_smoke"

    def __init__(self) -> None:
        self.network = f"caos-production-image-test-net-{uuid4().hex[:12]}"
        self.name = f"caos-production-image-test-db-{uuid4().hex[:12]}"
        subprocess.run(
            ["docker", "network", "create", self.network],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                self.name,
                "--network",
                self.network,
                "--network-alias",
                "db",
                "-e",
                "POSTGRES_DB=caos_smoke",
                "-e",
                "POSTGRES_USER=caos_smoke",
                "-e",
                "POSTGRES_PASSWORD=local-smoke-only",
                "postgres@sha256:"
                "18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73",
            ],
            check=True,
            capture_output=True,
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            probe = subprocess.run(
                ["docker", "exec", self.name, "pg_isready", "-U", "caos_smoke"],
                capture_output=True,
                check=False,
            )
            if probe.returncode == 0:
                return
            time.sleep(0.5)
        self.stop()
        raise TimeoutError(self.name)

    def stop(self) -> None:
        subprocess.run(["docker", "stop", self.name], capture_output=True, check=False)
        subprocess.run(
            ["docker", "network", "rm", self.network], capture_output=True, check=False
        )


class _ComposeStack:
    """A `compose.smoke.yaml` stack under its own disposable project name."""

    def __init__(self, image: str, edge_token: str, api_port: int = 18000) -> None:
        self.project = f"caos-workbench-test-{uuid4().hex[:12]}"
        self.api_origin = f"http://127.0.0.1:{api_port}"
        self.token = edge_token
        self.env = {
            **os.environ,
            "IMAGE": image,
            "CAOS_EDGE_TOKEN": edge_token,
            "CAOS_PUBLIC_ORIGIN": self.api_origin,
        }

    def _compose(self, *args: str) -> list[str]:
        return [
            "docker",
            "compose",
            "-p",
            self.project,
            "-f",
            str(COMPOSE_FILE),
            *args,
        ]

    def up(self) -> None:
        subprocess.run(
            self._compose("up", "--detach", "--wait", "smoke-postgres", "api"),
            env=self.env,
            check=True,
            capture_output=True,
        )

    def stop_database(self) -> None:
        # `pause`, not `stop`: `smoke-postgres`'s data directory is `tmpfs`
        # (decision 11), which does not survive a real stop -- the container
        # would come back with no schema applied and never answer OK again.
        # Pausing freezes the process without tearing down its mounts, so a
        # connection attempt against it times out (`STORE_UNAVAILABLE`)
        # instead of the data disappearing.
        subprocess.run(
            self._compose("pause", "smoke-postgres"),
            env=self.env,
            check=True,
            capture_output=True,
        )

    def start_database(self) -> None:
        subprocess.run(
            self._compose("unpause", "smoke-postgres"),
            env=self.env,
            check=True,
            capture_output=True,
        )

    def down(self) -> None:
        subprocess.run(
            self._compose("down", "--volumes"),
            env=self.env,
            check=False,
            capture_output=True,
        )


@pytest.fixture
def smoke_stack(built_image: str) -> Iterator[_ComposeStack]:
    stack = _ComposeStack(built_image, secrets.token_urlsafe(48))
    try:
        stack.up()
        yield stack
    finally:
        stack.down()


def test_the_image_serves_every_section_deep_link_and_the_real_api(
    smoke_stack: _ComposeStack,
) -> None:
    headers = {"x-caos-edge-token": smoke_stack.token}
    for section in SECTIONS:
        status, body = _wait_for_answer(
            f"{smoke_stack.api_origin}/{section}/", 30, headers
        )
        assert status == 200, section
        assert b"<html" in body.lower()

    status, body = _wait_for_answer(f"{smoke_stack.api_origin}/api/health", 30)
    assert status in (200, 503)
    document = json.loads(body)
    assert document["status"] in ("ready", "not_ready")


def test_the_image_contains_no_fixture_demo_marker_or_test_module(
    built_image: str,
) -> None:
    # `/app/vendor` is the pinned methodology bundle (invariant 4): it ships
    # its own `tests/` as part of what its manifest covers, never edited here,
    # so it is not host test scaffolding and is out of this scan's scope.
    found = _docker_run(
        built_image,
        ["--entrypoint", "find"],
        [
            "/app/server",
            "/app/site",
            "-iname",
            "*fixture*",
            "-o",
            "-iname",
            "*demo*",
            "-o",
            "-iname",
            "conftest.py",
            "-o",
            "-iname",
            "test_*.py",
        ],
    ).strip()
    assert found == "", found

    probe = "import sys; print('\\n'.join(p for p in sys.path if 'test' in p.lower()))"
    imports = _docker_run(
        built_image, ["--entrypoint", "python"], ["-c", probe]
    ).strip()
    assert imports == "", imports


def test_the_image_refuses_to_boot_with_the_trust_switch_and_a_token(
    built_image: str,
) -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "CAOS_TRUST_ROLE_HEADER=1",
            "-e",
            f"CAOS_EDGE_TOKEN={secrets.token_urlsafe(48)}",
            "-e",
            "CAOS_PUBLIC_ORIGIN=http://127.0.0.1",
            built_image,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0
    assert "EDGE_CONFIG_INVALID" in result.stdout + result.stderr


def test_the_image_without_a_token_answers_only_health(built_image: str) -> None:
    database = _Database()
    try:
        container = _Container(
            built_image,
            "-p",
            "127.0.0.1::8000",
            "--network",
            database.network,
            "-e",
            f"CAOS_DATABASE_URL={_Database.URL}",
            "-e",
            "CAOS_BLOB_ROOT=/tmp",
        )
        try:
            port = _published_port(container.name)
            origin = f"http://127.0.0.1:{port}"
            status, _ = _wait_for_answer(f"{origin}/api/health", 30)
            assert status in (200, 503)

            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-o",
                    "/dev/null",
                    "-w",
                    "%{http_code}",
                    f"{origin}/directory/",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.stdout.strip() == "403"
        finally:
            container.stop()
    finally:
        database.stop()


def test_a_direct_forged_identity_request_without_the_token_is_refused(
    smoke_stack: _ComposeStack,
) -> None:
    result = subprocess.run(
        [
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "-H",
            "x-caos-user: 00000000-0000-4000-8000-000000000001",
            "-H",
            "x-forwarded-groups: caos-admins",
            "-H",
            "sec-fetch-site: same-origin",
            f"{smoke_stack.api_origin}/api/health",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # Health needs no token; a case-bearing path does.
    other = subprocess.run(
        [
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "-H",
            "x-caos-user: 00000000-0000-4000-8000-000000000001",
            "-H",
            "x-forwarded-groups: caos-admins",
            "-H",
            "sec-fetch-site: same-origin",
            f"{smoke_stack.api_origin}/api/v1/cases",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout.strip() in ("200", "503")
    assert other.stdout.strip() == "403"


def _wait_for_status(url: str, want: int, deadline: float) -> bool:
    """Poll until `want` is seen, or `deadline` runs out. The compose
    healthcheck (any HTTP answer counts) reports the container up well before
    the probe loop's first round -- up to `PROBE_INTERVAL` -- has completed,
    so `200` is itself something this polls for, not something already true
    the moment `up --wait` returns."""
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        status, _ = _wait_for_answer(url, 5)
        if status == want:
            return True
        time.sleep(1)
    return False


def test_readiness_is_503_while_the_database_is_stopped_and_200_after(
    smoke_stack: _ComposeStack,
) -> None:
    url = f"{smoke_stack.api_origin}/api/health"
    assert _wait_for_status(url, 200, 45)

    smoke_stack.stop_database()
    assert _wait_for_status(url, 503, 45)

    smoke_stack.start_database()
    assert _wait_for_status(url, 200, 45)


def test_the_image_worker_exits_without_provider_and_price(built_image: str) -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "CAOS_DATABASE_URL=postgresql://x:x@127.0.0.1:1/x",
            "-e",
            "CAOS_BLOB_ROOT=/tmp",
            built_image,
            "python",
            "-m",
            "server.engine.worker",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert "PROVIDER_NOT_CONFIGURED" in result.stdout + result.stderr


def test_no_server_module_imports_a_test_fixture() -> None:
    """Static, needs no image: `server/` never names a `tests/` module."""
    forbidden = ("canonical_fixtures", "lite_route_fixtures", "journey")
    offenders = []
    for path in (REPO / "server").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in forbidden:
            if f"import {name}" in text or f"from {name}" in text:
                offenders.append((path, name))
    assert offenders == []


def _published_port(container: str) -> str:
    result = subprocess.run(
        ["docker", "port", container, "8000/tcp"],
        capture_output=True,
        text=True,
        check=True,
    )
    # "0.0.0.0:PORT" or "127.0.0.1:PORT"; the port is what curl needs.
    return result.stdout.strip().rsplit(":", 1)[-1]
