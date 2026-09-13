"""Running one canonical module: a conforming Markdown handoff and its record (§41).

The claims executor's unit structure with the canonical adapter's contract. The
attempt, the stored input, the pinned route and node, the pinned adapter and
the host identity are read in one unit before the call and again after it;
the upstream the prompt named must be unchanged. The call is billed before any
analysis, with the Markdown of the answer addressed as the call's diagnostic
whenever the transport yields one (§42.3), so a refused or Blocked handoff
still says what was said. Then the handoff must be the vendor's conforming
Markdown for exactly this invocation, and every citation must anchor in the
delivered evidence: one that does not refuses the whole handoff, since the
Markdown cannot be edited to drop what rests on it (§41.3).
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from server import methodology
from server.blobs import BlobStore
from server.engine.route import ResolvedRoute
from server.evidence.citations import verify_citations
from server.methodology.bundle import (
    Bundle,
    assemble_authority,
    authority_digest,
    verified_bytes,
)
from server.methodology.executor import (
    SKILL,
    Assignment,
    _delivered,
    _stored_identity,
)
from server.methodology.handoff import (
    GATE_MODULE,
    MAX_FILE_BYTES,
    MAX_TRANSPORT_CHARS,
    CanonicalRecord,
    HostIdentity,
    Projections,
    parse_response,
    read_record,
    record_bytes,
    validate_markdown,
)
from server.methodology.invocation import (
    build_handoff_prompt,
    host_identity,
    upstream_markdown,
)
from server.methodology.vendor import (
    VENDOR_MODULE,
    VendorContract,
    load_vendor_contract,
)
from server.provider import CompletionProvider, _reported_charge
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.outcomes import (
    CallOutcome,
    check_attempt,
    check_call,
    execution_reads,
    producer_identifier,
    record_outcome,
    require_idle,
)

_CATALOG = "references/CREDIT_OS_V_MODULE_CATALOG_v2.json"
# One compiled contract per manifest: the manifest digests every vendor file.
_CONTRACTS: dict[str, VendorContract] = {}
_CONTRACTS_LOCK = threading.Lock()


@dataclass(frozen=True, slots=True)
class HandoffOutcome:
    """The accepted Markdown, the host record beside it, and the call's facts."""

    markdown: bytes
    record: bytes
    charge: Decimal
    model: str
    generation_id: str
    # What `record_outcome` stored as the call's diagnostic Markdown address.
    diagnostic_sha256: str | None


def _contract(bundle: Bundle) -> VendorContract:
    key = bundle.manifest_sha256
    with _CONTRACTS_LOCK:
        if key not in _CONTRACTS:
            _CONTRACTS[key] = load_vendor_contract(bundle)
        return _CONTRACTS[key]


def _catalog(bundle: Bundle) -> dict[str, Any]:
    try:
        catalog = json.loads(verified_bytes(bundle, VENDOR_MODULE, _CATALOG))
    except ValueError:
        catalog = None
    if not isinstance(catalog, dict):
        raise Refusal(RefusalCode.AUTHORITY_BYTES_MISMATCH)
    return catalog


def _diagnostic(blobs: BlobStore, content: object) -> str | None:
    """The answer's Markdown as a blob address, or None when there is none.

    Lenient on purpose: this is what was said, not what is accepted. A blob
    that cannot be written is also None, because the bill must still commit.
    The bytes are untrusted provider text, never `BoundaryText`: no reader may
    render them or read them as analysis.
    """
    text = None
    if isinstance(content, str) and len(content) <= MAX_TRANSPORT_CHARS:
        with suppress(ValueError, RecursionError):
            wire = json.loads(content)
            text = wire.get("canonical_markdown") if isinstance(wire, dict) else None
    markdown = None
    if isinstance(text, str):
        with suppress(UnicodeEncodeError):
            markdown = text.encode("utf-8")
    if markdown is None or len(markdown) > MAX_FILE_BYTES:
        return None
    with suppress(OSError, Refusal):
        return blobs.put(markdown)
    return None


