"""Running one module: authority in, canonical envelope out.

The seam where four things meet, each of which the host owns and the module does
not: the bundle's verified authority (invariant 4), the evidence actually
delivered to this node (invariant 2), the provider call and its charge
(invariant 8), and the citation anchoring that decides whether a quote may reach
an artifact at all (invariant 11).

A module is asked a question and returns JSON. Everything it says about itself is
discarded: the envelope the host stores carries the module id the host asked for,
the build the host read, and the authority digest the host computed. That is
invariant 3, and it is the reason `execute_module` returns an `Envelope` built
here rather than the object the provider sent.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import (
    GATE_MODULE,
    EdgeType,
    ResolvedRoute,
    RouteNode,
    predecessors,
)
from server.engine.runtime import artifact_digests
from server.evidence.citations import verify_citations
from server.evidence.read import read_run_block
from server.methodology import CLAIMS_ADAPTER_VERSION as CLAIMS_ADAPTER_VERSION
from server.methodology.bundle import (
    Authority,
    Bundle,
    assemble_authority,
    authority_digest,
)
from server.methodology.envelope import (
    Claim,
    Envelope,
    parse_claims,
    parse_qa,
    parse_readiness,
)
from server.provider import CompletionProvider, _reported_charge
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.gates import execution_input
from server.store.outcomes import (
    CallOutcome,
    check_attempt,
    check_call,
    execution_reads,
    producer_identifier,
    record_outcome,
    require_idle,
)

# The two ways a quote fails to anchor. Either costs the claim resting on it and
# nothing more (docs/DECISIONS.md §26); any other refusal is the module breaking
# the contract, and refuses the answer.
QUOTE_MISSES = frozenset(
    {RefusalCode.CITATION_NOT_LOCATED, RefusalCode.CITATION_AMBIGUOUS}
)

# The skill is the authority; the reference files are what it may consult. Only
# the skill goes into the prompt, because the reference set of one module runs to
# tens of thousands of tokens and the budget is invariant 8's, not a suggestion.
SKILL = "SKILL.md"

_INSTRUCTION = """\
You are executing methodology module {module_id}. The authority for this module
follows, then the evidence you have been delivered. Use no other knowledge.

Return one JSON object and nothing else, with exactly this shape:

{{"claims": [{{"statement": "...", "citations": [
  {{"source_id": "...", "page": 1, "matched_text": "..."}}]}}]}}

Rules that will cause your answer to be refused if broken:
- Every claim carries at least one citation. Uncited claims are discarded.
- `matched_text` must be copied character for character from the evidence below,
  and must be a phrase that appears on one line of it. Do not paraphrase, do not
  join text across a blank line, do not add or remove punctuation.
- `source_id` must be one of the ids given below.
- Use no keys other than those shown.
"""

_QA_INSTRUCTION = """\
You are also this route's QA gate. Beside `claims`, return `qa_status`: exactly
one of "Passed", "Restricted", "Blocked". Only "Passed" releases the modules
that wait on QA.
"""

_GATE_INSTRUCTION = """\
You are also this run's source-readiness gate. Beside `claims`, return
`content_to_module_map`: one object for each module id listed here and no
others.

{module_ids}

Each object has exactly these keys:

{{"module_id": "...", "readiness_status": "READY", "readiness_effect": "..."}}

Rules that will cause your answer to be refused if broken:
- Every module id listed above appears exactly once, and no other id appears.
- `readiness_status` is one of READY, READY_WITH_LIMITATIONS, CONDITIONAL,
  BLOCKED.
- `readiness_effect` says in one sentence what the source set allows or
  prevents for that module.
