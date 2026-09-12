"""Human approval binds a run's exact host-derived preview and complete input.

Historical previews grant no authority: use also checks live sources and standing.
Runtime must call under its execution-boundary locks and recheck at acceptance.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

import psycopg

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, rollback_or_close
from server.store.audit import GovernedAction, governed_write
from server.store.members import Standing, satisfies, standing_of
from server.store.routes import resolved_route
from server.store.run_inputs import load_run_input
from server.store.source_sets import load_source_set


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


@dataclass(frozen=True, slots=True)
class GatePreview:
    """Show `content` exactly; submit its digests as expectations, never authority."""

    run_id: UUID
    case_id: UUID
    gate: Gate
    content: str
    preview_sha256: str
    input_fingerprint: str


def gate_preview(conn: StoreConnection, run_id: UUID, gate: Gate) -> GatePreview:
    """Historical content, even after withdrawal; caller owns the read transaction."""
    preview = _preview(conn, run_id, gate)
    if preview is None:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    return preview


def _preview(conn: StoreConnection, run_id: UUID, gate: Gate) -> GatePreview | None:
    try:
        pin = load_run_input(conn, run_id)
        if pin is None:
            return None
        data: dict[str, object] = {
            "format_version": 1,
            "gate": gate.value,
            "input": {
                **asdict(pin),
                "run_id": str(run_id),
                "case_id": str(pin.case_id),
            },
        }
        if gate is Gate.SOURCE_SET:
            source = load_source_set(conn, pin.case_id, pin.source_version)
            if source is None:
                raise Refusal(RefusalCode.RUN_INPUT_INVALID)
            data["sources"] = [
                {**asdict(member), "source_id": str(member.source_id)}
                for member in source.members
            ]
        else:
            route = resolved_route(conn, run_id)
            if route is None:
                raise Refusal(RefusalCode.RUN_INPUT_INVALID)
            data["route"] = asdict(route)
        content = json.dumps(
            data, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2
        )
        return GatePreview(
            run_id,
            pin.case_id,
            gate,
            content,
            sha256(content.encode("utf-8")).hexdigest(),
            pin.input_fingerprint,
        )
    except psycopg.Error:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None


def _sources_live(conn: StoreConnection, run_id: UUID) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM run_inputs i JOIN source_set_members m"
            " ON (m.case_id, m.version) = (i.case_id, i.source_version)"
            " LEFT JOIN live_sources s"
            " ON (s.case_id, s.source_id) = (m.case_id, m.source_id)"
            " WHERE i.run_id = %s AND s.source_id IS NULL LIMIT 1",
            (run_id,),
        ).fetchone()
        is None
    )


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
        preview = gate_preview(connection, approval.run_id, approval.gate)
        if (approval.preview_sha256, approval.input_fingerprint) != (
            preview.preview_sha256,
            preview.input_fingerprint,
        ):
            raise Refusal(RefusalCode.GATE_APPROVAL_MISMATCH)
        if not _sources_live(connection, approval.run_id):
            raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)
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


def gate_state(conn: StoreConnection, run_id: UUID, gate: Gate) -> GateState:
    """Current eligibility in the caller's transaction; corrupt identity refuses."""
    try:
        preview = _preview(conn, run_id, gate)
        if preview is None:
            return GateState.OPEN
        row = conn.execute(
            "SELECT preview_sha256, input_fingerprint, approved_by FROM run_gates"
            " WHERE run_id = %s AND gate = %s",
            (run_id, gate.value),
        ).fetchone()
        if (
            row is None
            or row[:2] != (preview.preview_sha256, preview.input_fingerprint)
            or not _sources_live(conn, run_id)
            or not satisfies(
                standing_of(conn, case_id=preview.case_id, user_id=row[2]),
                Standing.APPROVER,
            )
        ):
            return GateState.OPEN
    except psycopg.Error:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    return GateState.RELEASED


def source_set_fingerprint(conn: StoreConnection, case_id: UUID) -> str:
    """A digest over the case's live sources.

    Compatibility only, not an enforced run pin; new snapshots use source_sets.
    Order-independent, because the order documents were admitted in is not a
    change to the evidence and must not reopen a gate. Over `live_sources`, so a
    withdrawal moves this compatibility digest. Approval uses complete pins and
    checks current withdrawal separately.
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
    bound to that captured member reopens because the member is no longer live.
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
    try:
        row = conn.execute(
            "SELECT case_id FROM runs WHERE run_id = %s", (run_id,)
        ).fetchone()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    if row is None:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    return UUID(str(row[0]))
