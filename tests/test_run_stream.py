"""Phase 6 exit: the stream closes once a terminal run is fully delivered.

`SYSTEM_SPEC.md` §9. Run progress reaches the browser as SSE over `run_events`
with `Last-Event-ID` resume; membership is rechecked before each event; the
stream closes once a terminal run is fully delivered. The client never reads an
event's payload -- a name triggers a refetch.

That last sentence is why a stream event here carries an id and a name and
nothing else. A payload on the wire would be a second copy of state the client is
about to fetch properly, and the first thing to go stale.

What is *not* here is the HTTP binding. `text/event-stream` over a socket is
transport; every rule above is answerable without one, and this file answers
them. The framework arrives with the route that needs it.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from test_run_events import RECORD, approved_nodes

from server.api.stream import IO_BUDGET, TERMINAL, StreamEvent, tail
from server.refusals import Refusal
from server.store import StoreConnection
from server.store.events import RunEvent, events_of
from server.store.members import Standing, grant, revoke
from server.store.runs import (
    Accepted,
    block_run,
    complete_attempt,
    complete_run,
    fail_run,
    start_attempt,
    start_run,
)
from server.store.work import enqueue_run, request_cancel

# The producer the store records beside every accepted artifact: what the
# host configured, and the provider's own handle for the call.
MODEL = "a-model/for-the-test"
GENERATION = "gen-for-the-test"

ARTIFACT = "e" * 64
CHARGE = Decimal("0.01")


@pytest.fixture
def watched(case: tuple[StoreConnection, UUID]) -> tuple[StoreConnection, UUID, UUID]:
    """A run, and a READER entitled to watch it."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    viewer = uuid4()
    grant(conn, case_id=case_id, user_id=viewer, standing=Standing.READER)
    conn.commit()
    return conn, run_id, viewer


def _approved(conn: StoreConnection, run_id: UUID, blobs: Path) -> str:
    """Govern the run on the real route; acceptance requires it."""
    return next(iter(approved_nodes(conn, run_id, blobs).values()))


def _names(events: list[StreamEvent]) -> list[str]:
    return [event.name for event in events]


def test_sse_closes_after_terminal_delivery(
    watched: tuple[StoreConnection, UUID, UUID],
    tmp_path: Path,
) -> None:
    """The Phase 6 exit test.

    The tail is a finite thing once the run is terminal. It delivers the
    terminal event and returns -- it does not hold the connection open waiting
    for events that a completed run will never produce.
    """
    conn, run_id, viewer = watched
    node = _approved(conn, run_id, tmp_path)
    attempt_id = start_attempt(conn, run_id, node)
    complete_attempt(
        conn,
        attempt_id=attempt_id,
        accepted=Accepted(
            artifact_sha256=ARTIFACT,
            charge=CHARGE,
            model=MODEL,
            generation_id=GENERATION,
            record_sha256=RECORD,
        ),
    )

    # Late billing may follow a terminal event; it must not keep this tail open.
    conn.execute(
        "INSERT INTO run_events (run_id, seq, name) VALUES (%s, %s, %s)",
        (run_id, 7, RunEvent.CALL_OUTCOME_RECORDED.value),
    )
    conn.commit()

    delivered = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert _names(delivered) == [
        RunEvent.ROUTE_PINNED.value,
        RunEvent.INPUT_PINNED.value,
        RunEvent.ATTEMPT_STARTED.value,
        RunEvent.CALL_OUTCOME_RECORDED.value,
        RunEvent.ATTEMPT_ACCEPTED.value,
        RunEvent.RUN_COMPLETE.value,
    ]
    assert delivered[-1].name == RunEvent.RUN_COMPLETE.value, "the last thing sent"
    assert len(delivered) == 6, "delivery stopped at the terminal event"
    assert _names(
        list(tail(conn, run_id=run_id, actor_id=viewer, last_event_id=6))
    ) == [RunEvent.CALL_OUTCOME_RECORDED.value]


