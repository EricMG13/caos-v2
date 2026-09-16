"""The Analysis section read (Task 4.1, slice 4.1e).

Every accepted handoff of the displayed run, in route order, each read through
`accepted_handoff`: the record must bind its exact Markdown, the identity the
store rebuilds, this build and the accepted lineage, and nothing is re-anchored
(§42.4). Each is labelled per §46.3 -- `source_facts` are the host-verified
citations with withdrawal read live, `model_analysis` is the model's exact
Markdown, and `host_calculation` is `NONE`. A node without an accepted handoff
is listed as pending with its recomputed state and makes the document partial.
A run of another case, an unknown and a malformed run are one `RUN_NOT_FOUND`.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from server.api.reads.directory import SectionCaller, SectionStore
from server.api.reads.upload import READ_REQUIRES, CasePath
from server.api.wire import (
    AnalysisBody,
    AnalysisDocument,
    Chrome,
    CitationView,
    HandoffView,
    PendingNode,
    RectView,
    RunSubjectView,
    SectionNote,
    ServedRole,
    Subject,
)
from server.blobs import BlobStore
from server.deliverable.render import SCREENING_ONLY
from server.engine.route import NodeResult, NodeState, ResolvedRoute, node_states
from server.evidence.citations import AnchoredCitation
from server.methodology.bundle import Bundle
from server.methodology.canonical import accepted_handoff
from server.methodology.handoff import CanonicalRecord
from server.methodology.invocation import named_objects
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.members import satisfies, standing_of
from server.store.routes import resolved_route

# Fixed: standing; the case title, `now()`, latest run and the displayed run's
# ownership in one row; the subject; the pinned route (`resolved_route`); the
# accepted artifacts; the cited sources. Then, per accepted handoff, the host
# identity `accepted_handoff` rebuilds (as app's `CANONICAL_READINESS_IO`).
# Linear in handoffs, so declared for a LITE run of three; measured on one and
# on three in `tests/test_analysis_section.py`.
FIXED_IO = 6
PER_HANDOFF_IO = 10
LITE_NODES = 3
IO_BUDGET = FIXED_IO + LITE_NODES * PER_HANDOFF_IO

router = APIRouter()


def section_blobs() -> BlobStore:
    """The app's blob store, imported at call time for `section_store`'s reason
    (`server/api/app.py` imports this module before it defines `blob_store`)."""
    from server.api import app as api

    return api.blob_store()


def section_bundle() -> Bundle:
    """The process's one vendored bundle, lazily for the same reason."""
    from server.api import app as api

    return api.methodology_bundle()


def run_query(run: str | None = None) -> UUID | None:
    """The `run` query, or `RUN_NOT_FOUND` for one that names no run. Parsed
    here, like `case_path`, so a malformed run opens no connection."""
    if run is None:
        return None
    try:
        return UUID(run)
    except ValueError:
        raise Refusal(RefusalCode.RUN_NOT_FOUND) from None


RunQuery = Annotated[UUID | None, Depends(run_query)]
SectionBlobs = Annotated[BlobStore, Depends(section_blobs)]
SectionBundle = Annotated[Bundle, Depends(section_bundle)]


@router.get("/api/v1/cases/{case_id}/analysis", response_model=AnalysisDocument)
def read_analysis(  # noqa: PLR0913 -- identity, path, query, then the stores
    actor: SectionCaller,
    case_id: CasePath,
    run: RunQuery,
    conn: SectionStore,
    blobs: SectionBlobs,
    bundle: SectionBundle,
) -> AnalysisDocument:
    """The order of the parameters is load-bearing: identity, the path and the
    query, then the store."""
    standing = standing_of(conn, case_id=case_id, user_id=actor.user_id)
    if standing is None or not satisfies(standing, READ_REQUIRES):
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    row = conn.execute(
        "SELECT title, now(),"
        " (SELECT run_id FROM runs WHERE case_id = c.case_id"
        "  ORDER BY created_at DESC, run_id DESC LIMIT 1),"
        " EXISTS (SELECT 1 FROM runs WHERE run_id = %s::uuid AND case_id = c.case_id)"
        " FROM cases c WHERE c.case_id = %s",
        (run, case_id),
    ).fetchone()
    if row is None:  # standing on a case row that is gone: still not readable
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    title, observed_at, latest, owned = row
    if run is not None and not owned:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    displayed = run if run is not None else latest

    handoffs: list[HandoffView] = []
    pending: list[PendingNode] = []
    subject: RunSubjectView | None = None
    notes: list[SectionNote] = []
    route = None if displayed is None else resolved_route(conn, displayed)
    if displayed is not None and route is None:
        notes.append(SectionNote.ROUTE_NOT_PINNED)
    elif displayed is not None and route is not None:
        subject = _subject(conn, displayed)
        handoffs, pending = _handoffs(conn, blobs, bundle, route, displayed)
        if pending:
            notes.append(SectionNote.HANDOFFS_PENDING)
    return AnalysisDocument(
        chrome=Chrome(
            subject=Subject(case_id=case_id, title=title),
            served_role=ServedRole(global_role=actor.role, standing=standing),
        ),
        body=AnalysisBody(
            case_id=case_id,
            latest_run_id=latest,
            displayed_run_id=displayed,
            subject=subject,
            handoffs=handoffs,
            pending=pending,
        ),
        observed_at=observed_at,
        observed_empty=displayed is None,
        status="partial" if notes else "complete",
        notes=notes,
    )


