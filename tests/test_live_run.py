"""A live run, end to end: documents admitted, modules run, citations re-located.

Every link of this chain has its own test -- admission, route resolution, the
frontier loop, the provider, the proof -- and the live provider has answered a
single module (`test_module_execution.py`). Nothing drove the whole chain
against a model that really answers, so nothing showed the application working.
This does, with the provider built the way the application builds it: from the
environment (`OpenRouter.from_environment`, `docs/DECISIONS.md` §16).

Two documents, one per extractor, so the case holds a PDF as well as text. The
pathway is `DEEP_RESEARCH` -- CP-0 then CP-DR, the smallest route with an edge
in it -- because two calls cost under a cent and a nightly job exists to prove
the chain, not the catalog. `CAOS_LIVE_PATHWAY` names a larger one on demand.

What is asserted is what the host can prove, never the model's wording: the run
finished, every pinned node was accepted, and the proof re-derived every
citation against the documents (`server/qualification/proof.py`). It skips with
its reason without a credential, and `CAOS_REQUIRE_PROVIDER=1` turns the skip
into a failure.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from test_pdf_extraction import minimal_pdf

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import resolve_route
from server.engine.runtime import Execution, run_route
from server.evidence.ingest import Document, admit_pack
from server.evidence.pdf import PdfExtractor
from server.methodology.bundle import Bundle
from server.methodology.runner import ModuleProvider
from server.provider import OpenRouter
from server.qualification.proof import assert_orchestration_proof
from server.refusals import Refusal
from server.store import RunStatus, StoreConnection
from server.store.routes import pin_route
from server.store.runs import run_status, start_run

VENDORED = Path(__file__).resolve().parents[1] / "vendor/deploy-v"
CATALOG = (
    VENDORED / "skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"
PATHWAY = os.environ.get("CAOS_LIVE_PATHWAY", "DEEP_RESEARCH")
# The flat per-node reservation (CLAUDE.md, Phase 4). Nineteen of them -- the
# full assessment -- fit `server/store/budget.py`'s five-dollar `CEILING`, and a
# call on gpt-4o-mini costs about a tenth of a cent. It is what is set aside,
# not a cap on the call: a model priced like a frontier one can charge more per
# call than this, which is the per-model price table's gap (CLAUDE.md, Phase 5).
ESTIMATE = Decimal("0.10")

PROVIDER_REQUIRED = os.environ.get("CAOS_REQUIRE_PROVIDER") == "1"
_NO_CREDENTIAL = (
    "OPENROUTER_API_KEY or OPENROUTER_MODEL is unset: there is no live provider"
)

# One line per block, so a quote is a phrase on one line of one block.
REPORT = b"""Acme Holdings plc annual report 2026
Revenue for the year ended 31 December 2026 was USD 2,815.0m
EBITDA for the year was USD 412.3m
Total debt at 31 December 2026 was USD 1,240.0m
Cash and equivalents stood at USD 310.5m
The revolving credit facility of USD 500.0m matures in June 2029
"""
STATEMENT = minimal_pdf(
    [
        "Acme Holdings plc lender update Q4 2026",
        "Net leverage fell to 2.3x from 2.9x a year earlier",
        "Interest cover was 5.1x for the year",
    ]
)


def test_a_live_run_admits_documents_and_completes_its_route(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    try:
        completions = OpenRouter.from_environment()
    except Refusal:
        if PROVIDER_REQUIRED:
            pytest.fail(_NO_CREDENTIAL)
        pytest.skip(_NO_CREDENTIAL)

    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    bundle = Bundle(root=VENDORED)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    route = resolve_route(catalog, PROFILE, PATHWAY)

    # One extractor per admission, so the PDF is admitted on its own.
    text = Document(filename=BoundaryText.of("report.txt"), data=REPORT)
    pdf = Document(filename=BoundaryText.of("statement.pdf"), data=STATEMENT)
    source_ids = admit_pack(conn, blobs, case_id=case_id, documents=[text])
    source_ids += admit_pack(
        conn, blobs, case_id=case_id, documents=[pdf], extractor=PdfExtractor()
    )
    run_id = start_run(conn, case_id)
    conn.commit()
    pin_route(conn, run_id, route)

    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(
            ModuleProvider(
                conn=conn,
                bundle=bundle,
                blobs=blobs,
                completions=completions,
                delivered=_every_block(conn, source_ids),
                route=route,
            ),
            ESTIMATE,
        ),
    )

    assert run_status(conn, run_id) is RunStatus.COMPLETE
    # A run whose frontier emptied with nodes still BLOCKED is COMPLETE too, so
    # the count is what says every pinned node was accepted.
    proof = assert_orchestration_proof(conn, blobs, bundle, run_id=run_id)
    assert proof.artifacts == len(route.nodes)

    producers = conn.execute(
        "SELECT model, generation_id FROM artifacts WHERE run_id = %s", (run_id,)
    ).fetchall()
    assert {row[0] for row in producers} == {completions.model}
    assert all(row[1] for row in producers), "a call left no handle for the bill"

    charges = conn.execute(
        "SELECT amount FROM budget_ledger WHERE run_id = %s", (run_id,)
    ).fetchall()
    assert len(charges) == len(route.nodes)
    assert all(isinstance(row[0], Decimal) and row[0] >= 0 for row in charges)


def _every_block(
    conn: StoreConnection, source_ids: list[UUID]
) -> list[tuple[UUID, str]]:
    """Every block of every admitted document, delivered to every node: what the
    qualification harness delivers, for the same reason."""
    rows = conn.execute(
        "SELECT source_id, block_id FROM source_blocks"
        " WHERE source_id = ANY(%s) ORDER BY source_id, block_id",
        (source_ids,),
    ).fetchall()
    return [(UUID(str(row[0])), str(row[1])) for row in rows]
