"""Import paths for the test suite, and the database the store suite runs on."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import pytest

REPO = Path(__file__).resolve().parents[1]
# The gate scripts are executables, not a package; import them by path.
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

# The vendored bundle's verifier refuses a tree that carries bytecode.
sys.dont_write_bytecode = True

# The store suite needs a real PostgreSQL. Absent, it skips with its reason;
# CAOS_REQUIRE_POSTGRES=1 turns that skip into a failure, which is what CI sets,
# so that a store suite that skipped can never read as a store suite that passed
# (docs/AI_CODE_QUALITY.md section 4).
POSTGRES_URL = os.environ.get("CAOS_TEST_POSTGRES_URL")
POSTGRES_REQUIRED = os.environ.get("CAOS_REQUIRE_POSTGRES") == "1"
_UNSET = "CAOS_TEST_POSTGRES_URL is unset: no database to run the store suite against"
_LIVE_CONFIGURATION = (
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "CAOS_TEST_POSTGRES_URL",
)


@contextmanager
def route_fault(conn: object) -> Iterator[None]:
    """Privileged corruption only in this suite's disposable UUID databases."""
    from typing import cast

    from server.store import StoreConnection

    connection = cast(StoreConnection, conn)
    row = connection.execute("SELECT current_database()").fetchone()
    assert row is not None and row[0].startswith("caos_test_")
    with connection.transaction():
        connection.execute("ALTER TABLE run_routes DISABLE TRIGGER route_immutable")
        yield
        connection.execute("ALTER TABLE run_routes ENABLE TRIGGER route_immutable")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live-provider", action="store_true", help="run live provider tests"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    live = [item for item in items if item.get_closest_marker("live_provider")]
    if not config.getoption("--live-provider"):
        items[:] = [item for item in items if item not in live]
        config.hook.pytest_deselected(items=live)
        return

    missing = [name for name in _LIVE_CONFIGURATION if not os.environ.get(name)]
    if live and missing:
        raise pytest.UsageError("live provider tests require: " + ", ".join(missing))


def _url_for(database: str) -> str:
    parts = urlsplit(POSTGRES_URL or "")
    return urlunsplit(parts._replace(path=f"/{database}"))


def gate_verdict(prompt: str, status: str = "READY") -> dict[str, object]:
    """The gate's readiness map when the prompt asked for one, nothing when it
    did not -- merged by a stub into the body it was already returning.

    Phase 11 refuses a gate that does not cover every other module of the pinned
    route, so four completion stubs need the same extra key; here once rather
    than as four copies of one row. Every fixture route in this suite with a gate
    is DEEP_RESEARCH -- CP-0 and CP-DR alone -- so one row covers the rest of it.
    """
    if "content_to_module_map" not in prompt:
        return {}
    return {
        "content_to_module_map": [
            {
                "module_id": "CP-DR",
                "readiness_status": status,
                "readiness_effect": "what the admitted source allows",
            }
        ]
    }


def approve_run(
    conn: object,
    *,
    case_id: UUID,
    run_id: UUID,
    route: object,
    bundle: object,
) -> UUID:
    """Pin and govern one real test run, returning its synthetic approver."""
    from server.engine.route import ResolvedRoute
    from server.methodology.bundle import Bundle
    from server.store import StoreConnection
    from server.store.gates import Gate, GateApproval, approve_gate, gate_preview
    from server.store.members import Standing, grant
    from server.store.routes import pin_route
    from server.store.run_inputs import pin_run_input
    from server.store.source_sets import snapshot_source_set

    connection = cast(StoreConnection, conn)
    source = snapshot_source_set(connection, case_id)
    pin_route(connection, run_id, cast(ResolvedRoute, route))
    pin_run_input(connection, run_id, source.version, cast(Bundle, bundle))
    approver = uuid4()
    grant(
        connection,
        case_id=case_id,
        user_id=approver,
        standing=Standing.APPROVER,
    )
    connection.commit()
    for gate in Gate:
        preview = gate_preview(connection, run_id, gate)
        approve_gate(
            connection,
            GateApproval(
                run_id=run_id,
                gate=gate,
                actor_id=approver,
                preview_sha256=preview.preview_sha256,
                input_fingerprint=preview.input_fingerprint,
            ),
        )
    return approver


@pytest.fixture
def case(empty_database: str) -> Iterator[tuple[object, UUID]]:
    """An open case on a committed connection, with the schema applied.

    Typed loosely here so this module does not import the store at collection
    time; the suites that use it annotate the connection as `StoreConnection`.
    """
    from server.boundary_text import BoundaryText
    from server.store import apply_schema, connect
    from server.store.runs import create_case

    with connect(empty_database) as conn:
        apply_schema(conn)
        case_id = create_case(conn, BoundaryText.of("Acme 2026 refinancing"))
        conn.commit()
        yield conn, case_id


@pytest.fixture
def empty_database() -> Iterator[str]:
    """A database of its own, created empty and dropped after the test.

    A namespace inside one shared database would be cheaper and would not answer
    the question these tests ask: what a process finds when it starts against a
    database no schema has been applied to yet.
    """
    if POSTGRES_URL is None:
        if POSTGRES_REQUIRED:
            pytest.fail(_UNSET)
        pytest.skip(_UNSET)

    import psycopg

    name = f"caos_test_{uuid4().hex}"
    with psycopg.connect(POSTGRES_URL, autocommit=True) as admin:
        # The name is a uuid4 hex this function minted, never caller input.
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield _url_for(name)
    finally:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
