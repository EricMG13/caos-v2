"""The vendored bundle is the authority, and it is the one the spec was written
against.

Invariant 4: the bundle is the methodology authority, integrity checked on the
bytes. This is the pin -- every fact `docs/DECISIONS.md` §2 and §5 rest on,
asserted against the bytes in `vendor/`. A bundle swap that changes any of them
fails here rather than silently changing every route the system runs.

Verification at *use* is Phase 5. This is verification at rest: the vendored
copy is byte-identical to the manifest it shipped with.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

import pytest
from canonical_fixtures import CONTRACT, identity, upstream_ref
from lite_route_fixtures import realistic_handoff_markdown

BUNDLE = Path(__file__).resolve().parents[1] / "vendor" / "deploy-v"
CATALOG = (
    BUNDLE / "skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json"
)

# docs/DECISIONS.md §61, which moved the §13 pin. A run pinned to one build
# never executes under another.
BUILD_ID = "30222a494a5a1035c7955cb1ccfbe0b3b0fbbfa7d6426930f5dcf4d35aa1fc18"


def _load(path: Path) -> dict[str, object]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def catalog() -> dict[str, object]:
    return _load(CATALOG)


@pytest.fixture(scope="module")
def integrity() -> dict[str, object]:
    return _load(BUNDLE / "DEPLOY_V_INTEGRITY_v1.json")


def test_the_vendored_build_is_the_pinned_one(integrity: dict[str, object]) -> None:
    assert integrity["build_id"] == BUILD_ID


def test_every_vendored_byte_matches_the_manifest(integrity: dict[str, object]) -> None:
    roots = integrity["root_file_hashes"]
    skills = integrity["skills"]
    assert isinstance(roots, dict)
    assert isinstance(skills, list)

    expected: dict[Path, str] = {
        BUNDLE / name: str(entry["sha256"]) for name, entry in roots.items()
    }
    for skill in skills:
        folder = BUNDLE / "skills" / str(skill["folder_slug"])
        for name, entry in dict(skill["relative_file_hashes"]).items():
            expected[folder / name] = str(entry["sha256"])

    assert len(expected) > 300, "a manifest covering almost nothing is not a check"
    wrong = [
        path.relative_to(BUNDLE)
        for path, digest in expected.items()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest
    ]
    assert wrong == [], f"vendored copy differs from its manifest: {wrong[:5]}"


def test_the_typed_edges_are_where_the_spec_says(catalog: dict[str, object]) -> None:
    profiles = catalog["profiles"]
    assert isinstance(profiles, dict)
    assert set(profiles) == {"FULL_CREDIT_32", "LITE_CREDIT_22"}

    counted = collections.Counter(
        edge["type"] for edge in profiles["FULL_CREDIT_32"]["edges"]
    )
    # docs/DECISIONS.md §2: the numbers the predecessor's defect was measured in.
    assert counted == {"REQUIRED": 44, "OPTIONAL": 25, "ADVISORY": 22, "QA_GATE": 1}


def test_navigation_dependencies_is_the_untyped_list_we_must_not_read(
    catalog: dict[str, object],
) -> None:
    navigation = catalog["navigation"]
    assert isinstance(navigation, dict)
    pairs = navigation["dependencies"]
    assert isinstance(pairs, list)
    assert len(pairs) == 97
    # It carries no type at all -- which is why reading it enforced 47 soft
    # edges as mandatory and made the one QA_GATE not gate.
    assert all("type" not in pair for pair in pairs)


def test_the_catalog_carries_eighteen_pathways(catalog: dict[str, object]) -> None:
    profiles = catalog["profiles"]
    assert isinstance(profiles, dict)
    assert sum(len(profile["pathways"]) for profile in profiles.values()) == 18


def test_cp_parse_is_superseded_upstream_and_stage_zero_is_not_runnable(
    catalog: dict[str, object],
) -> None:
    # Both premises of the DECISIONS.md §5 carve-out. If upstream ever stops
    # saying either, the carve-out needs revisiting rather than carrying on.
    superseded = catalog["superseded_module_ids"]
    assert isinstance(superseded, dict)
    assert superseded["CP-PARSE"]["absorbed_by"] == "CP-0"
    preparation = catalog["preparation_stage"]
    assert isinstance(preparation, dict)
    assert preparation == {
        "module_id": "CP-0",
        "phase": "preparation",
        "required_before": "CP-0 readiness phase",
        "runnable": False,
    }


def test_the_catalog_declares_no_conditional_edge(catalog: dict[str, object]) -> None:
    # CONDITIONAL is a live edge type in CONTEXT.md and no edge uses it today,
    # so predicate freezing has nothing to act on. Recorded, not assumed.
    profiles = catalog["profiles"]
    assert isinstance(profiles, dict)
    conditional = [
        edge
        for profile in profiles.values()
        for edge in profile["edges"]
        if edge["type"] == "CONDITIONAL"
    ]
    assert conditional == []


def test_the_bundle_verifies_with_its_own_tool() -> None:
    # A second, independent verifier: the package's own read-only checker must
    # still accept the vendored bytes. `-B` because it refuses a tree that
    # carries bytecode, and cwd is the bundle because it resolves paths there.
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-B", "verify_package.py"],
        cwd=BUNDLE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]


# `docs/DECISIONS.md` §61: the three places CP-0 reads `CONDITIONAL` from must
# say the same thing -- a source condition, discharged by supplying the source
# and re-running CP-0, never an upstream handoff that has not run yet.
CP0_CONDITIONAL_TEXTS = (
    "skills/cp-0-source-readiness/SKILL.md",
    "skills/cp-0-source-readiness/references/REF_CP-0_STEPS.md",
    "skills/cp-0-source-readiness/references/CP-0__SourceReadiness__payload.schema.txt",
)


@pytest.mark.parametrize("relative", CP0_CONDITIONAL_TEXTS)
def test_cp0_defines_conditional_as_a_source_condition_everywhere_it_is_read(
    relative: str,
) -> None:
    text = (BUNDLE / relative).read_text(encoding="utf-8")
    assert "never a readiness ground" in text, relative
    assert "CP-0 is re-run" in text, relative


# `docs/DECISIONS.md` §63: T5B.5 is where CP-5 records what became of a
# calculation, and "not calculable from provided materials" is the answer its
# runbook asks for when the sources carry none. Its two status columns are
# exempt from the placeholder disqualifiers; its seven substantive columns are
# not, so a validator still cannot pass by leaving the work blank.
CP5_SKILL = "skills/cp-5-evidence-trace-validator/SKILL.md"
T5B5_STATUS_COLUMNS = ("Status", "Claim Status")
T5B5_PLACEHOLDER = "Not Calculable from Provided Materials"


def _cp5_handoff() -> str:
    cp0 = realistic_handoff_markdown(identity("CP-0"))
    cp0_ref = upstream_ref(identity("CP-0"), cp0)
    l10 = realistic_handoff_markdown(identity("CP-L10", upstream=(cp0_ref,)))
    upstream = (cp0_ref, upstream_ref(identity("CP-L10"), l10))
    return realistic_handoff_markdown(identity("CP-5", upstream=upstream)).decode()


def _with_t5b5_cell(markdown: str, column: str, value: str) -> str:
    """The fixture's first T5B.5 body row with one cell replaced, by column name."""
    start = markdown.index("#### T5B.5\n")
    lines = markdown[start:].split("\n")
    columns = [cell.strip() for cell in lines[2].strip().strip("|").split("|")]
    cells = [cell.strip() for cell in lines[4].strip().strip("|").split("|")]
    cells[columns.index(column)] = value
    lines[4] = "| " + " | ".join(cells) + " |"
    return markdown[:start] + "\n".join(lines)


