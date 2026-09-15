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

Rectangles are given in one convention whatever the page (§44.3): points from
the CropBox's top-left corner as the page is displayed, after `/Rotate`, with y
growing downward. Identity version 2 declares it beside the layout parameters
that decide where a word, a line and a region end.

Nothing above this module changes. It implements the same `Extractor` protocol,
so ingestion, block packing, citation anchoring and every refusal are the ones
already tested -- which is what a seam is for.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from importlib.metadata import version
from io import BytesIO
from typing import TYPE_CHECKING, TypedDict

from pdfminer.layout import LAParams, LTAnno, LTChar, LTPage, LTTextBox, LTTextLine
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.utils import apply_matrix_rect

from server.evidence.extract import (
    DEFAULT_LIMITS,
    AdmissionLimits,
    ExtractorIdentity,
    Token,
)
from server.refusals import Refusal, RefusalCode

if TYPE_CHECKING:
    from pdfminer.pdfpage import PDFPage


class _Layout(TypedDict):
    line_overlap: float
    char_margin: float
    line_margin: float
    word_margin: float
    boxes_flow: float
    detect_vertical: bool
    all_texts: bool


# The layout analysis pdfminer runs with, stated rather than inherited: these
# are pdfminer's own defaults, pinned here so the identity names the scalars
# that decide where a word, a line and a region end.
LAYOUT: _Layout = {
    "line_overlap": 0.5,
    "char_margin": 2.0,
    "line_margin": 0.5,
    "word_margin": 0.1,
    "boxes_flow": 0.5,
    "detect_vertical": False,
    "all_texts": False,
}
COORDINATES = "crop-top-left-rotated-pt"
# A token not wholly inside the crop is text no reader sees: dropped, not clipped.
CROP_POLICY = "drop-outside"

Frame = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class PdfExtractor:
    """Bytes of a PDF, as tokens with real coordinates."""

    @property
    def identity(self) -> ExtractorIdentity:
        # Everything that decides the tokens: engine, layout, convention, crop.
        return ExtractorIdentity(
            "caos.pdfminer",
            "2",
            {
                "pdfminer_version": version("pdfminer.six"),
                "line_overlap": LAYOUT["line_overlap"],
                "char_margin": LAYOUT["char_margin"],
                "line_margin": LAYOUT["line_margin"],
                "word_margin": LAYOUT["word_margin"],
                "boxes_flow": LAYOUT["boxes_flow"],
                "detect_vertical": LAYOUT["detect_vertical"],
                "all_texts": LAYOUT["all_texts"],
                "coordinates": COORDINATES,
                "crop_policy": CROP_POLICY,
                "password": "",
                "page_numbers": "all",
                "maxpages": 0,
                "caching": True,
            },
        )

    def extract(
        self,
        data: bytes,
        *,
        limits: AdmissionLimits = DEFAULT_LIMITS,
        deadline: float = float("inf"),
    ) -> list[Token]:
        """Refuses `SOURCE_NOT_READABLE` for bytes that are not a readable PDF.

        A scanned page parses fine and yields no tokens; that is not an error
        here, and `admit_pack` refuses it as `SOURCE_HAS_NO_TEXT` -- the code
        that says what is actually wrong with it.

        Pages come from `_pages` one at a time, and the page and time ceilings
        are checked before a page's boxes are walked -- so a document that
        crosses `max_pages` stops pulling pages from pdfminer's own generator
        rather than paying to lay out every remaining page first (§44.1/§44.2).
        """
        tokens: list[Token] = []
        region_id = 0
        line_id = 0
        for page_number, (frame, page) in enumerate(_pages(data), start=1):
            if page_number > limits.max_pages:
                raise Refusal(RefusalCode.SOURCE_TOO_LARGE)
            # Checked per page (§44.2): cooperative, not preemptive -- one
            # pathological page can still overrun it (CLAUDE.md ledger).
            if time.monotonic() > deadline:
                raise Refusal(RefusalCode.SOURCE_EXTRACTION_TIMEOUT)
            if frame is None:
                # Nothing on the page is visible, so nothing on it is citable.
                continue
            for box in page:
                if not isinstance(box, LTTextBox):
                    continue
                for line in box:
                    if not isinstance(line, LTTextLine):
                        continue
                    tokens.extend(
                        _line_tokens(line, frame, page_number, region_id, line_id)
                    )
                    if len(tokens) > limits.max_tokens:
                        raise Refusal(RefusalCode.SOURCE_TOO_LARGE)
                    line_id += 1
                region_id += 1
        return tokens


