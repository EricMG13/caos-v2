"""Create case and source admission (Task 4.2 slice 4.2d, decisions 2, 4, 6).

**Create case** (`POST /api/v1/cases`): identity, key, a global role that may
write, then the closed body. One nil-scope unit inserts the case, grants the
creator ADMIN standing and records `CASE_CREATED` beside the receipt -- a
single-actor release under invariant 5.

**Admission** (`POST /api/v1/cases/{case_id}/sources`), in this order:

1. Identity (401), then the envelope from headers alone: `multipart/form-data`
   with a declared `Content-Length` (else `REQUEST_INVALID`) no larger than the
   pack ceiling plus multipart overhead (else 413 `SOURCE_TOO_LARGE`).
2. Key, visibility, global role and the WRITER floor -- so a stranger's pack
   is never parsed, let alone extracted.
3. The standing read's transaction is closed, then the form is parsed with
   the stream held to its declared length: only file parts named `document`,
   each filename `BoundaryText` of at most 255 characters and not blank.
4. The receipt is looked up for the pack's digest and a replay answers without
   extracting; otherwise `prepare_pack` extracts (the §47 child for a PDF) with
   no transaction open and no case lock held.
5. One governed unit: `admit_prepared`, `SOURCES_ADMITTED` and the receipt.
   A refusal there commits no row; blobs already put are content-addressed
   orphans (CLAUDE.md known gaps).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response

from server.api.commands._request import (
    Key,
    command_response,
    json_body,
)
from server.api.deps import Caller, Store
from server.api.identity import Actor, GlobalRole
from server.api.wire import TITLE_CHARS, CaseCreated, CreateCase
from server.boundary_text import BoundaryText
from server.evidence.extract import DEFAULT_LIMITS
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.audit import GovernedAction
from server.store.commands import (
    NIL_SCOPE,
    request_digest,
    run_command,
)
from server.store.members import Standing, grant

# Measured by `tests/test_case_commands.py`.
CREATE_CASE_IO = 13  # lookup, the case row and its grant, the governed unit, receipt
ADMISSION_FIXED_IO = 14  # standing, receipt peek, lookup, the governed unit, receipt
ADMISSION_PER_DOCUMENT_IO = 4  # source, tokens, blocks, extraction
REPLAY_IO = 3  # decision 14: standing and the receipt lookup
IO_BUDGET = max(
    CREATE_CASE_IO,
    ADMISSION_FIXED_IO + ADMISSION_PER_DOCUMENT_IO * DEFAULT_LIMITS.max_documents,
)

CREATE_CASE = "CREATE_CASE"
ADMIT_SOURCES = "ADMIT_SOURCES"
DOCUMENT_PART = "document"
FILENAME_CHARS = 255
MULTIPART_OVERHEAD_BYTES = 1024 * 1024
MAX_UPLOAD_BYTES = DEFAULT_LIMITS.max_pack_bytes + MULTIPART_OVERHEAD_BYTES

router = APIRouter()


def _require_global_writer(actor: Caller) -> Actor:
    """A global role that may write: ANALYST or ADMIN."""
    if actor.role is GlobalRole.READER:
        raise Refusal(RefusalCode.NOT_AUTHORISED)
    return actor


@router.post("/api/v1/cases", status_code=201)
def create_case_command(
    actor: Caller,
    key: Key,
    _may_write: Annotated[Actor, Depends(_require_global_writer)],
    body: Annotated[CreateCase, Depends(json_body(CreateCase))],
    conn: Store,
) -> Response:
    title = BoundaryText.of(body.title, limit=TITLE_CHARS)
    case_id = uuid4()
    result = run_command(
        conn,
        scope=NIL_SCOPE,
        key=key,
        command=CREATE_CASE,
        request_sha256=request_digest(
            CREATE_CASE,
            case_id=None,
            run_id=None,
            gate=None,
            body={"title": title.value},
        ),
        action=GovernedAction(
            case_id=case_id,
            actor_id=actor.user_id,
            action="CASE_CREATED",
            requires=Standing.ADMIN,
            payload={"case_id": str(case_id)},
        ),
        prepare=_open_case(case_id, title, actor.user_id),
        write=lambda _unit: (201, CaseCreated(case_id=case_id)),
    )
    return command_response(result, CaseCreated)


def _open_case(
    case_id: UUID, title: BoundaryText, creator: UUID
) -> Callable[[StoreConnection], None]:
    """The case row and its creator's ADMIN standing, before the case lock the
    governed write then takes on them."""

    def prepare(conn: StoreConnection) -> None:
        conn.execute(
            "INSERT INTO cases (case_id, title) VALUES (%s, %s)", (case_id, title.value)
        )
        grant(conn, case_id=case_id, user_id=creator, standing=Standing.ADMIN)

    return prepare
