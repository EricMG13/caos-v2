"""Human gates, bound to the content that was reviewed.

Invariant 5: approval binds the exact reviewed content -- the preview digest plus
the input fingerprint. Not the run, and not the moment.

That choice does the work of a whole invalidation mechanism. An approval stores
the fingerprint of what the approver was shown; `gate_state` compares it with the
fingerprint of what is there *now*. So a gate reopens when the content moves, and
nothing has to go looking for approvals to cancel -- there is no list to keep
correct, and no way for a withdrawal to be applied to the sources and forgotten
at the gate.

`withdraw_source` is the other half of invariant 1. It removes evidence a
conclusion may already rest on, so it is a governed write: recorded in the chain,
refused to someone who may not do it, and never a delete. The source keeps its
row and leaves `live_sources`, which is what makes every later read refuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import GovernedAction, governed_write
from server.store.members import Standing


class Gate(StrEnum):
    """The digest-bound interrupts a run can wait on."""

    SOURCE_SET = "SOURCE_SET"
    RESEARCH_PLAN = "RESEARCH_PLAN"


class GateState(StrEnum):
    """Whether the run may pass, judged against the content that is there now."""

    OPEN = "OPEN"
    RELEASED = "RELEASED"


@dataclass(frozen=True, slots=True)
class GateApproval:
    """One person releasing one gate, over content they can be shown to have
    seen. `preview_sha256` is what they read; `input_fingerprint` is what it was
    computed from."""

    run_id: UUID
    gate: Gate
    actor_id: UUID
    preview_sha256: str
    input_fingerprint: str


def approve_gate(conn: StoreConnection, approval: GateApproval) -> None:
    """Release a gate, as a governed write requiring APPROVER standing.

    Through `governed_write` rather than beside it: releasing a gate is a human
    decision that a conclusion later rests on, so it is checked at the commit and
    recorded in the case's chain (`SYSTEM_SPEC.md` §8).
    """
    case_id = _case_of(conn, approval.run_id)
    action = GovernedAction(
        case_id=case_id,
        actor_id=approval.actor_id,
        action=f"GATE_RELEASED:{approval.gate.value}",
        requires=Standing.APPROVER,
        payload={
            "run_id": str(approval.run_id),
            "gate": approval.gate.value,
            "preview_sha256": approval.preview_sha256,
            "input_fingerprint": approval.input_fingerprint,
        },
    )

    def write(connection: StoreConnection) -> None:
        connection.execute(
            "INSERT INTO run_gates (run_id, gate, preview_sha256, input_fingerprint,"
            " approved_by) VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (run_id, gate) DO UPDATE SET"
            " preview_sha256 = EXCLUDED.preview_sha256,"
            " input_fingerprint = EXCLUDED.input_fingerprint,"
            " approved_by = EXCLUDED.approved_by, approved_at = now()",
            (
                approval.run_id,
                approval.gate.value,
                approval.preview_sha256,
                approval.input_fingerprint,
                approval.actor_id,
            ),
        )

    governed_write(conn, action, write)


def gate_state(
    conn: StoreConnection, run_id: UUID, gate: Gate, current_fingerprint: str
) -> GateState:
    """Whether the gate is released *for the content that is there now*.

    An approval whose fingerprint no longer matches releases nothing. It is an
    answer to a question nobody is asking any more, and treating it as current
    is how a run executes against a set its approver never saw.
    """
    row = conn.execute(
        "SELECT input_fingerprint FROM run_gates WHERE run_id = %s AND gate = %s",
        (run_id, gate.value),
    ).fetchone()
    if row is None or str(row[0]) != current_fingerprint:
        return GateState.OPEN
    return GateState.RELEASED


def source_set_fingerprint(conn: StoreConnection, case_id: UUID) -> str:
    """A digest over the case's live sources.

    Order-independent, because the order documents were admitted in is not a
    change to the evidence and must not reopen a gate. Over `live_sources`, so a
    withdrawal moves it -- which is the whole mechanism by which withdrawal
    reopens a gate.
    """
    rows = conn.execute(
        "SELECT document_sha256 FROM live_sources WHERE case_id = %s"
        " ORDER BY document_sha256",
        (case_id,),
    ).fetchall()
    digest = sha256()
    for row in rows:
        digest.update(str(row[0]).encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()


def withdraw_source(
    conn: StoreConnection, *, case_id: UUID, source_id: UUID, actor_id: UUID
) -> None:
    """Withdraw a source. Invariant 1's second half.

    Never a delete: a run that already cited this document has to stay
    explicable, so the row keeps its place and leaves `live_sources`. Every later
    `read_evidence` refuses because it reads through that view, and every gate
    bound to the old fingerprint reopens because the fingerprint moved.
    """
    action = GovernedAction(
        case_id=case_id,
        actor_id=actor_id,
        action="SOURCE_WITHDRAWN",
        requires=Standing.WRITER,
        payload={"source_id": str(source_id)},
    )

    def write(connection: StoreConnection) -> None:
        withdrawn = connection.execute(
            "UPDATE sources SET withdrawn_at = now()"
            " WHERE source_id = %s AND case_id = %s AND withdrawn_at IS NULL",
            (source_id, case_id),
        ).rowcount
        if not withdrawn:
            # Already withdrawn, another case's, or no source at all: nothing
            # was withdrawn, so the chain must not say something was. One code
            # for the three, as `read_evidence` gives one -- the difference
            # between them is not this caller's to learn from a refusal.
            raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)

    governed_write(conn, action, write)


def _case_of(conn: StoreConnection, run_id: UUID) -> UUID:
    row = conn.execute(
        "SELECT case_id FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    return UUID(str(row[0]))
