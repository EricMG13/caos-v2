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
from server.engine.route import GATE_MODULE, ResolvedRoute, frontier
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserve
from server.store.runs import Accepted, accept_attempt, complete_run, start_attempt


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


def artifact_digests(conn: StoreConnection, run_id: UUID) -> dict[str, str]:
    """Every accepted artifact of the run, keyed by route node id.

    One join, read in one place. `accepted_artifacts` below and
    `server.methodology.runner.ModuleProvider._upstream` both need exactly this
    row set -- the first to decide which nodes are COMPLETE and which body
    to read, the second to read a node's predecessors' bodies -- and a query
    string kept twice is a join two callers can silently drift out of step on
    the day the schema moves under one of them and not the other.
    """
    # Ordered, because the rows collapse into a dict and a node may hold more
    # than one accepted attempt: the latest wins, which is a rule rather than
    # whatever order the planner returned. Presence was all `node_states`
    # needed; Phase 11's chain reads the winning artifact's *contents* into the
    # next node's prompt, so which one wins is now part of the answer.
    rows = conn.execute(
        "SELECT attempts.route_node_id, artifacts.artifact_sha256"
        " FROM artifacts"
        " JOIN run_attempts AS attempts USING (attempt_id)"
        " WHERE artifacts.run_id = %s"
        " ORDER BY artifacts.created_at",
        (run_id,),
    ).fetchall()
    return {str(route_node_id): str(digest) for route_node_id, digest in rows}


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
        node.route_node_id for node in route.nodes if node.module_id == GATE_MODULE
    }
    return {
        node_id: (_body(blobs, digest) if node_id in readiness_nodes else {})
        for node_id, digest in artifact_digests(conn, run_id).items()
    }


def _body(blobs: BlobStore, artifact_sha256: str) -> object:
    """One stored artifact, decoded, or the refusal `proof.py` gives for the same
    bytes.

    `object` rather than a mapping: whatever JSON produced, unnarrowed. The one
    caller that reads into it, `readiness_from`, already answers "no readiness"
    to a body that is not a mapping, and narrowing here would turn that into a
    refusal -- a different question from whether the bytes can be read at all.

    This read sits on `GET /api/runs/{run_id}`, so an untyped decode error here
    is a 500 whose logged message quotes the document's own bytes. A blob
    refusal is folded into the same code because absent, damaged and undecodable
    bytes are one situation to a caller: the artifact this run accepted cannot
    be read back.

    Refused after the `except` rather than from inside it, the way
    `store_connection` refuses an unreachable database: raised outside the
    handler, the refusal carries neither `__cause__` nor `__context__`, so the
    decoder's message -- which quotes the bytes it choked on -- is not reachable
    from what a logger is handed. That is invariant 2's shape, and
    `test_a_cp0_artifact_that_is_not_json_is_a_typed_refusal` asserts both are
    `None` rather than trusting the placement.
    """
    try:
        return json.loads(blobs.get(artifact_sha256))
    except (ValueError, Refusal):
        pass
    raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)


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
        accepted=Accepted(
            artifact_sha256=result.artifact_sha256,
            charge=result.charge,
            model=result.model,
            generation_id=result.generation_id,
        ),
    )
