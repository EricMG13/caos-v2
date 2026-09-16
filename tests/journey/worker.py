"""The journey's worker: the real `run_worker` over a deterministic provider.

Task 4.5 decision 10. It runs from the production image with `./tests` mounted
read-only, in the Compose `journey` profile only; `server/` has no provider
selector, so this module is the only way a fake provider reaches a worker. No
network, no credentials: each claimed run is answered by
`RealisticLiteCompletions`, citing the pack's PDF among the run's pinned live
sources, at a fixed dated price. A run pinned to the insufficient pack instead
(`journey.pack.insufficient_pack`, the Phase 6 restricted case) is answered
with a validated CP-5 `Blocked`, so the route's own rule ends it BLOCKED: the
verdict is keyed on the evidence the run pinned, never on a switch.

`JOURNEY_EXIT_AFTER_FIRST_ACCEPT=1` (decision 12) makes the process
`os._exit(137)` once, after its first acceptance: at the next node's context
check, which the loop reaches only once the previous node's acceptance has
committed. A marker file under `JOURNEY_STATE_DIR` keeps the restarted
container from exiting again.
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Event
from uuid import UUID

import psycopg
from canonical_fixtures import QUOTE
from lite_route_fixtures import RealisticLiteCompletions

from journey.pack import INSUFFICIENT_NAME, PDF_NAME, insufficient_pack, journey_pack
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.runtime import Execution, Provider, ProviderResult
from server.engine.worker import (
    BLOB_ROOT,
    DATABASE_URL,
    VENDORED_BUNDLE,
    ExecutionFor,
    WorkerConfig,
    install_stop_handler,
    module_execution,
    run_worker,
)
from server.methodology.bundle import Bundle
from server.pricing import ModelPrice
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, apply_schema, connect
from server.store.outcomes import execution_reads
from server.store.source_sets import pinned_live_sources
from server.store.work import Lease

EXIT_AFTER_FIRST_ACCEPT = "JOURNEY_EXIT_AFTER_FIRST_ACCEPT"
STATE_DIR = "JOURNEY_STATE_DIR"
EXITED_MARKER = "journey-worker-exited-once"
KILLED = 137

# Input free; output priced so one call's worst case is 0.10 (as `priced` does).
JOURNEY_PRICE = ModelPrice(
    RealisticLiteCompletions.model,
    Decimal(0),
    Decimal("0.10") / 32_768,
    date(2026, 9, 14),
)

__all__ = ["JOURNEY_PRICE", "QUOTE", "completions_for", "journey_execution"]


def completions_for(sources: dict[str, UUID]) -> RealisticLiteCompletions:
    """The deterministic provider for the evidence in `sources` (document
    digest to source id): citing the pack's PDF with every module `Passed`
    when the certificate is pinned, citing the insufficient note with CP-5
    `Blocked` when only that is, or `ORCHESTRATION_SOURCE_NOT_PINNED`."""
    pdf = dict(journey_pack())[PDF_NAME]
    source_id = sources.get(hashlib.sha256(pdf).hexdigest())
    if source_id is not None:
        return RealisticLiteCompletions(source_id)
    note = dict(insufficient_pack())[INSUFFICIENT_NAME]
    source_id = sources.get(hashlib.sha256(note).hexdigest())
    if source_id is None:
        raise Refusal(RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED)
    return RealisticLiteCompletions(source_id, qa_by_module={"CP-5": "Blocked"})


@dataclass(slots=True)
class _ExitAfterFirstAccept:
    """Exits the process at the first context check after a call returned."""

    inner: Provider
    marker: Path
    returned: bool = False

    @property
    def model(self) -> str:
        return self.inner.model

    def check_context(self, route_node_id: str, module_id: str) -> None:
        if self.returned and not self.marker.exists():
            self.marker.write_text("exited\n", encoding="utf-8")
            os._exit(KILLED)
        self.inner.check_context(route_node_id, module_id)

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        result = self.inner.execute(route_node_id, module_id, attempt_id=attempt_id)
        self.returned = True
        return result


def journey_execution(
    bundle: Bundle, blobs: BlobStore, *, exit_marker: Path | None
) -> ExecutionFor:
    """Each claimed run executes through the real module provider, answered by
    `completions_for` its pinned live sources."""

    def execution_for(conn: StoreConnection, run_id: UUID, lease: Lease) -> Execution:
        with execution_reads(conn):
            sources = pinned_live_sources(conn, run_id)
        completions = completions_for(sources)
        execution = module_execution(completions, JOURNEY_PRICE, bundle, blobs)(
            conn, run_id, lease
        )
        if exit_marker is None:
            return execution
        provider = _ExitAfterFirstAccept(execution.provider, exit_marker)
        return Execution(provider, execution.price, execution.bundle, lease=lease)

    return execution_for


def main() -> int:
    """Configure from the environment, or print only the typed code and exit 2."""
    url, root = os.environ.get(DATABASE_URL), os.environ.get(BLOB_ROOT)
    marker: Path | None = None
    if os.environ.get(EXIT_AFTER_FIRST_ACCEPT) == "1":
        state = os.environ.get(STATE_DIR)
        if not state or not Path(state).is_dir():
            print("JOURNEY_STATE_DIR_NOT_CONFIGURED", file=sys.stderr)
            return 2
        marker = Path(state) / EXITED_MARKER
    if not url or not root:
        print(RefusalCode.STORE_NOT_CONFIGURED.value, file=sys.stderr)
        return 2
    try:
        bundle = Bundle(VENDORED_BUNDLE)
        bundle.verify_manifest()
        with connect(url) as conn:
            apply_schema(conn)
    except Refusal as refused:
        print(refused.code.value, file=sys.stderr)
        return 2
    except psycopg.Error:
        print(RefusalCode.STORE_UNAVAILABLE.value, file=sys.stderr)
        return 2
    stopping = Event()
    install_stop_handler(stopping)
    blobs = BlobStore(Path(root))
    return run_worker(
        WorkerConfig(BoundaryText.of(f"journey-worker-{os.getpid()}")),
        execution_for=journey_execution(bundle, blobs, exit_marker=marker),
        stopping=stopping,
        conn_factory=lambda: connect(url),
        blobs=blobs,
    )


if __name__ == "__main__":
    sys.exit(main())