def test_cp5_exempts_only_its_status_columns_from_the_disqualifiers() -> None:
    skill = (BUNDLE / CP5_SKILL).read_text(encoding="utf-8")
    rules = CONTRACT.completeness_check.load_contract(skill, "CP-5")
    register = rules["registers"]["T5B.5"]
    assert register["disqualifier_exempt_columns"] == list(T5B5_STATUS_COLUMNS)
    assert register["critical_columns"] == register["columns"]
    assert T5B5_PLACEHOLDER.casefold() in rules["blocklist"]
    substantive = [c for c in register["columns"] if c not in T5B5_STATUS_COLUMNS]
    assert len(substantive) == 7

    handoff = _cp5_handoff()
    check = CONTRACT.completeness_check.check
    assert check(skill, handoff, "CP-5")[0] == []
    for column in T5B5_STATUS_COLUMNS:
        honest = _with_t5b5_cell(handoff, column, T5B5_PLACEHOLDER)
        assert check(skill, honest, "CP-5")[0] == [], column
    for column in substantive:
        blank = _with_t5b5_cell(handoff, column, T5B5_PLACEHOLDER)
        assert check(skill, blank, "CP-5")[0] == [
            f"T5B.5 row 1: critical column '{column}' holds a disqualifying "
            f"placeholder '{T5B5_PLACEHOLDER}'"
        ]
