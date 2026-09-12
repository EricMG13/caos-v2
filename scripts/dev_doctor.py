#!/usr/bin/env python3
"""Check local development prerequisites without exposing configuration values."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys

# Commands below are fixed version probes; they never accept input or use a shell.
PYTHON_VERSION = sys.version_info[:2]
REQUIRED_CONFIGURATION = frozenset(
    {
        "CAOS_DATABASE_URL",
        "CAOS_TEST_POSTGRES_URL",
        "CAOS_BLOB_ROOT",
        "CAOS_TRUST_ROLE_HEADER",
        "CAOS_REQUIRE_POSTGRES",
    }
)
OPTIONAL_CONFIGURATION = frozenset(
    {
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
        "CAOS_REQUIRE_PROVIDER",
    }
)


def _version(command: list[str]) -> str:
    try:
        # The caller supplies only the fixed command lists in `_tool_versions`.
        result = subprocess.run(  # nosec B603
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "missing"
    return next(iter(result.stdout.strip().splitlines()), "missing")


def _tool_versions() -> list[tuple[str, str]]:
    return [
        ("node", _version(["node", "--version"]).removeprefix("v")),
        ("npm", _version(["npm", "--version"])),
        ("uv", _version(["uv", "--version"]).removeprefix("uv ").split()[0]),
        (
            "docker",
            _version(["docker", "--version"])
            .removeprefix("Docker version ")
            .split(",")[0],
        ),
        (
            "docker compose",
            _version(["docker", "compose", "version"])
            .removeprefix("Docker Compose version ")
            .removeprefix("v"),
        ),
        ("gitnexus", _version(["gitnexus", "--version"])),
        (
            "security Python",
            _version([".venv-security/bin/python", "--version"]).removeprefix(
                "Python "
            ),
        ),
        (
            "pre-commit",
            _version([".venv/bin/pre-commit", "--version"]).removeprefix("pre-commit "),
        ),
    ]


def main() -> int:
    healthy = True
    found_python = ".".join(map(str, PYTHON_VERSION))
    print(f"Python: {found_python}")
    if PYTHON_VERSION != (3, 14):
        print(f"Python 3.14 required; found {found_python}", file=sys.stderr)
        healthy = False

    tools = _tool_versions()
    for name, version in tools:
        print(f"{name}: {version}")
        if version == "missing":
            healthy = False
    versions = dict(tools)
    node_version = versions.get("node", "missing")
    if not node_version.startswith("24."):
        print(f"Node 24 required; found {node_version}", file=sys.stderr)
        healthy = False
    security_python = versions.get("security Python", "missing")
    if not security_python.startswith("3.12."):
        print(
            f"security Python 3.12 required; found {security_python}",
            file=sys.stderr,
        )
        healthy = False

    for name in sorted(REQUIRED_CONFIGURATION):
        present = bool(os.environ.get(name))
        print(f"{name}: {'present' if present else 'missing'}")
        healthy &= present
    for name in sorted(OPTIONAL_CONFIGURATION):
        state = "present" if os.environ.get(name) else "absent"
        print(f"{name}: {state} (optional live mode)")
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
