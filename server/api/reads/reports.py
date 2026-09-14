"""Exact saved Report and frozen/filed Committee reads; no write authority."""

import json
from hashlib import sha256
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from server.api.deps import Blobs, Caller, Methodology, Store
from server.api.reads.analysis import RunQuery
from server.api.reads.upload import READ_REQUIRES, CasePath
from server.api.wire import (
    Chrome,
    CommitteeBody,
    CommitteeDocument,
    ReportBody,
    ReportDocument,
    ServedRole,
    Subject,
)
from server.deliverable.filing import _signatures
from server.deliverable.receipts import read_filed_receipt
from server.deliverable.revisions import prove_revision, read_revision
from server.refusals import Refusal, RefusalCode
from server.store.audit import _digest_of, audit_head, audit_trail, verify_chain
from server.store.cases import lock_case
from server.store.members import satisfies, standing_of
from server.store.outcomes import execution_reads

# Three-node LITE: authorization/lock/selection (6), live proof (46).
# Committee adds publication/signatures (2) and three actor/audit proof reads.
# Filed Committee also adds receipt/audit (5) and saved payload (1).
IO_BUDGET = {"report": 52, "committee": 63, "frozen": 57}
router = APIRouter()


def revision_query(revision: str | None = None) -> UUID:
    try:
        return UUID(revision or "")
    except ValueError:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FOUND) from None


RevisionQuery = Annotated[UUID, Depends(revision_query)]


@router.get("/api/v1/cases/{case_id}/report", response_model=ReportDocument)
def read_report(  # noqa: PLR0913 -- caller and parsed selection precede stores
    actor: Caller,
    case_id: CasePath,
    run: RunQuery,
    revision: RevisionQuery,
    conn: Store,
    blobs: Blobs,
    bundle: Methodology,
) -> ReportDocument:
    return ReportDocument.model_validate(
        _read(actor, case_id, run, revision, conn, blobs, bundle, committee=False)
    )


@router.get("/api/v1/cases/{case_id}/committee", response_model=CommitteeDocument)
def read_committee(  # noqa: PLR0913 -- same selection, with frozen/receipt proof
    actor: Caller,
    case_id: CasePath,
    run: RunQuery,
    revision: RevisionQuery,
    conn: Store,
    blobs: Blobs,
    bundle: Methodology,
) -> CommitteeDocument:
    return CommitteeDocument.model_validate(
        _read(actor, case_id, run, revision, conn, blobs, bundle, committee=True)
    )


def _read(  # noqa: PLR0913 -- both documents share one authorization/proof unit
    actor: Caller,
    case_id: UUID,
    run: UUID | None,
    revision: UUID,
    conn: Store,
    blobs: Blobs,
    bundle: Methodology,
    *,
    committee: bool,
) -> dict[str, Any]:
    if run is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    with execution_reads(conn):
        if not satisfies(
            standing_of(conn, case_id=case_id, user_id=actor.user_id), READ_REQUIRES
        ):
            raise Refusal(RefusalCode.CASE_NOT_FOUND)
        lock_case(conn, case_id)
        standing = standing_of(conn, case_id=case_id, user_id=actor.user_id)
        if not satisfies(standing, READ_REQUIRES):
            raise Refusal(RefusalCode.CASE_NOT_FOUND)
        row = conn.execute(
            "SELECT payload_sha256,now() FROM deliverable_revisions"
            " WHERE case_id=%s AND run_id=%s AND revision_id=%s",
            (case_id, run, revision),
        ).fetchone()
        if row is None:
            raise Refusal(RefusalCode.DELIVERABLE_NOT_FOUND)
        digest, observed_at = row
        publication = _publication(conn, case_id, revision, digest) if committee else {}
        if publication.get("state") == "filed":
            publication["receipt"] = json.loads(
                read_filed_receipt(
                    conn,
                    blobs,
                    bundle,
                    case_id=case_id,
                    run_id=run,
                    revision_id=revision,
                )
            )
            payload = read_revision(conn, blobs, case_id=case_id, revision_id=revision)
        else:
            data = prove_revision(
                conn, blobs, bundle, case_id=case_id, revision_id=revision
            )
            if sha256(data).hexdigest() != digest:
                raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
            payload = json.loads(data)
        body = _body(payload, digest)
        return dict(
            chrome=Chrome(
                subject=Subject(case_id=case_id, title=payload["case_title"]),
                served_role=ServedRole(global_role=actor.role, standing=standing),
                actions=[],
            ),
            body=CommitteeBody(**body, **publication)
            if committee
            else ReportBody(**body),
            observed_at=observed_at,
            observed_empty=False,
            status="complete",
            notes=[],
        )


def _publication(
    conn: Store, case_id: UUID, revision: UUID, digest: str
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT p.payload_sha256,frozen_by,filed_by,filed_at,c.receipt_sha256"
        " FROM deliverable_publications p LEFT JOIN deliverable_receipts c"
        " USING (case_id,revision_id)"
        " WHERE case_id=%s AND revision_id=%s",
        (case_id, str(revision)),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FROZEN)
    frozen_digest, freezer, filer, filed_at, receipt_digest = row
    signatures = _signatures(conn, case_id, revision)
    signers = [who for who, _ in signatures]
    if (
        frozen_digest != digest
        or not signers
        or freezer in signers
        or any(signed != digest for _, signed in signatures)
        or (filer is None) != (filed_at is None)
        or (filer is None and receipt_digest is not None)
    ):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    bound = _digest_of({"revision_id": str(revision), "payload_sha256": digest})
    trail = audit_trail(conn, case_id)
    events = {(e.action, e.actor_id) for e in trail if e.payload_sha256 == bound}
    required = {("OPINION_SIGNED", who) for who in signers}
    required.add(("DELIVERABLE_FROZEN", freezer))
    if (
        not required <= events
        or not verify_chain(conn, case_id)
        or trail[-1].entry_sha256 != audit_head(conn, case_id)
    ):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    return dict(
        state="frozen" if filer is None else "filed",
        signed_by=signers,
        frozen_by=freezer,
        filed_by=filer,
        receipt=None,
    )


def _body(payload: dict[str, Any], digest: str) -> dict[str, Any]:
    artifacts = []
    for artifact in payload["artifacts"]:
        projections = json.loads(artifact["record"])["projections"]
        artifacts.append(dict(artifact))
        for key in (
            "qa_status",
            "committee_status",
            "decision_scope",
            "limitation_flags",
            "validation_warnings",
        ):
            artifacts[-1][key] = projections[key]
    return dict(
        case_id=payload["case_id"],
        displayed_run_id=payload["run_id"],
        revision_id=payload["revision_id"],
        payload_sha256=digest,
        case_title=payload["case_title"],
        artifacts=artifacts,
        narrative=[
            [
                dict(text=span.get("text"), figure=span.get("figure"))
                for span in paragraph
            ]
            for paragraph in payload["narrative"]
        ],
    )
