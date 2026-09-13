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
import re
import shlex
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

REPO = Path(__file__).resolve().parents[1]
MALFORMED = "HOOK_INPUT_MALFORMED"
# `format_file`: the pinned formatter is not installed here.
SKIPPED = -1
FORCE_PUSH = "refused: force push"
NO_VERIFY = "refused: --no-verify bypasses the gates in docs/AI_CODE_QUALITY.md"
UNPINNED = "refused: install from the hashed lock only"
CREDENTIALS = (
    "refused: credentials are read by the process, never printed (docs/DECISIONS.md 16)"
)
DOTENV = (
    "refused: .env is read by the process, never by a command (docs/DECISIONS.md 16)"
)
# A `.env` path, not `os.environ`, `process.env` or `.env.example`.
_DOTENV = re.compile(r"(?<![\w.])\.env(?!\.example)(?![A-Za-z0-9_])")
# git global options that take a separate value (`git -C dir push`).
_GIT_VALUED = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
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
    if _DOTENV.search(command):
        return DOTENV
    # A newline ends a command as `;` does.
    lines = command.replace("\n", " ; ")
    try:
        lexer = shlex.shlex(lines, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        # An unbalanced quote (often prose in a heredoc): err toward refusing by
        # applying the token rules to a plain split rather than skipping them.
        tokens = lines.split()
    return _token_reason(tokens)


def _token_reason(words: Sequence[str]) -> str | None:
    for index, word in enumerate(words):
        before = words[index - 1] if index else ";"
        until = _segment(words[index + 1 :])
        if Path(word).name == "git":
            subcommand, rest = _git_subcommand(until)
            if subcommand == "push" and _forced(rest):
                return FORCE_PUSH
            if subcommand == "commit" and _flag(rest, "n"):
                return NO_VERIFY
        if before == "pip" and word == "install" and "--require-hashes" not in until:
            return UNPINNED
        # `env` as a command word with nothing left to run prints the environment.
        if (
            Path(word).name == "env"
            and before in _OPERATORS
            and not _env_command(until)
        ):
            return CREDENTIALS
    return None


def _git_subcommand(arguments: Sequence[str]) -> tuple[str, Sequence[str]]:
    """git's subcommand and its arguments, past git's own global options."""
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        index += 2 if arguments[index] in _GIT_VALUED else 1
    if index >= len(arguments):
        return "", ()
    return arguments[index], arguments[index + 1 :]


def _env_command(arguments: Sequence[str]) -> list[str]:
    """What `env` would run: its arguments less options and assignments."""
    left: list[str] = []
    skip = False
    for argument in arguments:
        if skip:
            skip = False
        elif argument in {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}:
            skip = True
        elif not left and (argument.startswith("-") or "=" in argument):
            continue
        else:
            left.append(argument)
    return left


def _forced(arguments: Sequence[str]) -> bool:
    return (
        any(a.startswith(("--force", "--mirror")) for a in arguments)
        or _flag(arguments, "f")
        or any(a.startswith("+") for a in arguments)
    )


def _flag(arguments: Sequence[str], letter: str) -> bool:
    """A short flag, alone or inside a cluster such as `-nm`."""
    return any(
        a.startswith("-") and not a.startswith("--") and letter in a[1:]
        for a in arguments
    )


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
    # Case-folded: a case-insensitive filesystem reaches `vendor` as `Vendor` too.
    top = relative.parts[0].casefold()
    if top in _SKIPPED or path.suffix not in _PYTHON | _FRONTEND:
        return None
    if path.suffix in _FRONTEND and top != "frontend":
        return None
    return path


def format_file(
    path: Path,
    repo: Path = REPO,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> int:
    """Run the pinned formatter on one target. Returns its exit code."""
    if path.suffix in _PYTHON:
        # Beside the running interpreter: the repo venv locally, the CI Python.
        ruff = Path(sys.executable).parent / "ruff"
        argv = [str(ruff), "format", "--force-exclude", str(path)]
        cwd = repo
    else:
        prettier = repo / "frontend/node_modules/.bin/prettier"
        argv = [str(prettier), "--write", str(path)]
        # From `frontend/`, so `frontend/.prettierignore` applies.
        cwd = repo / "frontend"
    if not Path(argv[0]).is_file():
        # A fresh worktree has no venv or node_modules: nothing to format with,
        # which is not a formatting failure. Lint still checks the file later.
        return SKIPPED
    try:
        # Fixed executable and argv, no shell; the path was resolved in the repo.
        return run(argv, cwd=cwd, capture_output=True, check=False).returncode
    except OSError:
        return 2


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
            code = 0 if target is None else format_file(target)
            if code == SKIPPED:
                print("HOOK_FORMAT_SKIPPED", file=stderr)
                return 0
            if code != 0:
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
