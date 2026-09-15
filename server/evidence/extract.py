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

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import islice
from typing import Protocol

from server.boundary_text import BoundaryText
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


@dataclass(frozen=True, slots=True)
class AdmissionLimits:
    """Host policy ceilings, checked before the expensive step each bounds (§44.1).

    `max_documents` and `max_pack_bytes` bound the whole pack; `max_document_bytes`
    bounds one document, before its extractor ever runs. `max_pages`, `max_tokens`
    and `max_seconds` bound one document's extraction, checked cooperatively by the
    extractor itself -- per page for a PDF, per line for plain text -- so a
    document that crosses one refuses before the rest of it is read, not after.
    """

    max_documents: int
    max_document_bytes: int
    max_pack_bytes: int
    max_pages: int
    max_tokens: int
    max_seconds: float
    # What one PDF's compressed streams may inflate to, in total (§47).
    max_decoded_bytes: int


DEFAULT_LIMITS = AdmissionLimits(
    max_documents=50,
    max_document_bytes=20 * 1024 * 1024,
    max_pack_bytes=100 * 1024 * 1024,
    max_pages=500,
    max_tokens=500_000,
    max_seconds=60.0,
    max_decoded_bytes=256 * 1024 * 1024,
)


@dataclass(frozen=True, slots=True)
class ExtractorIdentity:
    """Host-owned algorithm/version and bounded flat effective configuration."""

    name: str
    version: str
    config: dict[str, str | int | float | bool | None]

    def canonical(self) -> str:
        if not self.name or not self.version or type(self.config) is not dict:
            raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
        texts = [self.name, self.version, *self.config]
        scalar_types = (str, int, float, bool, type(None))
        for value in self.config.values():
            if type(value) not in scalar_types:
                raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
            if isinstance(value, str):
                texts.append(value)
        for text in texts:
            if type(text) is not str or BoundaryText.of(text).value != text:
                raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
        canonical = json.dumps(
            {"name": self.name, "version": self.version, "config": self.config},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        BoundaryText.of(canonical)
        return canonical


class Extractor(Protocol):
    """Bytes to tokens. The one seam a real PDF extractor arrives through."""

    @property
    def identity(self) -> ExtractorIdentity: ...

    def extract(
        self,
        data: bytes,
        *,
        limits: AdmissionLimits = DEFAULT_LIMITS,
        deadline: float = float("inf"),
    ) -> list[Token]: ...


class ExtractorDispatch(Protocol):
    """Chooses the extractor for one document from its bytes (§44.6)."""

    def __call__(self, data: bytes) -> Extractor: ...


# Readers accept a PDF header anywhere in the first kilobyte, so a PDF with
# leading junk is still a PDF; past that it is not one any reader will open.
PDF_HEADER = b"%PDF-"
PDF_HEADER_WINDOW = 1024


def dispatch_by_content(data: bytes) -> Extractor:
    """A PDF by its header, plain text otherwise -- never by its filename.

    A name is whatever the uploader typed; the bytes are what the extractor
    will actually meet.
    """
    if PDF_HEADER in data[:PDF_HEADER_WINDOW]:
        # Imported here: `pdf` imports this module, and plain-text admission
        # should not pay for pdfminer.
        from server.evidence.pdf import PdfExtractor

        return PdfExtractor()
    return PlainTextExtractor()


@dataclass(frozen=True, slots=True)
class PlainTextExtractor:
    """UTF-8 text as tokens on a fixed-pitch page.

    Refuses `SOURCE_NOT_READABLE` for bytes that are not UTF-8, carrying the code
    and nothing else -- the offending bytes are exactly what must not travel.
    """

    @property
    def identity(self) -> ExtractorIdentity:
        return ExtractorIdentity(
            "caos.plain-text",
            "2",
            {
                "encoding": "utf-8",
                # Cells from the page's top-left corner, y down: the PDF
                # extractor's convention, with no crop or rotation to apply.
                "coordinates": "cell-top-left-pt",
                "cell_width": CELL_WIDTH,
                "cell_height": CELL_HEIGHT,
                "margin": MARGIN,
                "lines_per_page": LINES_PER_PAGE,
            },
        )

    def extract(
        self,
        data: bytes,
        *,
        limits: AdmissionLimits = DEFAULT_LIMITS,
        deadline: float = float("inf"),
    ) -> list[Token]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise Refusal(RefusalCode.SOURCE_NOT_READABLE) from None

        tokens: list[Token] = []
        region_id = 0
        for line_number, line in enumerate(text.splitlines()):
            # Checked per line (§44.2): cooperative, not preemptive -- one
            # pathological line can still overrun it (CLAUDE.md ledger).
            if time.monotonic() > deadline:
                raise Refusal(RefusalCode.SOURCE_EXTRACTION_TIMEOUT)
            page = line_number // LINES_PER_PAGE + 1
            if page > limits.max_pages:
                raise Refusal(RefusalCode.SOURCE_TOO_LARGE)
            if not line.strip():
                # A blank line closes the paragraph; the next non-blank one opens
                # a new region, so a quote cannot wrap across the gap.
                region_id += 1
                continue
            # One past the ceiling is enough to refuse: a line of a million
            # words never builds more (Phase 3 adversarial audit).
            words = _line_tokens(line, line_number, region_id)
            tokens.extend(islice(words, limits.max_tokens - len(tokens) + 1))
            if len(tokens) > limits.max_tokens:
                raise Refusal(RefusalCode.SOURCE_TOO_LARGE)
        return tokens


def _line_tokens(line: str, line_number: int, region_id: int) -> Iterator[Token]:
    page, row = divmod(line_number, LINES_PER_PAGE)
    top = MARGIN + row * CELL_HEIGHT
    for word, column in _words(line):
        yield Token(
            text=word,
            page=page + 1,
            region_id=region_id,
            line_id=line_number,
            x0=MARGIN + column * CELL_WIDTH,
            y0=top,
            x1=MARGIN + (column + len(word)) * CELL_WIDTH,
            y1=top + CELL_HEIGHT,
        )


def _words(line: str) -> Iterator[tuple[str, int]]:
    """Each whitespace-separated run with the column it starts at.

    Whitespace as `str.split()` draws it, not the space character alone.
    `server/evidence/citations.py` splits `matched_text` that way, so a token
    holding an interior tab is one the index can never be asked for: the line is
    delivered by `read_evidence` and the verbatim quote of it is then refused
    `CITATION_NOT_LOCATED`. The two have to agree on where a word ends, or the
    evidence a module was handed is evidence it cannot cite.
    """
    start: int | None = None
    for column, character in enumerate(line):
        if not character.isspace():
            if start is None:
                start = column
        elif start is not None:
            yield line[start:column], start
            start = None
    if start is not None:
        yield line[start:], start
