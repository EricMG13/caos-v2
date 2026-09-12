"""Phase 6 debt: the loop meets `execute_module` and charges what was reported.

`docs/REBUILD_PLAN.md` lists `test_the_loop_charges_what_the_provider_reported`
under Phase 6, owed by Phase 4. Phase 4's loop reserved an estimate and charged
whatever its stub handed back; Phase 5 built the real module execution and the
real provider, which reports `usage.cost`. This is the join.

The distinction the test exists for: an estimate is what the run set aside before
the call, and a charge is what the call cost. A ledger that recorded the estimate
would reconcile perfectly against itself and tell nobody what was spent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from conftest import gate_verdict

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import NodeState, ResolvedRoute, node_states, resolve_route
from server.engine.runtime import Execution, accepted_artifacts, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import Bundle
from server.methodology.runner import ModuleProvider
from server.provider import Completion
from server.store import RunStatus, StoreConnection
from server.store.runs import run_status, start_run

VENDORED = Path(__file__).resolve().parents[1] / "vendor/deploy-v"
PROFILE = "FULL_CREDIT_32"
# Two nodes: CP-0 and CP-DR. The smallest real pathway in the catalog.
SELECTION = "DEEP_RESEARCH"

ESTIMATE = Decimal("0.50")
# What the host configured and therefore what answered: fallbacks are off.
MODEL = "a-model/for-the-test"
# Deliberately unlike the estimate, and unlike a round number, so a ledger that
# recorded the wrong one cannot coincidentally agree.
REPORTED = Decimal("0.0000041")

REPORT = b"""Acme Holdings plc annual report 2026
Total debt at 31 December 2026 was USD 1,240.0m
"""


@dataclass
class _Completions:
    """A completion provider that answers with one valid claim, at a known cost."""

    source_id: UUID
    charge: Decimal = REPORTED
    # The identity a real provider carries: what the host configured, which
    # with fallbacks off is what answers.
    model: str = MODEL
    # What the gate says about the one other module of this pathway.
    verdict: str = "READY"
    calls: list[str] = field(default_factory=list)

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.calls.append(prompt[:40])
        body = json.dumps(
            {
                "claims": [
                    {
                        "statement": "Total debt was USD 1,240.0m.",
                        "citations": [
                            {
                                "source_id": str(self.source_id),
                                "page": 1,
                                "matched_text": "Total debt at 31 December 2026",
                            }
                        ],
                    }
                ],
                # A verdict on the rest of the route, when the prompt is the
                # gate's. This pathway is CP-0 and CP-DR alone.
                **gate_verdict(prompt, self.verdict),
            }
        )
        return Completion(
            content=body, charge=self.charge, generation_id="gen-loop-test"
        )


@pytest.fixture
def route() -> ResolvedRoute:
    catalog = json.loads(
        (
            VENDORED
            / "skills/cp-os-credit-os/references"
            / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
        ).read_text(encoding="utf-8")
    )
    return resolve_route(catalog, PROFILE, SELECTION)


@pytest.fixture
def ready(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> tuple[StoreConnection, UUID, UUID, BlobStore]:
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    [source_id] = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[Document(filename=BoundaryText.of("report.txt"), data=REPORT)],
    )
    run_id = start_run(conn, case_id)
    conn.commit()
    return conn, run_id, source_id, blobs


def _charges(conn: StoreConnection, run_id: UUID) -> list[Decimal]:
    rows = conn.execute(
        "SELECT amount FROM budget_ledger WHERE run_id = %s ORDER BY charged_at",
        (run_id,),
    ).fetchall()
    return [row[0] for row in rows]


def _reserved(conn: StoreConnection, run_id: UUID) -> list[Decimal]:
    rows = conn.execute(
        "SELECT amount FROM budget_reservations WHERE run_id = %s", (run_id,)
    ).fetchall()
    return [row[0] for row in rows]


def test_the_loop_charges_what_the_provider_reported(
    ready: tuple[StoreConnection, UUID, UUID, BlobStore], route: ResolvedRoute
) -> None:
    """The named test. Reserved the estimate, charged the report.

    Both numbers are in the store afterwards and they are different, which is
    the point: the reservation is what the ceiling was checked against, and the
    charge is what the run actually cost.
    """
    conn, run_id, source_id, blobs = ready
    completions = _Completions(source_id)
    provider = ModuleProvider(
        conn=conn,
        bundle=Bundle(root=VENDORED),
        blobs=blobs,
        completions=completions,
        delivered=_delivered(conn, source_id),
        route=route,
    )

    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(provider, ESTIMATE),
    )

    assert run_status(conn, run_id) is RunStatus.COMPLETE
    charges = _charges(conn, run_id)
    assert charges == [REPORTED, REPORTED], "the ledger holds what the calls cost"
    assert _reserved(conn, run_id) == [ESTIMATE, ESTIMATE], "and what was set aside"
    assert REPORTED != ESTIMATE, "a test that compared two equal numbers proves nothing"


def test_an_accepted_artifact_records_the_model_that_produced_it(
    ready: tuple[StoreConnection, UUID, UUID, BlobStore], route: ResolvedRoute
) -> None:
    """Invariant 3 over the one identity the store did not hold.

    A verdict binds `provider` — a string in a document this repository did not
    write — and nothing could compare it against what the runs behind it called,
    because nothing a run left behind named a model. The charge was recorded and
    the artifact was recorded; who produced them was not.

    The identity is the host's own configuration, not the provider's report of
    itself. `OpenRouter._post` sets `allow_fallbacks: false` precisely so that
    what was asked for is what answered, and reading the model back out of the
    response body would be taking a claim where the host already holds a fact
    (invariant 3).
    """
    conn, run_id, source_id, blobs = ready
    provider = ModuleProvider(
        conn=conn,
        bundle=Bundle(root=VENDORED),
        blobs=blobs,
        completions=_Completions(source_id),
        delivered=_delivered(conn, source_id),
        route=route,
    )

    run_route(
        conn, blobs, run_id=run_id, route=route, execution=Execution(provider, ESTIMATE)
    )

    recorded = conn.execute(
        "SELECT model, generation_id FROM artifacts WHERE run_id = %s", (run_id,)
    ).fetchall()
    assert [(str(row[0]), str(row[1])) for row in recorded] == [
        (MODEL, "gen-loop-test"),
        (MODEL, "gen-loop-test"),
    ], "one identity per accepted artifact, for both nodes of the pathway"


def test_the_artifact_is_the_envelope_the_host_built(
    ready: tuple[StoreConnection, UUID, UUID, BlobStore], route: ResolvedRoute
) -> None:
    """What the loop stores is the canonical envelope, addressed by its digest --
    not the provider's body, which is untrusted JSON the host has already
    replaced."""
    conn, run_id, source_id, blobs = ready
    provider = ModuleProvider(
        conn=conn,
        bundle=Bundle(root=VENDORED),
        blobs=blobs,
        completions=_Completions(source_id),
        delivered=_delivered(conn, source_id),
        route=route,
    )

    run_route(
        conn, blobs, run_id=run_id, route=route, execution=Execution(provider, ESTIMATE)
    )

    row = conn.execute(
        "SELECT artifact_sha256 FROM artifacts WHERE run_id = %s"
        " ORDER BY created_at LIMIT 1",
        (run_id,),
    ).fetchone()
    assert row is not None
    stored = json.loads(blobs.get(str(row[0])))

    assert stored["module_id"] == "CP-0", "the host's module id, not the module's"
    assert stored["build_id"].startswith("a43cb903")
    assert len(stored["authority_digest"]) == 64
    assert stored["claims"][0]["citations"][0]["bboxes"], "anchored by the host"


def test_a_module_that_cannot_be_anchored_stops_the_run(
    ready: tuple[StoreConnection, UUID, UUID, BlobStore], route: ResolvedRoute
) -> None:
    """A refusal inside a node is not a node that quietly produced nothing. The
    attempt and its reservation stay; the run does not complete."""
    conn, run_id, source_id, blobs = ready
    completions = _Completions(source_id)
    completions.source_id = UUID(int=0)  # cites evidence never delivered
    provider = ModuleProvider(
        conn=conn,
        bundle=Bundle(root=VENDORED),
        blobs=blobs,
        completions=completions,
        delivered=_delivered(conn, source_id),
        route=route,
    )

    with pytest.raises(Exception, match="CITATION_NOT_DELIVERED"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE),
        )

    assert run_status(conn, run_id) is RunStatus.RUNNING
    assert _reserved(conn, run_id) == [ESTIMATE], "the call was paid for regardless"
    assert _charges(conn, run_id) == [], "and nothing was accepted"


def test_a_node_the_gate_blocked_costs_no_call_and_no_charge(
    ready: tuple[StoreConnection, UUID, UUID, BlobStore], route: ResolvedRoute
) -> None:
    """The verdict decides what runs, driven end to end rather than composed.

    Each half held on its own -- the envelope carries the map, `_state_for`
    reads it, the frontier offers RUNNABLE and RESTRICTED -- and nothing put a
    real loop behind a real gate answer. CP-0 answers BLOCKED for the one other
    node here, so it is never offered: one call, one reservation, one charge, no
    attempt row, and a COMPLETE run reporting it unrun. A loop that ran it
    anyway would pay a provider for an answer the gate had already refused.
    """
    conn, run_id, source_id, blobs = ready
    completions = _Completions(source_id, verdict="BLOCKED")
    provider = ModuleProvider(
        conn=conn,
        bundle=Bundle(root=VENDORED),
        blobs=blobs,
        completions=completions,
        delivered=_delivered(conn, source_id),
        route=route,
    )

    run_route(
        conn, blobs, run_id=run_id, route=route, execution=Execution(provider, ESTIMATE)
    )

    nodes = {node.module_id: node.route_node_id for node in route.nodes}
    assert run_status(conn, run_id) is RunStatus.COMPLETE
    assert len(completions.calls) == 1, "the gate was asked; what it blocked was not"
    assert _charges(conn, run_id) == [REPORTED], "one charge, for the one call"
    assert _reserved(conn, run_id) == [ESTIMATE], "and one reservation behind it"
    assert _attempted(conn, run_id) == [nodes["CP-0"]], "no attempt row at all"
    states = node_states(route, accepted_artifacts(conn, blobs, route, run_id))
    assert states[nodes["CP-DR"]] is NodeState.BLOCKED, "reported unrun, with its cause"


def _attempted(conn: StoreConnection, run_id: UUID) -> list[str]:
    rows = conn.execute(
        "SELECT route_node_id FROM run_attempts WHERE run_id = %s ORDER BY started_at",
        (run_id,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _delivered(conn: StoreConnection, source_id: UUID) -> list[tuple[UUID, str]]:
    rows = conn.execute(
        "SELECT block_id FROM source_blocks WHERE source_id = %s ORDER BY block_id",
        (source_id,),
    ).fetchall()
    return [(source_id, str(row[0])) for row in rows]
