"""The orchestration proof over canonical artifacts (Task 3.1 slice d-2; §42.4).

A LITE run completed through `run_route` proves; then each thing the proof
re-derives is moved under it -- a blob, the binding, a projection, a pinned
source, a rectangle, the build -- and it refuses with the claim that failed and
no text in the exception chain.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

import pytest
from canonical_fixtures import CanonicalCompletions
from conftest import priced
from test_canonical_execution import _node, harness, route
from test_execution_freshness import _Harness
from test_loop_charges import ESTIMATE
from test_orchestration_proof import _token_fault

from server import methodology
from server.boundary_text import BoundaryText
from server.engine.runtime import Execution, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.handoff import CanonicalRecord, _decoded_record, record_bytes
from server.methodology.runner import ModuleProvider
from server.qualification import Assurance
from server.qualification.proof import OrchestrationProof, assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store.gates import withdraw_source
from server.store.members import Standing, grant

__all__ = ["harness", "route"]

MISMATCH = RefusalCode.ARTIFACT_RECORD_MISMATCH


@pytest.fixture
def ran(harness: _Harness) -> _Harness:
    provider = ModuleProvider(
        harness.conn,
        harness.bundle,
        harness.blobs,
        CanonicalCompletions(harness.source_id),
        harness.route,
        harness.run_id,
    )
    run_route(
        harness.conn,
        harness.blobs,
        run_id=harness.run_id,
        route=harness.route,
        execution=Execution(provider, priced(ESTIMATE), harness.bundle),
    )
    return harness


def _prove(ran: _Harness) -> OrchestrationProof:
    proof = assert_orchestration_proof(
        ran.conn, ran.blobs, ran.bundle, run_id=ran.run_id
    )
    ran.conn.rollback()
    return proof


def _refusal(ran: _Harness) -> RefusalCode:
    with pytest.raises(Refusal) as caught:
        _prove(ran)
    ran.conn.rollback()
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    return caught.value.code


def _stored(ran: _Harness, module_id: str) -> tuple[UUID, str, str]:
    row = ran.conn.execute(
        "SELECT attempt_id, artifact_sha256, record_sha256 FROM artifacts"
        " WHERE route_node_id = %s",
        (_node(ran, module_id).route_node_id,),
    ).fetchone()
    assert row is not None
    return UUID(str(row[0])), str(row[1]), str(row[2])


def _set(ran: _Harness, module_id: str, column: str, value: str | None) -> None:
    attempt, _artifact, _record = _stored(ran, module_id)
    assert column in {"artifact_sha256", "record_sha256"}
    ran.conn.execute(
        f"UPDATE artifacts SET {column} = %s WHERE attempt_id = %s",
        (value, attempt),
    )
    ran.conn.commit()


def _rewrite(
    ran: _Harness, module_id: str, change: Callable[[CanonicalRecord], CanonicalRecord]
) -> None:
    """Store a canonical, correctly bound record that says something else."""
    _attempt, _artifact, record = _stored(ran, module_id)
    changed = change(_decoded_record(ran.blobs.get(record)))
    _set(ran, module_id, "record_sha256", ran.blobs.put(record_bytes(changed)))


def test_a_lite_run_completed_through_the_runtime_proves(ran: _Harness) -> None:
    proof = _prove(ran)
    assert proof.assurance is Assurance.ORCHESTRATION_PROOF
    assert (proof.run_id, proof.build_id) == (ran.run_id, ran.bundle.build_id)
    assert (proof.artifacts, proof.citations) == (3, 3)


def test_a_changed_markdown_blob_refuses(ran: _Harness) -> None:
    _attempt, artifact, _record = _stored(ran, "CP-5")
    changed = ran.blobs.put(ran.blobs.get(artifact) + b"\n")
    _set(ran, "CP-5", "artifact_sha256", changed)
    assert _refusal(ran) is MISMATCH


@pytest.mark.parametrize("which", ["markdown", "record"])
def test_bytes_damaged_under_their_address_are_unreadable(
    ran: _Harness, which: str
) -> None:
    _attempt, artifact, record = _stored(ran, "CP-L10")
    path = ran.blobs.path_of(artifact if which == "markdown" else record)
    path.chmod(0o644)
    path.write_bytes(b"damaged")
    assert _refusal(ran) is RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE


def test_a_changed_record_blob_refuses(ran: _Harness) -> None:
    _attempt, _artifact, record = _stored(ran, "CP-L10")
    _set(ran, "CP-L10", "record_sha256", ran.blobs.put(ran.blobs.get(record) + b" "))
    assert _refusal(ran) is MISMATCH


def test_a_canonical_artifact_without_its_record_refuses(ran: _Harness) -> None:
    _set(ran, "CP-5", "record_sha256", None)
    assert _refusal(ran) is MISMATCH


def test_a_projection_the_markdown_does_not_say_refuses(ran: _Harness) -> None:
    def lying(record: CanonicalRecord) -> CanonicalRecord:
        readiness = (("CP-5", "READY"),)
        return replace(
            record, projections=replace(record.projections, readiness=readiness)
        )

    _rewrite(ran, "CP-0", lying)
    assert _refusal(ran) is MISMATCH


def test_an_identity_the_store_no_longer_holds_refuses(ran: _Harness) -> None:
    attempt, _artifact, _record = _stored(ran, "CP-5")
    ran.conn.execute(
        "UPDATE run_attempts SET ordinal = ordinal + 1 WHERE attempt_id = %s",
        (attempt,),
    )
    ran.conn.commit()
    assert _refusal(ran) is MISMATCH


def test_a_withdrawn_pinned_source_takes_the_proof_with_it(ran: _Harness) -> None:
    actor = uuid4()
    grant(ran.conn, case_id=ran.case_id, user_id=actor, standing=Standing.APPROVER)
    ran.conn.commit()
    withdraw_source(
        ran.conn, case_id=ran.case_id, actor_id=actor, source_id=ran.source_id
    )
    assert _refusal(ran) is RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED


def test_a_source_admitted_after_the_pin_cannot_support_the_proof(
    ran: _Harness,
) -> None:
    late = b"Total debt at 31 December 2026 was admitted late\n"
    admit_pack(
        ran.conn,
        ran.blobs,
        case_id=ran.case_id,
        documents=[Document(filename=BoundaryText.of("late.txt"), data=late)],
    )
    ran.conn.commit()

    def moved(record: CanonicalRecord) -> CanonicalRecord:
        cited = tuple(
            replace(c, document_sha256=sha256(late).hexdigest())
            for c in record.citations
        )
        return replace(record, citations=cited)

    _rewrite(ran, "CP-5", moved)
    assert _refusal(ran) is RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED


@pytest.mark.parametrize(
    "fault",
    [
        "UPDATE source_tokens SET x0 = x0 + 17.0, x1 = x1 + 17.0 WHERE source_id = %s",
        "DELETE FROM source_tokens WHERE source_id = %s",
    ],
)
def test_a_moved_or_lost_quote_refuses(ran: _Harness, fault: str) -> None:
    with _token_fault(ran.conn):
        ran.conn.execute(fault, (ran.source_id,))
    ran.conn.commit()
    assert _refusal(ran) is RefusalCode.ORCHESTRATION_CITATION_LOST


@pytest.mark.parametrize(
    "field", ["adapter_version", "build_id", "manifest_sha256", "authority_digest"]
)
def test_a_record_from_another_build_refuses(ran: _Harness, field: str) -> None:
    changes: dict[str, Any] = {field: "b" * 64}
    _rewrite(ran, "CP-L10", lambda record: replace(record, **changes))
    assert _refusal(ran) is RefusalCode.ORCHESTRATION_BUILD_MOVED


def test_a_run_pinned_under_another_adapter_refuses(
    ran: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(methodology, "CANONICAL_ADAPTER_VERSION", "another-adapter")
    assert _refusal(ran) is RefusalCode.ORCHESTRATION_BUILD_MOVED
