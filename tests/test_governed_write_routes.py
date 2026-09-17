"""Task 12.1: the seven governed writes reach the wire (O20).

Membership, withdrawal and the whole filing chain were store functions no
request path reached. Each is now one command through the shared envelope, so
what these prove is not that the store still works -- `tests/test_filing_chain.py`
and `tests/test_members.py` hold that -- but the three things a route adds:
the identity the caller may assert, the digest the request binds, and the
receipt a retry replays.

The three-actor rule is checked here over HTTP because that is where it can be
evaded: the Report section composes the control from what it can see, and a
signer whose browser still shows "Freeze" is refused at commit, under the case
lock, by the store and not by the view.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from command_fixtures import command_client, command_headers, member
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx import Response
from test_deliverable_canonical import harness, lite, route
from test_execution_freshness import _Harness
from test_revisions import _save
from test_run_commands import _Counting

from server.api.app import app, methodology_bundle, store_connection
from server.api.commands import deliverable, members
from server.api.commands._request import require_case_admin
from server.api.deps import actor_from_request
from server.store import StoreConnection, connect
from server.store.members import Standing, standing_of

__all__ = ["command_client", "harness", "lite", "route"]


@pytest.fixture
def filing_client(command_client: TestClient, lite: _Harness) -> TestClient:
    """The command client over the harness's own bundle and accepted run."""
    app.dependency_overrides[methodology_bundle] = lambda: lite.bundle
    return command_client


def _post(
    client: TestClient, path: str, user: UUID, body: dict[str, Any] | None = None
) -> Response:
    answer: Response = client.post(
        path, headers=command_headers(user), json={} if body is None else body
    )
    return answer


def _approver(lite: _Harness) -> UUID:
    return member(lite.conn, lite.case_id, Standing.APPROVER)


def _digest(lite: _Harness, revision: UUID) -> str:
    row = lite.conn.execute(
        "SELECT payload_sha256 FROM deliverable_revisions WHERE revision_id=%s",
        (revision,),
    ).fetchone()
    lite.conn.rollback()
    assert row is not None
    return str(row[0])


def _case(lite: _Harness) -> str:
    return f"/api/v1/cases/{lite.case_id}"


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


# --- the filing chain -------------------------------------------------------


def test_a_revision_is_saved_from_the_run_and_never_from_the_request(
    filing_client: TestClient, lite: _Harness
) -> None:
    writer = member(lite.conn, lite.case_id, Standing.WRITER)

    answer = _post(
        filing_client,
        f"{_case(lite)}/runs/{lite.run_id}/revisions",
        writer,
        {"expected_revision_id": None, "narrative": []},
    )

    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["run_id"] == str(lite.run_id)
    assert _digest(lite, UUID(body["revision_id"])) == body["payload_sha256"]


def test_a_signer_who_then_freezes_is_refused_at_commit(
    filing_client: TestClient, lite: _Harness
) -> None:
    """The three-actor rule. The control was offered; the commit refuses."""
    revision = _save(lite)
    digest = _digest(lite, revision)
    signer = _approver(lite)
    signed = _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/signature",
        signer,
        {"payload_sha256": digest},
    )
    assert signed.status_code == 200, signed.text

    frozen = _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/freeze",
        signer,
        {"payload_sha256": digest},
    )

    assert (frozen.status_code, frozen.json()["code"]) == (
        400,
        "APPROVER_NOT_INDEPENDENT",
    )
    publications = lite.conn.execute(
        "SELECT count(*) FROM deliverable_publications"
    ).fetchone()
    lite.conn.rollback()
    assert publications == (0,)


def test_a_signer_or_the_freezer_who_then_files_is_refused_at_commit(
    filing_client: TestClient, lite: _Harness
) -> None:
    revision = _save(lite)
    digest = _digest(lite, revision)
    signer, freezer = _approver(lite), _approver(lite)
    assert (
        _post(
            filing_client,
            f"{_case(lite)}/revisions/{revision}/signature",
            signer,
            {"payload_sha256": digest},
        ).status_code
        == 200
    )
    assert (
        _post(
            filing_client,
            f"{_case(lite)}/revisions/{revision}/freeze",
            freezer,
            {"payload_sha256": digest},
        ).status_code
        == 200
    )

    for actor in (signer, freezer):
        refused = _post(
            filing_client,
            f"{_case(lite)}/revisions/{revision}/filing",
            actor,
            {"payload_sha256": digest},
        )
        assert refused.json()["code"] == "APPROVER_NOT_INDEPENDENT", refused.text

    filer = _approver(lite)
    filed = _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/filing",
        filer,
        {"payload_sha256": digest},
    )
    assert filed.status_code == 200, filed.text
    assert filed.json()["filed_by"] == str(filer)
    receipts = lite.conn.execute("SELECT count(*) FROM deliverable_receipts").fetchone()
    lite.conn.rollback()
    assert receipts == (1,), "the filing event's detached receipt rides its unit"


