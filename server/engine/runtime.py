"""The frontier loop. No checkpointer: recovery is recomputation.

`docs/DECISIONS.md` §3. Execution state *is* the accepted-attempt ledger, so a
process that dies leaves nothing to restore -- the next one recomputes
`node_states` over the rows that survived and the frontier falls out of them. A
node that completed is not run again because it is COMPLETE, not because
something remembered it.

The order inside one pass is deliberate and is invariant 8's shape:

    start the attempt  ->  reserve  ->  call the provider  ->  accept

The attempt row exists before the call because it is the identity the call is
charged against. The reservation is taken before the call and commits on its own,
because a call that reached the provider is billable whether or not this process
lived to record it (`server/store/budget.py`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, frontier
from server.store import StoreConnection
from server.store.budget import reserve
from server.store.runs import accept_attempt, complete_run, start_attempt

CP0 = "CP-0"


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """What one module's execution produced: an artifact, and what it cost."""

    artifact_sha256: str
    charge: Decimal


class Provider(Protocol):
    """The seam Phase 5 fills with a real OpenRouter call."""

    def execute(self, route_node_id: str, module_id: str) -> ProviderResult: ...


@dataclass(frozen=True, slots=True)
class Execution:
    """How this run executes: who to ask, and what to set aside before asking.

    One thing rather than two loose arguments, because neither is meaningful
    without the other -- an estimate with no provider reserves against nothing,
    and a provider with no estimate is a call invariant 8 forbids.
    """

    provider: Provider
    estimate: Decimal


def run_route(
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    execution: Execution,
) -> None:
    """Run the route to its end, or leave it recoverable.

    Every pass recomputes the frontier from the store rather than advancing an
    index, so this is the same function whether it is starting a run or resuming
    one that died three nodes in.
    """
    while ready := frontier(route, accepted_artifacts(conn, blobs, route, run_id)):
        for route_node_id in ready:
            _run_node(
                conn,
                run_id=run_id,
                route=route,
                route_node_id=route_node_id,
                execution=execution,
            )
    complete_run(conn, run_id)


def accepted_artifacts(
    conn: StoreConnection, blobs: BlobStore, route: ResolvedRoute, run_id: UUID
) -> dict[str, Any]:
    """The run's accepted attempts, keyed by route node.

    Only CP-0's body is fetched. `node_states` reads readiness from that artifact
    and needs nothing but presence from the others, so fetching every payload
    would be a blob read per node per pass for data nobody looks at -- the ~8x
    shape `docs/AI_CODE_QUALITY.md` section 1 measures.
    """
    readiness_nodes = {
        node.route_node_id for node in route.nodes if node.module_id == CP0
    }
    rows = conn.execute(
        "SELECT attempts.route_node_id, artifacts.artifact_sha256"
        " FROM artifacts"
        " JOIN run_attempts AS attempts USING (attempt_id)"
        " WHERE artifacts.run_id = %s",
        (run_id,),
    ).fetchall()

    accepted: dict[str, Any] = {}
    for route_node_id, digest in rows:
        node_id = str(route_node_id)
        accepted[node_id] = (
            json.loads(blobs.get(str(digest))) if node_id in readiness_nodes else {}
        )
    return accepted


def _run_node(
    conn: StoreConnection,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    route_node_id: str,
    execution: Execution,
) -> None:
    """One try at one node. One attempt row, one reservation, one acceptance."""
    module_id = next(
        node.module_id for node in route.nodes if node.route_node_id == route_node_id
    )
    attempt_id = start_attempt(conn, run_id, route_node_id)
    reserve(conn, attempt_id, execution.estimate)

    result = execution.provider.execute(route_node_id, module_id)

    accept_attempt(
        conn,
        attempt_id=attempt_id,
        artifact_sha256=result.artifact_sha256,
        charge=result.charge,
    )
