"""The Directory section read (Task 4.1, slice 4.1c).

Every case the actor holds live standing on, and nothing else: a global ADMIN
without membership sees none, because standing is per case (decision 5's
"persona is not authority"). Past `CASES_MAX` the document is partial and says
so with `LIST_TRUNCATED` rather than silently dropping rows.
"""

from __future__ import annotations

from fastapi import APIRouter

from server.api.commands.availability import directory_actions
from server.api.deps import Caller, Store
from server.api.wire import (
    CASES_MAX,
    CaseRow,
    Chrome,
    DirectoryBody,
    DirectoryDocument,
    RunSummary,
    SectionNote,
    ServedRole,
)
from server.store.members import cases_for_member

# The store's `now()` and the one listing query (`cases_for_member` reads the
# source count and latest run laterally), whatever the number of cases.
# Measured in `tests/test_directory_upload_sections.py`.
IO_BUDGET = 2

router = APIRouter()


@router.get("/api/v1/directory", response_model=DirectoryDocument)
def read_directory(actor: Caller, conn: Store) -> DirectoryDocument:
    """`actor` is declared before `conn`: an anonymous request is refused
    before a connection opens."""
    [observed_at] = conn.execute("SELECT now()").fetchall()[0]
    listed = cases_for_member(conn, user_id=actor.user_id, limit=CASES_MAX + 1)
    truncated = len(listed) > CASES_MAX
    return DirectoryDocument(
        chrome=Chrome(
            subject=None,
            served_role=ServedRole(global_role=actor.role, standing=None),
            actions=directory_actions(actor.role),
        ),
        body=DirectoryBody(
            cases=[
                CaseRow(
                    case_id=row.case_id,
                    title=row.title,
                    created_at=row.created_at,
                    standing=row.standing,
                    live_sources=row.live_sources,
                    latest_run=None
                    if row.latest_run is None
                    else RunSummary(
                        run_id=row.latest_run.run_id,
                        status=row.latest_run.status,  # type: ignore[arg-type]
                        created_at=row.latest_run.created_at,
                        profile_id=row.latest_run.profile_id,
                        selection_id=row.latest_run.selection_id,
                    ),
                )
                for row in listed[:CASES_MAX]
            ]
        ),
        observed_at=observed_at,
        observed_empty=not listed,
        status="partial" if truncated else "complete",
        notes=[SectionNote.LIST_TRUNCATED] if truncated else [],
    )
