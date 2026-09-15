"""No reader takes an accepted artifact without its host record (Task 3.1
slice f-1c, §42.1).

A row with a NULL `record_sha256` refuses `ARTIFACT_RECORD_MISMATCH` in the
runtime, the proof and the API, whether or not the engine needs that node's
readiness: no artifact is read as a claims body.
"""

from __future__ import annotations

import pytest
from canonical_fixtures import (
    CATALOG,
    LITE_PROFILE,
    LITE_SELECTION,
    CanonicalCompletions,
)
from fastapi.testclient import TestClient
from test_canonical_readers import _reader, _run, client
from test_execution_freshness import _Harness, harness

from server.api.app import app, store_connection
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import accepted_artifacts
from server.qualification.proof import assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store.outcomes import execution_reads

__all__ = ["client", "harness"]

LITE = (LITE_PROFILE, LITE_SELECTION)


@pytest.fixture
def route() -> ResolvedRoute:
    return resolve_route(CATALOG, *LITE)


def _strip_record(harness: _Harness, module_id: str) -> None:
    node = next(n for n in harness.route.nodes if n.module_id == module_id)
    harness.conn.execute(
        "UPDATE artifacts SET record_sha256 = NULL WHERE run_id = %s"
        " AND route_node_id = %s",
        (harness.run_id, node.route_node_id),
    )
    harness.conn.commit()


@pytest.mark.parametrize("module_id", ["CP-0", "CP-L10"])
def test_readers_refuse_an_artifact_without_its_record(
    harness: _Harness, client: TestClient, module_id: str
) -> None:
    """No reader takes a row as a claims body: a NULL record refuses, whether
    or not the engine needs that node's readiness."""
    _run(harness, CanonicalCompletions(harness.source_id))
    headers = _reader(harness)
    _strip_record(harness, module_id)
    args = (harness.conn, harness.blobs, harness.route, harness.run_id)
    with pytest.raises(Refusal) as runtime:
        with execution_reads(harness.conn):
            accepted_artifacts(*args, bundle=harness.bundle)
    assert runtime.value.code is RefusalCode.ARTIFACT_RECORD_MISMATCH
    with pytest.raises(Refusal) as proof:
        with execution_reads(harness.conn):
            assert_orchestration_proof(
                harness.conn, harness.blobs, harness.bundle, run_id=harness.run_id
            )
    assert proof.value.code is RefusalCode.ARTIFACT_RECORD_MISMATCH
    app.dependency_overrides[store_connection] = lambda: harness.conn
    response = client.get(f"/api/runs/{harness.run_id}", headers=headers)
    assert response.status_code == 503
    assert response.json() == {"refusal": "ARTIFACT_RECORD_MISMATCH"}
