"""The Analysis section read (Phase 4 Task 4.1, slice 4.1e).

Every accepted handoff of the displayed run, in route order, read through
`accepted_handoff` -- the record bound to its Markdown and to the identity the
store rebuilds, no re-anchoring (§42.4) -- and labelled per §46.3: host-verified
source facts, model-authored analysis, and no host calculation. Unaccepted
nodes make the document partial. The case is the authorisation resource; a
run of another case is the same `RUN_NOT_FOUND` as an unknown one.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from conftest import priced
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from lite_route_fixtures import RealisticLiteCompletions
from test_canonical_execution import harness, route
from test_execution_freshness import _Harness
from test_loop_charges import ESTIMATE

from server.api import app as app_module
from server.api.app import app
from server.api.identity import TRUST_SWITCH
from server.api.reads import analysis as analysis_read
from server.api.reads import directory as directory_read
from server.api.reads import upload as upload_read
from server.api.reads.analysis import section_blobs, section_bundle
from server.api.reads.directory import section_store
from server.api.wire import CLEARS, AnalysisDocument
from server.boundary_text import BoundaryText
from server.engine.runtime import Execution, run_route
from server.methodology.handoff import _decoded_record, record_bytes
from server.methodology.runner import ModuleProvider
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.gates import withdraw_source
from server.store.members import Standing, grant, revoke
from server.store.runs import create_case, start_run

__all__ = ["harness", "route"]


@pytest.fixture
def client(
    harness: _Harness, empty_database: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)
    monkeypatch.delenv(TRUST_SWITCH, raising=False)
    app.dependency_overrides[section_store] = lambda: harness.conn
    app.dependency_overrides[section_blobs] = lambda: harness.blobs
    app.dependency_overrides[section_bundle] = lambda: harness.bundle
    try:
        with TestClient(app) as opened:
            yield opened
    finally:
        app.dependency_overrides.clear()


class _CountingConnection:
    """Counts store round trips, so the declared budget is measured."""

    def __init__(self, conn: StoreConnection) -> None:
        self._conn = conn
        self.executed = 0

    def execute(self, *args: object, **kwargs: object) -> object:
        self.executed += 1
        return self._conn.execute(*args, **kwargs)  # type: ignore[arg-type]


def _serving(counter: _CountingConnection) -> Callable[[], _CountingConnection]:
    return lambda: counter


def _as(user_id: UUID, groups: str | None = None) -> dict[str, str]:
    headers = {"x-caos-user": str(user_id)}
    if groups is not None:
        headers["x-forwarded-groups"] = groups
    return headers


def _refused(code: RefusalCode) -> dict[str, str]:
    return {"code": code.value, "clears": CLEARS[code]}


def _analysis(case_id: object, run: object | None = None) -> str:
    path = f"/api/v1/cases/{case_id}/analysis"
    return path if run is None else f"{path}?run={run}"


def _run(
    harness: _Harness, qa_by_module: dict[str, str] | None = None
) -> RealisticLiteCompletions:
    completions = RealisticLiteCompletions(
        harness.source_id, qa_by_module=qa_by_module or {}
    )
    provider = ModuleProvider(
        harness.conn,
        harness.bundle,
        harness.blobs,
        completions,
        harness.route,
        harness.run_id,
    )
    run_route(
        harness.conn,
        harness.blobs,
        run_id=harness.run_id,
        route=harness.route,
        execution=Execution(provider, priced(ESTIMATE), harness.bundle),
    )
    harness.conn.rollback()
    return completions


def _reader(harness: _Harness) -> UUID:
    user = uuid4()
    grant(harness.conn, case_id=harness.case_id, user_id=user, standing=Standing.READER)
    harness.conn.commit()
    return user


def _document(client: TestClient, harness: _Harness, path: str) -> AnalysisDocument:
    response = client.get(path, headers=_as(_reader(harness)))
    harness.conn.rollback()
    assert response.status_code == 200, response.json()
    return AnalysisDocument.model_validate(response.json())


def test_analysis_labels_source_facts_model_analysis_and_no_host_calculation(
    client: TestClient, harness: _Harness
) -> None:
    completions = _run(harness)

    document = _document(client, harness, _analysis(harness.case_id))

    body = document.body
    assert (document.status, document.notes, document.observed_empty) == (
        "complete",
        [],
        False,
    )
    assert body.case_id == harness.case_id
    assert body.latest_run_id == body.displayed_run_id == harness.run_id
    assert body.subject is not None
    assert body.subject.issuer_name
    assert body.pending == []
    assert [h.route_node_id for h in body.handoffs] == [
        n.route_node_id for n in harness.route.nodes
    ]
    rows = {
        str(node): (str(artifact), str(record), created)
        for node, artifact, record, created in harness.conn.execute(
            "SELECT route_node_id, artifact_sha256, record_sha256, created_at"
            " FROM artifacts WHERE run_id = %s",
            (harness.run_id,),
        ).fetchall()
    }
    harness.conn.rollback()
    for handoff, answer in zip(body.handoffs, completions.answers, strict=True):
        artifact, record, created = rows[handoff.route_node_id]
        assert (handoff.artifact_sha256, handoff.record_sha256) == (artifact, record)
        assert handoff.accepted_at == created
        assert handoff.host_calculation == "NONE"
        # The exact Markdown the model wrote, decoded, not rendered or trimmed.
        assert handoff.model_analysis == answer.decode("utf-8")
        assert handoff.model_analysis.encode() == harness.blobs.get(artifact)
        [fact] = handoff.source_facts
        assert fact.filename == "report.txt"
        assert fact.page == 1
        assert fact.matched_text == completions.quotes[0]
        assert fact.withdrawn_at is None
        assert fact.rects and all(r.x1 > r.x0 for r in fact.rects)


def test_restricted_limitations_and_screening_scope_reach_the_wire(
    client: TestClient, harness: _Harness
) -> None:
    _run(harness, qa_by_module={"CP-L10": "Restricted"})

    document = _document(client, harness, _analysis(harness.case_id))

    by_module = {h.module_id: h for h in document.body.handoffs}
    restricted = by_module["CP-L10"]
    assert restricted.qa_status == "Restricted"
    assert "Only one source report was delivered" in restricted.limitation_flags
    assert by_module["CP-5"].qa_status == "Passed"
    for handoff in by_module.values():
        # Every LITE handoff is a screen, whatever committee status it wrote.
        assert (handoff.decision_scope, handoff.screening_only) == (
            "SCREENING_ONLY",
            True,
        )


def test_withdrawal_of_a_cited_source_is_read_live(
    client: TestClient, harness: _Harness
) -> None:
    _run(harness)
    withdraw_source(
        harness.conn,
        case_id=harness.case_id,
        source_id=harness.source_id,
        actor_id=harness.approver,
    )
    harness.conn.commit()

    document = _document(client, harness, _analysis(harness.case_id))

    for handoff in document.body.handoffs:
        assert all(f.withdrawn_at is not None for f in handoff.source_facts)


def test_a_record_that_no_longer_binds_its_markdown_refuses_artifact_record_mismatch(
    client: TestClient, harness: _Harness
) -> None:
    _run(harness)
    last = harness.route.nodes[-1].route_node_id
    [[record_sha]] = harness.conn.execute(
        "SELECT record_sha256 FROM artifacts WHERE run_id = %s AND route_node_id = %s",
        (harness.run_id, last),
    ).fetchall()
    record = _decoded_record(harness.blobs.get(str(record_sha)))
    moved = replace(
        record,
        projections=replace(
            record.projections,
            confidence_score=record.projections.confidence_score - 1,
        ),
    )
    harness.conn.execute(
        "UPDATE artifacts SET record_sha256 = %s WHERE run_id = %s"
        " AND route_node_id = %s",
        (harness.blobs.put(record_bytes(moved)), harness.run_id, last),
    )
    harness.conn.commit()

    response = client.get(_analysis(harness.case_id), headers=_as(_reader(harness)))
    harness.conn.rollback()

    assert (response.status_code, response.json()) == (
        503,
        _refused(RefusalCode.ARTIFACT_RECORD_MISMATCH),
    )


def test_unaccepted_nodes_make_analysis_partial_with_a_note(
    client: TestClient, harness: _Harness
) -> None:
    _run(harness, qa_by_module={"CP-L10": "Blocked"})
    reader = _reader(harness)
    counter = _CountingConnection(harness.conn)
    app.dependency_overrides[section_store] = _serving(counter)

    response = client.get(_analysis(harness.case_id), headers=_as(reader))
    harness.conn.rollback()

    assert response.status_code == 200
    document = AnalysisDocument.model_validate(response.json())
    # The budget is linear in accepted handoffs: one here.
    assert counter.executed == analysis_read.FIXED_IO + analysis_read.PER_HANDOFF_IO

    assert document.status == "partial"
    assert [note.value for note in document.notes] == ["HANDOFFS_PENDING"]
    assert document.observed_empty is False
    assert [h.module_id for h in document.body.handoffs] == ["CP-0"]
    pending = [(p.module_id, p.state.value) for p in document.body.pending]
    assert [module for module, _state in pending] == ["CP-L10", "CP-5"]
    assert all(state != "COMPLETE" for _module, state in pending)


def test_run_and_analysis_name_displayed_and_latest_runs_separately(
    client: TestClient, harness: _Harness
) -> None:
    _run(harness)
    latest = start_run(harness.conn, harness.case_id)
    harness.conn.commit()

    shown = _document(client, harness, _analysis(harness.case_id, harness.run_id))
    assert (shown.body.latest_run_id, shown.body.displayed_run_id) == (
        latest,
        harness.run_id,
    )
    assert len(shown.body.handoffs) == 3
    assert shown.status == "complete"

    unpinned = _document(client, harness, _analysis(harness.case_id))
    assert (unpinned.body.latest_run_id, unpinned.body.displayed_run_id) == (
        latest,
        latest,
    )
    assert (unpinned.body.subject, unpinned.body.handoffs) == (None, [])
    assert unpinned.body.pending == []
    assert unpinned.status == "partial"
    assert [note.value for note in unpinned.notes] == ["ROUTE_NOT_PINNED"]


def test_a_case_without_a_run_is_observed_empty(
    client: TestClient, harness: _Harness
) -> None:
    empty = create_case(harness.conn, BoundaryText.of("No runs yet"))
    reader = uuid4()
    grant(harness.conn, case_id=empty, user_id=reader, standing=Standing.READER)
    harness.conn.commit()

    response = client.get(_analysis(empty), headers=_as(reader))
    harness.conn.rollback()

    document = AnalysisDocument.model_validate(response.json())
    assert (document.observed_empty, document.status, document.notes) == (
        True,
        "complete",
        [],
    )
    body = document.body
    assert [body.latest_run_id, body.displayed_run_id, body.subject] == [None] * 3


def test_a_run_of_another_case_unknown_or_malformed_is_run_not_found(
    client: TestClient, harness: _Harness
) -> None:
    other = create_case(harness.conn, BoundaryText.of("Another case"))
    foreign = start_run(harness.conn, other)
    harness.conn.commit()
    reader = _reader(harness)

    for run in (foreign, uuid4(), "not-a-run"):
        response = client.get(_analysis(harness.case_id, run), headers=_as(reader))
        harness.conn.rollback()
        assert (response.status_code, response.json()) == (
            404,
            _refused(RefusalCode.RUN_NOT_FOUND),
        ), run


def test_analysis_private_404_and_actor_matrix(
    client: TestClient, harness: _Harness
) -> None:
    conn, case_id = harness.conn, harness.case_id
    members = {s: uuid4() for s in (Standing.READER, Standing.WRITER)}
    for standing, user in members.items():
        grant(conn, case_id=case_id, user_id=user, standing=standing)
    revoked = uuid4()
    grant(conn, case_id=case_id, user_id=revoked, standing=Standing.WRITER)
    revoke(conn, case_id=case_id, user_id=revoked)
    conn.commit()

    anonymous = client.get(_analysis(case_id))
    assert (anonymous.status_code, anonymous.json()) == (
        401,
        _refused(RefusalCode.NOT_AUTHENTICATED),
    )
    allowed = (*members.items(), (Standing.APPROVER, harness.approver))
    for standing, user in allowed:
        response = client.get(_analysis(case_id), headers=_as(user))
        conn.rollback()
        assert response.status_code == 200, standing
        served = AnalysisDocument.model_validate(response.json()).chrome.served_role
        assert served.standing is standing

    refused = [
        (uuid4(), None, case_id),
        (revoked, None, case_id),
        (uuid4(), "caos-admins", case_id),
        (members[Standing.READER], None, uuid4()),
        (members[Standing.READER], None, "not-a-case"),
    ]
    for user, groups, path_case in refused:
        response = client.get(_analysis(path_case), headers=_as(user, groups))
        conn.rollback()
        assert (response.status_code, response.json()) == (
            404,
            _refused(RefusalCode.CASE_NOT_FOUND),
        ), (user, groups, path_case)


def test_an_anonymous_or_malformed_analysis_request_opens_no_store_connection(
    client: TestClient, harness: _Harness
) -> None:
    opened: list[str] = []

    def counted() -> StoreConnection:
        opened.append("store")
        return harness.conn

    app.dependency_overrides[section_store] = counted

    assert client.get(_analysis(harness.case_id)).status_code == 401
    for path in (_analysis("not-a-case"), _analysis(harness.case_id, "not-a-run")):
        assert client.get(path, headers=_as(uuid4())).status_code == 404
    assert opened == []


def test_the_analysis_request_path_declares_its_store_budget(
    client: TestClient, harness: _Harness
) -> None:
    _run(harness)
    reader = _reader(harness)
    counter = _CountingConnection(harness.conn)
    app.dependency_overrides[section_store] = _serving(counter)

    response = client.get(_analysis(harness.case_id), headers=_as(reader))
    harness.conn.rollback()

    assert response.status_code == 200
    assert len(AnalysisDocument.model_validate(response.json()).body.handoffs) == 3
    assert 0 < counter.executed == analysis_read.IO_BUDGET


def test_the_section_blobs_and_bundle_are_the_apps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`section_blobs` and `section_bundle` delegate to the app's dependencies."""
    monkeypatch.delenv(app_module.BLOB_ROOT, raising=False)
    with pytest.raises(Refusal) as refused:
        section_blobs()
    assert refused.value.code is RefusalCode.STORE_NOT_CONFIGURED
    assert section_bundle() is app_module.methodology_bundle()


def test_the_analysis_route_is_read_analysis_with_identity_before_the_store() -> None:
    """`read_analysis` serves the path; `section_actor`, `case_path` and
    `run_query` are solved before `section_store`, `section_blobs` and
    `section_bundle`."""
    [served] = [
        route for route in analysis_read.router.routes if isinstance(route, APIRoute)
    ]
    assert served.path == "/api/v1/cases/{case_id}/analysis"
    assert served.endpoint is analysis_read.read_analysis
    assert [d.call for d in served.dependant.dependencies] == [
        directory_read.section_actor,
        upload_read.case_path,
        analysis_read.run_query,
        section_store,
        section_blobs,
        section_bundle,
    ]
