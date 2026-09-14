"""Qualification execution requires current stored identity and external approval."""

from dataclasses import asdict, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import psycopg
import pytest
from test_qualification_harness import (
    OTHER,
    _approve,
    _case,
    _Completions,
    _count,
)
from test_qualification_prepare import Fixture, ready

from server.boundary_text import BoundaryText
from server.evidence.ingest import admit_pack
from server.methodology.bundle import MANIFEST_NAME, Bundle
from server.provider import Completion
from server.qualification import harness as subject
from server.qualification.matrix import QualificationSet
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.gates import Gate, gate_preview, withdraw_source
from server.store.members import Standing, grant, revoke
from server.store.routes import pin_route, resolved_route
from server.store.run_inputs import RunInput, load_run_input, pin_run_input
from server.store.runs import start_run
from server.store.source_sets import snapshot_source_set

__all__ = ["ready"]


def test_legacy_perform_refuses_without_spending(ready: Fixture) -> None:
    conn, blobs, harness, qualification = ready
    stopped = None
    try:
        subject.perform(conn, blobs, harness, qualification=qualification)
    except Refusal as refused:
        stopped = refused.code
    observed = (
        stopped,
        len(cast(_Completions, harness.completions).prompts),
        _count(conn, "SELECT count(*) FROM run_attempts"),
        _count(conn, "SELECT count(*) FROM budget_reservations"),
    )
    assert observed == (RefusalCode.RUN_INPUT_INVALID, 0, 0, 0)
    assert _count(conn, "SELECT count(*) FROM cases") == 0
    assert _count(conn, "SELECT count(*) FROM runs") == 0


def _run(ready: Fixture, prepared: object) -> subject.PerformedSet:
    conn, blobs, harness, qualification = ready
    return subject.perform(
        conn,
        blobs,
        harness,
        qualification=qualification,
        prepared=cast(tuple[subject.PreparedCase, ...], prepared),
    )


def _prepared(ready: Fixture) -> tuple[subject.PreparedCase, ...]:
    conn, blobs, harness, qualification = ready
    return subject.prepare(conn, blobs, harness, qualification=qualification)


def _unspent(conn: StoreConnection, run: UUID | None = None) -> None:
    for table in (
        "run_attempts",
        "budget_reservations",
        "call_outcomes",
        "budget_ledger",
        "artifacts",
    ):
        assert (
            conn.execute(
                "SELECT 1 FROM " + table + (" WHERE run_id=%s" if run else ""),
                (run,) if run else (),
            ).fetchall()
            == []
        ), table
    conn.rollback()


def test_approved_captured_inputs_survive_later_catalog_and_source_changes(
    ready: Fixture,
) -> None:
    conn, blobs, harness, qualification = ready
    prepared = _prepared(ready)
    previews = [
        [gate_preview(conn, item.input.run_id, gate) for gate in Gate]
        for item in prepared
    ]
    conn.rollback()
    _approve(conn, prepared)
    pin = prepared[0].input
    added = admit_pack(
        conn,
        blobs,
        case_id=pin.case_id,
        documents=list(_case("extra", OTHER).documents),
    )
    conn.commit()
    snapshot_source_set(conn, pin.case_id)
    assert load_run_input(conn, pin.run_id) == pin
    assert [
        [gate_preview(conn, item.input.run_id, gate) for gate in Gate]
        for item in prepared
    ] == previews
    for item_previews in previews:
        for preview in item_previews:
            assert (
                sha256(preview.content.encode()).hexdigest() == preview.preview_sha256
            )
            assert conn.execute(
                "SELECT preview_sha256,input_fingerprint FROM run_gates"
                " WHERE run_id=%s AND gate=%s",
                (preview.run_id, preview.gate.value),
            ).fetchone() == (preview.preview_sha256, preview.input_fingerprint)
    conn.rollback()
    result = _run((conn, blobs, replace(harness, catalog={}), qualification), prepared)
    assert conn.info.transaction_status.name == "IDLE"
    assert result.matrix is not None and len(result.matrix.rows) == 2
    assert all(
        record.proof is not None and record.proof.artifacts == 2
        for record in result.performed
    )
    prompts = cast(_Completions, harness.completions).prompts
    assert len(prompts) == 4 and all(str(added[0]) not in prompt for prompt in prompts)


