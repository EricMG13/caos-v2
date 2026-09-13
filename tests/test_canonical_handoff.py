"""A canonical Markdown handoff is judged by the vendor's validators, then held to
the host's identity (Phase 3 Task 3.1a; `docs/DECISIONS.md` §41).

Documents are generated the way `vendor/deploy-v/tests/test_module_workflow.py`
builds them: structural scenarios over the LITE earnings route, not analysis.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from canonical_fixtures import (
    CATALOG,
    CONTRACT,
    PINNED,
    RUN,
    wire,
)
from canonical_fixtures import handoff_markdown as _markdown
from canonical_fixtures import identity as _identity
from canonical_fixtures import skill as _skill
from canonical_fixtures import upstream_ref as _ref

from server.methodology.handoff import (
    HostIdentity,
    Projections,
    expected_filename,
    invocation_fields,
    validate_markdown,
)
from server.refusals import Refusal, RefusalCode

SECRET = "Confidential covenant headroom 7.3x"


def _validate(
    identity: HostIdentity, markdown: bytes, gate_expects: frozenset[str] = PINNED
) -> Projections:
    return validate_markdown(
        CONTRACT,
        CATALOG,
        _skill(identity.module_id),
        markdown,
        identity=identity,
        gate_expects=gate_expects,
    )


def _refused(
    identity: HostIdentity, markdown: bytes, **kwargs: frozenset[str]
) -> Refusal:
    with pytest.raises(Refusal) as refused:
        _validate(identity, markdown, **kwargs)
    return refused.value


CP0 = _identity("CP-0")
CP0_MD = _markdown(CP0)
L10 = _identity("CP-L10", (_ref(CP0, CP0_MD),))
L10_MD = _markdown(L10)
CP5 = _identity("CP-5", (_ref(CP0, CP0_MD), _ref(L10, L10_MD)))


def test_the_lite_earnings_route_validates_end_to_end() -> None:
    gate = _validate(CP0, CP0_MD)
    assert gate.readiness == (("CP-5", "READY"), ("CP-L10", "READY"))
    assert _validate(L10, L10_MD).qa_status == "Passed"
    assert _validate(CP5, _markdown(CP5)).module_id == "CP-5"


def test_a_missing_register_refuses_the_handoff() -> None:
    first = next(
        iter(
            CONTRACT.completeness_check.load_contract(
                _skill("CP-L10").decode(), "CP-L10"
            )["registers"]
        )
    )
    markdown = _markdown(L10, omit_register=first)
    # The structural validator alone would pass it; the register contract does not.
    assert CONTRACT.validate_handoff.validate_text(markdown.decode()).exit_code == 0
    assert _refused(L10, markdown).code is RefusalCode.HANDOFF_INCOMPLETE


def test_undeclared_fields_are_refused() -> None:
    markdown = _markdown(L10, override={"model_note": "trust me"})
    assert _refused(L10, markdown).code is RefusalCode.HANDOFF_UNDECLARED_FIELD


def test_blocked_qa_status_is_diagnostic_only() -> None:
    blocked = {
        "qa_status": "Blocked",
        "confidence_score": 30,
        "confidence_band": "Insufficient Information",
        "committee_status": "Blocked",
    }
    assert (
        _refused(L10, _markdown(L10, authored=blocked)).code
        is RefusalCode.HANDOFF_BLOCKED
    )
    # Identity is checked first: a Blocked handoff for someone else is a mismatch.
    wrong = _markdown(L10, authored=blocked, override={"issuer_name": "Other"})
    assert _refused(L10, wrong).code is RefusalCode.HANDOFF_IDENTITY_MISMATCH


def test_restricted_is_accepted_with_limitations() -> None:
    restricted = {
        "qa_status": "Restricted",
        "confidence_score": 55,
        "confidence_band": "Low",
        "committee_status": "Restricted",
        "limitation_flags": ["Interim period only"],
    }
    projections = _validate(L10, _markdown(L10, authored=restricted))
    assert projections.qa_status == "Restricted"
    assert projections.limitation_flags == ("Interim period only",)


def test_no_validator_text_reaches_a_refusal() -> None:
    markdown = _markdown(
        L10, override={"issuer_name": ["x"]}, body_note=SECRET
    ).replace(b"## QA Validation", b"## " + SECRET.encode())
    refusal = _refused(L10, markdown)
    assert refusal.code is RefusalCode.HANDOFF_MALFORMED
    assert refusal.__cause__ is None and refusal.__context__ is None
    assert SECRET not in repr(refusal.args) and SECRET not in str(refusal)


HOST_KEYS = sorted(invocation_fields(CONTRACT, L10))
# Each value stays valid to the vendor, so only the host's comparison can refuse.
CHANGED: dict[str, object] = {
    "analysis_date": "2026-09-07",
    "upstream_artifacts_used": [],
}


def _changed(key: str) -> object:
    value = invocation_fields(CONTRACT, L10)[key]
    if key in CHANGED:
        return CHANGED[key]
    assert isinstance(value, str)
    return value[:-1] + ("0" if value[-1] != "0" else "1")


@pytest.mark.parametrize("key", HOST_KEYS)
def test_every_host_owned_field_is_compared(key: str) -> None:
    refusal = _refused(L10, _markdown(L10, override={key: _changed(key)}))
    assert refusal.code is RefusalCode.HANDOFF_IDENTITY_MISMATCH


@pytest.mark.parametrize("key", HOST_KEYS)
def test_a_missing_host_owned_field_is_refused_by_code(key: str) -> None:
    refusal = _refused(L10, _markdown(L10, drop=key))
    assert refusal.code in {
        RefusalCode.HANDOFF_IDENTITY_MISMATCH,
        RefusalCode.HANDOFF_MALFORMED,
    }


def test_carriage_returns_are_refused() -> None:
    assert (
        _refused(L10, L10_MD.replace(b"\n", b"\r\n")).code
        is RefusalCode.HANDOFF_MALFORMED
    )


def test_a_screening_pathway_projects_its_scope() -> None:
    ready = {"committee_status": "Committee Ready"}
    assert (
        _validate(L10, _markdown(L10, authored=ready)).decision_scope
        == "SCREENING_ONLY"
    )


def test_a_scalar_that_parses_as_another_type_is_a_mismatch() -> None:
    numeric = _identity("CP-0", issuer_id="12345")
    markdown = _markdown(numeric, override={"issuer_id": 12345})
    assert _refused(numeric, markdown).code is RefusalCode.HANDOFF_IDENTITY_MISMATCH


def test_an_upgrade_link_is_refused() -> None:
    markdown = _markdown(L10, override={"credit_os_parent_run_id": RUN})
    assert _refused(L10, markdown).code is RefusalCode.HANDOFF_IDENTITY_MISMATCH


def test_a_module_outside_the_adapter_is_refused() -> None:
    other = dataclasses.replace(L10, module_id="CP-1")
    assert _refused(other, L10_MD).code is RefusalCode.HANDOFF_MODULE_UNSUPPORTED


def test_readiness_must_cover_exactly_the_pin() -> None:
    assert (
        _refused(CP0, CP0_MD, gate_expects=frozenset({"CP-L10"})).code
        is RefusalCode.HANDOFF_INCOMPLETE
    )
    assert (
        _refused(CP0, CP0_MD, gate_expects=PINNED | {"CP-1"}).code
        is RefusalCode.HANDOFF_INCOMPLETE
    )


@pytest.mark.parametrize("character", ["\u2028", "\u2029", "\ufeff", "\u202e"])
def test_invisible_separators_are_refused_not_normalised(character: str) -> None:
    markdown = _markdown(L10, body_note="Recorded" + character + " source p1.")
    assert _refused(L10, markdown).code is RefusalCode.HANDOFF_MALFORMED


def test_non_utf8_bytes_are_refused() -> None:
    assert _refused(L10, L10_MD + b"\xff").code is RefusalCode.HANDOFF_MALFORMED


def test_expected_filename_is_the_vendor_canonical_name() -> None:
    fields = invocation_fields(CONTRACT, L10)
    vendor_name = CONTRACT.validate_handoff.canonical_markdown_filename(fields)
    assert expected_filename(L10) == vendor_name == "EXAMPLE_CP-L10_20260908.md"


@pytest.mark.parametrize("status", ["NOT-A-STATUS", "", "READY|BLOCKED"])
def test_a_malformed_readiness_map_refuses_rather_than_raising(status: str) -> None:
    """REBUILD_PLAN Phase 11 exit, on CP-0's T8 register since f-1c: a status
    the vendor does not know refuses typed, with no context carried."""
    refused = _refused(
        CP0, _markdown(CP0, readiness={"CP-L10": status}), gate_expects=PINNED
    )
    assert refused.code is RefusalCode.HANDOFF_INCOMPLETE
    assert refused.__context__ is None and refused.__cause__ is None


def test_gate_readiness_projects_each_pinned_module_status() -> None:
    blocked = _markdown(CP0, readiness={"CP-L10": "BLOCKED"})
    gate = _validate(CP0, blocked)
    assert gate.readiness == (("CP-5", "READY"), ("CP-L10", "BLOCKED"))


def test_the_wire_carries_the_exact_markdown_bytes() -> None:
    body = json.loads(
        wire(L10_MD, [{"source_id": "s", "page": 1, "matched_text": "q"}])
    )
    assert set(body) == {"canonical_markdown", "citations"}
    assert body["canonical_markdown"].encode() == L10_MD
