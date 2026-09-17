"""Running one canonical module: a conforming Markdown handoff and its record (§41).

One pre-call read unit and one post-call read unit around the call. The
attempt, the stored input, the pinned route and node, the pinned adapter and
the host identity are read in one unit before the call and again after it;
the upstream the prompt named must be unchanged. The call is billed before any
analysis, with the exact response body addressed as the call's diagnostic
(§42.3), so a refused or Blocked handoff still says what was said -- and after
a crash the answer is accepted, blocked or explained from it, never paid for
again (`replay_billed`, brief 4.3 D7).
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
from enum import StrEnum
from typing import Any
from uuid import UUID

from server import methodology
from server.blobs import BlobStore
from server.engine.route import ResolvedRoute, RouteNode
from server.evidence.citations import (
    AnchoredCitation,
    verify_citations,
)
from server.methodology.bundle import (
    Bundle,
    DeliveredAuthority,
    assemble_authority,
    authority_digest,
    delivered_authority,
    delivered_authority_digest,
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
    LineageRef,
    Projections,
    UpstreamRef,
    parse_response,
    read_record,
    record_bytes,
    stored_lineage,
    validate_markdown,
)
from server.methodology.invocation import (
    accepted_lineage,
    build_handoff_prompt,
    call_time_identity,
    host_identity,
    prospective_identity,
    record_authority_matches,
    request_size,
    upstream_markdown,
)
from server.methodology.vendor import (
    VENDOR_MODULE,
    VendorContract,
    load_vendor_contract,
)
from server.provider import CompletionProvider, reported_charge
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserved_for
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
from server.store.run_inputs import load_run_input
from server.store.source_sets import SourceSet, load_source_set

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

    The whole closed transport, not only its Markdown, so `replay_billed` can
    re-run the complete verdict -- citations included -- from stored facts.
    Lenient on purpose: this is what was said, not what is accepted. A blob
    that cannot be written leaves the address None so the bill still commits,
    and the attempt then refuses as a store fault: a verdict that was never
    stored cannot be honoured on recovery, so it must not be silently lost.
    The bytes are untrusted provider text, never `BoundaryText`: no reader may
    render them, and only `replay_billed`'s full re-validation reads them.
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


def _within_reservation(
    conn: StoreConnection,
    provider: CompletionProvider,
    prompt: str,
    *,
    attempt_id: UUID,
) -> None:
    """Refuse a request this attempt's reservation does not cover (Task 8.2).

    The loop priced the prompt `check_context` built and reserved for it; this
    unit builds its own under the attempt's own identity. A rebuilt prompt that
    is larger -- or a configured price that moved between the two -- would
    otherwise be sent under a reservation too small for it, which is invariant
    8's "no provider call without a reservation" met only in form. So the
    reservation is read back with the price it was taken under and the request
    about to be sent is priced against exactly that price, before the call.

    A missing reservation refuses here as well as in `check_call`: the unit that
    spends checks it, not only the unit that ordered it.
    """
    from server.pricing import priced_request

    measured = request_size(provider, prompt)
    with execution_reads(conn):
        taken = reserved_for(conn, attempt_id)
    if taken is None:
        raise Refusal(RefusalCode.BUDGET_NOT_RESERVED)
    if taken.price.model != provider.model:
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    if priced_request(taken.price, measured) > taken.amount:
        raise Refusal(RefusalCode.CONTEXT_OVER_CEILING)


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
            lease=assignment.lease,
        )
        _stored_identity(conn, assignment, bundle, adapter=adapter)
        identity = _identity(conn, bundle, assignment)
        context = _context(conn, blobs, bundle, assignment, identity)
    # The record binds exactly the authority this prompt carries (§45.1).
    carried = delivered_authority(bundle, assignment.module_id)
    # Met before reservation by `check_context`; built again here so the call
    # carries exactly this attempt's identity, and refused again if it moved.
    prompt = _prompt(bundle, assignment, identity, context, carried)
    _within_reservation(conn, provider, prompt, attempt_id=attempt)

    bundle.verify_manifest()
    model = producer_identifier(provider.model, limit=256)
    if model is None:
        raise Refusal(RefusalCode.PROVIDER_NOT_CONFIGURED)
    require_idle(conn)
    completion = provider.complete(prompt, json_object=True)
    charge = reported_charge(
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

    with execution_reads(conn):
        check_attempt(
            conn,
            attempt_id=attempt,
            run_id=assignment.run_id,
            route_node_id=route_node_id,
        )
        _stored_identity(conn, assignment, bundle, adapter=adapter)
        markdown, record = _answer(
            conn,
            bundle,
            blobs,
            assignment,
            identity=identity,
            context=context,
            carried=carried,
            content=content,
        )
    return HandoffOutcome(
        markdown=markdown,
        record=record,
        charge=charge,
        model=model,
        generation_id=generation,
        diagnostic_sha256=diagnostic,
    )


def _answer(  # noqa: PLR0913 -- one recorded answer, keyword-only
    conn: StoreConnection,
    bundle: Bundle,
    blobs: BlobStore,
    assignment: Assignment,
    *,
    identity: HostIdentity,
    context: _Context,
    carried: DeliveredAuthority,
    content: str,
) -> tuple[bytes, bytes]:
    """The one post-call verdict on a recorded answer: its Markdown and record.

    Inside the caller's read unit, after it checked the attempt and the stored
    pin; the live call and `replay_billed` both decide here, so they cannot
    drift. `identity` is what the call was asked under. Refuses
    `HANDOFF_BLOCKED` for a validated Blocked handoff whose quotes anchored.
    """
    # The identity carries every accepted upstream digest, so this one
    # comparison also catches an upstream rewritten during the call.
    if _identity(conn, bundle, assignment) != identity:
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    if context.source_set is not None:
        _assert_originals(blobs, context.source_set)
    # ...and every ancestor's accepted pair, a record rewritten included.
    if _lineage_moved(conn, assignment.run_id, context.lineage):
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    # Exactly what the prompt was built from: pins are immutable, so the
    # pre-call reading is this unit's too, without a second query.
    blocks = _by_source(context.delivered)
    markdown, citations = parse_response(content, delivered=frozenset(blocks))
    authority = assemble_authority(bundle, assignment.module_id)
    projections = _unless_blocked(
        lambda: validate_markdown(
            _contract(bundle),
            _catalog(bundle),
            authority.files[SKILL],
            markdown,
            identity=identity,
            gate_expects=_gate_expects(assignment.route, assignment.module_id),
        )
    )
    # A Blocked verdict ends the run only once its quotes are verified: an
    # unanchorable Blocked handoff is an ordinary refusal (c-5b, P3-2).
    anchored = verify_citations(conn, delivered=blocks, citations=citations)
    if projections is None:
        raise Refusal(RefusalCode.HANDOFF_BLOCKED)
    _forecast_inputs(bundle, assignment.module_id, markdown, context)
    record = CanonicalRecord(
        artifact_sha256=hashlib.sha256(markdown).hexdigest(),
        adapter_version=methodology.CANONICAL_ADAPTER_VERSION,
        build_id=authority.build_id,
        manifest_sha256=bundle.manifest_sha256,
        authority_bundle_sha256=identity.authority_bundle_sha256,
        authority_digest=authority_digest(authority),
        delivered_authority_digest=delivered_authority_digest(carried),
        identity=identity,
        lineage=context.lineage,
        projections=projections,
        citations=tuple(anchored),
    )
    return markdown, record_bytes(record)


def check_context(  # noqa: PLR0913 -- one node of one run, keyword-only
    conn: StoreConnection,
    bundle: Bundle,
    blobs: BlobStore,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    node: RouteNode,
    provider: CompletionProvider,
) -> int:
    """Build the node's whole prompt before any attempt, reservation or call,
    and return the request size the call will be priced on.

    The pre-call unit `execute_handoff` runs, under `prospective_identity`, so
    every refusal the prompt would raise -- `CONTEXT_OVER_CEILING` on the whole
    request `provider` would send, and a delivered file whose bytes moved -- is
    raised while nothing has been started or set aside (§45.3, invariant 8).
    The prompt itself is not kept: the attempt's own is rebuilt from its own
    read unit, and the reservation this measurement produced is what that
    rebuild is then checked against (Task 8.2).
    """
    assignment = Assignment(node.module_id, run_id, node, route, _NO_ATTEMPT)
    with execution_reads(conn):
        _stored_identity(
            conn, assignment, bundle, adapter=methodology.CANONICAL_ADAPTER_VERSION
        )
        identity = prospective_identity(
            conn, bundle, run_id=run_id, route=route, node=node
        )
        context = _context(conn, blobs, bundle, assignment, identity)
    authority = delivered_authority(bundle, node.module_id)
    return request_size(
        provider, _prompt(bundle, assignment, identity, context, authority)
    )


# `check_context` runs before an attempt exists; nothing it reads uses the id.
_NO_ATTEMPT = UUID(int=0)


@dataclass(frozen=True, slots=True)
class _Context:
    """What one prompt is built from, each part read in one pre-call unit."""

    delivered: list[Delivery]
    upstream: tuple[tuple[UpstreamRef, bytes], ...]
    lineage: tuple[LineageRef, ...]
    # Each direct upstream's anchored citations, from its verified record.
    citations: dict[str, tuple[AnchoredCitation, ...]]
    source_set: SourceSet | None


def _source_preparation(
    conn: StoreConnection,
    blobs: BlobStore,
    assignment: Assignment,
    delivered: Sequence[Delivery],
) -> SourceSet | None:
    """CP-0 alone receives the verified source snapshot it must prepare."""
    if assignment.module_id != GATE_MODULE:
        return None
    pin = load_run_input(conn, assignment.run_id)
    if pin is None:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    source_set = load_source_set(conn, pin.case_id, pin.source_version)
    if source_set is None or source_set.fingerprint != pin.source_fingerprint:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    if {member.source_id for member in source_set.members} != {
        item.source_id for item in delivered
    }:
        raise Refusal(RefusalCode.EVIDENCE_NOT_AVAILABLE)
    _assert_originals(blobs, source_set)
    return source_set


def _assert_originals(blobs: BlobStore, source_set: SourceSet) -> None:
    """Keep original-blob failures typed and free of filesystem context."""
    refusal: RefusalCode | None = None
    for member in source_set.members:
        try:
            blobs.get(member.document_sha256)
        except OSError:
            refusal = RefusalCode.STORE_UNAVAILABLE
            break
        except Refusal as caught:
            refusal = caught.code
            break
    if refusal is not None:
        raise Refusal(refusal)


def _context(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    assignment: Assignment,
    identity: HostIdentity,
) -> _Context:
    """The delivered evidence, the verified upstream, its whole accepted lineage
    and its citation register, read inside the caller's unit after it checked
    the stored pin. Only accepted rows reach any part: a Blocked or refused
    attempt's diagnostic body is never read here."""
    delivered = _delivered(conn, assignment.run_id)
    source_set = _source_preparation(conn, blobs, assignment, delivered)
    # Records first: what binds and re-validates is then read as context.
    records, lineage = _upstream_records(
        conn, blobs, bundle, assignment, identity.upstream
    )
    return _Context(
        delivered=delivered,
        upstream=upstream_markdown(blobs, identity.upstream),
        lineage=lineage,
        citations={node: record.citations for node, record in records.items()},
        source_set=source_set,
    )


