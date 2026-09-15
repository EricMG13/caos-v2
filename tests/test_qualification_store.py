from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from qualification_fixtures import qualification_performed

import server.store as store
from server.qualification.store import (
    Evidence,
    PerformedEvidence,
    current_verdict,
    evidence_at,
    performed_evidence,
    record_evidence,
    record_performed,
    record_verdict,
)
from server.qualification.verdict import Verdict, read_verdict
from server.refusals import Refusal
from server.store import RunStatus, apply_schema, connect


def _evidence() -> Evidence:
    return Evidence("a" * 64, "b" * 64, "build", "adapter", "openrouter", "model")


def _performed() -> PerformedEvidence:
    return qualification_performed()


def _verdict(now: datetime, evidence: Evidence) -> Verdict:
    return read_verdict(
        {
            "provider": evidence.provider + ":" + evidence.model,
            "qualification_set_sha256": evidence.qualification_set_sha256,
            "build_id": evidence.build_id,
            "decided_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "reviewer": "Reviewer",
        },
        now=now,
    )


def test_record_evidence_is_idempotent_and_bound(empty_database: str) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        evidence = _performed().evidence
        assert record_performed(conn, _performed()) == evidence.performed_sha256
        assert record_evidence(conn, evidence) == evidence.sha256
        assert record_evidence(conn, evidence) == evidence.sha256
        assert evidence_at(conn, evidence_sha256=evidence.sha256) == evidence
        assert evidence_at(conn, evidence_sha256="c" * 64) is None
        conn.rollback()


def test_a_detached_performed_hash_cannot_be_recorded(empty_database: str) -> None:
    with connect(empty_database) as conn:
        apply_schema(conn)
        with pytest.raises(Refusal, match=r"^VERDICT_BINDING_INVALID$"):
            record_evidence(conn, _evidence())


def test_a_legacy_verdict_without_a_snapshot_is_not_current(
    empty_database: str,
) -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    evidence = _evidence()
    verdict = _verdict(now, evidence)
    with connect(empty_database) as conn:
        with patch.object(store, "MIGRATIONS", store.MIGRATIONS[:-1]):
            apply_schema(conn)
        conn.execute(
            "INSERT INTO qualification_evidence"
            " (evidence_sha256,qualification_set_sha256,performed_sha256,build_id,"
            " adapter_version,provider,model) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (evidence.sha256, *asdict(evidence).values()),
        )
        conn.execute(
            "INSERT INTO qualification_verdicts"
            " (evidence_sha256,reviewer_id,reviewer,decided_at,expires_at)"
            " VALUES (%s,%s,%s,%s,%s)",
            (
                evidence.sha256,
                uuid4(),
                verdict.reviewer.value,
                verdict.decided_at,
                verdict.expires_at,
            ),
        )
        conn.commit()
        apply_schema(conn)

        with pytest.raises(Refusal, match=r"^VERDICT_INCOMPLETE$"):
            current_verdict(conn, evidence=evidence, now=now)


def test_a_snapshot_with_different_identity_cannot_back_a_legacy_verdict(
    empty_database: str,
) -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    performed = _performed()
    evidence = replace(performed.evidence, model="substituted-model")
    verdict = _verdict(now, evidence)
    with connect(empty_database) as conn:
        apply_schema(conn)
        record_performed(conn, performed)
        conn.execute(
            "INSERT INTO qualification_evidence"
            " (evidence_sha256,qualification_set_sha256,performed_sha256,build_id,"
            " adapter_version,provider,model) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (evidence.sha256, *asdict(evidence).values()),
        )
        conn.execute(
            "INSERT INTO qualification_verdicts"
            " (evidence_sha256,reviewer_id,reviewer,decided_at,expires_at)"
            " VALUES (%s,%s,%s,%s,%s)",
            (
                evidence.sha256,
                uuid4(),
                verdict.reviewer.value,
                verdict.decided_at,
                verdict.expires_at,
            ),
        )
        conn.commit()

        assert evidence_at(conn, evidence_sha256=evidence.sha256) is None
        with pytest.raises(Refusal, match=r"^VERDICT_INCOMPLETE$"):
            current_verdict(conn, evidence=evidence, now=now)


def test_performed_evidence_digest_changes_with_the_recorded_outcome() -> None:
    original = _performed()
    [record] = original.performed.performed
    changed = performed_evidence(
        prepared=original.prepared,
        performed=replace(
            original.performed,
            performed=(replace(record, status=RunStatus.FAILED),),
        ),
    )

    assert changed.evidence.performed_sha256 != original.evidence.performed_sha256


def test_an_incomplete_snapshot_cannot_receive_a_verdict(empty_database: str) -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    original = _performed()
    incomplete = performed_evidence(
        prepared=original.prepared,
        performed=replace(original.performed, matrix=None),
    )
    with connect(empty_database) as conn:
        apply_schema(conn)
        record_performed(conn, incomplete)
        with pytest.raises(Refusal, match=r"^VERDICT_BINDING_INVALID$"):
            record_verdict(
                conn,
                evidence=incomplete.evidence,
                reviewer_id=uuid4(),
                verdict=_verdict(now, incomplete.evidence),
            )


def test_record_verdict_binds_the_reviewer_and_evidence(empty_database: str) -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    with connect(empty_database) as conn:
        apply_schema(conn)
        performed = _performed()
        evidence = performed.evidence
        record_performed(conn, performed)
        reviewer = uuid4()
        record_verdict(
            conn,
            evidence=evidence,
            reviewer_id=reviewer,
            verdict=_verdict(now, evidence),
        )
        assert current_verdict(conn, evidence=evidence, now=now)
