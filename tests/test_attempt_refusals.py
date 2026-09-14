"""Why a billed answer was not accepted, written once (Task 4.3 slice d, D7).

`record_refusal` explains a recorded call's answer so a retry never replays a
known refusal. It writes only for an attempt with a call outcome, only once,
and never for a code that describes the store, the run or its fence.
"""

from __future__ import annotations

import pytest
from canonical_fixtures import CATALOG, LITE_PROFILE, LITE_SELECTION
from test_accepted_owner import _billed
from test_execution_freshness import _Harness, harness

from server.engine.route import ResolvedRoute, resolve_route
from server.refusals import RefusalCode
from server.store.outcomes import record_refusal
from server.store.runs import start_attempt

__all__ = ["harness"]


@pytest.fixture
def route() -> ResolvedRoute:
    return resolve_route(CATALOG, LITE_PROFILE, LITE_SELECTION)


def _refusals(harness: _Harness) -> list[tuple[object, str]]:
    return harness.conn.execute(
        "SELECT attempt_id, code FROM attempt_refusals ORDER BY recorded_at"
    ).fetchall()


def test_a_billed_answer_is_explained_once(harness: _Harness) -> None:
    attempt = _billed(harness)

    assert record_refusal(
        harness.conn, attempt_id=attempt, code=RefusalCode.CITATION_NOT_LOCATED
    )
    assert not record_refusal(
        harness.conn, attempt_id=attempt, code=RefusalCode.HANDOFF_MALFORMED
    )
    assert _refusals(harness) == [(attempt, "CITATION_NOT_LOCATED")]


def test_a_store_or_run_code_is_never_an_explanation(harness: _Harness) -> None:
    attempt = _billed(harness)

    for code in (
        RefusalCode.STORE_UNAVAILABLE,
        RefusalCode.LEASE_NOT_HELD,
        RefusalCode.RUN_NOT_RUNNING,
        RefusalCode.HANDOFF_BLOCKED,
    ):
        assert not record_refusal(harness.conn, attempt_id=attempt, code=code)
    assert _refusals(harness) == []


def test_an_attempt_without_a_recorded_call_is_not_explained(
    harness: _Harness,
) -> None:
    node = harness.route.nodes[0].route_node_id
    attempt = start_attempt(harness.conn, harness.run_id, node)

    assert not record_refusal(
        harness.conn, attempt_id=attempt, code=RefusalCode.CITATION_NOT_LOCATED
    )
    assert _refusals(harness) == []
