"""Deterministic, source-derived CP-3C contract handoffs (route remains disabled)."""

# ruff: noqa: E501 -- fixture rows mirror the vendored Markdown table schema.

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from canonical_fixtures import (
    AUTHORED,
    BUNDLE,
    CATALOG,
    CONTRACT,
    RUN,
    conforming_rows,
    skill,
)
from lite_route_fixtures import _table, _yaml

from server.engine.route import resolve_route
from server.methodology.handoff import HostIdentity, UpstreamRef, invocation_fields
from server.methodology.vendor import authority_bundle_sha256

SELECTION = ("FULL_CREDIT_32", "COVENANT_REFINANCING")
ROUTE = resolve_route(CATALOG, *SELECTION)
MODULES = tuple(node.module_id for node in ROUTE.nodes)
LIMITATION = "Executed debt documents, current market data and CP-2C sponsor evidence are not supplied"
LEGAL_INDICATORS = (
    "Incremental debt capacity",
    "Lien capacity",
    "Unrestricted subsidiary capacity",
    "Investment capacity",
    "RP/junior debt payment capacity",
    "Collateral release",
    "Guarantor release",
    "Amendment thresholds",
    "Sacred rights",
    "Open-market purchase provisions",
    "MFN protection",
    "Intercreditor terms",
    "Class voting",
    "Pro rata sharing provisions",
)


@dataclass(frozen=True)
class RefinancingFacts:
    carrying_debt: int = 600
    gross_principal: int = 660
    cash: int = 120
    facility_commitment: int = 100
    facility_drawn: int = 20
    forecast_fcf: int = 50
    maturity_years: int = 2
    extension_amount: int = 200
    extension_date: str = "2026-03-15"
    extension_maturity: str = "2030-12-31"

    @property
    def available_liquidity(self) -> int:
        return self.cash + self.facility_commitment - self.facility_drawn

    @property
    def funding_gap(self) -> int:
        return self.carrying_debt - self.available_liquidity - self.forecast_fcf


FACTS = RefinancingFacts()


def refinancing_pack(facts: RefinancingFacts) -> bytes:
    return (
        "Acme Holdings FY2025 annual report\n"
        f"Term loan carrying value {facts.carrying_debt} USD million; gross principal "
        f"{facts.gross_principal} USD million; maturity 2027-12-31; senior secured fixed rate.\n"
        f"Cash and equivalents {facts.cash} USD million. Revolving facility commitment "
        f"{facts.facility_commitment} USD million, drawn {facts.facility_drawn} USD million, "
        f"committed and expires 2029-12-31. Forecast free cash flow {facts.forecast_fcf} "
        "USD million.\n"
        f"Subsequent event: on {facts.extension_date}, {facts.extension_amount} USD million "
        f"of the term loan was extended to {facts.extension_maturity}.\n"
        "No executed credit agreement, indenture, intercreditor agreement, or compliance certificate supplied.\n"
    ).encode()


PACK = refinancing_pack(FACTS)


def source_quote(facts: RefinancingFacts) -> str:
    return (
        f"Term loan carrying value {facts.carrying_debt} USD million; "
        f"gross principal {facts.gross_principal} USD million"
    )


QUOTE = source_quote(FACTS)


def cp3c_identity(module: str, upstream: tuple[UpstreamRef, ...] = ()) -> HostIdentity:
    node = next(node for node in ROUTE.nodes if node.module_id == module)
    name = CONTRACT.routing.Route(CATALOG, *SELECTION).by_module[module]["module_name"]
    return HostIdentity(
        RUN,
        *SELECTION,
        node.route_node_id,
        module,
        name,
        "ACME",
        "Acme Holdings",
        "FY2025",
        "2026-09-19",
        1,
        authority_bundle_sha256(BUNDLE),
        upstream,
    )


