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
    calls: list[list[str]] = []

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    assert format_file(tmp_path / "a.py", tmp_path, run) == 0
    assert format_file(tmp_path / "frontend/d.tsx", tmp_path, run) == 0
    assert calls == [
        [
            str(tmp_path / ".venv/bin/ruff"),
            "format",
            "--force-exclude",
            str(tmp_path / "a.py"),
        ],
        [
            str(tmp_path / "frontend/node_modules/.bin/prettier"),
            "--write",
            str(tmp_path / "frontend/d.tsx"),
        ],
    ]


def test_the_real_formatter_formats_authored_python_and_leaves_vendor_bytes(
    tmp_path: Path,
) -> None:
    authored = REPO / "tests" / f"_hook_probe_{os.getpid()}.py"
    vendored = next((REPO / "vendor").rglob("*.md"))
    before = sha256(vendored.read_bytes()).hexdigest()
    authored.write_text("x   =  1\n")
    try:
        assert _main("format", _event(file_path=str(authored))) == (0, "")
        assert authored.read_text() == "x = 1\n"
        assert _main("format", _event(file_path=str(vendored))) == (0, "")
    finally:
        authored.unlink()
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


def test_the_wired_guard_blocks_through_the_shell() -> None:
    command = json.loads(SETTINGS.read_text())["hooks"]["PreToolUse"][0]["hooks"][0][
        "command"
    ]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(REPO)}
    blocked = subprocess.run(
        ["/bin/sh", "-c", command],
        input=_event(command="git push -f"),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    allowed = subprocess.run(
        ["/bin/sh", "-c", command],
        input=_event(command="git status"),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    missing = subprocess.run(
        ["/bin/sh", "-c", command],
        input=_event(command="git status"),
        capture_output=True,
        text=True,
        env={**env, "CLAUDE_PROJECT_DIR": "/nonexistent"},
        check=False,
    )
    assert (blocked.returncode, allowed.returncode, missing.returncode) == (2, 0, 2)
