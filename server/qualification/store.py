"""Append-only persisted qualification evidence and authenticated verdicts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

import psycopg

from server.qualification.harness import Performed, PerformedSet, PreparedCase
from server.qualification.matrix import MatrixRow
from server.qualification.verdict import Verdict, read_verdict
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection


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


def _answered(row: MatrixRow) -> bool:
    """Whether this row is a result a reviewer could sign QUALIFIED over.

    Every key the case declared has to be answered, and a case may declare
    three kinds: expected citations, an expected refusal, and an expected
    forecast. `forecast_met` is `None` when no forecast was declared and a
    bool when one was, so `is not False` is the test -- a case keyed only by a
    forecast (which `assert_measurable` allows) was otherwise signable with
    that forecast unmet, because nothing here read the field.
    """
    if row.forecast_met is False or row.ready_met is False:
        return False
    if row.expected_refusal_met is not None:
        return row.expected_refusal_met
    return row.proven and not row.missed


@dataclass(frozen=True, slots=True)
class PerformedEvidence:
    """The immutable host snapshot a reviewer may sign, never a detached hash."""

    prepared: tuple[PreparedCase, ...]
    performed: PerformedSet

    @property
    def document(self) -> dict[str, object]:
        return {
            "prepared": [_prepared_document(item) for item in self.prepared],
            "performed": [
                _performed_document(item) for item in self.performed.performed
            ],
            "matrix": _matrix_document(self.performed),
        }

    @property
    def performed_sha256(self) -> str:
        return _digest(self.document)

    @property
    def complete(self) -> bool:
        """A matrix over runs that finished and answered their keys.

        A matrix alone is not enough. `Assurance` has one reviewer-written
        member, `QUALIFIED`, so a snapshot worth signing is one that could
        carry that word: every run reached `COMPLETE`, and every row either
        met the refusal its case declared or proved every expected citation.
        A run that validly returns a blocked readiness handoff stops with
        nothing in `stopped` and still builds a matrix — rows unproven, every
        key missed — which is the shape both live runs so far have taken, and
        exactly what must not be signable.
        """
        matrix = self.performed.matrix
        if matrix is None:
            return False
        if any(
            record.status is not RunStatus.COMPLETE
            for record in self.performed.performed
        ):
            return False
        return all(_answered(row) for row in matrix.rows)

    @property
    def evidence(self) -> Evidence:
        set_sha256, build_id, adapter_version, provider, model = _identity(
            self.prepared, self.performed
        )
        return Evidence(
            set_sha256,
            self.performed_sha256,
            build_id,
            adapter_version,
            provider,
            model,
        )


def performed_evidence(
    *, prepared: tuple[PreparedCase, ...], performed: PerformedSet
) -> PerformedEvidence:
    """Bind a returned performed set to the exact pins that produced it."""
    _identity(prepared, performed)
    return PerformedEvidence(prepared, performed)


def record_performed(conn: StoreConnection, performed: PerformedEvidence) -> str:
    """Persist one immutable performed snapshot before its evidence is recorded."""
    evidence = performed.evidence
    document = performed.document
    digest = evidence.performed_sha256
    conn.execute(
        "INSERT INTO qualification_performed"
        " (performed_sha256,qualification_set_sha256,build_id,adapter_version,"
        " provider,model,complete,performed_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        " ON CONFLICT (performed_sha256) DO NOTHING",
        (
            digest,
            evidence.qualification_set_sha256,
            evidence.build_id,
            evidence.adapter_version,
            evidence.provider,
            evidence.model,
            performed.complete,
            json.dumps(document, sort_keys=True, separators=(",", ":")),
        ),
    )
    row = conn.execute(
        "SELECT qualification_set_sha256,build_id,adapter_version,provider,model,"
        " complete,performed_json FROM qualification_performed"
        " WHERE performed_sha256=%s",
        (digest,),
    ).fetchone()
    if row != (
        evidence.qualification_set_sha256,
        evidence.build_id,
        evidence.adapter_version,
        evidence.provider,
        evidence.model,
        performed.complete,
        document,
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    return digest


def record_evidence(conn: StoreConnection, evidence: Evidence) -> str:
    """Persist exactly one identity row; a conflicting replay refuses."""
    performed = conn.execute(
        "SELECT qualification_set_sha256,build_id,adapter_version,provider,model"
        " FROM qualification_performed WHERE performed_sha256=%s",
        (evidence.performed_sha256,),
    ).fetchone()
    if performed != (
        evidence.qualification_set_sha256,
        evidence.build_id,
        evidence.adapter_version,
        evidence.provider,
        evidence.model,
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
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


def evidence_at(conn: StoreConnection, *, evidence_sha256: str) -> Evidence | None:
    """Return the exact stored evidence identity, never a similar candidate."""
    row = conn.execute(
        "SELECT e.qualification_set_sha256,e.performed_sha256,e.build_id,"
        " e.adapter_version,e.provider,e.model FROM qualification_evidence e"
        " JOIN qualification_performed p ON p.performed_sha256=e.performed_sha256"
        " AND (p.qualification_set_sha256,p.build_id,p.adapter_version,"
        " p.provider,p.model)=(e.qualification_set_sha256,e.build_id,"
        " e.adapter_version,e.provider,e.model)"
        " WHERE e.evidence_sha256=%s",
        (evidence_sha256,),
    ).fetchone()
    if row is None:
        return None
    evidence = Evidence(*row)
    if evidence.sha256 != evidence_sha256:
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    return evidence


def _identity(
    prepared: tuple[PreparedCase, ...], performed: PerformedSet
) -> tuple[str, str, str, str, str]:
    """The single identity used by both the snapshot and its evidence row."""
    if (
        type(prepared) is not tuple
        or not prepared
        or type(performed) is not PerformedSet
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    first = prepared[0]
    if any(type(item) is not PreparedCase for item in prepared):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    identity = (
        first.qualification_set_sha256,
        first.input.build_id,
        first.input.adapter_version,
        first.provider,
        first.model,
    )
    if any(
        (
            item.qualification_set_sha256,
            item.input.build_id,
            item.input.adapter_version,
            item.provider,
            item.model,
        )
        != identity
        for item in prepared
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    records = performed.performed
    if len(records) > len(prepared) or any(
        (record.case_label, record.run_id) != (item.case_label, item.input.run_id)
        for record, item in zip(records, prepared, strict=False)
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    matrix = performed.matrix
    if matrix is not None and (
        len(records) != len(prepared)
        or any(record.stopped is not None for record in records)
        or matrix.qualification_set_sha256 != identity[0]
        or matrix.build_id != identity[1]
        or [row.case_label for row in matrix.rows]
        != [item.case_label for item in prepared]
    ):
        raise Refusal(RefusalCode.VERDICT_BINDING_INVALID)
    return identity


def _prepared_document(item: PreparedCase) -> dict[str, object]:
    pin = item.input
    return {
        "case_label": item.case_label,
        "run_id": str(pin.run_id),
        "case_id": str(pin.case_id),
        "source_version": pin.source_version,
        "source_fingerprint": pin.source_fingerprint,
        "route_digest": pin.route_digest,
        "build_id": pin.build_id,
        "manifest_sha256": pin.manifest_sha256,
        "adapter_version": pin.adapter_version,
        "input_fingerprint": pin.input_fingerprint,
        "subject": None
        if pin.subject is None
        else {
            "issuer_id": pin.subject.issuer_id,
            "issuer_name": pin.subject.issuer_name,
            "reporting_period": pin.subject.reporting_period,
            "analysis_date": pin.subject.analysis_date,
        },
        "cos_run_id": pin.cos_run_id,
    }


def _performed_document(item: Performed) -> dict[str, object]:
    proof = item.proof
    return {
        "case_label": item.case_label,
        "run_id": str(item.run_id),
        "status": item.status.value,
        "stopped": None if item.stopped is None else item.stopped.value,
        "proof": None
        if proof is None
        else {
            "run_id": str(proof.run_id),
            "route_digest": proof.route_digest,
            "build_id": proof.build_id,
            "artifacts": proof.artifacts,
            "citations": proof.citations,
            "anchored": [list(value) for value in sorted(proof.anchored)],
        },
        "refusal": None if item.refusal is None else item.refusal.value,
        "unrun": [
            {
                "route_node_id": unrun.route_node_id,
                "state": unrun.state.value,
                "attempts": [
                    {
                        "attempt_id": str(attempt.attempt_id),
                        "reserved": attempt.reserved,
                        "outcome": attempt.outcome,
                        "charged": attempt.charged,
                        "model": attempt.model,
                        "generation_id": attempt.generation_id,
                    }
                    for attempt in unrun.attempts
                ],
            }
            for unrun in item.unrun
        ],
    }


def _matrix_document(performed: PerformedSet) -> dict[str, object] | None:
    matrix = performed.matrix
    if matrix is None:
        return None
    return {
        "qualification_set_sha256": matrix.qualification_set_sha256,
        "build_id": matrix.build_id,
        "rows": [
            {
                "case_label": row.case_label,
                "proven": row.proven,
                "refusal": None if row.refusal is None else row.refusal.value,
                "met": [
                    [
                        citation.module_id,
                        citation.document_sha256,
                        citation.matched_text,
                    ]
                    for citation in row.met
                ],
                "missed": [
                    [
                        citation.module_id,
                        citation.document_sha256,
                        citation.matched_text,
                    ]
                    for citation in row.missed
                ],
                "forecast_met": row.forecast_met,
                "expected_refusal_met": row.expected_refusal_met,
            }
            for row in matrix.rows
        ],
    }


def _digest(document: dict[str, object]) -> str:
    return sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    complete = conn.execute(
        "SELECT complete FROM qualification_performed WHERE performed_sha256=%s",
        (evidence.performed_sha256,),
    ).fetchone()
    if complete != (True,):
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
    now: datetime,
) -> Verdict:
    """Read only the current verdict bound to the exact requested evidence."""
    row = conn.execute(
        "SELECT q.reviewer,q.decided_at,q.expires_at,e.qualification_set_sha256,"
        " e.build_id,e.provider,e.model FROM qualification_verdicts q"
        " JOIN qualification_evidence e USING (evidence_sha256)"
        " JOIN qualification_performed p ON p.performed_sha256=e.performed_sha256"
        " AND (p.qualification_set_sha256,p.build_id,p.adapter_version,"
        " p.provider,p.model)=(e.qualification_set_sha256,e.build_id,"
        " e.adapter_version,e.provider,e.model)"
        " WHERE q.evidence_sha256=%s AND p.complete",
        (evidence.sha256,),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.VERDICT_INCOMPLETE)
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
