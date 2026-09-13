"""Phase 4 exit test: recovery is recomputation, not restoration.

`docs/DECISIONS.md` §3: execution state *is* the accepted-attempt ledger. There
is no checkpointer, so there is nothing to restore and nothing that can disagree
with the domain state -- which is where most of the predecessor's recovery
machinery came from.

A process that dies mid-run leaves accepted attempts behind. The next one
recomputes `node_states` over exactly those rows and continues from the frontier
that falls out. A node that completed is not run again, because it is COMPLETE,
not because anything remembered that it was.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from conftest import _url_for, approve_run
from psycopg.pq import TransactionStatus

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine import runtime as subject
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import (
    Execution,
    Provider,
    ProviderResult,
    accepted_artifacts,
    artifact_digests,
    run_route,
)
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import MANIFEST_NAME, Bundle
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, connect
from server.store.budget import reserve as reserve_budget
from server.store.events import RunEvent, events_of
from server.store.gates import Gate, withdraw_source
from server.store.members import Standing, grant, revoke
from server.store.routes import pin_route
from server.store.runs import run_status, start_run

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor/deploy-v/skills/cp-os-credit-os/references"
    / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
)
PROFILE = "FULL_CREDIT_32"
# Four nodes: CP-0, CP-1, CP-2, CP-2D. Small enough to count attempts by hand.
SELECTION = "LIQUIDITY_REVIEW"
ESTIMATE = Decimal("0.10")

# CP-0's artifact says every module's evidence is there, so no soft edge is left
# soft and the route runs straight through.
READY_EVERYWHERE: dict[str, Any] = {
    "content_to_module_map": [
        {"module_id": module, "readiness_status": "READY"}
        for module in ("CP-1", "CP-2", "CP-2D")
    ]
}


class _Boom(Exception):
    """A process death, in the only form a test can arrange."""


@dataclass
class _Provider:
    """Records what it was asked for, and can die on a chosen node."""

    blobs: BlobStore
    die_on: str | None = None
    at_call: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        self.calls: list[str] = []

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        self.calls.append(module_id)
        if self.at_call is not None:
            self.at_call()
        if module_id == self.die_on:
            raise _Boom(module_id)
        payload: dict[str, Any] = (
            READY_EVERYWHERE if module_id == "CP-0" else {"module_id": module_id}
        )
        digest = self.blobs.put(json.dumps(payload).encode("utf-8"))
        return ProviderResult(
            artifact_sha256=digest,
            charge=Decimal("0.01"),
            model="a-model/for-the-test",
            generation_id="gen-runtime-test",
        )


def test_the_fake_provider_satisfies_the_protocol(blobs: BlobStore) -> None:
    """`Provider` is the seam Phase 5 fills with a real OpenRouter call. If the
    stand-in here did not satisfy it, these tests would be exercising a shape
    the real provider will not have."""
    provider: Provider = _Provider(blobs)

    result = provider.execute("RN-x", "CP-1", attempt_id=uuid4())

    assert result.artifact_sha256
    assert result.charge == Decimal("0.01")


@pytest.fixture
def route() -> ResolvedRoute:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return resolve_route(catalog, PROFILE, SELECTION)


@pytest.fixture
def blobs(tmp_path: Path) -> BlobStore:
    return BlobStore(tmp_path / "blobs")


@pytest.fixture
def bundle() -> Bundle:
    return Bundle(CATALOG_PATH.parents[3])


def _approved_run(  # noqa: PLR0913
    conn: StoreConnection,
    case_id: UUID,
    route: ResolvedRoute,
    bundle: Bundle,
    blobs: BlobStore,
    *,
    ceiling: Decimal | None = None,
) -> UUID:
    admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[
            Document(filename=BoundaryText.of("runtime.txt"), data=b"runtime input\n")
        ],
    )
    run_id = start_run(conn, case_id, budget_ceiling=ceiling)
    conn.commit()
    approve_run(conn, case_id=case_id, run_id=run_id, route=route, bundle=bundle)
    return run_id


def _attempts_per_module(conn: StoreConnection, run_id: UUID) -> dict[str, int]:
    rows = conn.execute(
        "SELECT route_node_id, count(*) FROM run_attempts"
        " WHERE run_id = %s GROUP BY route_node_id",
        (run_id,),
    ).fetchall()
    return {str(node_id): int(count) for node_id, count in rows}


_WORK_TABLES = (
    "run_attempts",
    "budget_reservations",
    "call_outcomes",
    "budget_ledger",
    "artifacts",
)


def _assert_no_work(conn: StoreConnection, run_id: UUID) -> None:
    for table in _WORK_TABLES:
        assert conn.execute(
            "SELECT count(*) FROM " + table + " WHERE run_id=%s", (run_id,)
        ).fetchone() == (0,), table


def test_an_unapproved_run_never_reaches_the_provider(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    provider = _Provider(blobs, die_on="CP-0")

    with pytest.raises(Refusal, match=r"^RUN_INPUT_INVALID$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert provider.calls == []
    _assert_no_work(conn, run_id)


def test_a_historical_route_without_a_complete_input_never_reaches_the_provider(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    pin_route(conn, run_id, route)
    provider = _Provider(blobs)

    with pytest.raises(Refusal, match=r"^RUN_INPUT_INVALID$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert provider.calls == []
    _assert_no_work(conn, run_id)


@pytest.mark.parametrize("gate", list(Gate))
@pytest.mark.parametrize("fault", ["missing", "preview", "input"])
def test_each_current_gate_is_required_before_work(  # noqa: PLR0913
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
    gate: Gate,
    fault: str,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    if fault == "missing":
        conn.execute(
            "DELETE FROM run_gates WHERE run_id=%s AND gate=%s", (run_id, gate)
        )
    else:
        column = "preview_sha256" if fault == "preview" else "input_fingerprint"
        conn.execute(
            psycopg.sql.SQL(
                "UPDATE run_gates SET {}=%s WHERE run_id=%s AND gate=%s"
            ).format(psycopg.sql.Identifier(column)),
            ("0" * 64, run_id, gate),
        )
    conn.commit()
    provider = _Provider(blobs)

    with pytest.raises(Refusal, match=r"^GATE_APPROVAL_MISMATCH$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert provider.calls == []
    _assert_no_work(conn, run_id)


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("revoked", RefusalCode.GATE_APPROVAL_MISMATCH),
        ("downgraded", RefusalCode.GATE_APPROVAL_MISMATCH),
        ("withdrawn", RefusalCode.EVIDENCE_NOT_AVAILABLE),
    ],
)
def test_live_authority_is_required_before_work(  # noqa: PLR0913
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
    change: str,
    code: RefusalCode,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    actor = conn.execute(
        "SELECT DISTINCT approved_by FROM run_gates WHERE run_id=%s", (run_id,)
    ).fetchone()
    assert actor is not None
    actor_id = UUID(str(actor[0]))
    if change == "revoked":
        revoke(conn, case_id=case_id, user_id=actor_id)
        conn.commit()
    elif change == "downgraded":
        grant(conn, case_id=case_id, user_id=actor_id, standing=Standing.READER)
        conn.commit()
    else:
        source = conn.execute(
            "SELECT source_id FROM live_sources WHERE case_id=%s", (case_id,)
        ).fetchone()
        assert source is not None
        withdraw_source(
            conn, case_id=case_id, source_id=UUID(str(source[0])), actor_id=actor_id
        )
    provider = _Provider(blobs)

    with pytest.raises(Refusal, match=f"^{code.value}$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert provider.calls == []
    _assert_no_work(conn, run_id)


def test_the_final_pre_call_check_sees_a_late_revocation(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    actor = conn.execute(
        "SELECT DISTINCT approved_by FROM run_gates WHERE run_id=%s", (run_id,)
    ).fetchone()
    assert actor is not None
    conn.rollback()
    original = reserve_budget
    reservations = 0

    def reserve_then_revoke(
        connection: StoreConnection, attempt_id: UUID, amount: Decimal
    ) -> None:
        nonlocal reservations
        original(connection, attempt_id, amount)
        reservations += 1
        if reservations == 2:
            revoke(connection, case_id=case_id, user_id=UUID(str(actor[0])))
            connection.commit()

    monkeypatch.setattr(subject, "reserve", reserve_then_revoke)
    provider = _Provider(blobs)

    with pytest.raises(Refusal, match=r"^GATE_APPROVAL_MISMATCH$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert provider.calls == ["CP-0"]
    assert conn.execute(
        "SELECT count(*) FROM run_attempts WHERE run_id=%s", (run_id,)
    ).fetchone() == (2,)
    assert conn.execute(
        "SELECT count(*) FROM budget_reservations WHERE run_id=%s", (run_id,)
    ).fetchone() == (2,)
    assert conn.execute(
        "SELECT count(*) FROM artifacts WHERE run_id=%s", (run_id,)
    ).fetchone() == (1,)


def test_provider_transport_is_idle_and_holds_no_case_or_run_lock(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)

    def unlocked() -> None:
        assert conn.info.transaction_status is TransactionStatus.IDLE
        with connect(_url_for(conn.info.dbname)) as observer:
            observer.execute(
                "SELECT 1 FROM cases WHERE case_id=%s FOR UPDATE NOWAIT", (case_id,)
            )
            observer.execute(
                "SELECT 1 FROM runs WHERE run_id=%s FOR UPDATE NOWAIT", (run_id,)
            )
            observer.rollback()

    provider = _Provider(blobs, at_call=unlocked)
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(provider, ESTIMATE, bundle),
    )

    assert provider.calls == ["CP-0", "CP-1", "CP-2", "CP-2D"]


@pytest.mark.parametrize(
    "mode", ["pending", "autocommit", "repeatable", "serializable"]
)
def test_runtime_entry_preserves_caller_transaction_ownership(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
    mode: str,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    if mode == "pending":
        conn.execute("CREATE TABLE caller_work (id integer)")
    elif mode == "autocommit":
        conn.autocommit = True
    else:
        conn.isolation_level = (
            psycopg.IsolationLevel.REPEATABLE_READ
            if mode == "repeatable"
            else psycopg.IsolationLevel.SERIALIZABLE
        )
    provider = _Provider(blobs)

    with pytest.raises(Refusal, match=r"^STORE_NOT_TRANSACTIONAL$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert provider.calls == []
    if mode == "pending":
        assert conn.info.transaction_status is TransactionStatus.INTRANS
        assert conn.execute("SELECT to_regclass('caller_work')").fetchone() == (
            "caller_work",
        )
    else:
        assert conn.info.transaction_status is TransactionStatus.IDLE
    conn.rollback()
    conn.autocommit = False
    conn.isolation_level = None
    _assert_no_work(conn, run_id)


@pytest.mark.parametrize("wrong", ["route", "bundle"])
def test_caller_identity_cannot_replace_stored_authority(  # noqa: PLR0913
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
    tmp_path: Path,
    wrong: str,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    requested = route
    executing = bundle
    code = RefusalCode.ROUTE_IDENTITY_INVALID
    if wrong == "route":
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        requested = resolve_route(catalog, PROFILE, "DEEP_RESEARCH")
    else:
        raw = (bundle.root / MANIFEST_NAME).read_text(encoding="utf-8")
        (tmp_path / MANIFEST_NAME).write_text(
            raw.replace(bundle.build_id, "d" * 64), encoding="utf-8"
        )
        executing = Bundle(tmp_path)
        code = RefusalCode.RUN_INPUT_INVALID
    provider = _Provider(blobs)

    with pytest.raises(Refusal, match=f"^{code.value}$"):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=requested,
            execution=Execution(provider, ESTIMATE, executing),
        )

    assert provider.calls == []
    _assert_no_work(conn, run_id)


def test_a_route_runs_to_completion(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    provider = _Provider(blobs)

    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(provider, ESTIMATE, bundle),
    )

    assert provider.calls == ["CP-0", "CP-1", "CP-2", "CP-2D"]
    assert run_status(conn, run_id) is RunStatus.COMPLETE
    assert [e.name for e in events_of(conn, run_id)].count(
        RunEvent.RUN_COMPLETE.value
    ) == 1


def test_recovery_is_recomputation(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """The Phase 4 exit test. Kill mid-run, restart, and the run completes
    without restarting completed nodes and without a checkpoint file."""
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)

    dying = _Provider(blobs, die_on="CP-2")
    with pytest.raises(_Boom):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(dying, ESTIMATE, bundle),
        )

    assert dying.calls == ["CP-0", "CP-1", "CP-2"]
    assert run_status(conn, run_id) is RunStatus.RUNNING
    before = _attempts_per_module(conn, run_id)

    # The restart. Nothing was restored: node_states is recomputed over the rows
    # that survived, and the frontier falls out of them.
    restarted = _Provider(blobs)
    conn.rollback()
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(restarted, ESTIMATE, bundle),
    )

    assert restarted.calls == ["CP-2", "CP-2D"], "completed nodes are not run again"
    assert run_status(conn, run_id) is RunStatus.COMPLETE

    after = _attempts_per_module(conn, run_id)
    completed_before = [
        node_id
        for node_id, count in before.items()
        if node_id != _node_id(route, "CP-2")
    ]
    for node_id in completed_before:
        assert after[node_id] == 1, "an accepted node was attempted a second time"


def test_no_checkpoint_is_written_anywhere(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """`docs/DECISIONS.md` §3: no checkpointer. The store's own tables are the
    execution state, so there is no second place for it to disagree from."""
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)

    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(_Provider(blobs), ESTIMATE, bundle),
    )

    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = current_schema()"
    ).fetchall()
    assert not [name for (name,) in tables if "checkpoint" in str(name)]


def test_a_failed_attempt_leaves_its_row_and_its_reservation(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """One attempt row per try. The row and the reservation outlive the failure,
    because the call may have reached the provider and may be billed."""
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)

    with pytest.raises(_Boom):
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(_Provider(blobs, die_on="CP-1"), ESTIMATE, bundle),
        )

    row = conn.execute(
        "SELECT count(*) FROM budget_reservations WHERE run_id = %s", (run_id,)
    ).fetchone()
    assert row is not None
    assert row[0] == 2, "CP-0 and the failed CP-1 both reserved"


def test_the_run_stops_when_the_ceiling_is_reached(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """Invariant 8 reaching the loop: the next node is refused, not attempted."""
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs, ceiling=Decimal("0.15"))
    provider = _Provider(blobs)

    with pytest.raises(Refusal) as caught:
        run_route(
            conn,
            blobs,
            run_id=run_id,
            route=route,
            execution=Execution(provider, ESTIMATE, bundle),
        )

    assert caught.value.code is RefusalCode.BUDGET_CEILING_REACHED
    assert provider.calls == ["CP-0"], "the second node never reached the provider"


def test_accepted_artifacts_reads_cp0s_payload_and_no_other(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """`node_states` needs CP-0's readiness and nothing else's body, so nothing
    else's body is fetched from the blob store."""
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(_Provider(blobs), ESTIMATE, bundle),
    )

    accepted = accepted_artifacts(conn, blobs, route=route, run_id=run_id)

    assert accepted[_node_id(route, "CP-0")] == READY_EVERYWHERE
    assert accepted[_node_id(route, "CP-1")] == {}


def test_artifact_digests_maps_accepted_attempts_to_their_digest(
    case: tuple[StoreConnection, UUID],
    route: ResolvedRoute,
    blobs: BlobStore,
    bundle: Bundle,
) -> None:
    """The join `accepted_artifacts` above and `executor._upstream_digests`
    both read now lives in this one function -- proved here in isolation from
    either caller, since a test that only ever saw it through one of them could
    not tell a coincidence from the shared row set the fix depends on."""
    conn, case_id = case
    run_id = _approved_run(conn, case_id, route, bundle, blobs)

    assert artifact_digests(conn, run_id) == {}, "nothing accepted yet"
    conn.rollback()

    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=route,
        execution=Execution(_Provider(blobs), ESTIMATE, bundle),
    )

    digests = artifact_digests(conn, run_id)
    assert set(digests) == {
        _node_id(route, module) for module in ("CP-0", "CP-1", "CP-2", "CP-2D")
    }
    assert json.loads(blobs.get(digests[_node_id(route, "CP-0")])) == READY_EVERYWHERE


def _node_id(route: ResolvedRoute, module_id: str) -> str:
    return next(n.route_node_id for n in route.nodes if n.module_id == module_id)
