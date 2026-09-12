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

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from server.boundary_text import BoundaryText
from server.evidence.citations import verify_citations
from server.evidence.read import Block, read_block
from server.methodology.bundle import Bundle, assemble_authority, authority_digest
from server.methodology.envelope import Claim, Envelope, parse_claims, parse_readiness
from server.provider import CompletionProvider
from server.store import StoreConnection

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
class Assignment:
    """What the host hands one module for one node of one run."""

    module_id: str
    delivered: list[Delivery]
    # The modules this one must return a readiness verdict for: the pinned
    # route less itself when it is the gate, and empty for everyone else.
    gate_expects: frozenset[str] = frozenset()


def deliver(
    conn: StoreConnection, deliveries: list[tuple[UUID, str]]
) -> list[Delivery]:
    """Read the blocks this node is to receive, through the evidence boundary.

    Through the evidence boundary rather than around it: withdrawal is checked
    live at every use (invariant 1), and a delivery assembled by a different
    query would be the one path that skipped the check.
    """
    return [
        _delivery(
            source_id,
            block_id,
            read_block(conn, source_id=source_id, block_id=block_id),
        )
        for source_id, block_id in deliveries
    ]


def _delivery(source_id: UUID, block_id: str, block: Block) -> Delivery:
    return Delivery(
        source_id=source_id, block_id=block_id, page=block.page, text=block.text
    )


def build_prompt(
    module_id: str,
    authority: bytes,
    delivered: list[Delivery],
    *,
    gate_expects: frozenset[str] = frozenset(),
) -> str:
    """The question, the authority, and the evidence -- in that order."""
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
        + "\n--- AUTHORITY ---\n"
        + authority.decode("utf-8", errors="replace")
        + "\n--- EVIDENCE ---\n"
        + evidence
    )


def execute_module(
    conn: StoreConnection,
    bundle: Bundle,
    *,
    assignment: Assignment,
    provider: CompletionProvider,
) -> ModuleOutcome:
    """Run one module and return the envelope the host is willing to store.

    The order is the contract: authority is verified before the prompt is built,
    the provider is asked once, and every citation is re-derived against the
    token index *before* an envelope exists to be stored. A quote the host
    cannot locate exactly once refuses the whole envelope, which is invariant 11
    happening before the artifact rather than after it.

    `assignment` carries the module id, the delivered evidence and the gate
    expectation as one thing rather than three loose arguments, for the same
    reason `Execution` and `Accepted` (`docs/DECISIONS.md` §25) are one thing
    each: a module id with no evidence answers nothing, evidence with no module
    id has no authority to be read against, and the gate expectation is a fact
    about *this* module-and-run pair, not a fourth independent input. Deciding
    what that expectation is belongs to the caller that holds the route
    (`ModuleProvider.execute`) -- this function only reads it off the
    assignment it was handed.
    """
    authority = assemble_authority(bundle, assignment.module_id)
    prompt = build_prompt(
        assignment.module_id,
        authority.files[SKILL],
        assignment.delivered,
        gate_expects=assignment.gate_expects,
    )

    completion = provider.complete(prompt, json_object=True)

    sources = {item.source_id for item in assignment.delivered}
    claims = []
    for statement, citations in parse_claims(completion.content, delivered=sources):
        anchored = verify_citations(conn, delivered=sources, citations=citations)
        claims.append(
            Claim(statement=BoundaryText.of(statement), citations=tuple(anchored))
        )

    readiness = parse_readiness(completion.content, expected=assignment.gate_expects)

    envelope = Envelope(
        # The host's, not the module's. Whatever it claimed about its own
        # identity did not survive this line (invariant 3).
        module_id=assignment.module_id,
        build_id=authority.build_id,
        authority_digest=authority_digest(authority),
        claims=tuple(claims),
        readiness=tuple(readiness),
    )
    return ModuleOutcome(
        envelope=envelope,
        charge=completion.charge,
        # What the host asked, and what the provider called the call. The first
        # is a fact the host holds, the second is the provider's own handle and
        # is kept for reconciling a bill rather than for trusting.
        model=provider.model,
        generation_id=completion.generation_id,
    )
