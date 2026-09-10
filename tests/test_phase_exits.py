"""The plan's own standing rule, made executable.

`docs/REBUILD_PLAN.md`: "A phase is exited by its named tests, and
`test_every_exit_test_of_an_exited_phase_exists` refuses a later phase starting
before they are written."

That test was named in the seed and never written, which is the sort of thing
this repository is otherwise careful about: a rule enforced by intention rather
than by a tool is not enforced. It reads the plan, collects every test the plan
names, and checks the suite defines it.

What it cannot do is decide which phase is current -- so the phases not yet
reached are listed below, explicitly, with the reason each is absent. That list
is the whole point: adding code for a phase without its named test fails this,
and so does quietly deleting a test that already exists.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / "docs" / "REBUILD_PLAN.md"
SUITE = REPO / "tests"

# Named in the plan, and legitimately not written yet. Every entry states why,
# because "not yet" with no reason is how a list like this becomes a list of
# tests nobody intends to write.
NOT_YET_REACHED = {
    # Phase 9 -- the workspace. Frontend, and its own suite.
    "test_passport_contract",
    "test_book_binds_one_snapshot_per_compared_case",
    # Phase 10 -- qualification. The corpus harness and the verdict.
    "test_a_verdict_binds_provider_corpus_build_date_expiry_and_reviewer",
    "test_a_host_control_reads_orchestration_proof_never_qualified",
    # Owed by "the first phase exposing an HTTP route" (plan, standing rules).
    # No route exists yet: the run tail's contract is built and its transport is
    # not, recorded under Phase 6 in CLAUDE.md's known gaps.
    "test_production_never_trusts_role_header",
    "test_unauthorised_case_is_private_404",
}


def named_in_the_plan() -> set[str]:
    """Every `test_*` the plan names in backticks."""
    return set(re.findall(r"`(test_[a-z0-9_]+)`", PLAN.read_text(encoding="utf-8")))


def defined_in_the_suite() -> set[str]:
    """Every test the suite defines, by name."""
    defined: set[str] = set()
    for path in SUITE.rglob("test_*.py"):
        defined.update(
            re.findall(
                r"^def (test_[a-z0-9_]+)\(", path.read_text(encoding="utf-8"), re.M
            )
        )
    return defined


def test_every_exit_test_of_an_exited_phase_exists() -> None:
    """The named test the plan's standing rules call for.

    Fails two ways, both of which matter: a phase whose code arrived without its
    named test, and a named test that used to exist and was removed.
    """
    named = named_in_the_plan()
    missing = named - defined_in_the_suite()

    assert missing == NOT_YET_REACHED, (
        "the plan names tests the suite does not define, or the not-yet-reached "
        f"list is stale. Unexpectedly missing: {sorted(missing - NOT_YET_REACHED)}; "
        f"listed but now present: {sorted(NOT_YET_REACHED - missing)}"
    )


def test_the_plan_still_names_the_tests_this_list_excuses() -> None:
    """The excuse list cannot outlive the plan that justifies it.

    A name dropped from the plan but left here would silently excuse a test
    nobody is waiting for.
    """
    assert NOT_YET_REACHED <= named_in_the_plan()


def test_the_plan_names_the_tests_this_file_reads() -> None:
    """A guard against the parser silently matching nothing -- which would make
    every assertion above vacuously true."""
    named = named_in_the_plan()

    assert len(named) > 30, "the plan names far more tests than this found"
    assert "test_terminal_event_is_exactly_once" in named
