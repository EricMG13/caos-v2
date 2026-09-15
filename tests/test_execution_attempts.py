"""Explicit attempt identity and bounded, caller-safe execution read units.

On the canonical LITE route through the canonical executor (slice f-1a)."""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

import psycopg
import pytest
from conftest import _url_for, priced
from psycopg.pq import TransactionStatus
from test_loop_charges import (
    ESTIMATE,
    MODEL,
    REPORTED,
    VENDORED,
    _Completions,
    ready,
    route,
)

from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, RouteNode
from server.engine.runtime import Execution, ProviderResult, run_route
from server.methodology.bundle import Bundle
from server.methodology.canonical import execute_handoff
from server.methodology.executor import Assignment
from server.methodology.runner import ModuleProvider
from server.provider import OpenRouter
from server.refusals import Refusal
from server.store import StoreConnection, connect
from server.store.budget import reserve
from server.store.events import lock_run
from server.store.outcomes import CallOutcome, record_outcome
from server.store.runs import Accepted, accept_attempt, fail_run, start_attempt

__all__ = ["ready", "route"]


@pytest.fixture
def provider(
    ready: tuple[StoreConnection, UUID, UUID, BlobStore], route: ResolvedRoute
) -> ModuleProvider:
    conn, run, source, blobs = ready
    return ModuleProvider(
        conn,
        Bundle(VENDORED),
        blobs,
        _Completions(source),
        route,
        run,
    )


def _reserve(provider: ModuleProvider, node: RouteNode) -> UUID:
    attempt = start_attempt(provider.conn, provider.run_id, node.route_node_id)
    reserve(provider.conn, attempt, ESTIMATE)
    return attempt


def _invoke(
    provider: ModuleProvider,
    attempt: UUID,
    entry: str,
    node: RouteNode,
    module: str | None = None,
) -> None:
    module = node.module_id if module is None else module
    if entry == "runtime":
        run_route(
            provider.conn,
            provider.blobs,
            run_id=provider.run_id,
            route=provider.route,
            execution=Execution(provider, priced(ESTIMATE), provider.bundle),
        )
    elif entry == "module":
        provider.execute(node.route_node_id, module, attempt_id=attempt)
    else:
        execute_handoff(
            provider.conn,
            provider.bundle,
            provider.blobs,
            assignment=Assignment(
                module, provider.run_id, node, provider.route, attempt
            ),
            provider=provider.completions,
        )


def _fault(
    provider: ModuleProvider, node: RouteNode, attempt: UUID, fault: str
) -> tuple[ModuleProvider, UUID, RouteNode, str]:
    module = node.module_id
    conn = provider.conn
    if fault == "run":
        provider = replace(provider, run_id=uuid4())
    elif fault == "node":
        node = replace(node, route_node_id="wrong-node")
    elif fault == "module":
        module = "CP-1"
    elif fault == "missing":
        attempt = uuid4()
    elif fault == "unreserved":
        attempt = start_attempt(conn, provider.run_id, node.route_node_id)
    elif fault == "terminal":
        fail_run(conn, provider.run_id)
    elif fault == "used":
        record_outcome(conn, attempt_id=attempt, outcome=CallOutcome(None, None, None))
    elif fault == "ledger":
        conn.execute(
            "INSERT INTO budget_ledger (attempt_id,run_id,amount) VALUES (%s,%s,0)",
            (attempt, provider.run_id),
        )
    else:
        conn.execute(
            "INSERT INTO artifacts (attempt_id,run_id,case_id,artifact_sha256,model,"
            " generation_id) SELECT %s,run_id,case_id,%s,'legacy','legacy'"
            " FROM runs WHERE run_id=%s",
            (attempt, "a" * 64, provider.run_id),
        )
    conn.commit()
    return provider, attempt, node, module


@dataclass
class _Transport:
    conn: StoreConnection
    # A fixed answer, a transport failure, or an answer to the prompt sent.
    response: tuple[int, bytes] | Exception | Callable[[str], tuple[int, bytes]]
    calls: int = 0
    prompts: list[str] = field(default_factory=list)

    def post(
        self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
    ) -> tuple[int, bytes]:
        assert self.conn.info.transaction_status is TransactionStatus.IDLE
        self.calls += 1
        self.prompts.append(json.loads(body)["messages"][0]["content"])
        if isinstance(self.response, Exception):
            raise self.response
        if callable(self.response):
            return self.response(self.prompts[-1])
        return self.response