def _pages(data: bytes) -> Iterator[tuple[Frame | None, LTPage]]:
    """Each page's layout beside its visible crop in the layout's own space.

    `extract_pages`, written out so the `PDFPage` -- which carries the crop and
    the rotation, and which `extract_pages` does not hand back -- stays in hand.
    """
    # Imported here rather than at module scope: the interpreter pulls in most
    # of pdfminer, and nothing that merely imports this module should pay for it.
    from pdfminer.converter import PDFPageAggregator
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
    from pdfminer.pdfpage import PDFPage

    # Yielding inside this try keeps the whole walk lazy -- a caller that stops
    # asking for pages (the page ceiling above) never drives pdfminer's
    # generator past the one that crossed it -- while still catching a
    # malformed file however far into the walk it turns up malformed.
    try:
        resources = PDFResourceManager(caching=True)
        device = PDFPageAggregator(resources, laparams=LAParams(**LAYOUT))
        interpreter = PDFPageInterpreter(resources, device)
        for page in PDFPage.get_pages(BytesIO(data), caching=True):
            frame = _crop_frame(page)
            interpreter.process_page(page)
            yield frame, device.get_result()
    except (PDFSyntaxError, ValueError, TypeError, AssertionError):
        # pdfminer reports a malformed file in several shapes. None of them may
        # travel: the message quotes the bytes it choked on.
        raise Refusal(RefusalCode.SOURCE_NOT_READABLE) from None


def _crop_frame(page: PDFPage) -> Frame | None:
    """The visible region, in the rotated y-up space pdfminer lays a page out in,
    or `None` when the CropBox clipped to the MediaBox is empty on either axis.

    `PDFPageInterpreter.process_page` maps user space through a matrix built
    from the MediaBox and `/Rotate`; this is that matrix, applied to the
    CropBox clipped to the MediaBox (the PDF specification's visible region),
    so the frame and every character sit in one space. A rotation that is not
    a quarter turn is refused: pdfminer would lay it out unrotated, and the
    convention could not say what a reader sees.
    """
    if page.rotate not in (0, 90, 180, 270):
        raise Refusal(RefusalCode.SOURCE_NOT_READABLE)
    (x0, y0, x1, y1) = page.mediabox
    ctm = {
        90: (0, -1, 1, 0, -y0, x1),
        180: (-1, 0, 0, -1, x1, y1),
        270: (0, 1, -1, 0, y1, -x0),
    }.get(page.rotate, (1, 0, 0, 1, -x0, -y0))
    (m0, n0, m1, n1) = _ordered(page.mediabox)
    (c0, d0, c1, d1) = _ordered(page.cropbox)
    visible = (max(m0, c0), max(n0, d0), min(m1, c1), min(n1, d1))
    if visible[0] >= visible[2] or visible[1] >= visible[3]:
        # Clipped to nothing. `apply_matrix_rect` would normalise the inverted
        # rectangle into one covering the gap between the boxes -- text no
        # reader sees -- so an empty visible area is no frame at all.
        return None
    return apply_matrix_rect(ctm, visible)


def _ordered(rect: Frame) -> Frame:
    (x0, y0, x1, y1) = rect
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _line_tokens(
    line: LTTextLine, frame: Frame, page: int, region_id: int, line_id: int
) -> list[Token]:
    """Whitespace-separated runs of one line, each under the union of its
    characters' rectangles, measured from the crop's top-left corner.

    A run not wholly inside the crop is dropped: a clipped rectangle would
    anchor a quote whose other half no reader can see. A page whose crop misses
    the MediaBox has no frame and never reaches here (`extract` skips it).
    Membership uses pdfminer's full glyph box, descent included, so a word
    whose baseline is inside the edge but whose box crosses it is dropped.
    """
    (left, bottom, right, top) = frame
    tokens = []
    for run in _runs(line):
        x0 = min(character.x0 for character in run)
        y0 = min(character.y0 for character in run)
        x1 = max(character.x1 for character in run)
        y1 = max(character.y1 for character in run)
        if not (left <= x0 and x1 <= right and bottom <= y0 and y1 <= top):
            continue
        tokens.append(
            Token(
                text="".join(character.get_text() for character in run),
                page=page,
                region_id=region_id,
                line_id=line_id,
                x0=x0 - left,
                y0=top - y1,
                x1=x1 - left,
                y1=top - y0,
            )
        )
    return tokens


def _runs(line: LTTextLine) -> list[list[LTChar]]:
    """The line's characters grouped into words.

    Split on whitespace as the document draws it, so a word's rectangle covers
    the word and not the space beside it -- a rectangle wider than its quote
    highlights text the citation does not contain.

    A word break is not only a drawn space glyph: pdfminer's own layout
    analysis (`LTTextLineHorizontal.add`) inserts a virtual `LTAnno(" ")`
    between two characters whose gap exceeds `laparams.word_margin` times the
    character's own width or height -- which is how two glyphs positioned by a
    `TJ` kerning array with no space character between them are recognised as
    two words rather than one run of letters (§44.5: glyph merging follows
    pdfminer's `word_margin`, no custom heuristic). `LTAnno` carries no
    rectangle, so it never becomes part of a run; it only ends one.
    """
    runs: list[list[LTChar]] = []
    current: list[LTChar] = []
    for item in line:
        if isinstance(item, LTAnno):
            if item.get_text().isspace() and current:
                runs.append(current)
                current = []
            continue
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
