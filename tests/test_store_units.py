"""Store entry points that share a caller's transaction (Task 4.2c).

A command commits its state, its audit event and its idempotency receipt as one
unit, so every write it composes needs a form that neither commits nor rolls
back. The committing functions stay, as thin wrappers over these.
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
from server.store import StoreConnection
from server.store.audit import audit_trail
from server.store.gates import (
    Gate,
    GateState,
    approve_gate,
    gate_state,
    release_gate_in,
)
from server.store.routes import pin_route, pin_route_in
from server.store.run_inputs import RunSubject, pin_run_input_in
from server.store.runs import fail_run, start_run
from server.store.source_sets import snapshot_in, snapshot_source_set

__all__ = ["gated"]  # the fixture is used by name

TEXT = b"Total debt at 31 December 2026 was USD 1,240.0m\n"


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
