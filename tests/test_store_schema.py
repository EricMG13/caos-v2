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

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import psycopg
import pytest

import server.store as store
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.ingest import Document, admit_pack
from server.evidence.read import read_block
from server.refusals import Refusal, RefusalCode
from server.store import SCHEMA, RunStatus, StoreConnection, apply_schema, connect
from server.store.routes import resolved_route
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


def _catalog(conn: StoreConnection) -> list[object]:
    """Compare native definitions, normalizing only each owned schema's name."""
    schema = conn.execute("SELECT current_schema()").fetchone()
    assert schema is not None
    queries = (
        "SELECT table_name,column_name,column_default,is_identity,is_generated"
        " FROM information_schema.columns WHERE table_schema=current_schema()"
        " ORDER BY table_name,ordinal_position",
        "SELECT c.relname,k.conname,k.contype,k.condeferrable,k.condeferred,"
        " k.convalidated,pg_get_constraintdef(k.oid) FROM pg_constraint k"
        " JOIN pg_class c ON c.oid=k.conrelid"
        " WHERE c.relnamespace=current_schema()::regnamespace"
        " ORDER BY c.relname,k.conname",
        "SELECT tablename,indexname,indexdef FROM pg_indexes"
        " WHERE schemaname=current_schema() ORDER BY tablename,indexname",
        "SELECT c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid)"
        " FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid"
        " WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal"
        " ORDER BY c.relname,t.tgname",
        "SELECT proname,pg_get_functiondef(oid) FROM pg_proc"
        " WHERE pronamespace=current_schema()::regnamespace ORDER BY proname",
        "SELECT table_name,view_definition FROM information_schema.views"
        " WHERE table_schema=current_schema() ORDER BY table_name",
    )
    return [
        [
            tuple(
                value.replace(schema[0] + ".", "<schema>.")
                if isinstance(value, str)
                else value
                for value in row
            )
            for row in conn.execute(query).fetchall()
        ]
        for query in queries
    ]


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
                "INSERT INTO runs (run_id, case_id, status, budget_ceiling)"
                " VALUES (%s, %s, %s, %s)",
                (uuid4(), case_id, status.value, Decimal("1.00")),
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


def test_an_autocommit_connection_is_refused_rather_than_half_applied(
    empty_database: str,
) -> None:
    """Everything `apply_schema` promises is a property of one transaction.

    Under autocommit the advisory lock is taken and released by its own
    statement, so two processes starting at once both apply; and the DDL commits
    separately from the digest that records it, so a crash between them leaves a
    database whose tables exist and whose bookkeeping says they do not -- which
    the next startup answers by applying the schema again, onto tables that are
    already there. The mode is refused rather than supported.
    """
    with psycopg.connect(empty_database, autocommit=True) as conn:
        with pytest.raises(Refusal) as caught:
            apply_schema(conn)

        assert caught.value.code is RefusalCode.STORE_NOT_TRANSACTIONAL

    with connect(empty_database) as conn:
        assert _columns(conn) == [], "a refused apply must leave nothing behind"


def test_the_drift_refusal_carries_no_schema_text(empty_database: str) -> None:
    """The refusal names the code and nothing else -- a schema body in a log line
    is the vendor and filesystem detail `server/refusals.py` exists to keep out."""
    with connect(empty_database) as conn:
        apply_schema(conn)

        with pytest.raises(Refusal) as caught:
            apply_schema(conn, sql=DRIFTED)

        assert str(caught.value) == RefusalCode.STORE_SCHEMA_DRIFT.value
        assert "a_later_build_added_this" not in repr(caught.value)


def _legacy(conn: StoreConnection) -> None:
    conn.execute(SCHEMA)
    conn.execute(store._BOOKKEEPING)
    conn.execute(
        "INSERT INTO store_schema (applied_digest) VALUES (%s)",
        (sha256(SCHEMA.encode()).hexdigest(),),
    )
    conn.commit()


