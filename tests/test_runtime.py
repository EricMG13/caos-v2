"""Phase 4 exit test: recovery is recomputation, not restoration.

`docs/DECISIONS.md` §3: execution state *is* the accepted-attempt ledger. There
is no checkpointer, so there is nothing to restore and nothing that can disagree
with the domain state -- which is where most of the predecessor's recovery
machinery came from.

A process that dies mid-run leaves accepted attempts behind. The next one
recomputes `node_states` over exactly those rows and continues from the frontier
that falls out. A node that completed is not run again, because it is COMPLETE,
not because anything remembered that it was.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import (
    Execution,
    Provider,
    ProviderResult,
    accepted_artifacts,
    run_route,
)
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.events import RunEvent, events_of
from server.store.runs import run_status, start_run

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"
# Four nodes: CP-0, CP-1, CP-2, CP-2D. Small enough to count attempts by hand.
SELECTION = "LIQUIDITY_REVIEW"
ESTIMATE = Decimal("0.10")

# CP-0's artifact says every module's evidence is there, so no soft edge is left
# soft and the route runs straight through.
READY_EVERYWHERE: dict[str, Any] = {
    "content_to_module_map": [
        {"module_id": module, "readiness_status": "READY"}
        for module in ("CP-1", "CP-2", "CP-2D")
    ]
}


class _Boom(Exception):
    """A process death, in the only form a test can arrange."""


@dataclass
class _Provider:
    """Records what it was asked for, and can die on a chosen node."""

    blobs: BlobStore
    die_on: str | None = None

    def __post_init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, route_node_id: str, module_id: str) -> ProviderResult:
        self.calls.append(module_id)
        if module_id == self.die_on:
            raise _Boom(module_id)
        payload: dict[str, Any] = (
            READY_EVERYWHERE if module_id == "CP-0" else {"module_id": module_id}
        )
        digest = self.blobs.put(json.dumps(payload).encode("utf-8"))
        return ProviderResult(
            artifact_sha256=digest,
            charge=Decimal("0.01"),
            model="a-model/for-the-test",
            generation_id="gen-runtime-test",
        )


def test_the_fake_provider_satisfies_the_protocol(blobs: BlobStore) -> None:
    """`Provider` is the seam Phase 5 fills with a real OpenRouter call. If the
    stand-in here did not satisfy it, these tests would be exercising a shape
    the real provider will not have."""
    provider: Provider = _Provider(blobs)

    result = provider.execute("RN-x", "CP-1")

    assert result.artifact_sha256
    assert result.charge == Decimal("0.01")


@pytest.fixture
def route() -> ResolvedRoute:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return resolve_route(catalog, PROFILE, SELECTION)


@pytest.fixture
def blobs(tmp_path: Path) -> BlobStore:
    return BlobStore(tmp_path / "blobs")


def _attempts_per_module(conn: StoreConnection, run_id: UUID) -> dict[str, int]:
    rows = conn.execute(
        "SELECT route_node_id, count(*) FROM run_attempts"
        " WHERE run_id = %s GROUP BY route_node_id",
        (run_id,),
    ).fetchall()
    return {str(node_id): int(count) for node_id, count in rows}


def test_a_route_runs_to_completion(
    case: tuple[StoreConnection, UUID], route: ResolvedRoute, blobs: BlobStore
) -> None:
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    provider = _Provider(blobs)

    run_route(
        conn, blobs, run_id=run_id, route=route, execution=Execution(provider, ESTIMATE)
    )

    assert provider.calls == ["CP-0", "CP-1", "CP-2", "CP-2D"]
    assert run_status(conn, run_id) is RunStatus.COMPLETE
    assert [e.name for e in events_of(conn, run_id)].count(
        RunEvent.RUN_COMPLETE.value
    ) == 1


def test_recovery_is_recomputation(
    case: tuple[StoreConnection, UUID], route: ResolvedRoute, blobs: BlobStore
) -> None:
    """The Phase 4 exit test. Kill mid-run, restart, and the run completes
    without restarting completed nodes and without a checkpoint file."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()

    dying = _Provider(blobs, die_on="CP-2")
    with pytest.raises(_Boom):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(dying, ESTIMATE),
        )

    assert dying.calls == ["CP-0", "CP-1", "CP-2"]
    assert run_status(conn, run_id) is RunStatus.RUNNING
    before = _attempts_per_module(conn, run_id)

    # The restart. Nothing was restored: node_states is recomputed over the rows
    # that survived, and the frontier falls out of them.
    restarted = _Provider(blobs)
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(restarted, ESTIMATE),
    )

    assert restarted.calls == ["CP-2", "CP-2D"], "completed nodes are not run again"
    assert run_status(conn, run_id) is RunStatus.COMPLETE

    after = _attempts_per_module(conn, run_id)
    completed_before = [
        node_id
        for node_id, count in before.items()
        if node_id != _node_id(route, "CP-2")
    ]
    for node_id in completed_before:
        assert after[node_id] == 1, "an accepted node was attempted a second time"


def test_no_checkpoint_is_written_anywhere(
    case: tuple[StoreConnection, UUID], route: ResolvedRoute, blobs: BlobStore
) -> None:
    """`docs/DECISIONS.md` §3: no checkpointer. The store's own tables are the
    execution state, so there is no second place for it to disagree from."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()

    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(_Provider(blobs), ESTIMATE),
    )

    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = current_schema()"
    ).fetchall()
    assert not [name for (name,) in tables if "checkpoint" in str(name)]


def test_a_failed_attempt_leaves_its_row_and_its_reservation(
    case: tuple[StoreConnection, UUID], route: ResolvedRoute, blobs: BlobStore
) -> None:
    """One attempt row per try. The row and the reservation outlive the failure,
    because the call may have reached the provider and may be billed."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()

    with pytest.raises(_Boom):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(_Provider(blobs, die_on="CP-1"), ESTIMATE),
        )

    row = conn.execute(
        "SELECT count(*) FROM budget_reservations WHERE run_id = %s", (run_id,)
    ).fetchone()
    assert row is not None
    assert row[0] == 2, "CP-0 and the failed CP-1 both reserved"


def test_the_run_stops_when_the_ceiling_is_reached(
    case: tuple[StoreConnection, UUID], route: ResolvedRoute, blobs: BlobStore
) -> None:
    """Invariant 8 reaching the loop: the next node is refused, not attempted."""
    conn, case_id = case
    run_id = start_run(conn, case_id, budget_ceiling=Decimal("0.15"))
    conn.commit()
    provider = _Provider(blobs)

    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE),
        )

    assert caught.value.code is RefusalCode.BUDGET_CEILING_REACHED
    assert provider.calls == ["CP-0"], "the second node never reached the provider"


def test_accepted_artifacts_reads_cp0s_payload_and_no_other(
    case: tuple[StoreConnection, UUID], route: ResolvedRoute, blobs: BlobStore
) -> None:
    """`node_states` needs CP-0's readiness and nothing else's body, so nothing
    else's body is fetched from the blob store."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(_Provider(blobs), ESTIMATE),
    )

    accepted = accepted_artifacts(conn, blobs, route=route, run_id=run_id)

    assert accepted[_node_id(route, "CP-0")] == READY_EVERYWHERE
    assert accepted[_node_id(route, "CP-1")] == {}


def _node_id(route: ResolvedRoute, module_id: str) -> str:
    return next(n.route_node_id for n in route.nodes if n.module_id == module_id)
