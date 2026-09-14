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
from server.engine.route import (
    GATE_MODULE,
    EdgeType,
    NodeState,
    ResolvedRoute,
    frontier,
    node_states,
)
from server.methodology.bundle import Bundle
from server.pricing import ModelPrice, worst_case
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserve
from server.store.gates import execution_input
from server.store.outcomes import (
    CallOutcome,
    execution_reads,
    record_outcome,
    require_idle,
)
from server.store.runs import (
    Accepted,
    accept_attempt,
    block_run,
    complete_run,
    start_attempt,
)


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """What one module's execution produced: an artifact, what it cost, and who
    produced it.

    The identity travels beside the charge because they are recorded together
    and for the same reason: a run has to be able to say afterwards what was
    spent and what spent it (invariant 3).
    """

    artifact_sha256: str
    charge: Decimal
    model: str
    generation_id: str


class Provider(Protocol):
    """The seam Phase 5 fills with a real OpenRouter call.

    `model` is the configured model identity the call is billed as; a run's price
    must be for exactly that model.
    """

    @property
    def model(self) -> str: ...

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult: ...


@dataclass(frozen=True, slots=True)
class Execution:
    """How this run executes: who to ask, and what to set aside before asking.

    One thing rather than loose arguments, because none is meaningful without
    the others -- a price with no provider reserves against nothing, and a
    provider with no price is a call invariant 8 forbids. Every call reserves
    `worst_case(price)`, never a caller's guess (F06).
    """

    provider: Provider
    price: ModelPrice
    bundle: Bundle


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
    one that died three nodes in. Requires an idle, nonautocommit connection;
    owns its frontier reads and never adopts pending caller writes.
    """
    require_idle(conn)
    # Priced for the configured model, or no attempt at all.
    if execution.price.model != getattr(execution.provider, "model", None):
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    worst_case(execution.price)
    route = _execution_route(conn, run_id, route, execution.bundle)
    while True:
        with execution_reads(conn):
            ready = frontier(route, accepted_artifacts(conn, blobs, route, run_id))
        if not ready:
            break
        for route_node_id in ready:
            _run_node(
                conn,
                run_id=run_id,
                route=route,
                route_node_id=route_node_id,
                execution=execution,
            )
    # §39: success only when every pinned node was accepted; an empty frontier
    # with unfinished required work ends the run blocked.
    with execution_reads(conn):
        states = node_states(route, accepted_artifacts(conn, blobs, route, run_id))
    if all(state is NodeState.COMPLETE for state in states.values()):
        complete_run(conn, run_id)
    else:
        block_run(conn, run_id)


def artifact_digests(conn: StoreConnection, run_id: UUID) -> dict[str, str]:
    """Every accepted artifact of the run, keyed by route node id.

    One query, read in one place. `accepted_artifacts` below and
    `server.methodology.executor._upstream_digests` both need exactly this
    row set -- the first to decide which nodes are COMPLETE and which body
    to read, the second to read a node's predecessors' bodies -- and a query
    string kept twice is a join two callers can silently drift out of step on
    the day the schema moves under one of them and not the other.
    """
    # One row per node: `artifacts UNIQUE (run_id, route_node_id)` makes the
    # accepted owner a database fact, so no ordering picks a winner.
    rows = conn.execute(
        "SELECT route_node_id, artifact_sha256 FROM artifacts WHERE run_id = %s",
        (run_id,),
    ).fetchall()
    return {str(route_node_id): str(digest) for route_node_id, digest in rows}


def accepted_artifacts(
    conn: StoreConnection, blobs: BlobStore, route: ResolvedRoute, run_id: UUID
) -> dict[str, Any]:
    """The run's accepted attempts, keyed by route node.

    Only CP-0's and the QA gate source's bodies are fetched. `node_states` reads
    readiness and QA clearance from those and needs nothing but presence from the
    others, so fetching every payload
    would be a blob read per node per pass for data nobody looks at -- the ~8x
    shape `docs/AI_CODE_QUALITY.md` section 1 measures.
    """
    qa_sources = {e.source for e in route.edges if e.type is EdgeType.QA_GATE}
    readiness_nodes = {
        node.route_node_id
        for node in route.nodes
        if node.module_id == GATE_MODULE or node.module_id in qa_sources
    }
    try:
        return {
            node_id: (
                json.loads(blobs.get(digest)) if node_id in readiness_nodes else {}
            )
            for node_id, digest in artifact_digests(conn, run_id).items()
        }
    except ValueError:
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE) from None


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
    # Per call as well as per run: a provider whose model moved is unpriced.
    if execution.price.model != getattr(execution.provider, "model", None):
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    attempt_id = start_attempt(conn, run_id, route_node_id)
    reserve(conn, attempt_id, worst_case(execution.price))

    _execution_route(conn, run_id, route, execution.bundle)
    result = execution.provider.execute(route_node_id, module_id, attempt_id=attempt_id)

    require_idle(conn)
    record_outcome(
        conn,
        attempt_id=attempt_id,
        outcome=CallOutcome(result.charge, result.model, result.generation_id),
    )
    _execution_route(conn, run_id, route, execution.bundle)
    accept_attempt(
        conn,
        attempt_id=attempt_id,
        accepted=Accepted(
            artifact_sha256=result.artifact_sha256,
            charge=result.charge,
            model=result.model,
            generation_id=result.generation_id,
        ),
    )


def _execution_route(
    conn: StoreConnection,
    run_id: UUID,
    requested: ResolvedRoute,
    bundle: Bundle,
) -> ResolvedRoute:
    """Return current stored authority from one bounded, lock-owning read unit."""
    with execution_reads(conn):
        _input, stored = execution_input(conn, run_id, bundle)
        if stored != requested:
            raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
        return stored