def _lineage_moved(
    conn: StoreConnection, run_id: UUID, lineage: tuple[LineageRef, ...]
) -> bool:
    """Whether any ancestor's accepted (artifact, record) pair is no longer the
    one the prompt's lineage named. One query, none without lineage."""
    if not lineage:
        return False
    accepted = {row[0]: (row[2], row[3]) for row in accepted_rows(conn, run_id)}
    return any(
        accepted.get(link.route_node_id) != (link.artifact_sha256, link.record_sha256)
        for link in lineage
    )


def _prompt(
    bundle: Bundle,
    assignment: Assignment,
    identity: HostIdentity,
    context: _Context,
    authority: DeliveredAuthority,
) -> str:
    """The prompt over exactly the delivered authority (§45.1): names from the
    manifest and the verified SKILL.md, never from evidence or upstream text."""
    return build_handoff_prompt(
        _contract(bundle),
        identity=identity,
        authority=authority,
        catalog=_catalog(bundle),
        delivered=context.delivered,
        upstream=context.upstream,
        upstream_citations=context.citations,
        route=assignment.route,
        source_set=context.source_set,
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
    {
        RefusalCode.BLOB_ADDRESS_INVALID,
        RefusalCode.BLOB_DIGEST_MISMATCH,
        RefusalCode.BLOB_NOT_FOUND,
        RefusalCode.STORE_UNAVAILABLE,
        RefusalCode.STORE_NOT_TRANSACTIONAL,
    }
)


