"""The known-gaps ledger's own gate.

`CLAUDE.md` states the rule this enforces: "A ledger entry that describes a gap
the tree has since closed is the same defect as a missing one, read the other
way round." Two ways of getting there are mechanical, and this file is both.

The first is citation rot. An entry earns its keep by naming the test that holds
it open, and a named test that no longer exists turns the entry into an
assurance nobody runs. The second is the half-closed entry: this repository's
convention is that an open entry ends in an `*Upgrade:*` clause, so an entry
with no upgrade path has either been closed without being struck or was written
without saying what would close it.

What this cannot do is read an entry's prose and decide whether the tree still
behaves that way. Two entries were struck by hand in the commit that added this
file -- one claiming there was no `qualification_verdicts` table, one claiming a
proof was held and never stored -- and no rule here would have caught either,
because both were fluent, both cited nothing, and both kept their upgrade
clause while becoming false. Phrase-based rules were tried against the real
file and rejected: the best of them flagged three entries, of which one was the
genuine defect and two were correct entries using the same words. That limit is
recorded in the ledger under Completion Phase 7 rather than papered over with a
gate that looks stronger than it is.
"""

from __future__ import annotations

import re
from pathlib import Path

import ledger_state
import pytest

REPO = Path(__file__).resolve().parents[1]
SUITE = REPO / "tests"
WORKSPACE_SUITE = REPO / "frontend" / "tests"

# A Python test is a function; a workspace test is a title string. Both are
# cited in the ledger the same way, so both are read.
_PYTHON_TEST = re.compile(r"^\s*(?:async\s+)?def\s+(test_[a-z0-9_]+)", re.MULTILINE)
_WORKSPACE_TEST = re.compile(r"""\b(?:test|it)\(\s*(["'`])(test_[a-z0-9_]+)\1""")

# The ledger cites a test file as readily as a test function -- "`test_phase_exits.py`
# names it" is a citation of the module. A module stem is therefore a name this
# gate must accept, and `_names_in_the_suite` collects both.

# Names the ledger mentions without claiming the suite defines them. Two, found
# by running this gate rather than by reading: one test deliberately deleted and
# owed again, and one placeholder in a sentence describing a regex. Each entry
# states why, because an exemption with no reason is how a gate stops gating --
# and `test_no_exempt_name_has_quietly_been_written` refuses one that has since
# become real, so the list cannot outlive its reasons.
NOT_A_CITATION = {
    "test_cp1_produces_canonical_envelope_with_anchored_citations": (
        "deleted with the claims executor (docs/DECISIONS.md 42) and owed again "
        "when Phase 5 extends the canonical adapter to CP-1; the list that owns "
        "it is NOT_YET_REACHED in tests/test_phase_exits.py"
    ),
    "test_x": (
        "a placeholder inside the ledger's own description of the phase-exit "
        "gate's title regex, not a citation of anything"
    ),
}


def _names_in_the_suite() -> frozenset[str]:
    """Every test name the suite defines: functions, titles and module stems."""
    names: set[str] = set()
    for path in sorted(SUITE.rglob("test_*.py")):
        names.add(path.stem)
        names.update(_PYTHON_TEST.findall(path.read_text(encoding="utf-8")))
    if WORKSPACE_SUITE.is_dir():
        for pattern in ("*.ts", "*.tsx"):
            for path in sorted(WORKSPACE_SUITE.rglob(pattern)):
                text = path.read_text(encoding="utf-8")
                names.update(found[1] for found in _WORKSPACE_TEST.findall(text))
    return frozenset(names)


def test_every_test_a_ledger_entry_cites_exists_in_the_suite() -> None:
    """A cited test that nobody runs is a gap recorded as if it were guarded."""
    defined = _names_in_the_suite()
    missing = [
        f"{entry.title!r} cites {name!r}, which the suite does not define"
        for entry in ledger_state.read()
        for name in entry.tests
        if name not in defined and name not in NOT_A_CITATION
    ]
    assert not missing, "\n".join(missing)


def test_no_exempt_name_has_quietly_been_written() -> None:
    """An excuse that has come true is an excuse nobody is reading."""
    defined = _names_in_the_suite()
    stale = sorted(name for name in NOT_A_CITATION if name in defined)
    assert not stale, (
        "these names are exempt from the citation rule but the suite now "
        f"defines them; drop the exemption: {stale}"
    )


def test_every_open_ledger_entry_states_its_upgrade_path() -> None:
    """An open entry with no upgrade path is closed, or was never a gap.

    The convention holds for every open entry in the file today, which is what
    makes it a gate rather than a wish: it fails the day an entry is closed by
    deleting its upgrade clause and left unstruck.
    """
    silent = [
        f"[{entry.phase}] {entry.title!r} is open and states no *Upgrade:*"
        for entry in ledger_state.read()
        if entry.open and not entry.upgrade
    ]
    assert not silent, "\n".join(silent)


def test_the_reader_found_the_whole_ledger() -> None:
    """A reader that matched nothing would make both rules above vacuous.

    A count alone left slack: the Phase 7 confidence review showed that a `## `
    inserted mid-ledger would silently drop twelve entries and still clear a
    count floor. So the floor also names the two phases that bracket the
    section, which cannot both be present unless the reader ran its length.
    """
    found = ledger_state.read()
    phases = {entry.phase for entry in found}
    assert "Completion Phase 7" in phases, "the newest phase heading was not read"
    assert "Phase 1" in phases, (
        "the oldest phase heading was not read, so the reader stopped early"
    )
    assert len(found) > 80, f"read only {len(found)} ledger entries"
    assert any(entry.struck for entry in found), "no closed entry was recognised"
    assert any(entry.open for entry in found), "no open entry was recognised"
    assert all(entry.phase for entry in found), "an entry sits under no phase heading"
    assert all(entry.title for entry in found), "an entry parsed with no title"


def test_a_contract_with_no_ledger_heading_refuses() -> None:
    """The reader fails loudly rather than reporting an empty ledger."""
    with pytest.raises(ValueError):
        ledger_state.entries("# A contract with no ledger\n\nnothing here.\n")


def test_the_reader_separates_struck_entries_from_open_ones() -> None:
    """The one distinction every rule above rests on."""
    found = ledger_state.entries(
        "## Known gaps (honest ledger)\n\n"
        "**Completion Phase 7.**\n\n"
        "- ~~**Closed.**~~ Fixed in `abc1234`, `test_it_works` holds it.\n"
        "- **Open.** Still true. *Upgrade:* do the work.\n\n"
        "## Something else\n\n"
        "- **Not a ledger entry.** Outside the section.\n"
    )
    assert all(isinstance(entry, ledger_state.LedgerEntry) for entry in found)
    assert [(entry.title, entry.struck) for entry in found] == [
        ("Closed", True),
        ("Open", False),
    ]
    assert found[0].tests == ("test_it_works",)
    assert found[0].commits == ("abc1234",)
    assert found[1].upgrade and not found[0].open
