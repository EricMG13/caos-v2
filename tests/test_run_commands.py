"""Task 4.2 slice 4.2e: route selection, subject pin, gate preview and approval.

`create_run`, `pin_input`, `read_gate_preview`, `approve` and `path_gate`,
through the real app against PostgreSQL. A refusal commits nothing.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from command_fixtures import command_client, command_headers, member
from fastapi.testclient import TestClient
from httpx import Response

from server.api.commands import runs as runs_command
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.ingest import Document, admit_pack
from server.store import StoreConnection
from server.store.audit import audit_trail
from server.store.events import events_of
from server.store.routes import pinned_route
from server.store.run_inputs import load_run_input
from server.store.runs import create_case, fail_run, start_run

__all__ = ["command_client"]

ROUTE = {"profile_id": "LITE_CREDIT_22", "selection_id": "LITE_EARNINGS_UPDATE"}
SUBJECT = {
    "issuer_id": "EXAMPLE",
    "issuer_name": "Example Holdings plc",
    "reporting_period": "FY2025",
    "analysis_date": "2026-09-08",
}
PIN = {"subject": SUBJECT}
SOURCE_SET, RESEARCH_PLAN = "gates/source-set/", "gates/research-plan/"
TABLES = "runs run_routes run_inputs source_set_versions run_gates audit_events"


@pytest.fixture
def client(command_client: TestClient) -> TestClient:
    return command_client


@pytest.fixture
def sourced(case: tuple[StoreConnection, UUID], tmp_path: Path) -> UUID:
    """One live source on the case, admitted into the blob root the app serves."""
    conn, case_id = case
    [source_id] = _admit(conn, case_id, tmp_path, "report.txt")
    return source_id


def _admit(conn: StoreConnection, case_id: UUID, root: Path, name: str) -> list[UUID]:
    data = f"Total debt in {name} was USD 1,240.0m\n".encode()
    document = Document(filename=BoundaryText.of(name), data=data)
    admitted = admit_pack(
        conn, BlobStore(root / "blobs"), case_id=case_id, documents=[document]
    )
    conn.commit()
    return admitted


def _effects(conn: StoreConnection) -> tuple[int, ...]:
    """Everything a command could commit, counted."""
    counts = []
    for table in [*TABLES.split(), "command_requests"]:
        row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
        assert row is not None
        counts.append(int(row[0]))
    conn.rollback()
    return tuple(counts)


def _path(case_id: UUID, run: object = None, tail: str = "") -> str:
    runs = f"/api/v1/cases/{case_id}/runs"
    return runs if run is None else f"{runs}/{run}/{tail}"


def _send(  # noqa: PLR0913 -- the request and its identity
    client: TestClient,
    path: str,
    user: UUID | None,
    body: object = None,
    *,
    role: str = "ANALYST",
    key: UUID | None = None,
) -> Response:
    """A GET without a body, a POST with one."""
    headers = {} if user is None else command_headers(user, role=role, key=key)
    if body is None:
        got: Response = client.get(path, headers=headers)
        return got
    posted: Response = client.post(path, headers=headers, json=body)
    return posted


def _outcome(answer: Response) -> str:
    return f"{answer.status_code} {answer.json().get('code')}"


def _run(client: TestClient, case_id: UUID, writer: UUID, *, pin: bool) -> UUID:
    created = _send(client, _path(case_id), writer, ROUTE)
    assert created.status_code == 201, created.text
    run_id = UUID(created.json()["run_id"])
    if pin:
        pinned = _send(client, _path(case_id, run_id, "input"), writer, PIN)
        assert pinned.status_code == 200, pinned.text
    return run_id


def _digests(
    client: TestClient, case_id: UUID, run_id: UUID, user: UUID, gate: str = SOURCE_SET
) -> dict[str, str]:
    preview = _send(client, _path(case_id, run_id, gate + "preview"), user)
    assert preview.status_code == 200, preview.text
    return {k: preview.json()[k] for k in ("preview_sha256", "input_fingerprint")}


def test_only_an_adapter_route_can_be_selected(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, case_id = case
    writer = member(conn, case_id)
    resolved: list[tuple[str, str]] = []
    real = getattr(runs_command, "resolve_route", None)

    def watched(catalog: object, profile: str, selection: str) -> object:
        resolved.append((profile, selection))
        assert real is not None
        return real(catalog, profile, selection)

    monkeypatch.setattr(runs_command, "resolve_route", watched, raising=False)
    before = _effects(conn)
    for profile, selection in [
        ("FULL_CREDIT_32", "LIQUIDITY_REVIEW"),  # a real pathway, not enabled
        ("LITE_CREDIT_22", "NO_SUCH_PATHWAY"),
        ("NO_SUCH_PROFILE", "LITE_EARNINGS_UPDATE"),
    ]:
        body = {"profile_id": profile, "selection_id": selection}
        refused = _send(client, _path(case_id), writer, body)
        assert _outcome(refused) == "400 ROUTE_NOT_ENABLED"
    assert resolved == [], "a disabled pair is refused before resolution"
    extra = _send(client, _path(case_id), writer, {**ROUTE, "route": []})
    assert _outcome(extra) == "400 REQUEST_INVALID"
    assert _effects(conn) == before

    created = _send(client, _path(case_id), writer, ROUTE)

    assert created.status_code == 201
    run_id = UUID(created.json()["run_id"])
    assert resolved == [(ROUTE["profile_id"], ROUTE["selection_id"])]
    assert created.json() == {
        "case_id": str(case_id),
        "run_id": str(run_id),
        "route_digest": pinned_route(conn, run_id),
    }
    assert [e.name for e in events_of(conn, run_id)] == ["ROUTE_PINNED"]
    [entry] = audit_trail(conn, case_id)
    conn.rollback()
    assert (entry.action, entry.actor_id) == ("RUN_CREATED", writer)


def test_the_subject_pin_snapshots_live_sources_once(
    client: TestClient,
    case: tuple[StoreConnection, UUID],
    sourced: UUID,
    tmp_path: Path,
) -> None:
    conn, case_id = case
    writer = member(conn, case_id)
    run_id = _run(client, case_id, writer, pin=False)
    ended = _run(client, case_id, writer, pin=False)
    assert fail_run(conn, ended)
    foreign = start_run(conn, create_case(conn, BoundaryText.of("Other 2026")))
    conn.commit()
    before = _effects(conn)
    invalid = {"subject": {**SUBJECT, "analysis_date": "2026-02-30"}}
    for run, body, outcome in [
        (run_id, invalid, "400 REQUEST_INVALID"),
        (foreign, PIN, "404 RUN_NOT_FOUND"),
        ("not-a-run", PIN, "404 RUN_NOT_FOUND"),
        (ended, PIN, "409 RUN_NOT_RUNNING"),  # its snapshot rolls back too
    ]:
        answer = _send(client, _path(case_id, run, "input"), writer, body)
        assert _outcome(answer) == outcome
    assert _effects(conn) == before

    pinned = _send(client, _path(case_id, run_id, "input"), writer, PIN)

    assert pinned.status_code == 200, pinned.text
    stored = load_run_input(conn, run_id)
    assert stored is not None
    assert pinned.json() == {
        "run_id": str(run_id),
        "source_set_version": stored.source_version,
        "input_fingerprint": stored.input_fingerprint,
    }
    assert audit_trail(conn, case_id)[-1].action == "RUN_INPUT_PINNED"
    conn.rollback()
    assert _effects(conn)[3] == 1, "one source-set version"

    # A new source, then a second pin under a new key: a conflict, no snapshot.
    _admit(conn, case_id, tmp_path, "later.txt")
    before = _effects(conn)
    again = _send(client, _path(case_id, run_id, "input"), writer, PIN)
    assert _outcome(again) == "409 RUN_INPUT_ALREADY_PINNED"
    assert _effects(conn) == before