def _subject(conn: StoreConnection, run_id: UUID) -> RunSubjectView | None:
    """The pinned run subject, or None for a run pinned without one."""
    row = conn.execute(
        "SELECT issuer_id, issuer_name, reporting_period, analysis_date"
        " FROM run_inputs WHERE run_id = %s AND issuer_id IS NOT NULL",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    issuer_id, issuer_name, period, analysis_date = (str(value) for value in row)
    return RunSubjectView(
        issuer_id=issuer_id,
        issuer_name=issuer_name,
        reporting_period=period,
        analysis_date=analysis_date,
    )


def _handoffs(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    route: ResolvedRoute,
    run_id: UUID,
) -> tuple[list[HandoffView], list[PendingNode]]:
    """Accepted handoffs in route order, then every other node with its state.

    A row without its record, or whose record no longer binds, refuses
    `ARTIFACT_RECORD_MISMATCH` (503): the server's own bytes failed.
    """
    rows = {
        str(node): (UUID(str(attempt)), str(artifact), record, created)
        for node, attempt, artifact, record, created in conn.execute(
            "SELECT route_node_id, attempt_id, artifact_sha256, record_sha256,"
            " created_at FROM artifacts WHERE run_id = %s",
            (run_id,),
        ).fetchall()
    }
    pairs = {
        node: (artifact, None if record is None else str(record))
        for node, (_attempt, artifact, record, _created) in rows.items()
    }
    read: list[tuple[str, str, CanonicalRecord, bytes, object]] = []
    for node in route.nodes:
        if node.route_node_id not in rows:
            continue
        attempt, artifact, record_sha, created = rows[node.route_node_id]
        if record_sha is None:
            raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        markdown, record = accepted_handoff(
            conn,
            blobs,
            bundle,
            route,
            run_id=run_id,
            route_node_id=node.route_node_id,
            attempt_id=attempt,
            artifact_sha256=artifact,
            record_sha256=str(record_sha),
            accepted=pairs,
        )
        read.append((node.route_node_id, str(record_sha), record, markdown, created))

    documents = _cited_documents(conn, run_id, [r for _n, _s, r, _m, _c in read])
    handoffs = [
        _handoff_view(node_id, sha, record, markdown, created, documents)
        for node_id, sha, record, markdown, created in read
    ]
    accepted = {
        node_id: NodeResult(
            readiness=tuple(record.projections.readiness),
            qa_status=record.projections.qa_status,
        )
        for node_id, _s, record, _m, _c in read
    }
    states = node_states(route, accepted, named_objects(bundle, route))
    pending = [
        PendingNode(
            route_node_id=node.route_node_id,
            module_id=node.module_id,
            state=states[node.route_node_id],
        )
        for node in route.nodes
        if node.route_node_id not in accepted
        and states[node.route_node_id] is not NodeState.COMPLETE
    ]
    return handoffs, pending


def _cited_documents(
    conn: StoreConnection, run_id: UUID, records: list[CanonicalRecord]
) -> dict[str, tuple[str, object]]:
    """Filename and live withdrawal for every cited document, in one query.

    Among the run's pinned members, a live source is preferred, so a document
    withdrawn under one copy and still live under another reads live. A cited
    document no member names is the record disagreeing with the store.
    """
    cited = sorted({c.document_sha256 for r in records for c in r.citations})
    if not cited:
        return {}
    found = {
        str(document): (str(filename), withdrawn_at)
        for document, filename, withdrawn_at in conn.execute(
            "SELECT DISTINCT ON (s.document_sha256) s.document_sha256, s.filename,"
            " s.withdrawn_at FROM run_inputs i JOIN source_set_members m"
            " ON (m.case_id, m.version) = (i.case_id, i.source_version)"
            " JOIN sources s ON (s.case_id, s.source_id) = (m.case_id, m.source_id)"
            " WHERE i.run_id = %s AND s.document_sha256 = ANY(%s)"
            " ORDER BY s.document_sha256, s.withdrawn_at IS NOT NULL, s.source_id",
            (run_id, cited),
        ).fetchall()
    }
    if set(found) != set(cited):
        raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
    return found


def _handoff_view(  # noqa: PLR0913 -- one accepted handoff and its lookups
    route_node_id: str,
    record_sha256: str,
    record: CanonicalRecord,
    markdown: bytes,
    accepted_at: object,
    documents: dict[str, tuple[str, object]],
) -> HandoffView:
    projections = record.projections
    return HandoffView(
        route_node_id=route_node_id,
        module_id=projections.module_id,
        artifact_sha256=record.artifact_sha256,
        record_sha256=record_sha256,
        accepted_at=accepted_at,  # type: ignore[arg-type]
        qa_status=projections.qa_status,
        committee_status=projections.committee_status,
        confidence_score=projections.confidence_score,
        confidence_band=projections.confidence_band,
        limitation_flags=list(projections.limitation_flags),
        validation_warnings=list(projections.validation_warnings),
        decision_scope=projections.decision_scope,
        screening_only=projections.decision_scope == SCREENING_ONLY,
        source_facts=[_citation(c, documents) for c in record.citations],
        # Model-authored and rendered as text, never as markup (§46.3).
        model_analysis=markdown.decode("utf-8"),
        host_calculation="NONE",
    )


def _citation(
    citation: AnchoredCitation, documents: dict[str, tuple[str, object]]
) -> CitationView:
    filename, withdrawn_at = documents[citation.document_sha256]
    return CitationView(
        document_sha256=citation.document_sha256,
        filename=filename,
        page=citation.page,
        matched_text=citation.matched_text,
        rects=[RectView(x0=b.x0, y0=b.y0, x1=b.x1, y1=b.y1) for b in citation.bboxes],
        withdrawn_at=withdrawn_at,  # type: ignore[arg-type]
    )
