"""Provider facts commit before analytical refusal, acceptance or cleanup."""

import http.client
import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import psycopg
import pytest
from conftest import _url_for
from psycopg.pq import TransactionStatus
from test_call_outcomes import _counts
from test_execution_attempts import _invoke, _Transport, _wire, provider, ready, route
from test_loop_charges import ESTIMATE, MODEL, REPORTED, _Completions

from server.blobs import BlobStore
from server.evidence.citations import AnchoredCitation, Citation, verify_citations
from server.methodology import executor
from server.methodology.runner import ModuleProvider
from server.provider import MAX_RESPONSE_BYTES, Completion, OpenRouter
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, connect
from server.store.outcomes import CallOutcome, record_outcome
from server.store.runs import fail_run

__all__ = ["provider", "ready", "route"]


def _bill(
    dsn: str, run_id: UUID, charge: Decimal | None, *, status: str = "RUNNING"
) -> UUID:
    with connect(dsn) as observer:
        rows = observer.execute(
            "SELECT o.attempt_id,o.run_id,l.amount,r.amount FROM call_outcomes o"
            " LEFT JOIN budget_ledger l USING (attempt_id,run_id)"
            " JOIN budget_reservations r USING (attempt_id,run_id)"
        ).fetchall()
        assert len(rows) == 1
        attempt, run, amount, reserved = rows[0]
        assert (run, amount, reserved) == (run_id, charge, ESTIMATE)
        expected = 0 if charge is None else 1
        assert observer.execute("SELECT count(*) FROM budget_ledger").fetchone() == (
            expected,
        )
        assert observer.execute("SELECT count(*) FROM artifacts").fetchone() == (0,)
        assert observer.execute("SELECT status FROM runs").fetchone() == (status,)
        assert observer.execute(
            "SELECT name FROM run_events WHERE name IN"
            " ('CALL_OUTCOME_RECORDED','ATTEMPT_ACCEPTED','RUN_COMPLETE')"
        ).fetchall() == [("CALL_OUTCOME_RECORDED",)]
        assert isinstance(attempt, UUID)
        return attempt


@pytest.mark.parametrize(
    "response,code,charge",
    [
        ((200, _wire()), "PROVIDER_OUTPUT_TRUNCATED", Decimal("0.25")),
        ((200, _wire("content_filter")), "PROVIDER_REFUSED", Decimal("0.25")),
        ((402, _wire()), "PROVIDER_CALL_INVALID", Decimal("0.25")),
        ((503, _wire()), "PROVIDER_UNAVAILABLE", Decimal("0.25")),
        ((200, _wire("stop")), "ENVELOPE_INVALID", Decimal("0.25")),
        ((200, _wire(cost="0")), "PROVIDER_OUTPUT_TRUNCATED", Decimal("0")),
        ((200, _wire(identity="{}")), "PROVIDER_OUTPUT_TRUNCATED", Decimal("0.25")),
        ((200, _wire(cost="true")), "PROVIDER_OUTPUT_TRUNCATED", None),
        ((200, _wire(cost="null")), "PROVIDER_OUTPUT_TRUNCATED", None),
        ((200, _wire(cost="-1")), "PROVIDER_OUTPUT_TRUNCATED", None),
        ((200, _wire(cost="NaN")), "PROVIDER_OUTPUT_TRUNCATED", None),
        ((200, _wire(cost='"0.25"')), "PROVIDER_OUTPUT_TRUNCATED", None),
        ((200, _wire(cost='0.25,"cost":0.25')), "PROVIDER_OUTPUT_TRUNCATED", None),
        (
            (200, _wire(cost="1e9999999999999999999999999")),
            "PROVIDER_RESPONSE_INVALID",
            None,
        ),
        ((200, b"private"), "PROVIDER_RESPONSE_INVALID", None),
        ((200, b"x" * (MAX_RESPONSE_BYTES + 1)), "PROVIDER_RESPONSE_INVALID", None),
        (TimeoutError("private"), "PROVIDER_UNAVAILABLE", None),
        (http.client.IncompleteRead(b"private"), "PROVIDER_UNAVAILABLE", None),
    ],
)
def test_native_refusal_records_only_independently_known_money(
    provider: ModuleProvider,
    response: tuple[int, bytes] | Exception,
    code: str,
    charge: Decimal | None,
) -> None:
    transport = _Transport(provider.conn, response)
    provider = replace(
        provider, completions=OpenRouter("offline", MODEL, transport=transport)
    )
    with pytest.raises(Refusal, match=f"^{code}$") as caught:
        _invoke(provider, uuid4(), "runtime", provider.route.nodes[0])
    assert "private" not in str(caught.value) + repr(caught.value)
    assert caught.value.__cause__ is None
    assert transport.calls == 1
    assert provider.conn.info.transaction_status is TransactionStatus.IDLE
    _bill(_url_for(provider.conn.info.dbname), provider.run_id, charge)


