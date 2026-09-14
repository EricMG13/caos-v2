"""The Claude Code hooks read the event JSON they are actually given.

Every forbidden command here is a string handed to the guard, never executed.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from claude_hook import (  # noqa: E402
    MALFORMED,
    SKIPPED,
    HookInputError,
    format_file,
    format_target,
    guard_reason,
    main,
    parse_event,
)

SETTINGS = REPO / ".claude/settings.json"


def _event(**tool_input: object) -> str:
    return json.dumps({"hook_event_name": "PreToolUse", "tool_input": tool_input})


def _main(mode: str, raw: str) -> tuple[int, str]:
    stderr = io.StringIO()
    code = main(["claude_hook.py", mode], io.StringIO(raw), stderr)
    return code, stderr.getvalue()


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f",
        "git push origin main --force-with-lease",
        "git commit --no-verify -m x",
        "git commit -n -m x",
        "pip install requests",
        "printenv",
        "echo ${OPENROUTER_API_KEY}",
        "echo $OPENROUTER_MODEL",
        "env",
        "env | grep KEY",
        "cat .env",
        "git commit -nm x",
        "git push -fu origin b",
        "git push origin +main",
        "echo ok\ngit push -f origin x\n: '",
        "git commit -n -F- <<EOF\nit's\nEOF",
        "git -C /repo push --force origin x",
        "git -c core.hooksPath=/dev/null commit -n -m x",
        "git push --force-with-lease=main:abc origin main",
        "/usr/bin/git push -f",
        "git push --mirror",
        "env -u CAOS_REQUIRE_PROVIDER",
        "env -0",
        ".venv/bin/pip install requests",
        "pip3 install requests",
        "export",
        "export -p",
        "set",
        "declare -x",
        "command env",
        "git --config-env=x=Y push -f",
        "git --attr-source HEAD push --force",
    ],
)
def test_the_guard_refuses_forbidden_commands(command: str) -> None:
    code, stderr = _main("guard", _event(command=command))
    assert code == 2
    assert stderr.startswith("refused:")
    assert guard_reason(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "env -u OPENROUTER_API_KEY -u CAOS_REQUIRE_PROVIDER make test",
        "git push origin codex/branch",
        "git commit -m 'fix: done'",
        "pip install --require-hashes -r requirements.txt",
        "cp .env.example .env.example.bak",
        "cat <<'EOF'\nit's prose with an unbalanced quote\nEOF",
        "git commit -F- <<'EOF'\nguard a bare env) in prose\nEOF",
        "git log --grep commit -n 3",
        "git commit -m msg\nhead -n 5 file",
        "grep -r foo env",
        "git -C /repo log --oneline -3",
        "env -u OPENROUTER_API_KEY FOO=1 python script.py",
        "set -euo pipefail",
        "export FOO=1",
        ".venv/bin/pip install --require-hashes -r requirements.txt",
    ],
)
def test_the_guard_allows_ordinary_commands(command: str) -> None:
    assert _main("guard", _event(command=command)) == (0, "")


@pytest.mark.parametrize(
    "raw",
    ["", "not json", "[]", json.dumps({"tool_input": {}}), _event(command=7)],
)
def test_malformed_events_refuse_without_echoing_them(raw: str) -> None:
    with pytest.raises(HookInputError):
        parse_event(raw, "command")
    for mode in ("guard", "format"):
        code, stderr = _main(mode, raw)
        assert (code, stderr.strip()) == (2, MALFORMED)


def test_an_unknown_mode_refuses() -> None:
    assert _main("other", _event(command="ls"))[0] == 2


def test_format_targets_only_authored_files(tmp_path: Path) -> None:
    (tmp_path / "vendor").mkdir()
    (tmp_path / "frontend").mkdir()
    authored = tmp_path / "a.py"
    vendored = tmp_path / "vendor/b.py"
    linked = tmp_path / "c.py"
    styled = tmp_path / "frontend/d.css"
    outside = tmp_path / "e.css"
    for path in (authored, vendored, styled, outside):
        path.write_text("x = 1\n")
    linked.symlink_to(vendored)

    assert format_target(str(authored), tmp_path) == authored.resolve()
    assert format_target(str(styled), tmp_path) == styled.resolve()
    for skipped in (
        vendored,
        linked,
        outside,
        tmp_path / "missing.py",
        Path("/etc/hosts"),
    ):
        assert format_target(str(skipped), tmp_path) is None


def test_format_file_runs_the_pinned_formatter_on_one_path(tmp_path: Path) -> None:
    calls: list[tuple[list[str], object]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, kwargs["cwd"]))
        return subprocess.CompletedProcess(argv, 0)

    def missing(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        raise FileNotFoundError

    prettier = tmp_path / "frontend/node_modules/.bin/prettier"
    prettier.parent.mkdir(parents=True)
    prettier.write_text("")
    assert format_file(tmp_path / "a.py", tmp_path, run) == 0
    assert format_file(tmp_path / "frontend/d.tsx", tmp_path, run) == 0
    assert calls == [
        (
            [
                str(Path(sys.executable).parent / "ruff"),
                "format",
                "--force-exclude",
                str(tmp_path / "a.py"),
            ],
            tmp_path,
        ),
        (
            [
                str(tmp_path / "frontend/node_modules/.bin/prettier"),
                "--write",
                str(tmp_path / "frontend/d.tsx"),
            ],
            # From frontend/, so frontend/.prettierignore applies.
            tmp_path / "frontend",
        ),
    ]
    assert format_file(tmp_path / "a.py", tmp_path, missing) == 2


def test_the_real_formatter_formats_python_and_skips_the_vendor_path(
    tmp_path: Path,
) -> None:
    authored = tmp_path / "a.py"
    authored.write_text("x   =  1\n")
    assert format_file(authored, tmp_path) == 0
    assert authored.read_text() == "x = 1\n"

    vendored = REPO / "vendor/deploy-v/verify_package.py"
    before = sha256(vendored.read_bytes()).hexdigest()
    assert format_target(str(vendored)) is None
    assert _main("format", _event(file_path=str(vendored))) == (0, "")
    assert sha256(vendored.read_bytes()).hexdigest() == before


def test_settings_wire_both_hooks_through_stdin() -> None:
    settings = json.loads(SETTINGS.read_text())
    [pre] = settings["hooks"]["PreToolUse"]
    [post] = settings["hooks"]["PostToolUse"]
    guard = pre["hooks"][0]["command"]
    fmt = post["hooks"][0]["command"]
    assert pre["matcher"] == "Bash"
    assert post["matcher"] == "Write|Edit|MultiEdit"
    assert 'claude_hook.py" guard' in guard and guard.endswith("|| exit 2")
    assert 'claude_hook.py" format' in fmt
    for command in (guard, fmt):
        assert "CLAUDE_TOOL_INPUT" not in command and "CLAUDE_FILE_PATHS" not in command


def _wired(project: Path, command: str) -> int:
    hook = json.loads(SETTINGS.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]
    return subprocess.run(
        ["/bin/sh", "-c", hook["command"]],
        input=_event(command=command),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
        check=False,
    ).returncode


def test_the_wired_guard_blocks_through_the_shell(tmp_path: Path) -> None:
    """The real settings command, on a project with its venv and one without
    (a fresh worktree or CI), falls back to python3 and still decides."""
    with_venv = tmp_path / "with_venv"
    bare = tmp_path / "bare"
    for project in (with_venv, bare):
        (project / "scripts").mkdir(parents=True)
        (project / "scripts/claude_hook.py").symlink_to(REPO / "scripts/claude_hook.py")
    (with_venv / ".venv/bin").mkdir(parents=True)
    (with_venv / ".venv/bin/python").symlink_to(sys.executable)

    for project in (with_venv, bare):
        assert (_wired(project, "git push -f"), _wired(project, "git status")) == (2, 0)
    assert _wired(tmp_path / "missing", "git status") == 2


@pytest.mark.parametrize("text", ["os.environ", "process.env.KEY", "cat .env.example"])
def test_the_dotenv_rule_matches_a_path_not_a_word(text: str) -> None:
    assert guard_reason(f"python -c 'print({text!r})'") is None
    assert guard_reason("cat ./.env.local") is not None


def test_a_missing_formatter_skips_rather_than_failing(tmp_path: Path) -> None:
    """A fresh worktree has no node_modules: the edit is not a format failure."""
    (tmp_path / "frontend").mkdir()
    styled = tmp_path / "frontend/d.css"
    styled.write_text("a{}\n")
    assert format_file(styled, tmp_path) == SKIPPED
    stderr = io.StringIO()
    code = main(
        ["claude_hook.py", "format"],
        io.StringIO(_event(file_path=str(REPO / "frontend/package.json"))),
        stderr,
    )
    assert code == 0