def _populate(conn: StoreConnection, blobs: BlobStore) -> str:
    """Synthetic legacy records spanning evidence, route, audit and billing."""
    digest = blobs.put(b"synthetic legacy document and artifact")
    case_id = create_case(conn, BoundaryText.of("legacy evidence"))
    run_id = start_run(conn, case_id)
    attempt_id, source_id = uuid4(), uuid4()
    conn.execute(
        "INSERT INTO sources (source_id, case_id, document_sha256, filename)"
        " VALUES (%s, %s, %s, 'synthetic.txt')",
        (source_id, case_id, digest),
    )
    conn.execute(
        "INSERT INTO source_blocks VALUES (%s, 'b000000', 1, 'synthetic')", (source_id,)
    )
    conn.execute(
        "INSERT INTO source_tokens VALUES (%s, 0, 1, 0, 0, 'synthetic', 1, 2, 3, 4)",
        (source_id,),
    )
    conn.execute(
        "INSERT INTO run_attempts (attempt_id, run_id, route_node_id)"
        " VALUES (%s, %s, 'CP-DR')",
        (attempt_id, run_id),
    )
    conn.execute(
        "INSERT INTO artifacts"
        " (attempt_id, artifact_sha256, run_id, case_id, model, generation_id)"
        " VALUES (%s, %s, %s, %s, 'synthetic', 'synthetic')",
        (attempt_id, digest, run_id, case_id),
    )
    conn.execute(
        "INSERT INTO budget_ledger (attempt_id, run_id, amount) VALUES (%s, %s, 0.25)",
        (attempt_id, run_id),
    )
    conn.execute(
        "INSERT INTO budget_reservations (attempt_id, run_id, amount)"
        " VALUES (%s, %s, 0.50)",
        (attempt_id, run_id),
    )
    conn.execute(
        "INSERT INTO run_routes"
        " (run_id, profile_id, selection_id, route_digest, resolved)"
        " VALUES (%s, 'synthetic', 'synthetic', %s, '{}')",
        (run_id, digest),
    )
    conn.execute(
        "INSERT INTO run_events (run_id, seq, name) VALUES (%s, 1, 'ROUTE_PINNED')",
        (run_id,),
    )
    conn.execute(
        "INSERT INTO audit_events"
        " (case_id, seq, actor_id, action, payload_sha256,"
        " previous_sha256, entry_sha256)"
        " VALUES (%s, 1, %s, 'synthetic', %s, %s, %s)",
        (case_id, uuid4(), digest, digest, digest),
    )
    conn.commit()
    return digest


def _records(
    conn: StoreConnection, columns: list[tuple[object, ...]] | None = None
) -> dict[str, object]:
    """Compare the original named tables/columns, including all their rows."""
    tables: dict[str, list[str]] = {}
    for table, column, *_ in _columns(conn) if columns is None else columns:
        if table not in {"store_schema", "store_migrations"}:
            tables.setdefault(str(table), []).append(str(column))
    return {
        table: conn.execute(
            psycopg.sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
                psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, names)),
                psycopg.sql.Identifier(table),
                psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, names)),
            )
        ).fetchall()
        for table, names in tables.items()
    }


def test_real_legacy_upgrade_preserves_evidence_with_unknown_provenance(
    empty_database: str,
    tmp_path: Path,
) -> None:
    with connect(empty_database) as conn:
        _legacy(conn)
        blobs = BlobStore(tmp_path)
        digest = _populate(conn, blobs)
        columns = _columns(conn)
        before = _records(conn, columns)
        apply_schema(conn)
        assert _records(conn, columns) == before
        assert conn.execute("SELECT count(*) FROM source_extractions").fetchone() == (
            0,
        )
        row = conn.execute("SELECT source_id, case_id FROM sources").fetchone()
        assert row is not None
        source, case_id = row
        assert (
            read_block(conn, source_id=source, block_id="b000000").text.value
            == "synthetic"
        )
        assert blobs.get(digest) == b"synthetic legacy document and artifact"
        upgraded = _columns(conn)
        catalog = _catalog(conn)
        apply_schema(conn)
        assert _records(conn, columns) == before
        [new_source] = admit_pack(
            conn,
            blobs,
            case_id=case_id,
            documents=[Document(BoundaryText.of("new.txt"), b"known extraction")],
        )
        assert conn.execute("SELECT source_id FROM source_extractions").fetchall() == [
            (new_source,)
        ]
        conn.commit()
        conn.execute("CREATE SCHEMA real_fresh")
        conn.execute("SET search_path TO real_fresh")
        apply_schema(conn)
        assert _columns(conn) == upgraded
        assert _catalog(conn) == catalog


