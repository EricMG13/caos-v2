"""Phase 6: a human gate binds the exact content that was reviewed.

Invariant 5 (CLAUDE.md): approval binds the exact reviewed content -- the preview
digest plus the input fingerprint. Not the run, not the moment, the *content*.

The consequence is the interesting part, and it is why this file's two named
tests sit together. If an approval is bound to a fingerprint over the live source
set, then withdrawing a source changes the fingerprint, and the gate is open
again -- not because anything went looking for approvals to invalidate, but
because the thing that was approved is no longer what is there.

`docs/REBUILD_PLAN.md` names both:
`test_approval_binds_the_exact_reviewed_content` (Phase 6's exit) and
`test_a_withdrawn_source_refuses_the_read_and_reopens_the_gate` (the Phase 2 debt
Phase 6 owes, the second half of invariant 1).
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.ingest import Document, admit_pack
from server.evidence.read import read_evidence
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import audit_trail
from server.store.gates import (
    Gate,
    GateApproval,
    GateState,
    approve_gate,
    gate_state,
    source_set_fingerprint,
    withdraw_source,
)
from server.store.members import Standing, grant
from server.store.runs import start_run

PREVIEW = "a" * 64


@pytest.fixture
def gated(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> tuple[StoreConnection, UUID, UUID, UUID, UUID]:
    """A case with one source, a run on it, and an APPROVER."""
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    [source_id] = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[
            Document(
                filename=BoundaryText.of("report.txt"),
                data=b"Total debt at 31 December 2026 was USD 1,240.0m\n",
            )
        ],
    )
    run_id = start_run(conn, case_id)
    approver = uuid4()
    grant(conn, case_id=case_id, user_id=approver, standing=Standing.APPROVER)
    conn.commit()
    return conn, case_id, run_id, source_id, approver


def _approval(
    run_id: UUID, approver: UUID, fingerprint: str, preview: str = PREVIEW
) -> GateApproval:
    return GateApproval(
        run_id=run_id,
        gate=Gate.SOURCE_SET,
        actor_id=approver,
        preview_sha256=preview,
        input_fingerprint=fingerprint,
    )


def test_a_gate_starts_open(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    conn, case_id, run_id, _source_id, _approver = gated
    fingerprint = source_set_fingerprint(conn, case_id)

    assert gate_state(conn, run_id, Gate.SOURCE_SET, fingerprint) is GateState.OPEN


def test_an_approval_releases_the_gate_it_was_given_for(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    conn, case_id, run_id, _source_id, approver = gated
    fingerprint = source_set_fingerprint(conn, case_id)

    approve_gate(conn, _approval(run_id, approver, fingerprint))

    assert gate_state(conn, run_id, Gate.SOURCE_SET, fingerprint) is GateState.RELEASED


def test_approval_binds_the_exact_reviewed_content(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID], tmp_path: Path
) -> None:
    """The Phase 6 exit test.

    An approval carries the fingerprint of what the approver was shown. Once the
    content moves, that approval releases nothing -- it is an answer to a
    question nobody is asking any more.
    """
    conn, case_id, run_id, _source_id, approver = gated
    reviewed = source_set_fingerprint(conn, case_id)
    approve_gate(conn, _approval(run_id, approver, reviewed))
    assert gate_state(conn, run_id, Gate.SOURCE_SET, reviewed) is GateState.RELEASED

    # A second document is admitted. The set the approver looked at is not the
    # set the run would execute against.
    admit_pack(
        conn,
        BlobStore(tmp_path / "more"),
        case_id=case_id,
        documents=[
            Document(
                filename=BoundaryText.of("memo.txt"),
                data=b"Leverage is 3.4x on a net basis\n",
            )
        ],
    )
    conn.commit()
    moved = source_set_fingerprint(conn, case_id)

    assert moved != reviewed
    assert gate_state(conn, run_id, Gate.SOURCE_SET, moved) is GateState.OPEN


def test_a_withdrawn_source_refuses_the_read_and_reopens_the_gate(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    """The Phase 2 debt Phase 6 owes, and the second half of invariant 1.

    Both halves in one test because they are one fact: the source is gone, so
    reading it refuses and the approval that covered it no longer covers
    anything. Nothing goes looking for approvals to invalidate -- the gate
    reopens because the fingerprint moved.
    """
    conn, case_id, run_id, source_id, approver = gated
    row = conn.execute(
        "SELECT block_id FROM source_blocks WHERE source_id = %s", (source_id,)
    ).fetchone()
    assert row is not None
    block_id = str(row[0])
    reviewed = source_set_fingerprint(conn, case_id)
    approve_gate(conn, _approval(run_id, approver, reviewed))
    assert read_evidence(conn, source_id=source_id, block_id=block_id)
    assert gate_state(conn, run_id, Gate.SOURCE_SET, reviewed) is GateState.RELEASED

    withdraw_source(conn, case_id=case_id, source_id=source_id, actor_id=approver)

    with pytest.raises(Refusal) as caught:
        read_evidence(conn, source_id=source_id, block_id=block_id)
    assert caught.value.code is RefusalCode.EVIDENCE_NOT_AVAILABLE

    now = source_set_fingerprint(conn, case_id)
    assert now != reviewed
    assert gate_state(conn, run_id, Gate.SOURCE_SET, now) is GateState.OPEN


def test_withdrawal_is_a_governed_write(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    """It removes evidence a conclusion may already rest on, so it is recorded
    and it is refused to someone who may not do it."""
    conn, case_id, _run_id, source_id, _approver = gated
    stranger = uuid4()

    with pytest.raises(Refusal) as caught:
        withdraw_source(conn, case_id=case_id, source_id=source_id, actor_id=stranger)

    assert caught.value.code is RefusalCode.NOT_AUTHORISED
    assert source_set_fingerprint(conn, case_id)


def test_withdrawing_what_is_not_live_here_is_refused_and_recorded_nowhere(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID], tmp_path: Path
) -> None:
    """The audit chain records decisions that happened.

    A second withdrawal, another case's source and an id that names nothing all
    changed no row -- and each wrote SOURCE_WITHDRAWN into this case's chain, so
    the chain claimed four withdrawals where there had been one.
    """
    conn, case_id, _run_id, source_id, approver = gated
    other = conn.execute(
        "INSERT INTO cases (case_id, title) VALUES (%s, %s) RETURNING case_id",
        (uuid4(), "another issuer"),
    ).fetchone()
    assert other is not None
    [foreign] = admit_pack(
        conn,
        BlobStore(tmp_path / "other"),
        case_id=other[0],
        documents=[Document(filename=BoundaryText.of("b.txt"), data=b"Beta line\n")],
    )
    conn.commit()
    withdraw_source(conn, case_id=case_id, source_id=source_id, actor_id=approver)

    for target in (source_id, foreign, uuid4()):
        with pytest.raises(Refusal) as caught:
            withdraw_source(conn, case_id=case_id, source_id=target, actor_id=approver)
        assert caught.value.code is RefusalCode.EVIDENCE_NOT_AVAILABLE

    actions = [entry.action for entry in audit_trail(conn, case_id)]
    assert actions.count("SOURCE_WITHDRAWN") == 1


def test_a_reader_cannot_release_a_gate(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    conn, case_id, run_id, _source_id, _approver = gated
    reader = uuid4()
    grant(conn, case_id=case_id, user_id=reader, standing=Standing.READER)
    conn.commit()
    fingerprint = source_set_fingerprint(conn, case_id)

    with pytest.raises(Refusal) as caught:
        approve_gate(conn, _approval(run_id, reader, fingerprint))

    assert caught.value.code is RefusalCode.NOT_AUTHORISED
    assert gate_state(conn, run_id, Gate.SOURCE_SET, fingerprint) is GateState.OPEN


def test_approving_twice_keeps_the_later_approval(
    gated: tuple[StoreConnection, UUID, UUID, UUID, UUID],
) -> None:
    """A gate re-opened by moved content is approved again, against the content
    that is there now. The row is the current answer, not a history -- the
    history is the audit chain."""
    conn, case_id, run_id, _source_id, approver = gated
    first = source_set_fingerprint(conn, case_id)
    approve_gate(conn, _approval(run_id, approver, first))

    approve_gate(conn, _approval(run_id, approver, first, preview="b" * 64))

    assert gate_state(conn, run_id, Gate.SOURCE_SET, first) is GateState.RELEASED


def test_the_fingerprint_ignores_the_order_sources_arrived_in(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    """Two cases holding the same documents fingerprint the same. Otherwise the
    gate would reopen for a reason that is not a change to the evidence."""
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    first = Document(filename=BoundaryText.of("a.txt"), data=b"Alpha line\n")
    second = Document(filename=BoundaryText.of("b.txt"), data=b"Beta line\n")

    admit_pack(conn, blobs, case_id=case_id, documents=[first, second])
    one_way = source_set_fingerprint(conn, case_id)

    created = conn.execute(
        "INSERT INTO cases (case_id, title) VALUES (%s, %s) RETURNING case_id",
        (uuid4(), "same documents, other order"),
    ).fetchone()
    assert created is not None
    other = created[0]
    admit_pack(conn, blobs, case_id=other, documents=[second, first])

    assert source_set_fingerprint(conn, other) == one_way
