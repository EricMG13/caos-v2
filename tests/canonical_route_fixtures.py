"""Deterministic issuer handoffs for the catalog RELATIVE_VALUE route (§56).

The vendor owns register shapes; the values below are an independent authored
issuer example. They prove transport/lineage, not economic qualification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from canonical_fixtures import (
    AUTHORED,
    BUNDLE,
    CATALOG,
    CONTRACT,
    RUN,
    fields_from_prompt,
    skill,
    wire,
)
from lite_route_fixtures import _table, _yaml

from server.engine.route import resolve_route
from server.methodology.bundle import verified_bytes
from server.methodology.handoff import HostIdentity, UpstreamRef, invocation_fields
from server.methodology.vendor import authority_bundle_sha256
from server.provider import Completion, encode_request

SELECTION = ("FULL_CREDIT_32", "RELATIVE_VALUE")
ROUTE = resolve_route(CATALOG, *SELECTION)
MODULES = tuple(n.module_id for n in ROUTE.nodes)
OWNERS = tuple(m for m in MODULES if m != "CP-0")
PACK = b"""Acme Holdings plc FY2025 annual report extract
Revenue 1000 EBITDA 200 cash 100 debt 600 capex 40 interest 30 tax 20
Operating cash flow 140 and free cash flow 100 in USD millions consolidated
FY2026 base revenue growth 5 percent downside revenue growth minus 10 percent
Acme facility agreement dated 2025-01-01 section 12
Senior secured term loan 600 USD million fixed coupon 5 percent matures 2030
Maximum net leverage 4.0 times tested annually against covenant EBITDA
Restricted payments require net leverage below 3.0 times
Acme peer and market table dated 2026-09-08
Beta plc revenue 900 EBITDA 180 debt 500 cash 80 FY2025 USD million
Acme loan mid price 98 spread 350 basis points Beta loan spread 320 basis points
"""
QUOTES = {
    "CP-0": "Acme Holdings plc FY2025 annual report extract",
    "CP-1": "Revenue 1000 EBITDA 200 cash 100 debt 600",
    "CP-1C": "Beta plc revenue 900 EBITDA 180 debt 500 cash 80",
    "CP-2": "Operating cash flow 140 and free cash flow 100",
    "CP-4": "Maximum net leverage 4.0 times tested annually against covenant EBITDA",
    "CP-3D": "Acme loan mid price 98 spread 350 basis points",
    "CP-2A": "downside revenue growth minus 10 percent",
    "CP-2G": "FY2026 base revenue growth 5 percent",
    "CP-3": "Beta loan spread 320 basis points",
}
LIMITATION = (
    "Peer sample contains one comparable issuer; sizing requires portfolio data"
)


def route_identity(module: str, upstream: tuple[UpstreamRef, ...] = ()) -> HostIdentity:
    node = next(n for n in ROUTE.nodes if n.module_id == module)
    if module != "CP-0" and not upstream:
        upstream = tuple(
            UpstreamRef(
                n.route_node_id,
                n.module_id,
                RUN,
                "FY2025",
                hashlib.sha256(n.module_id.encode()).hexdigest(),
            )
            for n in ROUTE.nodes
            if any(e.source == n.module_id and e.target == module for e in ROUTE.edges)
        )
    return HostIdentity(
        RUN,
        *SELECTION,
        node.route_node_id,
        module,
        CONTRACT.routing.Route(CATALOG, *SELECTION).by_module[module]["module_name"],
        "ACME",
        "Acme Holdings plc",
        "FY2025",
        "2026-09-08",
        1,
        authority_bundle_sha256(BUNDLE),
        upstream,
    )


def driver_schema() -> dict[str, Any]:
    return dict(
        json.loads(
            verified_bytes(
                BUNDLE,
                "CP-2G",
                "references/CP-2G__ForwardCreditModel__payload.schema.txt",
            )
        )["$defs"]["forecast_driver"]
    )


def forecast_driver_rows() -> list[list[str]]:
    """Vendor's 42 rows: two cases, three years, seven drivers per year.

    The vendor driver vocabulary differs from CP-CF's movement vocabulary.
    Preserve it for the explicit 5.2b mapping, never rename vendor columns.
    """
    rows = []
    for case, growth in (("BASE", "0.05"), ("DOWNSIDE", "-0.10")):
        for year in (2026, 2027, 2028):
            drivers = [("division_growth", f"DIVISION_{i}", growth) for i in (1, 2, 3)]
            drivers += [
                (d, "", "0")
                for d in (
                    "acquisitions_disposals",
                    "net_equity_issue_repay",
                    "dividends_paid",
                    "other_investing_financing",
                )
            ]
            for driver, slot, value in drivers:
                rows.append(
                    [
                        driver,
                        slot,
                        case,
                        f"FY{year}",
                        str(year),
                        value,
                        "PERCENT_DECIMAL" if slot else "CURRENCY_MM",
                        f"A-{case}-{year}-{driver}-{slot}",
                        "READY",
                        "issuer-pack",
                        "issuer-pack.txt p1 forecast assumptions",
                        "2026-09-08",
                    ]
                )
    return rows


def _cp1() -> dict[str, list[list[str]]]:
    return {
        "T4.14": [
            [
                "FY2025",
                "FY",
                "actual",
                "2025-01-01/2025-12-31",
                "audited",
                "USD",
                "million",
                "reported",
                "consolidated",
                "issuer-pack p1",
            ]
        ],
        "T4.15": [
            [
                m,
                "FY2025",
                v,
                "+",
                "reported",
                "READY",
                "issuer-pack p1",
                "none disclosed",
                "annual only",
            ]
            for m, v in (
                ("revenue", "1000"),
                ("ebitda", "200"),
                ("cash", "100"),
                ("debt", "600"),
            )
        ],
        "T4.18": [
            [
                "TERM",
                "FY2025",
                "600",
                "600",
                "600",
                "600",
                "secured",
                "senior",
                "5 percent fixed",
                "2030",
            ]
        ],
        "T4.19": [
            [
                "net-debt",
                "FY2025",
                "500",
                "500",
                "0",
                "0.001",
                "reconciled",
                "600 debt less 100 cash",
            ]
        ],
    }


def _cp4() -> dict[str, list[list[str]]]:
    return {
        "T4C.4": [
            [
                "Net leverage",
                "maintenance",
                "4.0x",
                "FY2025",
                "(600-100)/200",
                "1.5x",
                "compliant",
                "annual test",
                "EBITDA decline erodes headroom",
                "monitor earnings",
                "issuer-pack p1 section 12",
            ]
        ]
    }


def _cp1c() -> dict[str, list[list[str]]]:
    return {
        "T4.3": [
            [
                "Beta plc",
                "900",
                "not disclosed in extract",
                "not disclosed in extract",
                "180",
                "20 percent",
                "not disclosed in extract",
                "FY2025",
                "USD million",
                "180/900",
                "same period and currency",
            ]
        ]
    }


def _cp2a() -> dict[str, list[list[str]]]:
    return {
        "T2B.4": [
            [
                "Revenue falls 10 percent",
                "reduced cash generation",
                "leverage rises at unchanged debt",
                "less covenant headroom",
                "stated downside assumption",
                "issuer-pack p1",
            ]
        ]
    }


def _cp3d() -> dict[str, list[list[str]]]:
    return {
        "T3E.2": [
            [
                "ACME-TERM",
                "mid 98",
                "not supplied in extract",
                "350bp spread",
                "not supplied in extract",
                "Beta loan 320bp",
                "issuer-pack p1 market table",
            ]
        ]
    }


def _cp2() -> dict[str, list[list[str]]]:
    return {
        "T2.10": [
            [str(i), driver, evidence, mechanic, implication, "negative", "Medium"]
            for i, driver, evidence, mechanic, implication in (
                (
                    1,
                    "Earnings shock",
                    "downside growth minus 10 percent",
                    "lower EBITDA",
                    "leverage rises",
                ),
                (
                    2,
                    "Refinancing",
                    "term loan matures 2030",
                    "cash required at maturity",
                    "monitor access to finance",
                ),
            )
        ]
    }


def _cp2g() -> dict[str, list[list[str]]]:
    return {
        "T2H.3": [
            [
                "A-BASE-2026-growth",
                "revenue_growth",
                "BASE",
                "FY2026",
                "0.05",
                "PERCENT_DECIMAL",
                "analyst assumption",
                "issuer-pack p1",
                "stated base case",
            ]
        ]
    }


def _cp3() -> dict[str, list[list[str]]]:
    return {
        "T3.5": [
            [
                "ACME-TERM",
                "98 / 350bp",
                "2026-09-08",
                "issuer-pack p1",
                "mid indicative",
                "Beta loan 320bp",
                "senior secured",
                "30bp premium with limited comparability",
                "monitor",
            ]
        ]
    }


_ROWS = {
    "CP-1": _cp1,
    "CP-4": _cp4,
    "CP-1C": _cp1c,
    "CP-2A": _cp2a,
    "CP-3D": _cp3d,
    "CP-2": _cp2,
    "CP-2G": _cp2g,
    "CP-3": _cp3,
}


@dataclass
class HandoffKnobs:
    fields: dict[str, Any] | None = None
    qa_status: str = "Passed"
    omit_register: str | None = None
    readiness: dict[str, str] = field(default_factory=dict)
    quote: str | None = None


def canonical_markdown(ident: HostIdentity, knobs: HandoffKnobs | None = None) -> bytes:
    knobs = knobs or HandoffKnobs()
    front = {
        **(knobs.fields or invocation_fields(CONTRACT, ident)),
        "confidence_score": 90,
        "confidence_band": "High",
        "committee_status": "Draft Only",
        "limitation_flags": [],
        "validation_warnings": [],
        "downstream_consumers": [],
        **AUTHORED[knobs.qa_status],
        "qa_status": knobs.qa_status,
    }
    if knobs.qa_status == "Restricted":
        front["limitation_flags"] = [LIMITATION]
    rules = CONTRACT.completeness_check.load_contract(
        skill(ident.module_id).decode(), ident.module_id
    )
    authored = _ROWS[ident.module_id]() if ident.module_id in _ROWS else {}
    appendix = "### Analytical appendix — complete canonical registers\n\n"
    for register, spec in rules["registers"].items():
        if register == knobs.omit_register:
            continue
        columns = spec["columns"] or ["Evidence"]
        rows = authored.get(register)
        if ident.module_id == "CP-0" and register == "T8":
            columns = CONTRACT.navigation.NEW_HEADERS
            rows = [
                [
                    str(i),
                    m,
                    "Run " + m,
                    "Run " + m
                    if knobs.readiness.get(m, "READY")
                    in {"READY", "READY_WITH_LIMITATIONS"}
                    else "DO NOT RUN",
                    "issuer-pack p1",
                    "Current handoff",
                    knobs.readiness.get(m, "READY"),
                    "issuer-pack p1",
                ]
                for i, m in enumerate(OWNERS, 1)
            ]
        if rows is None:
            # Explicitly bounded findings for the remaining appendix fields.
            rows = [
                [
                    f"{column}: {QUOTES[ident.module_id]}; extract only"
                    for column in columns
                ]
                for _ in range(max(1, spec["minimum_body_rows"]))
            ]
        appendix += "#### " + register + "\n\n" + _table(columns, rows)
    stable_registers = dict(
        zip(
            rules["unconditional_stable_tables"],
            ("T4.14", "T4.15", "T4.16", "T4.17", "T4.18", "T4.19", "T4.13"),
            strict=False,
        )
    )
    for table_id in rules["unconditional_stable_tables"]:
        if ident.module_id == "CP-2G":
            columns, rows = driver_schema()["required"], forecast_driver_rows()
        elif ident.module_id == "CP-1":
            register = stable_registers[table_id]
            columns = rules["registers"][register]["columns"]
            rows = authored.get(
                register, [[f"{c}: issuer-pack p1; extract only" for c in columns]]
            )
        else:
            columns, rows = ["source_locator"], [["issuer-pack p1"]]
        appendix += f"<!-- table-id: {table_id} -->\n" + _table(columns, rows)
    body = "".join(
        "## "
        + h
        + "\n\n"
        + (
            appendix
            if h == "Analysis"
            else (knobs.quote or QUOTES[ident.module_id]) + "\n\n"
        )
        for h in CONTRACT.validate_handoff.CANONICAL_HEADINGS
    )
    return ("---\n" + _yaml(front) + "\n---\n" + body).encode()


@dataclass
class RouteCompletions:
    source_id: UUID
    model: str = "a-model/for-the-test"
    charge: Decimal = Decimal("0.0000041")
    qa_by_module: dict[str, str] = field(default_factory=dict)
    readiness: dict[str, str] = field(default_factory=dict)
    quotes_by_module: dict[str, str] = field(default_factory=dict)
    prompts: list[str] = field(default_factory=list)
    answers: list[bytes] = field(default_factory=list)

    def request_bytes(self, prompt: str, *, json_object: bool = False) -> bytes:
        return encode_request(self.model, prompt, json_object=json_object)

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        assert json_object
        self.prompts.append(prompt)
        fields = fields_from_prompt(prompt)
        module = str(fields["module_id"])
        markdown = canonical_markdown(
            route_identity(module),
            HandoffKnobs(
                fields=fields,
                qa_status=self.qa_by_module.get(module, "Passed"),
                readiness=self.readiness,
                quote=self.quotes_by_module.get(module),
            ),
        )
        self.answers.append(markdown)
        return Completion(
            wire(
                markdown,
                [
                    {
                        "source_id": str(self.source_id),
                        "page": 1,
                        "matched_text": self.quotes_by_module.get(
                            module, QUOTES[module]
                        ),
                    }
                ],
            ),
            self.charge,
            "gen-relative-value",
        )