def _wire(
    finish: str = "length",
    cost: str = "0.25",
    identity: str = '"generation"',
    content: str = "private",
) -> bytes:
    return (
        '{"id":' + identity + ',"usage":{"cost":' + cost + '},"choices":['
        '{"finish_reason":'
        + json.dumps(finish)
        + ',"message":{"content":'
        + json.dumps(content)
        + "}}]}"
    ).encode()


def _accepted(result: ProviderResult) -> Accepted:
    return Accepted(
        result.artifact_sha256,
        result.charge,
        result.model,
        result.generation_id,
        diagnostic_sha256=result.diagnostic_sha256,
        record_sha256=result.record_sha256,
    )


def test_two_attempts_are_attributed_explicitly_and_transport_reads_are_idle(
    provider: ModuleProvider,
) -> None:
    first, second = provider.route.nodes[:2]
    a1, a2 = _reserve(provider, first), _reserve(provider, second)
    answers = provider.completions

    def answer(prompt: str) -> tuple[int, bytes]:
        content = answers.complete(prompt, json_object=True).content or ""
        return 200, _wire("stop", str(REPORTED), content=content)

    transport = _Transport(provider.conn, answer)
    provider = replace(
        provider, completions=OpenRouter("offline", MODEL, transport=transport)
    )
    result = provider.execute(first.route_node_id, first.module_id, attempt_id=a1)
    accept_attempt(provider.conn, attempt_id=a1, accepted=_accepted(result))
    result = provider.execute(second.route_node_id, second.module_id, attempt_id=a2)
    with connect(_url_for(provider.conn.info.dbname)) as observer:
        assert observer.execute(
            "SELECT attempt_id,amount FROM budget_ledger ORDER BY charged_at"
        ).fetchall() == [(a1, REPORTED), (a2, REPORTED)]
        assert observer.execute(
            "SELECT attempt_id FROM call_outcomes ORDER BY recorded_at"
        ).fetchall() == [(a1,), (a2,)]
        assert observer.execute("SELECT attempt_id FROM artifacts").fetchall() == [
            (a1,)
        ]
    accept_attempt(provider.conn, attempt_id=a2, accepted=_accepted(result))
    assert provider.conn.info.transaction_status is TransactionStatus.IDLE
    assert provider.conn.execute(
        "SELECT attempt_id,amount FROM budget_ledger ORDER BY charged_at"
    ).fetchall() == [(a1, REPORTED), (a2, REPORTED)]
    assert transport.calls == 2
    assert "--- UPSTREAM" in transport.prompts[1]


