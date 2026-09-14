"""Admitting a pack: the only way bytes enter a case.

`SYSTEM_SPEC.md` section 5. Web discovery is structurally absent -- there is no
code path from here to a network, and that is the point of there being one door.

The whole pack lands or none of it does. A half-admitted pack is a set of
documents nobody agreed to run against, and invariant 1 says a run executes
against the pinned set. This function does not commit: the caller's transaction
is what makes "whole or not at all" true, and a refusal leaves it to roll back.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import inf, isfinite
from uuid import UUID, uuid4

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.extract import (
    DEFAULT_LIMITS,
    AdmissionLimits,
    Extractor,
    ExtractorDispatch,
    ExtractorIdentity,
    Token,
    dispatch_by_content,
)
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.cases import lock_case

# pdfminer logs tokens and content-stream operands at DEBUG and WARNING, which is
# document text. Never let it reach this process's handlers.
_PDFMINER = logging.getLogger("pdfminer")
_PDFMINER.addHandler(logging.NullHandler())
_PDFMINER.propagate = False

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
    extractor_identity: str
    output_sha256: str
    extraction_sha256: str


@dataclass(frozen=True, slots=True)
class PreparedPack:
    """A whole pack, extracted and packed, before any store access."""

    documents: tuple[_Packed, ...]


def admit_pack(  # noqa: PLR0913 -- one pack's store, blobs and policy, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    case_id: UUID,
    documents: Sequence[Document],
    dispatch: ExtractorDispatch = dispatch_by_content,
    limits: AdmissionLimits = DEFAULT_LIMITS,
) -> list[UUID]:
    """Admit every document or refuse the pack. Returns the new source ids.

    `prepare_pack` then `admit_prepared`: extraction before the case lock, and
    no commit -- the caller's transaction makes the pack whole or nothing.
    """
    pack = prepare_pack(documents, dispatch=dispatch, limits=limits)
    return admit_prepared(conn, blobs, case_id, pack)


def prepare_pack(
    documents: Sequence[Document],
    *,
    dispatch: ExtractorDispatch = dispatch_by_content,
    limits: AdmissionLimits = DEFAULT_LIMITS,
) -> PreparedPack:
    """Bound, extract and pack every document, touching no store.

    Each document is read by the extractor `dispatch` chooses from its own
    bytes (§44.6), so a mixed pack admits whole and a PDF named `.txt` is still
    a PDF. Text is extracted to tokens carrying page, region, line and
    rectangle, and packed into blocks -- one row each when admitted, never a
    JSON column on the source row, which is the ~8x read defect
    `docs/AI_CODE_QUALITY.md` section 1 measures.

    `limits` bounds the pack (document count, pack bytes) and each document
    (document bytes, then -- inside its extractor -- pages, tokens and
    extraction time) before the expensive step each ceiling guards (§44.1).
    """
    if not documents:
        raise Refusal(RefusalCode.SOURCE_PACK_EMPTY)
    _check_pack_limits(documents, limits)

    # Extract everything first. A document that cannot be read must refuse the
    # pack before any of it is written, not after some of it is.
    pack_deadline = time.monotonic() + limits.max_pack_seconds
    extracted = [
        _extract(dispatch, document, limits, pack_deadline) for document in documents
    ]
    if any(not tokens for _identity, tokens in extracted):
        # Readable bytes, no text: a scanned page. Admitting it would put a
        # source in the pinned set that can never support a citation, and
        # invariant 11 would refuse every quote naming it at artifact time --
        # one run and one provider bill later than here.
        raise Refusal(RefusalCode.SOURCE_HAS_NO_TEXT)

    # And pack the blocks, which is where the text crosses the boundary. Here
    # rather than at the write, for the same reason the check above is here:
    # a line the boundary refuses is a line `read_evidence` refuses, so
    # admitting it would pin a source no run can read.
    return PreparedPack(
        tuple(
            _prepare(document, tokens, identity)
            for document, (identity, tokens) in zip(documents, extracted, strict=True)
        )
    )


def admit_prepared(
    conn: StoreConnection, blobs: BlobStore, case_id: UUID, pack: PreparedPack
) -> list[UUID]:
    """Write a prepared pack under the case lock, in the caller's transaction.

    Never commits: a refusal part way leaves rows the caller rolls back, and the
    blobs already put are harmless content-addressed orphans.
    """
    _require_case(conn, case_id)
    lock_case(conn, case_id)
    return [_admit_one(conn, blobs, case_id, one) for one in pack.documents]


def _check_pack_limits(documents: Sequence[Document], limits: AdmissionLimits) -> None:
    """Document count and byte ceilings, before any dispatch or extraction.

    Checked here rather than per document inside `_extract`, so a pack that
    is simply too big -- too many documents, or too many bytes total -- never
    reaches an extractor at all: not the one document over its own ceiling,
    and not the documents before it, either.
    """
    if len(documents) > limits.max_documents:
        raise Refusal(RefusalCode.SOURCE_TOO_LARGE)
    total_bytes = 0
    for document in documents:
        if len(document.data) > limits.max_document_bytes:
            raise Refusal(RefusalCode.SOURCE_TOO_LARGE)
        total_bytes += len(document.data)
    if total_bytes > limits.max_pack_bytes:
        raise Refusal(RefusalCode.SOURCE_TOO_LARGE)


def _extract(
    dispatch: ExtractorDispatch,
    document: Document,
    limits: AdmissionLimits,
    pack_deadline: float = inf,
) -> tuple[str, list[Token]]:
    """One document's canonical extractor identity and tokens, or a typed code.

    Whatever the dispatch or the extractor raises is reduced to a code and
    raised again outside the handler, so no message, cause or context -- all of
    which can quote the bytes an extractor choked on -- travels with it.
    """
    code: RefusalCode | None = None
    try:
        reader = dispatch(document.data)
        identity = _identity(reader)
        deadline = min(time.monotonic() + limits.max_seconds, pack_deadline)
        tokens = reader.extract(document.data, limits=limits, deadline=deadline)
    except Refusal as refusal:
        code = refusal.code
    except MemoryError:
        raise  # the process, not the document
    except Exception as failure:  # noqa: BLE001 -- untrusted bytes; any failure is a code
        code = _code_for(failure)
    if code is not None:
        raise Refusal(code) from None
    return identity, tokens


def _code_for(failure: Exception) -> RefusalCode:
    # Imported here so plain-text admission never loads pdfminer.
    from pdfminer.pdfdocument import PDFEncryptionError

    if isinstance(failure, PDFEncryptionError):
        return RefusalCode.SOURCE_ENCRYPTED
    return RefusalCode.SOURCE_NOT_READABLE


def _identity(reader: Extractor) -> str:
    try:
        declared = reader.identity
    except (Refusal, AttributeError, TypeError, ValueError, OverflowError):
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID) from None
    if not isinstance(declared, ExtractorIdentity):
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID) from None
    try:
        return declared.canonical()
    except (Refusal, AttributeError, TypeError, ValueError, OverflowError):
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID) from None


def _prepare(document: Document, tokens: list[Token], identity: str) -> _Packed:
    prepared: list[Token] = []
    try:
        for token in tokens:
            indices = (token.page, token.region_id, token.line_id)
            coords = (token.x0, token.y0, token.x1, token.y1)
            if any(type(i) is not int or not -(2**31) <= i < 2**31 for i in indices):
                raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
            if any(
                type(c) not in (int, float) or not isfinite(c) or float(c) != c
                for c in coords
            ):
                raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
            if type(token.text) is not str:
                raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
            BoundaryText.of(token.text)
            prepared.append(Token(token.text, *indices, *map(float, coords)))
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID) from None
    blocks = _blocks(prepared)
    output = _digest(
        {
            "format_version": 1,
            "tokens": [asdict(token) for token in prepared],
            "blocks": [
                [block.block_id, block.page, block.text.value] for block in blocks
            ],
        }
    )
    extraction = _digest(
        {
            "format_version": 1,
            "document_sha256": sha256(document.data).hexdigest(),
            "extractor_identity": json.loads(identity),
            "output_sha256": output,
        }
    )
    return _Packed(document, prepared, blocks, identity, output, extraction)


def _digest(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


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
    conn.execute(
        "INSERT INTO source_extractions"
        " (source_id, format_version, extractor_identity,"
        " output_sha256, extraction_sha256)"
        " VALUES (%s, 1, %s, %s, %s)",
        (
            source_id,
            packed.extractor_identity,
            packed.output_sha256,
            packed.extraction_sha256,
        ),
    )
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
    block_ids = block_ids_by_line(lines)

    return [
        _Block(
            block_id=block_ids[line_id],
            page=line[0].page,
            text=BoundaryText.of(" ".join(token.text for token in line)),
        )
        for line_id, line in sorted(lines.items())
    ]


def block_ids_by_line(line_ids: Iterable[int]) -> dict[int, str]:
    """Line id to the block id admission writes for it: the one numbering.

    One block per line, the source's distinct line ids numbered in ascending
    order and zero-padded to six digits (wider past 999,999 lines). Admission
    packs with it and citation anchoring reads it back from the token index, so
    the two cannot disagree about which block a quoted line belongs to.
    """
    return {
        line_id: f"{BLOCK_PREFIX}{ordinal:06d}"
        for ordinal, line_id in enumerate(sorted(set(line_ids)))
    }


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
