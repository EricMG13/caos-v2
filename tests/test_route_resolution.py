"""Phase 3 exit tests: the phase the predecessor got wrong.

`docs/DECISIONS.md` §2 records what it got wrong and how it was measured. Route
resolution read `navigation.dependencies` -- 97 untyped pairs meant for display --
instead of `profile["edges"]`. The consequences were exact: 25 OPTIONAL and 22
ADVISORY edges were enforced as mandatory, the single QA_GATE did not gate, and
RESTRICTED could not occur at all.

Every test here reads the vendored catalog rather than a fixture, so the numbers
are the build's own (`tests/test_bundle_pin.py` pins them). The soft-edge rule is
the one worth stating twice: OPTIONAL and ADVISORY degrade a target to RESTRICTED
-- which runs and carries its limitation forward -- unless the edge's source
module is READY or READY_WITH_LIMITATIONS in the accepted CP-0 artifact, at which
point the evidence exists and the edge blocks.

Readiness is read from that artifact and never passed in (`docs/DECISIONS.md`
§12, adopting CAOS-Final §18): a caller that could assert readiness could assert
its way past the gate that exists to measure it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.engine.route import (
    Edge,
    EdgeType,
    NodeState,
    ResolvedRoute,
    RouteExtensions,
    RouteNode,
    dependency_order,
    frontier,
    limitations_of,
    node_states,
    readiness_from,
    resolve_route,
    route_digest,
)
from server.refusals import Refusal, RefusalCode

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"
READY = ("READY", "READY_WITH_LIMITATIONS")


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    """The vendored build's own catalog, not a fixture standing in for it."""
    loaded: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return loaded


def _cp0_artifact(**readiness: str) -> dict[str, Any]:
    """A CP-0 artifact carrying a readiness status per module, in the shape the
    bundle's own payload schema declares (`content_to_module_map`)."""
    return {
        "content_to_module_map": [
            {"module_id": module_id, "readiness_status": status}
            for module_id, status in readiness.items()
        ]
    }