def _rows(facts: RefinancingFacts) -> dict[str, list[list[str]]]:
    return {
        "T3D.1": [
            [
                "annual-report",
                "FY2025 annual report",
                "audited",
                "FY2025",
                "Acme Holdings",
                "debt, cash, facility and FCF",
                "executed debt documents absent",
                "funding gap",
            ]
        ],
        "T3D.2": [
            [
                "Term loan",
                str(facts.carrying_debt),
                "USD",
                "2027-12-31",
                str(facts.maturity_years),
                "senior secured",
                "fixed",
                "fixed",
                "not disclosed",
                "high: within two-year horizon",
                "refinancing required",
                f"annual report debt note: carrying value {facts.carrying_debt}; same note: gross principal {facts.gross_principal}; material definition conflict retained",
            ]
        ],
        "T3D.3": [
            [
                "Funding gap",
                f"cash {facts.cash} + committed undrawn {facts.facility_commitment - facts.facility_drawn} + FCF {facts.forecast_fcf}; as-of maturity wall only, subsequent extension is pro-forma only",
                f"{facts.funding_gap} USD million shortfall",
                "Increasing",
                "internal sources below maturity wall",
                "external refinancing required",
                "High",
                "annual report debt and cash disclosures",
            ],
            [
                "Subsequent-event refinancing",
                f"On {facts.extension_date}, {facts.extension_amount} USD million was extended to {facts.extension_maturity}",
                f"pro forma maturity wall {facts.carrying_debt - facts.extension_amount} USD million; as-of wall remains {facts.carrying_debt} USD million",
                "Decreasing",
                "extension reduces but does not replace the as-of maturity wall",
                "assess as-of and pro-forma views separately",
                "High",
                "annual report subsequent-events disclosure",
            ],
            [
                "Market access",
                "[Market Data Not Provided] — no current price, spread, yield, rating or outlook supplied",
                "market feasibility not established",
                "Low",
                "ordinary-course execution cannot be evidenced",
                "path conclusions remain conditional",
                "Low",
                "T3D.11 market-data gap",
            ],
        ],
        "T3D.4": [
            [
                indicator,
                "Unclear",
                "Executed debt documents not supplied",
                "capacity cannot be inferred from market convention",
                "no LME path enabled or asserted",
                "Low",
                "T3D.11 executed-document gap",
            ]
            for indicator in LEGAL_INDICATORS
        ],
        "T3D.5": [
            [
                factor,
                "No sponsor/governance evidence supplied",
                "[Insufficient Information] — CP-2C unavailable",
                "willingness cannot be inferred from identity",
                "no sponsor-supported path is assumed",
                "T3D.11 sponsor/governance gap",
            ]
            for factor in (
                "Historical sponsor refinancing/LME behaviour",
                "Current sponsor support signals",
                "Sponsor economic incentive",
                "Governance structure",
            )
        ],
        "T3D.6": [
            [
                "Consensual refinancing",
                "[Insufficient Information] — market data unavailable",
                "[Insufficient Information] — market direction unavailable",
                f"maturity wall and {facts.funding_gap} funding gap",
                "current market data not provided",
                "ordinary refinancing access",
                "existing creditors face refinancing execution risk",
                "annual report / T3D.3 market-data gap",
            ],
            [
                "Priming debt",
                "[Insufficient Information] — executed documents unavailable",
                "[Insufficient Information] — legal capacity unavailable",
                "maturity pressure only",
                "legal capacity and sponsor willingness are not supported",
                "incremental debt, lien and intercreditor capacity",
                "most adverse scenario only; no LME intent inferred",
                "T3D.4 / T3D.5 gaps",
            ],
        ],
        "T3D.7": [
            [
                "Refinancing pressure",
                "High",
                f"{facts.carrying_debt} due versus {facts.available_liquidity + facts.forecast_fcf} internal sources",
                f"{facts.funding_gap} funding gap",
                "elevated refinancing vulnerability",
                "annual report",
            ],
            [
                "Legal capacity",
                "[Insufficient Information] — executed documents unavailable",
                "no executed debt documents supplied",
                "coercive capacity is unsupported",
                "no LME path is treated as feasible",
                "T3D.4 / T3D.11",
            ],
            [
                "Sponsor willingness",
                "[Insufficient Information] — CP-2C unavailable",
                "no sponsor/governance evidence supplied",
                "willingness is unsupported",
                "no sponsor-driven path is assumed",
                "T3D.5 / T3D.11",
            ],
            [
                "Market access",
                "[Insufficient Information] — market data unavailable",
                "current market data not provided",
                "feasibility cannot be evidenced",
                "consensual path remains conditional",
                "T3D.3 / T3D.11",
            ],
            [
                "Recovery impact",
                "[Insufficient Information] — coercive path unsupported",
                "no supported coercive path or legal mechanics",
                "priming and subordination are scenario-only",
                "no recovery conclusion",
                "T3D.6 / T3D.8",
            ],
            [
                "Overall Prime/LME vulnerability",
                "[Insufficient Information] — required evidence unavailable",
                "refinancing pressure is meaningful but legal capacity and willingness are unsupported",
                "pressure alone cannot establish LME vulnerability",
                "consensual refinancing is a provisional scenario, not a feasibility conclusion",
                "T3D.2-T3D.6",
            ],
        ],
        "T3D.8": [
            [
                "Senior secured term lenders",
                "existing claim",
                "refinancing stress",
                "priming-debt scenario exposure only",
                "no recovery conclusion",
                "not established without executed documents",
                "annual report / T3D.4 gap",
            ]
        ],
        "T3D.9": [
            [
                "Funding access",
                "refinancing progress",
                "before 2027 maturity",
                "Leading",
                "external funding needed",
                "Consensual refinancing",
                "annual report",
            ],
            [
                "Market access",
                "price / spread / yield / rating evidence",
                "first current market-data observation",
                "Leading",
                "changes consensual-refinancing feasibility",
                "Consensual refinancing; Amend & Extend",
                "T3D.3 market-data gap",
            ],
            [
                "Legal-capacity evidence",
                "executed debt documents received",
                "first source-supported capacity conclusion",
                "Leading",
                "may change the Prime/LME score and adverse path",
                "Priming debt; Uptier; Drop-down",
                "T3D.4 legal gap",
            ],
        ],
        "T3D.10": [
            [
                "Base",
                f"{facts.available_liquidity + facts.forecast_fcf} internal sources and ordinary access",
                "Consensual refinancing",
                "before 2027",
                "refinancing execution",
                "not assessed",
                "[Insufficient Information] — market direction unavailable",
                "Low",
                "annual report",
            ],
            [
                "Stress",
                "FCF or access deteriorates",
                "Amend & Extend",
                "before 2027",
                "heightened creditor risk",
                "not assessed",
                "Increasing",
                "Low",
                "annual report / gaps ledger",
            ],
            [
                "LME",
                "ordinary access fails and executed documents later support priming capacity",
                "Priming debt",
                "scenario only; before 2027 maturity",
                "non-participants could be subordinated",
                "potential recovery impairment if the assumptions hold",
                "[Insufficient Information] — legal capacity unavailable",
                "Low",
                "T3D.4 gap; no LME intent asserted",
            ],
        ],
        "T3D.11": [
            [
                "Legal capacity",
                "Executed debt documents",
                "cannot determine LME paths",
                "LME conclusion restricted",
                "obtain executed agreements and amendments",
            ],
            [
                "Market access",
                "ratings and market evidence",
                "cannot assess feasibility",
                "market path conditional",
                "obtain current market evidence",
            ],
            [
                "Sponsor and governance",
                "CP-2C or equivalent sponsor/governance evidence",
                "willingness cannot be inferred from identity",
                "sponsor path and vulnerability score remain limited",
                "obtain current sponsor/governance evidence",
            ],
            [
                "Downside and recovery",
                "CP-2A downside, recovery evidence and historical LME precedent",
                "stress severity and recovery mechanics cannot be evidenced",
                "stress/LME scenarios and creditor recovery remain conditional",
                "obtain downside, recovery and precedent evidence",
            ],
        ],
    }


