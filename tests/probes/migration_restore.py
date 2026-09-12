"""Manual, synthetic pg_dump/restore proof; never collected by ordinary CI.

Run from the repository with .venv/bin/python tests/probes/migration_restore.py.
Only the pinned local test PostgreSQL is addressed, never the shared dev DB.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_store_schema import _legacy, _populate, _records

from server.blobs import BlobStore
from server.store import apply_schema, connect

_ADMIN = "postgresql://postgres:local-test-admin-only@127.0.0.1:55437/postgres"
_CONTAINER = "caos-workbench-dev-test-postgres-1"


def main() -> None:
    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI required for this manual proof"
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "OPENROUTER_API_KEY",
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
                before = _records(conn)
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
                assert _records(conn) == before
                apply_schema(conn)
                assert _records(conn) == before
                assert conn.execute(
                    "SELECT version FROM store_migrations"
                ).fetchall() == [(1,)]
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
                        assert stored_digest == digest
                        assert (
                            BlobStore(Path(tmp) / "restored_blobs").get(stored_digest)
                            == b"synthetic legacy document and artifact"
                        )
            print(
                f"PASS dump={len(dump)} bytes; {original} -> {restored};"
                " version=1; rows/blobs intact"
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
