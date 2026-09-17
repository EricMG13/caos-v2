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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from server.evidence.ingest import block_ids_by_line, line_groups
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

    No server path calls this: it judges no delivery, so a run's citations go
    through `verify_citations`. It remains the extractor suites' probe of the
    search rule alone (`tests/test_pdf_extraction.py`). Refuses
    `CITATION_NOT_LOCATED` when the quote is not there and `CITATION_AMBIGUOUS`
    when it is there more than once. Neither refusal carries the quote.
    """
    return _locate(_page_tokens(conn, source_id, page), page, matched_text)


def _locate(tokens: list[_Token], page: int, matched_text: str) -> list[Rect]:
    return _rectangles(_unique_run(tokens, matched_text), page)


def _unique_run(tokens: list[_Token], matched_text: str) -> list[_Token]:
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
    return matches[0]


@dataclass(slots=True)
class TokenIndex:
    """What `verify_citations` read from the token index, keyed per page and
    per source, so several calls inside one read unit read each once.

    Holds only what the store returned; delivery is judged per call against
    that call's `delivered`, never cached.
    """

    pages: dict[tuple[UUID, int], list[_Token]] = field(default_factory=dict)
    digests: dict[UUID, str] = field(default_factory=dict)
    line_blocks: dict[UUID, dict[int, tuple[str, ...]]] = field(default_factory=dict)


def verify_citations(
    conn: StoreConnection,
    *,
    delivered: Mapping[UUID, frozenset[str]],
    citations: Sequence[Citation],
    index: TokenIndex | None = None,
) -> list[AnchoredCitation]:
    """Re-derive every citation, or refuse the set.

    Called before an artifact is written, never after: an artifact naming a quote
    nobody can find is the thing invariant 11 exists to prevent, and one that has
    already been stored is a correction rather than a refusal.

    A citation may only name evidence actually delivered to that node
    (`SYSTEM_SPEC.md` section 5) -- a real source in the same case is still
    something this node was not given. `delivered` maps each source to the
    exact blocks the node was handed, and the one match must lie wholly within
    their lines: a quote on an undelivered page, or wrapping onto an undelivered
    line, refuses `CITATION_NOT_DELIVERED`. Ambiguity is still counted over the
    whole page (`docs/DECISIONS.md` section 44.5), so a quote repeated on a line
    the node never saw is ambiguous rather than resolved to the copy it did.

    An artifact carries many citations and they cluster: several quotes from one
    page of one source is the normal shape. Both lookups are therefore fetched
    once per distinct page and per distinct source rather than once per citation,
    which is the N+1 that `docs/AI_CODE_QUALITY.md` section 1 measures at ~8x on
    exactly this kind of list. A caller verifying several lists in one unit
    passes one `TokenIndex` to share those reads across them.
    """
    if index is None:
        index = TokenIndex()
    pages, digests, ordinals = index.pages, index.digests, index.line_blocks

    anchored = []
    for citation in citations:
        blocks = delivered.get(citation.source_id)
        if blocks is None:
            raise Refusal(RefusalCode.CITATION_NOT_DELIVERED)
        key = (citation.source_id, citation.page)
        if key not in pages:
            pages[key] = _page_tokens(conn, citation.source_id, citation.page)
        if citation.source_id not in digests:
            digests[citation.source_id] = _document_sha256(conn, citation.source_id)
        run = _unique_run(pages[key], citation.matched_text)
        if citation.source_id not in ordinals:
            ordinals[citation.source_id] = _line_blocks(conn, citation.source_id)
        lines = ordinals[citation.source_id]
        if any(not _delivered(lines.get(token.line_id), blocks) for token in run):
            raise Refusal(RefusalCode.CITATION_NOT_DELIVERED)
        boxes = _rectangles(run, citation.page)
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


def _line_blocks(conn: StoreConnection, source_id: UUID) -> dict[int, tuple[str, ...]]:
    """Line id to the blocks admission wrote for it, once per source: admission's
    own numbering (`block_ids_by_line`) over the token index's line ids.

    A line past `GROUP_WIDTH` was split, so a line may own more than one block.
    Which lines were split is not guessed: a source whose stored block count is
    its line count had none, which is every source admitted before there was any
    splitting and every source whose lines fit. Only when the counts differ is
    the packing recomputed from the text, and the count travels with the line
    ids rather than in a statement of its own.
    """
    rows = conn.execute(
        "SELECT lines.line_id, blocks.stored FROM"
        " (SELECT DISTINCT line_id FROM source_tokens WHERE source_id = %s) AS lines,"
        " (SELECT count(*) AS stored FROM source_blocks WHERE source_id = %s)"
        " AS blocks",
        (source_id, source_id),
    ).fetchall()
    line_ids = [int(row[0]) for row in rows]
    stored = int(rows[0][1]) if rows else 0
    if stored == len(line_ids):
        return block_ids_by_line(dict.fromkeys(line_ids, 1))
    counts = _group_counts(conn, source_id)
    if sum(counts.values()) != stored:
        # The recomputation is a derivation of what admission wrote, and here
        # it does not agree with it. The store cannot have drifted -- 0027
        # seals extracted evidence -- so the rule has: this source was packed
        # under a different `GROUP_WIDTH`. Every id past the disagreement is
        # then an id no row carries, and asking whether such a block was
        # delivered answers about the citation when the fault is the host's.
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)
    return block_ids_by_line(counts)


def _group_counts(conn: StoreConnection, source_id: UUID) -> dict[int, int]:
    """How many blocks each line needs, recomputed from its text by admission's
    own rule -- the read a source carrying a split line pays, and no other."""
    rows = conn.execute(
        "SELECT line_id, text FROM source_tokens WHERE source_id = %s"
        " ORDER BY token_id",
        (source_id,),
    ).fetchall()
    lines: dict[int, list[str]] = {}
    for line_id, text in rows:
        lines.setdefault(int(line_id), []).append(str(text))
    return {
        line_id: len(line_groups(" ".join(words))) for line_id, words in lines.items()
    }


def _delivered(ids: tuple[str, ...] | None, blocks: frozenset[str]) -> bool:
    """A line is delivered when every block it was split into was.

    Fail closed, and deliberately line-granular: a quote crossing a group
    boundary needs both sides, and a delivery carrying half a split line
    carries none of it. Nothing narrows a delivery below a whole source today,
    so this is the rule per-node evidence selection will meet rather than one
    any run can meet now.
    """
    if not ids:
        return False
    return all(block in blocks for block in ids)


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
