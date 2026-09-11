"""Every governed race proven on two independent connections.

`docs/AI_CODE_QUALITY.md` section 1 lists concurrency at ~2x in agent-written
code, and the control it names is this file: a race argued from the code is not
a race proven. One connection cannot prove a lock -- it never contends with
itself -- so each test here holds two.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID

import pytest

from server.boundary_text import BoundaryText
from server.store import RunStatus, apply_schema, connect
from server.store.events import events_of
from server.store.runs import (
    Accepted,
    complete_attempt,
    create_case,
    run_status,
    start_attempt,
    start_run,
)

# The producer the store records beside every accepted artifact: what the
# host configured, and the provider's own handle for the call.
MODEL = "a-model/for-the-test"
GENERATION = "gen-for-the-test"

ARTIFACT = "c" * 64
CHARGE = Decimal("0.0142")
APPENDERS = 8


@pytest.fixture
def prepared_run(empty_database: str) -> tuple[UUID, UUID]:
    with connect(empty_database) as conn:
        apply_schema(conn)
        case_id = create_case(conn, BoundaryText.of("Acme 2026 refinancing"))
        run_id = start_run(conn, case_id)
        conn.commit()
    return case_id, run_id


def test_concurrent_appenders_never_share_a_seq(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """`run_events.seq` is allocated under the run row lock (SYSTEM_SPEC.md 2).

    Without the lock, two connections read the same `max(seq)` and insert the
    same next one: on a primary key that is a failed insert, and on anything
    weaker it is two events that claim one position in the stream.
    """
    _case_id, run_id = prepared_run

    def append(node: int) -> None:
        with connect(empty_database) as conn:
            start_attempt(conn, run_id, f"CP-{node}")
            conn.commit()

    with ThreadPoolExecutor(max_workers=APPENDERS) as pool:
        list(pool.map(append, range(APPENDERS)))

    with connect(empty_database) as conn:
        assert [event.seq for event in events_of(conn, run_id)] == list(
            range(1, APPENDERS + 1)
        )


def test_two_connections_completing_one_run_produce_one_terminal_event(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """Exactly-once under real contention rather than under replay.

    Two recovering processes can both believe they own the same attempt. The
    conditional update is what makes only one of them right.
    """
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        attempt_id = start_attempt(conn, run_id, "CP-1")
        conn.commit()

    def complete() -> bool:
        with connect(empty_database) as conn:
            return complete_attempt(
                conn,
                attempt_id=attempt_id,
                accepted=Accepted(
                    artifact_sha256=ARTIFACT,
                    charge=CHARGE,
                    model=MODEL,
                    generation_id=GENERATION,
                ),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.submit(complete).result() for _ in range(2))

    assert outcomes == [False, True], "exactly one caller completed the run"
    with connect(empty_database) as conn:
        row = conn.execute(
            "SELECT count(*) FROM budget_ledger WHERE run_id = %s", (run_id,)
        ).fetchone()
        assert row is not None and row[0] == 1
        assert run_status(conn, run_id) is RunStatus.COMPLETE
