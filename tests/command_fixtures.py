"""Shared fixtures for the Task 4.2 command suites: identity headers with an
`Idempotency-Key`, case members, and the real app served on the `case`
fixture's connection (import the fixture by name and list it in `__all__`)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from server.api import app as app_module
from server.api.app import app, blob_store, store_connection
from server.blobs import BlobStore
from server.store import StoreConnection
from server.store.members import Standing, grant

# The identity provider's group for each global role (`server/api/identity.py`).
GROUPS = {"READER": "caos-readers", "ANALYST": "caos-analysts", "ADMIN": "caos-admins"}


def command_headers(
    user: UUID, *, role: str = "ANALYST", key: UUID | str | None = None
) -> dict[str, str]:
    """What the edge forwards for `user` holding global `role`, and the key.

    `key=None` mints a fresh one; pass `""` to send the header empty.
    """
    return {
        "x-caos-user": str(user),
        "x-forwarded-groups": GROUPS[role],
        "idempotency-key": str(uuid4() if key is None else key),
    }


def member(
    conn: StoreConnection, case_id: UUID, standing: Standing = Standing.WRITER
) -> UUID:
    """A new user holding `standing` on the case, committed."""
    user = uuid4()
    grant(conn, case_id=case_id, user_id=user, standing=standing)
    conn.commit()
    return user


def constant(value: object) -> Callable[[], object]:
    """A dependency override with no parameters FastAPI would read as inputs."""
    return lambda: value


@pytest.fixture
def command_client(
    case: tuple[StoreConnection, UUID],
    empty_database: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """The real app, booted against the test database, on the case's connection."""
    conn, _case_id = case
    monkeypatch.setenv(app_module.DATABASE_URL, empty_database)
    app.dependency_overrides[store_connection] = constant(conn)
    app.dependency_overrides[blob_store] = constant(BlobStore(tmp_path / "blobs"))
    try:
        with TestClient(app) as opened:
            yield opened
    finally:
        app.dependency_overrides.clear()
