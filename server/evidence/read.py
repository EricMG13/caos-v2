"""`read_evidence`: the host boundary a module receives evidence through.

Invariant 2: validated at the boundary, fails closed with a typed code, and **no
text is returned on refusal** -- not in the exception chain, the delivered set,
or the ledger. Every refusal here is raised `from None` for that reason: a
chained `psycopg` error carries the statement, and the statement carries the
identifiers a document was stored under.

One code answers every unavailable read. Distinguishing "no such source" from
"withdrawn" from "no such block" would tell a caller which of the three it
guessed right, and a caller entitled to know already has the delivered set.
Stored text retains historical typed BoundaryText refusals without its contents.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import psycopg

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection

# One read is one row fetch. The predecessor's blocks lived in a JSON column on
# the source row, so every read parsed every block: ~8x, the largest multiple in
# the measurements behind docs/AI_CODE_QUALITY.md. `test_io_budget_read_evidence`
# counts the round trips against this number.
IO_BUDGET = 1

_BLOCK_QUERY = (
    "SELECT blocks.page, blocks.text FROM source_blocks AS blocks"
    " JOIN live_sources USING (source_id)"
    " WHERE blocks.source_id = %s AND blocks.block_id = %s"
)
_RUN_BLOCK_QUERY = (
    "SELECT blocks.page, blocks.text FROM runs AS run"
    " JOIN run_inputs AS inputs ON (inputs.run_id,inputs.case_id)"
    " = (run.run_id,run.case_id)"
    " JOIN source_set_versions AS versions"
    " ON (versions.case_id,versions.version,versions.fingerprint)"
    " = (inputs.case_id,inputs.source_version,inputs.source_fingerprint)"
    " JOIN source_set_members AS members ON (members.case_id,members.version)"
    " = (versions.case_id,versions.version)"
    " JOIN live_sources AS sources ON (sources.case_id,sources.source_id)"
    " = (members.case_id,members.source_id)"
    " JOIN source_extractions AS extraction ON extraction.source_id = sources.source_id"
    " JOIN source_blocks AS blocks ON blocks.source_id = sources.source_id"
    " WHERE run.run_id = %s AND sources.source_id = %s AND blocks.block_id = %s"
    " AND members.document_sha256 = sources.document_sha256"
    " AND members.extractor_identity = extraction.extractor_identity"
    " AND members.output_sha256 = extraction.output_sha256"
    " AND members.extraction_sha256 = extraction.extraction_sha256"
)


@dataclass(frozen=True, slots=True)
class Block:
    """One block as the host holds it: its text, and the page it sits on.

    The page travels with the text because it is the host's fact and the
    module's obligation. A module cites the page it was told about, so a module
    told the wrong one writes a citation invariant 11 refuses -- for a quote
    that is really there, under a number nobody gave it a way to know.
    """

    page: int
    text: BoundaryText


def read_block(conn: StoreConnection, *, source_id: UUID, block_id: str) -> Block:
    """One block of one live source, or `EVIDENCE_NOT_AVAILABLE`.

    The join to `live_sources` is what makes withdrawal a live check at every use
    rather than a promise made when the source set was pinned (invariant 1).

    Still one row fetch: the page is a column of the row already being read, so
    `IO_BUDGET` is unchanged and there is no second path to a block that could
    forget the join above.
    """
    return _fetch_block(conn, _BLOCK_QUERY, (source_id,), block_id)


def read_run_block(
    conn: StoreConnection, *, run_id: UUID, source_id: UUID, block_id: str
) -> Block:
    """One live block with its run's exact captured membership and identity.

    This does not verify the complete pin hash, gates, actor or execution context.
    Later caller integration must use approved_run_input/execution_input first.
    Native immutable foreign keys bind stored run/case/route/version ownership.
    Both readers retain caller transactions, including on failure, and preserve
    historical BOUNDARY_TEXT_INVALID/TOO_LONG refusals for stored text.
    """
    return _fetch_block(conn, _RUN_BLOCK_QUERY, (run_id, source_id), block_id)


def _fetch_block(
    conn: StoreConnection, query: str, identifiers: tuple[UUID, ...], block_id: str
) -> Block:
    if any(not isinstance(value, UUID) for value in identifiers) or not _is_block_id(
        block_id
    ):
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE) from None
    try:
        row = conn.execute(query, (*identifiers, block_id)).fetchone()
    except psycopg.Error:
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE) from None
    if row is None:
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE) from None
    try:
        return Block(page=int(row[0]), text=BoundaryText.of(row[1]))
    except Refusal as refused:
        raise Refusal(refused.code) from None


def read_evidence(
    conn: StoreConnection, *, source_id: UUID, block_id: str
) -> BoundaryText:
    """The text of one block of one live source, or `EVIDENCE_NOT_AVAILABLE`.

    The named boundary of invariant 2, and a projection of `read_block` rather
    than a second query -- one statement, one live-source check, one refusal.
    """
    return read_block(conn, source_id=source_id, block_id=block_id).text


def _is_block_id(block_id: str) -> bool:
    # Ingest mints minimum-width-six ASCII ordinals, without alternate padding.
    return (
        isinstance(block_id, str)
        and len(block_id) >= 7
        and block_id[0] == "b"
        and block_id[1:].isascii()
        and block_id[1:].isdigit()
        and (len(block_id) == 7 or block_id[1] != "0")
    )
