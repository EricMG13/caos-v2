"""Deterministic issuer handoffs for the catalog RELATIVE_VALUE route (§56).

The vendor owns register shapes; the values below are an independent authored
issuer example. They prove transport/lineage, not economic qualification.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
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
    conforming_rows,
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
        # `Direction` is the vendor's own enum (Positive | Negative | Mixed) and
        # the register must carry both a support and a risk (§92).
        "T2.10": [
            [str(i), driver, evidence, mechanic, implication, direction, "Medium"]
            for i, driver, evidence, mechanic, implication, direction in (
                (
                    1,
                    "Earnings shock",
                    "downside growth minus 10 percent",
                    "lower EBITDA",
                    "leverage rises",
                    "Negative",
                ),
                (
                    2,
                    "Refinancing",
                    "term loan matures 2030",
                    "cash required at maturity",
                    "monitor access to finance",
                    "Positive",
                ),
            )
        ]
    }


def _cp2g() -> dict[str, list[list[str]]]:
    # `class` is the vendor's enum and the register must carry a BASE and a
    # DOWNSIDE case (`cp2g.requires_downside_case`, §92).
    return {
        "T2H.3": [
            [
                "A-BASE-2026-growth",
                "revenue_growth",
                "BASE",
                "FY2026",
                "0.05",
                "PERCENT_DECIMAL",
                "analyst_judgment",
                "issuer-pack p1",
                "stated base case",
            ],
            [
                "A-DOWNSIDE-2026-growth",
                "revenue_growth",
                "DOWNSIDE",
                "FY2026",
                "-0.10",
                "PERCENT_DECIMAL",
                "analyst_judgment",
                "issuer-pack p1",
                "downside growth minus 10 percent",
            ],
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


def _bounded_cell(ident: HostIdentity) -> Callable[[str, int], str]:
    """The explicitly bounded finding a register cell carries for `ident`."""
    quote = QUOTES[ident.module_id]
    return lambda column, _n: f"{column}: {quote}; extract only"


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
            # Explicitly bounded findings for the remaining appendix fields,
            # shaped to the profile's own semantic rules.
            rows = conforming_rows(register, spec, rules, _bounded_cell(ident))
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


# ---------------------------------------------------------------------------
# LITE_DECISION_LEDGER (CP-0 -> CP-8), Completion Phase 9 Task 9.3.
#
# Kept apart from the RELATIVE_VALUE builder above rather than folded into it:
# the two routes pin different consumers (CP-0's T8 names exactly the route's
# own), a different decision scope, and a two-document pack -- CP-8 post-
# mortems a *decision record* (T0) against a later *outcome* (T1), and its own
# gate is that without the record it is Blocked and must "not reconstruct a
# thesis after the fact". Both documents below are an authored example issuer,
# as the pack above is: they prove the contract and lineage, not a real
# post-mortem.
# ---------------------------------------------------------------------------

LEDGER_SELECTION = ("LITE_CREDIT_22", "LITE_DECISION_LEDGER")
LEDGER_ROUTE = resolve_route(CATALOG, *LEDGER_SELECTION)
LEDGER_MODULES = tuple(n.module_id for n in LEDGER_ROUTE.nodes)
LEDGER_PACK = {
    "memo": b"""Acme Holdings plc credit committee decision record dated 2025-02-14
Decision add to the Acme senior secured term loan at an overweight posture
Position size 25 USD million approved by the credit portfolio committee
Thesis deleveraging from net leverage 3.5 times to 3.0 times by FY2025
Greatest uncertainty is a revenue decline that delays deleveraging
Expected spread tightening of 50 basis points over a 24 month hold
Exit trigger net leverage above 4.0 times at any annual test
""",
    "outcome": b"""Acme Holdings plc FY2025 outcome extract
