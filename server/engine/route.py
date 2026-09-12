"""Route resolution: pure, from typed edges, and pinned once.

`docs/DECISIONS.md` §2 is the reason this module is built before anything that
depends on it. The predecessor resolved routes from `navigation.dependencies` --
97 untyped pairs meant for display -- so 25 OPTIONAL and 22 ADVISORY edges were
enforced as mandatory, the single QA_GATE did not gate, and RESTRICTED could not
occur. Nothing here reads that list; the typed set is `profile["edges"]`.

Three rules carry the phase:

*Blocking and soft.* REQUIRED, CONDITIONAL and QA_GATE block. OPTIONAL and
ADVISORY degrade their target to RESTRICTED -- which **runs**, carrying its
limitation forward -- unless the edge's source module is READY or
READY_WITH_LIMITATIONS, at which point the evidence exists and running without it
would discard what the case has.

*Readiness is read, never passed.* It comes from the accepted CP-0 artifact's
`content_to_module_map` (`docs/DECISIONS.md` §12, adopting CAOS-Final §18). A
caller able to assert readiness could assert its way past the gate that measures
it.

*Resolution is pure.* No I/O, no clock. The resolved route is digested at the
plan gate and execution reads only the pin, so a replay from the same pins takes
the same path (invariant 10).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from json import dumps
from typing import Any

from server.refusals import Refusal, RefusalCode


class EdgeType(StrEnum):
    """The bundle's words, unchanged (CONTEXT.md)."""

    REQUIRED = "REQUIRED"
    CONDITIONAL = "CONDITIONAL"
    QA_GATE = "QA_GATE"
    OPTIONAL = "OPTIONAL"
    ADVISORY = "ADVISORY"


class NodeState(StrEnum):
    """The bundle's four. RESTRICTED runs; it is not "degraded" or "partial"."""

    COMPLETE = "COMPLETE"
    RUNNABLE = "RUNNABLE"
    RESTRICTED = "RESTRICTED"
    BLOCKED = "BLOCKED"


BLOCKING = frozenset({EdgeType.REQUIRED, EdgeType.CONDITIONAL, EdgeType.QA_GATE})
SOFT = frozenset({EdgeType.OPTIONAL, EdgeType.ADVISORY})
# The two CP-0 readiness statuses that mean the evidence is there. The other two
# the schema declares -- CONDITIONAL, BLOCKED -- leave a soft edge soft.
READY = frozenset({"READY", "READY_WITH_LIMITATIONS"})

# The run's source-readiness gate. Named once here because three callers need
# it: the reader below, the runtime's artifact fetch, and the executor's prompt.
GATE_MODULE = "CP-0"

# The host's model extension. `SYSTEM_SPEC.md` §6.2: CP-CF is appended at stage
# 100 with synthesised REQUIRED edges naming every artifact owner it reads, so
# CP-2G completing alone does not release it. No catalog is edited.
MODEL_MODULE = "CP-CF"
MODEL_STAGE = 100
MODEL_OWNERS = ("CP-1", "CP-2G", "CP-4")
RESEARCH_STAGE = 99


@dataclass(frozen=True, slots=True)
class RouteNode:
    """One module's place in one route."""

    route_node_id: str
    module_id: str
    stage: int


@dataclass(frozen=True, slots=True)
class Edge:
    """A typed dependency between two modules of this route."""

    source: str
    target: str
    type: EdgeType


@dataclass(frozen=True, slots=True)
class RouteExtensions:
    """The host-declared additions to a pathway, which travel together.

    `SYSTEM_SPEC.md` section 4 listed these as separate keyword arguments to
    `resolve_route`; corrected in place by `docs/DECISIONS.md` section 21, which
    also says why. They are one thing -- how this route was extended beyond the
    catalog's own node list -- and each is part of the pinned digest.
    """

    research_brief: Mapping[str, Any] | None = None
    model_extension: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedRoute:
    """A closed node list in dependency order, its typed edges, its predicates."""

    profile_id: str
    selection_id: str
    nodes: tuple[RouteNode, ...]
    edges: tuple[Edge, ...]
    predicates: tuple[tuple[str, str], ...] = ()


