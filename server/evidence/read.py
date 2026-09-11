"""`read_evidence`: the host boundary a module receives evidence through.

Invariant 2: validated at the boundary, fails closed with a typed code, and **no
text is returned on refusal** -- not in the exception chain, the delivered set,
or the ledger. Every refusal here is raised `from None` for that reason: a
chained `psycopg` error carries the statement, and the statement carries the
identifiers a document was stored under.

One code answers every unavailable read. Distinguishing "no such source" from
"withdrawn" from "no such block" would tell a caller which of the three it
guessed right, and a caller entitled to know already has the delivered set.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from server.boundary_text import BoundaryText
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection

# One read is one row fetch. The predecessor's blocks lived in a JSON column on
# the source row, so every read parsed every block: ~8x, the largest multiple in
# the measurements behind docs/AI_CODE_QUALITY.md. `test_io_budget_read_evidence`
# counts the round trips against this number.
IO_BUDGET = 1

# A block id this repository minted: `b` and six digits (server/evidence/ingest).
# Checked before the store is touched, so a malformed one costs no round trip.
_BLOCK_ID_LENGTH = 7


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
    if not _is_block_id(block_id):
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)

    row = conn.execute(
        "SELECT blocks.page, blocks.text FROM source_blocks AS blocks"
        " JOIN live_sources USING (source_id)"
        " WHERE blocks.source_id = %s AND blocks.block_id = %s",
        (source_id, block_id),
    ).fetchone()
    if row is None:
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)
    return Block(page=int(row[0]), text=BoundaryText.of(row[1]))


def read_evidence(
    conn: StoreConnection, *, source_id: UUID, block_id: str
) -> BoundaryText:
    """The text of one block of one live source, or `EVIDENCE_NOT_AVAILABLE`.

    The named boundary of invariant 2, and a projection of `read_block` rather
    than a second query -- one statement, one live-source check, one refusal.
    """
    return read_block(conn, source_id=source_id, block_id=block_id).text


def _is_block_id(block_id: str) -> bool:
    return (
        len(block_id) == _BLOCK_ID_LENGTH
        and block_id[0] == "b"
        and block_id[1:].isdigit()
    )
