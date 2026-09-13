"""One canonical invocation: the host identity from the store, then its prompt (§41).

`host_identity` reads every host-owned fact from what the store pinned -- the
run input's subject and vendor run id, the attempt's stored ordinal, the pinned
route and the accepted upstream artifacts -- so no caller's copy of an identity
survives (invariant 3). `build_handoff_prompt` hands the module those exact
front-matter lines to copy, the exact upstream Markdown as context, and every
delivered block as evidence; it refuses an oversized request rather than cut
anything out of it.

The claims-JSON path in `executor.py` is untouched; slice c-5a wires this in.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from server import methodology
from server.blobs import BlobStore
from server.engine.route import BLOCKING, ResolvedRoute, RouteNode
from server.engine.runtime import artifact_digests
from server.methodology.bundle import Bundle, verified_bytes
from server.methodology.executor import Delivery
from server.methodology.handoff import (
    ADAPTER_MODULES,
    GATE_MODULE,
    HostIdentity,
    UpstreamRef,
    expected_filename,
    invocation_fields,
)
from server.methodology.vendor import (
    VENDOR_MODULE,
    VendorContract,
    authority_bundle_sha256,
)
from server.provider import MAX_REQUEST_BYTES
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import resolved_route
from server.store.run_inputs import load_run_input
from server.store.runs import attempt_ordinal

_CATALOG = "references/CREDIT_OS_V_MODULE_CATALOG_v2.json"


def host_identity(  # noqa: PLR0913 -- the brief's keyword-only identity inputs
    conn: StoreConnection,
    bundle: Bundle,
    *,
    run_id: UUID,
    route: ResolvedRoute,
    node: RouteNode,
    attempt_id: UUID,
) -> HostIdentity:
    """This attempt's host identity, read inside the caller's transaction.

    Refuses `RUN_INPUT_INVALID` for a pin that is not canonical (format 2 with a
    subject) or was taken under another bundle build; `ROUTE_IDENTITY_INVALID`
    when the caller's route or node is not the pin, or a blocking upstream has
    no accepted artifact; `ATTEMPT_NOT_FOUND` for an attempt of another run or
    node. `module_name` is not pinned on `RouteNode`, so it is read from the
    verified bundle catalog the pin's build names.
    """
    pin = load_run_input(conn, run_id)
    if (
        pin is None
        or pin.subject is None
        or pin.cos_run_id is None
        or pin.adapter_version != methodology.CANONICAL_ADAPTER_VERSION
        or (pin.build_id, pin.manifest_sha256)
        != (bundle.build_id, bundle.manifest_sha256)
    ):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    stored = resolved_route(conn, run_id)
    if stored is None or stored != route or node not in stored.nodes:
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    if node.module_id not in ADAPTER_MODULES:
        raise Refusal(RefusalCode.HANDOFF_MODULE_UNSUPPORTED)
    owner = conn.execute(
        "SELECT run_id, route_node_id FROM run_attempts WHERE attempt_id = %s",
        (attempt_id,),
    ).fetchone()
    if owner != (run_id, node.route_node_id):
        raise Refusal(RefusalCode.ATTEMPT_NOT_FOUND)
    subject = pin.subject
    return HostIdentity(
        run_id=pin.cos_run_id,
        profile_id=stored.profile_id,
        selection_id=stored.selection_id,
        route_node_id=node.route_node_id,
        module_id=node.module_id,
        module_name=_module_name(bundle, stored, node),
        issuer_id=subject.issuer_id,
        issuer_name=subject.issuer_name,
        reporting_period=subject.reporting_period,
        analysis_date=subject.analysis_date,
        ordinal=attempt_ordinal(conn, attempt_id),
        authority_bundle_sha256=authority_bundle_sha256(bundle),
        upstream=_upstream(
            stored,
            node,
            artifact_digests(conn, run_id),
            run_id=pin.cos_run_id,
            period=subject.reporting_period,
        ),
    )


def _module_name(bundle: Bundle, route: ResolvedRoute, node: RouteNode) -> str:
    try:
        catalog = json.loads(verified_bytes(bundle, VENDOR_MODULE, _CATALOG))
        pathway = catalog["profiles"][route.profile_id]["pathways"]
        nodes = pathway[route.selection_id]["nodes"]
        names = [
            entry["module_name"]
            for entry in nodes
            if entry["route_node_id"] == node.route_node_id
            and entry["module_id"] == node.module_id
        ]
    except (ValueError, KeyError, TypeError):
        names = []
    if len(names) != 1 or not isinstance(names[0], str) or not names[0]:
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    return names[0]


def _upstream(
    route: ResolvedRoute,
    node: RouteNode,
    accepted: Mapping[str, str],
    *,
    run_id: str,
    period: str,
) -> tuple[UpstreamRef, ...]:
    """Every accepted direct input; a missing blocking one refuses.

    The vendor's `routing.expected_upstream_digests` without its predicates and
    readiness: a CONDITIONAL edge blocks unconditionally here (the host
    evaluates no predicate), and a soft edge whose source has not been accepted
    is omitted, as the vendor omits it.
    """
    by_module = {n.module_id: n for n in route.nodes}
    refs: dict[str, UpstreamRef] = {}
    for edge in route.edges:
        if edge.target != node.module_id:
            continue
        source = by_module.get(edge.source)
        digest = None if source is None else accepted.get(source.route_node_id)
        if source is None or digest is None:
            if edge.type in BLOCKING:
                raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
            continue
        refs[source.route_node_id] = UpstreamRef(
            route_node_id=source.route_node_id,
            module_id=source.module_id,
            run_id=run_id,
            period=period,
            sha256=digest,
        )
    return tuple(refs[key] for key in sorted(refs))


def upstream_markdown(
    blobs: BlobStore, refs: Sequence[UpstreamRef]
) -> tuple[tuple[UpstreamRef, bytes], ...]:
    """Each accepted upstream handoff's exact Markdown, proven by its digest."""

    def read(ref: UpstreamRef) -> bytes:
        try:
            return blobs.get(ref.sha256)
        except (Refusal, OSError):
            pass
        raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)

    return tuple((ref, read(ref)) for ref in refs)