Net leverage 2.8 times at 31 December 2025 audited
Senior secured term loan spread 300 basis points at 31 December 2025
Revenue grew 4 percent in FY2025 against FY2024
""",
}
LEDGER_FILENAMES = {"memo": "decision-record.txt", "outcome": "outcome-extract.txt"}
# Whole lines of the pack, so each quote is whole tokens (invariant 11). CP-8
# cites both sides of the window it measures: the thesis as recorded and the
# outcome as realised.
LEDGER_QUOTES: dict[str, tuple[tuple[str, str], ...]] = {
    "CP-0": (
        (
            "memo",
            "Acme Holdings plc credit committee decision record dated 2025-02-14",
        ),
    ),
    "CP-8": (
        (
            "memo",
            "Thesis deleveraging from net leverage 3.5 times to 3.0 times by FY2025",
        ),
        ("outcome", "Net leverage 2.8 times at 31 December 2025 audited"),
    ),
}


def ledger_identity(
    module: str, upstream: tuple[UpstreamRef, ...] = ()
) -> HostIdentity:
    """One node's host identity on the decision-ledger route."""
    node = next(n for n in LEDGER_ROUTE.nodes if n.module_id == module)
    if module != "CP-0" and not upstream:
        upstream = tuple(
            UpstreamRef(
                n.route_node_id,
                n.module_id,
                RUN,
                "FY2025",
                hashlib.sha256(n.module_id.encode()).hexdigest(),
            )
            for n in LEDGER_ROUTE.nodes
            if any(
                e.source == n.module_id and e.target == module
                for e in LEDGER_ROUTE.edges
            )
        )
    route = CONTRACT.routing.Route(CATALOG, *LEDGER_SELECTION)
    return HostIdentity(
        RUN,
        *LEDGER_SELECTION,
        node.route_node_id,
        module,
        route.by_module[module]["module_name"],
        "ACME",
        "Acme Holdings plc",
        "FY2025",
        "2026-09-08",
        1,
        authority_bundle_sha256(BUNDLE),
        upstream,
    )


def cp8_rows() -> dict[str, list[list[str]]]:
    """CP-8's eight registers, each cell read off the memo or the outcome.

    T7.1-T7.4 are the half a document settles: the decision and its thesis as
    recorded at T0, the outcome as realised at T1, and the variance between
    them. T7.5-T7.7 are judgement the fixture asserts and nothing can prove on
    one decision -- which is why no qualification key is written over them.
    No cell is a placeholder the vendor's critical-column blocklist refuses:
    what the record does not state is said in words and carried to T7.8.
    """
    return {
        "T7.1": [
            [
                "Add",
                "Overweight",
                "Acme senior secured term loan",
                "25 USD million",
                "2025-02-14",
                "Credit portfolio committee",
                "Completed",
            ]
        ],
        "T7.2": [
            [
                "Deleveraging from net leverage 3.5 times to 3.0 times by FY2025",
                "A revenue decline that delays deleveraging",
                "Downside path: revenue decline",
                "Spread tightening of 50 basis points",
                "Not stated in the decision record; see T7.8",
                "24 months",
                "Net leverage above 4.0 times at any annual test",
                "MEMO-1",
            ]
        ],
        "T7.3": [
            [
                "Net leverage",
                "2.8 times",
                "2025-12-31",
                "FY2025 outcome extract",
                "Final",
                "OUT-1",
            ],
            [
                "Term loan spread",
                "300 basis points",
                "2025-12-31",
                "FY2025 outcome extract",
                "Interim",
                "OUT-2",
            ],
        ],
        "T7.4": [
            [
                "Net leverage",
                "3.0 times",
                "2.8 times",
                "Favourable: 0.2 times below the recorded expectation",
                "High",
                "MEMO-1; OUT-1",
            ],
            [
                "Term loan spread",
                "50 basis points tightening",
                "300 basis points",
                "Not comparable: the entry spread was not recorded",
                "Low",
                "MEMO-1; OUT-2",
            ],
        ],
        "T7.5": [
            [
                "Net leverage 0.2 times below expectation",
                "Thesis Confirmed",
                "Y",
                "None: no process gap",
                "Deleveraging tracked the recorded base case",
                "MEMO-1; OUT-1",
            ]
        ],
        "T7.6": [
            [
                "No pattern: one decision recorded",
                "None",
                "No prior adjusted",
                "One decision, below the three-decision gate",
                "No calibration recommendation",
            ]
        ],
        "T7.7": [
            [
                "1 of 1 thesis confirmed",
                "One pathway: LITE decision ledger",
                "Thesis Confirmed: 1",
                "Record the entry spread with every decision",
            ]
        ],
        "T7.8": [
            [
                "Rating path",
                "Expected rating path",
                "Rating migration cannot be compared with an expectation",
                "T7.2 rating path left unstated",
                "Record the expected rating path at decision",
            ]
        ],
    }


