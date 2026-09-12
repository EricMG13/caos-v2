"""Reproduce F02 without a provider call or a normal-suite failure.

Run from the repository root with CAOS_TEST_POSTGRES_URL set. The probe creates
and drops a UUID-named database; exit 1 is the expected result until F02 is fixed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from server.blobs import BlobStore  # noqa: E402
from server.boundary_text import BoundaryText  # noqa: E402
from server.engine.route import resolve_route  # noqa: E402
from server.engine.runtime import Execution, run_route  # noqa: E402
from server.store import RunStatus, apply_schema, connect  # noqa: E402
from server.store.budget import reserve  # noqa: E402
from server.store.routes import pin_route  # noqa: E402
from server.store.runs import (  # noqa: E402
    Accepted,
    accept_attempt,
    create_case,
    run_status,
    start_attempt,
    start_run,
)

CATALOG = REPO / (
    "vendor/deploy-v/skills/cp-os-credit-os/references/"
    "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)


class ProviderWasCalled(AssertionError):
    pass


class NoProvider:
    def execute(self, route_node_id: str, module_id: str) -> object:
        raise ProviderWasCalled


def _url_for(base: str, database: str) -> str:
    return urlunsplit(urlsplit(base)._replace(path=f"/{database}"))


def main() -> None:
    base = os.environ["CAOS_TEST_POSTGRES_URL"]
    database = f"caos_test_{uuid4().hex}"
    route = resolve_route(
        json.loads(CATALOG.read_text(encoding="utf-8")),
        "FULL_CREDIT_32",
        "LIQUIDITY_REVIEW",
    )

    with psycopg.connect(base, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database}"')
    try:
        with (
            tempfile.TemporaryDirectory() as tmp,
            connect(_url_for(base, database)) as conn,
        ):
            apply_schema(conn)
            case_id = create_case(conn, BoundaryText.of("F02 isolated probe"))
            run_id = start_run(conn, case_id)
            pin_route(conn, run_id, route)
            conn.commit()

            cp0 = next(node for node in route.nodes if node.module_id == "CP-0")
            body = {
                "content_to_module_map": [
                    {
                        "module_id": module,
                        "readiness_status": "BLOCKED",
                    }
                    for module in ("CP-1", "CP-2", "CP-2D")
                ]
            }
            blobs = BlobStore(Path(tmp) / "blobs")
            digest = blobs.put(json.dumps(body).encode())
            attempt_id = start_attempt(conn, run_id, cp0.route_node_id)
            reserve(conn, attempt_id, Decimal("0.01"))
            accept_attempt(
                conn,
                attempt_id=attempt_id,
                accepted=Accepted(digest, Decimal("0.00"), "probe", "probe"),
            )

            run_route(
                conn,
                blobs,
                run_id=run_id,
                route=route,
                execution=Execution(NoProvider(), Decimal("0.01")),
            )
            status = run_status(conn, run_id)
            accepted = conn.execute(
                "SELECT count(*) FROM artifacts WHERE run_id = %s", (run_id,)
            ).fetchone()[0]
            print(
                f"stored_status={status.value} "
                f"accepted_nodes={accepted}/{len(route.nodes)}"
            )
            assert status is not RunStatus.COMPLETE, (
                "F02: blocked downstream nodes wrongly allowed terminal COMPLETE"
            )
    finally:
        with psycopg.connect(base, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')


if __name__ == "__main__":
    main()
