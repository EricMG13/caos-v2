"""Every governed race proven on two independent connections.

`docs/AI_CODE_QUALITY.md` section 1 lists concurrency at ~2x in agent-written
code, and the control it names is this file: a race argued from the code is not
a race proven. One connection cannot prove a lock -- it never contends with
itself -- so each test here holds two.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest
from canonical_fixtures import CATALOG, LITE_PROFILE, LITE_SELECTION, VENDORED
from conftest import priced
from test_run_events import RECORD, accept_nodes, approved_nodes

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine import runtime
from server.engine.route import NodeState, resolve_route
from server.engine.runtime import Execution, ProviderResult, run_route
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, apply_schema, connect, runs
from server.store.budget import reserve
from server.store.events import RunEvent, events_of
from server.store.outcomes import check_call, execution_reads
from server.store.runs import (
    Accepted,
    accept_attempt,
    block_run,
    complete_attempt,
    complete_run,
    create_case,
    fail_run,
    run_status,
    start_attempt,
    start_run,
)
from server.store.work import Lease, claim_run, enqueue_run, request_cancel

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


def test_two_connections_claiming_one_queued_run_claim_it_once(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """`FOR UPDATE SKIP LOCKED` and the token increment make one claim (D3, I1)."""
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        enqueue_run(conn, run_id)
        conn.commit()
    start = Barrier(APPENDERS)

    def claim(worker: int) -> Lease | None:
        with connect(empty_database) as conn:
            start.wait(5)
            return claim_run(
                conn, worker=BoundaryText.of(f"worker-{worker}"), lease_seconds=60
            )

    with ThreadPoolExecutor(max_workers=APPENDERS) as pool:
        claims = list(pool.map(claim, range(APPENDERS)))

    assert [lease for lease in claims if lease is not None] == [Lease(run_id, 1)]
    with connect(empty_database) as conn:
        assert conn.execute(
            "SELECT state, lease_token FROM run_work WHERE run_id = %s", (run_id,)
        ).fetchone() == ("CLAIMED", 1)


def test_two_connections_completing_one_run_produce_one_terminal_event(
    empty_database: str, prepared_run: tuple[UUID, UUID], tmp_path: Path
) -> None:
    """Exactly-once under real contention rather than under replay.

    Two recovering processes can both believe they own the same attempt. The
    conditional update is what makes only one of them right.
    """
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        *others, last = approved_nodes(conn, run_id, tmp_path).values()
        # Completion needs every other pinned node accepted (brief 4.3 D8).
        accept_nodes(conn, run_id, *others)
        attempt_id = start_attempt(conn, run_id, last)
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
                    record_sha256=RECORD,
                ),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete) for _ in range(2)]
        outcomes = sorted(future.result() for future in futures)

    assert outcomes == [False, True], "exactly one caller completed the run"
    with connect(empty_database) as conn:
        row = conn.execute(
            "SELECT count(*) FROM budget_ledger WHERE run_id = %s", (run_id,)
        ).fetchone()
        assert row is not None and row[0] == len(others) + 1, "one charge per node"
        assert run_status(conn, run_id) is RunStatus.COMPLETE
        assert [e.name for e in events_of(conn, run_id)].count("RUN_COMPLETE") == 1


# -- The lease fence (brief 4.3 D3; interleavings I2-I4, I7, I8, I12) --------

RESERVED = Decimal("0.10")
WORKER = BoundaryText.of("worker-a")


def _claimed(url: str, run_id: UUID, *, enqueue: bool = True) -> Lease:
    with connect(url) as conn:
        if enqueue:
            enqueue_run(conn, run_id)
            conn.commit()
        lease = claim_run(conn, worker=WORKER, lease_seconds=60)
    assert lease is not None and lease.run_id == run_id
    return lease


def _reclaimed(url: str, run_id: UUID) -> Lease:
    """Expire the holder's lease and claim the run on another connection."""
    with connect(url) as conn:
        conn.execute(
            "UPDATE run_work SET lease_expires_at = now() - interval '1 second'"
            " WHERE run_id = %s",
            (run_id,),
        )
        conn.commit()
        lease = claim_run(conn, worker=BoundaryText.of("worker-b"), lease_seconds=60)
    assert lease is not None and lease.run_id == run_id
    return lease


def _refused(code: RefusalCode, call: Callable[[], object]) -> None:
    with pytest.raises(Refusal) as refused:
        call()
    assert refused.value.code is code


def _count(conn: StoreConnection, table: str, run_id: UUID) -> int:
    row = conn.execute(
        "SELECT count(*) FROM " + table + " WHERE run_id = %s", (run_id,)
    ).fetchone()
    conn.rollback()
    assert row is not None
    return int(row[0])


