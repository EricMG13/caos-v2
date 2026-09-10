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

*A terminal event ends the tail.* A completed run produces nothing further, so
holding the connection open is a promise about events that cannot arrive.

The HTTP binding is not here. `text/event-stream` over a socket is transport, and
every rule above is answerable without one; the framework arrives with the route
that serves it (CLAUDE.md known gaps).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from server.store import StoreConnection
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

# The events after which there is nothing more to send.
TERMINAL = frozenset({RunEvent.RUN_COMPLETE.value, RunEvent.RUN_FAILED.value})

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
