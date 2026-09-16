"""Task 4.2 slice 4.2d: create case and source admission over the real app.

Create case is one nil-scope unit: the case, the creator's ADMIN standing, the
`CASE_CREATED` event and the receipt. Admission checks the envelope and the
caller before it reads a byte of the pack, parses and extracts with no
transaction open and no case lock held, then writes rows, event and receipt in
one governed unit (decisions 2, 4 and 6).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from command_fixtures import command_client, command_headers
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx import Response
from starlette.datastructures import FormData
from starlette.requests import Request

from server.api.app import app
from server.api.commands import cases
from server.api.deps import store_connection
from server.evidence import ingest
from server.store import StoreConnection
from server.store import commands as store_commands
from server.store.audit import audit_trail, verify_chain
from server.store.members import Standing, standing_of

__all__ = ["command_client"]

TEXT = b"Supplied quarterly report text.\n"


def _count(conn: StoreConnection, sql: str, *params: object) -> int:
    row = conn.execute(sql, params).fetchone()
    conn.rollback()
    assert row is not None
    return int(row[0])


def _sources(conn: StoreConnection, case_id: UUID) -> int:
    return _count(conn, "SELECT count(*) FROM sources WHERE case_id = %s", case_id)


def _receipts(conn: StoreConnection) -> int:
    return _count(conn, "SELECT count(*) FROM command_requests")


def _admit(  # noqa: PLR0913 -- one upload, its actor and its key
    client: TestClient,
    case_id: UUID,
    user: UUID,
    files: list[tuple[str, bytes]],
    *,
    role: str = "ANALYST",
    key: UUID | None = None,
) -> Response:
    answer: Response = client.post(
        f"/api/v1/cases/{case_id}/sources",
        headers=command_headers(user, role=role, key=key),
        files=[
            ("document", (name, data, "application/octet-stream"))
            for name, data in files
        ],
    )
    return answer


def _create(
    client: TestClient, user: UUID, title: str = "Acme 2027", role: str = "ANALYST"
) -> Response:
    answer: Response = client.post(
        "/api/v1/cases", headers=command_headers(user, role=role), json={"title": title}
    )
    return answer


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, int]]:
    """How often the route parsed a form and prepared (extracted) a pack."""
    counts = {"form": 0, "prepare": 0}
    real_form = Request._get_form

    async def form(self: Request, **kwargs: int) -> FormData:
        counts["form"] += 1
        return await real_form(self, **kwargs)

    def prepare(documents: list[ingest.Document]) -> ingest.PreparedPack:
        counts["prepare"] += 1
        return ingest.prepare_pack(documents)

    monkeypatch.setattr(Request, "_get_form", form)
    monkeypatch.setattr(cases, "prepare_pack", prepare)
    yield counts


def test_create_case_grants_the_creator_admin_in_one_audited_unit(
    case: tuple[StoreConnection, UUID],
    command_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, _ = case
    creator = uuid4()

    created = _create(command_client, creator, "Acme 2027 refinancing")

    assert created.status_code == 201
    case_id = UUID(created.json()["case_id"])
    assert created.json() == {"case_id": str(case_id)}
    title = conn.execute("SELECT title FROM cases WHERE case_id = %s", (case_id,))
    assert title.fetchone() == ("Acme 2027 refinancing",)
    assert standing_of(conn, case_id=case_id, user_id=creator) is Standing.ADMIN
    [event] = audit_trail(conn, case_id)
    assert (event.action, event.actor_id) == ("CASE_CREATED", creator)
    assert verify_chain(conn, case_id)
    conn.rollback()
    assert _receipts(conn) == 1

    # A failure at the unit's last statement leaves no case and no standing.
    def lost(*_args: object, **_kwargs: object) -> bool:
        raise psycopg.OperationalError

    monkeypatch.setattr(store_commands, "record_receipt", lost)
    before = _count(conn, "SELECT count(*) FROM cases")
    failed = _create(command_client, uuid4(), "Never lands")
    assert (failed.status_code, failed.json()["code"]) == (503, "STORE_UNAVAILABLE")
    assert _count(conn, "SELECT count(*) FROM cases") == before
    assert _count(conn, "SELECT count(*) FROM case_members") == 1
    assert _count(conn, "SELECT count(*) FROM audit_events") == 1


def test_create_case_title_crosses_boundary_text(
    case: tuple[StoreConnection, UUID], command_client: TestClient
) -> None:
    conn, _ = case
    refused = _create(command_client, uuid4(), "Acme \u202e7202")
    assert (refused.status_code, refused.json()["code"]) == (
        400,
        "BOUNDARY_TEXT_INVALID",
    )
    assert _count(conn, "SELECT count(*) FROM cases") == 1
    created = _create(command_client, uuid4(), "Café")
    stored = conn.execute(
        "SELECT title FROM cases WHERE case_id = %s", (created.json()["case_id"],)
    ).fetchone()
    conn.rollback()
    assert stored == ("Café",)


def test_a_replayed_create_case_makes_one_case(
    case: tuple[StoreConnection, UUID], command_client: TestClient
) -> None:
    conn, _ = case
    user, key = uuid4(), uuid4()
    headers = command_headers(user, key=key)
    first = command_client.post("/api/v1/cases", headers=headers, json={"title": "A"})
    again = command_client.post("/api/v1/cases", headers=headers, json={"title": "A"})
    other = command_client.post("/api/v1/cases", headers=headers, json={"title": "B"})

    assert (first.status_code, again.status_code) == (201, 201)
    assert again.json() == first.json()
    assert again.headers["idempotency-replayed"] == "true"
    assert (other.status_code, other.json()["code"]) == (409, "IDEMPOTENCY_KEY_REUSED")
    assert _count(conn, "SELECT count(*) FROM cases") == 2


@pytest.mark.parametrize(
    ("role", "status"), [("READER", 403), ("ANALYST", 201), ("ADMIN", 201)]
)
def test_create_case_actor_matrix(
    case: tuple[StoreConnection, UUID],
    command_client: TestClient,
    role: str,
    status: int,
) -> None:
    conn, _ = case
    answer = _create(command_client, uuid4(), role=role)
    assert answer.status_code == status
    if status == 403:
        assert answer.json()["code"] == "NOT_AUTHORISED"
        assert _count(conn, "SELECT count(*) FROM cases") == 1
    anonymous = command_client.post("/api/v1/cases", json={"title": "x"})
    assert (anonymous.status_code, anonymous.json()["code"]) == (
        401,
        "NOT_AUTHENTICATED",
    )


class _Counting:
    """Counts store round trips (statements and cursors) on the request's
    connection, so each declared budget is measured rather than asserted."""

    def __init__(self, conn: StoreConnection) -> None:
        self._conn = conn
        self.executed = 0

    def execute(self, *args: Any, **kwargs: Any) -> object:  # noqa: ANN401
        self.executed += 1
        return self._conn.execute(*args, **kwargs)

    def cursor(self, *args: Any, **kwargs: Any) -> object:  # noqa: ANN401
        self.executed += 1
        return self._conn.cursor(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._conn, name)


def test_each_case_command_declares_and_meets_its_store_budget(
    case: tuple[StoreConnection, UUID], command_client: TestClient
) -> None:
    conn, _case_id = case

    def measured(send: Callable[[], Response]) -> tuple[int, int]:
        counter = _Counting(conn)
        app.dependency_overrides[store_connection] = lambda: counter
        answer = send()
        app.dependency_overrides[store_connection] = lambda: conn
        return answer.status_code, counter.executed

    user, key = uuid4(), uuid4()
    create = lambda: command_client.post(  # noqa: E731
        "/api/v1/cases", headers=command_headers(user, key=key), json={"title": "A"}
    )
    assert measured(create) == (201, cases.CREATE_CASE_IO)
    assert measured(create)[1] <= cases.REPLAY_IO


def test_create_case_is_the_one_route_of_its_router_so_far() -> None:
    served = {
        (route.path, route.endpoint)
        for route in cases.router.routes
        if isinstance(route, APIRoute)
    }
    # `admit_sources` joins it with the admission half of this slice.
    assert served == {("/api/v1/cases", cases.create_case_command)}