@pytest.mark.parametrize("entry", ["module", "executor"])
@pytest.mark.parametrize(
    "fault,code",
    [
        ("run", "ATTEMPT_NOT_FOUND"),
        ("node", "ATTEMPT_NOT_FOUND"),
        ("module", "ROUTE_IDENTITY_INVALID"),
        ("missing", "ATTEMPT_NOT_FOUND"),
        ("unreserved", "BUDGET_NOT_RESERVED"),
        ("used", "CALL_OUTCOME_CONFLICT"),
        ("ledger", "CALL_OUTCOME_LEGACY"),
        ("artifact", "CALL_OUTCOME_LEGACY"),
        ("terminal", "RUN_NOT_RUNNING"),
    ],
)
def test_invalid_or_used_attempt_cannot_reach_completion(
    provider: ModuleProvider,
    entry: str,
    fault: str,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """check_call refuses before either evidence or upstream context is read."""
    from server.methodology import canonical, executor

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid attempt reached evidence or upstream reads")

    monkeypatch.setattr(executor, "read_run_block", forbidden)
    monkeypatch.setattr(canonical, "upstream_markdown", forbidden)
    node = provider.route.nodes[0]
    attempt = _reserve(provider, node)
    actual_run = provider.run_id
    conn = provider.conn
    provider, attempt, node, module = _fault(provider, node, attempt, fault)
    with connect(_url_for(conn.info.dbname)) as blocker:
        if fault == "run":
            lock_run(blocker, actual_run)
            conn.execute("SET lock_timeout = '100ms'")
            conn.commit()
        with pytest.raises(Refusal, match=f"^{code}$"):
            _invoke(provider, attempt, entry, node, module)
    assert conn.info.transaction_status is TransactionStatus.IDLE
    assert isinstance(provider.completions, _Completions)
    assert provider.completions.prompts == []


@pytest.mark.parametrize("entry", ["runtime", "module", "executor"])
@pytest.mark.parametrize(
    "state", ["pending", "autocommit", "repeatable", "serializable"]
)
def test_execution_refuses_unowned_transaction_without_touching_pending_writes(
    provider: ModuleProvider,
    entry: str,
    state: str,
) -> None:
    """require_idle preserves caller writes; isolation checks own only new reads."""
    conn = provider.conn
    node = provider.route.nodes[0]
    attempt = _reserve(provider, node)
    if state == "pending":
        conn.execute("UPDATE cases SET title = 'pending caller work'")
    elif state == "autocommit":
        conn.autocommit = True
    else:
        conn.isolation_level = (
            psycopg.IsolationLevel.REPEATABLE_READ
            if state == "repeatable"
            else psycopg.IsolationLevel.SERIALIZABLE
        )
    with pytest.raises(Refusal, match=r"^STORE_NOT_TRANSACTIONAL$"):
        _invoke(provider, attempt, entry, node)
    if state == "pending":
        assert conn.info.transaction_status is TransactionStatus.INTRANS
        assert conn.execute("SELECT title FROM cases").fetchone() == (
            "pending caller work",
        )
        with connect(_url_for(conn.info.dbname)) as observer:
            assert observer.execute("SELECT title FROM cases").fetchone() != (
                "pending caller work",
            )
    else:
        assert conn.info.transaction_status is TransactionStatus.IDLE
    assert isinstance(provider.completions, _Completions)
    assert provider.completions.prompts == []
    conn.rollback()


@pytest.mark.parametrize("entry", ["runtime", "module", "executor"])
def test_failed_successful_read_cleanup_closes_before_call(
    provider: ModuleProvider,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
) -> None:
    node = provider.route.nodes[0]
    attempt = _reserve(provider, node)

    def broken(conn: StoreConnection) -> None:
        raise psycopg.OperationalError("private")

    monkeypatch.setattr(psycopg.Connection, "rollback", broken)
    with pytest.raises(Refusal, match=r"^STORE_UNAVAILABLE$"):
        _invoke(provider, attempt, entry, node)
    assert provider.conn.closed
    assert isinstance(provider.completions, _Completions)
    assert provider.completions.prompts == []


@pytest.mark.parametrize("stage", ["delivery", "upstream", "frontier"])
@pytest.mark.parametrize("broken_cleanup", [False, True])
def test_owned_pretransport_read_failure_cleans_up_without_call(
    provider: ModuleProvider,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    broken_cleanup: bool,
) -> None:
    """execution_reads releases its unit or closes when its own cleanup fails."""
    from server.engine import runtime
    from server.methodology import canonical, executor

    dsn = _url_for(provider.conn.info.dbname)

    def fail(*args: object, **kwargs: object) -> None:
        provider.conn.execute("SELECT 1")
        if broken_cleanup:
            monkeypatch.setattr(psycopg.Connection, "rollback", broken)
        raise psycopg.OperationalError("private")

    def broken(conn: StoreConnection) -> None:
        raise psycopg.OperationalError("private")

    owner, name = {
        "delivery": (executor, "read_run_block"),
        "upstream": (canonical, "upstream_markdown"),
        "frontier": (runtime, "accepted_artifacts"),
    }[stage]
    monkeypatch.setattr(owner, name, fail)
    with pytest.raises(Refusal, match=r"^STORE_UNAVAILABLE$") as caught:
        _invoke(provider, uuid4(), "runtime", provider.route.nodes[0])
    assert caught.value.__cause__ is None
    assert (
        provider.conn.closed
        or provider.conn.info.transaction_status is TransactionStatus.IDLE
    )
    assert isinstance(provider.completions, _Completions)
    assert provider.completions.prompts == []
    monkeypatch.undo()
    with connect(dsn) as observer:
        assert observer.execute("SELECT count(*) FROM budget_ledger").fetchone() == (0,)