@pytest.mark.parametrize("prefix", [2, 3, 4, 5])
def test_real_extraction_upgrade_preserves_known_and_unknown_rows(
    empty_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prefix: int
) -> None:
    with connect(empty_database) as conn:
        with monkeypatch.context() as patch:
            patch.setattr(store, "MIGRATIONS", store.MIGRATIONS[:prefix])
            apply_schema(conn)
        blobs = BlobStore(tmp_path)
        digest = _populate(conn, blobs)
        case_id = conn.execute("SELECT case_id FROM cases LIMIT 1").fetchone()
        assert case_id is not None
        admit_pack(
            conn,
            blobs,
            case_id=case_id[0],
            documents=[Document(BoundaryText.of("known.txt"), b"known")],
        )
        conn.commit()
        columns, before = _columns(conn), _records(conn)
        apply_schema(conn)
        assert _records(conn, columns) == before
        apply_schema(conn)
        assert _records(conn, columns) == before
        assert conn.execute("SELECT count(*) FROM run_inputs").fetchone() == (0,)
        assert blobs.get(digest) == b"synthetic legacy document and artifact"

        [run] = conn.execute("SELECT run_id FROM runs").fetchone() or ()
        with pytest.raises(Refusal, match=r"^ROUTE_IDENTITY_INVALID$"):
            resolved_route(conn, run)


