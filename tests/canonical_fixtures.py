"""Deterministic canonical Markdown handoffs for the LITE earnings route.

Built the way `vendor/deploy-v/tests/test_module_workflow.py` builds them:
structural scenarios over CP-0 -> CP-L10 -> CP-5, not issuer analysis. Shared
by every suite that needs a handoff the vendor validators accept.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from server.methodology.bundle import Bundle, verified_bytes
from server.methodology.handoff import HostIdentity, UpstreamRef, invocation_fields
from server.methodology.vendor import authority_bundle_sha256, load_vendor_contract
from server.provider import Completion

VENDORED = Path(__file__).resolve().parents[1] / "vendor/deploy-v"
BUNDLE = Bundle(VENDORED)
CONTRACT = load_vendor_contract(BUNDLE)
CATALOG = json.loads(
    (
        VENDORED
        / "skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json"
    ).read_text()
)
LITE_PROFILE = "LITE_CREDIT_22"
LITE_SELECTION = "LITE_EARNINGS_UPDATE"
ROUTE = CONTRACT.routing.Route(CATALOG, LITE_PROFILE, LITE_SELECTION)
RUN = "COS-20260908T120000Z-" + "1" * 32
PINNED = frozenset({"CP-L10", "CP-5"})


def identity(
    module_id: str, upstream: tuple[UpstreamRef, ...] = (), **changes: object
) -> HostIdentity:
    """The host identity of one LITE node, with any field replaced."""
    node = ROUTE.by_module[module_id]
    values: dict[str, Any] = {
        "run_id": RUN,
        "profile_id": ROUTE.profile_id,
        "selection_id": ROUTE.selection_id,
        "route_node_id": node["route_node_id"],
        "module_id": module_id,
        "module_name": node["module_name"],
        "issuer_id": "EXAMPLE",
        "issuer_name": "Example",
        "reporting_period": "FY2025",
        "analysis_date": "2026-09-08",
        "ordinal": 1,
        "authority_bundle_sha256": authority_bundle_sha256(BUNDLE),
        "upstream": upstream,
    }
    values.update(changes)
    return HostIdentity(**values)


def _table(columns: list[str] | tuple[str, ...], rows: list[list[str]]) -> str:
    head = (
        "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
    )
    return head + "".join("| " + " | ".join(row) + " |\n" for row in rows) + "\n"


def _yaml(fields: dict[str, Any]) -> str:
    lines = []
    for key, value in fields.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            lines.append(key + ":")
            for item in value:
                for n, (k, v) in enumerate(item.items()):
                    lines.append(
                        ("  - " if n == 0 else "    ") + k + ": " + json.dumps(v)
                    )
        else:
            lines.append(key + ": " + json.dumps(value))
    return "\n".join(lines)


def skill(module_id: str) -> bytes:
    """The module's verified `SKILL.md`."""
    return verified_bytes(BUNDLE, module_id, "SKILL.md")


def handoff_markdown(  # noqa: PLR0913 -- one knob per fixture variant
    identity: HostIdentity,
    *,
    fields: dict[str, Any] | None = None,
    authored: dict[str, Any] | None = None,
    override: dict[str, Any] | None = None,
    omit_register: str | None = None,
    drop: str | None = None,
    body_note: str = "Recorded source p1.",
    readiness: dict[str, str] | None = None,
) -> bytes:
    """A handoff the vendor validators accept for `identity`, then varied.

    `fields` replaces the host-owned front matter (a fake provider copies what
    the prompt handed it); `readiness` sets CP-0's T8 status per pinned module.
    """
    front: dict[str, Any] = {
        **(fields if fields is not None else invocation_fields(CONTRACT, identity)),
        "confidence_score": 90,
        "confidence_band": "High",
        "qa_status": "Passed",
        "committee_status": "Draft Only",
        "limitation_flags": [],
        "validation_warnings": [],
        "downstream_consumers": [],
        **(authored or {}),
        **(override or {}),
    }
    front.pop(drop or "", None)
    rules = CONTRACT.completeness_check.load_contract(
        skill(identity.module_id).decode(), identity.module_id
    )
    appendix = "### Analytical appendix — complete canonical registers\n\n"
    for register, spec in rules["registers"].items():
        if register == omit_register:
            continue
        appendix += "#### " + register + "\n\n"
        if identity.module_id == "CP-0" and register == "T8":
            appendix += _table(CONTRACT.navigation.NEW_HEADERS, _t8(readiness or {}))
        else:
            columns = spec["columns"] or ["Evidence"]
            appendix += _table(
                columns,
                [["Recorded source p1"] * len(columns)]
                * max(1, spec["minimum_body_rows"]),
            )
    for table_id in rules["unconditional_stable_tables"]:
        appendix += (
            "<!-- table-id: "
            + table_id
            + " -->\n"
            + _table(["source_locator"], [["Source p1"]])
        )
    headings = CONTRACT.validate_handoff.CANONICAL_HEADINGS
    body = "".join(
        "## " + h + "\n\n" + (appendix if h == "Analysis" else body_note + "\n\n")
        for h in headings
    )
    return ("---\n" + _yaml(front) + "\n---\n" + body).encode()