def _accepted() -> Accepted:
    return Accepted(
        artifact_sha256=ARTIFACT,
        charge=CHARGE,
        model=MODEL,
        generation_id=GENERATION,
        record_sha256=RECORD,
    )


def _checked(
    conn: StoreConnection, attempt: UUID, run_id: UUID, node: str, lease: Lease | None
) -> None:
    with execution_reads(conn):
        check_call(
            conn, attempt_id=attempt, run_id=run_id, route_node_id=node, lease=lease
        )


def test_a_reclaimed_lease_refuses_the_stale_start_attempt(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """I2: a holder whose lease was reclaimed starts nothing."""
    _case_id, run_id = prepared_run
    stale = _claimed(empty_database, run_id)
    fresh = _reclaimed(empty_database, run_id)
    with connect(empty_database) as a, connect(empty_database) as b:
        _refused(
            RefusalCode.LEASE_NOT_HELD,
            lambda: start_attempt(a, run_id, "CP-0", lease=stale),
        )
        assert _count(a, "run_attempts", run_id) == 0
        attempt = start_attempt(b, run_id, "CP-0", lease=fresh)
        assert b.execute(
            "SELECT lease_token FROM run_attempts WHERE attempt_id = %s", (attempt,)
        ).fetchone() == (fresh.token,)


def test_a_reclaimed_lease_refuses_the_stale_reservation_and_no_call_is_made(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """I3: the reservation refuses, and the pre-transport check refuses too."""
    _case_id, run_id = prepared_run
    stale = _claimed(empty_database, run_id)
    with connect(empty_database) as a:
        attempt = start_attempt(a, run_id, "CP-0", lease=stale)
        _reclaimed(empty_database, run_id)
        _refused(
            RefusalCode.LEASE_NOT_HELD,
            lambda: reserve(a, attempt, RESERVED, lease=stale),
        )
        assert _count(a, "budget_reservations", run_id) == 0
        _refused(
            RefusalCode.LEASE_NOT_HELD,
            lambda: _checked(a, attempt, run_id, "CP-0", stale),
        )


def test_a_stale_worker_returning_after_reclaim_keeps_its_bill_and_accepts_nothing(
    empty_database: str, prepared_run: tuple[UUID, UUID], tmp_path: Path
) -> None:
    """I4: money always commits; acceptance is the holder's alone."""
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        node = approved_nodes(conn, run_id, tmp_path)["CP-0"]
    stale = _claimed(empty_database, run_id)
    with connect(empty_database) as a, connect(empty_database) as b:
        first = start_attempt(a, run_id, node, lease=stale)
        reserve(a, first, RESERVED, lease=stale)
        # A is calling; its lease expires and B reclaims, starts and pays.
        fresh = _reclaimed(empty_database, run_id)
        second = start_attempt(b, run_id, node, lease=fresh)
        reserve(b, second, RESERVED, lease=fresh)
        # A returns before B accepts: nothing but the fence stops it.
        _refused(
            RefusalCode.LEASE_NOT_HELD,
            lambda: accept_attempt(
                a, attempt_id=first, accepted=_accepted(), lease=stale
            ),
        )
        assert _count(a, "budget_ledger", run_id) == 1, "A's bill committed"
        assert _count(a, "artifacts", run_id) == 0
        assert accept_attempt(b, attempt_id=second, accepted=_accepted(), lease=fresh)
        assert _count(b, "budget_ledger", run_id) == 2
        assert b.execute(
            "SELECT attempt_id FROM artifacts WHERE run_id = %s", (run_id,)
        ).fetchall() == [(second,)]


def test_a_claim_during_an_in_flight_acceptance_takes_nothing(
    empty_database: str, prepared_run: tuple[UUID, UUID], tmp_path: Path
) -> None:
    """I7: the accept holds the work row and renews it; the claim skips it."""
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        node = approved_nodes(conn, run_id, tmp_path)["CP-0"]
    lease = _claimed(empty_database, run_id)
    with connect(empty_database) as a, connect(empty_database) as b:
        attempt = start_attempt(a, run_id, node, lease=lease)
        reserve(a, attempt, RESERVED, lease=lease)
        b.execute(
            "UPDATE run_work SET lease_expires_at = now() - interval '1 second'"
            " WHERE run_id = %s",
            (run_id,),
        )
        b.commit()
        # The acceptance unit, stopped before its commit.
        assert runs._accept(a, attempt, _accepted(), lease)
        assert claim_run(b, worker=WORKER, lease_seconds=60) is None, "row held"
        a.commit()
        assert claim_run(b, worker=WORKER, lease_seconds=60) is None, "renewed"
        assert _count(b, "artifacts", run_id) == 1
        assert b.execute(
            "SELECT state, lease_token FROM run_work WHERE run_id = %s", (run_id,)
        ).fetchone() == ("CLAIMED", lease.token)


def test_a_stale_worker_cannot_end_the_run(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """I8: every terminal transition is fenced."""
    _case_id, run_id = prepared_run
    stale = _claimed(empty_database, run_id)
    fresh = _reclaimed(empty_database, run_id)
    with connect(empty_database) as conn:
        for end in (complete_run, block_run, fail_run):
            _refused(
                RefusalCode.LEASE_NOT_HELD,
                lambda end=end: end(conn, run_id, lease=stale),  # type: ignore[misc]
            )
            assert run_status(conn, run_id) is RunStatus.RUNNING
        assert not [e for e in events_of(conn, run_id) if e.name.startswith("RUN_")]
        conn.rollback()
        assert fail_run(conn, run_id, lease=fresh)
        assert run_status(conn, run_id) is RunStatus.FAILED


def test_an_unleased_writer_cannot_touch_an_enqueued_run(
    empty_database: str, prepared_run: tuple[UUID, UUID], tmp_path: Path
) -> None:
    """I12: once enqueued, a run has no direct writers."""
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        node = approved_nodes(conn, run_id, tmp_path)["CP-0"]
        enqueue_run(conn, run_id)
        conn.commit()
        _refused(RefusalCode.LEASE_NOT_HELD, lambda: start_attempt(conn, run_id, node))
    lease = _claimed(empty_database, run_id, enqueue=False)
    with connect(empty_database) as conn:
        attempt = start_attempt(conn, run_id, node, lease=lease)
        _refused(RefusalCode.LEASE_NOT_HELD, lambda: reserve(conn, attempt, RESERVED))
        reserve(conn, attempt, RESERVED, lease=lease)
        _refused(
            RefusalCode.LEASE_NOT_HELD,
            lambda: _checked(conn, attempt, run_id, node, None),
        )
        _refused(
            RefusalCode.LEASE_NOT_HELD,
            lambda: accept_attempt(conn, attempt_id=attempt, accepted=_accepted()),
        )
        for end in (complete_run, block_run, fail_run):
            _refused(RefusalCode.LEASE_NOT_HELD, lambda end=end: end(conn, run_id))  # type: ignore[misc]
        assert _count(conn, "artifacts", run_id) == 0
        assert run_status(conn, run_id) is RunStatus.RUNNING


def test_a_requested_cancel_refuses_the_next_start_and_reservation(
    empty_database: str, prepared_run: tuple[UUID, UUID], tmp_path: Path
) -> None:
    """D4: a cancel stops new spend; an answer already paid for still lands."""
    _case_id, run_id = prepared_run
    with connect(empty_database) as conn:
        node = approved_nodes(conn, run_id, tmp_path)["CP-0"]
    lease = _claimed(empty_database, run_id)
    with connect(empty_database) as a, connect(empty_database) as b:
        paid = start_attempt(a, run_id, node, lease=lease)
        reserve(a, paid, RESERVED, lease=lease)
        unpaid = start_attempt(a, run_id, "CP-L10", lease=lease)
        assert request_cancel(b, run_id)
        b.commit()
        _refused(
            RefusalCode.RUN_CANCEL_REQUESTED,
            lambda: reserve(a, unpaid, RESERVED, lease=lease),
        )
        _refused(
            RefusalCode.RUN_CANCEL_REQUESTED,
            lambda: start_attempt(a, run_id, node, lease=lease),
        )
        assert _count(a, "budget_reservations", run_id) == 1
        assert _count(a, "run_attempts", run_id) == 2
        assert accept_attempt(a, attempt_id=paid, accepted=_accepted(), lease=lease)


def test_a_terminal_transition_marks_work_done_in_the_same_transaction(
    empty_database: str, prepared_run: tuple[UUID, UUID]
) -> None:
    """A work row that cannot close rolls the terminal status and event back."""
    _case_id, run_id = prepared_run
    lease = _claimed(empty_database, run_id)
    with connect(empty_database) as conn:
        conn.execute(
            "CREATE FUNCTION refuse_done() RETURNS trigger LANGUAGE plpgsql AS"
            " $$ BEGIN RAISE EXCEPTION 'no'; END; $$"
        )
        conn.execute(
            "CREATE TRIGGER refuse_done BEFORE UPDATE ON run_work FOR EACH ROW"
            " WHEN (NEW.state = 'DONE') EXECUTE FUNCTION refuse_done()"
        )
        conn.commit()
        _refused(
            RefusalCode.STORE_UNAVAILABLE, lambda: block_run(conn, run_id, lease=lease)
        )
        assert run_status(conn, run_id) is RunStatus.RUNNING
        names = [e.name for e in events_of(conn, run_id)]
        assert RunEvent.RUN_BLOCKED.value not in names
        conn.execute("DROP TRIGGER refuse_done ON run_work")
        conn.commit()
        assert block_run(conn, run_id, lease=lease)
        assert conn.execute(
            "SELECT state FROM run_work WHERE run_id = %s", (run_id,)
        ).fetchone() == ("DONE",)
        assert [e.name for e in events_of(conn, run_id)].count(
            RunEvent.RUN_BLOCKED.value
        ) == 1


@dataclass
class _Reclaiming:
    """A provider during whose call another worker reclaims the run."""

    url: str
    run_id: UUID
    calls: list[str] = field(default_factory=list)

    @property
    def model(self) -> str:
        return MODEL

    def check_context(self, route_node_id: str, module_id: str) -> None:
        return None

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        self.calls.append(module_id)
        _reclaimed(self.url, self.run_id)
        return ProviderResult(ARTIFACT, CHARGE, MODEL, GENERATION, record_sha256=RECORD)


def test_the_runtime_writes_under_its_executions_lease(
    empty_database: str, prepared_run: tuple[UUID, UUID], tmp_path: Path
) -> None:
    """`Execution.lease` reaches every fenced write: a lease lost mid-call keeps
    the bill and accepts nothing, and the stale lease then starts nothing."""
    _case_id, run_id = prepared_run
    bundle = Bundle(VENDORED)
    route = resolve_route(CATALOG, LITE_PROFILE, LITE_SELECTION)
    with connect(empty_database) as conn:
        approved_nodes(conn, run_id, tmp_path, bundle, route)
        conn.commit()
    lease = _claimed(empty_database, run_id)
    blobs = BlobStore(tmp_path / "blobs")
    provider = _Reclaiming(empty_database, run_id)
    with connect(empty_database) as conn:

        def run() -> None:
            run_route(
                conn,
                blobs,
                run_id=run_id,
                route=route,
                execution=Execution(provider, priced(RESERVED), bundle, lease=lease),
            )

        _refused(RefusalCode.LEASE_NOT_HELD, run)
        assert provider.calls == ["CP-0"]
        assert _count(conn, "budget_ledger", run_id) == 1
        assert _count(conn, "artifacts", run_id) == 0
        _refused(RefusalCode.LEASE_NOT_HELD, run)
        assert provider.calls == ["CP-0"], "a stale lease starts no attempt"
        assert _count(conn, "run_attempts", run_id) == 1


@pytest.mark.parametrize("moves", [1, 2])
def test_a_stale_terminal_decision_runs_one_more_pass_then_raises(
    empty_database: str,
    prepared_run: tuple[UUID, UUID],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    moves: int,
) -> None:
    """D8: `run_route` decides from a read unit; a node accepted on another
    connection before the lock refuses `RUN_TERMINAL_STALE`, and the loop
    decides once more from the store -- at most once per call."""
    _case_id, run_id = prepared_run
    bundle = Bundle(VENDORED)
    route = resolve_route(CATALOG, LITE_PROFILE, LITE_SELECTION)
    with connect(empty_database) as conn:
        nodes = approved_nodes(conn, run_id, tmp_path, bundle, route)
        conn.commit()
    # Neither gate nor QA source: accepted as presence, no record to verify.
    movers = [nodes["CP-L10"], nodes["CP-5"]][:moves]
    decided: list[frozenset[str] | None] = []

    def moving(
        conn: StoreConnection,
        run: UUID,
        *,
        lease: Lease | None = None,
        accepted: frozenset[str] | None = None,
    ) -> bool:
        decided.append(accepted)
        if movers:
            with connect(empty_database) as other:
                accept_nodes(other, run, movers.pop(0))
        return block_run(conn, run, lease=lease, accepted=accepted)

    monkeypatch.setattr(runtime, "frontier", lambda *_args: ())
    monkeypatch.setattr(
        runtime,
        "node_states",
        lambda *_args: {n.route_node_id: NodeState.BLOCKED for n in route.nodes},
    )
    monkeypatch.setattr(runtime, "block_run", moving)
    execution = Execution(_Reclaiming(empty_database, run_id), priced(RESERVED), bundle)
    blobs = BlobStore(tmp_path / "blobs")
    with connect(empty_database) as conn:

        def run() -> None:
            run_route(conn, blobs, run_id=run_id, route=route, execution=execution)

        if moves == 1:
            run()
            assert run_status(conn, run_id) is RunStatus.BLOCKED
        else:
            _refused(RefusalCode.RUN_TERMINAL_STALE, run)
            assert run_status(conn, run_id) is RunStatus.RUNNING
        assert decided == [frozenset(), frozenset({nodes["CP-L10"]})], "no third"
        names = [e.name for e in events_of(conn, run_id)]
        assert names.count(RunEvent.RUN_BLOCKED.value) == (2 - moves)
