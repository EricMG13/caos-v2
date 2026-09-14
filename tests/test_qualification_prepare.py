"""Preparation pins inputs without granting approval or executing any run."""

import json
from collections.abc import Iterator
from dataclasses import asdict, replace
from decimal import ROUND_DOWN, Decimal, localcontext
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import psycopg
import pytest
from conftest import priced
from test_qualification_harness import (
    CATALOG,
    ESTIMATE,
    OTHER,
    REPORT,
    SET_CEILING,
    VENDORED,
    _case,
    _Completions,
    _count,
)

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import resolve_route
from server.methodology.bundle import Bundle
from server.qualification import harness as subject
from server.qualification.matrix import QualificationSet
from server.refusals import Refusal
from server.store import StoreConnection, apply_schema, connect
from server.store.budget import CEILING
from server.store.gates import Gate, GateState, gate_preview, gate_state
from server.store.routes import resolved_route
from server.store.run_inputs import load_run_input
from server.store.runs import create_case
from server.store.source_sets import load_source_set

Fixture = tuple[StoreConnection, BlobStore, subject.Harness, QualificationSet]


@pytest.fixture
def ready(empty_database: str, tmp_path: Path) -> Iterator[Fixture]:
    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        yield (
            conn,
            BlobStore(tmp_path / "blobs"),
            subject.Harness(
                Bundle(VENDORED), CATALOG, _Completions(), priced(ESTIMATE), SET_CEILING
            ),
            QualificationSet((_case("first", REPORT), _case("second", OTHER))),
        )


def _unapproved_and_unspent(conn: StoreConnection, harness: subject.Harness) -> None:
    for table in (
        "case_members",
        "run_gates",
        "audit_events",
        "run_attempts",
        "budget_reservations",
        "call_outcomes",
        "budget_ledger",
        "artifacts",
    ):
        assert _count(conn, "SELECT count(*) FROM " + table) == 0, table
    assert cast(_Completions, harness.completions).prompts == []
    conn.rollback()


@pytest.mark.parametrize("precision", [28, 1])
def test_aggregate_ceiling_is_exact_under_decimal_context(precision: int) -> None:
    qualification = QualificationSet(tuple(_case(str(i), REPORT) for i in range(3)))
    harness = subject.Harness(
        Bundle(VENDORED), CATALOG, _Completions(), priced(ESTIMATE), Decimal("10")
    )
    with localcontext() as context:
        context.prec, context.rounding = precision, ROUND_DOWN
        with pytest.raises(Refusal, match=r"^QUALIFICATION_SET_OVER_CEILING$"):
            subject._affordable(qualification, harness, ())
        subject._affordable(qualification, replace(harness, ceiling=Decimal("15")), ())


def test_a_price_whose_route_cannot_fit_a_run_is_refused_before_any_case(
    ready: Fixture,
) -> None:
    """Every node reserves one worst case against its run's ceiling, so a
    two-node route priced above half the ceiling would pay for a call it could
    never finish (the whole-phase confidence review's F-1)."""
    conn, blobs, harness, qualification = ready
    half = replace(harness, price=priced(CEILING / 2 + Decimal("0.01")))
    route = resolve_route(CATALOG, qualification.cases[0].profile_id, "DEEP_RESEARCH")
    # Exact whatever the ambient precision (the whole-phase audit's W-1).
    with localcontext() as context:
        context.prec = 1
        with pytest.raises(Refusal, match=r"^QUALIFICATION_SET_OVER_CEILING$"):
            subject._affordable(qualification, half, [route])
    with pytest.raises(Refusal, match=r"^QUALIFICATION_SET_OVER_CEILING$"):
        subject.prepare(conn, blobs, half, qualification=qualification)
    assert _count(conn, "SELECT count(*) FROM cases") == 0
    _unapproved_and_unspent(conn, half)


@pytest.mark.parametrize(
    "ceiling",
    [
        10,
        True,
        "10",
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("-1"),
    ],
)
def test_invalid_ceiling_refuses_before_preparation(
    ready: Fixture, ceiling: object
) -> None:
    conn, blobs, harness, qualification = ready
    code = "MONEY_INVALID" if isinstance(ceiling, Decimal) else "MONEY_NOT_DECIMAL"
    with pytest.raises(Refusal, match=f"^{code}$"):
        subject.prepare(
            conn,
            blobs,
            replace(harness, ceiling=cast(Decimal, ceiling)),
            qualification=qualification,
        )
    assert conn.info.transaction_status.name == "IDLE"
    assert _count(conn, "SELECT count(*) FROM cases") == 0
    _unapproved_and_unspent(conn, harness)


