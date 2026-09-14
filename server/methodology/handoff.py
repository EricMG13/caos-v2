"""The canonical Markdown handoff: vendor conformance, then host identity (§41).

A module's output is one UTF-8 Markdown file whose SHA-256 is the lineage hash
downstream handoffs name. The vendor's validators decide whether it conforms;
this module decides whether it is *this* invocation's handoff. Every field the
host owns is compared type-exactly against what the host would have written,
because a provider-claimed identity never survives (invariant 3).

Pure: no I/O, no clock. Every refusal is a typed code raised outside the handler
that caught the vendor's exception, so neither the exception chain nor the
refusal carries vendor text, which can quote the document (invariant 2).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from server.boundary_text import BoundaryText
from server.methodology.vendor import VendorContract
from server.refusals import Refusal, RefusalCode

ADAPTER_MODULES = frozenset({"CP-0", "CP-L10", "CP-5"})
GATE_MODULE = "CP-0"
ZERO_SHA256 = "0" * 64
# The vendor's frozen reader limits (CREDIT_OS_RUNTIME_LIMITS_v1).
MAX_FILE_BYTES = 26_214_400
MAX_FRONTMATTER_BYTES = 262_144
MAX_LINE_BYTES = 65_536
# Characters BoundaryText keeps that still make one text read as two.
_INVISIBLE = frozenset("\u2028\u2029\ufeff")
_UPGRADE_KEYS = ("credit_os_parent_run_id", "credit_os_upgrade_source_sha256")


@dataclass(frozen=True, slots=True)
class UpstreamRef:
    """One accepted upstream handoff as the host recorded it."""

    route_node_id: str
    module_id: str
    run_id: str
    period: str
    sha256: str


@dataclass(frozen=True, slots=True)
class HostIdentity:
    """Everything the host owns about one invocation. None of it is the model's."""

    run_id: str
    profile_id: str
    selection_id: str
    route_node_id: str
    module_id: str
    module_name: str
    issuer_id: str
    issuer_name: str
    reporting_period: str
    analysis_date: str
    ordinal: int
    authority_bundle_sha256: str
    upstream: tuple[UpstreamRef, ...]


@dataclass(frozen=True, slots=True)
class Projections:
    """What the host reads back from a conforming handoff. Model-authored."""

    module_id: str
    qa_status: str
    committee_status: str
    confidence_score: int
    confidence_band: str
    limitation_flags: tuple[str, ...]
    validation_warnings: tuple[str, ...]
    downstream_consumers: tuple[str, ...]
    readiness: tuple[tuple[str, str], ...]
    # The pathway's catalog scope; `SCREENING_ONLY` is never committee clearance,
    # whatever `committee_status` the model wrote.
    decision_scope: str


def _vendor[T](code: RefusalCode, call: Callable[[], T]) -> T:
    with suppress(Exception):  # any vendor failure is this refusal
        return call()
    # Raised after the handler has closed, so `__context__` holds no vendor text.
    raise Refusal(code)


def expected_filename(identity: HostIdentity) -> str:
    compact = identity.analysis_date.replace("-", "")
    return f"{identity.issuer_id}_{identity.module_id}_{compact}.md"


def invocation_fields(
    contract: VendorContract, identity: HostIdentity
) -> dict[str, Any]:
    """The host-owned front matter for this invocation, built by the vendor envelope."""
    upstream = sorted(identity.upstream, key=lambda ref: ref.route_node_id)
    gate = [ref.sha256 for ref in upstream if ref.module_id == GATE_MODULE]
    envelope = _vendor(
        RefusalCode.HANDOFF_IDENTITY_MISMATCH,
        lambda: contract.envelope.build(
            run_id=identity.run_id,
            profile_id=identity.profile_id,
            selection_id=identity.selection_id,
            route_node_id=identity.route_node_id,
            module_id=identity.module_id,
            module_name=identity.module_name,
            expected_output_filename=expected_filename(identity),
            authority_bundle_sha256=identity.authority_bundle_sha256,
            accepted_cp0_sha256=gate[0] if gate else ZERO_SHA256,
            required_upstream_digests={
                ref.route_node_id: ref.sha256 for ref in upstream
            },
            ordinal=identity.ordinal,
        ),
    )
    return {
        "module_id": identity.module_id,
        "module_name": identity.module_name,
        "issuer_id": identity.issuer_id,
        "issuer_name": identity.issuer_name,
        "run_id": identity.run_id,
        "reporting_period": identity.reporting_period,
        "analysis_date": identity.analysis_date,
        "credit_os_run_id": identity.run_id,
        "credit_os_profile_id": identity.profile_id,
        "credit_os_selection_id": identity.selection_id,
        "credit_os_authority_bundle_sha256": identity.authority_bundle_sha256,
        "credit_os_attempt_id": envelope["attempt_id"],
        "credit_os_route_node_id": identity.route_node_id,
        "credit_os_invocation_sha256": _vendor(
            RefusalCode.HANDOFF_IDENTITY_MISMATCH,
            lambda: contract.envelope.digest(envelope),
        ),
        "upstream_artifacts_used": [
            {
                "module_id": ref.module_id,
                "run_id": ref.run_id,
                "period": ref.period,
                "sha256": ref.sha256,
            }
            for ref in upstream
        ],
    }


