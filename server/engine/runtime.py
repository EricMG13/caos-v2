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
from typing import Protocol
from uuid import UUID

from server.blobs import BlobStore
from server.engine.route import (
    GATE_MODULE,
    EdgeType,
    NodeResult,
    NodeState,
    ResolvedRoute,
    claims_result,
    frontier,
    node_states,
)
from server.methodology.bundle import Bundle
from server.methodology.canonical import accepted_projections, blocked_verdict
from server.pricing import ModelPrice, worst_case
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserve
from server.store.gates import execution_input

# `artifact_digests` is re-exported: it now lives in the store (no import cycle).
from server.store.outcomes import (
    CallOutcome,
    accepted_rows,
    execution_reads,
    record_outcome,
    require_idle,
)
from server.store.outcomes import artifact_digests as artifact_digests
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
    # A canonical pin's host record and the call's diagnostic body (§42).
    record_sha256: str | None = None
    diagnostic_sha256: str | None = None


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
    bundle = execution.bundle
    while True:
        with execution_reads(conn):
            accepted = accepted_artifacts(conn, blobs, route, run_id, bundle=bundle)
            ready = frontier(route, accepted)
            # Before any attempt: a Blocked verdict whose bill committed but
            # whose block did not (a crash in that gap) is never paid twice.
            blocked = bool(ready) and blocked_verdict(
                conn, blobs, bundle, run_id=run_id, route=route, route_node_ids=ready
            )
        if blocked:
            block_run(conn, run_id)
            return
        if not ready:
            break
        for route_node_id in ready:
            if not _run_node(
                conn,
                blobs,
                run_id=run_id,
                route=route,
                route_node_id=route_node_id,
                execution=execution,
            ):
                return  # A validated Blocked handoff ended the run BLOCKED.
    # §39: success only when every pinned node was accepted; an empty frontier
    # with unfinished required work ends the run blocked.
    with execution_reads(conn):
        accepted = accepted_artifacts(conn, blobs, route, run_id, bundle=bundle)
        states = node_states(route, accepted)
    if all(state is NodeState.COMPLETE for state in states.values()):
        complete_run(conn, run_id)
    else:
        block_run(conn, run_id)


def accepted_artifacts(
    conn: StoreConnection,
    blobs: BlobStore,
    route: ResolvedRoute,
    run_id: UUID,
    *,
    bundle: Bundle | None = None,
) -> dict[str, NodeResult]:
    """The run's accepted attempts, keyed by route node, as typed results.

    Only CP-0's and the QA gate source's bodies are fetched. `node_states` reads
    readiness and QA clearance from those and needs nothing but presence from the
    others, so fetching every payload
    would be a blob read per node per pass for data nobody looks at -- the ~8x
    shape `docs/AI_CODE_QUALITY.md` section 1 measures.

    One query for the rows, then per readiness node: a claims row
    (`record_sha256` NULL) is one blob read of its JSON body (`claims_result`);
    a canonical row's
    readiness and `qa_status` come from its record, verified against its
    Markdown under `bundle` (§42.4) -- the host identity's queries, two blob
    reads and the vendor validators, per pass. Without a bundle such a row
    refuses rather than be read as JSON.
    """
    qa_sources = {e.source for e in route.edges if e.type is EdgeType.QA_GATE}
    readiness_nodes = {
        node.route_node_id
        for node in route.nodes
        if node.module_id == GATE_MODULE or node.module_id in qa_sources
    }
    gates = {n.route_node_id for n in route.nodes if n.module_id == GATE_MODULE}
    accepted: dict[str, NodeResult] = {}
    for node_id, attempt, digest, record in accepted_rows(conn, run_id):
        if node_id not in readiness_nodes:
            accepted[node_id] = NodeResult()
        elif record is None:
            accepted[node_id] = claims_result(
                _claims_body(blobs, digest), gate=node_id in gates
            )
        elif bundle is None:
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        else:
            projections = accepted_projections(
                conn,
                blobs,
                bundle,
                route,
                run_id=run_id,
                route_node_id=node_id,
                attempt_id=attempt,
                artifact_sha256=digest,
                record_sha256=record,
            )
            accepted[node_id] = NodeResult(
                readiness=tuple(projections.readiness),
                qa_status=projections.qa_status,
            )
    return accepted


def _claims_body(blobs: BlobStore, digest: str) -> object:
    try:
        return json.loads(blobs.get(digest))
    except ValueError:
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE) from None


def _run_node(  # noqa: PLR0913 -- one node of one run, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    route_node_id: str,
    execution: Execution,
) -> bool:
    """One try at one node. One attempt row, one reservation, one acceptance.

    Returns False when a validated Blocked handoff ended the run BLOCKED: the
    bill and diagnostic are already recorded, nothing is accepted, no retry.
    """
    module_id = next(
        node.module_id for node in route.nodes if node.route_node_id == route_node_id
    )
    # Per call as well as per run: a provider whose model moved is unpriced.
    if execution.price.model != getattr(execution.provider, "model", None):
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    attempt_id = start_attempt(conn, run_id, route_node_id)
    reserve(conn, attempt_id, worst_case(execution.price))

    _execution_route(conn, run_id, route, execution.bundle)
    try:
        result = execution.provider.execute(
            route_node_id, module_id, attempt_id=attempt_id
        )
    except Refusal as refusal:
        if refusal.code is not RefusalCode.HANDOFF_BLOCKED:
            raise
        result = None
    if result is None:
        _end_blocked(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            node=route_node_id,
            bundle=execution.bundle,
        )
        return False

    require_idle(conn)
    # The canonical executor recorded its diagnostic with the call: this is
    # then an exact replay, and acceptance binds the host record (§42).
    record_outcome(
        conn,
        attempt_id=attempt_id,
        outcome=CallOutcome(
            result.charge,
            result.model,
            result.generation_id,
            result.diagnostic_sha256,
        ),
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
            diagnostic_sha256=result.diagnostic_sha256,
            record_sha256=result.record_sha256,
        ),
    )
    return True


def _end_blocked(  # noqa: PLR0913 -- one node of one run, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    node: str,
    bundle: Bundle,
) -> None:
    """End the run BLOCKED on a validated Blocked handoff (brief correction 6).

    The raised code is not trusted: the verdict is re-derived from the stored
    bill and response body by the same `blocked_verdict` crash recovery uses,
    and a Blocked claim it does not confirm is an ordinary refusal.
    """
    with execution_reads(conn):
        blocked = blocked_verdict(
            conn,
            blobs,
            bundle,
            run_id=run_id,
            route=route,
            route_node_ids=(node,),
        )
    if not blocked:
        raise Refusal(RefusalCode.HANDOFF_BLOCKED)
    block_run(conn, run_id)


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
