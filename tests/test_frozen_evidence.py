"""Native extraction seals protect admitted evidence and its historical pins."""

from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from test_case_ordering import _blocked
from test_run_inputs import SUBJECT, Prepared, prepared

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence import ingest
from server.evidence.citations import Citation, verify_citations
from server.evidence.ingest import Document, admit_pack
from server.evidence.read import read_block
from server.refusals import Refusal
from server.store import StoreConnection, connect
from server.store.run_inputs import load_run_input, pin_run_input

__all__ = ["prepared"]


@pytest.mark.parametrize("table", ["source_blocks", "source_tokens"])
def test_ordinary_mutation_cannot_change_pinned_evidence(
    prepared: Prepared, table: str
) -> None:
    conn, run, sources, bundle, _ = prepared
    pin = pin_run_input(conn, run, sources.version, bundle, subject=SUBJECT)
    source = sources.members[0].source_id
    with pytest.raises(psycopg.Error):
        conn.execute(f"UPDATE {table} SET text = 'two' WHERE source_id = %s", (source,))
    conn.rollback()
    assert load_run_input(conn, run) == pin
    assert read_block(conn, source_id=source, block_id="b000000").text.value == "one"
    with pytest.raises(Refusal, match=r"^CITATION_NOT_LOCATED$"):
        verify_citations(
            conn, delivered={source}, citations=[Citation(source, 1, "two")]
        )


def _parent(conn: StoreConnection) -> UUID:
    source = uuid4()
    conn.execute(
        "INSERT INTO sources (source_id, case_id, document_sha256, filename)"
        " SELECT %s, case_id, document_sha256, filename FROM sources LIMIT 1",
        (source,),
    )
    return source


def _insert(conn: StoreConnection, table: str, source: UUID) -> None:
    values = {
        "source_blocks": "(%s, 'b999999', 1, 'late')",
        "source_tokens": "(%s, 999999, 1, 0, 0, 'late', 0, 0, 1, 1)",
    }
    conn.execute(
        f"INSERT INTO {table} VALUES {values[table.rsplit('.', 1)[-1]]}", (source,)
    )


@pytest.mark.parametrize("table", ["source_blocks", "source_tokens"])
@pytest.mark.parametrize("known", [False, True])
@pytest.mark.parametrize("change", ["noop", "key", "owner", "delete", "truncate"])
def test_native_children_are_immutable(
    prepared: Prepared, table: str, known: bool, change: str
) -> None:
    conn, _, sources, _, _ = prepared
    other = _parent(conn)
    source = sources.members[0].source_id if known else other
    if not known:
        _insert(conn, table, source)
    conn.commit()
    before = conn.execute(f"SELECT * FROM {table} ORDER BY source_id").fetchall()
    statements = {
        "noop": f"UPDATE {table} SET text = text WHERE source_id = %s",
        "key": f"UPDATE {table} SET "
        + ("block_id = 'new'" if table == "source_blocks" else "token_id = -1")
        + " WHERE source_id = %s",
        "owner": f"UPDATE {table} SET source_id = '{other}' WHERE source_id = %s",
        "delete": f"DELETE FROM {table} WHERE source_id = %s",
        "truncate": f"TRUNCATE {table}",
    }
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        conn.execute(statements[change], None if change == "truncate" else (source,))
    conn.rollback()
    assert (
        conn.execute(f"SELECT * FROM {table} ORDER BY source_id").fetchall() == before
    )


@pytest.mark.parametrize(
    "tables", ["source_blocks, source_tokens", "sources CASCADE", "cases CASCADE"]
)
def test_combined_and_cascade_truncate_refuse(prepared: Prepared, tables: str) -> None:
    conn, _, _, _, _ = prepared
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        conn.execute(f"TRUNCATE {tables}")
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM source_blocks").fetchone() == (1,)


@pytest.mark.parametrize("table", ["source_blocks", "source_tokens"])
@pytest.mark.parametrize("path", ["values", "select", "multirow", "copy", "shadow"])
def test_sealed_source_refuses_valid_unique_late_insert(
    prepared: Prepared, table: str, path: str
) -> None:
    conn, _, sources, _, _ = prepared
    source = sources.members[0].source_id
    row = list(conn.execute(f"SELECT * FROM {table} LIMIT 1").fetchone() or ())
    row[1] = "b999999" if table == "source_blocks" else 999999
    placeholders = ",".join("%s" for _ in row)
    if path == "shadow":
        conn.execute(
            "CREATE SCHEMA shadow; CREATE TABLE shadow.sources (LIKE sources);"
            " CREATE TABLE shadow.source_extractions (LIKE source_extractions);"
            " SET search_path TO shadow, public"
        )
    with pytest.raises(psycopg.errors.CheckViolation, match="sealed"):
        if path == "copy":
            with conn.cursor().copy(f"COPY {table} FROM STDIN") as copy:
                copy.write_row(row)
        elif path == "multirow":
            second = [*row]
            second[1] = "b999998" if table == "source_blocks" else 999998
            conn.execute(
                f"INSERT INTO {table} VALUES ({placeholders}), ({placeholders})",
                (*row, *second),
            )
        elif path == "select":
            conn.execute(f"INSERT INTO {table} SELECT {placeholders}", row)
        else:
            _insert(conn, "public." + table if path == "shadow" else table, source)
    conn.rollback()
    assert conn.execute(f"SELECT count(*) FROM {table}").fetchone() == (1,)


