"""Cases and the runs that belong to them.

The two rows every later part of Phase 1 hangs off: a run's events are ordered
under its row lock, its attempts and charges reference it, and its terminal event
is the one `test_terminal_event_is_exactly_once` counts.

Nothing here commits. The caller owns the transaction, because the pairing rule
(`SYSTEM_SPEC.md` section 2) is that state and its event commit together -- a
function that committed on its own behalf would make that impossible to honour.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection


def create_case(conn: StoreConnection, title: BoundaryText) -> UUID:
    """Open a case. Its title crossed the boundary before it got here."""
    case_id = uuid4()
    conn.execute(
        "INSERT INTO cases (case_id, title) VALUES (%s, %s)",
        (case_id, title.value),
    )
    return case_id


def start_run(conn: StoreConnection, case_id: UUID) -> UUID:
    """Start a run against a case. RUNNING is the only state a run starts in."""
    run_id = uuid4()
    conn.execute(
        "INSERT INTO runs (run_id, case_id, status) VALUES (%s, %s, %s)",
        (run_id, case_id, RunStatus.RUNNING.value),
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
