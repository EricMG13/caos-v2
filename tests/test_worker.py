"""The PostgreSQL worker loop (brief 4.3 D9): claim, drive, map, stop cleanly.

Every run here is the canonical LITE route through the real `ModuleProvider`,
answered by a deterministic completions double; no provider is ever live.
"""

from __future__ import annotations

import ast
import signal
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from uuid import UUID

import psycopg
import pytest
from canonical_fixtures import UNANCHORED, CanonicalCompletions
from conftest import priced
from lite_route_fixtures import RealisticLiteCompletions
from test_runtime import ESTIMATE, _approved_run, _Run, blobs, bundle, route

from server import provider as provider_module
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine import worker
from server.engine.route import ResolvedRoute
from server.engine.worker import (
    WorkerConfig,
    install_stop_handler,
    module_execution,
    run_worker,
    work_once,
)
from server.methodology.bundle import Bundle
from server.provider import CompletionProvider
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.runs import run_status
from server.store.work import LEASE_SECONDS, enqueue_run

__all__ = ["blobs", "bundle", "route"]

REPO = Path(__file__).resolve().parents[1]
CONFIG = WorkerConfig(BoundaryText.of("worker-test"), poll_seconds=0.5)


def queued_run(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
) -> _Run:
    """An approved LITE run, enqueued and committed."""
    conn, case_id = case
    run = _approved_run(conn, case_id, route, bundle, blobs)
    enqueue_run(conn, run.run_id)
    conn.commit()
    return run


def work_row(conn: StoreConnection, run_id: UUID) -> tuple[object, ...]:
    row = conn.execute(
        "SELECT state, stop_code, worker, lease_expires_at IS NULL"
        " FROM run_work WHERE run_id = %s",
        (run_id,),
    ).fetchone()
    conn.rollback()
    assert row is not None
    return tuple(row)


def count(conn: StoreConnection, table: str, run_id: UUID) -> int:
    row = conn.execute(
        "SELECT count(*) FROM " + table + " WHERE run_id = %s", (run_id,)
    ).fetchone()
    conn.rollback()
    assert row is not None
    return int(row[0])


def drive(
    run: _Run, completions: CompletionProvider, *, stopping: Event | None = None
) -> UUID | None:
    return work_once(
        run.conn,
        run.blobs,
        execution_for=module_execution(
            completions, priced(ESTIMATE), run.bundle, run.blobs
        ),
        config=CONFIG,
        stopping=stopping or Event(),
    )


def test_worker_drives_an_enqueued_lite_run_to_complete_with_a_deterministic_provider(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
) -> None:
    run = queued_run(case, route, bundle, blobs)
    completions = RealisticLiteCompletions(run.source_id)

    assert drive(run, completions) == run.run_id

    assert run_status(run.conn, run.run_id) is RunStatus.COMPLETE
    assert work_row(run.conn, run.run_id) == ("DONE", None, None, True)
    assert count(run.conn, "artifacts", run.run_id) == len(route.nodes)
    assert len(completions.prompts) == len(route.nodes)
    assert drive(run, completions) is None, "nothing left to claim"


def test_worker_stops_a_refused_run_with_its_code_and_releases_the_lease(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
) -> None:
    run = queued_run(case, route, bundle, blobs)
    completions = CanonicalCompletions(run.source_id, quotes=(UNANCHORED,))

    assert drive(run, completions) == run.run_id

    [(code,)] = run.conn.execute(
        "SELECT r.code FROM attempt_refusals r JOIN run_attempts a USING (attempt_id)"
        " WHERE a.run_id = %s",
        (run.run_id,),
    ).fetchall()
    assert work_row(run.conn, run.run_id) == ("STOPPED", code, None, True)
    assert run_status(run.conn, run.run_id) is RunStatus.RUNNING
    run.conn.rollback()
    assert drive(run, completions) is None, "a stopped run waits for a retry"
    assert len(completions.prompts) == 1


def test_sigterm_finishes_the_unit_and_requeues(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
) -> None:
    """The signal only sets `stopping`; the call in flight is billed and
    accepted, and the next node is never started."""
    run = queued_run(case, route, bundle, blobs)
    stopping = Event()
    previous = signal.getsignal(signal.SIGTERM)
    install_stop_handler(stopping)
    try:
        completions = CanonicalCompletions(
            run.source_id, during=lambda: signal.raise_signal(signal.SIGTERM)
        )
        assert drive(run, completions, stopping=stopping) == run.run_id
    finally:
        signal.signal(signal.SIGTERM, previous)

    assert stopping.is_set()
    assert len(completions.prompts) == 1
    assert count(run.conn, "artifacts", run.run_id) == 1
    assert count(run.conn, "run_attempts", run.run_id) == 1
    assert work_row(run.conn, run.run_id) == ("QUEUED", None, None, True)
    assert run_status(run.conn, run.run_id) is RunStatus.RUNNING
    run.conn.rollback()
    assert drive(run, completions, stopping=stopping) is None, "stopping claims nothing"


