"""Append-only persisted qualification evidence and authenticated verdicts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

import psycopg

from server.qualification.verdict import Verdict, read_verdict
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection


@dataclass(frozen=True, slots=True)
class Evidence:
    qualification_set_sha256: str
    performed_sha256: str
    build_id: str
    adapter_version: str
    provider: str
    model: str

    @property
    def sha256(self) -> str:
        return sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def record_evidence(conn: StoreConnection, evidence: Evidence) -> str:
    """Persist exactly one identity row; a conflicting replay refuses."""
    digest = evidence.sha256
    conn.execute(
        "INSERT INTO qualification_evidence"
        " (evidence_sha256,qualification_set_sha256,performed_sha256,build_id,"
        " adapter_version,provider,model) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        " ON CONFLICT (evidence_sha256) DO NOTHING",
        (digest, *asdict(evidence).values()),
    )
    row = conn.execute(
        "SELECT qualification_set_sha256,performed_sha256,build_id,adapter_version,"
        " provider,model FROM qualification_evidence WHERE evidence_sha256=%s",
        (digest,),
    ).fetchone()
    if row != tuple(asdict(evidence).values()):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    return digest


def record_verdict(
    conn: StoreConnection,
    *,
    evidence: Evidence,
    reviewer_id: UUID,
    verdict: Verdict,
) -> None:
    """Store one reviewer decision over already-persisted exact evidence."""
    if (
        verdict.qualification_set_sha256 != evidence.qualification_set_sha256
        or (verdict.provider.value != evidence.provider + ":" + evidence.model)
        or verdict.build_id != evidence.build_id
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    digest = record_evidence(conn, evidence)
    try:
        conn.execute(
            "INSERT INTO qualification_verdicts"
            " (evidence_sha256,reviewer_id,reviewer,decided_at,expires_at)"
            " VALUES (%s,%s,%s,%s,%s)",
            (
                digest,
                reviewer_id,
                verdict.reviewer.value,
                verdict.decided_at,
                verdict.expires_at,
            ),
        )
    except psycopg.Error:
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID) from None


def current_verdict(
    conn: StoreConnection,
    *,
    evidence: Evidence,
    reviewer_id: UUID,
    now: datetime,
) -> Verdict:
    """Read only the current verdict bound to the exact requested evidence."""
    row = conn.execute(
        "SELECT q.reviewer,q.decided_at,q.expires_at,e.qualification_set_sha256,"
        " e.build_id,e.provider,e.model FROM qualification_verdicts q"
        " JOIN qualification_evidence e USING (evidence_sha256)"
        " WHERE q.evidence_sha256=%s AND q.reviewer_id=%s",
        (evidence.sha256, reviewer_id),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    reviewer, decided_at, expires_at, set_digest, build_id, provider, model = row
    if (set_digest, build_id, provider, model) != (
        evidence.qualification_set_sha256,
        evidence.build_id,
        evidence.provider,
        evidence.model,
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    return read_verdict(
        {
            "provider": provider + ":" + model,
            "qualification_set_sha256": set_digest,
            "build_id": build_id,
            "decided_at": decided_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "reviewer": reviewer,
        },
        now=now,
    )