def resolve_route(
    catalog: Mapping[str, Any],
    profile_id: str,
    selection_id: str,
    *,
    extensions: RouteExtensions | None = None,
    predicates: Mapping[str, str] | None = None,
) -> ResolvedRoute:
    """The pathway's nodes and the typed edges among them. Pure; no I/O.

    `extensions.research_brief` appends CP-DR at stage 99 and
    `extensions.model_extension` appends CP-CF at stage 100, both host-declared
    and neither editing the catalog (`docs/DECISIONS.md` §6).

    An extension naming a module the pathway already runs is refused
    `ROUTE_DUPLICATE_MODULE` by `dependency_order`, rather than appending a
    second node for it. Skipping the append would be the quieter answer and the
    worse one: a caller asking for this pathway *with* a research brief means
    the brief to reach CP-DR, and a route that ignored the extension would say
    nothing about having ignored it.
    """
    extended = extensions or RouteExtensions()
    profile = _profile(catalog, profile_id)
    pathway = _pathway(profile, selection_id)

    nodes = [
        RouteNode(
            route_node_id=str(node["route_node_id"]),
            module_id=str(node["module_id"]),
            stage=int(node["stage"]),
        )
        for node in pathway["nodes"]
    ]
    if extended.research_brief is not None:
        nodes.append(_extension_node(profile_id, selection_id, "CP-DR", RESEARCH_STAGE))
    if extended.model_extension:
        nodes.append(_model_node(profile_id, selection_id, nodes))

    edges = _edges_among(profile, {node.module_id for node in nodes})
    if extended.model_extension:
        edges += tuple(
            Edge(source=owner, target=MODEL_MODULE, type=EdgeType.REQUIRED)
            for owner in MODEL_OWNERS
        )
    return ResolvedRoute(
        profile_id=profile_id,
        selection_id=selection_id,
        nodes=dependency_order(nodes, edges),
        edges=edges,
        predicates=tuple(sorted((predicates or {}).items())),
    )


def dependency_order(
    nodes: Sequence[RouteNode], edges: Sequence[Edge]
) -> tuple[RouteNode, ...]:
    """Nodes ordered so every edge's source precedes its target.

    Ties break on stage then route node id, so the order is a function of the
    route rather than of dictionary iteration -- which is what lets the digest
    mean something.
    """
    # One node per module, checked before anything is keyed by module. Every
    # reader downstream assumes it -- `node_states` builds its complete set from
    # `module_id`, `readiness_from` returns at the first CP-0 node -- and so did
    # the two dicts below, which is what made a second node for one module
    # disappear into a key collision instead of into a refusal. A closed node
    # list (invariant 10) cannot lose a member that way.
    modules = [node.module_id for node in nodes]
    if len(set(modules)) != len(modules):
        raise Refusal(RefusalCode.ROUTE_DUPLICATE_MODULE)

    incoming = {node.module_id: 0 for node in nodes}
    for edge in edges:
        incoming[edge.target] += 1

    remaining = {node.module_id: node for node in nodes}
    ordered: list[RouteNode] = []
    while remaining:
        ready = sorted(
            (node for module_id, node in remaining.items() if not incoming[module_id]),
            key=lambda node: (node.stage, node.route_node_id),
        )
        if not ready:
            # The catalog is a DAG; a cycle means the pin would never resolve.
            raise Refusal(RefusalCode.ROUTE_HAS_A_CYCLE)
        for node in ready:
            ordered.append(node)
            del remaining[node.module_id]
            for edge in edges:
                if edge.source == node.module_id:
                    incoming[edge.target] -= 1
    return tuple(ordered)


def node_states(
    route: ResolvedRoute, accepted: Mapping[str, Any]
) -> dict[str, NodeState]:
    """Each node's state, recomputed from the accepted attempts. Never stored."""
    readiness = readiness_from(route, accepted)
    complete = {
        node.module_id for node in route.nodes if node.route_node_id in accepted
    }

    states = {}
    for node in route.nodes:
        if node.module_id in complete:
            states[node.route_node_id] = NodeState.COMPLETE
            continue
        unmet = _unmet(route, node.module_id, complete)
        states[node.route_node_id] = _state_for(unmet, readiness)
    return states


def frontier(route: ResolvedRoute, accepted: Mapping[str, Any]) -> list[str]:
    """The nodes that may run now: RUNNABLE and RESTRICTED, in route order."""
    states = node_states(route, accepted)
    return [
        node.route_node_id
        for node in route.nodes
        if states[node.route_node_id] in {NodeState.RUNNABLE, NodeState.RESTRICTED}
    ]


def waiting_on(
    route: ResolvedRoute, accepted: Mapping[str, Any], route_node_id: str
) -> tuple[Edge, ...]:
    """Every dependency this node is still waiting for, typed.

    The reason behind a state. A surface reporting BLOCKED with no cause tells a
    reader the run is stuck without telling them what it is stuck on, and the
    types are what separate a node waiting for a module from one waiting for a
    person at the QA gate.

    A node the route does not carry is `ORCHESTRATION_NODE_NOT_IN_ROUTE`. The
    node list is closed (invariant 10), so asking about one outside it is a
    fact about the route rather than an accident -- and the alternative was
    `StopIteration`, which is untyped here and disappears silently if it is
    ever raised inside a generator.
    """
    complete = {
        node.module_id for node in route.nodes if node.route_node_id in accepted
    }
    node = next((n for n in route.nodes if n.route_node_id == route_node_id), None)
    if node is None:
        raise Refusal(RefusalCode.ORCHESTRATION_NODE_NOT_IN_ROUTE)
    return _unmet(route, node.module_id, complete)


