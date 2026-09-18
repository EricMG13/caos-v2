"""One PostgreSQL-backed worker: poll, claim a run, drive it, map the outcome.

Brief 4.3 D9. No broker, no LISTEN/NOTIFY, no listener: lease expiry has to be
polled anyway, and the work row is the whole queue. A claim is per run (D1), so
this process is the run's only writer until its lease is lost, and every write
it makes is fenced by the lease token (D3).

`stopping` is checked between nodes -- before a node's context check, so before
its attempt, reservation or call -- and between polls, never during a call: a
SIGTERM lets the call in flight be billed and accepted, then gives the run back
to the queue.
"""

from __future__ import annotations

import os
import secrets
import signal
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import Event
from uuid import UUID

import psycopg

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.runtime import Execution, Provider, ProviderResult, run_route
from server.methodology.bundle import Bundle
from server.methodology.runner import ModuleProvider
from server.pricing import ModelPrice, worst_case
from server.provider import CompletionProvider, OpenRouter
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, apply_schema, connect, rollback_or_close
from server.store.gates import execution_input
from server.store.outcomes import execution_reads
from server.store.runs import cancel_run
from server.store.work import (
    LEASE_SECONDS,
    Lease,
    WorkerState,
    beat,
    claim_run,
    release,
    stop,
)

DATABASE_URL = "CAOS_DATABASE_URL"
BLOB_ROOT = "CAOS_BLOB_ROOT"
# `model,input_per_token,output_per_token,YYYY-MM-DD`: the worker's price (§49).
MODEL_PRICE = "CAOS_MODEL_PRICE"
VENDORED_BUNDLE = Path(__file__).resolve().parents[2] / "vendor" / "deploy-v"
# Only the faults that are the *store's*, not one run's. A blob fault names a
# run: releasing it would put that run back at the head of the queue (`release`
# leaves `requested_at` alone) to fail the same way every poll, with no stop
# code and no line on stderr. It is parked STOPPED with its code instead, which
# is what tells an operator to restore the blob. Replay does not need the
# release: `outcomes._NOT_AN_EXPLANATION` is what keeps a billed answer out of
# `attempt_refusals`, and `_drive` asks `replay_billed` before any new attempt,
# so a requeued run replays the body it already paid for.
STORE_FAULTS = frozenset(
    {RefusalCode.STORE_UNAVAILABLE, RefusalCode.STORE_NOT_TRANSACTIONAL}
)

ExecutionFor = Callable[[StoreConnection, UUID, Lease], Execution]


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    """Who this worker is (diagnostic only) and how it paces itself."""

    worker: BoundaryText
    lease_seconds: int = LEASE_SECONDS
    poll_seconds: float = 1.0
    backoff_cap_seconds: float = 30.0


class _Stopping(Exception):
    """Raised between nodes once `stopping` is set; never during a call."""


@dataclass(frozen=True, slots=True)
class _Stoppable:
    """The run's provider, refusing to begin another node once stopping."""

    inner: Provider
    stopping: Event

    @property
    def model(self) -> str:
        return self.inner.model

    def check_context(self, route_node_id: str, module_id: str) -> int:
        if self.stopping.is_set():
            raise _Stopping
        return self.inner.check_context(route_node_id, module_id)

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        return self.inner.execute(route_node_id, module_id, attempt_id=attempt_id)


