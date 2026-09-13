"""Cases and the runs that belong to them.

The two rows every later part of Phase 1 hangs off: a run's events are ordered
under its row lock, its attempts and charges reference it, and its terminal event
is the one `test_terminal_event_is_exactly_once` counts.

Who commits, and why it differs: `create_case` and `start_run` do not, because
they are setup and their caller may want them beside something else. The three
transitions below do, because each one *is* a unit of work in the sense the
pairing rule means (`SYSTEM_SPEC.md` section 2) -- state and its event, together
or not at all. Leaving that commit to a caller would leave the invariant to a
caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

import psycopg

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, rollback_or_close
from server.store.budget import CEILING, validate_spend
from server.store.cases import lock_case
from server.store.events import RunEvent, append, lock_run
from server.store.gates import approved_run_input
from server.store.outcomes import (
    CallOutcome,
    _attempt_owner,
    _locked_attempt,
    accepted_owner,
    record_outcome,
)


def create_case(conn: StoreConnection, title: BoundaryText) -> UUID:
    """Open a case. Its title crossed the boundary before it got here."""
    case_id = uuid4()
    conn.execute(
        "INSERT INTO cases (case_id, title) VALUES (%s, %s)",
        (case_id, title.value),
    )
    return case_id


def start_run(
    conn: StoreConnection, case_id: UUID, *, budget_ceiling: Decimal | None = None
) -> UUID:
    """Start a run against a case. RUNNING is the only state a run starts in.

    The ceiling is carried from the first row rather than attached later: a run
    that existed for even one attempt without one is invariant 8 with the number
    left out. `server.store.budget.CEILING` is what a caller that names none
    gets.
    """
    ceiling = CEILING if budget_ceiling is None else budget_ceiling
    validate_spend(ceiling)
    lock_case(conn, case_id)
    run_id = uuid4()
    conn.execute(
        "INSERT INTO runs (run_id, case_id, status, budget_ceiling)"
        " VALUES (%s, %s, %s, %s)",
        (run_id, case_id, RunStatus.RUNNING.value, ceiling),
    )
    return run_id


def run_status(conn: StoreConnection, run_id: UUID) -> RunStatus:
    """The run's status, or `RUN_NOT_FOUND` -- the same refusal an unauthorised
    run gets, so that neither answer tells a caller the other one exists."""
    row = conn.execute(
        "SELECT status FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    return RunStatus(row[0])


def start_attempt(conn: StoreConnection, run_id: UUID, route_node_id: str) -> UUID:
    """Record one try at one node, and say so in the stream.

    The row exists before the work does, because it is the identity the work is
    charged against: a crash after a provider completed still has the attempt it
    completed (`docs/DECISIONS.md` §12, adopting CAOS-Final §21 with Phase 4).
    """
    if lock_run(conn, run_id) is not RunStatus.RUNNING:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.RUN_NOT_RUNNING)
    if accepted_owner(conn, run_id, route_node_id) is not None:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.NODE_ALREADY_ACCEPTED)

    attempt_id = uuid4()
    conn.execute(
        "INSERT INTO run_attempts (attempt_id, run_id, route_node_id)"
        " VALUES (%s, %s, %s)",
        (attempt_id, run_id, route_node_id),
    )
    append(conn, run_id, RunEvent.ATTEMPT_STARTED)
    conn.commit()
    return attempt_id


@dataclass(frozen=True, slots=True)
class Accepted:
    """Analysis proposed for acceptance, beside independently durable call facts."""

    artifact_sha256: str
    charge: Decimal
    model: str
    generation_id: str
    diagnostic_sha256: str | None = None


def accept_attempt(
    conn: StoreConnection,
    *,
    attempt_id: UUID,
    accepted: Accepted,
) -> bool:
    """Commit call facts first, then independently accept eligible analysis.

    A later refusal/rollback cannot erase a committed bill. Each unit derives
    and locks current ownership; no lock or mutable status survives the gap.
    """
    try:
        inserted = _accept(conn, attempt_id, accepted)
        conn.commit()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    return inserted


def _accept(conn: StoreConnection, attempt: UUID, accepted: Accepted) -> bool:
    if not isinstance(accepted, Accepted):
        raise Refusal(RefusalCode.CALL_OUTCOME_INVALID)
    validate_spend(accepted.charge)
    try:
        record_outcome(
            conn,
            attempt_id=attempt,
            outcome=CallOutcome(
                accepted.charge,
                accepted.model,
                accepted.generation_id,
                accepted.diagnostic_sha256,
            ),
        )
    except Refusal as refusal:
        if refusal.code is not RefusalCode.CALL_OUTCOME_LEGACY:
            raise
        _legacy_replay(conn, attempt, accepted)
        return False
    return _accept_artifact(conn, attempt, accepted)


def _accept_artifact(conn: StoreConnection, attempt: UUID, accepted: Accepted) -> bool:
    run, case, status = _locked_attempt(conn, attempt)
    if (
        not isinstance(accepted.artifact_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", accepted.artifact_sha256) is None
    ):
        raise Refusal(RefusalCode.BLOB_ADDRESS_INVALID)
    values = (
        accepted.artifact_sha256,
        run,
        case,
        accepted.model,
        accepted.generation_id,
    )
    row = conn.execute(
        "SELECT artifact_sha256,run_id,case_id,model,generation_id FROM artifacts"
        " WHERE attempt_id = %s",
        (attempt,),
    ).fetchone()
    if row is not None:
        if row != values:
            raise Refusal(RefusalCode.CALL_OUTCOME_CONFLICT)
        return False
    if status is not RunStatus.RUNNING:
        return False
    # Fresh authority in this locked unit: governed writes take the case lock
    # first, so nothing can commit between this check and the insert.
    _pin, route = approved_run_input(conn, run)
    node = conn.execute(
        "SELECT route_node_id FROM run_attempts WHERE attempt_id = %s", (attempt,)
    ).fetchone()
    if node is None or node[0] not in {n.route_node_id for n in route.nodes}:
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    # One owner per node, under the run lock; the unique constraint backs it.
    if accepted_owner(conn, run, node[0]) is not None:
        raise Refusal(RefusalCode.NODE_ALREADY_ACCEPTED)
    # `route_node_id` is filled from the attempt by the migration 0009 trigger.
    conn.execute(
        "INSERT INTO artifacts (attempt_id, artifact_sha256, run_id, case_id,"
        " model, generation_id)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (attempt, *values),
    )
    append(conn, run, RunEvent.ATTEMPT_ACCEPTED)
    return True


def _legacy_replay(conn: StoreConnection, attempt: UUID, accepted: Accepted) -> None:
    run, case, _status = _locked_attempt(conn, attempt)
    row = conn.execute(
        "SELECT a.artifact_sha256,a.run_id,a.case_id,a.model,a.generation_id,"
        " l.run_id,l.amount FROM artifacts a JOIN budget_ledger l USING (attempt_id)"
        " WHERE a.attempt_id=%s",
        (attempt,),
    ).fetchone()
    if accepted.diagnostic_sha256 is not None or row != (
        accepted.artifact_sha256,
        run,
        case,
        accepted.model,
        accepted.generation_id,
        run,
        accepted.charge,
    ):
        raise Refusal(RefusalCode.CALL_OUTCOME_LEGACY)


def complete_run(conn: StoreConnection, run_id: UUID) -> bool:
    """End a run that finished its route. Returns whether this call ended it."""
    lock_run(conn, run_id)
    return _transition(conn, run_id, RunStatus.COMPLETE, RunEvent.RUN_COMPLETE)


def complete_attempt(
    conn: StoreConnection, *, attempt_id: UUID, accepted: Accepted
) -> bool:
    """Accept the attempt and end the run it belongs to.

    The single-node shape Phase 1 exits on, kept as one call because
    `test_terminal_event_is_exactly_once` is about the two committing as one
    story: a crash in the gap yields one artifact, one charge, one terminal
    event, however many times it is replayed.
    """
    accept_attempt(conn, attempt_id=attempt_id, accepted=accepted)
    return complete_run(conn, _attempt_owner(conn, attempt_id)[0])


def fail_run(conn: StoreConnection, run_id: UUID) -> bool:
    """End a run without an artifact. Returns whether this call ended it."""
    lock_run(conn, run_id)
    return _transition(conn, run_id, RunStatus.FAILED, RunEvent.RUN_FAILED)


def _transition(
    conn: StoreConnection, run_id: UUID, into: RunStatus, event: RunEvent
) -> bool:
    """Move a RUNNING run into a terminal status, appending `event` only if the
    move actually happened. Zero rows updated, no event -- the rule that makes a
    terminal event exactly-once (`SYSTEM_SPEC.md` section 2)."""
    changed = conn.execute(
        "UPDATE runs SET status = %s WHERE run_id = %s AND status = %s",
        (into.value, run_id, RunStatus.RUNNING.value),
    ).rowcount
    if changed:
        append(conn, run_id, event)
    conn.commit()
    return bool(changed)