def test_a_failed_run_closes_the_stream_too(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, run_id, viewer = watched
    fail_run(conn, run_id)

    delivered = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert _names(delivered) == [RunEvent.RUN_FAILED.value]


def test_a_blocked_run_closes_the_stream_too(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, run_id, viewer = watched
    assert block_run(conn, run_id)
    assert not block_run(conn, run_id), "the terminal event is exactly-once"

    delivered = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert _names(delivered) == [RunEvent.RUN_BLOCKED.value]


def test_a_cancelled_run_closes_the_stream_too(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, run_id, viewer = watched
    enqueue_run(conn, run_id)
    assert request_cancel(conn, run_id)
    conn.commit()
    assert not request_cancel(conn, run_id), "the terminal event is exactly-once"
    conn.commit()

    delivered = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert _names(delivered) == [RunEvent.RUN_CANCELLED.value]
    assert RunEvent.RUN_CANCELLED.value in TERMINAL


def test_a_blocked_run_refuses_new_attempts(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, run_id, _viewer = watched
    block_run(conn, run_id)
    with pytest.raises(Refusal, match=r"^RUN_NOT_RUNNING$"):
        start_attempt(conn, run_id, "CP-1")
    # Blocked is not a way station to success: completion adds nothing.
    assert not complete_run(conn, run_id)
    assert [e.name for e in events_of(conn, run_id)] == [RunEvent.RUN_BLOCKED.value]


def test_a_running_run_delivers_what_there_is_and_stops(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    """Not terminal, so the tail is caught up rather than closed. The caller
    reconnects with Last-Event-ID; nothing here blocks waiting."""
    conn, run_id, viewer = watched
    start_attempt(conn, run_id, "CP-1")

    delivered = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert _names(delivered) == [RunEvent.ATTEMPT_STARTED.value]


def test_a_tail_resumes_after_last_event_id(
    watched: tuple[StoreConnection, UUID, UUID],
    tmp_path: Path,
) -> None:
    """`Last-Event-ID` is the seq of the last event the client actually got.

    Resuming from it must not re-deliver that event: a client that refetches on
    every name would do the work twice, and a terminal event delivered twice
    closes a stream that was already closed.
    """
    conn, run_id, viewer = watched
    node = _approved(conn, run_id, tmp_path)
    attempt_id = start_attempt(conn, run_id, node)
    complete_attempt(
        conn,
        attempt_id=attempt_id,
        accepted=Accepted(
            artifact_sha256=ARTIFACT,
            charge=CHARGE,
            model=MODEL,
            generation_id=GENERATION,
            record_sha256=RECORD,
        ),
    )
    first = list(tail(conn, run_id=run_id, actor_id=viewer))

    resumed = list(
        tail(conn, run_id=run_id, actor_id=viewer, last_event_id=first[2].id)
    )

    assert _names(resumed) == [
        RunEvent.CALL_OUTCOME_RECORDED.value,
        RunEvent.ATTEMPT_ACCEPTED.value,
        RunEvent.RUN_COMPLETE.value,
    ]
    assert [event.id for event in resumed] == [4, 5, 6]


def test_resuming_from_the_last_event_delivers_nothing(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, run_id, viewer = watched
    fail_run(conn, run_id)
    [only] = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert list(tail(conn, run_id=run_id, actor_id=viewer, last_event_id=only.id)) == []


def test_the_stream_carries_a_name_and_a_position_and_nothing_else(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    """`SYSTEM_SPEC.md` §9: the client never reads event payloads. A payload on
    the wire is a second copy of state the client is about to fetch properly,
    and the first thing to go stale."""
    conn, run_id, viewer = watched
    start_attempt(conn, run_id, "CP-1")

    [event] = list(tail(conn, run_id=run_id, actor_id=viewer))

    assert isinstance(event, StreamEvent)
    assert event.id == 1
    assert event.name == RunEvent.ATTEMPT_STARTED.value
    assert set(vars(StreamEvent).get("__annotations__", {})) == {"id", "name"}


class _CountingConnection:
    """Counts store round trips, so the declared budget is measured."""

    def __init__(self, conn: StoreConnection) -> None:
        self._conn = conn
        self.executed = 0

    def execute(self, *args: object, **kwargs: object) -> object:
        self.executed += 1
        return self._conn.execute(*args, **kwargs)  # type: ignore[arg-type]


def test_the_tail_costs_its_declared_budget_plus_one_check_per_event(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    """The fixed cost is `IO_BUDGET`; the rest is the mandated recheck.

    Asserted rather than described, so a fourth fixed query added later has to
    be argued for instead of arriving unnoticed.
    """
    conn, run_id, viewer = watched
    start_attempt(conn, run_id, "CP-0")
    start_attempt(conn, run_id, "CP-1")
    counter = _CountingConnection(conn)

    delivered = list(tail(counter, run_id=run_id, actor_id=viewer))  # type: ignore[arg-type]

    assert len(delivered) == 2
    assert counter.executed == IO_BUDGET + len(delivered)


def test_a_non_member_is_delivered_nothing(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    """The same silence an unknown run gets. Neither answer says the other
    exists (`SYSTEM_SPEC.md` §8: unknown and unauthorised both 404)."""
    conn, run_id, _viewer = watched
    start_attempt(conn, run_id, "CP-1")

    assert list(tail(conn, run_id=run_id, actor_id=uuid4())) == []


def test_membership_is_rechecked_before_each_event(
    watched: tuple[StoreConnection, UUID, UUID],
) -> None:
    """Not once at the handshake. A stream can outlive the standing that opened
    it, and an SSE connection is exactly the thing that stays open across a
    revocation.
    """
    conn, run_id, viewer = watched
    case_id = conn.execute(
        "SELECT case_id FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    assert case_id is not None
    start_attempt(conn, run_id, "CP-0")
    start_attempt(conn, run_id, "CP-1")

    # `tail` is a generator, so stopping here is exactly the pause a revocation
    # would land in. No seam in the production code is needed to arrange it.
    stream = tail(conn, run_id=run_id, actor_id=viewer)
    first = next(stream)

    revoke(conn, case_id=case_id[0], user_id=viewer)
    conn.commit()

    assert first.name == RunEvent.ATTEMPT_STARTED.value
    assert list(stream) == [], (
        "the second event was not delivered to a member who no longer is one"
    )