def _t8(readiness: dict[str, str]) -> list[list[str]]:
    rows = []
    for n, module in enumerate(sorted(PINNED), 1):
        status = readiness.get(module, "READY")
        runnable = status in {"READY", "READY_WITH_LIMITATIONS"}
        command = "Run " + module
        rows.append(
            [
                str(n),
                module,
                command,
                command if runnable else "DO NOT RUN",
                "Source p1",
                "Current handoff",
                status,
                "Relevant source p1",
            ]
        )
    return rows


def upstream_ref(identity: HostIdentity, markdown: bytes) -> UpstreamRef:
    """How a downstream node names this accepted handoff."""
    return UpstreamRef(
        route_node_id=identity.route_node_id,
        module_id=identity.module_id,
        run_id=identity.run_id,
        period=identity.reporting_period,
        sha256=hashlib.sha256(markdown).hexdigest(),
    )


def wire(markdown: bytes, citations: list[dict[str, object]]) -> str:
    """The closed provider transport `{canonical_markdown, citations}` (§41)."""
    return json.dumps(
        {"canonical_markdown": markdown.decode("utf-8"), "citations": citations}
    )


def fields_from_prompt(prompt: str) -> dict[str, Any]:
    """The host-owned front matter a prompt handed over, parsed by the vendor."""
    found = re.search(
        r"--- HOST-OWNED FRONT MATTER ([0-9a-f]{16}) \(copy exactly\) ---\n", prompt
    )
    assert found is not None
    end = prompt.index(f"\n--- END HOST-OWNED FRONT MATTER {found.group(1)} ---")
    block = prompt[found.end() : end]
    parsed, _body = CONTRACT.validate_handoff.parse_restricted_frontmatter(
        "---\n" + block + "\n---\n"
    )
    return dict(parsed)


# Whole words of the harness report's page 1, repeated in every handoff body.
QUOTE = "Total debt at 31 December 2026"
# Whole words of the body that no evidence carries.
UNANCHORED = "Leverage was unchanged"
# The authored fields a validated `qa_status` must agree with.
AUTHORED = {
    "Passed": {},
    "Restricted": {
        "confidence_score": 50,
        "confidence_band": "Low",
        "committee_status": "Restricted",
        "limitation_flags": ["Only one source report was delivered"],
    },
    "Blocked": {
        "confidence_score": 30,
        "confidence_band": "Insufficient Information",
        "committee_status": "Blocked",
    },
}


@dataclass
class CanonicalCompletions:
    """A provider that copies the prompt's host front matter into a handoff.

    `mutate` edits the copied fields (identity tampering); `content` replaces the
    whole answer; `during` runs inside the call, before the answer.
    `qa_by_module` overrides `qa_status` per module on a whole route.
    """

    source_id: UUID
    charge: Decimal | None = Decimal("0.0000041")
    model: str = "a-model/for-the-test"
    generation_id: str = "gen-canonical-test"
    qa_status: str = "Passed"
    qa_by_module: dict[str, str] = field(default_factory=dict)
    readiness: dict[str, str] = field(default_factory=dict)
    quotes: tuple[str, ...] = (QUOTE,)
    mutate: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    content: str | None = None
    during: Callable[[], None] | None = None
    prompts: list[str] = field(default_factory=list)
    answers: list[bytes] = field(default_factory=list)
    # Every response body exactly as sent: what the attempt's diagnostic holds.
    bodies: list[str] = field(default_factory=list)

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        assert json_object
        self.prompts.append(prompt)
        if self.during is not None:
            self.during()
        if self.content is not None:
            self.bodies.append(self.content)
            return Completion(self.content, self.charge, self.generation_id)
        fields = fields_from_prompt(prompt)
        if self.mutate is not None:
            fields = self.mutate(fields)
        module_id = str(fields["module_id"])
        qa = self.qa_by_module.get(module_id, self.qa_status)
        markdown = handoff_markdown(
            identity(module_id),
            fields=fields,
            authored={**AUTHORED[qa], "qa_status": qa},
            readiness=self.readiness,
            body_note=f"{QUOTE} was recorded. {UNANCHORED} here.",
        )
        self.answers.append(markdown)
        citations: list[dict[str, object]] = [
            {"source_id": str(self.source_id), "page": 1, "matched_text": quote}
            for quote in self.quotes
        ]
        self.bodies.append(wire(markdown, citations))
        return Completion(self.bodies[-1], self.charge, self.generation_id)