def _ledger_t8(readiness: dict[str, str]) -> list[list[str]]:
    """CP-0's T8, naming exactly this route's pinned consumers."""
    rows = []
    for n, module in enumerate(LEDGER_MODULES[1:], 1):
        status = readiness.get(module, "READY")
        command = "Run " + module
        runnable = status in {"READY", "READY_WITH_LIMITATIONS"}
        rows.append(
            [
                str(n),
                module,
                command,
                command if runnable else "DO NOT RUN",
                "decision-record.txt p1",
                "Current handoff",
                status,
                "decision-record.txt p1",
            ]
        )
    return rows


def ledger_markdown(ident: HostIdentity, knobs: HandoffKnobs | None = None) -> bytes:
    """A handoff the vendor validators accept for a decision-ledger node."""
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
    quotes = [quote for _document, quote in LEDGER_QUOTES[ident.module_id]]
    authored = cp8_rows() if ident.module_id == "CP-8" else {}
    appendix = "### Analytical appendix — complete canonical registers\n\n"
    for register, spec in rules["registers"].items():
        if register == knobs.omit_register:
            continue
        columns = spec["columns"] or ["Evidence"]
        if ident.module_id == "CP-0" and register == "T8":
            columns = CONTRACT.navigation.NEW_HEADERS
            rows = _ledger_t8(knobs.readiness)
        else:
            rows = authored.get(register) or conforming_rows(
                register, spec, rules, lambda column, _n: f"{column}: {quotes[0]}"
            )
        appendix += "#### " + register + "\n\n" + _table(columns, rows)
    if knobs.quote is not None:
        quotes[-1] = knobs.quote
    note = "".join(quote + ".\n\n" for quote in quotes)
    body = "".join(
        "## " + h + "\n\n" + (appendix if h == "Analysis" else note)
        for h in CONTRACT.validate_handoff.CANONICAL_HEADINGS
    )
    return ("---\n" + _yaml(front) + "\n---\n" + body).encode()


@dataclass
class LedgerCompletions:
    """A provider answering the decision-ledger route deterministically.

    `memo_id` and `outcome_id` are the two admitted documents' source ids, so
    each citation names the document its quote is from. `quotes_by_module`
    replaces a module's *last* quote -- CP-8's realised outcome -- in both the
    body and the citation, which is how a test offers an outcome the pack does
    not hold.
    """

    memo_id: UUID
    outcome_id: UUID
    model: str = "a-model/for-the-test"
    charge: Decimal = Decimal("0.0000041")
    qa_by_module: dict[str, str] = field(default_factory=dict)
    readiness: dict[str, str] = field(default_factory=dict)
    quotes_by_module: dict[str, str] = field(default_factory=dict)
    prompts: list[str] = field(default_factory=list)
    answers: list[bytes] = field(default_factory=list)
    bodies: list[str] = field(default_factory=list)

    def request_bytes(self, prompt: str, *, json_object: bool = False) -> bytes:
        return encode_request(self.model, prompt, json_object=json_object)

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        assert json_object
        self.prompts.append(prompt)
        fields = fields_from_prompt(prompt)
        module = str(fields["module_id"])
        quotes = list(LEDGER_QUOTES[module])
        replaced = self.quotes_by_module.get(module)
        if replaced is not None:
            quotes[-1] = (quotes[-1][0], replaced)
        markdown = ledger_markdown(
            ledger_identity(module),
            HandoffKnobs(
                fields=fields,
                qa_status=self.qa_by_module.get(module, "Passed"),
                readiness=self.readiness,
                quote=replaced,
            ),
        )
        self.answers.append(markdown)
        ids = {"memo": self.memo_id, "outcome": self.outcome_id}
        citations: list[dict[str, object]] = [
            {"source_id": str(ids[document]), "page": 1, "matched_text": quote}
            for document, quote in quotes
        ]
        self.bodies.append(wire(markdown, citations))
        return Completion(self.bodies[-1], self.charge, "gen-decision-ledger")
