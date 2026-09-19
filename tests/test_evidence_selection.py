"""Per-node evidence selection from CP-0's T8 `Source files to attach` (§95).

The gate's accepted row for a consumer names the pinned sources it is to be
handed; the host maps the names to members and delivers only their blocks, so
a quote of an unnamed pinned source is refused `CITATION_NOT_DELIVERED` on a
real run shape for the first time. A row the host cannot read as a selection
delivers the whole pin, as every run before; a half-readable row refuses before
any attempt. The rule is pure over pinned inputs, so every reader selects alike.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from canonical_fixtures import CATALOG, CONTRACT, CanonicalCompletions
from test_canonical_execution import (
    _accept,
    _node,
    _refused,
    _run,
    harness,
    route,
)
from test_execution_freshness import _counts, _Harness
from test_loop_charges import REPORTED

from server.methodology import canonical
from server.methodology.canonical import check_context
from server.methodology.executor import Assignment
from server.methodology.invocation import prospective_identity
from server.methodology.selection import (
    Basis,
    Selection,
    demand_cells,
    demand_items,
    select_sources,
)
from server.refusals import Refusal, RefusalCode
from server.store.source_sets import SourceSetMember

__all__ = ["harness", "route"]

# The harness admits two documents: `report.txt` (its `source_id`) and
# `uncited.txt` (its `witness_id`), whose one line is below.
WITNESS_QUOTE = "Captured but deliberately not delivered."
REPORT = "report.txt"
WITNESS = "uncited.txt"


def _member(filename: str, digest: str | None = None) -> SourceSetMember:
    return SourceSetMember(
        source_id=uuid4(),
        document_sha256=digest or ("ab" * 32),
        filename=filename,
        admitted_at="2026-09-18T00:00:00+00:00",
        extractor_identity="{}",
        output_sha256="cd" * 32,
        extraction_sha256="ef" * 32,
    )


# --- the pure rule -----------------------------------------------------------


def test_an_absent_or_empty_cell_is_no_demand_and_selects_the_whole_pin() -> None:
    members = (_member("a.txt"), _member("b.txt"))
    assert select_sources(members, None) == Selection(Basis.WHOLE_NO_DEMAND, None)
    assert select_sources(members, "") == Selection(Basis.WHOLE_NO_DEMAND, None)
    assert select_sources(members, "  ; , ") == Selection(Basis.WHOLE_NO_DEMAND, None)
    assert demand_items("") == ()


def test_a_cell_naming_nothing_the_pin_carries_is_read_as_no_selection() -> None:
    """The fixtures' `Source p1` is this case: nothing narrows, as before §95."""
    members = (_member("a.txt"), _member("b.txt"))
    found = select_sources(members, "Source p1")
    assert found == Selection(Basis.WHOLE_UNMAPPED, None) and found.whole


def test_every_item_mapping_to_one_member_selects_exactly_those_members() -> None:
    a, b, c = _member("a.txt"), _member("b.txt", "12" * 32), _member("c.txt")
    members = (a, b, c)
    assert select_sources(members, "a.txt") == Selection(
        Basis.NAMED, frozenset({a.source_id})
    )
    assert select_sources(members, '`a.txt`; "c.txt"') == Selection(
        Basis.NAMED, frozenset({a.source_id, c.source_id})
    )
    assert select_sources(members, "a.txt, c.txt\nc.txt") == Selection(
        Basis.NAMED, frozenset({a.source_id, c.source_id})
    )
    # A document digest names its member too, in any case.
    assert select_sources(members, ("12" * 32).upper()) == Selection(
        Basis.NAMED, frozenset({b.source_id})
    )
    assert demand_items("a.txt; c.txt<br>b.txt") == ("a.txt", "c.txt", "b.txt")


