"""The run tail: what the browser is told, and when it stops being told it.

`SYSTEM_SPEC.md` §9. Progress reaches the browser as SSE over `run_events` with
`Last-Event-ID` resume, membership is rechecked before each event, and the stream
closes once a terminal run is fully delivered.

A stream event carries an id and a name. Nothing else, because the client never
reads payloads -- a name triggers a refetch of the section that changed. A
payload on the wire would be a second copy of state the client is about to fetch
properly, and the first thing to go stale.

Three rules, each of which is a decision rather than an implementation detail:

*Resume excludes the marker.* `Last-Event-ID` is the last event the client
actually received, so delivery starts strictly after it. Re-delivering it would
make a client that refetches on every name do the work twice, and would close a
stream that had already closed.

*Membership is rechecked before each event, not at the handshake.* An SSE
connection is exactly the thing that stays open across a revocation.

*A terminal event ends this tail.* Late billing events remain durable and can
be read by explicitly resuming after the terminal marker.

The HTTP binding is not here. `text/event-stream` over a socket is transport, and
every rule above is answerable without one; the framework arrives with the route
that serves it (CLAUDE.md known gaps).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from time import monotonic, sleep
from uuid import UUID

from server.api.events import STREAM_NAMES, Marker, parse_marker
from server.api.wire import EventName
from server.store import StoreConnection
from server.store.audit import actions_after
from server.store.events import RunEvent
from server.store.members import Standing, satisfies, standing_of

# Two fixed round trips -- the run's case, then the events after the marker --
# and then one standing recheck per event delivered.
#
# That per-event term is an N+1, and it stays. `SYSTEM_SPEC.md` section 9
# requires the recheck *before each event*, and hoisting it out of the loop is
# precisely what test_membership_is_rechecked_before_each_event refuses. It is
# also cheap where it matters: a live tail delivers events as they happen, so the
# checks are spread across the life of the stream rather than paid in a burst.
IO_BUDGET = 2

# The events that close this analytical-progress stream.
TERMINAL = frozenset(
    {
        RunEvent.RUN_COMPLETE.value,
        RunEvent.RUN_FAILED.value,
        RunEvent.RUN_BLOCKED.value,
        RunEvent.RUN_CANCELLED.value,
    }
)

# Watching a run is reading it. Anything a stream can reveal, the run document
# reveals to the same person.
WATCH_REQUIRES = Standing.READER


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """One SSE frame: the position to resume from, and the name that triggers a
    refetch."""

    id: int
    name: str


def tail(
    conn: StoreConnection,
    *,
    run_id: UUID,
    actor_id: UUID,
    last_event_id: int = 0,
) -> Iterator[StreamEvent]:
    """Deliver this run's events after `last_event_id`, while the actor may see
    them, stopping once a terminal one has been sent.

    Yields nothing at all for a run the actor cannot watch and for a run that
    does not exist -- the same silence, because telling the two apart is telling
    a stranger that a case exists.

    A generator on purpose: the recheck happens between yields, which is where a
    revocation lands in life and is also how a test can arrange one without this
    function growing a seam that exists only for tests.
    """
    case_id = _case_of(conn, run_id)
    if case_id is None:
        return

    for event_id, name in _events_after(conn, run_id, last_event_id):
        if not satisfies(
            standing_of(conn, case_id=case_id, user_id=actor_id), WATCH_REQUIRES
        ):
            return

        yield StreamEvent(id=event_id, name=name)

        if name in TERMINAL:
            return


def _events_after(
    conn: StoreConnection, run_id: UUID, last_event_id: int
) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT seq, name FROM run_events WHERE run_id = %s AND seq > %s ORDER BY seq",
        (run_id, last_event_id),
    ).fetchall()
    return [(int(row[0]), str(row[1])) for row in rows]


def _case_of(conn: StoreConnection, run_id: UUID) -> UUID | None:
    row = conn.execute(
        "SELECT case_id FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    return None if row is None else UUID(str(row[0]))


# The case stream (brief 4.4 decisions 1-4), beside the run tail it replaces.

# Once per connection: the heads and the run's terminal position, one query.
CONNECT_IO = 1
# Per poll: the audit actions after the cursor, the run events after it (until
# the terminal is delivered), and the standing recheck. Each frame then costs
# one more recheck -- the N+1 §9 mandates, spread across the stream's life.
POLL_IO = 3

# How many run events one poll reads; the next poll continues after the last.
RUN_PAGE = 500


@dataclass(frozen=True, slots=True)
class _CaseEvent:
    """One case-stream frame: the position to resume from, and the name that
    triggers a refetch -- `None` for the cursor-only frame."""

    id: Marker
    name: EventName | None


def case_tail(  # noqa: PLR0913 -- the stream's identity, then its lifetime
    conn: StoreConnection,
    *,
    case_id: UUID,
    run_id: UUID | None,
    actor_id: UUID,
    after: str | None,
    deadline: float = 0.0,
    poll: float = 0.0,
) -> Iterator[_CaseEvent]:
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
    yield _CaseEvent(at, None)

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


def _pending(
    conn: StoreConnection, case_id: UUID, run_id: UUID | None, at: Marker
) -> list[tuple[_CaseEvent, bool]]:
    """One poll's rows after `at`, each with its cursor and name (`None` for a
    silent row, which still advances the cursor), and whether it ends the run
    half. The run's rows stop at its terminal; `run_id` is `None` once that has
    been delivered, and the run is not read at all."""
    pending: list[tuple[_CaseEvent, bool]] = []
    for seq, action in actions_after(conn, case_id=case_id, seq=at.audit_seq):
        at = Marker(seq, at.run_seq)
        pending.append((_CaseEvent(at, STREAM_NAMES.get(action)), False))
    if run_id is None:
        return pending
    for seq, event in _run_events_after(conn, run_id, at.run_seq):
        at = Marker(at.audit_seq, seq)
        closes = event in TERMINAL
        pending.append((_CaseEvent(at, STREAM_NAMES.get(event)), closes))
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
