"""Phase 1: the store applies the schema it declares, and says so when it cannot.

`docs/REBUILD_PLAN.md` Phase 1 asks for the Postgres schema "in full at startup".
The failure that phrasing invites is `CREATE TABLE IF NOT EXISTS` over a database
an older build created: every statement succeeds, the missing column is never
mentioned, and the first write to it fails in production instead of at boot. So
startup records which declared schema it applied and refuses a database that was
built from a different one.

Invariants protected: `SYSTEM_SPEC.md` section 2 -- PostgreSQL owns everything
transactional, and what it owns is the declared shape rather than whatever the
first deployment happened to create.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import SCHEMA, RunStatus, StoreConnection, apply_schema, connect
from server.store.runs import create_case, run_status, start_run

# A declared schema that differs from the repository's by one table -- the shape
# a later build has when it adds one, and the shape `IF NOT EXISTS` hides.
DRIFTED = SCHEMA + "\nCREATE TABLE a_later_build_added_this (case_id uuid);\n"


def _columns(conn: StoreConnection) -> list[tuple[object, ...]]:
    """Every column of every table in the connection's own namespace."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT table_name, column_name, data_type, is_nullable"
            " FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " ORDER BY table_name, column_name"
        )
        return cursor.fetchall()


def test_the_declared_schema_holds_a_case_and_its_run(empty_database: str) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        case_id = create_case(conn, BoundaryText.of("Acme 2026 refinancing"))
        run_id = start_run(conn, case_id)
        conn.commit()

        assert run_status(conn, run_id) is RunStatus.RUNNING


def test_every_run_status_is_one_the_database_accepts(empty_database: str) -> None:
    """`RunStatus` and the `runs_status_is_known` CHECK are two spellings of one
    closed set. Nothing but this test stops a status added to one of them from
    reaching an INSERT that the other refuses."""
    with connect(empty_database) as conn:
        apply_schema(conn)
        case_id = create_case(conn, BoundaryText.of("Acme 2026 refinancing"))

        for status in RunStatus:
            conn.execute(
                "INSERT INTO runs (run_id, case_id, status) VALUES (%s, %s, %s)",
                (uuid4(), case_id, status.value),
            )
        conn.commit()


def test_applying_the_declared_schema_twice_changes_nothing(
    empty_database: str,
) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        after_first = _columns(conn)

        apply_schema(conn)

        assert _columns(conn) == after_first


def test_a_database_built_from_another_schema_is_refused(empty_database: str) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)

        with pytest.raises(Refusal) as caught:
            apply_schema(conn, sql=DRIFTED)

        assert caught.value.code is RefusalCode.STORE_SCHEMA_DRIFT


def test_the_drift_refusal_carries_no_schema_text(empty_database: str) -> None:
    """The refusal names the code and nothing else -- a schema body in a log line
    is the vendor and filesystem detail `server/refusals.py` exists to keep out."""
    with connect(empty_database) as conn:
        apply_schema(conn)

        with pytest.raises(Refusal) as caught:
            apply_schema(conn, sql=DRIFTED)

        assert str(caught.value) == RefusalCode.STORE_SCHEMA_DRIFT.value
        assert "a_later_build_added_this" not in repr(caught.value)