def module_execution(
    completions: CompletionProvider,
    price: ModelPrice,
    bundle: Bundle,
    blobs: BlobStore,
    connect_store: Callable[[], StoreConnection] | None = None,
) -> ExecutionFor:
    """Each claimed run executes its pinned route through the real module
    provider, on the worker's connection and under its lease.

    `connect_store` is what lets a pass run its independent nodes at once: each
    gets a connection of its own and a provider bound to it, because a node's
    pre-call unit opens a transaction under the case lock and `ModuleProvider`
    reads the store to build its prompt. Omitted -- which is every test that
    drives this directly -- the loop stays sequential, and it is sequential
    anyway wherever a frontier offers one node, which is every LITE route this
    build enables.

    The lease is shared across those connections on purpose: it fences the
    *run*, and each write checks the token it was taken under, so two nodes of
    one run writing under one lease is the claim working rather than a hole in
    it.
    """

    def execution_for(conn: StoreConnection, run_id: UUID, lease: Lease) -> Execution:
        with execution_reads(conn):
            _pin, route = execution_input(conn, run_id, bundle)
        provider = ModuleProvider(
            conn, bundle, blobs, completions, route, run_id, lease
        )

        def per_node() -> tuple[StoreConnection, Provider]:
            assert connect_store is not None  # only reachable when it is set
            node_conn = connect_store()
            return node_conn, ModuleProvider(
                node_conn, bundle, blobs, completions, route, run_id, lease
            )

        return Execution(
            provider,
            price,
            bundle,
            lease=lease,
            per_node=per_node if connect_store else None,
        )

    return execution_for


def _stoppable_nodes(
    execution: Execution, stopping: Event
) -> Callable[[], tuple[StoreConnection, Provider]] | None:
    """The per-node factory, each provider wrapped so a concurrent pass stops.

    Without this a SIGTERM would stop the sequential loop between nodes and not
    a concurrent one, because `_Stoppable` was only ever put around the
    execution's own provider -- the nodes of a batch build their own.
    """
    build = execution.per_node
    if build is None:
        return None

    def stoppable_node() -> tuple[StoreConnection, Provider]:
        node_conn, provider = build()
        return node_conn, _Stoppable(provider, stopping)

    return stoppable_node


def work_once(
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    execution_for: ExecutionFor,
    config: WorkerConfig,
    stopping: Event,
) -> UUID | None:
    """Claim at most one run and drive it until it ends or cannot go on.

    Returns the claimed run, or None when stopping or nothing is claimable. A
    store fault releases the claim (or leaves it to expire) and is raised, so
    the loop backs off.
    """
    if stopping.is_set():
        return None
    lease = claim_run(conn, worker=config.worker, lease_seconds=config.lease_seconds)
    if lease is None:
        return None
    # Said before the run is driven rather than after it: driving is the part
    # that takes minutes, and a worker that went quiet *while working* is a
    # different thing for an operator than one that went quiet while idle.
    # `claim_run` commits alone, so this beat is its own unit too.
    _beat(conn, config, "WORKING", 0)
    try:
        execution = execution_for(conn, lease.run_id, lease)
        with execution_reads(conn):
            _pin, route = execution_input(conn, lease.run_id, execution.bundle)
        run_route(
            conn,
            blobs,
            run_id=lease.run_id,
            route=route,
            # `replace`, not a fresh `Execution` listing the fields this line
            # happens to know about. It used to be the latter, and when
            # `per_node` was added the worker silently dropped it -- so the
            # concurrent pass was built, tested, documented and then never
            # reached production, because one constructor call four screens
            # away did not mention it. A field added tomorrow survives this.
            execution=replace(
                execution,
                provider=_Stoppable(execution.provider, stopping),
                lease=lease,
                per_node=_stoppable_nodes(execution, stopping),
            ),
        )
    except _Stopping:
        _settle(conn, lambda: release(conn, lease))
    except psycopg.Error:
        _settle(conn, lambda: release(conn, lease))
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except Refusal as refused:
        _refused(conn, lease, refused)
    except Exception as fault:  # noqa: BLE001 -- neither a refusal nor a store error
        # Parked, not raised: a worker that died holding the claim would find the
        # same run first after every lease expiry and never reach the rest of the
        # queue. The class and the frame it was raised in are host facts; the
        # message may quote a document and is never written.
        frames = traceback.extract_tb(fault.__traceback__)
        where = f"{frames[-1].filename}:{frames[-1].lineno}" if frames else "?"
        print(f"{type(fault).__name__} at {where}", file=sys.stderr)
        _settle(conn, lambda: stop(conn, lease, RefusalCode.INTERNAL_FAULT))
    return lease.run_id