@pytest.mark.parametrize("field", list(RunInput.__dataclass_fields__))
def test_every_carrier_field_matches_the_stored_input(
    ready: Fixture, field: str
) -> None:
    conn, _, harness, _ = ready
    prepared = _prepared(ready)
    _approve(conn, prepared)
    a, b = prepared
    value = (
        uuid4()
        if field in {"run_id", "case_id"}
        else 2
        if field == "source_version"
        else "changed"
    )
    pin = replace(a.input, **{field: value})  # type: ignore[arg-type]
    changed = replace(a, input=pin)
    with pytest.raises(Refusal, match=r"^RUN_INPUT_INVALID$"):
        _run(ready, (changed, b))
    assert conn.info.transaction_status.name == "IDLE"
    assert cast(_Completions, harness.completions).prompts == []
    _unspent(conn)


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "length",
        "list",
        "tuple-subclass",
        "swapped",
        "run",
        "case",
        "run-string",
        "case-string",
        "label",
        "item",
        "input",
        "item-subclass",
        "input-subclass",
        "bool-version",
        "bundle",
    ],
)
def test_untrusted_carrier_shape_refuses_before_paid_work(
    ready: Fixture, fault: str
) -> None:
    conn, blobs, harness, qualification = ready
    prepared = _prepared(ready)
    _approve(conn, prepared)
    a, b = prepared
    candidates = {
        "none": None,
        "length": (a,),
        "list": list(prepared),
        "tuple-subclass": type("Carrier", (tuple,), {})(prepared),
        "swapped": (b, a),
        "run": (a, replace(b, input=replace(b.input, run_id=a.input.run_id))),
        "case": (a, replace(b, input=replace(b.input, case_id=a.input.case_id))),
        "run-string": (
            replace(a, input=replace(a.input, run_id=cast(UUID, str(a.input.run_id)))),
            b,
        ),
        "case-string": (
            replace(
                a, input=replace(a.input, case_id=cast(UUID, str(a.input.case_id)))
            ),
            b,
        ),
        "label": (replace(a, case_label="different"), b),
        "item": (SimpleNamespace(case_label=a.case_label, input=a.input), b),
        "input": (
            replace(a, input=cast(RunInput, SimpleNamespace(**asdict(a.input)))),
            b,
        ),
        "item-subclass": (
            type("CarrierItem", (subject.PreparedCase,), {})(a.case_label, a.input),
            b,
        ),
        "input-subclass": (
            replace(a, input=type("Pin", (RunInput,), {})(**asdict(a.input))),
            b,
        ),
        "bool-version": (replace(a, input=replace(a.input, source_version=True)), b),
    }
    if fault == "bundle":
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
    with pytest.raises(Refusal, match=r"^RUN_INPUT_INVALID$"):
        _run((conn, blobs, harness, qualification), candidates.get(fault, prepared))
    assert conn.info.transaction_status.name == "IDLE"
    assert cast(_Completions, harness.completions).prompts == []
    _unspent(conn)


@pytest.mark.parametrize(
    "fault",
    [
        "owner",
        "title",
        "budget",
        "research",
        "profile",
        "selection",
        "bytes",
        "filename",
        "multiplicity",
        "bundle",
    ],
)
def test_real_approved_input_transplants_are_refused(
    ready: Fixture, tmp_path: Path, fault: str
) -> None:
    conn, blobs, harness, qualification = ready
    a, b = _prepared(ready)
    original = qualification.cases[0]
    if fault in {"budget", "research"}:
        route = resolved_route(conn, a.input.run_id)
        assert route is not None
        run = start_run(
            conn,
            a.input.case_id,
            budget_ceiling=Decimal("6") if fault == "budget" else None,
        )
        conn.commit()
        pin_route(conn, run, route)
        a = replace(
            a,
            input=pin_run_input(
                conn,
                run,
                a.input.source_version,
                harness.bundle,
                {} if fault == "research" else None,
            ),
        )
    _approve(conn, (a, b))
    if fault == "owner":
        a = replace(a, input=replace(b.input, case_id=a.input.case_id))
    changed = {
        "title": replace(original, label="renamed"),
        "profile": replace(original, profile_id="OTHER"),
        "selection": replace(original, selection_id="BASELINE"),
        "bytes": _case(original.label, OTHER),
        "filename": replace(
            original,
            documents=(
                replace(original.documents[0], filename=BoundaryText.of("renamed.txt")),
            ),
        ),
        "multiplicity": replace(original, documents=original.documents * 2),
    }.get(fault, original)
    a = replace(a, case_label=changed.label)
    if fault == "bundle":
        raw = (harness.bundle.root / MANIFEST_NAME).read_text()
        (tmp_path / MANIFEST_NAME).write_text(
            raw.replace(harness.bundle.build_id, "d" * 64)
        )
        harness = replace(harness, bundle=Bundle(tmp_path))
    with pytest.raises(Refusal, match=r"^RUN_INPUT_INVALID$"):
        _run((conn, blobs, harness, QualificationSet((changed,))), (a,))
    assert conn.info.transaction_status.name == "IDLE"
    assert cast(_Completions, harness.completions).prompts == []
    _unspent(conn)