# --- digest-bound conflicts, driven with two connections --------------------


def test_a_save_that_raced_another_save_refuses_rather_than_committing(
    filing_client: TestClient, lite: _Harness, empty_database: str
) -> None:
    """Both drafts were written against the same latest revision; one lands."""
    writer = member(lite.conn, lite.case_id, Standing.WRITER)
    path = f"{_case(lite)}/runs/{lite.run_id}/revisions"
    seen: dict[str, Any] = {"expected_revision_id": None, "narrative": []}

    first = _post(filing_client, path, writer, seen)
    assert first.status_code == 201, first.text
    second = _post(filing_client, path, writer, seen)

    assert (second.status_code, second.json()["code"]) == (
        409,
        "COMMAND_EXPECTATION_STALE",
    )
    with connect(empty_database) as observer:
        rows = observer.execute(
            "SELECT count(*) FROM deliverable_revisions WHERE run_id=%s",
            (lite.run_id,),
        ).fetchone()
    assert rows == (1,)


def test_a_freeze_against_a_digest_that_is_not_the_revisions_refuses(
    filing_client: TestClient, lite: _Harness
) -> None:
    revision = _save(lite)
    digest = _digest(lite, revision)
    _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/signature",
        _approver(lite),
        {"payload_sha256": digest},
    )

    answer = _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/freeze",
        _approver(lite),
        {"payload_sha256": "b" * 64},
    )

    assert answer.json()["code"] == "DELIVERABLE_MOVED_SINCE_SIGNING", answer.text


def test_a_filing_against_a_digest_that_is_no_longer_the_frozen_one_refuses(
    filing_client: TestClient, lite: _Harness
) -> None:
    revision = _save(lite)
    digest = _digest(lite, revision)
    _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/signature",
        _approver(lite),
        {"payload_sha256": digest},
    )
    _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/freeze",
        _approver(lite),
        {"payload_sha256": digest},
    )

    answer = _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/filing",
        _approver(lite),
        {"payload_sha256": "c" * 64},
    )

    assert answer.json()["code"] == "DELIVERABLE_MOVED_SINCE_SIGNING", answer.text


# --- receipts ---------------------------------------------------------------


def test_every_new_command_replays_its_receipt_and_commits_nothing_twice(
    filing_client: TestClient, lite: _Harness
) -> None:
    conn, case_id = lite.conn, lite.case_id
    admin = member(conn, case_id, Standing.ADMIN)
    newcomer = uuid4()
    revision = _save(lite)
    digest = _digest(lite, revision)
    signer = _approver(lite)
    freezer = _approver(lite)
    _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/signature",
        signer,
        {"payload_sha256": digest},
    )
    _post(
        filing_client,
        f"{_case(lite)}/revisions/{revision}/freeze",
        freezer,
        {"payload_sha256": digest},
    )
    filer = _approver(lite)
    sent: list[tuple[str, UUID, dict[str, Any]]] = [
        (
            f"{_case(lite)}/members",
            admin,
            {"user_id": str(newcomer), "standing": "READER"},
        ),
        (
            f"{_case(lite)}/revisions/{revision}/filing",
            filer,
            {"payload_sha256": digest},
        ),
    ]
    for path, actor, body in sent:
        headers = command_headers(actor)
        first = filing_client.post(path, headers=headers, json=body)
        assert first.status_code in (200, 201), first.text
        events = conn.execute("SELECT count(*) FROM audit_events").fetchone()
        conn.rollback()

        again = filing_client.post(path, headers=headers, json=body)

        assert again.headers["idempotency-replayed"] == "true"
        assert again.json() == first.json()
        after = conn.execute("SELECT count(*) FROM audit_events").fetchone()
        conn.rollback()
        assert after == events, path


_FILING = ("SAVE_REVISION", "SIGN_OPINION", "FREEZE_DELIVERABLE", "FILE_DELIVERABLE")
_PATH = {
    "SIGN_OPINION": "signature",
    "FREEZE_DELIVERABLE": "freeze",
    "FILE_DELIVERABLE": "filing",
}


def _shown(
    client: TestClient, lite: _Harness, revision: UUID, actor: UUID
) -> dict[str, str | None]:
    """The Report section's judgement of its four controls, for this actor."""
    answer = client.get(
        f"{_case(lite)}/report?run={lite.run_id}&revision={revision}",
        headers=command_headers(actor),
    )
    assert answer.status_code == 200, answer.text
    return {
        view["action"]: view["refusal"] and view["refusal"]["code"]
        for view in answer.json()["chrome"]["actions"]
    }