def _accept(
    route: ResolvedRoute, *module_ids: str, cp0: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Accepted artifacts keyed by route node, CP-0's carrying the readiness."""
    wanted = set(module_ids)
    accepted = {}
    for node in route.nodes:
        if node.module_id == "CP-0" and ("CP-0" in wanted or cp0 is not None):
            accepted[node.route_node_id] = cp0 if cp0 is not None else _cp0_artifact()
        elif node.module_id in wanted:
            accepted[node.route_node_id] = {}
    return accepted


def _node_id(route: ResolvedRoute, module_id: str) -> str:
    return next(n.route_node_id for n in route.nodes if n.module_id == module_id)


def _state(route: ResolvedRoute, accepted: dict[str, Any], module_id: str) -> NodeState:
    return node_states(route, accepted)[_node_id(route, module_id)]


def test_the_typed_edges_are_read_not_the_untyped_display_list(
    catalog: dict[str, Any],
) -> None:
    """The predecessor's defect, stated as a test. `navigation.dependencies`
    carries no type, so a route built from it cannot tell REQUIRED from
    ADVISORY -- which is how 47 soft edges became mandatory."""
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")

    assert {edge.type for edge in route.edges} & {
        EdgeType.OPTIONAL,
        EdgeType.ADVISORY,
    }, "a resolved route carries soft edges; the untyped list cannot express them"


def test_optional_edge_does_not_block(catalog: dict[str, Any]) -> None:
    """CP-1A -> CP-2 is OPTIONAL. With CP-1A unaccepted and not READY, CP-2 is
    RESTRICTED: it runs and carries the limitation, rather than waiting."""
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    accepted = _accept(route, "CP-0", "CP-1", cp0=_cp0_artifact(**{"CP-1A": "BLOCKED"}))

    assert _state(route, accepted, "CP-2") is NodeState.RESTRICTED
    assert _node_id(route, "CP-2") in frontier(route, accepted)


def test_optional_edge_blocks_when_source_ready(catalog: dict[str, Any]) -> None:
    """The same edge, the other way. CP-0 says the evidence CP-1A needs is
    READY, so running CP-2 without it would discard evidence the case has."""
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    accepted = _accept(route, "CP-0", "CP-1", cp0=_cp0_artifact(**{"CP-1A": "READY"}))

    assert _state(route, accepted, "CP-2") is NodeState.BLOCKED
    assert _node_id(route, "CP-2") not in frontier(route, accepted)


@pytest.mark.parametrize("status", READY)
def test_both_ready_statuses_harden_a_soft_edge(
    catalog: dict[str, Any], status: str
) -> None:
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    accepted = _accept(route, "CP-0", "CP-1", cp0=_cp0_artifact(**{"CP-1A": status}))

    assert _state(route, accepted, "CP-2") is NodeState.BLOCKED


def test_qa_gate_blocks_cp6_until_cp5_accepted(catalog: dict[str, Any]) -> None:
    """The one QA_GATE in this build, CP-5 -> CP-6. Under the predecessor it did
    not gate, because the untyped list it read had no QA_GATE in it."""
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    everything_but_cp5 = [
        node.module_id for node in route.nodes if node.module_id not in {"CP-5", "CP-6"}
    ]
    accepted = _accept(route, *everything_but_cp5, cp0=_cp0_artifact())

    assert _state(route, accepted, "CP-6") is NodeState.BLOCKED

    accepted[_node_id(route, "CP-5")] = {}
    assert _state(route, accepted, "CP-6") is NodeState.RUNNABLE


def test_restricted_node_runs_and_carries_limitation(catalog: dict[str, Any]) -> None:
    """RESTRICTED is the bundle's word and it means *runs*. The node is in the
    frontier, and it can say which unmet edge restricted it -- a limitation that
    reached an artifact without naming its cause would be unauditable."""
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    accepted = _accept(route, "CP-0", "CP-1", cp0=_cp0_artifact(**{"CP-1A": "BLOCKED"}))
    cp2 = _node_id(route, "CP-2")

    assert cp2 in frontier(route, accepted)

    unmet = limitations_of(route, accepted, cp2)
    assert unmet, "a RESTRICTED node names what it is missing"
    assert {edge.source for edge in unmet} <= {"CP-1A", "CP-1B", "CP-1C", "CP-1D"}
    assert all(edge.type in {EdgeType.OPTIONAL, EdgeType.ADVISORY} for edge in unmet)


def test_dependency_order_refuses_a_cycle() -> None:
    """The catalog is a DAG. A cycle would mean a route that never resolves, and
    a pin nothing could execute -- so it is refused rather than ordered around."""
    nodes = [RouteNode("RN-A", "CP-A", 1), RouteNode("RN-B", "CP-B", 2)]
    edges = [
        Edge("CP-A", "CP-B", EdgeType.REQUIRED),
        Edge("CP-B", "CP-A", EdgeType.REQUIRED),
    ]

    with pytest.raises(Refusal) as caught:
        dependency_order(nodes, edges)

    assert caught.value.code is RefusalCode.ROUTE_HAS_A_CYCLE


def test_readiness_is_read_only_from_the_cp0_artifact(catalog: dict[str, Any]) -> None:
    """`docs/DECISIONS.md` §12, adopting CAOS-Final §18: readiness is read from
    the accepted CP-0 artifact and never passed in.

    A readiness claim inside some other module's artifact is not readiness. If it
    were, any module could harden the soft edges that feed it and assert its way
    past the gate that exists to measure whether the evidence is there.
    """
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    smuggled = {_node_id(route, "CP-1"): _cp0_artifact(**{"CP-1A": "READY"})}

    assert readiness_from(route, smuggled) == {}

    honest = _accept(route, "CP-0", cp0=_cp0_artifact(**{"CP-1A": "READY"}))
    assert readiness_from(route, honest) == {"CP-1A": "READY"}


def test_a_node_with_every_edge_met_is_runnable(catalog: dict[str, Any]) -> None:
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    accepted = _accept(route, "CP-0", cp0=_cp0_artifact())

    assert _state(route, accepted, "CP-1") is NodeState.RUNNABLE


def test_an_accepted_node_is_complete(catalog: dict[str, Any]) -> None:
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    accepted = _accept(route, "CP-0", cp0=_cp0_artifact())

    assert _state(route, accepted, "CP-0") is NodeState.COMPLETE
    assert _node_id(route, "CP-0") not in frontier(route, accepted)


def test_the_first_frontier_is_cp0_alone(catalog: dict[str, Any]) -> None:
    """Nothing has been accepted, so nothing has readiness. Every other node
    waits on a REQUIRED edge from CP-0."""
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")

    assert frontier(route, {}) == [_node_id(route, "CP-0")]


def test_dependency_order_puts_every_edge_before_its_target(
    catalog: dict[str, Any],
) -> None:
    route = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    position = {node.module_id: index for index, node in enumerate(route.nodes)}

    for edge in route.edges:
        assert position[edge.source] < position[edge.target], (
            f"{edge.source} must be resolved before {edge.target}"
        )


def test_resolved_route_is_pinned_and_replays_identically(
    catalog: dict[str, Any],
) -> None:
    """Invariant 10. Resolution is a pure function of pinned inputs, so the same
    inputs digest the same and execution reading only the pin takes the same
    path. A digest that moved would mean a replay was a different run."""
    first = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")
    second = resolve_route(catalog, PROFILE, "FULL_CREDIT_ASSESSMENT")

    assert route_digest(first) == route_digest(second)
    assert [n.route_node_id for n in first.nodes] == [
        n.route_node_id for n in second.nodes
    ]

    other = resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW")
    assert route_digest(other) != route_digest(first)


def test_the_research_extension_appends_cp_dr_without_editing_the_catalog(
    catalog: dict[str, Any],
) -> None:
    plain = resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW")
    extended = resolve_route(
        catalog,
        PROFILE,
        "LIQUIDITY_REVIEW",
        extensions=RouteExtensions(research_brief={"question": "refinancing"}),
    )

    assert "CP-DR" not in {node.module_id for node in plain.nodes}
    assert "CP-DR" in {node.module_id for node in extended.nodes}
    assert route_digest(extended) != route_digest(plain)


def test_cp_cf_waits_for_all_required_owners(catalog: dict[str, Any]) -> None:
    """`SYSTEM_SPEC.md` §6.2: the extension synthesises REQUIRED edges from
    CP-1, CP-2G and CP-4, which name every artifact owner CP-CF reads. CP-2G
    completing alone does not release it."""
    route = resolve_route(
        catalog,
        PROFILE,
        "FULL_CREDIT_ASSESSMENT",
        extensions=RouteExtensions(model_extension=True),
    )
    owners = {"CP-1", "CP-2G", "CP-4"}

    incoming = {edge.source for edge in route.edges if edge.target == "CP-CF"}
    assert owners <= incoming

    accepted = _accept(route, "CP-0", "CP-1", "CP-2G", cp0=_cp0_artifact())
    assert _state(route, accepted, "CP-CF") is NodeState.BLOCKED

    accepted[_node_id(route, "CP-4")] = {}
    assert _state(route, accepted, "CP-CF") is NodeState.RUNNABLE


def test_model_extension_refuses_missing_owner(catalog: dict[str, Any]) -> None:
    """COVENANT_REFINANCING carries CP-1 and CP-4 but no CP-2G. An extended
    route missing a required owner is refused during resolution, before pinning
    -- rather than dropping the edge or running CP-CF on missing inputs."""
    with pytest.raises(Refusal) as caught:
        resolve_route(
            catalog,
            PROFILE,
            "COVENANT_REFINANCING",
            extensions=RouteExtensions(model_extension=True),
        )

    assert caught.value.code is RefusalCode.ROUTE_EXTENSION_OWNER_MISSING


def test_an_unknown_pathway_is_refused(catalog: dict[str, Any]) -> None:
    with pytest.raises(Refusal) as caught:
        resolve_route(catalog, PROFILE, "NO_SUCH_PATHWAY")

    assert caught.value.code is RefusalCode.ROUTE_SELECTION_UNKNOWN


def test_an_unknown_profile_is_refused(catalog: dict[str, Any]) -> None:
    with pytest.raises(Refusal) as caught:
        resolve_route(catalog, "NO_SUCH_PROFILE", "FULL_CREDIT_ASSESSMENT")

    assert caught.value.code is RefusalCode.ROUTE_PROFILE_UNKNOWN
