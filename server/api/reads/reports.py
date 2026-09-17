"""Exact saved Report and frozen/filed Committee reads; no write authority."""

import json
from hashlib import sha256
from typing import Any
from uuid import UUID

from fastapi import APIRouter

from server.api.commands.availability import FilingFacts, report_actions
from server.api.deps import (
    Blobs,
    Caller,
    CasePath,
    Methodology,
    RevisionQuery,
    RunQuery,
    Store,
    readable,
)
from server.api.wire import CommitteeDocument, ReportDocument
from server.deliverable.filing import revision_signatures
from server.deliverable.receipts import read_filed_receipt
from server.deliverable.revisions import prove_revision, read_revision
from server.refusals import Refusal, RefusalCode
from server.store.audit import audit_head, audit_trail, verify_chain
from server.store.commands import payload_digests
from server.store.members import standing_of
from server.store.outcomes import execution_reads

# Three-node LITE: isolation/standing/selection (3), live proof (40). No lock:
# a read takes none, and the payload digest below is the consistency check.
# Committee adds publication/signatures (2) and three actor/audit proof reads.
# Filed Committee also adds receipt/audit (5) and saved payload (1).
# Task 12.1 adds two to each: the publication row and the signatures the
# section's four filing actions are judged from. Proving a filing act costs one
# more read per actor it looks for -- the receipts that actor committed on this
# case, which is how an event written by a command is rebuilt (`payload_digests`)
# -- so a frozen revision pays two, one signer and its freezer, and a filed one
# pays a third for its filer.
# The figures below are therefore stated **for one signer**, which is the only
# shape any fixture has and no longer the only shape the store allows: the
# opinions table is keyed per signer and `sign_opinion_in` refuses only a frozen
# revision, so a second approver may sign before the freeze and costs one more
# read. Measured at 53 for the frozen path with two signers. Recorded in
# CLAUDE.md rather than absorbed into the number, because a budget fitted to the
# widest shape stops measuring the common one.
IO_BUDGET = {"report": 45, "committee": 59, "frozen": 52}
router = APIRouter()


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
        # Read inside the unit rather than as `VisibleCase`: `execution_reads`
        # adopts no transaction already open, and a standing read before it
        # would be one.
        standing = readable(standing_of(conn, case_id=case_id, user_id=actor.user_id))
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
        return dict(
            chrome=dict(
                subject=dict(case_id=case_id, title=payload["case_title"]),
                served_role=dict(global_role=actor.role, standing=standing),
                actions=report_actions(
                    actor.role, standing, _filing_facts(conn, case_id, revision, actor)
                ),
            ),
            body={**_body(payload, digest), **publication},
            observed_at=observed_at,
            observed_empty=False,
            status="complete",
            notes=[],
        )


def _filing_facts(
    conn: Store, case_id: UUID, revision: UUID, actor: Caller
) -> FilingFacts:
    """What the section can say about this revision's filing, and no more.

    Deliberately not `_publication`: that one proves the chain and refuses a
    revision that is not frozen, which is the state the sign and freeze
    controls exist for. Availability grants nothing, so it reads the two rows
    and judges from them.
    """
    row = conn.execute(
        "SELECT frozen_by,filed_by FROM deliverable_publications"
        " WHERE case_id=%s AND revision_id=%s",
        (case_id, str(revision)),
    ).fetchone()
    signers = {who for who, _ in revision_signatures(conn, case_id, revision)}
    frozen_by = None if row is None else UUID(str(row[0]))
    return FilingFacts(
        signed=bool(signers),
        frozen=row is not None,
        filed=row is not None and row[1] is not None,
        actor_signed=actor.user_id in signers,
        actor_froze=actor.user_id == frozen_by,
    )


def _publication(
    conn: Store, case_id: UUID, revision: UUID, digest: str
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT p.payload_sha256,frozen_by,filed_by,filed_at,"
        " c.receipt_sha256 IS NOT NULL OR EXISTS (SELECT 1 FROM audit_events e"
        " LEFT JOIN deliverable_receipts r ON r.case_id=e.case_id"
        " AND r.filed_event_sha256=e.entry_sha256 WHERE e.case_id=p.case_id"
        " AND e.action='DELIVERABLE_FILED' AND r.revision_id IS NULL"
        " AND NOT EXISTS (SELECT 1 FROM legacy_filing_events l"
        " WHERE l.case_id=e.case_id AND l.filed_event_sha256=e.entry_sha256))"
        " FROM deliverable_publications p LEFT JOIN deliverable_receipts c"
        " USING (case_id,revision_id)"
        " WHERE case_id=%s AND revision_id=%s",
        (case_id, str(revision)),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.DELIVERABLE_NOT_FROZEN)
    frozen_digest, freezer, filer, filed_at, filing_evidence = row
    signatures = revision_signatures(conn, case_id, revision)
    signers = [who for who, _ in signatures]
    if (
        frozen_digest != digest
        or not signers
        or freezer in signers
        or any(signed != digest for _, signed in signatures)
        or (filer is None) != (filed_at is None)
        or (filer is None and filing_evidence)
    ):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    bound = {"revision_id": str(revision), "payload_sha256": digest}
    trail = audit_trail(conn, case_id)
    required = {("OPINION_SIGNED", who) for who in signers}
    required.add(("DELIVERABLE_FROZEN", freezer))
    # One act, two possible writers: a store function called directly binds the
    # payload as given, a command's envelope adds its request digest. Both are
    # rebuilt exactly, so neither comparison is looser than the other. Read once
    # per actor this read is looking for rather than once per entry of a trail
    # that is the whole case's: only these actors' events can satisfy `required`.
    accepted = {
        actor: payload_digests(conn, scope=case_id, actor_id=actor, payload=bound)
        for _action, actor in required
    }
    events = {
        (entry.action, entry.actor_id)
        for entry in trail
        if entry.payload_sha256 in accepted.get(entry.actor_id, frozenset())
    }
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