class Verdict(StrEnum):
    """What a billed answer's stored body re-derives to (brief 4.3 D7)."""

    ANSWERED = "ANSWERED"
    BLOCKED = "BLOCKED"
    REFUSED = "REFUSED"


@dataclass(frozen=True, slots=True)
class Replayed:
    """One billed, unaccepted, unexplained attempt and its re-derived verdict:
    the outcome to accept when ANSWERED, the refusal's code when REFUSED."""

    attempt_id: UUID
    verdict: Verdict
    outcome: HandoffOutcome | None = None
    code: RefusalCode | None = None


def unexplained_charge(
    conn: StoreConnection,
    *,
    run_id: UUID,
    route_node_ids: Sequence[str],
) -> str | None:
    """A ready node already paid for whose answer was never stored.

    `_diagnostic` can fail to write its body after `record_outcome` has already
    committed the charge: the bytes are gone, and `replay_billed` cannot settle
    the attempt because it requires a diagnostic to read. Left alone the next
    pass starts a fresh attempt, reserves again and calls the provider again,
    so one node is billed twice with nobody deciding that it should be. The
    run ceiling bounds it; nothing else does.

    Returns the first such node, for a caller that refuses rather than spends.
    Paying again may well be the right answer -- but it is an operator's to
    give, which is what parking the run with a code asks for.
    """
    row = conn.execute(
        "SELECT t.route_node_id FROM call_outcomes o JOIN run_attempts t"
        " USING (attempt_id) JOIN budget_ledger l"
        " ON (l.run_id, l.attempt_id) = (o.run_id, o.charged_attempt_id)"
        " WHERE t.run_id = %s AND t.route_node_id = ANY(%s)"
        " AND o.diagnostic_sha256 IS NULL"
        " AND NOT EXISTS (SELECT 1 FROM artifacts a WHERE a.attempt_id = o.attempt_id)"
        " AND NOT EXISTS"
        " (SELECT 1 FROM attempt_refusals r WHERE r.attempt_id = o.attempt_id)"
        " ORDER BY t.ordinal, t.route_node_id LIMIT 1",
        (run_id, list(route_node_ids)),
    ).fetchone()
    return None if row is None else str(row[0])


