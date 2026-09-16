"""The case stream: what the browser is told, and when it stops being told it.

`SYSTEM_SPEC.md` §9 as brief 4.4 decisions 1-4 restate it. One stream per case
carries the case's audit actions and, for a named run, that run's events --
because withdrawal is recorded in `audit_events`, which a run tail never read.

A stream event carries a cursor and a name. Nothing else: the client never
reads payloads, and a payload would be a second copy of state the client is
about to fetch properly. The rules, each a decision rather than a detail:

*The first frame is a cursor.* It sets the browser's `lastEventId` to the
resume position and dispatches nothing.

*Resume excludes the marker.* Delivery starts strictly after it in both
sequences.

*Standing is rechecked before each frame and on each poll.* An SSE connection
is exactly the thing that stays open across a revocation, and losing standing
closes the stream rather than idling it.

*An idle stream still hands back control.* With `heartbeat`, each poll ends
in `None`, which the route writes as an SSE comment: the thread driving this
generator returns to the server every poll, so a browser that went away is
noticed within one poll rather than at the deadline.

*A delivered terminal ends the run half.* Once the run's terminal event has
been delivered, or the marker is already past it, `run_events` is never read
again for this stream -- late billing after a terminal stays durable and is not
redelivered (F16). The audit half polls on until the deadline.

The HTTP binding is `server/api/app.py`'s: this module yields, it does not
frame.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Literal, overload
from uuid import UUID

from server.api.events import STREAM_NAMES, Marker, parse_marker
from server.api.wire import EventName
from server.store import StoreConnection
from server.store.audit import actions_after
from server.store.events import RunEvent
from server.store.members import Standing, satisfies, standing_of

# Once per connection: the heads and the run's terminal position, one query.
CONNECT_IO = 1
# Per poll: the audit actions after the cursor, the run events after it (until
# the terminal is delivered), and the standing recheck. Each frame then costs
# one more recheck -- the N+1 §9 mandates, spread across the stream's life.
POLL_IO = 3
IO_BUDGET = CONNECT_IO + POLL_IO

# How many run events one poll reads; the next poll continues after the last.
RUN_PAGE = 500

# The events that end the run half of a stream.
TERMINAL = frozenset(
    {
        RunEvent.RUN_COMPLETE.value,
        RunEvent.RUN_FAILED.value,
        RunEvent.RUN_BLOCKED.value,
        RunEvent.RUN_CANCELLED.value,
    }
)

# Watching a case is reading it. Anything a stream can reveal, the section
# documents reveal to the same person.
WATCH_REQUIRES = Standing.READER


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """One frame: the position to resume from, and the name that triggers a
    refetch -- `None` for the cursor-only frame."""

    id: Marker
    name: EventName | None


@overload
def case_tail(
    conn: StoreConnection,
    *,
    case_id: UUID,
    run_id: UUID | None,
    actor_id: UUID,
    after: str | None,
    deadline: float = ...,
    poll: float = ...,
    heartbeat: Literal[False] = ...,
) -> Iterator[StreamEvent]: ...


@overload
def case_tail(
    conn: StoreConnection,
    *,
    case_id: UUID,
    run_id: UUID | None,
    actor_id: UUID,
    after: str | None,
    deadline: float = ...,
    poll: float = ...,
    heartbeat: Literal[True],
) -> Iterator[StreamEvent | None]: ...


def case_tail(  # noqa: PLR0913 -- the stream's identity, then its lifetime
    conn: StoreConnection,
    *,
    case_id: UUID,
    run_id: UUID | None,
    actor_id: UUID,
    after: str | None,
    deadline: float = 0.0,
    poll: float = 0.0,
    heartbeat: bool = False,
) -> Iterator[StreamEvent | None]:
    """The cursor frame, then named frames after `after`, polling every `poll`
    seconds until `deadline` seconds have passed or standing is lost.

    `after` is the raw `Last-Event-ID`; it is parsed against the heads read
    here. A deadline of zero is one poll. Yields nothing at all to an actor
    who cannot read the case.
    """
    started = monotonic()
    audit_head, run_head, terminal = _heads(conn, case_id, run_id)
    at = parse_marker(after, Marker(audit_head, run_head))
    run_open = run_id is not None and (terminal is None or at.run_seq < terminal)

    if not _may_watch(conn, case_id, actor_id):
        return
    yield StreamEvent(at, None)

    while True:
        for event, closes in _pending(conn, case_id, run_id if run_open else None, at):
            at = event.id
            if event.name is not None:
                if not _may_watch(conn, case_id, actor_id):
                    return
                yield event
            run_open = run_open and not closes

        if not _may_watch(conn, case_id, actor_id):
            return
        if monotonic() - started >= deadline:
            return
        sleep(poll)
        if heartbeat:
            yield None


def _pending(
    conn: StoreConnection, case_id: UUID, run_id: UUID | None, at: Marker
) -> list[tuple[StreamEvent, bool]]:
    """One poll's rows after `at`, each with its cursor and name (`None` for a
    silent row, which still advances the cursor), and whether it ends the run
    half. The run's rows stop at its terminal; `run_id` is `None` once that has
    been delivered, and the run is not read at all."""
    pending: list[tuple[StreamEvent, bool]] = []
    for seq, action in actions_after(conn, case_id=case_id, seq=at.audit_seq):
        at = Marker(seq, at.run_seq)
        pending.append((StreamEvent(at, STREAM_NAMES.get(action)), False))
    if run_id is None:
        return pending
    for seq, event in _run_events_after(conn, run_id, at.run_seq):
        at = Marker(at.audit_seq, seq)
        closes = event in TERMINAL
        pending.append((StreamEvent(at, STREAM_NAMES.get(event)), closes))
        if closes:
            break
    return pending


def _may_watch(conn: StoreConnection, case_id: UUID, actor_id: UUID) -> bool:
    return satisfies(
        standing_of(conn, case_id=case_id, user_id=actor_id), WATCH_REQUIRES
    )


def _heads(
    conn: StoreConnection, case_id: UUID, run_id: UUID | None
) -> tuple[int, int, int | None]:
    """The case's audit head, the run's event head, and the run's first
    terminal position -- aggregates only, never the tail's rows."""
    row = conn.execute(
        "SELECT"
        " (SELECT coalesce(max(seq), 0) FROM audit_events WHERE case_id = %s),"
        " (SELECT coalesce(max(seq), 0) FROM run_events WHERE run_id = %s),"
        " (SELECT min(seq) FROM run_events WHERE run_id = %s AND name = ANY(%s))",
        (case_id, run_id, run_id, sorted(TERMINAL)),
    ).fetchone()
    if row is None:  # pragma: no cover -- a scalar SELECT always returns a row
        return 0, 0, None
    return int(row[0]), int(row[1]), None if row[2] is None else int(row[2])


def _run_events_after(
    conn: StoreConnection, run_id: UUID, seq: int
) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT seq, name FROM run_events WHERE run_id = %s AND seq > %s"
        " ORDER BY seq LIMIT %s",
        (run_id, seq, RUN_PAGE),
    ).fetchall()
    return [(int(row[0]), str(row[1])) for row in rows]