@pytest.mark.parametrize(
    "isolation", ["repeatable read", "serializable", "read uncommitted"]
)
@pytest.mark.parametrize(
    "table", ["source_blocks", "source_tokens", "source_extractions"]
)
def test_non_read_committed_writes_refuse(
    prepared: Prepared, isolation: str, table: str
) -> None:
    conn, _, _, _, _ = prepared
    parent = _parent(conn)
    conn.commit()
    conn.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation}")
    with pytest.raises(psycopg.errors.InvalidTransactionState, match="read committed"):
        if table == "source_extractions":
            _seal(conn, parent)
        else:
            _insert(conn, table, parent)
    conn.rollback()


def _seal(conn: StoreConnection, source: UUID) -> None:
    # Synthetic visible UNKNOWN parent: exercises locking, not certified admission.
    conn.execute(
        "INSERT INTO source_extractions SELECT %s, format_version, extractor_identity,"
        " output_sha256, extraction_sha256 FROM source_extractions LIMIT 1",
        (source,),
    )


@pytest.mark.parametrize("table", ["source_blocks", "source_tokens"])
@pytest.mark.parametrize("commit", [False, True])
def test_visible_parent_seal_wait_refresh_and_independent_parent(
    prepared: Prepared, empty_database: str, table: str, commit: bool
) -> None:
    conn, _, _, _, _ = prepared
    source, independent = _parent(conn), _parent(conn)
    conn.commit()
    _seal(conn, source)
    with connect(empty_database) as other:
        other.execute("SET lock_timeout = '1s'")
        _insert(other, table, independent)
        other.commit()

        def waiting() -> None:
            if commit:
                with pytest.raises(psycopg.errors.CheckViolation, match="sealed"):
                    _insert(other, table, source)
                other.rollback()
            else:
                _insert(other, table, source)
                other.commit()

        with _blocked(conn, other, waiting):
            if not commit:
                conn.rollback()
    assert conn.execute(
        f"SELECT count(*) FROM {table} WHERE source_id = %s", (source,)
    ).fetchone() == (0 if commit else 1,)


@pytest.mark.parametrize("table", ["source_blocks", "source_tokens"])
def test_real_private_admission_refuses_external_children_in_both_orders(
    prepared: Prepared,
    empty_database: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    table: str,
) -> None:
    conn, _, sources, _, _ = prepared
    store_blocks = ingest._store_blocks
    with connect(empty_database) as other:
        other.execute("SET statement_timeout = '1s'")
        other.commit()

        def before_seal(
            c: StoreConnection, source: UUID, blocks: list[ingest._Block]
        ) -> None:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                _insert(other, table, source)
            other.rollback()
            store_blocks(c, source, blocks)

        monkeypatch.setattr(ingest, "_store_blocks", before_seal)
        [source] = admit_pack(
            conn,
            BlobStore(tmp_path),
            case_id=sources.case_id,
            documents=[Document(BoundaryText.of("private.txt"), b"private")],
        )
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            _insert(other, table, source)
        other.rollback()
        conn.commit()
        with pytest.raises(psycopg.errors.CheckViolation, match="sealed"):
            _insert(other, table, source)
        other.rollback()
    assert (
        read_block(conn, source_id=source, block_id="b000000").text.value == "private"
    )


def test_second_seal_failure_rolls_back_entire_pack(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    conn, case_id = case
    conn.execute(
        "CREATE FUNCTION fail_second_seal() RETURNS trigger LANGUAGE plpgsql AS $$"
        " BEGIN IF (SELECT count(*) FROM source_extractions) = 1 THEN"
        " RAISE EXCEPTION 'synthetic seal failure'; END IF; RETURN NEW; END $$;"
        " CREATE TRIGGER fail_second_seal BEFORE INSERT ON source_extractions"
        " FOR EACH ROW EXECUTE FUNCTION fail_second_seal()"
    )
    conn.commit()
    with pytest.raises(psycopg.errors.RaiseException, match="synthetic seal failure"):
        admit_pack(
            conn,
            BlobStore(tmp_path),
            case_id=case_id,
            documents=[Document(BoundaryText.of(name), b"one") for name in ("a", "b")],
        )
    conn.rollback()
    for table in ("sources", "source_blocks", "source_tokens", "source_extractions"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)