def _refused(conn: StoreConnection, lease: Lease, refused: Refusal) -> None:
    code = refused.code
    if code in (RefusalCode.LEASE_NOT_HELD, RefusalCode.RUN_NOT_RUNNING):
        _settle(conn, lambda: False)  # another holder or a terminal run owns it
    elif code is RefusalCode.RUN_CANCEL_REQUESTED:
        _settle(conn, lambda: False)
        try:
            cancel_run(conn, lease.run_id, lease=lease)  # commits its own unit
        except Refusal as lost:
            # `cancel_run` refuses three classes and no others: a store
            # fault (`STORE_UNAVAILABLE` or `STORE_NOT_TRANSACTIONAL`),
            # `LEASE_NOT_HELD` from its `require_lease` fence, and
            # `RUN_NOT_FOUND` from `lock_run` for a run row that is not there
            # (a run already terminal is answered False, not refused). The
            # store fault heals itself -- released, or failing that left to
            # expire -- so the run is reclaimed and the cancel retried, the
            # same back-off the branch below gives that class, and parking it
            # would turn a transient fault into a stop an operator must
            # requeue by hand. A missing run has no such recovery, and raising
            # it would leave `work_once` holding the claim, with the run at
            # the head of every later poll.
            unmet = lost.code
            if unmet in STORE_FAULTS:
                _settle(conn, lambda: release(conn, lease))
                raise Refusal(unmet) from None
            if unmet is not RefusalCode.LEASE_NOT_HELD:
                print(unmet.value, file=sys.stderr)
                _settle(conn, lambda: stop(conn, lease, unmet))
    elif code in STORE_FAULTS:
        _settle(conn, lambda: release(conn, lease))
        raise Refusal(code)
    else:
        _settle(conn, lambda: stop(conn, lease, code))


def _settle(conn: StoreConnection, write: Callable[[], bool]) -> None:
    """Discard any open unit, then commit one queue write; a store that cannot
    take it leaves the lease to expire."""
    try:
        conn.rollback()
        write()
        conn.commit()
    except psycopg.Error:
        rollback_or_close(conn)


def pause_seconds(config: WorkerConfig, failures: int) -> float:
    """The next wait: the poll interval, doubled per consecutive store fault up
    to the cap, with +-20% jitter so workers do not poll in step."""
    base = config.poll_seconds * float(2 ** max(failures - 1, 0))
    # Integer thousandths first: `0.8 + 400 / 1000` is 1.2000000000000002.
    jitter = (800 + secrets.randbelow(401)) / 1000
    return min(base, config.backoff_cap_seconds) * jitter


def _beat(
    conn: StoreConnection, config: WorkerConfig, state: WorkerState, faults: int
) -> None:
    """Record this worker's state, and never let saying so stop it working.

    A heartbeat is an observation for a person, not a fence: nothing reads it
    to decide whether work may proceed. So a store that will not take the beat
    must not take the worker down with it -- the loop's own fault handling is
    what answers a store that is failing, and it does that by trying to claim a
    run, which is the thing that actually matters.
    """
    try:
        beat(conn, worker_id=config.worker.value, state=state, faults=faults)
        conn.commit()
    except (psycopg.Error, Refusal):
        conn.rollback()


