"""The Directory section read (Task 4.1, slice 4.1c).

Every case the actor holds live standing on, and nothing else: a global ADMIN
without membership sees none, because standing is per case (decision 5's
"persona is not authority"). Past `CASES_MAX` the document is partial and says
so with `LIST_TRUNCATED` rather than silently dropping rows.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from server.api.identity import Actor, actor_from_headers
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
from server.store import StoreConnection
from server.store.members import cases_for_member

# The store's `now()` and the one listing query (`cases_for_member` reads the
# source count and latest run laterally), whatever the number of cases.
# Measured in `tests/test_directory_upload_sections.py`.
IO_BUDGET = 2

router = APIRouter()


def section_actor(request: Request) -> Actor:
    """Who is asking; `app.actor_from_request`'s rule, without the store."""
    return actor_from_headers(request.headers)


def section_store() -> Iterator[StoreConnection]:
    """The request's connection, from `app.store_connection`.

    Imported at call time: `server/api/app.py` imports this module to include
    its router before it defines `Caller` and `Store`, so importing them here
    is a cycle whichever module loads first. The section reads depend on these
    two instead, and a test overrides them rather than the app's.
    """
    from server.api import app as api

    yield from api.store_connection()


# Declared in this order on every section route: identity is solved before the
# store dependency, so an anonymous request opens no connection.
SectionCaller = Annotated[Actor, Depends(section_actor)]
SectionStore = Annotated[StoreConnection, Depends(section_store)]


@router.get("/api/v1/directory", response_model=DirectoryDocument)
def read_directory(actor: SectionCaller, conn: SectionStore) -> DirectoryDocument:
    """`actor` is declared before `conn`: an anonymous request is refused
    before a connection opens."""
    [observed_at] = conn.execute("SELECT now()").fetchall()[0]
    listed = cases_for_member(conn, user_id=actor.user_id, limit=CASES_MAX + 1)
    truncated = len(listed) > CASES_MAX
    return DirectoryDocument(
        chrome=Chrome(
            subject=None,
            served_role=ServedRole(global_role=actor.role, standing=None),
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