@pytest.mark.parametrize("later", [False, True])
@pytest.mark.parametrize("gate", list(Gate))
@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "preview_sha256",
        "input_fingerprint",
        "revoked",
        "downgraded",
        "withdrawn",
    ],
)
def test_current_authority_is_rechecked_before_each_case(
    ready: Fixture, monkeypatch: pytest.MonkeyPatch, later: bool, gate: Gate, fault: str
) -> None:
    conn, _, harness, _ = ready
    prepared = _prepared(ready)
    _approve(conn, prepared)
    actor = _approve(conn, prepared[1:], gates=(gate,))[0]
    pin = prepared[1].input

    def change() -> None:
        if fault == "missing":
            conn.execute(
                "DELETE FROM run_gates WHERE run_id=%s AND gate=%s",
                (pin.run_id, gate.value),
            )
        elif fault in {"preview_sha256", "input_fingerprint"}:
            conn.execute(
                psycopg.sql.SQL(
                    "UPDATE run_gates SET {}=%s WHERE run_id=%s AND gate=%s"
                ).format(psycopg.sql.Identifier(fault)),
                ("0" * 64, pin.run_id, gate.value),
            )
        elif fault == "revoked":
            revoke(conn, case_id=pin.case_id, user_id=actor)
        elif fault == "downgraded":
            grant(conn, case_id=pin.case_id, user_id=actor, standing=Standing.WRITER)
        else:
            source = conn.execute(
                "SELECT source_id FROM source_set_members"
                " WHERE case_id=%s AND version=%s",
                (pin.case_id, pin.source_version),
            ).fetchone()
            assert source is not None
            conn.rollback()
            withdraw_source(
                conn, case_id=pin.case_id, source_id=source[0], actor_id=actor
            )
        conn.commit()

    original = _Completions.complete

    def complete(
        provider: _Completions, prompt: str, *, json_object: bool = False
    ) -> Completion:
        result = original(provider, prompt, json_object=json_object)
        if len(provider.prompts) == 1:
            change()
        return result

    code = (
        RefusalCode.EVIDENCE_NOT_AVAILABLE
        if fault == "withdrawn"
        else RefusalCode.GATE_APPROVAL_MISMATCH
    )
    if later:
        monkeypatch.setattr(_Completions, "complete", complete)
        result = _run(ready, prepared)
        assert conn.info.transaction_status.name == "IDLE"
        first, second = result.performed
        assert (
            first.proof is not None
            and first.proof.artifacts == 2
            and first.stopped is None
        )
        assert second.run_id == pin.run_id and second.stopped is code
        assert second.status is RunStatus.RUNNING
        assert (
            second.proof is None
            and second.refusal is RefusalCode.ORCHESTRATION_NOTHING_TO_PROVE
        )
        assert len(second.unrun) == 2 and result.matrix is None
        assert _count(conn, "SELECT count(*) FROM budget_ledger") == 2
        assert _count(conn, "SELECT count(*) FROM artifacts") == 2
        assert len(cast(_Completions, harness.completions).prompts) == 2
        sources = conn.execute(
            "SELECT source_id FROM source_set_members WHERE case_id=%s", (pin.case_id,)
        ).fetchall()
        assert sources and all(
            str(source[0]) not in prompt
            for source in sources
            for prompt in cast(_Completions, harness.completions).prompts
        )
        _unspent(conn, pin.run_id)
    else:
        change()
        with pytest.raises(Refusal, match=f"^{code.value}$"):
            _run(ready, prepared)
        assert conn.info.transaction_status.name == "IDLE"
        assert cast(_Completions, harness.completions).prompts == []
        _unspent(conn)
