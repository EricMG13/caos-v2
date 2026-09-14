"""The Upload section read (Task 4.1, slice 4.1c).

Every source of one case, admitted or withdrawn -- withdrawal read live, never
from a snapshot -- with the set versions each belongs to. The case is the
authorisation resource: unknown, unauthorised, revoked and malformed are one
private 404 `CASE_NOT_FOUND`, because any difference between them is the
disclosure (decision 1).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from server.api.deps import Caller, Store
from server.api.wire import (
    SOURCES_MAX,
    Chrome,
    SectionNote,
    ServedRole,
    SetVersion,
    SourceRow,
    Subject,
    UploadBody,
    UploadDocument,
)
from server.refusals import Refusal, RefusalCode
from server.store.members import Standing, satisfies, standing_of
from server.store.source_sets import case_sources

# Standing, the case title with the store's `now()`, then `case_sources`'s set
# versions and sources: four, whatever the number of sources or versions.
# Measured in `tests/test_directory_upload_sections.py`.
IO_BUDGET = 4

READ_REQUIRES = Standing.READER

router = APIRouter()


def case_path(case_id: str) -> UUID:
    """The path's case id, or the refusal a case the caller may not read gets.

    Typed `str` and parsed here rather than typed `UUID`, so a malformed id is
    answered `CASE_NOT_FOUND` in the refusal body instead of FastAPI's 422 --
    and, as a dependency declared after identity and before the store, without
    opening a connection. `from None`: the ValueError quotes the path.
    """
    try:
        return UUID(case_id)
    except ValueError:
        raise Refusal(RefusalCode.CASE_NOT_FOUND) from None


CasePath = Annotated[UUID, Depends(case_path)]


@router.get("/api/v1/cases/{case_id}/upload", response_model=UploadDocument)
def read_upload(actor: Caller, case_id: CasePath, conn: Store) -> UploadDocument:
    """The order of the three parameters is load-bearing: identity, then the
    path, then the store."""
    standing = standing_of(conn, case_id=case_id, user_id=actor.user_id)
    if standing is None or not satisfies(standing, READ_REQUIRES):
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    row = conn.execute(
        "SELECT title, now() FROM cases WHERE case_id = %s", (case_id,)
    ).fetchone()
    if row is None:  # standing on a case row that is gone: still not readable
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    title, observed_at = row
    listed = case_sources(conn, case_id=case_id, limit=SOURCES_MAX)
    return UploadDocument(
        chrome=Chrome(
            subject=Subject(case_id=case_id, title=title),
            served_role=ServedRole(global_role=actor.role, standing=standing),
        ),
        body=UploadBody(
            case_id=case_id,
            sources=[
                SourceRow(
                    source_id=source.source_id,
                    filename=source.filename,
                    document_sha256=source.document_sha256,
                    admitted_at=source.admitted_at,
                    withdrawn_at=source.withdrawn_at,
                    extractor_identity=source.extractor_identity,
                    set_versions=list(source.set_versions),
                )
                for source in listed.sources
            ],
            set_versions=[
                SetVersion(
                    version=version.version,
                    fingerprint=version.fingerprint,
                    member_count=version.member_count,
                )
                for version in listed.set_versions
            ],
        ),
        observed_at=observed_at,
        observed_empty=not listed.sources,
        status="partial" if listed.truncated else "complete",
        notes=[SectionNote.LIST_TRUNCATED] if listed.truncated else [],
    )
