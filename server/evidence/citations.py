"""Invariant 11: the host re-locates the quote, and refuses one it cannot.

A citation as a module offers it is `{source_id, page, matched_text}`. What
reaches an artifact is that plus the coordinates the host derived by finding the
quote in its own token index. The module never supplies a rectangle, because a
rectangle it supplied would be a claim nobody checked.

Two rules make the search honest:

*Exactly once.* A quote found twice is refused rather than resolved to the first
match. Highlighting one of two identical sentences asserts a precision the host
does not have.

*Never across a region.* Matching joins tokens within a line and continues only
onto the next line of the same region (`SYSTEM_SPEC.md` section 5). Two columns
are two regions, so a phrase cannot be assembled across the gutter between them --
which is what a naive scan of page text does, and what it silently produces is a
quote that exists nowhere on the page.

The result is one rectangle per line the quote covers, the shape a PDF
highlight's QuadPoints uses and for the same reason: selected text wraps, and a
single enclosing rectangle would cover text the quote does not contain.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection


@dataclass(frozen=True, slots=True)
class Rect:
    """One line's worth of a quote, in page coordinates."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class Citation:
    """What a module offers: where it says the quote is, and what it says it is."""

    source_id: UUID
    page: int
    matched_text: str


@dataclass(frozen=True, slots=True)
class AnchoredCitation:
    """What reaches the artifact: the module's claim, re-derived by the host."""

    document_sha256: str
    page: int
    matched_text: str
    bboxes: tuple[Rect, ...]


@dataclass(frozen=True, slots=True)
class _Token:
    text: str
    region_id: int
    line_id: int
    x0: float
    y0: float
    x1: float
    y1: float


def anchor_citation(
    conn: StoreConnection, *, source_id: UUID, page: int, matched_text: str
) -> list[Rect]:
    """Find `matched_text` on `page` of a live source; return its rectangles.

    Refuses `CITATION_NOT_LOCATED` when the quote is not there and
    `CITATION_AMBIGUOUS` when it is there more than once. Neither refusal carries
    the quote.
    """
    return _locate(_page_tokens(conn, source_id, page), page, matched_text)


def _locate(tokens: list[_Token], page: int, matched_text: str) -> list[Rect]:
    """The one search rule both entry points use: exactly once, never across a
    region."""
    words = matched_text.split()
    if not words:
        raise Refusal(RefusalCode.CITATION_NOT_LOCATED)
    matches = [
        run for start in range(len(tokens)) if (run := _match_at(tokens, start, words))
    ]
    if not matches:
        raise Refusal(RefusalCode.CITATION_NOT_LOCATED)
    if len(matches) > 1:
        raise Refusal(RefusalCode.CITATION_AMBIGUOUS)
    return _rectangles(matches[0], page)


def verify_citations(
    conn: StoreConnection,
    *,
    delivered: set[UUID],
    citations: Sequence[Citation],
) -> list[AnchoredCitation]:
    """Re-derive every citation, or refuse the set.

    Called before an artifact is written, never after: an artifact naming a quote
    nobody can find is the thing invariant 11 exists to prevent, and one that has
    already been stored is a correction rather than a refusal.

    A citation may only name evidence actually delivered to that node
    (`SYSTEM_SPEC.md` section 5) -- a real source in the same case is still
    something this node was not given.

    An artifact carries many citations and they cluster: several quotes from one
    page of one source is the normal shape. Both lookups are therefore fetched
    once per distinct page and per distinct source rather than once per citation,
    which is the N+1 that `docs/AI_CODE_QUALITY.md` section 1 measures at ~8x on
    exactly this kind of list.
    """
    pages: dict[tuple[UUID, int], list[_Token]] = {}
    digests: dict[UUID, str] = {}

    anchored = []
    for citation in citations:
        if citation.source_id not in delivered:
            raise Refusal(RefusalCode.CITATION_NOT_DELIVERED)
        key = (citation.source_id, citation.page)
        if key not in pages:
            pages[key] = _page_tokens(conn, citation.source_id, citation.page)
        if citation.source_id not in digests:
            digests[citation.source_id] = _document_sha256(conn, citation.source_id)
        boxes = _locate(pages[key], citation.page, citation.matched_text)
        anchored.append(
            AnchoredCitation(
                document_sha256=digests[citation.source_id],
                page=citation.page,
                matched_text=citation.matched_text,
                bboxes=tuple(boxes),
            )
        )
    return anchored


def _page_tokens(conn: StoreConnection, source_id: UUID, page: int) -> list[_Token]:
    """The page's tokens in reading order, from a live source only."""
    rows = conn.execute(
        "SELECT tokens.text, tokens.region_id, tokens.line_id,"
        " tokens.x0, tokens.y0, tokens.x1, tokens.y1"
        " FROM source_tokens AS tokens"
        " JOIN live_sources USING (source_id)"
        " WHERE tokens.source_id = %s AND tokens.page = %s"
        " ORDER BY tokens.token_id",
        (source_id, page),
    ).fetchall()
    return [_Token(*row) for row in rows]


def _match_at(tokens: list[_Token], start: int, words: Sequence[str]) -> list[_Token]:
    """The tokens matching `words` from `start`, or an empty list.

    A run may cross a line boundary only inside one region. Crossing regions is
    what assembles a phrase across a column gutter, and the phrase it assembles
    is on no page.
    """
    if start + len(words) > len(tokens):
        return []
    run = tokens[start : start + len(words)]
    if any(token.text != word for token, word in zip(run, words, strict=True)):
        return []
    if any(token.region_id != run[0].region_id for token in run):
        return []
    return run


def _rectangles(run: list[_Token], page: int) -> list[Rect]:
    """One rectangle per line the run covers, in reading order."""
    by_line: dict[int, list[_Token]] = {}
    for token in run:
        by_line.setdefault(token.line_id, []).append(token)
    return [
        Rect(
            page=page,
            x0=min(token.x0 for token in line),
            y0=min(token.y0 for token in line),
            x1=max(token.x1 for token in line),
            y1=max(token.y1 for token in line),
        )
        for _line_id, line in sorted(by_line.items())
    ]


def _document_sha256(conn: StoreConnection, source_id: UUID) -> str:
    row = conn.execute(
        "SELECT document_sha256 FROM live_sources WHERE source_id = %s",
        (source_id,),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)
    return str(row[0])