@pytest.mark.parametrize("failure", ["envelope", "readiness", "citation", "blob"])
def test_analysis_failure_preserves_bill_and_exact_replay(
    provider: ModuleProvider,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    original = provider.completions.complete

    def complete(prompt: str, *, json_object: bool = False) -> Completion:
        result = original(prompt, json_object=json_object)
        if failure == "envelope":
            return replace(result, content="private")
        body = json.loads(result.content or "")
        if failure == "readiness":
            body.pop("content_to_module_map")
        elif failure == "citation":
            body["claims"][0]["citations"][0]["source_id"] = str(uuid4())
        return replace(result, content=json.dumps(body))

    def broken_blob(self: BlobStore, data: bytes) -> str:
        raise OSError("synthetic")

    monkeypatch.setattr(provider.completions, "complete", complete)
    if failure == "blob":
        monkeypatch.setattr(BlobStore, "put", broken_blob)
    codes = {
        "envelope": "ENVELOPE_INVALID",
        "readiness": "READINESS_INCOMPLETE",
        "citation": "CITATION_NOT_DELIVERED",
    }
    with pytest.raises(OSError if failure == "blob" else Refusal) as caught:
        _invoke(provider, uuid4(), "runtime", provider.route.nodes[0])
    assert str(caught.value) == codes.get(failure, "synthetic")
    assert provider.conn.info.transaction_status is TransactionStatus.IDLE
    dsn = _url_for(provider.conn.info.dbname)
    attempt = _bill(dsn, provider.run_id, REPORTED)
    facts = CallOutcome(REPORTED, MODEL, "gen-loop-test")
    assert not record_outcome(provider.conn, attempt_id=attempt, outcome=facts)
    with pytest.raises(Refusal, match=r"^CALL_OUTCOME_CONFLICT$"):
        record_outcome(
            provider.conn, attempt_id=attempt, outcome=replace(facts, charge=None)
        )
    with pytest.raises(Refusal, match=r"^CALL_OUTCOME_CONFLICT$"):
        _invoke(provider, attempt, "module", provider.route.nodes[0])
    assert isinstance(provider.completions, _Completions)
    assert len(provider.completions.prompts) == 1
    assert _bill(dsn, provider.run_id, REPORTED) == attempt


@pytest.mark.parametrize(
    "failure,broken_cleanup,code",
    [
        ("sql", False, "STORE_UNAVAILABLE"),
        ("sql", True, "STORE_UNAVAILABLE"),
        ("refusal", False, "CITATION_NOT_DELIVERED"),
        ("refusal", True, "CITATION_NOT_DELIVERED"),
        ("success", True, "STORE_UNAVAILABLE"),
    ],
)
def test_postbilling_citation_cleanup_preserves_money_and_original_refusal(
    provider: ModuleProvider,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    broken_cleanup: bool,
    code: str,
) -> None:
    dsn = _url_for(provider.conn.info.dbname)

    def broken(conn: StoreConnection) -> None:
        raise psycopg.OperationalError("private")

    def fault(
        conn: StoreConnection, *, delivered: set[UUID], citations: Sequence[Citation]
    ) -> list[AnchoredCitation]:
        anchored = verify_citations(conn, delivered=delivered, citations=citations)
        if broken_cleanup:
            monkeypatch.setattr(psycopg.Connection, "rollback", broken)
        if failure == "sql":
            conn.execute("SELECT missing_private_column")
        elif failure == "refusal":
            raise Refusal(RefusalCode.CITATION_NOT_DELIVERED)
        return anchored

    monkeypatch.setattr(executor, "verify_citations", fault)
    with pytest.raises(Refusal, match=f"^{code}$") as caught:
        _invoke(provider, uuid4(), "runtime", provider.route.nodes[0])
    assert caught.value.__cause__ is None
    assert (
        provider.conn.closed
        or provider.conn.info.transaction_status is TransactionStatus.IDLE
    )
    assert isinstance(provider.completions, _Completions)
    assert len(provider.completions.prompts) == 1
    monkeypatch.undo()
    _bill(dsn, provider.run_id, REPORTED)


@pytest.mark.parametrize("broken_cleanup", [False, True])
def test_failed_outcome_persistence_refuses_before_blob_storage(
    provider: ModuleProvider,
    monkeypatch: pytest.MonkeyPatch,
    broken_cleanup: bool,
) -> None:
    dsn = _url_for(provider.conn.info.dbname)
    provider.conn.execute("ALTER TABLE call_outcomes ADD CHECK (false)")
    provider.conn.commit()
    original = provider.completions.complete

    def broken(conn: StoreConnection) -> None:
        raise psycopg.OperationalError("private")

    def complete(prompt: str, *, json_object: bool = False) -> Completion:
        result = original(prompt, json_object=json_object)
        if broken_cleanup:
            monkeypatch.setattr(psycopg.Connection, "rollback", broken)
        return result

    def forbidden(self: BlobStore, data: bytes) -> str:
        pytest.fail("failed billing reached blob storage")

    monkeypatch.setattr(provider.completions, "complete", complete)
    monkeypatch.setattr(BlobStore, "put", forbidden)
    with pytest.raises(Refusal, match=r"^STORE_UNAVAILABLE$") as caught:
        _invoke(provider, uuid4(), "runtime", provider.route.nodes[0])
    assert caught.value.__cause__ is None
    assert provider.conn.closed is broken_cleanup
    assert (
        broken_cleanup
        or provider.conn.info.transaction_status is TransactionStatus.IDLE
    )
    assert isinstance(provider.completions, _Completions)
    assert len(provider.completions.prompts) == 1
    monkeypatch.undo()
    with connect(dsn) as observer:
        assert _counts(observer) == (0, 0, 0)
        assert observer.execute(
            "SELECT amount FROM budget_reservations"
        ).fetchall() == [(ESTIMATE,)]
        assert observer.execute("SELECT status FROM runs").fetchone() == ("RUNNING",)


def test_late_known_refusal_is_billed_after_inflight_run_cancellation(
    provider: ModuleProvider,
) -> None:
    dsn = _url_for(provider.conn.info.dbname)

    class _CancelledTransport(_Transport):
        def post(
            self, url: str, body: bytes, headers: Mapping[str, str], timeout: float
        ) -> tuple[int, bytes]:
            response = super().post(url, body, headers, timeout)
            with connect(dsn) as cancellation:
                cancellation.execute("SET lock_timeout = '1s'")
                assert fail_run(cancellation, provider.run_id)
            return response

    transport = _CancelledTransport(provider.conn, (200, _wire()))
    provider = replace(
        provider, completions=OpenRouter("offline", MODEL, transport=transport)
    )
    with pytest.raises(Refusal, match=r"^PROVIDER_OUTPUT_TRUNCATED$"):
        _invoke(provider, uuid4(), "runtime", provider.route.nodes[0])
    assert transport.calls == 1
    assert provider.conn.info.transaction_status is TransactionStatus.IDLE
    _bill(dsn, provider.run_id, Decimal("0.25"), status="FAILED")
