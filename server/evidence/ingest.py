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


@dataclass(frozen=True, slots=True)
class _Block:
    """One packed block, before it is written: its id, its page, its text.

    The text is `BoundaryText` because that is what the block will be read back
    as. Packing before writing is what lets a line the boundary refuses refuse
    the pack rather than the read.
    """

    block_id: str
    page: int
    text: BoundaryText


@dataclass(frozen=True, slots=True)
class _Packed:
    """One document, extracted and packed, before any of it is written.

    One object rather than three arguments threaded through two functions --
    the shape `Execution` and `Harness` already take here. They are the whole
    of what admitting a document needs, and passing them apart made the
    signature wide enough that the argument ceiling refused it, which is the
    ceiling doing its job.
    """

    document: Document
    tokens: list[Token]
    blocks: list[_Block]


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

    # And pack the blocks, which is where the text crosses the boundary. Here
    # rather than at the write, for the same reason the check above is here:
    # a line the boundary refuses is a line `read_evidence` refuses, so
    # admitting it would pin a source no run can read.
    packed = [
        _Packed(document=document, tokens=tokens, blocks=_blocks(tokens))
        for document, tokens in extracted
    ]

    return [_admit_one(conn, blobs, case_id, one) for one in packed]


def _require_case(conn: StoreConnection, case_id: UUID) -> None:
    row = conn.execute(
        "SELECT case_id FROM cases WHERE case_id = %s", (case_id,)
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.CASE_NOT_FOUND)


def _admit_one(
    conn: StoreConnection, blobs: BlobStore, case_id: UUID, packed: _Packed
) -> UUID:
    source_id = uuid4()
    conn.execute(
        "INSERT INTO sources (source_id, case_id, document_sha256, filename)"
        " VALUES (%s, %s, %s, %s)",
        (
            source_id,
            case_id,
            blobs.put(packed.document.data),
            packed.document.filename.value,
        ),
    )
    _store_tokens(conn, source_id, packed.tokens)
    _store_blocks(conn, source_id, packed.blocks)
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


def _blocks(tokens: list[Token]) -> list[_Block]:
    """One block per line, in reading order, its text across the boundary.

    `source_blocks.text` is pinned state, and CLAUDE.md's rule is that every
    string reaching pinned state carries `BoundaryText`. It was carried on the
    way out instead -- `read_evidence` calls `BoundaryText.of` -- which left
    admission writing a bare `str`, so a line over the limit and a line holding
    the override control the boundary exists to refuse were both admitted and
    then refused at every read. A refusal here costs a pack; there it cost a
    pinned source no run can read.
    """
    lines: dict[int, list[Token]] = {}
    for token in tokens:
        lines.setdefault(token.line_id, []).append(token)

    return [
        _Block(
            block_id=f"{BLOCK_PREFIX}{ordinal:06d}",
            page=line[0].page,
            text=BoundaryText.of(" ".join(token.text for token in line)),
        )
        for ordinal, (_line_id, line) in enumerate(sorted(lines.items()))
    ]


def _store_blocks(conn: StoreConnection, source_id: UUID, blocks: list[_Block]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO source_blocks (source_id, block_id, page, text)"
            " VALUES (%s, %s, %s, %s)",
            [
                (source_id, block.block_id, block.page, block.text.value)
                for block in blocks
            ],
        )
