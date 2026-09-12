"""The UI fixture server is explicit, and local gates say what they prove."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def test_frontend_commands_separate_real_and_demo_artifacts() -> None:
    package = _read("frontend/package.json")

    assert '"dev:demo": "vite --mode demo"' in package
    assert '"build:demo": "vite build --mode demo --outDir dist-demo' in package
    assert '"preview:demo": "vite preview --mode demo --outDir dist-demo' in package
    assert '"test": "vitest run --mode demo"' in package


def test_vite_defaults_to_the_real_loopback_api() -> None:
    config = _read("frontend/vite.config.ts")

    assert 'target: "http://127.0.0.1:8000"' in config
    assert 'mode === "demo"' in config
    assert "configurePreviewServer" in config
    assert '["GET", "HEAD"].includes(req.method' in config
    assert "405," in config
    assert 'code: "READ_ONLY_DEMO"' in config


def test_fixture_browser_launchers_never_reuse_an_unrelated_server() -> None:
    playwright = _read("frontend/playwright.config.ts")
    axe = _read("frontend/scripts/a11y-axe.mjs")

    assert 'command: "npm run preview:demo"' in playwright
    assert "reuseExistingServer: false" in playwright
    assert '"--mode",' in axe and '"demo",' in axe
    assert '"--outDir",' in axe and '"dist-demo",' in axe


def test_complete_local_gate_requires_database_image_frontend_and_base() -> None:
    makefile = _read("Makefile")

    assert "check-fast:" in makefile
    assert "check-postgres:" in makefile
    assert "test-postgres-races:" in makefile
    assert "frontend-check:" in makefile
    assert "check-size:" in makefile
    assert "PR_BASE is required" in _read("scripts/check_pr_size.py")
    assert "$(MAKE) --no-print-directory image" in makefile
    check_recipe = makefile.split("\ncheck:\n", 1)[1].split("\ndoctor:", 1)[0]
    assert "check-size" not in check_recipe


def test_postgres_preflight_does_not_echo_the_connection_string() -> None:
    sentinel = "postgresql://secret:do-not-print@127.0.0.1:1/caos"
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_postgres.py")],
        env={"CAOS_TEST_POSTGRES_URL": sentinel},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "test PostgreSQL is not reachable" in result.stdout
    assert sentinel not in result.stdout + result.stderr


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _size_repo(tmp_path: Path, changed_lines: int) -> tuple[Path, str]:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Gate test")
    (tmp_path / "kept.txt").write_text("", encoding="utf-8")
    _git(tmp_path, "add", "kept.txt")
    _git(tmp_path, "commit", "-qm", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (tmp_path / "kept.txt").write_text("x\n" * changed_lines, encoding="utf-8")
    _git(tmp_path, "add", "kept.txt")
    _git(tmp_path, "commit", "-qm", "change")
    return tmp_path, base


def test_changed_lines_accepts_the_exact_threshold(tmp_path: Path) -> None:
    repo, base = _size_repo(tmp_path, 800)

    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_pr_size.py"), base],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "changed lines: 800" in result.stdout


def test_size_gate_rejects_over_limit_and_invalid_base(tmp_path: Path) -> None:
    repo, base = _size_repo(tmp_path, 801)

    over = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_pr_size.py"), base],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    invalid = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_pr_size.py"), "not-a-base"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    missing = subprocess.run(
        [sys.executable, str(REPO / "scripts/check_pr_size.py")],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert over.returncode != 0
    assert "PR too large" in over.stderr
    assert invalid.returncode != 0
    assert "not-a-base" in invalid.stderr
    assert missing.returncode != 0
    assert "PR_BASE is required" in missing.stderr