@dataclass
class _Clock(Event):
    """A `stopping` event that records each pause and stops after `limit`."""

    limit: int = 4
    pauses: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__()

    def wait(self, timeout: float | None = None) -> bool:
        assert timeout is not None
        self.pauses.append(timeout)
        if len(self.pauses) >= self.limit:
            self.set()
        return self.is_set()


@pytest.mark.parametrize(
    "code",
    [
        RefusalCode.BLOB_ADDRESS_INVALID,
        RefusalCode.BLOB_DIGEST_MISMATCH,
        RefusalCode.BLOB_NOT_FOUND,
    ],
)
def test_a_blob_fault_parks_the_run_with_its_code(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
    code: RefusalCode,
) -> None:
    """A blob fault names one run, so it parks rather than going back in the queue.

    `release` leaves `requested_at` alone and `claim_run` orders by it, so a
    released run is re-claimed first every poll. A lost or tampered original
    does not heal on its own, so releasing it would spin the worker on that run
    forever with no stop code, no event and nothing on stderr. STOPPED with the
    code is the signal to restore the blob; the operator requeues, and
    `replay_billed` uses the body already paid for.
    """
    run = queued_run(case, route, bundle, blobs)

    def faulty(conn: StoreConnection, run_id: UUID, lease: object) -> object:
        raise Refusal(code)

    assert (
        work_once(
            run.conn,
            run.blobs,
            execution_for=faulty,  # type: ignore[arg-type]
            config=CONFIG,
            stopping=Event(),
        )
        == run.run_id
    )

    assert work_row(run.conn, run.run_id) == ("STOPPED", code.value, None, True)


@pytest.mark.parametrize(
    "code",
    [RefusalCode.STORE_UNAVAILABLE, RefusalCode.STORE_NOT_TRANSACTIONAL],
)
def test_store_fault_backs_off_without_holding_a_claim(  # noqa: PLR0913 -- parametrized store faults
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
    empty_database: str,
    code: RefusalCode,
) -> None:
    run = queued_run(case, route, bundle, blobs)
    config = WorkerConfig(
        BoundaryText.of("worker-test"), poll_seconds=1.0, backoff_cap_seconds=3.0
    )
    built: list[UUID] = []

    def faulty(conn: StoreConnection, run_id: UUID, lease: object) -> object:
        built.append(run_id)
        raise Refusal(code)

    connects = iter([False, True, True, True, True])

    def conn_factory() -> StoreConnection:
        if not next(connects):
            raise psycopg.OperationalError("down")
        return psycopg.connect(empty_database, autocommit=False)

    clock = _Clock(limit=4)
    assert (
        run_worker(
            config,
            execution_for=faulty,  # type: ignore[arg-type]
            stopping=clock,
            conn_factory=conn_factory,
            blobs=blobs,
        )
        == 0
    )

    assert built == [run.run_id] * 3, "each claim was released and taken again"
    assert work_row(run.conn, run.run_id) == ("QUEUED", None, None, True)
    assert worker.pause_seconds(config, 9) <= 3.0 * 1.2, "capped"
    base = [1.0, 2.0, 3.0, 3.0]
    assert len(clock.pauses) == len(base)
    for pause, expected in zip(clock.pauses, base, strict=True):
        assert expected * 0.8 <= pause <= expected * 1.2


def test_main_refuses_without_provider_and_price(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def never(*_args: object, **_kwargs: object) -> object:
        pytest.fail("no store, bundle or call before configuration")

    monkeypatch.setattr(worker, "connect", never)
    monkeypatch.setattr(worker, "run_worker", never)
    monkeypatch.setattr(provider_module.OpenRouter, "complete", never)
    for name in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "CAOS_MODEL_PRICE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CAOS_DATABASE_URL", "postgresql://unused.invalid/none")
    monkeypatch.setenv("CAOS_BLOB_ROOT", "/nonexistent")

    assert worker.main() == 2
    assert capsys.readouterr().err == "PROVIDER_NOT_CONFIGURED\n"

    secret = "synthetic-key-never-printed-4c1d"
    monkeypatch.setenv("OPENROUTER_API_KEY", secret)
    monkeypatch.setenv("OPENROUTER_MODEL", "a-model/for-the-test")
    for price in ("", "a-model/for-the-test,0,1", "other/model,0,0.1,2026-09-13"):
        monkeypatch.setenv("CAOS_MODEL_PRICE", price)
        assert worker.main() == 2
        captured = capsys.readouterr()
        assert captured.err == "PROVIDER_NOT_CONFIGURED\n"
        assert secret not in captured.out + captured.err


def test_price_from_environment_reads_one_dated_price() -> None:
    price = worker.price_from_environment("m/x", "m/x,0.000001,0.000004,2026-09-13")
    assert (str(price.input_per_token), str(price.as_of)) == ("0.000001", "2026-09-13")
    with pytest.raises(Refusal, match=r"^MONEY_INVALID$"):
        worker.price_from_environment("m/x", "m/x,NaN,0.1,2026-09-13")


