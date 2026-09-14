"""Claude Code hooks, read from the event JSON on standard input.

The previous inline hooks read `CLAUDE_TOOL_INPUT_command` and
`CLAUDE_FILE_PATHS`, which Claude Code never sets, so the guard allowed every
command and the formatter formatted nothing (docs/DECISIONS.md §39). A hook
receives one JSON object on stdin with `tool_name` and `tool_input`; for a
PreToolUse hook, exit 2 blocks the call and stderr goes back to the model.

`guard` screens a Bash command. It is a pattern screen, not a sandbox: a command
built to hide its intent at run time passes. Any failure to read the event
refuses, and `.claude/settings.json` turns a crash or a missing interpreter
into a refusal too, so the guard fails closed.

`format` formats one authored file after a Write or Edit. Vendor and `.claude`
paths, files outside the repository and other suffixes are left byte for byte.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

REPO = Path(__file__).resolve().parents[1]
MALFORMED = "HOOK_INPUT_MALFORMED"
FORCE_PUSH = "refused: force push"
NO_VERIFY = "refused: --no-verify bypasses the gates in docs/AI_CODE_QUALITY.md"
UNPINNED = "refused: install from the hashed lock only"
CREDENTIALS = (
    "refused: credentials are read by the process, never printed (docs/DECISIONS.md 16)"
)
DOTENV = (
    "refused: .env is read by the process, never by a command (docs/DECISIONS.md 16)"
)
_OPERATORS = frozenset({"|", "||", "&", "&&", ";", ">", ">>", "<", "(", ")"})
_SKIPPED = ("vendor", ".claude")
_PYTHON = frozenset({".py"})
_FRONTEND = frozenset({".ts", ".tsx", ".css"})


class HookInputError(ValueError):
    """The event on stdin is not the shape this hook reads."""


def parse_event(raw: str, key: str) -> str:
    """`tool_input[key]` from one hook event, or `HookInputError`. Never echoes."""
    try:
        event = json.loads(raw)
    except ValueError:
        raise HookInputError(MALFORMED) from None
    tool_input = event.get("tool_input") if isinstance(event, dict) else None
    value = tool_input.get(key) if isinstance(tool_input, dict) else None
    if not isinstance(value, str) or not value:
        raise HookInputError(MALFORMED)
    return value


def guard_reason(command: str) -> str | None:
    """Why this Bash command is refused, or None to allow it."""
    if "--no-verify" in command:
        return NO_VERIFY
    if "printenv" in command or "$OPENROUTER" in command or "${OPENROUTER" in command:
        return CREDENTIALS
    if ".env" in command.replace(".env.example", ""):
        return DOTENV
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        # ponytail: an unbalanced quote (often prose in a heredoc) keeps only the
        # substring screen above; the token rules below need a split.
        return None
    return _token_reason(tokens)


def _token_reason(words: Sequence[str]) -> str | None:
    for index, word in enumerate(words):
        after = words[index + 1 :]
        until = _segment(after)
        if word == "push" and {"-f", "--force", "--force-with-lease"} & set(until):
            return FORCE_PUSH
        if word == "commit" and "-n" in until:
            return NO_VERIFY
        if word == "install" and index and words[index - 1] == "pip":
            if "--require-hashes" not in until:
                return UNPINNED
        if word == "env" and (not after or after[0] in _OPERATORS):
            return CREDENTIALS
    return None


def _segment(words: Sequence[str]) -> list[str]:
    """The arguments of one simple command: words up to the next operator."""
    taken = []
    for word in words:
        if word in _OPERATORS:
            break
        taken.append(word)
    return taken


def format_target(file_path: str, repo: Path = REPO) -> Path | None:
    """The authored file to format, or None to leave it untouched."""
    root = repo.resolve()
    path = Path(file_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    relative = path.relative_to(root)
    if relative.parts[0] in _SKIPPED or path.suffix not in _PYTHON | _FRONTEND:
        return None
    if path.suffix in _FRONTEND and relative.parts[0] != "frontend":
        return None
    return path


def format_file(
    path: Path,
    repo: Path = REPO,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> int:
    """Run the pinned formatter on one target. Returns its exit code."""
    if path.suffix in _PYTHON:
        # The pinned dev venv's ruff when `make venv` has been run (the local
        # dev flow); otherwise whatever `ruff` PATH resolves to (CI's `test`
        # job installs it system-wide, docs/DECISIONS.md §48).
        venv_ruff = repo / ".venv/bin/ruff"
        ruff = (
            str(venv_ruff)
            if venv_ruff.is_file()
            else shutil.which("ruff") or str(venv_ruff)
        )
        argv = [ruff, "format", "--force-exclude", str(path)]
    else:
        prettier = repo / "frontend/node_modules/.bin/prettier"
        argv = [str(prettier), "--write", str(path)]
    # Fixed executable and argv, no shell; the path was resolved inside the repo.
    return run(argv, capture_output=True, check=False).returncode


def main(argv: Sequence[str], stdin: TextIO, stderr: TextIO) -> int:
    mode = argv[1] if len(argv) == 2 else ""
    try:
        if mode == "guard":
            reason = guard_reason(parse_event(stdin.read(), "command"))
            if reason is None:
                return 0
            print(reason, file=stderr)
            return 2
        if mode == "format":
            target = format_target(parse_event(stdin.read(), "file_path"))
            if target is not None and format_file(target) != 0:
                print("HOOK_FORMAT_FAILED", file=stderr)
                return 2
            return 0
    except HookInputError:
        print(MALFORMED, file=stderr)
        return 2
    print("usage: claude_hook.py guard|format", file=stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv, sys.stdin, sys.stderr))
