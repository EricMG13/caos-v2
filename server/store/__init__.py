"""The store: one PostgreSQL, and the schema it is required to already have.

`docs/REBUILD_PLAN.md` Phase 1 asks for the schema "in full at startup", which is
a claim about what a running process may assume. `apply_schema` is what makes the
claim true, and the reason it records a digest rather than re-running idempotent
DDL is in `schema.sql`: statements that quietly do nothing cannot tell a process
started against last month's database that a column it is about to write is not
there.

Drift is a refusal, not a migration. This repository has never deployed, so there
is no upgrade path to honour yet; the day there is, it is a decision entry and a
migration table, not an `IF NOT EXISTS` (CLAUDE.md known gaps).
"""

from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

import psycopg

from server.refusals import Refusal, RefusalCode

type StoreConnection = psycopg.Connection[tuple[Any, ...]]

SCHEMA = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")

# One well-known lock, held for the applying transaction only, so two processes
# starting at once do not both read an empty bookkeeping table and both apply.
# The value is arbitrary and permanent; it identifies this lock, nothing else.
_SCHEMA_LOCK = 0x0CA05_5CE_1
# One row, enforced by the database rather than argued from the lock above: the
# primary key admits only `true` and the CHECK admits only `true`, so a second
# row cannot be inserted and `SELECT` cannot become order-dependent.
_BOOKKEEPING = (
    "CREATE TABLE IF NOT EXISTS store_schema ("
    " only_row boolean PRIMARY KEY DEFAULT true CHECK (only_row),"
    " applied_digest text NOT NULL)"
)


class RunStatus(StrEnum):
    """A run's own state. Node states are the bundle's four and are not these."""

    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


def connect(url: str) -> StoreConnection:
    """A connection with the store's policy on it: transactions are explicit."""
    return psycopg.connect(url, autocommit=False)


def apply_schema(conn: StoreConnection, *, sql: str = SCHEMA) -> None:
    """Apply `sql` to a database nothing has applied a schema to; else check it.

    Refuses `STORE_SCHEMA_DRIFT` when the database was built from a different
    declared schema. The refusal carries the code alone: the schema body would
    put table and column names into whatever logs it.
    """
    digest = sha256(sql.encode("utf-8")).hexdigest()
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (_SCHEMA_LOCK,))
    conn.execute(_BOOKKEEPING)
    applied = conn.execute("SELECT applied_digest FROM store_schema").fetchone()
    if applied is None:
        conn.execute(sql)
        conn.execute("INSERT INTO store_schema (applied_digest) VALUES (%s)", (digest,))
    elif applied[0] != digest:
        # Rolling back here rather than leaving it to the caller releases the
        # advisory lock now; a refused startup should not hold it while it dies.
        conn.rollback()
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT)
    conn.commit()