def test_populated_legacy_advances_and_repeat_preserves_history(
    empty_database: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with connect(empty_database) as conn:
        _legacy(conn)
        blobs = BlobStore(tmp_path)
        digest = _populate(conn, blobs)
        columns = _columns(conn)
        before = _records(conn, columns)
        conn.commit()
        monkeypatch.setattr(
            store,
            "MIGRATIONS",
            (
                ("0001_legacy", SCHEMA),
                (
                    "0002_probe",
                    "ALTER TABLE cases ADD COLUMN migration_probe integer DEFAULT 7",
                ),
            ),
        )
        apply_schema(conn)
        assert conn.execute("SELECT migration_probe FROM cases").fetchone() == (7,)
        assert _records(conn, columns) == before
        assert blobs.get(digest) == b"synthetic legacy document and artifact"
        history = conn.execute(
            "SELECT * FROM store_migrations ORDER BY version"
        ).fetchall()
        assert len(history) == 2
        apply_schema(conn)
        assert (
            conn.execute("SELECT * FROM store_migrations ORDER BY version").fetchall()
            == history
        )
        upgraded_columns = _columns(conn)
        conn.execute("CREATE SCHEMA fresh_equivalence")
        conn.execute("SET search_path TO fresh_equivalence")
        apply_schema(conn)
        assert _columns(conn) == upgraded_columns
        assert conn.execute(
            "SELECT version, name, digest FROM store_migrations ORDER BY version"
        ).fetchall() == [row[:3] for row in history]


@pytest.mark.parametrize(
    "tamper",
    [
        "UPDATE store_migrations SET digest = 'edited' WHERE version = 1",
        "UPDATE store_migrations SET name = 'unknown' WHERE version = 1",
        "UPDATE store_migrations SET version ="
        " (SELECT max(version) + 1 FROM store_migrations) WHERE version = 1",
        "DELETE FROM store_migrations",
        "DROP TABLE store_migrations",
        "DELETE FROM store_schema",
        "UPDATE store_schema SET applied_digest = 'invalid'",
    ],
)
def test_migration_history_tampering_refuses(empty_database: str, tamper: str) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.execute(tamper)
        conn.commit()
        with pytest.raises(Refusal) as caught:
            apply_schema(conn)
        assert str(caught.value) == RefusalCode.STORE_SCHEMA_DRIFT.value
        assert conn.info.transaction_status is psycopg.pq.TransactionStatus.IDLE


@pytest.mark.parametrize("state", ["fresh", "legacy", "versioned"])
def test_failed_migration_rolls_back_and_releases_lock(
    empty_database: str,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    rollback = store.rollback_or_close
    failed_states = []

    def record_failure(connection: StoreConnection) -> None:
        failed_states.append(connection.info.transaction_status)
        rollback(connection)

    monkeypatch.setattr(store, "rollback_or_close", record_failure)
    with connect(empty_database) as conn:
        if state == "legacy":
            _legacy(conn)
        elif state == "versioned":
            apply_schema(conn)
        before, catalog = _columns(conn), _catalog(conn)
        conn.commit()
        monkeypatch.setattr(
            store,
            "MIGRATIONS",
            (
                *store.MIGRATIONS,
                (
                    "probe_fails",
                    "CREATE TABLE secret_probe (id integer); SELECT missing_secret",
                ),
            ),
            raising=False,
        )
        with pytest.raises(Refusal) as caught:
            apply_schema(conn)
        assert "secret" not in str(caught.value)
        assert failed_states == [psycopg.pq.TransactionStatus.INERROR]
        assert conn.info.transaction_status is psycopg.pq.TransactionStatus.IDLE
        assert _columns(conn) == before
        assert _catalog(conn) == catalog
        with connect(empty_database) as other:
            assert other.execute(
                "SELECT pg_try_advisory_xact_lock(%s)", (store._SCHEMA_LOCK,)
            ).fetchone() == (True,)


@pytest.mark.parametrize("state", ["fresh", "legacy", "prefix"])
def test_concurrent_starters_apply_once(
    empty_database: str,
    state: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if state != "fresh":
        with connect(empty_database) as conn:
            if state == "legacy":
                _legacy(conn)
            else:
                with monkeypatch.context() as patch:
                    patch.setattr(store, "MIGRATIONS", store.MIGRATIONS[:4])
                    apply_schema(conn)
            _populate(conn, BlobStore(tmp_path))
    monkeypatch.setattr(
        store,
        "MIGRATIONS",
        (*store.MIGRATIONS, ("probe_once", "CREATE TABLE once_only (id integer)")),
    )
    ready = Barrier(2)

    def start() -> None:
        with connect(empty_database) as conn:
            ready.wait(timeout=10)
            apply_schema(conn)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(start) for _ in range(2)]
        for future in futures:
            future.result(timeout=15)
    with connect(empty_database) as conn:
        assert conn.execute("SELECT count(*) FROM store_migrations").fetchone() == (
            len(store.MIGRATIONS),
        )


def test_interruption_before_commit_rolls_back(
    empty_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migrate = store._migrate

    def interrupted(conn: StoreConnection, sql: str) -> None:
        migrate(conn, sql)
        raise KeyboardInterrupt

    monkeypatch.setattr(store, "_migrate", interrupted)
    with connect(empty_database) as conn:
        with pytest.raises(KeyboardInterrupt):
            apply_schema(conn)
        assert conn.info.transaction_status is psycopg.pq.TransactionStatus.IDLE
        assert _columns(conn) == []


@pytest.mark.parametrize("manifest", [(), (("wrong_baseline", SCHEMA),)])
def test_invalid_manifest_refuses_without_mutation(
    empty_database: str,
    monkeypatch: pytest.MonkeyPatch,
    manifest: tuple[tuple[str, str], ...],
) -> None:
    monkeypatch.setattr(store, "MIGRATIONS", manifest)
    with connect(empty_database) as conn:
        with pytest.raises(Refusal):
            apply_schema(conn)
        assert _columns(conn) == []


def test_invalid_legacy_digest_preserves_data(empty_database: str) -> None:
    with connect(empty_database) as conn:
        _legacy(conn)
        case_id = create_case(conn, BoundaryText.of("preserved"))
        conn.execute("UPDATE store_schema SET applied_digest = 'invalid'")
        conn.commit()
        with pytest.raises(Refusal):
            apply_schema(conn)
        assert conn.execute(
            "SELECT title FROM cases WHERE case_id = %s", (case_id,)
        ).fetchone() == ("preserved",)
        assert conn.execute("SELECT to_regclass('store_migrations')").fetchone() == (
            None,
        )


@pytest.mark.parametrize("change", ["older", "edited", "reordered", "missing_tail"])
def test_newer_database_or_changed_applied_prefix_refuses(
    empty_database: str,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    baseline = store.MIGRATIONS
    later = (*baseline, ("probe_tail", "CREATE TABLE probe (id integer)"))
    monkeypatch.setattr(store, "MIGRATIONS", later)
    with connect(empty_database) as conn:
        apply_schema(conn)
        if change == "older":
            monkeypatch.setattr(store, "MIGRATIONS", baseline)
        elif change == "edited":
            monkeypatch.setattr(
                store, "MIGRATIONS", (*baseline, ("probe_tail", "SELECT 1"))
            )
        elif change == "reordered":
            conn.execute(
                "UPDATE store_migrations SET version = version + %s", (len(later),)
            )
        else:
            conn.execute(
                "DELETE FROM store_migrations WHERE version = %s", (len(later),)
            )
        conn.commit()
        with pytest.raises(Refusal):
            apply_schema(conn)


def test_apply_schema_closed_connection_is_sanitized(empty_database: str) -> None:
    """rollback_or_close must retain the migration's safe refusal code."""
    conn = connect(empty_database)
    conn.close()
    with pytest.raises(Refusal) as caught:
        apply_schema(conn)
    assert caught.value.code is RefusalCode.STORE_SCHEMA_DRIFT


def test_apply_schema_cleanup_preserves_cancellation(
    empty_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(conn: StoreConnection, sql: str) -> None:
        conn.close()
        raise KeyboardInterrupt

    monkeypatch.setattr(store, "_migrate", interrupted)
    with connect(empty_database) as conn, pytest.raises(KeyboardInterrupt):
        apply_schema(conn)


@pytest.mark.parametrize(
    "table,column",
    [
        ("runs", "budget_ceiling"),
        ("budget_reservations", "amount"),
        ("budget_ledger", "amount"),
    ],
)
@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "-Infinity"])
def test_native_money_constraints_refuse_malformed_rows(
    empty_database: str, tmp_path: Path, table: str, column: str, value: str
) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        _populate(conn, BlobStore(tmp_path))
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(f"UPDATE {table} SET {column} = %s", (Decimal(value),))
        conn.rollback()


@pytest.mark.parametrize("table", ["budget_reservations", "budget_ledger"])
def test_budget_owner_keys_reject_existing_unrelated_run(
    empty_database: str, tmp_path: Path, table: str
) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        _populate(conn, BlobStore(tmp_path))
        other_case = create_case(conn, BoundaryText.of("unrelated owner"))
        other_run = start_run(conn, other_case)
        conn.commit()
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(f"UPDATE {table} SET run_id = %s", (other_run,))
        conn.rollback()


@pytest.mark.parametrize("prefix", [0, 5])
@pytest.mark.parametrize(
    "malformed",
    [
        ("runs", "budget_ceiling", "-1"),
        ("runs", "budget_ceiling", "NaN"),
        ("budget_ledger", "amount", "-1"),
        ("budget_ledger", "amount", "Infinity"),
        ("budget_reservations", "amount", "NaN"),
        ("budget_reservations", "amount", "Infinity"),
        ("budget_reservations", "run_id", "unrelated"),
        ("budget_ledger", "run_id", "unrelated"),
    ],
)
def test_invalid_populated_money_upgrade_refuses_atomically(
    empty_database: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prefix: int,
    malformed: tuple[str, str, str],
) -> None:
    table, column, value = malformed
    with connect(empty_database) as conn:
        if prefix:
            with monkeypatch.context() as patch:
                patch.setattr(store, "MIGRATIONS", store.MIGRATIONS[:prefix])
                apply_schema(conn)
        else:
            _legacy(conn)
        _populate(conn, BlobStore(tmp_path))
        invalid: Decimal | UUID
        if value == "unrelated":
            owner = create_case(conn, BoundaryText.of("unrelated historical owner"))
            invalid = start_run(conn, owner)
        else:
            invalid = Decimal(value)
        conn.execute(f"UPDATE {table} SET {column} = %s", (invalid,))
        conn.commit()
        before, columns, catalog = repr(_records(conn)), _columns(conn), _catalog(conn)
        history = conn.execute("SELECT applied_digest FROM store_schema").fetchall()
        migrations = (
            conn.execute("SELECT * FROM store_migrations ORDER BY version").fetchall()
            if prefix
            else None
        )
        conn.commit()
        with pytest.raises(Refusal, match=r"^STORE_SCHEMA_DRIFT$"):
            apply_schema(conn)
        assert conn.info.transaction_status is psycopg.pq.TransactionStatus.IDLE
        assert repr(_records(conn)) == before
        assert _columns(conn) == columns
        assert _catalog(conn) == catalog
        assert (
            conn.execute("SELECT applied_digest FROM store_schema").fetchall()
            == history
        )
        if prefix:
            assert (
                conn.execute(
                    "SELECT * FROM store_migrations ORDER BY version"
                ).fetchall()
                == migrations
            )