def limitations_of(
    route: ResolvedRoute, accepted: Mapping[str, Any], route_node_id: str
) -> tuple[Edge, ...]:
    """The soft edges a RESTRICTED node is running without.

    A node that carries a limitation forward has to be able to say which one:
    "RESTRICTED" on an artifact with no cause attached is not auditable.
    """
    return tuple(
        edge for edge in waiting_on(route, accepted, route_node_id) if edge.type in SOFT
    )


def readiness_from(route: ResolvedRoute, accepted: Mapping[str, Any]) -> dict[str, str]:
    """Per-module readiness, read from the accepted CP-0 artifact and nowhere else."""
    for node in route.nodes:
        if node.module_id != GATE_MODULE:
            continue
        artifact = accepted.get(node.route_node_id)
        if not isinstance(artifact, Mapping):
            return {}
        entries = artifact.get("content_to_module_map", [])
        return {
            str(entry["module_id"]): str(entry["readiness_status"])
            for entry in entries
            if isinstance(entry, Mapping)
        }
    return {}


def route_digest(route: ResolvedRoute) -> str:
    """The digest pinned at the plan gate. A function of the route alone."""
    canonical = dumps(
        {
            "profile_id": route.profile_id,
            "selection_id": route.selection_id,
            "nodes": [
                [node.route_node_id, node.module_id, node.stage] for node in route.nodes
            ],
            "edges": sorted(
                [edge.source, edge.target, edge.type.value] for edge in route.edges
            ),
            "predicates": [list(pair) for pair in route.predicates],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _state_for(unmet: tuple[Edge, ...], readiness: Mapping[str, str]) -> NodeState:
    """The soft-edge rule, in one place."""
    for edge in unmet:
        if edge.type in BLOCKING:
            return NodeState.BLOCKED
        if readiness.get(edge.source) in READY:
            # The evidence this soft edge would have carried exists. Running
            # without it would discard what the case already has.
            return NodeState.BLOCKED
    return NodeState.RESTRICTED if unmet else NodeState.RUNNABLE


def _unmet(
    route: ResolvedRoute, module_id: str, complete: set[str]
) -> tuple[Edge, ...]:
    return tuple(
        edge
        for edge in route.edges
        if edge.target == module_id and edge.source not in complete
    )


def _profile(catalog: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    profiles = catalog.get("profiles")
    if not isinstance(profiles, Mapping) or profile_id not in profiles:
        raise Refusal(RefusalCode.ROUTE_PROFILE_UNKNOWN)
    profile = profiles[profile_id]
    if not isinstance(profile, Mapping):
        raise Refusal(RefusalCode.ROUTE_PROFILE_UNKNOWN)
    return profile


def _pathway(profile: Mapping[str, Any], selection_id: str) -> Mapping[str, Any]:
    pathways = profile.get("pathways")
    if not isinstance(pathways, Mapping) or selection_id not in pathways:
        raise Refusal(RefusalCode.ROUTE_SELECTION_UNKNOWN)
    pathway = pathways[selection_id]
    if not isinstance(pathway, Mapping):
        raise Refusal(RefusalCode.ROUTE_SELECTION_UNKNOWN)
    return pathway


def _edges_among(profile: Mapping[str, Any], modules: set[str]) -> tuple[Edge, ...]:
    """`profile["edges"]`, restricted to this route's nodes. Never
    `navigation.dependencies`, which carries no type at all."""
    return tuple(
        Edge(
            source=str(edge["source"]),
            target=str(edge["target"]),
            type=EdgeType(edge["type"]),
        )
        for edge in profile["edges"]
        if edge["source"] in modules and edge["target"] in modules
    )


def _extension_node(
    profile_id: str, selection_id: str, module_id: str, stage: int
) -> RouteNode:
    return RouteNode(
        route_node_id=f"RN-{profile_id}-{selection_id}-{stage}-{module_id}",
        module_id=module_id,
        stage=stage,
    )


def _model_node(
    profile_id: str, selection_id: str, nodes: Sequence[RouteNode]
) -> RouteNode:
    """CP-CF, refused unless every artifact owner it reads is on the route.

    Refusing here is the point: dropping the edge instead would run CP-CF on
    inputs that are not there, and pinning it would put that into the digest a
    replay is bound to.
    """
    present = {node.module_id for node in nodes}
    if not set(MODEL_OWNERS) <= present:
        raise Refusal(RefusalCode.ROUTE_EXTENSION_OWNER_MISSING)
    return _extension_node(profile_id, selection_id, MODEL_MODULE, MODEL_STAGE)
