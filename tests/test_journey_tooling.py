"""The journey's own tooling, where it fails in ways that name nothing.

Driven without Docker: each check here is one the tooling makes before a stack
exists, or inside a loop a fake upstream can drive.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from journey import run


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