def _send(
    client: TestClient, lite: _Harness, revision: UUID, actor: UUID, action: str
) -> Response:
    digest = _digest(lite, revision)
    if action == "SAVE_REVISION":
        return _post(
            client,
            f"{_case(lite)}/runs/{lite.run_id}/revisions",
            actor,
            {"expected_revision_id": str(revision), "narrative": []},
        )
    return _post(
        client,
        f"{_case(lite)}/revisions/{revision}/{_PATH[action]}",
        actor,
        {"payload_sha256": digest},
    )


def test_every_filing_control_the_report_shows_answers_as_it_was_shown(
    filing_client: TestClient, lite: _Harness
) -> None:
    """Step 5's gate for this section: a control shown available succeeds and a
    control shown refused refuses with exactly the code shown -- walked over
    every state the chain distinguishes, judged by the document read
    immediately before each command is sent."""
    signer, freezer, filer = (_approver(lite) for _ in range(3))
    revision = _save(lite)

    def walk(actor: UUID, action: str) -> None:
        shown = _shown(filing_client, lite, revision, actor)[action]
        answer = _send(filing_client, lite, revision, actor, action)
        if shown is None:
            assert answer.status_code in (200, 201), (action, answer.text)
        else:
            assert answer.json()["code"] == shown, (action, answer.text)

    # Unsigned: freeze and file are refused, the sign is not.
    for action in _FILING[1:]:
        walk(freezer, action)
    walk(signer, "SIGN_OPINION")
    # Signed: the signer is offered neither the freeze nor the filing.
    for action in _FILING[1:]:
        walk(signer, action)
    walk(freezer, "FREEZE_DELIVERABLE")
    # Frozen: the signer and the freezer are refused the filing; a third is not.
    for actor in (signer, freezer, filer):
        walk(actor, "FILE_DELIVERABLE")
    # Filed: every one of the three is refused, each with its own code.
    for action in _FILING[1:]:
        walk(filer, action)
    # And a member below the floor is refused every one of them.
    reader = member(lite.conn, lite.case_id, Standing.READER)
    assert set(_shown(filing_client, lite, revision, reader).values()) == {
        "NOT_AUTHORISED"
    }


def test_each_new_command_meets_its_declared_store_budget(
    filing_client: TestClient, lite: _Harness
) -> None:
    """The declared `IO_BUDGET` is measured, not estimated.

    The withdrawal is sent last on purpose: it takes the run's one source out
    of the live set, and every later derivation of this run's payload would
    then refuse -- which is invariant 1 working, and would make the save's
    measurement a measurement of a refusal.
    """
    conn, case_id = lite.conn, lite.case_id
    counted = _Counting(conn)
    app.dependency_overrides[store_connection] = lambda: counted
    approver = _approver(lite)
    revision = _save(lite)
    digest = _digest(lite, revision)
    writer = member(conn, case_id, Standing.WRITER)
    admin = member(conn, case_id, Standing.ADMIN)
    target = member(conn, case_id, Standing.READER)

    sent = [
        (
            deliverable.IO_BUDGET,
            f"{_case(lite)}/runs/{lite.run_id}/revisions",
            writer,
            {"expected_revision_id": str(revision), "narrative": []},
        ),
        (
            deliverable.IO_BUDGET,
            f"{_case(lite)}/revisions/{revision}/signature",
            approver,
            {"payload_sha256": digest},
        ),
        (
            members.IO_BUDGET,
            f"{_case(lite)}/members",
            admin,
            {"user_id": str(uuid4()), "standing": "READER"},
        ),
        (members.IO_BUDGET, f"{_case(lite)}/members/{target}/revocation", admin, {}),
        (
            members.IO_BUDGET,
            f"{_case(lite)}/sources/{lite.source_id}/withdrawal",
            writer,
            {},
        ),
    ]
    for budget, path, actor, body in sent:
        counted.executed = 0
        answer = filing_client.post(path, headers=command_headers(actor), json=body)
        assert answer.status_code in (200, 201), (path, answer.text)
        assert 0 < counted.executed <= budget, (path, counted.executed)


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
        ("/revisions/not-a-uuid/signature", "DELIVERABLE_NOT_FOUND"),
        ("/revisions/not-a-uuid/freeze", "DELIVERABLE_NOT_FOUND"),
        ("/revisions/not-a-uuid/filing", "DELIVERABLE_NOT_FOUND"),
        ("/members/not-a-uuid/revocation", "REQUEST_INVALID"),
    ],
)
def test_a_malformed_path_id_is_refused_in_the_declared_body(
    command_client: TestClient,
    case: tuple[StoreConnection, UUID],
    path: str,
    code: str,
) -> None:
    """`source_path`, `revision_path` and `member_path` each answer in the
    declared refusal body rather than FastAPI's 422, which would quote the
    input back."""
    conn, case_id = case
    actor = member(conn, case_id, Standing.ADMIN)

    answer = _post(command_client, f"/api/v1/cases/{case_id}{path}", actor)

    assert answer.json()["code"] == code, answer.text
