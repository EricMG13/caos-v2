"""Task 12.1: the governed writes reach the wire (O20).

Membership, withdrawal and the filing chain were store functions no request
path reached; this suite grows one section at a time as they arrive. Each is
one command through the shared envelope, so what these prove is not that the
store still works -- the store's own suites hold that -- but the three things a
route adds: the identity the caller may assert, the digest the request binds,
and the receipt a retry replays.

"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from command_fixtures import command_client, command_headers, member
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx import Response

from server.api.app import app
from server.api.commands._request import require_case_admin
from server.api.deps import actor_from_request
from server.store import StoreConnection
from server.store.members import Standing, standing_of

__all__ = ["command_client"]


def _post(
    client: TestClient, path: str, user: UUID, body: dict[str, Any] | None = None
) -> Response:
    answer: Response = client.post(
        path, headers=command_headers(user), json={} if body is None else body
    )
    return answer


# --- membership -------------------------------------------------------------


def test_an_administrator_grants_and_revokes_standing_over_http(
    command_client: TestClient, case: tuple[StoreConnection, UUID]
) -> None:
    conn, case_id = case
    admin = member(conn, case_id, Standing.ADMIN)
    newcomer = uuid4()

    granted = _post(
        command_client,
        f"/api/v1/cases/{case_id}/members",
        admin,
        {"user_id": str(newcomer), "standing": "WRITER"},
    )
    assert (granted.status_code, granted.json()["standing"]) == (201, "WRITER")
    conn.rollback()
    assert standing_of(conn, case_id=case_id, user_id=newcomer) is Standing.WRITER
    conn.rollback()

    revoked = _post(
        command_client, f"/api/v1/cases/{case_id}/members/{newcomer}/revocation", admin
    )
    assert revoked.status_code == 200
    conn.rollback()
    assert standing_of(conn, case_id=case_id, user_id=newcomer) is None
    conn.rollback()


def test_revoking_a_user_who_holds_no_standing_writes_no_event(
    command_client: TestClient, case: tuple[StoreConnection, UUID]
) -> None:
    """`withdraw_source`'s rule, one table over: nothing was revoked, so the
    chain must not say something was."""
    conn, case_id = case
    admin = member(conn, case_id, Standing.ADMIN)
    before = conn.execute("SELECT count(*) FROM audit_events").fetchone()
    conn.rollback()

    answer = _post(
        command_client, f"/api/v1/cases/{case_id}/members/{uuid4()}/revocation", admin
    )

    assert (answer.status_code, answer.json()["code"]) == (400, "REQUEST_INVALID")
    after = conn.execute("SELECT count(*) FROM audit_events").fetchone()
    receipts = conn.execute("SELECT count(*) FROM command_requests").fetchone()
    conn.rollback()
    assert (after, receipts) == (before, (0,))


# --- withdrawal -------------------------------------------------------------


def test_withdrawing_a_source_over_http_takes_it_out_of_the_live_set(
    command_client: TestClient, case: tuple[StoreConnection, UUID]
) -> None:
    conn, case_id = case
    writer = member(conn, case_id, Standing.WRITER)
    admitted = command_client.post(
        f"/api/v1/cases/{case_id}/sources",
        headers=command_headers(writer),
        files=[("document", ("report.txt", b"Total debt was USD 1,240.0m\n", "x"))],
    )
    [source_id] = admitted.json()["source_ids"]

    answer = _post(
        command_client,
        f"/api/v1/cases/{case_id}/sources/{source_id}/withdrawal",
        writer,
    )

    assert (answer.status_code, answer.json()["source_id"]) == (200, source_id)
    live = conn.execute(
        "SELECT count(*) FROM live_sources WHERE case_id=%s", (case_id,)
    ).fetchone()
    conn.rollback()
    assert live == (0,)
    again = _post(
        command_client,
        f"/api/v1/cases/{case_id}/sources/{source_id}/withdrawal",
        writer,
    )
    assert (again.status_code, again.json()["code"]) == (409, "EVIDENCE_NOT_AVAILABLE")


def test_require_case_admin_is_the_floor_the_membership_commands_declare() -> None:
    """The floor is a dependency the route names, not a line inside it: an
    ADMIN floor written in the body would run after the store was opened."""
    routes = {
        inner.path: inner
        for route in app.routes
        for inner in getattr(getattr(route, "original_router", None), "routes", [route])
        if isinstance(inner, APIRoute)
    }
    for path in (
        "/api/v1/cases/{case_id}/members",
        "/api/v1/cases/{case_id}/members/{user_id}/revocation",
    ):
        calls = [d.call for d in routes[path].dependant.dependencies]
        assert require_case_admin in calls, path
        assert calls.index(actor_from_request) < calls.index(require_case_admin)


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/sources/not-a-uuid/withdrawal", "EVIDENCE_NOT_AVAILABLE"),
        ("/members/not-a-uuid/revocation", "REQUEST_INVALID"),
    ],
)
def test_a_malformed_path_id_is_refused_in_the_declared_body(
    command_client: TestClient,
    case: tuple[StoreConnection, UUID],
    path: str,
    code: str,
) -> None:
    """`source_path` and `member_path` answer in the declared refusal body
    rather than FastAPI's 422, which would quote the input back."""
    conn, case_id = case
    actor = member(conn, case_id, Standing.ADMIN)

    answer = _post(command_client, f"/api/v1/cases/{case_id}{path}", actor)

    assert answer.json()["code"] == code, answer.text
