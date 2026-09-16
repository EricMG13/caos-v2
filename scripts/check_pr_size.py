"""Apply the hosted PR line-count policy to a caller-supplied base commit."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys

# This gate invokes only an absolute git executable with an argv list.

LIMIT = 800
EXCLUSIONS = (
    ":!*.lock",
    ":!requirements*.txt",
    # Root-anchored: git's default pathspec matching needs a `/` before the
    # name, so `**/vendor/**` would not match the bundle at `vendor/deploy-v/`.
    ":!vendor/**",
    ":!docs/**",
    ":!*package-lock.json",
    ":!frontend/fixtures/**",
)


def changed_lines(base: str) -> int:
    git = shutil.which("git")
    if git is None:
        raise FileNotFoundError("git")
    # No shell: the caller's base is one opaque argv value.
    subprocess.run(  # nosec B603
        [git, "rev-parse", "--verify", f"{base}^{{commit}}"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    # Fixed command and pathspec, again without a shell.
    result = subprocess.run(  # nosec B603
        [git, "diff", "--numstat", f"{base}...HEAD", "--", ".", *EXCLUSIONS],
        check=True,
        capture_output=True,
        text=True,
    )
    total = 0
    for line in result.stdout.splitlines():
        added, removed, _path = line.split("\t", 2)
        if added != "-" and removed != "-":
            total += int(added) + int(removed)
    return total


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1]:
        print("PR_BASE is required: pass the exact PR base commit", file=sys.stderr)
        return 2
    try:
        count = changed_lines(sys.argv[1])
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"cannot diff caller-supplied base {sys.argv[1]}", file=sys.stderr)
        return 2
    print(f"changed lines: {count}")
    if count > LIMIT:
        print("PR too large; split it (docs/AI_CODE_QUALITY.md)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
