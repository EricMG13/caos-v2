"""Manual, synthetic pg_dump/restore proof; never collected by ordinary CI.

Run from the repository with .venv/bin/python tests/probes/migration_restore.py.
Only the pinned local test PostgreSQL is addressed, never the shared dev DB.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import UUID, uuid4

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_frozen_evidence import _insert
from test_run_inputs import _prepare
from test_store_schema import _catalog, _columns, _legacy, _populate, _records

import server.store as store
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute
from server.evidence.read import read_block
from server.store import MIGRATIONS, StoreConnection, apply_schema, connect
from server.store.budget import remaining, reserve
from server.store.extraction_integrity import _verify_extractions_v1
from server.store.gates import Gate, GateApproval, approve_gate, gate_preview
from server.store.members import Standing, grant
from server.store.run_inputs import load_run_input, pin_run_input
from server.store.runs import Accepted, accept_attempt, create_case, start_attempt

_ADMIN = "postgresql://postgres:local-test-admin-only@127.0.0.1:55437/postgres"
_CONTAINER = "caos-workbench-dev-test-postgres-1"


def _check_frozen(conn: StoreConnection, source: UUID | None) -> None:
    before = _records(conn)
    _verify_extractions_v1(conn)
    conn.commit()
    for table in ("source_blocks", "source_tokens"):
        for mutation in (
            f"UPDATE {table} SET text = text",
            f"DELETE FROM {table}",
            f"TRUNCATE {table}",
        ):
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                with conn.transaction():
                    conn.execute(mutation)
        if source is not None:
            with pytest.raises(psycopg.errors.CheckViolation, match="sealed"):
                with conn.transaction():
                    _insert(conn, table, source)
    assert _records(conn) == before


def _approve(
    conn: StoreConnection, case_id: UUID, run: UUID, route: ResolvedRoute
) -> str:
    """Acceptance requires every gate's current approval (Task17d3a); returns
    the real CP-DR node."""
    approver = uuid4()
    grant(conn, case_id=case_id, user_id=approver, standing=Standing.APPROVER)
    conn.commit()
    for gate in Gate:
        preview = gate_preview(conn, run, gate)
        approve_gate(
            conn,
            GateApproval(
                run_id=run,
                gate=gate,
                actor_id=approver,
                preview_sha256=preview.preview_sha256,
                input_fingerprint=preview.input_fingerprint,
            ),
        )
    return next(n.route_node_id for n in route.nodes if n.module_id == "CP-DR")


def _backup_schema(conn: StoreConnection, prefix_seven: bool) -> None:
    with patch.object(
        store, "MIGRATIONS", MIGRATIONS[:7] if prefix_seven else MIGRATIONS
    ):
        apply_schema(conn)


def main(*, migrated: bool = False, prefix_seven: bool = False) -> None:
    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI required for this manual proof"
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "OPENROUTER_API_KEY",
            "MODEL",
            "BASE_URL",
            "OPENROUTER_MODEL",
            "OPENROUTER_BASE_URL",
            "CAOS_REQUIRE_PROVIDER",
        }
    }
    created: list[str] = []
    original, restored = (f"caos_restore_{uuid4().hex}" for _ in range(2))
    with psycopg.connect(_ADMIN, autocommit=True) as admin, TemporaryDirectory() as tmp:
        try:
            admin.execute(
                psycopg.sql.SQL("CREATE DATABASE {}").format(
                    psycopg.sql.Identifier(original)
                )
            )
            created.append(original)
            blobs = BlobStore(Path(tmp) / "original_blobs")
            with connect(_ADMIN.rsplit("/", 1)[0] + "/" + original) as conn:
                _legacy(conn)
                digest = _populate(conn, blobs)
                if migrated:
                    _backup_schema(conn, prefix_seven)
                    case_id = create_case(
                        conn, BoundaryText.of("complete input restore")
                    )
                    run, sources, bundle, route = _prepare(conn, case_id, blobs.root)
                    pin = pin_run_input(
                        conn, run, sources.version, bundle, {"q": "Café?"}
                    )
                    attempt = start_attempt(
                        conn, run, _approve(conn, case_id, run, route)
                    )
                    reserve(conn, attempt, Decimal("0.25"))
                    accept_attempt(
                        conn,
                        attempt_id=attempt,
                        accepted=Accepted(
                            digest, Decimal("0.75"), "synthetic", "restore"
                        ),
                    )
                columns = _columns(conn)
                before = _records(conn, columns)
                catalog = _catalog(conn)
            dump = subprocess.run(  # nosec B603
                [
                    docker,
                    "exec",
                    _CONTAINER,
                    "pg_dump",
                    "-U",
                    "postgres",
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                    original,
                ],
                check=True,
                capture_output=True,
                env=env,
            ).stdout
            shutil.copytree(blobs.root, Path(tmp) / "restored_blobs")
            admin.execute(
                psycopg.sql.SQL("CREATE DATABASE {}").format(
                    psycopg.sql.Identifier(restored)
                )
            )
            created.append(restored)
            subprocess.run(  # nosec B603
                [
                    docker,
                    "exec",
                    "-i",
                    _CONTAINER,
                    "pg_restore",
                    "-U",
                    "postgres",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--no-acl",
                    "--dbname",
                    restored,
                ],
                input=dump,
                check=True,
                env=env,
            )
            with connect(_ADMIN.rsplit("/", 1)[0] + "/" + restored) as conn:
                assert _records(conn, columns) == before
                assert _catalog(conn) == catalog
                apply_schema(conn)
                assert _records(conn, columns) == before
                assert conn.execute(
                    "SELECT version FROM store_migrations ORDER BY version"
                ).fetchall() == [(i,) for i in range(1, len(MIGRATIONS) + 1)]
                assert conn.execute(
                    "SELECT count(*) FROM source_extractions"
                ).fetchone() == (1 if migrated else 0,)
                assert conn.execute(
                    "SELECT count(*) FROM call_outcomes"
                ).fetchone() == (1 if migrated else 0,)
                if migrated:
                    assert load_run_input(conn, run) == pin
                    assert remaining(conn, run) == Decimal("4.25")
                _check_frozen(conn, sources.members[0].source_id if migrated else None)
                for (source,) in conn.execute(
                    "SELECT source_id FROM sources"
                ).fetchall():
                    assert read_block(
                        conn, source_id=source, block_id="b000000"
                    ).text.value in {"synthetic", "one"}
                for table, column in (
                    ("sources", "document_sha256"),
                    ("artifacts", "artifact_sha256"),
                ):
                    rows = conn.execute(
                        psycopg.sql.SQL("SELECT {} FROM {}").format(
                            psycopg.sql.Identifier(column),
                            psycopg.sql.Identifier(table),
                        )
                    )
                    for (stored_digest,) in rows:
                        restored_bytes = BlobStore(Path(tmp) / "restored_blobs").get(
                            stored_digest
                        )
                        assert restored_bytes == blobs.get(stored_digest)
            print(
                f"PASS dump={len(dump)} bytes; {original} -> {restored};"
                f" version={len(MIGRATIONS)}; rows/blobs intact;"
                f" migrated_backup={migrated}; prefix_seven={prefix_seven};"
                " legacy provenance UNKNOWN; known v1 verified; native guards refuse"
            )
        finally:
            for name in reversed(created):
                admin.execute(
                    psycopg.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        psycopg.sql.Identifier(name)
                    )
                )
                print(f"Removed owned disposable database: {name}")


if __name__ == "__main__":
    main()
    main(migrated=True)
    main(migrated=True, prefix_seven=True)
