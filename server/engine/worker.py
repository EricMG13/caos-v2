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
from dataclasses import dataclass
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
from server.store.work import LEASE_SECONDS, Lease, claim_run, release, stop

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

    def check_context(self, route_node_id: str, module_id: str) -> None:
        if self.stopping.is_set():
            raise _Stopping
        self.inner.check_context(route_node_id, module_id)

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        return self.inner.execute(route_node_id, module_id, attempt_id=attempt_id)


def module_execution(
    completions: CompletionProvider, price: ModelPrice, bundle: Bundle, blobs: BlobStore
) -> ExecutionFor:
    """Each claimed run executes its pinned route through the real module
    provider, on the worker's connection and under its lease."""

    def execution_for(conn: StoreConnection, run_id: UUID, lease: Lease) -> Execution:
        with execution_reads(conn):
            _pin, route = execution_input(conn, run_id, bundle)
        provider = ModuleProvider(
            conn, bundle, blobs, completions, route, run_id, lease
        )
        return Execution(provider, price, bundle, lease=lease)

    return execution_for


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
    try:
        execution = execution_for(conn, lease.run_id, lease)
        stoppable = _Stoppable(execution.provider, stopping)
        with execution_reads(conn):
            _pin, route = execution_input(conn, lease.run_id, execution.bundle)
        run_route(
            conn,
            blobs,
            run_id=lease.run_id,
            route=route,
            execution=Execution(stoppable, execution.price, execution.bundle, lease),
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
            # A store fault here heals itself: released, the lease expires,
            # the run is reclaimed and the cancel is retried -- so it takes the
            # same back-off the branch below gives that class, and parking it
            # would turn a transient fault into a stop an operator must requeue
            # by hand. Anything else -- `RUN_NOT_RUNNING` for a run already
            # terminal, and the codes `cancel_run`'s own writes carry -- has no
            # such recovery, and raising it would leave `work_once` holding the
            # claim, with the run at the head of every later poll.
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
    """Configure from the environment, or print only the typed code and exit 2
    having made no call."""
    stopping = Event()
    try:
        completions = OpenRouter.from_environment()
        price = price_from_environment(
            completions.model, os.environ.get(MODEL_PRICE, "")
        )
        url, root = _store_configuration()
        bundle = Bundle(VENDORED_BUNDLE)
        bundle.verify_manifest()
        with connect(url) as conn:
            apply_schema(conn)
    except Refusal as refused:
        print(refused.code.value, file=sys.stderr)
        return 2
    except psycopg.Error:
        print(RefusalCode.STORE_UNAVAILABLE.value, file=sys.stderr)
        return 2
    install_stop_handler(stopping)
    blobs = BlobStore(Path(root))
    return run_worker(
        WorkerConfig(BoundaryText.of(f"worker-{os.getpid()}")),
        execution_for=module_execution(completions, price, bundle, blobs),
        stopping=stopping,
        conn_factory=lambda: connect(url),
        blobs=blobs,
    )


if __name__ == "__main__":
    sys.exit(main())
