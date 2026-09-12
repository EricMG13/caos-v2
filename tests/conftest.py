"""Import paths for the test suite, and the database the store suite runs on."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import pytest

REPO = Path(__file__).resolve().parents[1]
# The gate scripts are executables, not a package; import them by path.
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

# The vendored bundle's verifier refuses a tree that carries bytecode.
sys.dont_write_bytecode = True

# The store suite needs a real PostgreSQL. Absent, it skips with its reason;
# CAOS_REQUIRE_POSTGRES=1 turns that skip into a failure, which is what CI sets,
# so that a store suite that skipped can never read as a store suite that passed
# (docs/AI_CODE_QUALITY.md section 4).
POSTGRES_URL = os.environ.get("CAOS_TEST_POSTGRES_URL")
POSTGRES_REQUIRED = os.environ.get("CAOS_REQUIRE_POSTGRES") == "1"
_UNSET = "CAOS_TEST_POSTGRES_URL is unset: no database to run the store suite against"


def _url_for(database: str) -> str:
    parts = urlsplit(POSTGRES_URL or "")
    return urlunsplit(parts._replace(path=f"/{database}"))


def gate_verdict(prompt: str, status: str = "READY") -> dict[str, object]:
    """The gate's readiness map when the prompt asked for one, nothing when it
    did not -- merged by a stub into the body it was already returning.

    Phase 11 refuses a gate that does not cover every other module of the pinned
    route, so four completion stubs need the same extra key; here once rather
    than as four copies of one row. Every fixture route in this suite with a gate
    is DEEP_RESEARCH -- CP-0 and CP-DR alone -- so one row covers the rest of it.
    """
    if "content_to_module_map" not in prompt:
        return {}
    return {
        "content_to_module_map": [
            {
                "module_id": "CP-DR",
                "readiness_status": status,
                "readiness_effect": "what the admitted source allows",
            }
        ]
    }


@pytest.fixture
def case(empty_database: str) -> Iterator[tuple[object, UUID]]:
    """An open case on a committed connection, with the schema applied.

    Typed loosely here so this module does not import the store at collection
    time; the suites that use it annotate the connection as `StoreConnection`.
    """
    from server.boundary_text import BoundaryText
    from server.store import apply_schema, connect
    from server.store.runs import create_case

    with connect(empty_database) as conn:
        apply_schema(conn)
        case_id = create_case(conn, BoundaryText.of("Acme 2026 refinancing"))
        conn.commit()
        yield conn, case_id


@pytest.fixture
def empty_database() -> Iterator[str]:
    """A database of its own, created empty and dropped after the test.

    A namespace inside one shared database would be cheaper and would not answer
    the question these tests ask: what a process finds when it starts against a
    database no schema has been applied to yet.
    """
    if POSTGRES_URL is None:
        if POSTGRES_REQUIRED:
            pytest.fail(_UNSET)
        pytest.skip(_UNSET)

    import psycopg

    name = f"caos_test_{uuid4().hex}"
    with psycopg.connect(POSTGRES_URL, autocommit=True) as admin:
        # The name is a uuid4 hex this function minted, never caller input.
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield _url_for(name)
    finally:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
