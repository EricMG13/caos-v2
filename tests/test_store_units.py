"""Store entry points that share a caller's transaction (Task 4.2c).

A command commits its state, its audit event and its idempotency receipt as one
unit, so every write it composes needs a form that neither commits nor rolls
back. The committing functions stay, as thin wrappers over these.

The committing wrappers themselves (audit remediation Task 10): eleven of them
owned their transaction with the same eight lines -- commit on success, roll
back or close on a store fault and answer it `STORE_UNAVAILABLE` with no driver
text, roll back or close on anything else and let it through. `committed_unit`
is those lines, beside `rollback_or_close`, and the last test here is what
keeps a twelfth copy from growing back.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from psycopg.pq import TransactionStatus
from test_gates import _approval, gated
from test_route_pinning import CATALOG_PATH, PROFILE

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import resolve_route
from server.evidence import ingest
from server.evidence.extract import DEFAULT_LIMITS, AdmissionLimits
from server.evidence.ingest import (
    Document,
    PreparedPack,
    admit_pack,
    admit_prepared,
    prepare_pack,
)
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, apply_schema, committed_unit, connect
from server.store.audit import audit_trail
from server.store.gates import (
    Gate,
    GateState,
    approve_gate,
    gate_state,
    release_gate_in,
)
from server.store.outcomes import _require_attempt
from server.store.routes import pin_route, pin_route_in
from server.store.run_inputs import RunSubject, pin_run_input_in
from server.store.runs import fail_run, start_attempt, start_run
from server.store.source_sets import snapshot_in, snapshot_source_set
from server.store.work import require_running

__all__ = ["gated"]  # the fixture is used by name

TEXT = b"Total debt at 31 December 2026 was USD 1,240.0m\n"
STORE = Path(__file__).resolve().parents[1] / "server" / "store"
# The commit block exactly: `execution_reads` ends in a rollback and
# `apply_schema` refuses under its own code, so neither is this shape.
COMMIT_BLOCK = (
    "        conn.commit()\n"
    "    except psycopg.Error:\n"
    "        rollback_or_close(conn)\n"
    "        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None"
)


def _count(conn: StoreConnection, table: str) -> int:
    # `table` is a literal from this module, never caller input.
    row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])


def _documents(*data: bytes) -> list[Document]:
    return [
        Document(BoundaryText.of(f"doc-{i}.txt"), one) for i, one in enumerate(data)
    ]


def test_the_in_transaction_pins_do_not_commit(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    conn, case_id = case
    admit_pack(conn, BlobStore(tmp_path), case_id=case_id, documents=_documents(TEXT))
    run_id = start_run(conn, case_id)
    conn.commit()

    snapshot_in(conn, case_id)
    assert conn.info.transaction_status is TransactionStatus.INTRANS
    conn.rollback()
    assert _count(conn, "source_set_versions") == 0

    source = snapshot_source_set(conn, case_id)
    route = resolve_route(
        json.loads(CATALOG_PATH.read_text()), PROFILE, "DEEP_RESEARCH"
    )
    events = _count(conn, "run_events")
    conn.commit()
    pin_route_in(conn, run_id, route)
    assert conn.info.transaction_status is TransactionStatus.INTRANS
    conn.rollback()
    assert (_count(conn, "run_routes"), _count(conn, "run_events")) == (0, events)

    pin_route(conn, run_id, route)
    events = _count(conn, "run_events")
    conn.commit()
    pin_run_input_in(
        conn,
        run_id,
        source.version,
        Bundle(CATALOG_PATH.parents[3]),
        subject=RunSubject("EXAMPLE", "Example Holdings plc", "FY2025", "2026-09-08"),
    )
    assert conn.info.transaction_status is TransactionStatus.INTRANS
    conn.rollback()
    assert (_count(conn, "run_inputs"), _count(conn, "run_events")) == (0, events)


def test_approval_on_a_terminal_run_is_refused(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    conn, case_id, run_id, _source_id, approver = gated
    approval = _approval(conn, run_id, approver)
    conn.commit()
    assert fail_run(conn, run_id)

    with pytest.raises(Refusal, match=r"^RUN_NOT_RUNNING$"):
        approve_gate(conn, approval)

    assert conn.info.transaction_status is TransactionStatus.IDLE
    with pytest.raises(Refusal, match=r"^RUN_NOT_RUNNING$"):
        release_gate_in(conn, approval)
    conn.rollback()
    assert audit_trail(conn, case_id) == []
    assert _count(conn, "run_gates") == 0
    assert gate_state(conn, run_id, Gate.SOURCE_SET) is GateState.OPEN


def test_prepare_pack_touches_no_store(
    case: tuple[StoreConnection, UUID],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, case_id = case
    blobs = BlobStore(tmp_path)
    one_document = replace(DEFAULT_LIMITS, max_documents=1)
    offered: list[tuple[list[Document], AdmissionLimits]] = [
        ([], DEFAULT_LIMITS),
        (_documents(TEXT, TEXT), one_document),
        (_documents(b"\xff\xfe\x00 not text at all"), DEFAULT_LIMITS),
        (_documents(b"   \n\n  \n"), DEFAULT_LIMITS),
    ]
    expected = []
    for documents, limits in offered:
        with pytest.raises(Refusal) as caught:
            admit_pack(conn, blobs, case_id=case_id, documents=documents, limits=limits)
        expected.append(caught.value.code)
        conn.rollback()

    def no_store(*_args: object, **_kwargs: object) -> None:
        pytest.fail("prepare_pack reached the store")

    monkeypatch.setattr(ingest, "lock_case", no_store)
    monkeypatch.setattr(ingest, "_require_case", no_store)
    refused = []
    for documents, limits in offered:
        with pytest.raises(Refusal) as caught:
            prepare_pack(documents, limits=limits)
        refused.append(caught.value.code)
    assert (
        refused
        == expected
        == [
            RefusalCode.SOURCE_PACK_EMPTY,
            RefusalCode.SOURCE_TOO_LARGE,
            RefusalCode.SOURCE_NOT_READABLE,
            RefusalCode.SOURCE_HAS_NO_TEXT,
        ]
    )
    pack = prepare_pack(_documents(TEXT, b"Memo\n"))
    assert isinstance(pack, PreparedPack)
    assert len(pack.documents) == 2


def test_admit_prepared_is_whole_or_nothing_without_commit(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    conn, case_id = case
    pack = prepare_pack(_documents(TEXT, b"Credit memo\n"))

    admitted = admit_prepared(conn, BlobStore(tmp_path), case_id, pack)
    assert len(admitted) == 2
    assert conn.info.transaction_status is TransactionStatus.INTRANS
    conn.rollback()
    assert _count(conn, "sources") == 0

    class Failing(BlobStore):
        calls = 0

        def put(self, data: bytes) -> str:
            Failing.calls += 1
            if Failing.calls == 2:
                raise Refusal(RefusalCode.STORE_UNAVAILABLE)
            return super().put(data)

    with pytest.raises(Refusal, match=r"^STORE_UNAVAILABLE$"):
        admit_prepared(conn, Failing(tmp_path), case_id, pack)
    conn.rollback()
    assert (_count(conn, "sources"), _count(conn, "source_tokens")) == (0, 0)

    with pytest.raises(Refusal, match=r"^CASE_NOT_FOUND$"):
        admit_prepared(conn, BlobStore(tmp_path), uuid4(), pack)
    conn.rollback()
    assert _count(conn, "sources") == 0


def test_committed_unit_commits_once_and_hides_the_driver_message(
    empty_database: str,
) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        with committed_unit(conn):
            conn.execute("SELECT 1")
        assert conn.info.transaction_status is TransactionStatus.IDLE
        with pytest.raises(Refusal) as refused, committed_unit(conn):
            conn.execute("SELECT * FROM no_such_table")
        assert refused.value.code is RefusalCode.STORE_UNAVAILABLE
        assert refused.value.__cause__ is None
        assert refused.value.__suppress_context__
        # The aborted transaction was rolled back, so the next caller can go on.
        assert conn.info.transaction_status is TransactionStatus.IDLE
        assert conn.execute("SELECT 1").fetchone() == (1,)


def test_committed_unit_rolls_back_and_lets_any_other_failure_through(
    empty_database: str,
) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        with pytest.raises(KeyboardInterrupt), committed_unit(conn):
            conn.execute("SELECT 1")
            raise KeyboardInterrupt
        assert conn.info.transaction_status is TransactionStatus.IDLE
        refusal = Refusal(RefusalCode.RUN_NOT_FOUND)
        with pytest.raises(Refusal) as refused, committed_unit(conn):
            raise refusal
        assert refused.value is refusal


def test_no_store_module_spells_the_commit_block_by_hand() -> None:
    offenders = sorted(
        path.name
        for path in STORE.glob("*.py")
        if path.name != "__init__.py"
        and COMMIT_BLOCK in path.read_text(encoding="utf-8")
    )
    assert offenders == [], offenders


def test_the_spend_fence_refuses_an_ended_run_before_it_asks_for_a_lease(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    conn, _case_id, run_id, _source_id, _approver = gated
    # RUNNING and never enqueued: the direct caller passes the fence.
    require_running(conn, run_id, None)
    conn.rollback()
    assert fail_run(conn, run_id)
    with pytest.raises(Refusal, match=r"^RUN_NOT_RUNNING$"):
        require_running(conn, run_id, None)
    conn.rollback()
    with pytest.raises(Refusal, match=r"^RUN_NOT_FOUND$"):
        require_running(conn, uuid4(), None)
    conn.rollback()


def test_an_attempt_is_revalidated_under_the_run_it_was_started_for(
    case: tuple[StoreConnection, UUID],
) -> None:
    conn, case_id = case
    own = start_run(conn, case_id)
    other = start_run(conn, case_id)
    conn.commit()
    attempt_id = start_attempt(conn, own, "CP-0")
    _require_attempt(conn, attempt_id, own)
    with pytest.raises(Refusal, match=r"^ATTEMPT_NOT_FOUND$"):
        _require_attempt(conn, attempt_id, other)
    conn.rollback()
    with pytest.raises(Refusal, match=r"^ATTEMPT_NOT_FOUND$"):
        _require_attempt(conn, uuid4(), own)
    conn.rollback()
