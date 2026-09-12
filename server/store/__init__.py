"""One PostgreSQL store with ordered, immutable host-owned migrations."""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

import psycopg

from server.refusals import Refusal, RefusalCode

type StoreConnection = psycopg.Connection[tuple[Any, ...]]

SCHEMA = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
# Append reviewed SQL files here; never edit an applied entry or schema.sql.
MIGRATIONS = (
    ("0001_legacy", SCHEMA),
    (
        "0002_extraction",
        Path(__file__).with_name("0002_extraction.sql").read_text(encoding="utf-8"),
    ),
    (
        "0003_source_sets",
        Path(__file__).with_name("0003_source_sets.sql").read_text(encoding="utf-8"),
    ),
    (
        "0004_route_integrity",
        Path(__file__)
        .with_name("0004_route_integrity.sql")
        .read_text(encoding="utf-8"),
    ),
    (
        "0005_run_inputs",
        Path(__file__).with_name("0005_run_inputs.sql").read_text(encoding="utf-8"),
    ),
    (
        "0006_budget",
        Path(__file__).with_name("0006_budget.sql").read_text(encoding="utf-8"),
    ),
)

# One well-known lock, held for the applying transaction only, so two processes
# starting at once do not both read an empty bookkeeping table and both apply.
# The value is arbitrary and permanent; it identifies this lock, nothing else.
_SCHEMA_LOCK = 0x0CA05_5CE_1
# Metadata lives outside the immutable baseline. The legacy digest is replaced
# by a digest of the full ordered history on adoption. IF NOT EXISTS only
# bootstraps metadata; it never substitutes for a business-schema migration.
#
# One row, enforced by the database rather than argued from the lock above: the
# primary key admits only `true` and the CHECK admits only `true`, so a second
# row cannot be inserted and `SELECT` cannot become order-dependent.
_BOOKKEEPING = (
    "CREATE TABLE IF NOT EXISTS store_schema ("
    " only_row boolean PRIMARY KEY DEFAULT true CHECK (only_row),"
    " applied_digest text NOT NULL)"
)
_HISTORY = (
    "CREATE TABLE IF NOT EXISTS store_migrations ("
    " version integer PRIMARY KEY CHECK (version > 0),"
    " name text NOT NULL UNIQUE, digest text NOT NULL,"
    " applied_at timestamptz NOT NULL DEFAULT now())"
)


class RunStatus(StrEnum):
    """A run's own state. Node states are the bundle's four and are not these."""

    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


def connect(url: str) -> StoreConnection:
    """A connection with the store's policy on it: transactions are explicit."""
    return psycopg.connect(url, autocommit=False)


def rollback_or_close(conn: StoreConnection) -> None:
    """A failed rollback must not mask the refusal or leave a committable unit."""
    try:
        conn.rollback()
    except psycopg.Error:
        conn.close()


def apply_schema(conn: StoreConnection, *, sql: str = SCHEMA) -> None:
    """Advance a verified migration prefix atomically, or refuse sanitized.

    Owns and completes the caller transaction, as before: call before business
    writes. `sql` is retained for compatibility but must match the legacy file.
    """
    if conn.autocommit:
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)
    try:
        _migrate(conn, sql)
        conn.commit()
    except (Refusal, psycopg.Error):
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT) from None
    except BaseException:
        rollback_or_close(conn)
        raise


def _migrate(conn: StoreConnection, sql: str) -> None:
    """Validate the complete applied prefix under the lock before advancing it."""
    if sql != SCHEMA or not MIGRATIONS or MIGRATIONS[0] != ("0001_legacy", SCHEMA):
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT)
    expected = [
        (version, name, sha256(body.encode("utf-8")).hexdigest())
        for version, (name, body) in enumerate(MIGRATIONS, 1)
    ]
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (_SCHEMA_LOCK,))
    conn.execute(_BOOKKEEPING)
    conn.execute(_HISTORY)
    applied = conn.execute("SELECT applied_digest FROM store_schema").fetchone()
    history = conn.execute(
        "SELECT version, name, digest FROM store_migrations ORDER BY version"
    ).fetchall()
    applied_count = len(history)
    # The head digest also binds the history length: deleting a trailing
    # applied row cannot turn a newer database into a valid older prefix.
    head = sha256(json.dumps(history).encode("utf-8")).hexdigest()
    legacy = applied == (expected[0][2],) and not history
    if (
        history != expected[:applied_count]
        or (applied is None and history)
        or (applied is not None and not legacy and applied != (head,))
    ):
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT)
    if applied_count == len(expected):
        return
    for version, name, digest in expected[applied_count:]:
        if not (legacy and version == 1):
            conn.execute(MIGRATIONS[version - 1][1])
        conn.execute(
            "INSERT INTO store_migrations (version, name, digest) VALUES (%s, %s, %s)",
            (version, name, digest),
        )
    digest = sha256(json.dumps(expected).encode("utf-8")).hexdigest()
    conn.execute(
        "INSERT INTO store_schema (applied_digest) VALUES (%s)"
        " ON CONFLICT (only_row)"
        " DO UPDATE SET applied_digest = EXCLUDED.applied_digest",
        (digest,),
    )