def test_preparation_creates_exact_inputs_and_external_previews(ready: Fixture) -> None:
    conn, blobs, harness, qualification = ready
    prepared = subject.prepare(conn, blobs, harness, qualification=qualification)
    assert conn.info.transaction_status.name == "IDLE"
    assert isinstance(prepared, tuple) and len(prepared) == 2
    assert len({item.input.case_id for item in prepared}) == 2
    assert len({item.input.run_id for item in prepared}) == 2
    for item, case in zip(prepared, qualification.cases, strict=True):
        assert isinstance(item, subject.PreparedCase)
        pin = item.input
        assert item.case_label == case.label
        assert pin == load_run_input(conn, pin.run_id)
        assert pin.research_json is None and pin.source_version == 1
        assert conn.execute(
            "SELECT c.title, r.budget_ceiling, r.status FROM runs r"
            " JOIN cases c USING(case_id) WHERE r.run_id=%s AND c.case_id=%s",
            (pin.run_id, pin.case_id),
        ).fetchone() == (case.label, CEILING, "RUNNING")
        source = load_source_set(conn, pin.case_id, pin.source_version)
        assert source is not None and source.fingerprint == pin.source_fingerprint
        assert sorted(
            (m.filename, m.document_sha256) for m in source.members
        ) == sorted(
            (d.filename.value, sha256(d.data).hexdigest()) for d in case.documents
        )
        route = resolved_route(conn, pin.run_id)
        assert route == resolve_route(CATALOG, case.profile_id, case.selection_id)
        assert route is not None
        for gate in Gate:
            preview = gate_preview(conn, pin.run_id, gate)
            expected: dict[str, object] = {
                "format_version": 1,
                "gate": gate.value,
                "input": {
                    **asdict(pin),
                    "run_id": str(pin.run_id),
                    "case_id": str(pin.case_id),
                },
            }
            if gate is Gate.SOURCE_SET:
                expected["sources"] = [
                    {**asdict(m), "source_id": str(m.source_id)} for m in source.members
                ]
            else:
                expected["route"] = asdict(route)
            assert preview.content == json.dumps(
                expected, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2
            )
            assert (
                preview.preview_sha256 == sha256(preview.content.encode()).hexdigest()
            )
            assert preview.input_fingerprint == pin.input_fingerprint
            assert gate_state(conn, pin.run_id, gate) is GateState.OPEN
        assert blobs.get(source.members[0].document_sha256) == case.documents[0].data
    _unapproved_and_unspent(conn, harness)


@pytest.mark.parametrize(
    "fault,code",
    [
        ("empty", "QUALIFICATION_SET_EMPTY"),
        ("documents", "QUALIFICATION_SET_EMPTY"),
        ("expects", "QUALIFICATION_SET_EMPTY"),
        ("duplicate", "QUALIFICATION_SET_AMBIGUOUS"),
        ("unanswerable", "QUALIFICATION_KEY_UNANSWERABLE"),
        ("route", "ROUTE_SELECTION_UNKNOWN"),
        ("label", "BOUNDARY_TEXT_TOO_LONG"),
        ("control", "BOUNDARY_TEXT_INVALID"),
        ("ceiling", "QUALIFICATION_SET_OVER_CEILING"),
        ("bundle", "RUN_INPUT_INVALID"),
    ],
)
def test_whole_set_pure_defects_leave_no_setup(
    ready: Fixture, fault: str, code: str
) -> None:
    conn, blobs, harness, qualification = ready
    first, second = qualification.cases
    changes = {
        "documents": replace(second, documents=()),
        "expects": replace(second, expects=()),
        "duplicate": replace(second, label=first.label),
        "unanswerable": replace(second, expects=first.expects),
        "route": replace(second, selection_id="NO_SUCH_PATHWAY"),
        "label": replace(second, label="x" * 129),
        "control": replace(second, label="bad\x00label"),
    }
    qualification = QualificationSet(
        () if fault == "empty" else (first, changes.get(fault, second))
    )
    if fault == "ceiling":
        harness = replace(harness, ceiling=CEILING)
    elif fault == "bundle":
        harness = replace(
            harness,
            bundle=cast(
                Bundle,
                SimpleNamespace(
                    build_id=harness.bundle.build_id,
                    manifest_sha256=harness.bundle.manifest_sha256,
                ),
            ),
        )
    with pytest.raises(Refusal, match=f"^{code}$"):
        subject.prepare(conn, blobs, harness, qualification=qualification)
    assert conn.info.transaction_status.name == "IDLE"
    assert _count(conn, "SELECT count(*) FROM cases") == 0
    assert not blobs.root.exists()
    _unapproved_and_unspent(conn, harness)