def test_a_filename_is_matched_as_cp0_was_shown_it() -> None:
    """CP-0 is shown `invocation._printable(filename)`, which drops U+2028,
    U+2029 and U+FEFF; a name copied back as shown must still name its member,
    or a readable neighbour turns the cell half-readable and refuses the node
    permanently (the wave-four acceptance review's P3)."""
    shown, other = _member("Q4\u2028results.txt"), _member("other.txt")
    assert select_sources((shown, other), "Q4results.txt; other.txt") == Selection(
        Basis.NAMED, frozenset({shown.source_id, other.source_id})
    )


def test_a_filename_carrying_a_separator_is_matched_whole_first() -> None:
    odd = _member("Q4 2026, release.txt")
    other = _member("release.txt")
    assert select_sources((odd, other), " Q4 2026, release.txt ") == Selection(
        Basis.NAMED, frozenset({odd.source_id})
    )


def test_a_half_readable_cell_is_refused_not_narrowed_and_not_widened() -> None:
    """§88.2's hazard: narrowing to the readable half would turn a truthful
    quote of the unread half into `CITATION_NOT_DELIVERED`; widening would
    discard a demand the gate stated."""
    members = (_member("a.txt"), _member("b.txt"))
    with pytest.raises(Refusal) as refused:
        select_sources(members, "a.txt; the prepared artifact")
    assert refused.value.code is RefusalCode.EVIDENCE_DEMAND_UNRESOLVED
    assert refused.value.__context__ is None and refused.value.__cause__ is None


def test_a_name_two_members_answer_to_is_refused() -> None:
    twins = (_member("same.txt"), _member("same.txt"), _member("other.txt"))
    with pytest.raises(Refusal) as refused:
        select_sources(twins, "same.txt")
    assert refused.value.code is RefusalCode.EVIDENCE_DEMAND_UNRESOLVED
    # A digest shared by two members is the same ambiguity.
    shared = (_member("x.txt", "34" * 32), _member("y.txt", "34" * 32))
    with pytest.raises(Refusal):
        select_sources(shared, "34" * 32)


def test_selection_is_a_pure_function_of_its_inputs() -> None:
    a, b = _member("a.txt"), _member("b.txt")
    assert select_sources((a, b), "b.txt; a.txt") == select_sources(
        (b, a), "a.txt, b.txt"
    )


# --- the run shape -----------------------------------------------------------


def _gate(harness: _Harness, source_files: dict[str, str]) -> CanonicalCompletions:
    completions = CanonicalCompletions(harness.source_id, source_files=source_files)
    attempt, result = _run(harness, "CP-0", completions)
    _accept(harness, attempt, result)
    return completions


def _evidence_sources(prompt: str) -> set[str]:
    return {
        line.removeprefix("source_id: ")
        for line in prompt.splitlines()
        if line.startswith("source_id: ")
    }


def test_the_gate_cell_is_read_through_the_vendors_own_parser(
    harness: _Harness,
) -> None:
    completions = _gate(harness, {"CP-L10": REPORT, "CP-5": f"{REPORT}; {WITNESS}"})
    cells = demand_cells(CONTRACT.navigation, CATALOG, completions.answers[0])
    assert cells == {"CP-L10": REPORT, "CP-5": f"{REPORT}; {WITNESS}"}
    with pytest.raises(Refusal) as refused:
        demand_cells(CONTRACT.navigation, CATALOG, b"no table here")
    assert refused.value.code is RefusalCode.HANDOFF_INCOMPLETE


def test_a_node_is_handed_only_the_members_its_gate_row_names(
    harness: _Harness,
) -> None:
    _gate(harness, {"CP-L10": REPORT})
    screen = CanonicalCompletions(harness.source_id)
    attempt, result = _run(harness, "CP-L10", screen)
    [prompt] = screen.prompts
    assert _evidence_sources(prompt) == {str(harness.source_id)}
    assert WITNESS_QUOTE not in prompt
    _accept(harness, attempt, result)
    assert _counts(harness)[2] == 2