def test_the_lease_outlives_the_provider_timeout() -> None:
    """D5: a lease renewed before a call outlives two socket timeouts."""
    assert LEASE_SECONDS > 2 * provider_module.TIMEOUT_SECONDS
    assert WorkerConfig(BoundaryText.of("w")).lease_seconds == LEASE_SECONDS


FORBIDDEN_MODULES = frozenset(
    {"server.provider", "server.methodology.runner", "server.engine.worker"}
)
FORBIDDEN_NAMES = frozenset(
    {
        "run_route",
        "Execution",
        "ModuleProvider",
        "OpenRouter",
        "UrllibTransport",
        "Transport",
        "execute_handoff",
        "work_once",
        "run_worker",
    }
)


def _reaches(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names if a.name in FORBIDDEN_MODULES}
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in FORBIDDEN_MODULES:
                found.add(module)
            found |= {
                f"{module}.{a.name}"
                for a in node.names
                if a.name in FORBIDDEN_NAMES
                or f"{module}.{a.name}" in FORBIDDEN_MODULES
            }
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
            found.add(node.attr)
    return found


def test_no_api_module_reaches_the_runtime_or_a_provider_transport() -> None:
    """D4: a browser disconnect cannot cancel a paid call because the API holds
    nothing that makes one. The API shares `server.engine.runtime` for
    `accepted_artifacts`, so the check is on what each module names, not on the
    transitive import closure."""
    modules = sorted((REPO / "server" / "api").rglob("*.py"))
    assert len(modules) > 5, "a scan that read nothing is a failure"
    reached = {
        str(path.relative_to(REPO)): hits
        for path in modules
        if (hits := _reaches(ast.parse(path.read_text(encoding="utf-8"))))
    }
    assert reached == {}
    assert _reaches(ast.parse("from server.engine.runtime import run_route")) == {
        "server.engine.runtime.run_route"
    }


def test_an_unexpected_fault_parks_the_run_and_the_worker_goes_on(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A fault that is neither a refusal nor a store error must not kill the
    worker with the claim still held: the run would be reclaimed first after
    every lease expiry and block the queue. It is parked `INTERNAL_FAULT`
    (retry requeues it), the fault's class alone is written, and `work_once`
    returns so the loop polls on."""
    run = queued_run(case, route, bundle, blobs)

    def fault() -> None:
        raise RuntimeError("an unexpected fault with text that must not be shown")  # noqa: TRY003 -- the text is the point

    completions = CanonicalCompletions(run.source_id, during=fault)

    assert drive(run, completions) == run.run_id

    assert work_row(run.conn, run.run_id) == ("STOPPED", "INTERNAL_FAULT", None, True)
    assert run_status(run.conn, run.run_id) is RunStatus.RUNNING
    run.conn.rollback()
    written = capsys.readouterr().err
    assert "RuntimeError" in written and "must not be shown" not in written


def test_the_widest_jitter_stays_within_twenty_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bounds are exact at both ends: the float sum once overshot +20%."""
    config = WorkerConfig(BoundaryText.of("worker-test"), poll_seconds=1.0)
    monkeypatch.setattr("server.engine.worker.secrets.randbelow", lambda _n: 400)
    assert worker.pause_seconds(config, 2) <= 2.0 * 1.2
    monkeypatch.setattr("server.engine.worker.secrets.randbelow", lambda _n: 0)
    assert worker.pause_seconds(config, 2) >= 2.0 * 0.8


def test_a_stale_terminal_on_cancel_parks_the_run_and_never_escapes(  # noqa: PLR0913 -- the loop's own fixtures, plus the patch and the capture
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W4: `cancel_run` refuses more than a lost lease -- `RUN_TERMINAL_STALE`
    when the accepted set moved under it (§49.4). Re-raising it inside the
    mapper leaves `work_once` with the claim still held, so the run is reclaimed
    first after every lease expiry and the queue stops. It parks with its code
    instead, the way every other refusal does."""
    run = queued_run(case, route, bundle, blobs)

    def cancelling(conn: StoreConnection, run_id: UUID, lease: object) -> object:
        raise Refusal(RefusalCode.RUN_CANCEL_REQUESTED)

    def stale(*args: object, **kwargs: object) -> None:
        raise Refusal(RefusalCode.RUN_TERMINAL_STALE)

    monkeypatch.setattr(worker, "cancel_run", stale)

    assert (
        work_once(
            run.conn,
            run.blobs,
            execution_for=cancelling,  # type: ignore[arg-type]
            config=CONFIG,
            stopping=Event(),
        )
        == run.run_id
    )

    assert work_row(run.conn, run.run_id) == (
        "STOPPED",
        RefusalCode.RUN_TERMINAL_STALE.value,
        None,
        True,
    )
    assert capsys.readouterr().err.strip().splitlines()[-1] == "RUN_TERMINAL_STALE"
