"""Run membership reads; caller authority integration remains a later task."""

from dataclasses import replace
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.pq import TransactionStatus
from test_extraction_provenance import Reader
from test_read_evidence import _CountingConnection
from test_run_inputs import SUBJECT, Prepared, prepared
from test_source_sets import _admit

from server.boundary_text import BoundaryText
from server.evidence import read
from server.evidence.extract import Extractor, PlainTextExtractor
from server.refusals import Refusal
from server.store import StoreConnection
from server.store.outcomes import execution_reads
from server.store.run_inputs import load_run_input, pin_run_input
from server.store.runs import create_case, start_run
from server.store.source_sets import snapshot_source_set

__all__ = ["prepared"]


@pytest.fixture
def pinned(prepared: Prepared) -> Prepared:
    conn, run, sources, bundle, _ = prepared
    pin_run_input(conn, run, sources.version, bundle, subject=SUBJECT)
    return prepared


def test_run_read_keeps_captured_membership_after_later_admission(
    pinned: Prepared, tmp_path: Path
) -> None:
    conn, run, sources, _, _ = pinned
    pin = load_run_input(conn, run)
    source = sources.members[0].source_id
    _admit(conn, sources.case_id, tmp_path)
    conn.commit()
    later = snapshot_source_set(conn, sources.case_id)
    assert later.version != sources.version
    counter = _CountingConnection(conn)
    block = read.read_run_block(
        cast(StoreConnection, counter), run_id=run, source_id=source, block_id="b000000"
    )
    assert block == read.Block(page=1, text=BoundaryText.of("one"))
    assert counter.executed == read.IO_BUDGET == 1
    assert load_run_input(conn, run) == pin


@pytest.mark.parametrize(
    "fault",
    ["missing-run", "missing-input", "wrong-case", "withdrawn", "missing-block"],
)
def test_run_read_refuses_unavailable_membership(
    pinned: Prepared, tmp_path: Path, fault: str
) -> None:
    conn, run, sources, _, _ = pinned
    source, block_id = sources.members[0].source_id, "b000000"
    if fault == "missing-run":
        run = uuid4()
    elif fault == "missing-input":
        run = start_run(conn, sources.case_id)
    elif fault == "wrong-case":
        other = create_case(conn, BoundaryText.of("other"))
        source = _admit(conn, other, tmp_path)
    elif fault == "withdrawn":
        conn.execute(
            "UPDATE sources SET withdrawn_at = now() WHERE source_id = %s", (source,)
        )
    else:
        block_id = "b999999"
    counter = _CountingConnection(conn)
    with pytest.raises(Refusal, match=r"^EVIDENCE_NOT_AVAILABLE$") as caught:
        read.read_run_block(
            cast(StoreConnection, counter),
            run_id=run,
            source_id=source,
            block_id=block_id,
        )
    assert caught.value.__cause__ is None
    assert counter.executed == 1


@pytest.mark.parametrize("different_extractor", [False, True])
def test_equal_bytes_do_not_admit_a_post_pin_source(
    pinned: Prepared, tmp_path: Path, different_extractor: bool
) -> None:
    conn, run, sources, _, _ = pinned
    extractor = Reader(replace(PlainTextExtractor().identity, name="other"))
    added = _admit(
        conn,
        sources.case_id,
        tmp_path,
        cast(Extractor, extractor) if different_extractor else None,
    )
    assert (
        read.read_block(conn, source_id=added, block_id="b000000").text.value == "one"
    )
    assert conn.execute(
        "SELECT document_sha256 FROM sources WHERE source_id = %s", (added,)
    ).fetchone() == (sources.members[0].document_sha256,)
    with pytest.raises(Refusal, match=r"^EVIDENCE_NOT_AVAILABLE$"):
        read.read_run_block(conn, run_id=run, source_id=added, block_id="b000000")