_INSTRUCTION = """\
You are executing methodology module {module_id} ({module_name}) at route node
{route_node_id}. The authority for this module follows, then the accepted
upstream handoffs, then the evidence you have been delivered. Use no other
knowledge.

Return one JSON object and nothing else, with exactly this shape:

{{"canonical_markdown": "...", "citations": [
  {{"source_id": "...", "page": 1, "matched_text": "..."}}]}}

Rules that will cause your answer to be refused if broken:
- `canonical_markdown` is the complete canonical Markdown handoff the
  authority's output contract specifies: YAML front matter between two `---`
  lines, then the canonical headings and every register. Its file name is
  {filename}.
- The front matter carries the host-owned lines below exactly as given,
  character for character and quotes included: change, reorder or drop none of
  them. Add the fields the authority asks you to author after them.
- Every citation's `matched_text` is whole words copied character for character
  from one line of the evidence below, and the same words appear verbatim in the
  Markdown body after the front matter.
- Give at least one citation. `source_id` is one of the ids given below, and
  `page` is the page given with it.
- Use no keys other than those shown.
"""

_GATE_INSTRUCTION = """\
You are this run's source-readiness gate.
Register T8 lists exactly these modules, each once, and no others: {module_ids}
"""


def _yaml(fields: Mapping[str, Any]) -> str:
    """The front matter as the vendor's restricted YAML, every scalar JSON-quoted."""
    lines = []
    for key, value in fields.items():
        if isinstance(value, list) and value:
            lines.append(f"{key}:")
            for item in value:
                for n, (name, scalar) in enumerate(item.items()):
                    marker = "  - " if n == 0 else "    "
                    lines.append(f"{marker}{name}: {json.dumps(scalar)}")
        else:
            lines.append(f"{key}: {json.dumps(value)}")
    return "\n".join(lines)


def _upstream_section(upstream: Sequence[tuple[UpstreamRef, bytes]]) -> str:
    if not upstream:
        return ""
    sections = []
    for ref, data in upstream:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        if text is None or hashlib.sha256(data).hexdigest() != ref.sha256:
            raise Refusal(RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE)
        sections.append(
            f"module_id: {ref.module_id}\nroute_node_id: {ref.route_node_id}\n"
            f"sha256: {ref.sha256}\n{text}"
        )
    return (
        "\n--- UPSTREAM (accepted handoffs, exact bytes: context, not evidence; "
        "cite only the evidence below) ---\n" + "\n\n".join(sections)
    )


def build_handoff_prompt(  # noqa: PLR0913 -- one prompt, each input keyword-only
    contract: VendorContract,
    *,
    identity: HostIdentity,
    skill: bytes,
    delivered: Sequence[Delivery],
    upstream: Sequence[tuple[UpstreamRef, bytes]],
    gate_expects: frozenset[str],
) -> str:
    """The task, the host-owned front matter, the authority, upstream, evidence.

    `upstream` must be exactly `identity.upstream` with bytes that hash to each
    ref, or the prompt would show the module other context than its front
    matter names. A prompt over `MAX_REQUEST_BYTES` refuses
    `PROVIDER_CALL_INVALID`, the provider's own code for it; nothing is cut.
    """
    if identity.module_id not in ADAPTER_MODULES:
        raise Refusal(RefusalCode.HANDOFF_MODULE_UNSUPPORTED)
    if tuple(ref for ref, _ in upstream) != identity.upstream or (
        bool(gate_expects) != (identity.module_id == GATE_MODULE)
    ):
        raise Refusal(RefusalCode.ROUTE_IDENTITY_INVALID)
    try:
        authority = skill.decode("utf-8")
    except UnicodeDecodeError:
        authority = None
    if authority is None:
        raise Refusal(RefusalCode.AUTHORITY_BYTES_MISMATCH)
    gate = (
        _GATE_INSTRUCTION.format(module_ids=", ".join(sorted(gate_expects)))
        if gate_expects
        else ""
    )
    evidence = "\n\n".join(
        f"source_id: {item.source_id}\npage: {item.page}\n{item.text.value}"
        for item in delivered
    )
    prompt = (
        _INSTRUCTION.format(
            module_id=identity.module_id,
            module_name=identity.module_name,
            route_node_id=identity.route_node_id,
            filename=expected_filename(identity),
        )
        + gate
        + "\n--- HOST-OWNED FRONT MATTER (copy exactly) ---\n"
        + _yaml(invocation_fields(contract, identity))
        + "\n--- END HOST-OWNED FRONT MATTER ---\n"
        + "\n--- AUTHORITY ---\n"
        + authority
        + _upstream_section(upstream)
        + "\n--- EVIDENCE ---\n"
        + evidence
    )
    if len(prompt.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise Refusal(RefusalCode.PROVIDER_CALL_INVALID)
    return prompt
