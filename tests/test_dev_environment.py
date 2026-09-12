"""Development setup stays reproducible, isolated, and secret-safe."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
TOOLS = [
    ("node", "24.1.0"),
    ("npm", "11.0.0"),
    ("uv", "0.12.0"),
    ("docker", "29.0.0"),
    ("docker compose", "5.2.0"),
    ("gitnexus", "1.6.9"),
    ("security Python", "3.12.12"),
    ("pre-commit", "4.6.2"),
]


def _load_doctor() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "dev_doctor", REPO / "scripts" / "dev_doctor.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_reports_presence_without_secret_values(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    doctor = _load_doctor()
    sentinel = "synthetic-do-not-print-93fc"
    for name in doctor.REQUIRED_CONFIGURATION | doctor.OPTIONAL_CONFIGURATION:
        monkeypatch.setenv(name, sentinel)
    monkeypatch.setattr(doctor, "_tool_versions", lambda: TOOLS)

    assert doctor.main() == 0
    captured = capsys.readouterr()
    assert sentinel not in captured.out + captured.err
    assert "CAOS_DATABASE_URL: present" in captured.out
    assert "OPENROUTER_API_KEY: present (optional live mode)" in captured.out


def test_doctor_rejects_the_wrong_runtime(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    doctor = _load_doctor()
    monkeypatch.setattr(doctor, "PYTHON_VERSION", (3, 13))
    monkeypatch.setattr(doctor, "_tool_versions", lambda: TOOLS)
    for name in doctor.REQUIRED_CONFIGURATION:
        monkeypatch.setenv(name, "configured")

    assert doctor.main() == 1
    assert "Python 3.14 required; found 3.13" in capsys.readouterr().err


def test_empty_tool_output_is_reported_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doctor = _load_doctor()
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=""),
    )

    assert doctor._version(["node", "--version"]) == "missing"


def test_malformed_runtime_versions_fail_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    doctor = _load_doctor()
    malformed = [
        (name, "not-a-version" if name in {"node", "security Python"} else value)
        for name, value in TOOLS
    ]
    monkeypatch.setattr(doctor, "_tool_versions", lambda: malformed)
    for name in doctor.REQUIRED_CONFIGURATION:
        monkeypatch.setenv(name, "configured")

    assert doctor.main() == 1
    captured = capsys.readouterr()
    assert "Node 24 required; found not-a-version" in captured.err
    assert "security Python 3.12 required; found not-a-version" in captured.err
    assert "Traceback" not in captured.out + captured.err


def test_index_fails_closed_when_gitnexus_is_not_installed() -> None:
    result = subprocess.run(
        ["make", "--no-print-directory", "index"],
        cwd=REPO,
        env={"PATH": "/usr/bin:/bin"},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "gitnexus is required; install it before indexing" in result.stderr
    assert "npx" not in result.stdout + result.stderr
    assert "pnpm" not in result.stdout + result.stderr


def test_make_doctor_uses_the_bootstrapped_python(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        (REPO / "Makefile").read_text(encoding="utf-8"), encoding="utf-8"
    )
    project_bin = tmp_path / ".venv" / "bin"
    project_bin.mkdir(parents=True)
    (project_bin / "python").symlink_to(sys.executable)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "dev_doctor.py").write_text(
        'print("project interpreter selected")\n', encoding="utf-8"
    )
    ambient_python = tmp_path / "python3"
    ambient_python.write_text("#!/bin/sh\nexit 93\n", encoding="utf-8")
    ambient_python.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}:{environment['PATH']}"

    result = subprocess.run(
        ["make", "--no-print-directory", "doctor"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "project interpreter selected"


def test_compose_keeps_dev_and_test_storage_isolated() -> None:
    compose = (REPO / "compose.yaml").read_text(encoding="utf-8")

    digest = "18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73"
    assert f"postgres@sha256:{digest}" in compose
    assert '"127.0.0.1:55436:5432"' in compose
    assert '"127.0.0.1:55437:5432"' in compose
    assert "caos-workbench-dev-postgres" in compose
    assert "tmpfs:" in compose
    assert "caos_app" in (REPO / "scripts" / "dev-init.sql").read_text(encoding="utf-8")