@pytest.mark.parametrize(
    "mode", ["pending", "autocommit", "repeatable", "serializable"]
)
def test_preparation_requires_idle_read_committed_entry(
    ready: Fixture,
    empty_database: str,
    mode: str,
) -> None:
    conn, blobs, harness, qualification = ready
    if mode == "pending":
        pending = create_case(conn, BoundaryText.of("caller work"))
    elif mode == "autocommit":
        conn.autocommit = True
    else:
        conn.isolation_level = (
            psycopg.IsolationLevel.REPEATABLE_READ
            if mode == "repeatable"
            else psycopg.IsolationLevel.SERIALIZABLE
        )
    with pytest.raises(Refusal, match=r"^STORE_NOT_TRANSACTIONAL$"):
        subject.prepare(conn, blobs, harness, qualification=qualification)
    if mode == "pending":
        assert conn.info.transaction_status.name == "INTRANS"
        assert conn.execute(
            "SELECT title FROM cases WHERE case_id=%s", (pending,)
        ).fetchone() == ("caller work",)
        with connect(empty_database) as observer:
            assert (
                observer.execute(
                    "SELECT 1 FROM cases WHERE case_id=%s", (pending,)
                ).fetchone()
                is None
            )
    else:
        assert conn.info.transaction_status.name == "IDLE"
    conn.rollback()
    conn.autocommit = False
    assert _count(conn, "SELECT count(*) FROM cases") == 0
    _unapproved_and_unspent(conn, harness)


@pytest.mark.parametrize("stage", ["extraction", "setup", "snapshot", "route", "input"])
def test_later_preparation_failure_keeps_prior_commits(
    ready: Fixture,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    conn, blobs, harness, qualification = ready
    first, second = qualification.cases
    if stage == "extraction":
        qualification = QualificationSet((first, _case(second.label, b" \n\t")))
    prefix = {
        "setup": "INSERT INTO runs",
        "snapshot": "INSERT INTO source_set_versions",
        "route": "INSERT INTO run_routes",
        "input": "INSERT INTO run_inputs",
    }.get(stage)
    execute = psycopg.Connection.execute
    calls = 0

    def fail_second(
        c: StoreConnection, query: str, *args: object, **kwargs: object
    ) -> object:
        nonlocal calls
        if prefix is not None and query.startswith(prefix):
            calls += 1
            if calls == 2:
                return execute(c, "SELECT missing_qualification_column")
        return execute(c, query, *args, **kwargs)  # type: ignore[arg-type]

    with monkeypatch.context() as patch:
        patch.setattr(psycopg.Connection, "execute", fail_second)
        code = "SOURCE_HAS_NO_TEXT" if stage == "extraction" else "STORE_UNAVAILABLE"
        with pytest.raises(Refusal, match=f"^{code}$") as caught:
            subject.prepare(conn, blobs, harness, qualification=qualification)
    assert caught.value.__cause__ is None
    assert conn.info.transaction_status.name == "IDLE"
    prior = conn.execute(
        "SELECT r.run_id FROM runs r JOIN cases c USING(case_id) WHERE c.title=%s",
        (first.label,),
    ).fetchone()
    assert prior is not None and load_run_input(conn, prior[0]) is not None
    assert blobs.get(sha256(REPORT).hexdigest()) == REPORT
    committed_setup = 1 if stage in {"extraction", "setup"} else 2
    assert _count(conn, "SELECT count(*) FROM cases") == committed_setup
    assert _count(conn, "SELECT count(*) FROM runs") == committed_setup
    assert _count(conn, "SELECT count(*) FROM source_set_versions") == (
        2 if stage in {"route", "input"} else 1
    )
    assert _count(conn, "SELECT count(*) FROM run_routes") == (
        2 if stage == "input" else 1
    )
    assert _count(conn, "SELECT count(*) FROM run_inputs") == 1
    if stage != "extraction":
        assert blobs.get(sha256(OTHER).hexdigest()) == OTHER
    _unapproved_and_unspent(conn, harness)