def test_an_absent_demand_delivers_the_whole_pin_as_before(harness: _Harness) -> None:
    """Every existing fixture writes `Source p1`, which names no member."""
    _gate(harness, {})
    screen = CanonicalCompletions(
        harness.source_id, cited=((harness.witness_id, WITNESS_QUOTE),)
    )
    attempt, result = _run(harness, "CP-L10", screen)
    [prompt] = screen.prompts
    assert _evidence_sources(prompt) == {
        str(harness.source_id),
        str(harness.witness_id),
    }
    _accept(harness, attempt, result)


def test_a_quote_on_an_undelivered_member_is_refused_on_a_real_run(
    harness: _Harness,
) -> None:
    """The first real run shape on which `CITATION_NOT_DELIVERED` fires: the
    witness is pinned, live, captured and not named for CP-L10."""
    _gate(harness, {"CP-L10": REPORT})
    screen = CanonicalCompletions(
        harness.source_id, cited=((harness.witness_id, WITNESS_QUOTE),)
    )
    assert _refused(harness, "CP-L10", screen) is RefusalCode.CITATION_NOT_DELIVERED
    [prompt] = screen.prompts
    assert WITNESS_QUOTE not in prompt
    # Billed and recorded, no artifact for the screen: one attempt each.
    assert _counts(harness) == (2, [REPORTED, REPORTED], 1, 2, 2)


def test_a_demand_the_host_half_reads_is_refused_before_any_attempt(
    harness: _Harness,
) -> None:
    _gate(harness, {"CP-L10": f"{REPORT}; a prepared artifact"})
    node = _node(harness, "CP-L10")
    with pytest.raises(Refusal) as refused:
        check_context(
            harness.conn,
            harness.bundle,
            harness.blobs,
            run_id=harness.run_id,
            route=harness.route,
            node=node,
            provider=CanonicalCompletions(harness.source_id),
        )
    assert refused.value.code is RefusalCode.EVIDENCE_DEMAND_UNRESOLVED
    harness.conn.rollback()
    # Only the gate's attempt exists; nothing was reserved or called for CP-L10.
    assert _counts(harness) == (1, [REPORTED], 1, 1, 1)
    screen = CanonicalCompletions(harness.source_id)
    assert _refused(harness, "CP-L10", screen) is RefusalCode.EVIDENCE_DEMAND_UNRESOLVED
    assert screen.prompts == []


def test_every_reader_of_the_context_selects_the_same_blocks(harness: _Harness) -> None:
    """Pure over the pins: the pre-call unit and a replay build one delivery."""
    _gate(harness, {"CP-L10": REPORT})
    node = _node(harness, "CP-L10")
    assignment = Assignment(
        node.module_id, harness.run_id, node, harness.route, UUID(int=0)
    )

    def context() -> canonical._Context:
        identity = prospective_identity(
            harness.conn,
            harness.bundle,
            run_id=harness.run_id,
            route=harness.route,
            node=node,
        )
        built = canonical._context(
            harness.conn, harness.blobs, harness.bundle, assignment, identity
        )
        harness.conn.rollback()
        return built

    first, second = context(), context()
    assert (
        first.selection
        == second.selection
        == Selection(Basis.NAMED, frozenset({harness.source_id}))
    )
    assert first.delivered == second.delivered
    assert {d.source_id for d in first.delivered} == {harness.source_id}


def test_the_gate_itself_is_always_handed_the_whole_pin(harness: _Harness) -> None:
    node = _node(harness, "CP-0")
    assignment = Assignment(
        node.module_id, harness.run_id, node, harness.route, UUID(int=0)
    )
    identity = prospective_identity(
        harness.conn,
        harness.bundle,
        run_id=harness.run_id,
        route=harness.route,
        node=node,
    )
    built = canonical._context(
        harness.conn, harness.blobs, harness.bundle, assignment, identity
    )
    harness.conn.rollback()
    assert built.selection == Selection(Basis.WHOLE_NO_DEMAND, None)
    assert {d.source_id for d in built.delivered} == {
        harness.source_id,
        harness.witness_id,
    }
