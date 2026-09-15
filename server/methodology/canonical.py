"""Running one canonical module: a conforming Markdown handoff and its record (§41).

The claims executor's unit structure with the canonical adapter's contract. The
attempt, the stored input, the pinned route and node, the pinned adapter and
the host identity are read in one unit before the call and again after it;
the upstream the prompt named must be unchanged. The call is billed before any
analysis, with the exact response body addressed as the call's diagnostic
(§42.3), so a refused or Blocked handoff still says what was said -- and a
Blocked verdict can be re-derived from it after a crash (`blocked_verdict`).
Then the handoff must be the vendor's conforming Markdown for exactly this
invocation, and every citation must anchor in the delivered evidence: one that
does not refuses the whole handoff, since the Markdown cannot be edited to drop
what rests on it (§41.3).
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable, Collection, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from server import methodology
from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, RouteNode
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
    Delivery,
    _delivered,
    _stored_identity,
)
from server.methodology.handoff import (
    GATE_MODULE,
    MAX_TRANSPORT_CHARS,
    CanonicalRecord,
    HostIdentity,
    Projections,
    UpstreamRef,
    parse_response,
    read_record,
    record_bytes,
    validate_markdown,
)
from server.methodology.invocation import (
    build_handoff_prompt,
    call_time_identity,
    host_identity,
    record_authority_matches,
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
    accepted_rows,
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
    # What `record_outcome` stored as the call's diagnostic body address.
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


def _diagnostic(blobs: BlobStore, content: object) -> tuple[str | None, bool]:
    """The exact response body as a blob address (None when there is none), and
    whether a body that exists could not be stored.

    The whole closed transport, not only its Markdown, so `blocked_verdict` can
    re-run the complete verdict -- citations included -- from stored facts.
    Lenient on purpose: this is what was said, not what is accepted. A blob
    that cannot be written leaves the address None so the bill still commits,
    and the attempt then refuses as a store fault: a verdict that was never
    stored cannot be honoured on recovery, so it must not be silently lost.
    The bytes are untrusted provider text, never `BoundaryText`: no reader may
    render them, and only `blocked_verdict`'s full re-validation reads them.
    """
    if not isinstance(content, str) or len(content) > MAX_TRANSPORT_CHARS:
        return None, False
    try:
        data = content.encode("utf-8")
    except UnicodeEncodeError:
        return None, False  # a lone surrogate: no body the host could store
    with suppress(OSError, Refusal):
        return blobs.put(data), False
    return None, True


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
        # Records first: what binds and re-validates is then read as context.
        _upstream_records(conn, blobs, bundle, assignment, identity.upstream)
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
    diagnostic, unstored = _diagnostic(blobs, content)
    require_idle(conn)
    record_outcome(
        conn,
        attempt_id=attempt,
        outcome=CallOutcome(charge, model, generation, diagnostic),
    )
    if unstored:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE)
    if completion.refusal is not None:
        code = completion.refusal
        if not isinstance(code, RefusalCode):
            code = RefusalCode.PROVIDER_RESPONSE_INVALID
        raise Refusal(code) from None
    if not isinstance(content, str) or charge is None or generation is None:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)

    catalog = _catalog(bundle)
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
        # Exactly what the prompt was built from: pins are immutable, so the
        # pre-call reading is this unit's too, without a second query.
        blocks = _by_source(delivered)
        markdown, citations = parse_response(content, delivered=frozenset(blocks))
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
        anchored = verify_citations(conn, delivered=blocks, citations=citations)
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


def _by_source(delivered: Sequence[Delivery]) -> dict[UUID, frozenset[str]]:
    """Source to the block ids a node was handed, from its deliveries."""
    blocks: dict[UUID, set[str]] = {}
    for delivery in delivered:
        blocks.setdefault(delivery.source_id, set()).add(delivery.block_id)
    return {source: frozenset(ids) for source, ids in blocks.items()}


def _unless_blocked(validate: Callable[[], Projections]) -> Projections | None:
    """The projections, or None for a validated Blocked handoff."""
    try:
        return validate()
    except Refusal as refusal:
        if refusal.code is not RefusalCode.HANDOFF_BLOCKED:
            raise
    return None


# Refusals that say the store, not the answer, failed: never read as a verdict.
_STORE_FAULTS = frozenset(
    {RefusalCode.STORE_UNAVAILABLE, RefusalCode.STORE_NOT_TRANSACTIONAL}
)


def blocked_verdict(  # noqa: PLR0913 -- one run's nodes, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    route_node_ids: Collection[str],
) -> bool:
    """Whether a billed attempt of one of these nodes answered a validated Blocked.

    Brief correction 6 re-derived from committed facts, inside the caller's read
    unit, so the live path and crash recovery decide alike: an unaccepted
    attempt with a known charge and generation whose stored response body
    re-validates -- identity rebuilt for that attempt, vendor validation, every
    citation anchored -- to `HANDOFF_BLOCKED`. Any other refusal means that
    attempt was an ordinary refusal. One query when nothing was billed.
    """
    rows = conn.execute(
        "SELECT t.route_node_id, o.attempt_id, o.diagnostic_sha256"
        " FROM call_outcomes o JOIN run_attempts t USING (attempt_id)"
        " WHERE t.run_id = %s AND t.route_node_id = ANY(%s)"
        " AND o.charged_attempt_id IS NOT NULL AND o.generation_id IS NOT NULL"
        " AND o.diagnostic_sha256 IS NOT NULL AND NOT EXISTS"
        " (SELECT 1 FROM artifacts a WHERE a.attempt_id = o.attempt_id)"
        " ORDER BY t.route_node_id, t.ordinal",
        (run_id, list(route_node_ids)),
    ).fetchall()
    nodes = {node.route_node_id: node for node in route.nodes}
    blocks: dict[UUID, frozenset[str]] | None = None
    for route_node_id, attempt, diagnostic in rows:
        node = nodes.get(str(route_node_id))
        if node is None:
            continue
        body = _stored_body(blobs, str(diagnostic))
        if blocks is None:
            # Once per call: every captured block, whatever the attempts.
            try:
                blocks = _by_source(_delivered(conn, run_id))
            except Refusal as refusal:
                if refusal.code in _STORE_FAULTS:
                    raise
                return False  # e.g. a withdrawn source: no verdict can be re-derived
        if body is not None and _answered_blocked(
            conn,
            bundle,
            route,
            node,
            run_id=run_id,
            attempt_id=UUID(str(attempt)),
            body=body,
            blocks=blocks,
        ):
            return True
    return False


def _stored_body(blobs: BlobStore, diagnostic_sha256: str) -> str | None:
    """A billed attempt's stored body. A blob that will not read is a store
    fault, never "not blocked": reading it as an answer would pay again."""
    try:
        data = blobs.get(diagnostic_sha256)
    except (OSError, Refusal):
        data = None
    if data is None:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _answered_blocked(  # noqa: PLR0913 -- one stored attempt, keyword-only
    conn: StoreConnection,
    bundle: Bundle,
    route: ResolvedRoute,
    node: RouteNode,
    *,
    run_id: UUID,
    attempt_id: UUID,
    body: str,
    blocks: Mapping[UUID, frozenset[str]],
) -> bool:
    try:
        # The call-time identity every reader shares: an unaccepted attempt has
        # no record, so it names its blocking inputs and those accepted before.
        identity = call_time_identity(
            conn,
            route,
            host_identity(
                conn,
                bundle,
                run_id=run_id,
                route=route,
                node=node,
                attempt_id=attempt_id,
            ),
            attempt_id=attempt_id,
            record=None,
        )
        markdown, citations = parse_response(body, delivered=frozenset(blocks))
        authority = assemble_authority(bundle, node.module_id)
        projections = _unless_blocked(
            lambda: validate_markdown(
                _contract(bundle),
                _catalog(bundle),
                authority.files[SKILL],
                markdown,
                identity=identity,
                gate_expects=_gate_expects(route, node.module_id),
            )
        )
        if projections is not None:
            return False
        # Anchored before Blocked is honoured, exactly as on the live path.
        verify_citations(conn, delivered=blocks, citations=citations)
    except Refusal as refusal:
        if refusal.code in _STORE_FAULTS:
            raise
        return False
    return True


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

    The identity is `call_time_identity`, the one rule the proof and the
    deliverable use too, so a soft input accepted after its target never makes
    the runtime refuse a record the other readers accept.
    """
    node = next((n for n in route.nodes if n.route_node_id == route_node_id), None)
    if node is None:
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    record = _accepted_record(
        conn,
        blobs,
        bundle,
        route,
        node,
        run_id=run_id,
        attempt_id=attempt_id,
        artifact_sha256=artifact_sha256,
        record_sha256=record_sha256,
    )
    identity = record.identity
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