def replay_billed(  # noqa: PLR0913 -- one run's nodes, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    route_node_ids: Collection[str],
) -> Replayed | None:
    """The first billed answer of these nodes still owed a verdict, re-derived.

    Inside the caller's read unit, so the live path and crash recovery decide
    alike and a recorded answer is never paid for twice: an attempt with a known
    charge, generation and stored body, no artifact and no `attempt_refusals`
    row, in ordinal order. Its attempt and stored pin are checked as the live
    post-call unit checks them, and those refusals -- about the run, not the
    answer -- raise. The answer is then judged by `_answer` under the identity
    its call could have named (`call_time_identity`), which must still be
    `host_identity` now: a soft input accepted after the attempt started makes
    it REFUSED `ROUTE_IDENTITY_INVALID`. A store fault always raises, never a
    verdict. One query when nothing is owed.
    """
    rows = conn.execute(
        "SELECT t.route_node_id, o.attempt_id, o.diagnostic_sha256, l.amount,"
        " o.model, o.generation_id"
        " FROM call_outcomes o JOIN run_attempts t USING (attempt_id)"
        " JOIN budget_ledger l"
        " ON (l.run_id, l.attempt_id) = (o.run_id, o.charged_attempt_id)"
        " WHERE t.run_id = %s AND t.route_node_id = ANY(%s)"
        " AND o.generation_id IS NOT NULL AND o.model IS NOT NULL"
        " AND o.diagnostic_sha256 IS NOT NULL"
        " AND NOT EXISTS (SELECT 1 FROM artifacts a WHERE a.attempt_id = o.attempt_id)"
        " AND NOT EXISTS"
        " (SELECT 1 FROM attempt_refusals r WHERE r.attempt_id = o.attempt_id)"
        " ORDER BY t.ordinal, t.route_node_id",
        (run_id, list(route_node_ids)),
    ).fetchall()
    nodes = {node.route_node_id: node for node in route.nodes}
    for route_node_id, attempt, diagnostic, charge, model, generation in rows:
        node = nodes.get(str(route_node_id))
        if node is None:
            continue
        attempt_id = UUID(str(attempt))
        body = _stored_body(blobs, str(diagnostic))
        assignment = Assignment(node.module_id, run_id, node, route, attempt_id)
        check_attempt(
            conn,
            attempt_id=attempt_id,
            run_id=run_id,
            route_node_id=node.route_node_id,
        )
        _stored_identity(
            conn, assignment, bundle, adapter=methodology.CANONICAL_ADAPTER_VERSION
        )
        try:
            markdown, record = _replayed_answer(conn, blobs, bundle, assignment, body)
        except Refusal as refusal:
            if refusal.code in _STORE_FAULTS:
                raise
            code = refusal.code
        else:
            outcome = HandoffOutcome(
                markdown, record, charge, str(model), str(generation), str(diagnostic)
            )
            return Replayed(attempt_id, Verdict.ANSWERED, outcome=outcome)
        if code is RefusalCode.HANDOFF_BLOCKED:
            return Replayed(attempt_id, Verdict.BLOCKED)
        return Replayed(attempt_id, Verdict.REFUSED, code=code)
    return None


