"""The pin: where a resolved route becomes the thing execution reads.

Invariant 10 in two halves. `tests/test_route_resolution.py` holds the pure half
-- resolution is a function of pinned inputs, so it digests the same every time.
This file holds the other: the digest is written once, with its event, and a
replay reads the pin rather than re-resolving against a catalog that may have
moved underneath it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from server.engine.route import ResolvedRoute, resolve_route, route_digest
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.events import RunEvent, events_of
from server.store.routes import pin_route, pinned_route, resolved_route
from server.store.runs import start_run

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return loaded


def _route(catalog: dict[str, Any], selection_id: str) -> ResolvedRoute:
    return resolve_route(catalog, PROFILE, selection_id)


def test_a_pinned_route_is_what_execution_reads(
    catalog: dict[str, Any], case: tuple[StoreConnection, UUID]
) -> None:
    """The other half of invariant 10. Pinning happens once at the plan gate;
    the pin is what a replay reads, so re-pinning the same route is the gate
    replayed and re-pinning a different one is a different run wearing the same
    id."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    resolved = resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW")

    digest = pin_route(conn, run_id, resolved)

    assert digest == route_digest(resolved)
    assert pinned_route(conn, run_id) == digest
    assert [event.name for event in events_of(conn, run_id)] == [
        RunEvent.ROUTE_PINNED.value
    ]

    # The same gate, replayed after a crash: accepted, and not a second event.
    assert pin_route(conn, run_id, resolve_route(catalog, PROFILE, "LIQUIDITY_REVIEW"))
    assert len(events_of(conn, run_id)) == 1

    with pytest.raises(Refusal) as caught:
        pin_route(conn, run_id, resolve_route(catalog, PROFILE, "EARNINGS_UPDATE"))
    assert caught.value.code is RefusalCode.ROUTE_ALREADY_PINNED
    assert pinned_route(conn, run_id) == digest


def test_the_pinned_route_reads_back_as_the_route_that_was_pinned(
    catalog: dict[str, Any], case: tuple[StoreConnection, UUID]
) -> None:
    """`resolved_route` is what a surface draws a running route from.

    Read back, never re-resolved: resolving the catalog again would draw
    whatever it says today, which is the one thing pinning exists to prevent.
    The digest is the check -- a round trip that lost an edge's type or a
    predicate would digest differently, which is precisely what execution would
    then disagree with.
    """
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    pinned = resolve_route(
        catalog, PROFILE, "FULL_CREDIT_ASSESSMENT", predicates={"has_covenants": "yes"}
    )
    pin_route(conn, run_id, pinned)

    read_back = resolved_route(conn, run_id)

    assert read_back == pinned
    assert read_back is not None
    assert route_digest(read_back) == pinned_route(conn, run_id)


def test_a_run_before_its_plan_gate_has_no_resolved_route(
    case: tuple[StoreConnection, UUID],
) -> None:
    """Not an error. There is simply nothing pinned yet, and a caller that got a
    route here would be reading one nobody approved."""
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()

    assert resolved_route(conn, run_id) is None