def execute_handoff(
    conn: StoreConnection,
    bundle: Bundle,
    blobs: BlobStore,
    *,
    assignment: Assignment,
    provider: CompletionProvider,
) -> HandoffOutcome:
    """Run one reserved attempt of a canonical pin from idle entry.

    Refuses `RUN_INPUT_INVALID` for a pin of any other adapter before the call.
    Billing, with the diagnostic address, commits before any analytical
    refusal. A validated `qa_status: Blocked` refuses `HANDOFF_BLOCKED` only
    once the host identity has held and every citation has anchored.
    """
    adapter = methodology.CANONICAL_ADAPTER_VERSION
    attempt, route_node_id = assignment.attempt_id, assignment.node.route_node_id
    with execution_reads(conn):
        check_call(
            conn,
            attempt_id=attempt,
            run_id=assignment.run_id,
            route_node_id=route_node_id,
        )
        _stored_identity(conn, assignment, bundle, adapter=adapter)
        identity = _identity(conn, bundle, assignment)
        delivered = _delivered(conn, assignment.run_id)
        upstream = upstream_markdown(blobs, identity.upstream)
    contract = _contract(bundle)
    authority = assemble_authority(bundle, assignment.module_id)
    prompt = build_handoff_prompt(
        contract,
        identity=identity,
        skill=authority.files[SKILL],
        delivered=delivered,
        upstream=upstream,
        route=assignment.route,
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
    content = completion.content if completion.refusal is None else None
    diagnostic = _diagnostic(blobs, content)
    require_idle(conn)
    record_outcome(
        conn,
        attempt_id=attempt,
        outcome=CallOutcome(charge, model, generation, diagnostic),
    )
    if completion.refusal is not None:
        code = completion.refusal
        if not isinstance(code, RefusalCode):
            code = RefusalCode.PROVIDER_RESPONSE_INVALID
        raise Refusal(code) from None
    if not isinstance(content, str) or charge is None or generation is None:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)

    catalog = _catalog(bundle)
    sources = {item.source_id for item in delivered}
    gate_expects = _gate_expects(assignment.route, assignment.module_id)
    with execution_reads(conn):
        check_attempt(
            conn,
            attempt_id=attempt,
            run_id=assignment.run_id,
            route_node_id=route_node_id,
        )
        _stored_identity(conn, assignment, bundle, adapter=adapter)
        # The identity carries every accepted upstream digest, so this one
        # comparison also catches an upstream rewritten during the call.
        if _identity(conn, bundle, assignment) != identity:
            raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
        markdown, citations = parse_response(content, delivered=frozenset(sources))
        projections = _unless_blocked(
            lambda: validate_markdown(
                contract,
                catalog,
                authority.files[SKILL],
                markdown,
                identity=identity,
                gate_expects=gate_expects,
            )
        )
        # A Blocked verdict ends the run only once its quotes are verified: an
        # unanchorable Blocked handoff is an ordinary refusal (c-5b, P3-2).
        anchored = verify_citations(conn, delivered=sources, citations=citations)
        if projections is None:
            raise Refusal(RefusalCode.HANDOFF_BLOCKED)
    record = CanonicalRecord(
        artifact_sha256=hashlib.sha256(markdown).hexdigest(),
        adapter_version=adapter,
        build_id=authority.build_id,
        manifest_sha256=bundle.manifest_sha256,
        authority_bundle_sha256=identity.authority_bundle_sha256,
        authority_digest=authority_digest(authority),
        identity=identity,
        projections=projections,
        citations=tuple(anchored),
    )
    return HandoffOutcome(
        markdown=markdown,
        record=record_bytes(record),
        charge=charge,
        model=model,
        generation_id=generation,
        diagnostic_sha256=diagnostic,
    )


def _unless_blocked(validate: Callable[[], Projections]) -> Projections | None:
    """The projections, or None for a validated Blocked handoff."""
    try:
        return validate()
    except Refusal as refusal:
        if refusal.code is not RefusalCode.HANDOFF_BLOCKED:
            raise
    return None


def accepted_projections(  # noqa: PLR0913 -- one accepted row, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    route: ResolvedRoute,
    *,
    run_id: UUID,
    route_node_id: str,
    attempt_id: UUID,
    artifact_sha256: str,
    record_sha256: str,
) -> Projections:
    """An accepted canonical artifact's projections, re-derived and compared.

    Inside the caller's read unit: the host identity is rebuilt from the stored
    facts, the record must bind this Markdown and that identity, and the
    projections re-parsed from the Markdown must equal the record's (§42.4).
    Citations are not re-anchored here; the proof and freezing do that.
    """
    node = next((n for n in route.nodes if n.route_node_id == route_node_id), None)
    if node is None:
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    identity = host_identity(
        conn, bundle, run_id=run_id, route=route, node=node, attempt_id=attempt_id
    )
    record = read_record(
        blobs,
        artifact_sha256=artifact_sha256,
        record_sha256=record_sha256,
        expected=identity,
    )
    try:
        markdown = blobs.get(artifact_sha256)
    except (Refusal, OSError):
        markdown = None
    if markdown is None:
        raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
    authority = assemble_authority(bundle, node.module_id)
    projections = validate_markdown(
        _contract(bundle),
        _catalog(bundle),
        authority.files[SKILL],
        markdown,
        identity=identity,
        gate_expects=_gate_expects(route, node.module_id),
    )
    if projections != record.projections:
        raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
    return projections


def _gate_expects(route: ResolvedRoute, module_id: str) -> frozenset[str]:
    if module_id != GATE_MODULE:
        return frozenset()
    return frozenset(n.module_id for n in route.nodes) - {GATE_MODULE}


def _identity(
    conn: StoreConnection, bundle: Bundle, assignment: Assignment
) -> HostIdentity:
    return host_identity(
        conn,
        bundle,
        run_id=assignment.run_id,
        route=assignment.route,
        node=assignment.node,
        attempt_id=assignment.attempt_id,
    )