def blocked_verdict(  # noqa: PLR0913 -- one run's nodes, keyword-only
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    route_node_ids: Collection[str],
) -> UUID | None:
    """The attempt whose answer, the first `replay_billed` owes a verdict on,
    re-derives to Blocked; None when that answer is anything else, or there is
    none. The attempt rather than a bool, because the transition that acts on
    the verdict records which answer it was (`block_run`, §68)."""
    replayed = replay_billed(
        conn, blobs, bundle, run_id=run_id, route=route, route_node_ids=route_node_ids
    )
    if replayed is None or replayed.verdict is not Verdict.BLOCKED:
        return None
    return replayed.attempt_id


def _stored_body(blobs: BlobStore, diagnostic_sha256: str) -> str | None:
    """A billed attempt's stored body. A blob that will not read is a store
    fault, never a verdict: reading it as a refusal would pay again."""
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


def _replayed_answer(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    assignment: Assignment,
    body: str | None,
) -> tuple[bytes, bytes]:
    """`_answer` over a stored body, with the context its call was built from."""
    if body is None:
        raise Refusal(RefusalCode.PROVIDER_RESPONSE_INVALID)
    # An unaccepted attempt has no record, so its call named its blocking
    # inputs and the soft ones accepted before it started; `_answer` refuses
    # the attempt when that is no longer every input accepted now.
    identity = call_time_identity(
        conn,
        assignment.route,
        _identity(conn, bundle, assignment),
        attempt_id=assignment.attempt_id,
        record=None,
    )
    return _answer(
        conn,
        bundle,
        blobs,
        assignment,
        identity=identity,
        context=_context(conn, blobs, bundle, assignment, identity),
        carried=delivered_authority(bundle, assignment.module_id),
        content=body,
    )


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
    accepted: Mapping[str, tuple[str, str | None]] | None = None,
) -> Projections:
    """An accepted canonical artifact's projections, re-derived and compared.

    Inside the caller's read unit: the host identity is rebuilt from the stored
    facts, the record must bind this Markdown and that identity, and the
    projections re-parsed from the Markdown must equal the record's (§42.4).
    Citations are not re-anchored here; the proof and freezing do that.
    `accepted` is the unit's accepted pairs when the caller holds them.

    The identity is `call_time_identity`, the one rule the proof and the
    deliverable use too, so a soft input accepted after its target never makes
    the runtime refuse a record the other readers accept.
    """
    _record, projections = _verified_accepted(
        conn,
        blobs,
        bundle,
        route,
        run_id=run_id,
        route_node_id=route_node_id,
        attempt_id=attempt_id,
        artifact_sha256=artifact_sha256,
        record_sha256=record_sha256,
        accepted=accepted,
    )
    return projections


def accepted_handoff(  # noqa: PLR0913 -- one accepted row, keyword-only
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
    accepted: Mapping[str, tuple[str, str | None]] | None = None,
) -> tuple[bytes, CanonicalRecord]:
    """An accepted canonical artifact's exact Markdown and its verified record.

    The checks `accepted_projections` makes, inside the caller's read unit:
    the record binds this Markdown, the identity rebuilt from the store, this
    build and the accepted lineage, and the projections re-derived from the
    Markdown equal the record's (§42.4). Citations are not re-anchored; the
    rectangles are the ones recorded at acceptance.
    """
    record, _projections = _verified_accepted(
        conn,
        blobs,
        bundle,
        route,
        run_id=run_id,
        route_node_id=route_node_id,
        attempt_id=attempt_id,
        artifact_sha256=artifact_sha256,
        record_sha256=record_sha256,
        accepted=accepted,
    )
    # The bytes just validated, read again digest-checked for the caller.
    return blobs.get(artifact_sha256), record


