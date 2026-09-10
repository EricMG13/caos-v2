"""Admitting a pack: the only way bytes enter a case.

`SYSTEM_SPEC.md` section 5. Web discovery is structurally absent -- there is no
code path from here to a network, and that is the point of there being one door.

The whole pack lands or none of it does. A half-admitted pack is a set of
documents nobody agreed to run against, and invariant 1 says a run executes
against the pinned set. This function does not commit: the caller's transaction
is what makes "whole or not at all" true, and a refusal leaves it to roll back.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.extract import Extractor, PlainTextExtractor, Token
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection

# One block per line while small. `SYSTEM_SPEC.md` section 5 bounds line groups
# once a document is not small; this build packs a line per block and the group
# arrives with the document that needs it (CLAUDE.md known gaps).
BLOCK_PREFIX = "b"


@dataclass(frozen=True, slots=True)
class Document:
    """One document offered to a case. Its name crossed the boundary already."""

    filename: BoundaryText
    data: bytes


def admit_pack(
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    case_id: UUID,
    documents: Sequence[Document],
    extractor: Extractor | None = None,
) -> list[UUID]:
    """Admit every document or refuse the pack. Returns the new source ids.

    Bytes go to the blob store under their digest; the row holds the address.
    Text is extracted to tokens carrying page, region, line and rectangle, and
    packed into blocks -- one row each, never a JSON column on the source row,
    which is the ~8x read defect `docs/AI_CODE_QUALITY.md` section 1 measures.
    """
    if not documents:
        raise Refusal(RefusalCode.SOURCE_PACK_EMPTY)
    _require_case(conn, case_id)
    reader = extractor if extractor is not None else PlainTextExtractor()

    # Extract everything first. A document that cannot be read must refuse the
    # pack before any of it is written, not after some of it is.
    extracted = [(document, reader.extract(document.data)) for document in documents]
    if any(not tokens for _document, tokens in extracted):
        # Readable bytes, no text: a scanned page. Admitting it would put a
        # source in the pinned set that can never support a citation, and
        # invariant 11 would refuse every quote naming it at artifact time --
        # one run and one provider bill later than here.
        raise Refusal(RefusalCode.SOURCE_HAS_NO_TEXT)

    source_ids = []
    for document, tokens in extracted:
        source_ids.append(_admit_one(conn, blobs, case_id, document, tokens))
    return source_ids


def _require_case(conn: StoreConnection, case_id: UUID) -> None:
    row = conn.execute(
        "SELECT case_id FROM cases WHERE case_id = %s", (case_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.CASE_NOT_FOUND)


def _admit_one(
    conn: StoreConnection,
    blobs: BlobStore,
    case_id: UUID,
    document: Document,
    tokens: list[Token],
) -> UUID:
    source_id = uuid4()
    conn.execute(
        "INSERT INTO sources (source_id, case_id, document_sha256, filename)"
        " VALUES (%s, %s, %s, %s)",
        (source_id, case_id, blobs.put(document.data), document.filename.value),
    )
    _store_tokens(conn, source_id, tokens)
    _store_blocks(conn, source_id, tokens)
    return source_id


def _store_tokens(conn: StoreConnection, source_id: UUID, tokens: list[Token]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO source_tokens"
            " (source_id, token_id, page, region_id, line_id, text, x0, y0, x1, y1)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    source_id,
                    token_id,
                    token.page,
                    token.region_id,
                    token.line_id,
                    token.text,
                    token.x0,
                    token.y0,
                    token.x1,
                    token.y1,
                )
                for token_id, token in enumerate(tokens)
            ],
        )


def _store_blocks(conn: StoreConnection, source_id: UUID, tokens: list[Token]) -> None:
    """One block per line, in reading order, keyed by `(source_id, block_id)`."""
    lines: dict[int, list[Token]] = {}
    for token in tokens:
        lines.setdefault(token.line_id, []).append(token)

    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO source_blocks (source_id, block_id, page, text)"
            " VALUES (%s, %s, %s, %s)",
            [
                (
                    source_id,
                    f"{BLOCK_PREFIX}{ordinal:06d}",
                    line[0].page,
                    " ".join(token.text for token in line),
                )
                for ordinal, (_line_id, line) in enumerate(sorted(lines.items()))
            ],
        )
