"""Limits before the expensive step, and a deadline both extractors keep (§44.1/§44.2).

Nothing bounded a pack before this: a document held whole in memory, extracted
whole before any ceiling was consulted. `AdmissionLimits` states the numbers
host policy accepts, `admit_pack` refuses a pack that crosses the cheap ones
(document count, pack bytes, one document's bytes) before any extractor runs,
and each extractor refuses the expensive ones (pages, tokens, time) as it walks
its own document -- cooperatively, so a document already over a ceiling stops
without finishing the rest of the walk that would have proven it.
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from typing import cast
from uuid import UUID

import pdfminer.high_level
import pytest
from pdfminer.layout import LTPage
from test_pdf_extraction import LEFT_MARGIN, raw_pdf

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.extract import (
    DEFAULT_LIMITS,
    AdmissionLimits,
    Extractor,
    PlainTextExtractor,
    Token,
)
from server.evidence.ingest import Document, admit_pack
from server.evidence.pdf import PdfExtractor
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection

TEXT = b"alpha beta\ngamma delta\n"


def _document(name: str, data: bytes) -> Document:
    return Document(filename=BoundaryText.of(name), data=data)


def _limits(  # noqa: PLR0913 -- every field of AdmissionLimits, keyword-only
    *,
    max_documents: int = DEFAULT_LIMITS.max_documents,
    max_document_bytes: int = DEFAULT_LIMITS.max_document_bytes,
    max_pack_bytes: int = DEFAULT_LIMITS.max_pack_bytes,
    max_pages: int = DEFAULT_LIMITS.max_pages,
    max_tokens: int = DEFAULT_LIMITS.max_tokens,
    max_seconds: float = DEFAULT_LIMITS.max_seconds,
) -> AdmissionLimits:
    return AdmissionLimits(
        max_documents=max_documents,
        max_document_bytes=max_document_bytes,
        max_pack_bytes=max_pack_bytes,
        max_pages=max_pages,
        max_tokens=max_tokens,
        max_seconds=max_seconds,
    )


def _rows(conn: StoreConnection) -> int:
    total = 0
    for table in ("sources", "source_tokens", "source_blocks", "source_extractions"):
        row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
        assert row is not None
        total += int(row[0])
    return total


class _Spy:
    """Records whether it was ever asked to extract; never really is."""

    identity = PlainTextExtractor().identity
    called = False

    def extract(
        self, data: bytes, *, limits: AdmissionLimits, deadline: float
    ) -> list[Token]:
        type(self).called = True
        return PlainTextExtractor().extract(data, limits=limits, deadline=deadline)


def test_an_oversized_document_is_refused_before_extraction(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    conn, case_id = case
    _Spy.called = False
    tiny = _limits(max_document_bytes=4)

    with pytest.raises(Refusal) as caught:
        admit_pack(
            conn,
            BlobStore(tmp_path),
            case_id=case_id,
            documents=[_document("memo.txt", TEXT)],
            dispatch=lambda data: cast(Extractor, _Spy()),
            limits=tiny,
        )

    assert caught.value.code is RefusalCode.SOURCE_TOO_LARGE
    assert _Spy.called is False, "the ceiling refused it before any extractor ran"
    assert _rows(conn) == 0


@pytest.mark.parametrize(
    "limits",
    [
        pytest.param(_limits(max_documents=1), id="too many documents"),
        pytest.param(_limits(max_pack_bytes=len(TEXT)), id="too many bytes total"),
    ],
)
def test_a_pack_over_the_document_or_byte_ceiling_is_refused(
    case: tuple[StoreConnection, UUID], tmp_path: Path, limits: AdmissionLimits
) -> None:
    conn, case_id = case

    with pytest.raises(Refusal) as caught:
        admit_pack(
            conn,
            BlobStore(tmp_path),
            case_id=case_id,
            documents=[_document("one.txt", TEXT), _document("two.txt", TEXT)],
            limits=limits,
        )

    assert caught.value.code is RefusalCode.SOURCE_TOO_LARGE
    assert _rows(conn) == 0


def multi_page_pdf(contents: list[bytes]) -> bytes:
    """A PDF of `len(contents)` pages, each page's stream exactly one entry.

    Written the way `raw_pdf` is, object by object, so the fixture stays a
    plain byte string with no dependency of its own -- extended here to more
    than the one page `raw_pdf` builds.
    """
    count = len(contents)
    font_object = 3 + 2 * count
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(f"{3 + i} 0 R".encode() for i in range(count))
        + b"] /Count "
        + str(count).encode()
        + b" >>",
    ]
    for i in range(count):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 "
            + str(font_object).encode()
            + b" 0 R >> >> /Contents "
            + str(3 + count + i).encode()
            + b" 0 R >>"
        )
    for content in contents:
        objects.append(
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    start_xref = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(start_xref).encode()
        + b"\n%%EOF\n"
    )
    return bytes(out)


def _page(line: str) -> bytes:
    return (
        f"BT\n/F1 12 Tf\n1 0 0 1 {LEFT_MARGIN:.0f} 700 Tm\n({line}) Tj\nET\n"
    ).encode("ascii")


def test_pages_over_the_ceiling_refuse_without_parsing_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A page ceiling of one still has to learn a second page exists -- pulling
    it from pdfminer's own generator is unavoidable -- but must never pull a
    third. `extract_pages` is spied on to count exactly how many pages the
    walk actually asked pdfminer to lay out."""
    real = pdfminer.high_level.extract_pages
    seen: list[LTPage] = []

    def spy(pdf_file: BytesIO) -> Iterator[LTPage]:
        for page in real(pdf_file):
            seen.append(page)
            yield page

    monkeypatch.setattr(pdfminer.high_level, "extract_pages", spy)
    data = multi_page_pdf([_page("Page one"), _page("Page two"), _page("Page three")])
    limits = _limits(max_pages=1)

    with pytest.raises(Refusal) as caught:
        PdfExtractor().extract(data, limits=limits, deadline=float("inf"))

    assert caught.value.code is RefusalCode.SOURCE_TOO_LARGE
    assert len(seen) == 2, "the page that crossed the ceiling, never the one after it"


