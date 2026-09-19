"""Per-node evidence selection from CP-0's T8 `Source files to attach` (§95).

The gate's accepted T8 carries, per consumer module, the vendor's own
`Recommendation.source_files_to_attach` (§92, one reader of one table). The
host maps that cell to the run's pinned source-set members and delivers a
consumer only those members' blocks. Everything here is a pure function of
pinned inputs -- the accepted CP-0 Markdown, the pinned members, the module
id -- so every reader that builds a node's context (the pre-call check, the
attempt, a crash replay) selects the same blocks (invariant 10), and no host
rule invents a demand the gate did not write (invariant 4).

Three outcomes, fail-closed in the direction that matters:

- **named**: every item of the cell maps to exactly one member -- by its
  admitted filename or its document digest -- and the node is handed those
  members and nothing else.
- **whole**: the cell is empty, or names nothing the pin carries. The host
  cannot read it as a selection, so it delivers what every run before §95
  delivered. Narrowing on a guess would turn a truthful quote of an unnamed
  source into `CITATION_NOT_DELIVERED` (§88.2); a whole delivery weakens no
  invariant, and a prompt too wide for the ceiling still refuses
  `CONTEXT_OVER_CEILING` rather than truncating.
- **refused**: the cell is half-readable -- some items map and some do not --
  or an item maps to more than one member. Either narrowing to the readable
  half or widening to the whole would decide something the gate did not say,
  so the node refuses `EVIDENCE_DEMAND_UNRESOLVED` before any attempt,
  reservation or call. The discharge is a successor run whose CP-0 writes a
  cell the host can read.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from server.refusals import Refusal, RefusalCode
from server.store.source_sets import SourceSetMember

# The vendor's reading of the cell (`navigation.parse_t8`) is the only reader
# of the table; this module reads its parsed row and never the Markdown.
type VendorNavigation = Any

# A cell lists files; these separate its items. A filename carrying one of them
# is matched whole first, so a single such name still reads.
_SEPARATORS = re.compile(r"[;,\n]|<br\s*/?>", re.IGNORECASE)
# Backtick, the ASCII quotes and the four curly ones, spelled by code point so
# no lookalike character sits in the source.
_WRAPPING = "`'\"" + "".join(map(chr, (0x201C, 0x201D, 0x2018, 0x2019)))
_DIGEST = re.compile(r"[0-9a-f]{64}")


class Basis(StrEnum):
    """Why a node was handed the members it was handed."""

    # No T8 row names the module, or its cell is empty.
    WHOLE_NO_DEMAND = "WHOLE_NO_DEMAND"
    # The cell names nothing the pin carries: not a selection the host can act on.
    WHOLE_UNMAPPED = "WHOLE_UNMAPPED"
    # Every item mapped to exactly one pinned member.
    NAMED = "NAMED"


@dataclass(frozen=True, slots=True)
class Selection:
    """The members one node is handed; `source_ids` is None for the whole pin."""

    basis: Basis
    source_ids: frozenset[UUID] | None

    @property
    def whole(self) -> bool:
        return self.source_ids is None


def demand_cells(
    navigation: VendorNavigation, catalog: Mapping[str, Any], gate_markdown: bytes
) -> dict[str, str]:
    """Each consumer module's `Source files to attach` cell, from the accepted
    CP-0 Markdown through the vendor's own T8 parser and no other reader.

    The Markdown is one the caller has already verified as the accepted gate
    record's, so the parse cannot fail; if it does, the code is the one the
    gate's own validation gives an unreadable T8, and nothing of the text
    travels with it.
    """
    try:
        rows = navigation.parse_t8(
            gate_markdown.decode("utf-8"), navigation.validate_catalog(catalog)
        )
        return {str(row.module_id): str(row.source_files_to_attach) for row in rows}
    except Exception:  # noqa: BLE001 -- any failure inside is this refusal
        raise Refusal(RefusalCode.HANDOFF_INCOMPLETE) from None


def demand_items(cell: str) -> tuple[str, ...]:
    """The cell's items in written order, each stripped of whitespace and
    wrapping quotation; an empty cell has none."""
    return tuple(
        stripped
        for item in _SEPARATORS.split(cell)
        if (stripped := item.strip().strip(_WRAPPING).strip())
    )


def select_sources(members: Sequence[SourceSetMember], cell: str | None) -> Selection:
    """The pure rule: `cell` against the pinned members, as documented above.

    Deterministic in the members' order: the answer is a set. Refuses
    `EVIDENCE_DEMAND_UNRESOLVED` for a half-readable cell or an item naming
    more than one member; the refusal carries no item text.
    """
    if cell is None:
        return Selection(Basis.WHOLE_NO_DEMAND, None)
    whole = cell.strip().strip(_WRAPPING).strip()
    items = (whole,) if whole and _matching(members, whole) else demand_items(cell)
    if not items:
        return Selection(Basis.WHOLE_NO_DEMAND, None)
    mapped: set[UUID] = set()
    unmapped = 0
    for item in items:
        found = _matching(members, item)
        if len(found) > 1:
            raise Refusal(RefusalCode.EVIDENCE_DEMAND_UNRESOLVED)
        if found:
            mapped |= found
        else:
            unmapped += 1
    if not mapped:
        return Selection(Basis.WHOLE_UNMAPPED, None)
    if unmapped:
        raise Refusal(RefusalCode.EVIDENCE_DEMAND_UNRESOLVED)
    return Selection(Basis.NAMED, frozenset(mapped))


def _matching(members: Sequence[SourceSetMember], item: str) -> set[UUID]:
    """The members `item` names: its admitted filename, exactly, or its
    document digest (any case). A digest names the document, so two members
    of one document both answer, and that ambiguity is the caller's to refuse."""
    digest = item.lower() if _DIGEST.fullmatch(item.lower()) else None
    return {
        member.source_id
        for member in members
        if member.filename == item or member.document_sha256 == digest
    }
