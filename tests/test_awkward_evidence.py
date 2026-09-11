"""One deliberately awkward document, through the paths that admit and read it.

Four of the six defects this file arrived with failed the same way: *the test
wrote the fixture, so the test could not see the assumption the fixture
encoded*. Every citation fixture in the suite used `page=1`, because every
fixture document was under sixty lines. Every extraction fixture separated its
words with spaces. Every ingestion fixture was short and clean.

So this fixture is awkward on purpose -- a tab-separated table row, a
non-breaking space, runs of spaces, a blank line, and enough lines that the
quote a module is asked to find sits on page two. It is driven through the real
`admit_pack`, the real `read_block`, the real `build_prompt` and the real
`verify_citations`, and the property it asserts is the one the system actually
promises: **text this repository delivered can be quoted back to it, and the
rectangle comes back.**

A unit test for each of those four steps would pass on a clean fixture and say
nothing about this one. The value here is the whole round trip over input
nobody would have chosen.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.citations import Citation, verify_citations
from server.evidence.extract import LINES_PER_PAGE
from server.evidence.ingest import Document, admit_pack
from server.evidence.read import read_block
from server.methodology.executor import Delivery, build_prompt
from server.store import StoreConnection

# Sixty filler lines, a blank one to close the region, then the table. The
# quote lands on page two, in a region of its own.
AWKWARD = (
    "\n".join(f"Section {n} of the annual report" for n in range(LINES_PER_PAGE - 1))
    + "\n\n"
    + "Facility\tDrawn\tUndrawn\n"
    + "Term loan B\tUSD 1,240.0m\N{NO-BREAK SPACE}drawn\tUSD    0.0m\n"
).encode()


@pytest.fixture
def admitted(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> tuple[StoreConnection, UUID]:
    conn, case_id = case
    [source_id] = admit_pack(
        conn,
        BlobStore(tmp_path / "blobs"),
        case_id=case_id,
        documents=[Document(filename=BoundaryText.of("facilities.txt"), data=AWKWARD)],
    )
    return conn, source_id


def _block(conn: StoreConnection, source_id: UUID, needle: str) -> str:
    row = conn.execute(
        "SELECT block_id FROM source_blocks WHERE source_id = %s AND text LIKE %s",
        (source_id, f"%{needle}%"),
    ).fetchone()
    assert row is not None, f"no block carries {needle!r}"
    return str(row[0])


def test_an_awkward_document_can_be_quoted_back_to_the_host(
    admitted: tuple[StoreConnection, UUID],
) -> None:
    """Admit, read, announce, cite. The whole promise in one pass."""
    conn, source_id = admitted
    block_id = _block(conn, source_id, "Term loan B")
    block = read_block(conn, source_id=source_id, block_id=block_id)

    # The host knows which page it read, and says so in the prompt.
    assert block.page == 2
    prompt = build_prompt(
        "CP-1",
        b"AUTHORITY",
        [
            Delivery(
                source_id=source_id,
                block_id=block_id,
                page=block.page,
                text=block.text,
            )
        ],
    )
    assert f"page: {block.page}" in prompt

    # A module quoting the delivered line verbatim is anchored, not refused.
    [anchored] = verify_citations(
        conn,
        delivered={source_id},
        citations=[
            Citation(
                source_id=source_id, page=block.page, matched_text=block.text.value
            )
        ],
    )
    assert anchored.page == 2
    assert anchored.bboxes, "an anchored citation carries its rectangle"
