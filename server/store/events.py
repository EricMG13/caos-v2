"""The run's event stream: append-only, numbered per run, ordered by a row lock.

`SYSTEM_SPEC.md` section 2: `run_events.seq` is per-run monotonic, allocated
under the run row lock, and no event is inserted without the transition it
records. The second half is enforced by the callers in `runs.py`, which append
only on a conditional update that changed a row. The first half is enforced
here: `append` takes the lock itself rather than trusting its caller to have
taken it, because "allocated under the run row lock" is not a comment.

The stream is what the browser tails (`SYSTEM_SPEC.md` section 9) and the client
never reads an event's payload -- a name triggers a refetch. So an event carries
a name and a position, and nothing a document produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection


class RunEvent(StrEnum):
    """Every event a run can carry. The `run_events_name_is_known` CHECK holds
    the same set; `test_every_run_event_is_one_the_database_accepts` keeps them
    from becoming two."""

    ROUTE_PINNED = "ROUTE_PINNED"
    ATTEMPT_STARTED = "ATTEMPT_STARTED"
    RUN_COMPLETE = "RUN_COMPLETE"
    RUN_FAILED = "RUN_FAILED"


@dataclass(frozen=True, slots=True)
class Event:
    """One position in one run's stream."""

    seq: int
    name: str
    at: datetime


def lock_run(conn: StoreConnection, run_id: UUID) -> RunStatus:
    """Take the run row lock and return the status held under it.

    Every ordering guarantee in this module is this lock. Re-taking it inside one
    transaction is free, so callers that already hold it lose nothing by the
    functions below taking it again.

    The status comes back from the same statement rather than a second `SELECT`:
    a caller that locks in order to decide on the status would otherwise pay two
    round trips for one answer, and excessive I/O is the largest measured
    multiple in `docs/AI_CODE_QUALITY.md` section 1.
    """
    row = conn.execute(
        "SELECT status FROM runs WHERE run_id = %s FOR UPDATE", (run_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    return RunStatus(row[0])


def append(conn: StoreConnection, run_id: UUID, event: RunEvent) -> None:
    """Append `event` to the run's stream.

    Never call this except beside the transition it records, in that
    transition's transaction.

    The position is allocated by the same statement that takes it. Reading
    `max(seq)` and inserting it back separately is two round trips, and the
    caller would have to be trusted to keep them in one transaction for the
    lock above to mean anything.
    """
    lock_run(conn, run_id)
    conn.execute(
        "INSERT INTO run_events (run_id, seq, name)"
        " SELECT %s::uuid, coalesce(max(seq), 0) + 1, %s::text"
        " FROM run_events WHERE run_id = %s",
        (run_id, event.value, run_id),
    )


def events_of(conn: StoreConnection, run_id: UUID) -> list[Event]:
    """The run's stream in order. The order is the `seq`, never the clock: two
    events can share a timestamp and never share a position."""
    rows = conn.execute(
        "SELECT seq, name, at FROM run_events WHERE run_id = %s ORDER BY seq",
        (run_id,),
    ).fetchall()
    return [Event(seq=int(seq), name=name, at=at) for seq, name, at in rows]
