"""Text into tokens that carry where they were.

Invariant 11 needs four things per token: the page, the layout region, the line,
and a rectangle. A citation is re-located by joining tokens within a line and
continuing only onto the next line of the same region, so a quote can never be
assembled across a column gutter -- the two columns are different regions and the
phrase never forms (`SYSTEM_SPEC.md` section 5).

What extracts them is deliberately an argument. This module ships the plain-text
extractor, which is honest about what it is: a `.txt` document has no typography,
so its rectangles are the cells of a fixed-pitch rendering at `CELL`, stated here
rather than implied. `docs/REBUILD_PLAN.md` owes Phase 6 a real PDF fixture
through a real extractor (`test_citations_anchor_in_an_extracted_pdf`); that
extractor implements the same protocol and nothing above this module changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.refusals import Refusal, RefusalCode

# A fixed-pitch cell, in points. 7.2 x 12.0 is a 12pt monospace at its usual
# advance width; the numbers matter only in that they are declared and constant,
# because a rectangle derived from them describes a rendering we can reproduce.
CELL_WIDTH = 7.2
CELL_HEIGHT = 12.0
MARGIN = 72.0
# A blank line ends a region: consecutive non-blank lines are one paragraph, and
# a paragraph is the unit a quote may wrap within.
LINES_PER_PAGE = 60


@dataclass(frozen=True, slots=True)
class Token:
    """One extracted text run, and where on the page it sat."""

    text: str
    page: int
    region_id: int
    line_id: int
    x0: float
    y0: float
    x1: float
    y1: float


class Extractor(Protocol):
    """Bytes to tokens. The one seam a real PDF extractor arrives through."""

    def extract(self, data: bytes) -> list[Token]: ...


@dataclass(frozen=True, slots=True)
class PlainTextExtractor:
    """UTF-8 text as tokens on a fixed-pitch page.

    Refuses `SOURCE_NOT_READABLE` for bytes that are not UTF-8, carrying the code
    and nothing else -- the offending bytes are exactly what must not travel.
    """

    def extract(self, data: bytes) -> list[Token]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise Refusal(RefusalCode.SOURCE_NOT_READABLE) from None

        tokens: list[Token] = []
        region_id = 0
        for line_number, line in enumerate(text.splitlines()):
            if not line.strip():
                # A blank line closes the paragraph; the next non-blank one opens
                # a new region, so a quote cannot wrap across the gap.
                region_id += 1
                continue
            tokens.extend(_line_tokens(line, line_number, region_id))
        return tokens


def _line_tokens(line: str, line_number: int, region_id: int) -> list[Token]:
    page, row = divmod(line_number, LINES_PER_PAGE)
    top = MARGIN + row * CELL_HEIGHT
    tokens = []
    for word, column in _words(line):
        tokens.append(
            Token(
                text=word,
                page=page + 1,
                region_id=region_id,
                line_id=line_number,
                x0=MARGIN + column * CELL_WIDTH,
                y0=top,
                x1=MARGIN + (column + len(word)) * CELL_WIDTH,
                y1=top + CELL_HEIGHT,
            )
        )
    return tokens


def _words(line: str) -> list[tuple[str, int]]:
    """Each whitespace-separated run with the column it starts at.

    Whitespace as `str.split()` draws it, not the space character alone.
    `server/evidence/citations.py` splits `matched_text` that way, so a token
    holding an interior tab is one the index can never be asked for: the line is
    delivered by `read_evidence` and the verbatim quote of it is then refused
    `CITATION_NOT_LOCATED`. The two have to agree on where a word ends, or the
    evidence a module was handed is evidence it cannot cite.
    """
    words: list[tuple[str, int]] = []
    start: int | None = None
    for column, character in enumerate(line):
        if not character.isspace():
            if start is None:
                start = column
        elif start is not None:
            words.append((line[start:column], start))
            start = None
    if start is not None:
        words.append((line[start:], start))
    return words
