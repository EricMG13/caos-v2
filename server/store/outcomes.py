"""One immutable call outcome; known spend lives only in the original ledger."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, rollback_or_close
from server.store.budget import reserved_for, validate_spend
from server.store.events import RunEvent, append, lock_run


def require_idle(conn: StoreConnection) -> None:
    """Execution never adopts an active caller transaction, even read-only."""
    if conn.autocommit or conn.info.transaction_status is not TransactionStatus.IDLE:
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)


@contextmanager
def execution_reads(conn: StoreConnection) -> Iterator[None]:
    """Own one bounded execution read unit; no transport inside this scope."""
    require_idle(conn)  # Outside cleanup: pending caller writes remain untouched.
    try:
        _read_committed(conn)
        yield
        conn.rollback()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise


def _read_committed(conn: StoreConnection) -> None:
    if conn.execute("SHOW transaction_isolation").fetchone() != ("read committed",):
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)


def check_attempt(
    conn: StoreConnection, *, attempt_id: UUID, run_id: UUID, route_node_id: str
) -> None:
    """Require the attempt's current run/node identity and RUNNING owner."""
    if not isinstance(attempt_id, UUID) or conn.execute(
        "SELECT run_id,route_node_id FROM run_attempts WHERE attempt_id=%s",
        (attempt_id,),
    ).fetchone() != (run_id, route_node_id):
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    owner, _case, status = _locked_attempt(conn, attempt_id)
    if owner != run_id or conn.execute(
        "SELECT route_node_id FROM run_attempts WHERE attempt_id=%s AND run_id=%s",
        (attempt_id, run_id),
    ).fetchone() != (route_node_id,):
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    if status is not RunStatus.RUNNING:
        raise Refusal(RefusalCode.RUN_NOT_RUNNING)


def check_call(
    conn: StoreConnection, *, attempt_id: UUID, run_id: UUID, route_node_id: str
) -> None:
    """Require this unused reserved attempt. Caller owns the read transaction.

    Absence checks are not a concurrent call claim or crash/retry certainty.
    """
    check_attempt(
        conn,
        attempt_id=attempt_id,
        run_id=run_id,
        route_node_id=route_node_id,
    )
    if reserved_for(conn, attempt_id) is None:
        raise Refusal(RefusalCode.BUDGET_NOT_RESERVED)
    if conn.execute(
        "SELECT 1 FROM call_outcomes WHERE attempt_id=%s", (attempt_id,)
    ).fetchone():
        raise Refusal(RefusalCode.CALL_OUTCOME_CONFLICT)
    if conn.execute(
        "SELECT 1 FROM budget_ledger WHERE attempt_id=%s"
        " UNION ALL SELECT 1 FROM artifacts WHERE attempt_id=%s",
        (attempt_id, attempt_id),
    ).fetchone():
        raise Refusal(RefusalCode.CALL_OUTCOME_LEGACY)


@dataclass(frozen=True, slots=True)
class CallOutcome:
    """None is unknown, including spend. Diagnostic bytes, when available,
    belong in a bounded blob; only its address belongs here. Model is the
    host's configured identifier; generation_id is the provider's handle.
    """

    charge: Decimal | None
    model: str | None
    generation_id: str | None
    diagnostic_sha256: str | None = None


def record_outcome(
    conn: StoreConnection, *, attempt_id: UUID, outcome: CallOutcome
) -> bool:
    """Commit outcome/known charge/event even after termination; never analysis.

    Owns the caller transaction. Exact replay is a no-op; conflicts and legacy
    rows refuse. Unknown outcomes remain immutable, with no backfill.
    """
    try:
        inserted = _record(conn, attempt_id, outcome)
        conn.commit()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    return inserted


def _record(conn: StoreConnection, attempt: UUID, outcome: CallOutcome) -> bool:
    run, _case, _status = _locked_attempt(conn, attempt)
    row = conn.execute(
        "SELECT l.amount, o.model, o.generation_id, o.diagnostic_sha256"
        " FROM call_outcomes o LEFT JOIN budget_ledger l"
        " ON (l.run_id,l.attempt_id) = (o.run_id,o.charged_attempt_id)"
        " WHERE o.attempt_id = %s",
        (attempt,),
    ).fetchone()
    if row is None:
        if conn.execute(
            "SELECT attempt_id FROM budget_ledger WHERE attempt_id = %s"
            " UNION ALL SELECT attempt_id FROM artifacts WHERE attempt_id = %s",
            (attempt, attempt),
        ).fetchone():
            raise Refusal(RefusalCode.CALL_OUTCOME_LEGACY)
    _validate(outcome)
    if row is not None:
        if row != (
            outcome.charge,
            outcome.model,
            outcome.generation_id,
            outcome.diagnostic_sha256,
        ):
            raise Refusal(RefusalCode.CALL_OUTCOME_CONFLICT)
        return False
    if outcome.charge is not None:
        conn.execute(
            "INSERT INTO budget_ledger (attempt_id,run_id,amount) VALUES (%s,%s,%s)",
            (attempt, run, outcome.charge),
        )
    conn.execute(
        "INSERT INTO call_outcomes (attempt_id,run_id,charged_attempt_id,model,"
        " generation_id,diagnostic_sha256) VALUES (%s,%s,%s,%s,%s,%s)",
        (
            attempt,
            run,
            attempt if outcome.charge is not None else None,
            outcome.model,
            outcome.generation_id,
            outcome.diagnostic_sha256,
        ),
    )
    append(conn, run, RunEvent.CALL_OUTCOME_RECORDED)
    return True


def producer_identifier(value: object, *, limit: int) -> str | None:
    """An exact producer identifier, or unknown; never coerce response fields."""
    if (
        isinstance(value, str)
        and len(value) <= limit
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]*", value) is not None
    ):
        return value
    return None


def _validate(outcome: CallOutcome) -> None:
    if not isinstance(outcome, CallOutcome):
        raise Refusal(RefusalCode.CALL_OUTCOME_INVALID)
    if outcome.charge is not None:
        validate_spend(outcome.charge)
    for value, limit in ((outcome.model, 256), (outcome.generation_id, 512)):
        if value is not None and producer_identifier(value, limit=limit) is None:
            raise Refusal(RefusalCode.CALL_OUTCOME_INVALID)
    digest = outcome.diagnostic_sha256
    if digest is not None and (
        not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise Refusal(RefusalCode.CALL_OUTCOME_INVALID)


def _attempt_owner(conn: StoreConnection, attempt_id: UUID) -> tuple[UUID, UUID]:
    if not isinstance(attempt_id, UUID):
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    row = conn.execute(
        "SELECT attempts.run_id, runs.case_id FROM run_attempts AS attempts"
        " JOIN runs USING (run_id) WHERE attempts.attempt_id = %s",
        (attempt_id,),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    return row[0], row[1]


def _locked_attempt(
    conn: StoreConnection, attempt_id: UUID
) -> tuple[UUID, UUID, RunStatus]:
    run, case = _attempt_owner(conn, attempt_id)
    status = lock_run(conn, run)
    if (
        conn.execute(
            "SELECT 1 FROM run_attempts WHERE attempt_id = %s AND run_id = %s"
            " FOR KEY SHARE",
            (attempt_id, run),
        ).fetchone()
        is None
    ):
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    return run, case, status