def _verified_accepted(  # noqa: PLR0913 -- one accepted row, keyword-only
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
    accepted: Mapping[str, tuple[str, str | None]] | None,
) -> tuple[CanonicalRecord, Projections]:
    """`accepted_projections` with the verified record it read beside them."""
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
        accepted=accepted,
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
    if node.module_id == "CP-CF":
        assignment = Assignment(node.module_id, run_id, node, route, attempt_id)
        _forecast_inputs(
            bundle,
            node.module_id,
            markdown,
            _context(conn, blobs, bundle, assignment, identity),
        )
    return record, projections


def _forecast_inputs(
    bundle: Bundle, module: str, markdown: bytes, context: _Context
) -> None:
    """The same owner-binding check at acceptance, replay and every accepted read."""
    if module != "CP-CF":
        return
    from server.methodology.forecast import (
        validate_driver_mapping,
        validate_forecast_bindings,
    )

    upstream = {ref.module_id: data for ref, data in context.upstream}
    citations = {
        ref.module_id: context.citations[ref.route_node_id]
        for ref, _data in context.upstream
    }
    validate_forecast_bindings(markdown, upstream, citations)
    validate_driver_mapping(_contract(bundle), markdown, upstream["CP-2G"])
    parse = _contract(bundle).validate_handoff.validate_text
    fields = parse(markdown.decode()).fields
    for data in upstream.values():
        owner = parse(data.decode()).fields
        if (
            owner["qa_status"] == "Restricted" and fields["qa_status"] != "Restricted"
        ) or any(
            not set(owner[key]) <= set(fields[key])
            for key in ("limitation_flags", "validation_warnings")
        ):
            raise Refusal(RefusalCode.HANDOFF_INCOMPLETE)


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
    accepted: Mapping[str, tuple[str, str | None]] | None,
) -> CanonicalRecord:
    """An accepted row's record, bound to its call-time identity and this build.

    `ARTIFACT_RECORD_MISMATCH` when it does not bind (`read_record`) or its
    lineage is not the accepted chain the store holds now (§45.4);
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
    upstream = record.identity.upstream
    if record.lineage != accepted_lineage(
        conn, blobs, run_id=run_id, upstream=upstream, accepted=accepted
    ):
        raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
    return record


def _upstream_records(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    assignment: Assignment,
    refs: tuple[UpstreamRef, ...],
) -> tuple[dict[str, CanonicalRecord], tuple[LineageRef, ...]]:
    """Every upstream the prompt will carry is an accepted record of this build
    whose projections re-derive from its Markdown and whose own lineage is the
    accepted chain; returns those records by route node and the whole lineage
    behind them, read from those records.

    Inside the pre-call read unit, so nothing another build wrote, and no record
    that disagrees with its own Markdown, reaches the prompt (invariant 4; the
    same checks the frontier and the proof apply). A row whose digest is not the
    ref's is `ROUTE_IDENTITY_INVALID`; a row without a record, or whose Markdown
    will not read, `ARTIFACT_RECORD_MISMATCH`.
    One `accepted_rows` query for the whole unit, none when there is no
    upstream; each upstream record is read once, by its own verification, and
    that verified record is what the lineage is read from.
    """
    if not refs:
        return {}, ()
    rows = {row[0]: row for row in accepted_rows(conn, assignment.run_id)}
    accepted = {row[0]: (row[2], row[3]) for row in rows.values()}
    nodes = {n.route_node_id: n for n in assignment.route.nodes}
    verified: dict[str, CanonicalRecord] = {}
    by_node: dict[str, CanonicalRecord] = {}
    for ref in refs:
        row = rows.get(ref.route_node_id)
        if row is None or row[2] != ref.sha256 or ref.route_node_id not in nodes:
            raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
        _, attempt, digest, record_sha256 = row
        if record_sha256 is None:
            raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        record, _projections = _verified_accepted(
            conn,
            blobs,
            bundle,
            assignment.route,
            run_id=assignment.run_id,
            route_node_id=ref.route_node_id,
            attempt_id=attempt,
            artifact_sha256=digest,
            record_sha256=record_sha256,
            accepted=accepted,
        )
        verified[record_sha256] = by_node[ref.route_node_id] = record
    return by_node, stored_lineage(blobs, refs, accepted, verified=verified)


def _gate_expects(route: ResolvedRoute, module_id: str) -> frozenset[str]:
    if module_id != GATE_MODULE:
        return frozenset()
    # The vendor T8 cannot name host modules; CP-CF is released by its four
    # REQUIRED owner/gate edges, after these exact vendor readiness rows.
    return frozenset(n.module_id for n in route.nodes) - {GATE_MODULE, "CP-CF"}


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
