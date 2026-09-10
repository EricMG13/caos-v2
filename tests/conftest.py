"""Import paths for the test suite, and the database the store suite runs on."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

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