def _text(markdown: bytes) -> str:
    malformed = Refusal(RefusalCode.HANDOFF_MALFORMED)
    if len(markdown) > MAX_FILE_BYTES:
        raise malformed
    try:
        text = markdown.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    # Canonical Markdown is LF-only; a CR would let the host and the vendor
    # disagree about where lines, and so the front matter, end.
    if text is None or "\r" in text or _INVISIBLE.intersection(text):
        raise malformed
    try:
        clean = BoundaryText.of(text, limit=len(text)).value == text
    except Refusal:
        clean = False
    lines = text.split("\n")
    closing = (
        lines.index("---", 1) if lines[:1] == ["---"] and "---" in lines[1:] else 0
    )
    if (
        not clean
        or any(len(line.encode()) > MAX_LINE_BYTES for line in lines)
        or len("\n".join(lines[: closing + 1]).encode()) > MAX_FRONTMATTER_BYTES
    ):
        raise malformed
    return text


def _same(left: object, right: object) -> bool:
    """Equal and of the same JSON type: `12345` is not `"12345"`, `true` is not `1`."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _declared_keys(contract: VendorContract) -> frozenset[str]:
    vendor = contract.validate_handoff
    return frozenset(
        (
            *vendor.REQUIRED_FIELDS,
            *vendor.ISSUER_FIELDS,
            *contract.envelope.RUN_ANCHOR_FIELDS,
            *contract.envelope.ECHO_FIELDS,
            *_UPGRADE_KEYS,
        )
    )


def _readiness(
    contract: VendorContract,
    catalog: Mapping[str, Any],
    text: str,
    gate_expects: frozenset[str],
) -> tuple[tuple[str, str], ...]:
    nav = contract.navigation
    rows = _vendor(
        RefusalCode.HANDOFF_INCOMPLETE,
        lambda: nav.parse_t8(text, nav.validate_catalog(catalog)),
    )
    readiness = tuple(sorted((row.module_id, row.readiness) for row in rows))
    if frozenset(module for module, _ in readiness) != gate_expects:
        raise Refusal(RefusalCode.HANDOFF_INCOMPLETE)
    return readiness


def _decision_scope(catalog: Mapping[str, Any], identity: HostIdentity) -> str:
    try:
        pathway = catalog["profiles"][identity.profile_id]["pathways"]
        scope = pathway[identity.selection_id]["decision_scope"]
    except (KeyError, TypeError):
        scope = None
    if not isinstance(scope, str) or not scope:
        raise Refusal(RefusalCode.HANDOFF_IDENTITY_MISMATCH)
    return scope


def validate_markdown(  # noqa: PLR0913 -- the brief's pure signature
    contract: VendorContract,
    catalog: Mapping[str, Any],
    skill: bytes,
    markdown: bytes,
    *,
    identity: HostIdentity,
    gate_expects: frozenset[str],
) -> Projections:
    """Refuse anything but this invocation's conforming handoff; project the rest.

    Order is the contract: bytes, vendor structure, declared keys, host identity,
    register completeness, gate readiness, then `qa_status`. A validated Blocked
    handoff refuses `HANDOFF_BLOCKED` only once it is proven to be this
    invocation's, so the caller can record it as a diagnostic outcome.

    `skill` is the module's verified `SKILL.md`. Not implemented here, and
    recorded as gaps: the vendor's `semantic_rules` and
    `document_substrings_casefold`. The pathway's `decision_scope` is projected,
    not reconciled with `committee_status`, which the vendor does not map.
    """
    if identity.module_id not in ADAPTER_MODULES:
        raise Refusal(RefusalCode.HANDOFF_MODULE_UNSUPPORTED)
    text = _text(markdown)
    result = _vendor(
        RefusalCode.HANDOFF_MALFORMED,
        lambda: contract.validate_handoff.validate_text(text),
    )
    if result.errors or result.fields is None:
        raise Refusal(RefusalCode.HANDOFF_MALFORMED)
    fields: dict[str, Any] = result.fields
    if not _declared_keys(contract).issuperset(fields):
        raise Refusal(RefusalCode.HANDOFF_UNDECLARED_FIELD)

    host = invocation_fields(contract, identity)
    if any(
        key not in fields or not _same(fields[key], value)
        for key, value in host.items()
    ) or any(fields.get(key) is not None for key in _UPGRADE_KEYS):
        raise Refusal(RefusalCode.HANDOFF_IDENTITY_MISMATCH)

    violations = _vendor(
        RefusalCode.HANDOFF_INCOMPLETE,
        lambda: contract.completeness_check.check(
            skill.decode("utf-8"), text, identity.module_id
        )[0],
    )
    if violations:
        raise Refusal(RefusalCode.HANDOFF_INCOMPLETE)
    readiness = (
        _readiness(contract, catalog, text, gate_expects)
        if identity.module_id == GATE_MODULE
        else ()
    )
    if fields["qa_status"] == "Blocked":
        raise Refusal(RefusalCode.HANDOFF_BLOCKED)
    return Projections(
        module_id=identity.module_id,
        qa_status=fields["qa_status"],
        committee_status=fields["committee_status"],
        confidence_score=fields["confidence_score"],
        confidence_band=fields["confidence_band"],
        limitation_flags=tuple(fields["limitation_flags"]),
        validation_warnings=tuple(fields["validation_warnings"]),
        downstream_consumers=tuple(fields["downstream_consumers"]),
        readiness=readiness,
        decision_scope=_decision_scope(catalog, identity),
    )
