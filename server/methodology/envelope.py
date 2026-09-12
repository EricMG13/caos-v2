"""The canonical envelope: bounded, closed, and re-derived by the host.

Invariant 9: module output is the strict canonical envelope -- bounded schema,
undeclared fields refused, citations only from delivered evidence. Invariant 3:
provider-claimed identity never survives; whatever a module says about its own
module id, build or digests is an expectation the host re-verifies.

So the envelope a module *returns* and the envelope the host *stores* are two
different objects. The first is untrusted JSON. The second is built here, from
the first's claims plus facts only the host knows: which build was read, what
authority digest it hashed to, and where each quote actually sits in the token
index.

`extra="forbid"` both ways, in the plainest form available: a key the schema does
not declare is a refusal, not a field to ignore. Ignoring it is how a module
starts smuggling state past a reviewer who is reading the declared shape.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from server.boundary_text import BoundaryText
from server.evidence.citations import AnchoredCitation, Citation
from server.refusals import Refusal, RefusalCode

# What a module may return, and nothing else.
CLAIM_KEYS = frozenset({"statement", "citations"})
CITATION_KEYS = frozenset({"source_id", "page", "matched_text"})
ENVELOPE_KEYS = frozenset({"claims"})

# A bound on what one module may assert in one run. Not a performance limit: an
# envelope with a thousand claims is a module that has stopped answering the
# question and started narrating, and every claim costs a citation anchor.
MAX_CLAIMS = 50


@dataclass(frozen=True, slots=True)
class Claim:
    """One statement a module made, and the evidence it rests on."""

    statement: BoundaryText
    citations: tuple[AnchoredCitation, ...]


@dataclass(frozen=True, slots=True)
class Envelope:
    """What the host stores. Identity is the host's, never the module's."""

    module_id: str
    build_id: str
    authority_digest: str
    claims: tuple[Claim, ...]
    # The claims refused because a quote did not anchor (docs/DECISIONS.md §26),
    # kept beside the ones that survived so the artifact says the module
    # asserted more than it established.
    claims_refused: int


def parse_claims(
    body: str, *, delivered: set[UUID]
) -> list[tuple[str, list[Citation]]]:
    """Read a module's JSON into claims and citation requests, or refuse.

    Nothing here trusts a value. The shape is checked key by key, every declared
    source is checked against what this node was actually delivered, and any
    undeclared key refuses the whole envelope rather than being dropped.
    """
    decoded = _object(body)
    _closed(decoded, ENVELOPE_KEYS)

    claims = decoded.get("claims")
    if not isinstance(claims, list) or not claims:
        raise Refusal(RefusalCode.ENVELOPE_INVALID)
    if len(claims) > MAX_CLAIMS:
        raise Refusal(RefusalCode.ENVELOPE_INVALID)

    return [_claim(claim, delivered) for claim in claims]


def _claim(claim: object, delivered: set[UUID]) -> tuple[str, list[Citation]]:
    if not isinstance(claim, dict):
        raise Refusal(RefusalCode.ENVELOPE_INVALID)
    _closed(claim, CLAIM_KEYS)

    statement = claim.get("statement")
    citations = claim.get("citations")
    if not isinstance(statement, str) or not statement.strip():
        raise Refusal(RefusalCode.ENVELOPE_INVALID)
    if not isinstance(citations, list) or not citations:
        # A claim with no citation is an assertion, and this system does not
        # store assertions (invariant 9: citations only from delivered evidence).
        raise Refusal(RefusalCode.ENVELOPE_UNCITED_CLAIM)

    return statement, [_citation(citation, delivered) for citation in citations]


def _citation(citation: object, delivered: set[UUID]) -> Citation:
    if not isinstance(citation, dict):
        raise Refusal(RefusalCode.ENVELOPE_INVALID)
    _closed(citation, CITATION_KEYS)

    try:
        source_id = UUID(str(citation["source_id"]))
        page = int(citation["page"])
    except (KeyError, ValueError, TypeError):
        raise Refusal(RefusalCode.ENVELOPE_INVALID) from None

    matched_text = citation.get("matched_text")
    if not isinstance(matched_text, str) or not matched_text.strip():
        raise Refusal(RefusalCode.ENVELOPE_INVALID)
    if source_id not in delivered:
        raise Refusal(RefusalCode.CITATION_NOT_DELIVERED)

    return Citation(source_id=source_id, page=page, matched_text=matched_text)


def _object(body: str) -> dict[str, Any]:
    try:
        decoded = json.loads(body)
    except ValueError:
        # The body is a completion and a completion echoes the prompt, so the
        # parse error is dropped rather than reported.
        raise Refusal(RefusalCode.ENVELOPE_INVALID) from None
    if not isinstance(decoded, dict):
        raise Refusal(RefusalCode.ENVELOPE_INVALID)
    return decoded


def _closed(mapping: dict[str, Any], allowed: frozenset[str]) -> None:
    """`extra="forbid"`. An undeclared key refuses the envelope.

    Dropping it instead is how a module starts carrying state past a reviewer
    who is reading the declared shape and seeing nothing unusual.
    """
    if set(mapping) - allowed:
        raise Refusal(RefusalCode.ENVELOPE_UNDECLARED_FIELD)
