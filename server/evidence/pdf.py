"""A real PDF into tokens that carry where they were.

`docs/DECISIONS.md` §21. `pdfminer.six` exposes a layout tree that maps exactly
onto the three things invariant 11 needs from a token:

    LTTextBox   -> the region a quote may not leave
    LTTextLine  -> the line it sits on
    LTChar      -> the rectangle, taken from the character rather than estimated

The last one is the point. `PlainTextExtractor` derives rectangles from a
declared fixed pitch, which is honest for a `.txt` file and is a fiction for a
PDF. Here the coordinates come out of the document, so a citation's rectangle is
a measurement rather than a reconstruction.

Nothing above this module changes. It implements the same `Extractor` protocol,
so ingestion, block packing, citation anchoring and every refusal are the ones
already tested -- which is what a seam is for.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pdfminer.layout import LTChar, LTPage, LTTextBox, LTTextLine
from pdfminer.pdfparser import PDFSyntaxError

from server.evidence.extract import Token
from server.refusals import Refusal, RefusalCode


@dataclass(frozen=True, slots=True)
class PdfExtractor:
    """Bytes of a PDF, as tokens with real coordinates."""

    def extract(self, data: bytes) -> list[Token]:
        """Refuses `SOURCE_NOT_READABLE` for bytes that are not a readable PDF.

        A scanned page parses fine and yields no tokens; that is not an error
        here, and `admit_pack` refuses it as `SOURCE_HAS_NO_TEXT` -- the code
        that says what is actually wrong with it.
        """
        tokens: list[Token] = []
        region_id = 0
        line_id = 0
        for page_number, page in enumerate(_pages(data), start=1):
            for box in page:
                if not isinstance(box, LTTextBox):
                    continue
                for line in box:
                    if not isinstance(line, LTTextLine):
                        continue
                    tokens.extend(_line_tokens(line, page_number, region_id, line_id))
                    line_id += 1
                region_id += 1
        return tokens


def _pages(data: bytes) -> list[LTPage]:
    # Imported here rather than at module scope: `extract_pages` pulls in most of
    # pdfminer, and nothing that merely imports this module should pay for it.
    from pdfminer.high_level import extract_pages

    try:
        return list(extract_pages(BytesIO(data)))
    except (PDFSyntaxError, ValueError, TypeError, AssertionError):
        # pdfminer reports a malformed file in several shapes. None of them may
        # travel: the message quotes the bytes it choked on.
        raise Refusal(RefusalCode.SOURCE_NOT_READABLE) from None


def _line_tokens(
    line: LTTextLine, page: int, region_id: int, line_id: int
) -> list[Token]:
    """Whitespace-separated runs of one line, each under the union of its
    characters' rectangles."""
    tokens = []
    for run in _runs(line):
        tokens.append(
            Token(
                text="".join(character.get_text() for character in run),
                page=page,
                region_id=region_id,
                line_id=line_id,
                x0=min(character.x0 for character in run),
                y0=min(character.y0 for character in run),
                x1=max(character.x1 for character in run),
                y1=max(character.y1 for character in run),
            )
        )
    return tokens


def _runs(line: LTTextLine) -> list[list[LTChar]]:
    """The line's characters grouped into words.

    Split on whitespace as the document draws it, so a word's rectangle covers
    the word and not the space beside it -- a rectangle wider than its quote
    highlights text the citation does not contain.
    """
    runs: list[list[LTChar]] = []
    current: list[LTChar] = []
    for item in line:
        if not isinstance(item, LTChar):
            continue
        if item.get_text().isspace():
            if current:
                runs.append(current)
                current = []
            continue
        current.append(item)
    if current:
        runs.append(current)
    return runs
