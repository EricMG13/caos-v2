"""The frontier loop. No checkpointer: recovery is recomputation.

`docs/DECISIONS.md` §3. Execution state *is* the accepted-attempt ledger, so a
process that dies leaves nothing to restore -- the next one recomputes
`node_states` over the rows that survived and the frontier falls out of them. A
node that completed is not run again because it is COMPLETE, not because
something remembered it.

The order inside one pass is deliberate and is invariant 8's shape:

    check the context  ->  start the attempt  ->  reserve  ->  call  ->  accept

The attempt row exists before the call because it is the identity the call is
charged against. The reservation is taken before the call and commits on its own,
because a call that reached the provider is billable whether or not this process
lived to record it (`server/store/budget.py`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from server.blobs import BlobStore
from server.engine.route import (
    GATE_MODULE,
    EdgeType,
    NamedObjects,
    NodeResult,
    NodeState,
    ResolvedRoute,
    frontier,
    node_states,
)
from server.methodology.bundle import Bundle
from server.methodology.canonical import (
    Replayed,
    Verdict,
    accepted_projections,
    blocked_verdict,
    replay_billed,
    unexplained_charge,
)
from server.methodology.invocation import named_objects
from server.methodology.verification import AcceptedRow
from server.pricing import ModelPrice, worst_case
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserve
from server.store.gates import execution_input

# `artifact_digests` is re-exported: it now lives in the store (no import cycle).
from server.store.outcomes import (
    accepted_rows,
    execution_reads,
    record_refusal,
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
from server.store.work import Lease, holds_lease


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

    def check_context(self, route_node_id: str, module_id: str) -> None:
        """Refuse a context the call could not carry (`CONTEXT_OVER_CEILING`),
        before the loop starts an attempt or reserves anything (§45.3)."""

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        """Call for this reserved attempt and record its own call outcome --
        the charge, the producer identity and the diagnostic address -- before
        returning, as `execute_handoff` does the moment the provider answers.

        The loop does not record it a second time: a call that reached the
        provider must be billed by the unit that made it, because only that
        unit is still running when the answer arrives (invariant 6).
        """


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
    # The worker's claim on this run; None is a direct caller (harness, tests),
    # which may drive only a run that was never enqueued (brief 4.3 D3).
    lease: Lease | None = None


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
    # Read once from verified bundle bytes, handed to the pure engine (§46.1).
    named = named_objects(execution.bundle, route)
    try:
        _drive(
            conn, blobs, run_id=run_id, route=route, execution=execution, named=named
        )
    except Refusal as refusal:
        # D8: the accepted set moved between the decision and the lock. One
        # more pass decides again from the store; a second move raises.
        if refusal.code is not RefusalCode.RUN_TERMINAL_STALE:
            raise
        _drive(
            conn, blobs, run_id=run_id, route=route, execution=execution, named=named
        )


def _refuse_unexplained(
    conn: StoreConnection,
    run_id: UUID,
    ready: Sequence[str],
    lease: Lease | None,
) -> None:
    """Refuse a ready node already paid for whose answer was never stored.

    `replay_billed` needs a body to settle from; this outcome has none, so the
    next pass would start a fresh attempt and pay for the same node twice with
    nobody choosing to. The lease answer comes first: a caller that lost the
    run is told that before it is told anything about what the run contains,
    which is the order every write in `_run_node` takes.
    """
    if unexplained_charge(conn, run_id=run_id, route_node_ids=ready) is None:
        return
    if not holds_lease(conn, run_id, lease):
        raise Refusal(RefusalCode.LEASE_NOT_HELD)
    raise Refusal(RefusalCode.CALL_OUTCOME_UNEXPLAINED)


def _drive(  # noqa: PLR0913 -- one run, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    execution: Execution,
    named: NamedObjects,
) -> None:
    """The frontier passes and the terminal decision, whose terminal call
    carries the accepted set it was decided from (brief 4.3 D8)."""
    bundle = execution.bundle
    while True:
        with execution_reads(conn):
            accepted = accepted_artifacts(conn, blobs, route, run_id, bundle=bundle)
            ready = frontier(route, accepted, named)
            # Before any attempt: an answer whose bill committed but whose
            # acceptance, block or explanation did not (a crash in that gap)
            # is settled from its stored body, never paid for twice (D7).
            replayed = (
                replay_billed(
                    conn,
                    blobs,
                    bundle,
                    run_id=run_id,
                    route=route,
                    route_node_ids=ready,
                )
                if ready
                else None
            )
            # A charge whose body was never stored cannot be replayed, and
            # starting a fresh attempt over it would pay for the same node
            # twice without anyone choosing to. Park the run instead.
            if ready and replayed is None:
                _refuse_unexplained(conn, run_id, ready, execution.lease)
        if replayed is not None:
            if not _settle(conn, blobs, replayed, run_id=run_id, lease=execution.lease):
                return
            continue
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
        states = node_states(route, accepted, named)
    # Re-derived under `lock_run` by the store, which refuses a moved snapshot.
    decided = frozenset(accepted)
    if all(state is NodeState.COMPLETE for state in states.values()):
        complete_run(conn, run_id, lease=execution.lease, accepted=decided)
    else:
        block_run(conn, run_id, lease=execution.lease, accepted=decided)


def _settle(
    conn: StoreConnection,
    blobs: BlobStore,
    replayed: Replayed,
    *,
    run_id: UUID,
    lease: Lease | None,
) -> bool:
    """Act on a replayed verdict with no call. Returns False once the run ended.

    ANSWERED accepts the stored answer under its original bill; BLOCKED ends the
    run as a live Blocked handoff does (a node's own verdict, so no snapshot);
    REFUSED writes the explanation once and refuses with its code, so the
    caller stops and a retry makes one new attempt instead of replaying it.
    """
    if replayed.verdict is Verdict.BLOCKED:
        block_run(conn, run_id, lease=lease, verdict=replayed.attempt_id)
        return False
    outcome = replayed.outcome
    if replayed.verdict is Verdict.REFUSED or outcome is None:
        code = replayed.code or RefusalCode.PROVIDER_RESPONSE_INVALID
        record_refusal(conn, attempt_id=replayed.attempt_id, code=code, lease=lease)
        raise Refusal(code)
    stored: tuple[str, str] | None = None
    try:
        stored = blobs.put(outcome.markdown), blobs.put(outcome.record)
    except (OSError, Refusal):
        pass  # raised below, outside the handler: no context carried
    if stored is None:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE)
    accept_attempt(
        conn,
        attempt_id=replayed.attempt_id,
        accepted=Accepted(
            artifact_sha256=stored[0],
            charge=outcome.charge,
            model=outcome.model,
            generation_id=outcome.generation_id,
            diagnostic_sha256=outcome.diagnostic_sha256,
            record_sha256=stored[1],
        ),
        lease=lease,
    )
    return True


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

    One query for the rows. A row without its host record refuses
    `ARTIFACT_RECORD_MISMATCH`: no artifact is read as a claims body (§42.1).
    Per readiness node, readiness and `qa_status` come from its record,
    verified against its Markdown under `bundle` (§42.4) -- the host
    identity's queries, two blob reads and the vendor validators, per pass.
    Without a bundle such a row refuses `ORCHESTRATION_ARTIFACT_UNREADABLE`.
    """
    qa_sources = {e.source for e in route.edges if e.type is EdgeType.QA_GATE}
    readiness_nodes = {
        node.route_node_id
        for node in route.nodes
        if node.module_id == GATE_MODULE or node.module_id in qa_sources
    }
    accepted: dict[str, NodeResult] = {}
    rows = accepted_rows(conn, run_id)
    # The one reading every verified row's lineage is compared with.
    pairs = {node_id: (digest, record) for node_id, _a, digest, record in rows}
    for node_id, attempt, digest, record in rows:
        if record is None:
            raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        if node_id not in readiness_nodes:
            accepted[node_id] = NodeResult()
        elif bundle is None:
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        else:
            projections = accepted_projections(
                conn,
                blobs,
                bundle,
                route,
                AcceptedRow(
                    run_id=run_id,
                    route_node_id=node_id,
                    attempt_id=attempt,
                    artifact_sha256=digest,
                    record_sha256=record,
                ),
                accepted=pairs,
            )
            accepted[node_id] = NodeResult(
                readiness=tuple(projections.readiness),
                qa_status=projections.qa_status,
            )
    return accepted


def _explain_live(
    conn: StoreConnection, attempt_id: UUID, refused: Refusal, lease: Lease | None
) -> None:
    """Write why a recorded call's answer was refused, once (D7). A store that
    cannot take the explanation leaves it unwritten -- the caller keeps the
    original refusal, and the next pass's replay explains the stored answer."""
    try:
        record_refusal(conn, attempt_id=attempt_id, code=refused.code, lease=lease)
    except Refusal as fault:
        if fault.code not in _STORE_FAULTS:
            raise


_STORE_FAULTS = frozenset(
    {
        RefusalCode.BLOB_ADDRESS_INVALID,
        RefusalCode.BLOB_DIGEST_MISMATCH,
        RefusalCode.BLOB_NOT_FOUND,
        RefusalCode.STORE_UNAVAILABLE,
        RefusalCode.STORE_NOT_TRANSACTIONAL,
    }
)


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
    # The whole prompt is built and bounded while nothing is started or set
    # aside: an over-ceiling context costs no attempt, reservation or call.
    execution.provider.check_context(route_node_id, module_id)
    lease = execution.lease
    attempt_id = start_attempt(conn, run_id, route_node_id, lease=lease)
    reserve(conn, attempt_id, worst_case(execution.price), lease=lease)

    _execution_route(conn, run_id, route, execution.bundle)
    refused: Refusal | None = None
    result: ProviderResult | None = None
    try:
        result = execution.provider.execute(
            route_node_id, module_id, attempt_id=attempt_id
        )
    except Refusal as refusal:
        refused = refusal
    if refused is not None and refused.code is not RefusalCode.HANDOFF_BLOCKED:
        # A recorded call's answer is explained once, so no retry replays it
        # (D7); an attempt with no recorded call writes nothing.
        _explain_live(conn, attempt_id, refused, lease)
        raise refused
    if result is None:
        _end_blocked(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            node=route_node_id,
            execution=execution,
        )
        return False

    _execution_route(conn, run_id, route, execution.bundle)
    # ponytail: the executor recorded this outcome with the call, and `_accept`
    # commits exactly it before it enters `_accept_artifact`, so no accepted
    # artifact can be unbilled; a record here as well would be a knowing no-op
    # costing a COMMIT and two row locks. Ceiling: a provider that returns
    # without having billed its own call loses that call outright to a crash
    # before acceptance -- `replay_billed` needs the joined ledger row and a
    # stored body, `unexplained_charge` needs the outcome row, so neither
    # matches and the node is re-attempted and paid for again with nobody
    # deciding to. Nothing inside the acceptance unit can reach that window;
    # only a record adjacent to the call can, which is where this one is.
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
        lease=lease,
    )
    return True


def _end_blocked(  # noqa: PLR0913 -- one node of one run, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    node: str,
    execution: Execution,
) -> None:
    """End the run BLOCKED on a validated Blocked handoff (brief correction 6).

    The raised code is not trusted: the verdict is re-derived from the stored
    bill and response body by the same `replay_billed` crash recovery uses,
    and a Blocked claim it does not confirm is an ordinary refusal. The attempt
    it confirms is what the transition records as the reason (§68): this is
    the last moment the answer can be judged, since `check_attempt` refuses a
    replay once the run is no longer RUNNING.
    """
    with execution_reads(conn):
        blocked = blocked_verdict(
            conn,
            blobs,
            execution.bundle,
            run_id=run_id,
            route=route,
            route_node_ids=(node,),
        )
    if blocked is None:
        raise Refusal(RefusalCode.HANDOFF_BLOCKED)
    block_run(conn, run_id, lease=execution.lease, verdict=blocked)


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