"""


@dataclass(frozen=True, slots=True)
class ModuleOutcome:
    """What one module execution produced, and what the call cost.

    Two things rather than one because they answer to different rules: the
    envelope is the module's output under invariant 9, and the charge is the
    provider's reported `usage.cost` under invariant 8. The loop needs both and
    they must not be conflated -- a charge folded into the envelope would be a
    figure inside a document the host claims to have derived.
    """

    envelope: Envelope
    charge: Decimal
    model: str
    generation_id: str


@dataclass(frozen=True, slots=True)
class Delivery:
    """One block of evidence handed to a module, and where it came from.

    `page` is part of "where it came from". A module cites the page the prompt
    named, so a delivery that could not say which page it was read from is one
    whose quotes invariant 11 refuses the moment the block is not on page one.
    """

    source_id: UUID
    block_id: str
    page: int
    text: BoundaryText


@dataclass(frozen=True, slots=True)
class UpstreamClaim:
    """One thing an earlier module established, and the quotes under it.

    Plain `str`, not `BoundaryText`: this is transient prompt context that is
    never persisted, and the text was already validated at the boundary once,
    when the upstream module's own claim was stored.
    """

    statement: str
    quotes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Upstream:
    """What one direct predecessor accepted, as the host stored it."""

    module_id: str
    claims: tuple[UpstreamClaim, ...]


@dataclass(frozen=True, slots=True)
class Assignment:
    """What the host hands one module for one node of one run.

    Identity only. What the module reads -- the evidence, the gate's
    expectation and its predecessors' results -- is derived from the run's pins
    inside the authority unit (`_context`), so no caller's copy of it survives.
    """

    module_id: str
    run_id: UUID
    node: RouteNode
    route: ResolvedRoute
    # The reserved attempt this call is made under.
    attempt_id: UUID


@dataclass(frozen=True, slots=True)
class _Context:
    """What this node reads, as the host derived it from the pins."""

    delivered: list[Delivery]
    gate_expects: frozenset[str]
    upstream: tuple[Upstream, ...]
    # Predecessor module -> the accepted artifact read, rechecked after the call.
    digests: dict[str, str]
    # Whether this module is a QA_GATE source, asked for its clearance.
    qa: bool


# Every block of the run's pinned source-set version, never the case's live set.
_CAPTURED = (
    "SELECT b.source_id, b.block_id FROM run_inputs i"
    " JOIN source_set_members m"
    " ON (m.case_id, m.version) = (i.case_id, i.source_version)"
    " JOIN source_blocks b ON b.source_id = m.source_id"
    " WHERE i.run_id = %s ORDER BY b.source_id, b.block_id"
)


def _context(
    conn: StoreConnection, blobs: BlobStore, bundle: Bundle, assignment: Assignment
) -> _Context:
    """Evidence through the run-bound reader, and the stored route's upstream.

    Called only after `_stored_identity`, so `assignment.route` is the pin.
    """
    delivered = _delivered(conn, assignment.run_id)
    module_id = assignment.module_id
    gate_expects = (
        frozenset(node.module_id for node in assignment.route.nodes) - {module_id}
        if module_id == GATE_MODULE
        else frozenset()
    )
    digests = _upstream_digests(conn, assignment)
    upstream = tuple(
        Upstream(module, _stored_claims(blobs, bundle, module, digest))
        for module, digest in digests.items()
    )
    qa = any(
        edge.type is EdgeType.QA_GATE and edge.source == module_id
        for edge in assignment.route.edges
    )
    return _Context(delivered, gate_expects, upstream, digests, qa)


def _delivered(conn: StoreConnection, run_id: UUID) -> list[Delivery]:
    """Every captured block of the run, each through the run-bound reader."""
    delivered = []
    for source, block in conn.execute(_CAPTURED, (run_id,)).fetchall():
        source_id = UUID(str(source))
        read = read_run_block(
            conn, run_id=run_id, source_id=source_id, block_id=str(block)
        )
        delivered.append(Delivery(source_id, str(block), read.page, read.text))
    return delivered


def _upstream_digests(conn: StoreConnection, assignment: Assignment) -> dict[str, str]:
    """Each direct predecessor's accepted artifact in this run, in route order.

    A predecessor with no accepted artifact is skipped: a soft edge's source may
    never have run, the same "unmet" a RESTRICTED node already tolerates.
    """
    # One accepted owner per node is a store constraint (migration 0009).
    accepted = artifact_digests(conn, assignment.run_id)
    nodes = {node.module_id: node.route_node_id for node in assignment.route.nodes}
    return {
        module: accepted[nodes[module]]
        for module in predecessors(assignment.route, assignment.module_id)
        if nodes.get(module) in accepted
    }


def _stored_claims(
    blobs: BlobStore, bundle: Bundle, module_id: str, artifact_sha256: str
) -> tuple[UpstreamClaim, ...]:
    """One predecessor's accepted claims, under the identity the pin requires.

    The same codes as `server/qualification/proof.py`: bytes that will not load
    or name another module are unreadable, and an artifact produced under
    another build or authority is `ORCHESTRATION_BUILD_MOVED`. Nothing
    document-derived reaches a refusal.
    """
    try:
        decoded = json.loads(blobs.get(artifact_sha256))
    except (ValueError, Refusal):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE) from None
    if not isinstance(decoded, dict) or decoded.get("module_id") != module_id:
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    expected = authority_digest(assemble_authority(bundle, module_id))
    if (decoded.get("build_id"), decoded.get("authority_digest")) != (
        bundle.build_id,
        expected,
    ):
        raise Refusal(RefusalCode.ORCHESTRATION_BUILD_MOVED)
    claims = decoded.get("claims")
    if not isinstance(claims, list):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    return tuple(_stored_claim(claim) for claim in claims)


def _stored_claim(claim: object) -> UpstreamClaim:
    if not isinstance(claim, dict):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    statement = claim.get("statement")
    citations = claim.get("citations")
    if not isinstance(statement, str) or not isinstance(citations, list):
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
    quotes = []
    for citation in citations:
        quote = citation.get("matched_text") if isinstance(citation, dict) else None
        if not isinstance(quote, str):
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        quotes.append(quote)
    return UpstreamClaim(statement=statement, quotes=tuple(quotes))


def _upstream(upstream: Sequence[Upstream]) -> str:
    """Earlier modules' accepted results, as context.

    Marked as not evidence in the text, and enforced by the rule that was
    already there: a citation names delivered evidence or it does not anchor.
    """
    if not upstream:
        return ""
    sections = []
    for module in upstream:
        lines = [f"module_id: {module.module_id}"]
        for claim in module.claims:
            lines.append(f"- {claim.statement}")
            lines.extend(f"  quoted: {quote}" for quote in claim.quotes)
        sections.append("\n".join(lines))
    return (
        "\n--- UPSTREAM (earlier modules' accepted results: context, not "
        "evidence; cite only the evidence below) ---\n" + "\n\n".join(sections)
    )


def build_prompt(  # noqa: PLR0913 - one prompt, each input keyword-only
    module_id: str,
    authority: bytes,
    delivered: list[Delivery],
    *,
    gate_expects: frozenset[str] = frozenset(),
    upstream: Sequence[Upstream] = (),
    qa: bool = False,
) -> str:
    """The question, the authority, what the chain established, and the
    evidence -- in that order."""
    evidence = "\n\n".join(
        f"source_id: {item.source_id}\npage: {item.page}\n{item.text.value}"
        for item in delivered
    )
    gate = (
        _GATE_INSTRUCTION.format(module_ids=", ".join(sorted(gate_expects)))
        if gate_expects
        else ""
    )
    return (
        _INSTRUCTION.format(module_id=module_id)
        + gate
        + (_QA_INSTRUCTION if qa else "")
        + "\n--- AUTHORITY ---\n"
        + authority.decode("utf-8", errors="replace")
        + _upstream(upstream)
        + "\n--- EVIDENCE ---\n"
        + evidence
    )


def execute_module(
    conn: StoreConnection,
    bundle: Bundle,
    blobs: BlobStore,
    *,
    assignment: Assignment,
    provider: CompletionProvider,
) -> ModuleOutcome:
    """Run one reserved attempt from idle entry, owning bounded read units.

    Supplied run/node identity must match the actual attempt, and the complete
    current input, whole stored route, node and module must match the
    assignment both before the call and again before analysis. The evidence,
    gate expectation and upstream are derived from the pins in the same unit as
    that check, and the upstream read must be unchanged before analysis.
    Billing commits before any analytical refusal and survives later cleanup.

    The order is the contract: authority is verified before the prompt is built,
    the provider is asked once, and every citation is re-derived against the
    token index *before* an envelope exists to be stored. A quote the host
    cannot locate exactly once refuses the claim resting on it -- invariant 11
    happening before the artifact rather than after it -- and the envelope
    counts what it refused. An answer with no claim left is refused (§26).
    """
    with execution_reads(conn):
        check_call(
            conn,
            attempt_id=assignment.attempt_id,
            run_id=assignment.run_id,
            route_node_id=assignment.node.route_node_id,
        )
        _stored_identity(conn, assignment, bundle, adapter=CLAIMS_ADAPTER_VERSION)
        context = _context(conn, blobs, bundle, assignment)
    authority = assemble_authority(bundle, assignment.module_id)
    prompt = build_prompt(
        assignment.module_id,
        authority.files[SKILL],
        context.delivered,
        gate_expects=context.gate_expects,
        upstream=context.upstream,
        qa=context.qa,
    )

    bundle.verify_manifest()
    model = producer_identifier(provider.model, limit=256)
    if model is None:
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    require_idle(conn)
    completion = provider.complete(prompt, json_object=True)
    charge = _reported_charge(
        completion.charge if isinstance(completion.charge, Decimal) else None
    )
    generation = producer_identifier(completion.generation_id, limit=512)
    require_idle(conn)
    record_outcome(
        conn,
        attempt_id=assignment.attempt_id,
        outcome=CallOutcome(charge, model, generation),
    )
    if completion.refusal is not None:
        code = completion.refusal
        if not isinstance(code, RefusalCode):
            code = RefusalCode.PROVIDER_RESPONSE_INVALID
        raise Refusal(code) from None
    if not isinstance(completion.content, str) or charge is None or generation is None:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    with execution_reads(conn):
        check_attempt(
            conn,
            attempt_id=assignment.attempt_id,
            run_id=assignment.run_id,
            route_node_id=assignment.node.route_node_id,
        )
        _stored_identity(conn, assignment, bundle, adapter=CLAIMS_ADAPTER_VERSION)
        if _upstream_digests(conn, assignment) != context.digests:
            raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
        envelope = _envelope(conn, assignment, context, authority, completion.content)
    return ModuleOutcome(
        envelope=envelope,
        charge=charge,
        model=model,
        generation_id=generation,
    )


def _stored_identity(
    conn: StoreConnection, assignment: Assignment, bundle: Bundle, *, adapter: str
) -> None:
    """Current input with the actual Bundle, the exact pinned route/node, and
    the pinned adapter this executor implements (§42.1): a pin never runs
    under the other adapter, whoever calls."""
    pin, stored = execution_input(conn, assignment.run_id, bundle)
    if pin.adapter_version != adapter:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    if (
        stored != assignment.route
        or assignment.node not in stored.nodes
        or assignment.node.module_id != assignment.module_id
    ):
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)


def _envelope(
    conn: StoreConnection,
    assignment: Assignment,
    context: _Context,
    authority: Authority,
    content: str,
) -> Envelope:
    sources = {item.source_id for item in context.delivered}
    # The map first: it is a pure read of the same body, and a map the host
    # cannot bound refuses this answer whatever the claims say. After the loop it
    # was reached only once every quote had been anchored against the token index
    # -- a query per citation spent on an answer already refused.
    readiness = parse_readiness(content, expected=context.gate_expects)
    qa_status = parse_qa(content, expected=context.qa)

    claims = []
    misses: list[RefusalCode] = []
    for statement, citations in parse_claims(content, delivered=sources):
        # Before the quotes: a statement the boundary refuses is the module
        # breaking the contract, which costs the answer rather than the claim.
        text = BoundaryText.of(statement)
        try:
            anchored = verify_citations(conn, delivered=sources, citations=citations)
        except Refusal as missed:
            if missed.code not in QUOTE_MISSES:
                raise
            misses.append(missed.code)
            continue
        claims.append(Claim(statement=text, citations=tuple(anchored)))
    if not claims:
        # Nothing the module established survived. Refused with the first
        # quote's code, as an answer that anchored nothing always was.
        raise Refusal(misses[0])

    return Envelope(
        # The host's, not the module's. Whatever it claimed about its own
        # identity did not survive this line (invariant 3).
        module_id=assignment.module_id,
        build_id=authority.build_id,
        authority_digest=authority_digest(authority),
        claims=tuple(claims),
        readiness=tuple(readiness),
        claims_refused=len(misses),
        qa_status=qa_status,
    )
