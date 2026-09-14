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
    (
        "0007_call_outcomes",
        Path(__file__).with_name("0007_call_outcomes.sql").read_text(encoding="utf-8"),
    ),
    (
        "0008_frozen_evidence",
        Path(__file__)
        .with_name("0008_frozen_evidence.sql")
        .read_text(encoding="utf-8"),
    ),
    (
        "0009_accepted_owner",
        Path(__file__).with_name("0009_accepted_owner.sql").read_text(encoding="utf-8"),
    ),
    (
        "0010_blocked_runs",
        Path(__file__).with_name("0010_blocked_runs.sql").read_text(encoding="utf-8"),
    ),
    (
        "0011_run_subject",
        Path(__file__).with_name("0011_run_subject.sql").read_text(encoding="utf-8"),
    ),
    (
        "0012_artifact_record",
        Path(__file__)
        .with_name("0012_artifact_record.sql")
        .read_text(encoding="utf-8"),
    ),
    (
        "0013_run_work",
        Path(__file__).with_name("0013_run_work.sql").read_text(encoding="utf-8"),
    ),
    (
        "0014_command_requests",
        Path(__file__)
        .with_name("0014_command_requests.sql")
        .read_text(encoding="utf-8"),
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
    # Recoverable: the route has required work no accepted result can release.
    BLOCKED = "BLOCKED"
    # A requested cancel took effect before any worker drove the run further.
    CANCELLED = "CANCELLED"


def connect(url: str, *, connect_timeout: int | None = None) -> StoreConnection:
    """A connection with the store's policy on it: transactions are explicit.

    `connect_timeout` (seconds) bounds the connection attempt, for a caller
    such as the health probe that must not wait on an unanswering host.
    """
    if connect_timeout is None:
        return psycopg.connect(url, autocommit=False)
    return psycopg.connect(url, autocommit=False, connect_timeout=connect_timeout)


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


def verify_schema(conn: StoreConnection) -> None:
    """Refuse `STORE_SCHEMA_DRIFT` unless every declared migration is applied.

    The check `_migrate` makes, read-only: SELECTs alone, no DDL, no advisory
    lock, no write and no commit -- the caller owns (and should roll back or
    close) the transaction. A partial prefix is drift here too: a process that
    serves requests is one whose startup advanced it in full. A missing
    bookkeeping table is drift; any other store error propagates as itself.
    """
    expected = _expected_history()
    try:
        applied = conn.execute("SELECT applied_digest FROM store_schema").fetchone()
        history = conn.execute(
            "SELECT version, name, digest FROM store_migrations ORDER BY version"
        ).fetchall()
    except psycopg.errors.UndefinedTable:
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT) from None
    head = sha256(json.dumps(expected).encode("utf-8")).hexdigest()
    if history != expected or applied != (head,):
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT)


def _expected_history() -> list[tuple[int, str, str]]:
    """The ordered `(version, name, digest)` rows a fully migrated store holds."""
    if not MIGRATIONS or MIGRATIONS[0] != ("0001_legacy", SCHEMA):
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT)
    return [
        (version, name, sha256(body.encode("utf-8")).hexdigest())
        for version, (name, body) in enumerate(MIGRATIONS, 1)
    ]


def _migrate(conn: StoreConnection, sql: str) -> None:
    """Validate the complete applied prefix under the lock before advancing it."""
    if sql != SCHEMA:
        raise Refusal(RefusalCode.STORE_SCHEMA_DRIFT)
    expected = _expected_history()
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
        if (version, name) == (8, "0008_frozen_evidence"):
            # Historical v1 verification belongs only to this migration.
            from server.store.extraction_integrity import _verify_extractions_v1

            _verify_extractions_v1(conn)
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