@pytest.mark.parametrize(
    "field",
    ["document_sha256", "extractor_identity", "output_sha256", "extraction_sha256"],
)
def test_run_read_compares_each_captured_current_identity(
    pinned: Prepared, empty_database: str, field: str
) -> None:
    conn, run, sources, _, _ = pinned
    source = sources.members[0].source_id
    database = urlsplit(empty_database).path.removeprefix("/")
    assert database == "caos_test_" + UUID(database.removeprefix("caos_test_")).hex
    assert conn.execute("SELECT current_database()").fetchone() == (database,)
    table = "sources" if field == "document_sha256" else "source_extractions"
    with conn.transaction():
        if table == "source_extractions":
            conn.execute(
                "ALTER TABLE source_extractions DISABLE TRIGGER extraction_is_immutable"
            )
        conn.execute(
            psycopg.sql.SQL("UPDATE {} SET {} = %s WHERE source_id = %s").format(
                psycopg.sql.Identifier(table), psycopg.sql.Identifier(field)
            ),
            ("{}" if field == "extractor_identity" else "0" * 64, source),
        )
        if table == "source_extractions":
            conn.execute(
                "ALTER TABLE source_extractions ENABLE TRIGGER extraction_is_immutable"
            )
    with pytest.raises(Refusal, match=r"^EVIDENCE_NOT_AVAILABLE$"):
        read.read_run_block(conn, run_id=run, source_id=source, block_id="b000000")


@pytest.mark.parametrize("field", ["run_id", "source_id", "block_id"])
@pytest.mark.parametrize("invalid", [None, 0, "invalid"])
def test_run_read_validates_arguments_before_sql(
    pinned: Prepared, field: str, invalid: object
) -> None:
    conn, run, sources, _, _ = pinned
    args = {
        "run_id": run,
        "source_id": sources.members[0].source_id,
        "block_id": "b000000",
    }
    args[field] = invalid
    counter = _CountingConnection(conn)
    with pytest.raises(Refusal, match=r"^EVIDENCE_NOT_AVAILABLE$"):
        read.read_run_block(cast(StoreConnection, counter), **args)  # type: ignore[arg-type]
    assert counter.executed == 0


@pytest.mark.parametrize("fault", ["select", "cleanup", "pending"])
def test_run_read_owned_cleanup_never_adopts_pending_work(
    pinned: Prepared, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    conn, run, sources, _, _ = pinned
    source = sources.members[0].source_id
    execute = psycopg.Connection.execute

    def fail(c: StoreConnection, query: str, *args: object, **kwargs: object) -> object:
        if "JOIN run_inputs" in query:
            return execute(c, 'SELECT "private evidence"')
        return execute(c, query, *args, **kwargs)  # type: ignore[arg-type]

    def broken(c: StoreConnection) -> None:
        raise psycopg.OperationalError("private")

    if fault == "pending":
        conn.execute(
            "UPDATE cases SET title = 'pending caller work' WHERE case_id = %s",
            (sources.case_id,),
        )
    with monkeypatch.context() as patch:
        patch.setattr(psycopg.Connection, "execute", fail)
        if fault == "cleanup":
            patch.setattr(psycopg.Connection, "rollback", broken)
        code = (
            "STORE_NOT_TRANSACTIONAL"
            if fault == "pending"
            else "EVIDENCE_NOT_AVAILABLE"
        )
        with pytest.raises(Refusal, match=f"^{code}$") as caught:
            with execution_reads(conn):
                read.read_run_block(
                    conn, run_id=run, source_id=source, block_id="b000000"
                )
        assert caught.value.__cause__ is None
    if fault == "pending":
        assert conn.info.transaction_status is TransactionStatus.INTRANS
        assert conn.execute(
            "SELECT title FROM cases WHERE case_id = %s", (sources.case_id,)
        ).fetchone() == ("pending caller work",)
        conn.rollback()
    else:
        assert (
            conn.closed
            if fault == "cleanup"
            else conn.info.transaction_status is TransactionStatus.IDLE
        )
