from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from server.qualification.store import (
    Evidence,
    current_verdict,
    record_evidence,
    record_verdict,
)
from server.qualification.verdict import Verdict, read_verdict
from server.refusals import Refusal
from server.store import apply_schema, connect


def _evidence() -> Evidence:
    return Evidence("a" * 64, "b" * 64, "build", "adapter", "openrouter", "model")


def _verdict(now: datetime) -> Verdict:
    return read_verdict(
        {
            "provider": "openrouter:model",
            "qualification_set_sha256": "a" * 64,
            "build_id": "build",
            "decided_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "reviewer": "Reviewer",
        },
        now=now,
    )


def test_record_evidence_is_idempotent_and_bound(empty_database: str) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        evidence = _evidence()
        assert record_evidence(conn, evidence) == evidence.sha256
        assert record_evidence(conn, evidence) == evidence.sha256
        conn.rollback()


def test_record_verdict_binds_the_reviewer_and_evidence(empty_database: str) -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    with connect(empty_database) as conn:
        apply_schema(conn)
        evidence = _evidence()
        reviewer = uuid4()
        record_verdict(
            conn, evidence=evidence, reviewer_id=reviewer, verdict=_verdict(now)
        )
        assert current_verdict(conn, evidence=evidence, reviewer_id=reviewer, now=now)
        with pytest.raises(Refusal):
            current_verdict(conn, evidence=evidence, reviewer_id=uuid4(), now=now)