def _accepted_record(  # noqa: PLR0913 -- one accepted row, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    route: ResolvedRoute,
    node: RouteNode,
    *,
    run_id: UUID,
    attempt_id: UUID,
    artifact_sha256: str,
    record_sha256: str,
) -> CanonicalRecord:
    """An accepted row's record, bound to its call-time identity and this build.

    `ARTIFACT_RECORD_MISMATCH` when it does not bind (`read_record`);
    `ORCHESTRATION_BUILD_MOVED` when it was written under another adapter,
    build, manifest or authority, as the proof maps it. Caller owns the read.
    """
    try:
        stored = blobs.get(record_sha256)
    except (Refusal, OSError):
        stored = None
    identity = call_time_identity(
        conn,
        route,
        host_identity(
            conn, bundle, run_id=run_id, route=route, node=node, attempt_id=attempt_id
        ),
        attempt_id=attempt_id,
        record=stored,
    )
    record = read_record(
        blobs,
        artifact_sha256=artifact_sha256,
        record_sha256=record_sha256,
        expected=identity,
    )
    if not record_authority_matches(record, bundle=bundle, module_id=node.module_id):
        raise Refusal(RefusalCode.ORCHESTRATION_BUILD_MOVED)
    return record


def _upstream_records(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    assignment: Assignment,
    refs: tuple[UpstreamRef, ...],
) -> None:
    """Every upstream the prompt will carry is an accepted record of this build
    whose projections re-derive from its Markdown.

    Inside the pre-call read unit, so nothing another build wrote, and no record
    that disagrees with its own Markdown, reaches the prompt (invariant 4; the
    same checks the frontier and the proof apply). A row whose digest is not the
    ref's is `ROUTE_IDENTITY_INVALID`; a row without a record, or whose Markdown
    will not read, `ARTIFACT_RECORD_MISMATCH`.
    No query when there is no upstream.
    """
    if not refs:
        return
    rows = {row[0]: row for row in accepted_rows(conn, assignment.run_id)}
    nodes = {n.route_node_id: n for n in assignment.route.nodes}
    for ref in refs:
        row = rows.get(ref.route_node_id)
        if row is None or row[2] != ref.sha256 or ref.route_node_id not in nodes:
            raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
        _, attempt, digest, record = row
        if record is None:
            raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        accepted_projections(
            conn,
            blobs,
            bundle,
            assignment.route,
            run_id=assignment.run_id,
            route_node_id=ref.route_node_id,
            attempt_id=attempt,
            artifact_sha256=digest,
            record_sha256=record,
        )


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
