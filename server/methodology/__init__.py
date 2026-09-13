"""The methodology boundary: the bundle, the registry, the calculator seam."""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.methodology.handoff import ADAPTER_MODULES

if TYPE_CHECKING:
    from server.engine.route import ResolvedRoute

CLAIMS_ADAPTER_VERSION = "claims-json-v1"
CANONICAL_ADAPTER_VERSION = "canonical-markdown-v1"


def adapter_for(route: ResolvedRoute) -> str:
    """The host adapter a run on `route` pins, derived from the pinned route alone.

    Temporary dispatch (`docs/DECISIONS.md` §42.1): canonical exactly when every
    node's module is a canonical adapter module, claims otherwise. No flag,
    environment value or caller chooses it. It expires at Task 3.1 slice f-1,
    which makes the adapter one constant and removes the claims branch.
    """
    if route.nodes and all(node.module_id in ADAPTER_MODULES for node in route.nodes):
        return CANONICAL_ADAPTER_VERSION
    return CLAIMS_ADAPTER_VERSION