def test_tokens_over_the_ceiling_refuse() -> None:
    limits = _limits(max_tokens=2)

    with pytest.raises(Refusal) as caught:
        PlainTextExtractor().extract(
            b"alpha beta gamma delta\n", limits=limits, deadline=float("inf")
        )

    assert caught.value.code is RefusalCode.SOURCE_TOO_LARGE


def test_tokens_over_the_ceiling_refuse_in_a_pdf_too() -> None:
    limits = _limits(max_tokens=1)
    data = raw_pdf(b"BT\n/F1 12 Tf\n1 0 0 1 72 700 Tm\n(Alpha Beta Gamma) Tj\nET\n")

    with pytest.raises(Refusal) as caught:
        PdfExtractor().extract(data, limits=limits, deadline=float("inf"))

    assert caught.value.code is RefusalCode.SOURCE_TOO_LARGE


@pytest.mark.parametrize(
    "extractor",
    [
        pytest.param(PlainTextExtractor(), id="plain text"),
        pytest.param(PdfExtractor(), id="pdf"),
    ],
)
def test_extraction_past_the_deadline_refuses(
    extractor: Extractor, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deadline already past refuses on the first cooperative check -- no
    real sleep, since the deadline itself is what is manipulated."""
    import time

    past = time.monotonic() - 1
    if isinstance(extractor, PdfExtractor):
        data = raw_pdf(b"BT\n/F1 12 Tf\n1 0 0 1 72 700 Tm\n(Alpha) Tj\nET\n")
    else:
        data = TEXT

    with pytest.raises(Refusal) as caught:
        extractor.extract(data, limits=DEFAULT_LIMITS, deadline=past)

    assert caught.value.code is RefusalCode.SOURCE_EXTRACTION_TIMEOUT


def test_a_document_under_every_limit_still_admits(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    """Guard: the ceilings above must not narrow an ordinary admission."""
    conn, case_id = case

    sources = admit_pack(
        conn,
        BlobStore(tmp_path),
        case_id=case_id,
        documents=[_document("memo.txt", TEXT)],
        limits=DEFAULT_LIMITS,
    )

    assert len(sources) == 1
    assert _rows(conn) > 0