def run_worker(
    config: WorkerConfig,
    *,
    execution_for: ExecutionFor,
    stopping: Event,
    conn_factory: Callable[[], StoreConnection],
    blobs: BlobStore,
) -> int:
    """Poll until `stopping`; returns the process exit code."""
    conn: StoreConnection | None = None
    failures = 0
    try:
        while not stopping.is_set():
            claimed: UUID | None = None
            try:
                if conn is None or conn.closed:
                    conn = conn_factory()
                _beat(conn, config, "POLLING", failures)
                claimed = work_once(
                    conn,
                    blobs,
                    execution_for=execution_for,
                    config=config,
                    stopping=stopping,
                )
                failures = 0
            except (Refusal, psycopg.OperationalError) as fault:
                if isinstance(fault, Refusal) and fault.code not in STORE_FAULTS:
                    raise
                failures += 1
                # Said here rather than at the next poll, and before the
                # connection is dropped. A worker looping claim-fault-claim
                # would otherwise read `WORKING` -- its last word before the
                # fault -- for as long as it kept faulting, which is the exact
                # signal this beat exists to carry. A beat that cannot be
                # written on a connection that has just failed is no loss: a
                # store that is down cannot record that it is down, and the
                # staleness of the last beat says it instead.
                if conn is not None:
                    _beat(conn, config, "BACKOFF", failures)
                _closed(conn)
                conn = None
            if claimed is None:
                stopping.wait(pause_seconds(config, failures))
    finally:
        _closed(conn)
    return 0


def _closed(conn: StoreConnection | None) -> None:
    if conn is not None:
        conn.close()


def price_from_environment(model: str, value: str) -> ModelPrice:
    """A dated price for exactly the configured model, or a typed refusal."""
    parts = value.split(",")
    try:
        name, given_input, given_output, as_of = parts
        price = ModelPrice(
            name, Decimal(given_input), Decimal(given_output), date.fromisoformat(as_of)
        )
    except (ValueError, InvalidOperation):
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED) from None
    if price.model != model:
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    worst_case(price)
    return price


def _store_configuration() -> tuple[str, str]:
    url, root = os.environ.get(DATABASE_URL), os.environ.get(BLOB_ROOT)
    if not url or not root:
        raise Refusal(RefusalCode.STORE_NOT_CONFIGURED)
    return url, root


def install_stop_handler(stopping: Event) -> None:
    """SIGTERM only sets `stopping`; the loop decides when that is safe."""
    signal.signal(signal.SIGTERM, lambda _signum, _frame: stopping.set())


def main() -> int:
    """Configure from the environment, or exit 2 having made no call, printing
    the typed code -- and, where a variable nobody set is the reason, that
    variable's name beside it. A name is a host fact; a value is never printed.

    The name is attached beside the handler rather than at the check, so it is
    correct only while nothing between the check and the price call can raise:
    today `price_from_environment` refuses an empty value on the next line."""
    stopping = Event()
    # A variable nobody set is an unset variable, not a misconfigured one. Its
    # *name* is a host fact and is printed; its contents never are.
    unset = ""
    try:
        completions = OpenRouter.from_environment()
        given = os.environ.get(MODEL_PRICE, "")
        unset = "" if given else MODEL_PRICE
        price = price_from_environment(completions.model, given)
        url, root = _store_configuration()
        bundle = Bundle(VENDORED_BUNDLE)
        bundle.verify_manifest()
        with connect(url) as conn:
            apply_schema(conn)
    except Refusal as refused:
        named = f" {unset} unset" if unset else ""
        print(f"{refused.code.value}{named}", file=sys.stderr)
        return 2
    except psycopg.Error:
        print(RefusalCode.STORE_UNAVAILABLE.value, file=sys.stderr)
        return 2
    install_stop_handler(stopping)
    blobs = BlobStore(Path(root))
    return run_worker(
        WorkerConfig(BoundaryText.of(f"worker-{os.getpid()}")),
        # The same factory the loop uses for its own connection: a concurrent
        # pass opens one per node and closes it when that node is done.
        execution_for=module_execution(
            completions, price, bundle, blobs, lambda: connect(url)
        ),
        stopping=stopping,
        conn_factory=lambda: connect(url),
        blobs=blobs,
    )


if __name__ == "__main__":
    sys.exit(main())
