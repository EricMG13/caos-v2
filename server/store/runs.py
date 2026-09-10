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

from decimal import Decimal
from uuid import UUID, uuid4

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.budget import CEILING
from server.store.events import RunEvent, append, lock_run


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
    if not isinstance(ceiling, Decimal):
        raise Refusal(RefusalCode.MONEY_NOT_DECIMAL)
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
        raise Refusal(RefusalCode.RUN_NOT_RUNNING)

    attempt_id = uuid4()
    conn.execute(
        "INSERT INTO run_attempts (attempt_id, run_id, route_node_id)"
        " VALUES (%s, %s, %s)",
        (attempt_id, run_id, route_node_id),
    )
    append(conn, run_id, RunEvent.ATTEMPT_STARTED)
    conn.commit()
    return attempt_id


def complete_attempt(
    conn: StoreConnection,
    *,
    attempt_id: UUID,
    artifact_sha256: str,
    charge: Decimal,
) -> bool:
    """Accept an attempt's artifact, charge it, and complete the run it belongs
    to. Returns whether this call was the one that completed the run.

    Which run and which case are read from the attempt rather than taken from
    the caller. The store already knows, and a caller that can name them can
    name the wrong ones -- charging one run's ledger for another run's work
    (invariant 3: the host owns identity).

    Everything here is written to survive being called twice with the same
    arguments, because a caller that crashed after the commit cannot tell that
    it committed. The artifact and the charge are keyed by `attempt_id` and land
    with `ON CONFLICT DO NOTHING`; the run's transition is a conditional update,
    and its zero rows are what suppress a second terminal event.

    A run that has already ended accepts nothing further -- not the artifact and
    not the charge. Writing them anyway would leave a failed run holding an
    accepted artifact, and Phase 3 recomputes node states from exactly those.
    """
    if not isinstance(charge, Decimal):
        # Before any write: a float that reached the ledger would already have
        # lost the cent it cannot represent (invariant 7).
        raise Refusal(RefusalCode.MONEY_NOT_DECIMAL)

    run_id, case_id = _attempt_owner(conn, attempt_id)
    if lock_run(conn, run_id) is not RunStatus.RUNNING:
        conn.commit()  # nothing changed; release the row lock rather than hold it
        return False

    conn.execute(
        "INSERT INTO artifacts (attempt_id, artifact_sha256, run_id, case_id)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (attempt_id) DO NOTHING",
        (attempt_id, artifact_sha256, run_id, case_id),
    )
    conn.execute(
        "INSERT INTO budget_ledger (attempt_id, run_id, amount)"
        " VALUES (%s, %s, %s) ON CONFLICT (attempt_id) DO NOTHING",
        (attempt_id, run_id, charge),
    )
    return _transition(conn, run_id, RunStatus.COMPLETE, RunEvent.RUN_COMPLETE)


def fail_run(conn: StoreConnection, run_id: UUID) -> bool:
    """End a run without an artifact. Returns whether this call ended it."""
    lock_run(conn, run_id)
    return _transition(conn, run_id, RunStatus.FAILED, RunEvent.RUN_FAILED)


def _attempt_owner(conn: StoreConnection, attempt_id: UUID) -> tuple[UUID, UUID]:
    """The run and case an attempt belongs to, or `ATTEMPT_NOT_FOUND`.

    Safe to read before the run row lock is taken: `run_attempts` is append-only,
    so an attempt's owner is fixed the moment the row exists.
    """
    row = conn.execute(
        "SELECT attempts.run_id, runs.case_id"
        " FROM run_attempts AS attempts"
        " JOIN runs USING (run_id)"
        " WHERE attempts.attempt_id = %s",
        (attempt_id,),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    return UUID(str(row[0])), UUID(str(row[1]))


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