def _analysis(facts: RefinancingFacts) -> str:
    sources = facts.available_liquidity + facts.forecast_fcf
    pro_forma_wall = facts.carrying_debt - facts.extension_amount
    return (
        "### Liquidity view\n\n"
        f"At the balance-sheet date, {facts.carrying_debt} USD million matures inside "
        f"the two-year window against {sources} USD million of cash, committed undrawn "
        f"capacity and forecast free cash flow, leaving a {facts.funding_gap} USD million "
        f"funding gap. The {facts.extension_date} subsequent extension is not blended into "
        f"that view; pro forma, the maturity wall falls to {pro_forma_wall} USD million. "
        "Consensual refinancing is the provisional base scenario, but current market data "
        "is not supplied, so it is not an assessed most-likely path. "
        "Executed debt documents and sponsor evidence are also absent, so legal capacity, "
        "willingness, priming mechanics and recovery effects are not asserted. Overall "
        "Prime/LME vulnerability is Insufficient Information with Low evidence confidence; "
        "pressure alone cannot establish a coercive path. CP-3C Completed with Limitations. "
        "Prime/LME Vulnerability: Insufficient Information. Key Gaps: legal, market, sponsor "
        "and recovery evidence.\n\n"
    )


def cp3c_markdown(
    ident: HostIdentity,
    *,
    facts: RefinancingFacts = FACTS,
    omit_register: str | None = None,
    fields: dict[str, Any] | None = None,
    qa_status: str = "Restricted",
) -> bytes:
    rules = CONTRACT.completeness_check.load_contract(skill("CP-3C").decode(), "CP-3C")
    front = {
        **(fields or invocation_fields(CONTRACT, ident)),
        "confidence_score": 90,
        "confidence_band": "High",
        "committee_status": "Draft Only",
        "limitation_flags": [],
        "validation_warnings": [],
        "downstream_consumers": [],
        **AUTHORED[qa_status],
        "qa_status": qa_status,
    }
    if qa_status == "Restricted":
        front["limitation_flags"] = [LIMITATION]
    appendix = "### Analytical appendix — complete canonical registers\n\n"
    for register, spec in rules["registers"].items():
        if register == omit_register:
            continue
        rows = _rows(facts).get(register) or conforming_rows(
            register, spec, rules, lambda column, _: f"{column}: annual report"
        )
        appendix += (
            "#### " + register + "\n\n" + _table(spec["columns"] or ["Evidence"], rows)
        )
    body = "".join(
        "## "
        + heading
        + "\n\n"
        + (
            _analysis(facts) + appendix
            if heading == "Analysis"
            else source_quote(facts) + "\n\n"
        )
        for heading in CONTRACT.validate_handoff.CANONICAL_HEADINGS
    )
    return ("---\n" + _yaml(front) + "\n---\n" + body).encode()


def direct_upstream(include_cp4: bool = True) -> tuple[UpstreamRef, ...]:
    modules = ("CP-0", "CP-1", "CP-2D") + (("CP-4",) if include_cp4 else ())
    return tuple(
        UpstreamRef(
            cp3c_identity(module).route_node_id,
            module,
            RUN,
            "FY2025",
            hashlib.sha256(module.encode()).hexdigest(),
        )
        for module in modules
    )
