"""A canonical route through the real runtime (Task 3.1 slice c-5b; §41, §42).

`run_route` accepts a canonical result with its host record, replays the
executor's diagnostic exactly, reads CP-0 readiness and QA from records
verified against their Markdown, and ends the run BLOCKED on a validated
Blocked handoff. The post-call freshness guarantees are proven here too
(their claims-adapter variants were removed with the claims route in f-1a).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID

import pytest
from canonical_fixtures import QUOTE, UNANCHORED, CanonicalCompletions
from conftest import priced, recorded_statements
from test_canonical_execution import (
    _accept,
    _node,
    _reserved,
    _run,
    harness,
    route,
)
from test_execution_freshness import (
    _counts,
    _events,
    _Harness,
    _RefusedCompletion,
    _revoke_during_transport,
    _still_running,
)
from test_loop_charges import ESTIMATE, MODEL, REPORTED

from server.blobs import BlobStore
from server.engine import runtime
from server.engine.runtime import Execution, Provider, ProviderResult, run_route
from server.methodology import canonical, executor
from server.methodology.canonical import accepted_projections, blocked_verdict
from server.methodology.handoff import (
    Projections,
    _decoded_record,
    read_record,
    record_bytes,
)
from server.methodology.invocation import host_identity
from server.methodology.runner import ModuleProvider
from server.provider import Completion, CompletionProvider
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, connect
from server.store.events import lock_run
from server.store.outcomes import accepted_rows
from server.store.runs import block_run

__all__ = ["harness", "route"]


@dataclass
class _Answers:
    """A deterministic canonical answer, with a hook inside the call."""

    delegate: CanonicalCompletions
    during: Callable[[], None] = lambda: None
    facts: dict[str, Any] = field(default_factory=dict)
    model: str = MODEL
    calls: int = 0

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.calls += 1
        self.during()
        return replace(
            self.delegate.complete(prompt, json_object=json_object), **self.facts
        )


def _answers(
    harness: _Harness,
    during: Callable[[], None] = lambda: None,
    facts: dict[str, Any] | None = None,
) -> _Answers:
    return _Answers(CanonicalCompletions(harness.source_id), during, facts or {})


def _module_provider(
    harness: _Harness, completions: CompletionProvider
) -> ModuleProvider:
    return ModuleProvider(
        harness.conn,
        harness.bundle,
        harness.blobs,
        completions,
        harness.route,
        harness.run_id,
    )


def _run_route(harness: _Harness, provider: Provider) -> RefusalCode | None:
    try:
        run_route(
            harness.conn,
            harness.blobs,
            run_id=harness.run_id,
            route=harness.route,
            execution=Execution(provider, priced(ESTIMATE), harness.bundle),
        )
    except Refusal as refused:
        assert refused.__cause__ is None and refused.__context__ is None
        return refused.code
    return None


def _status(harness: _Harness) -> str:
    with connect(harness.url) as observer:
        row = observer.execute(
            "SELECT status FROM runs WHERE run_id=%s", (harness.run_id,)
        ).fetchone()
    assert row is not None
    return str(row[0])


def _projections(harness: _Harness) -> dict[str, Projections]:
    """Every accepted record, read back under the identity the store rebuilds."""
    rows = harness.conn.execute(
        "SELECT t.route_node_id, a.attempt_id, a.artifact_sha256, a.record_sha256,"
        " o.diagnostic_sha256 FROM artifacts a JOIN run_attempts t USING (attempt_id)"
        " JOIN call_outcomes o USING (attempt_id)"
    ).fetchall()
    read = {}
    for node_id, attempt, artifact, record, diagnostic in rows:
        node = next(n for n in harness.route.nodes if n.route_node_id == node_id)
        identity = host_identity(
            harness.conn,
            harness.bundle,
            run_id=harness.run_id,
            route=harness.route,
            node=node,
            attempt_id=attempt,
        )
        # The diagnostic is the whole response body the Markdown came out of.
        said = json.loads(harness.blobs.get(diagnostic))
        assert said["canonical_markdown"].encode() == harness.blobs.get(artifact)
        found = read_record(
            harness.blobs,
            artifact_sha256=artifact,
            record_sha256=record,
            expected=identity,
        )
        assert [c.matched_text for c in found.citations] == [QUOTE]
        read[node.module_id] = found.projections
    harness.conn.rollback()
    return read


@pytest.mark.parametrize("qa", ["Passed", "Restricted"])
def test_a_lite_route_completes_through_the_real_runtime(
    harness: _Harness, qa: str
) -> None:
    answers = CanonicalCompletions(harness.source_id, qa_by_module={"CP-L10": qa})
    assert _run_route(harness, _module_provider(harness, answers)) is None
    assert _counts(harness) == (3, [REPORTED] * 3, 3, 3, 3)
    assert [
        _events(harness, name)
        for name in ("CALL_OUTCOME_RECORDED", "ATTEMPT_ACCEPTED", "RUN_COMPLETE")
    ] == [3, 3, 1]
    read = _projections(harness)
    assert sorted(read) == ["CP-0", "CP-5", "CP-L10"]
    assert read["CP-0"].readiness == (("CP-5", "READY"), ("CP-L10", "READY"))
    screen = read["CP-L10"]
    assert (screen.qa_status, bool(screen.limitation_flags)) == (
        qa,
        qa == "Restricted",
    )


def test_the_gate_blocking_a_module_ends_the_run_without_calling_it(
    harness: _Harness,
) -> None:
    answers = CanonicalCompletions(harness.source_id, readiness={"CP-L10": "BLOCKED"})
    assert _run_route(harness, _module_provider(harness, answers)) is None
    # CP-5's edge from CP-L10 is soft, so CP-5 runs without it; CP-L10 never.
    called = [prompt.split(maxsplit=6)[5] for prompt in answers.prompts]
    assert called == ["CP-0", "CP-5"]
    assert _counts(harness) == (2, [REPORTED] * 2, 2, 2, 2)
    assert (_status(harness), _events(harness, "RUN_BLOCKED")) == ("BLOCKED", 1)


def test_a_validated_blocked_handoff_ends_the_run_blocked_without_retry(
    harness: _Harness,
) -> None:
    answers = CanonicalCompletions(harness.source_id, qa_by_module={"CP-5": "Blocked"})
    assert _run_route(harness, _module_provider(harness, answers)) is None
    assert len(answers.prompts) == 3
    assert _counts(harness) == (3, [REPORTED] * 3, 2, 3, 3)
    assert (_status(harness), _events(harness, "RUN_BLOCKED")) == ("BLOCKED", 1)
    assert _events(harness, "RUN_COMPLETE") == 0
    # The Blocked answer is the attempt's diagnostic, never an artifact.
    blocked = hashlib.sha256(answers.bodies[2].encode()).hexdigest()
    with connect(harness.url) as observer:
        row = observer.execute(
            "SELECT count(*) FROM call_outcomes o JOIN run_attempts t"
            " USING (attempt_id) WHERE o.diagnostic_sha256=%s"
            " AND t.route_node_id=%s AND NOT EXISTS"
            " (SELECT 1 FROM artifacts a WHERE a.attempt_id=o.attempt_id)",
            (blocked, _node(harness, "CP-5").route_node_id),
        ).fetchone()
    assert row == (1,)


def test_an_unanchorable_blocked_handoff_is_an_ordinary_refusal(
    harness: _Harness,
) -> None:
    """Quotes are anchored before Blocked is honoured (c-5b, P3-2)."""
    answers = CanonicalCompletions(
        harness.source_id, qa_status="Blocked", quotes=(UNANCHORED,)
    )
    code = _run_route(harness, _module_provider(harness, answers))
    assert code is RefusalCode.CITATION_NOT_LOCATED
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)
    _still_running(harness)
    assert _events(harness, "RUN_BLOCKED") == 0


@dataclass
class _UnbilledBlocked:
    """A Provider claiming Blocked without any call behind it."""

    model: str = MODEL

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        raise Refusal(RefusalCode.HANDOFF_BLOCKED)


def test_an_unbilled_blocked_claim_never_ends_the_run(harness: _Harness) -> None:
    assert _run_route(harness, _UnbilledBlocked()) is RefusalCode.HANDOFF_BLOCKED
    assert _counts(harness) == (0, [], 0, 1, 1)
    _still_running(harness)


def test_a_crash_before_the_block_commits_resumes_blocked_without_a_second_call(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict is re-derived from the stored bill and diagnostic (P1)."""
    crashes = [RefusalCode.STORE_UNAVAILABLE]

    def crashing(conn: StoreConnection, run_id: UUID) -> bool:
        if crashes:
            raise Refusal(crashes.pop())
        return block_run(conn, run_id)

    monkeypatch.setattr(runtime, "block_run", crashing)
    answers = CanonicalCompletions(harness.source_id, qa_by_module={"CP-5": "Blocked"})
    provider = _module_provider(harness, answers)
    assert _run_route(harness, provider) is RefusalCode.STORE_UNAVAILABLE
    _still_running(harness)
    screen = _node(harness, "CP-5").route_node_id
    with recorded_statements(harness.conn) as statements:
        verdict = blocked_verdict(
            harness.conn,
            harness.blobs,
            harness.bundle,
            run_id=harness.run_id,
            route=harness.route,
            route_node_ids=[screen],
        )
    assert verdict
    # The captured pins are read once, by the reader the verdict re-anchors on.
    assert statements.count(executor._CAPTURED) == 1
    harness.conn.rollback()
    # Resume: no attempt, reservation or call; the run ends BLOCKED once.
    assert _run_route(harness, provider) is None
    assert len(answers.prompts) == 3
    assert _counts(harness) == (3, [REPORTED] * 3, 2, 3, 3)
    assert (_status(harness), _events(harness, "RUN_BLOCKED")) == ("BLOCKED", 1)


def test_an_unreadable_stored_verdict_is_a_fault_not_a_second_call(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A diagnostic blob that will not read never counts as "not blocked"."""
    crashes = [RefusalCode.STORE_UNAVAILABLE]

    def crashing(conn: StoreConnection, run_id: UUID) -> bool:
        if crashes:
            raise Refusal(crashes.pop())
        return block_run(conn, run_id)

    monkeypatch.setattr(runtime, "block_run", crashing)
    answers = CanonicalCompletions(harness.source_id, qa_by_module={"CP-5": "Blocked"})
    provider = _module_provider(harness, answers)
    assert _run_route(harness, provider) is RefusalCode.STORE_UNAVAILABLE
    blocked = hashlib.sha256(answers.bodies[2].encode()).hexdigest()
    harness.blobs.path_of(blocked).unlink()
    assert _run_route(harness, provider) is RefusalCode.STORE_UNAVAILABLE
    assert len(answers.prompts) == 3
    _still_running(harness)


def test_a_body_that_cannot_be_stored_refuses_after_its_bill(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = CanonicalCompletions(harness.source_id)
    provider = _module_provider(harness, answers)
    real_put = BlobStore.put

    def failing(self: BlobStore, data: bytes) -> str:
        if answers.bodies and data == answers.bodies[-1].encode():
            raise OSError
        return real_put(self, data)

    monkeypatch.setattr(BlobStore, "put", failing)
    assert _run_route(harness, provider) is RefusalCode.STORE_UNAVAILABLE
    assert _counts(harness)[:2] == (1, [REPORTED])
    _still_running(harness)


@dataclass
class _ClaimsBlocked:
    """Makes a real, billed call, then says Blocked whatever the answer was."""

    inner: ModuleProvider
    module: str = "CP-0"
    model: str = MODEL

    def execute(
        self, route_node_id: str, module_id: str, *, attempt_id: UUID
    ) -> ProviderResult:
        try:
            result = self.inner.execute(route_node_id, module_id, attempt_id=attempt_id)
        except Refusal:
            result = None
        if module_id == self.module:
            raise Refusal(RefusalCode.HANDOFF_BLOCKED)
        assert result is not None
        return result


@pytest.mark.parametrize(
    "knobs",
    [{}, {"qa_status": "Blocked", "quotes": (UNANCHORED,)}],
    ids=["passed", "unanchorable-blocked"],
)
def test_a_blocked_claim_without_a_validated_diagnostic_never_ends_the_run(
    harness: _Harness, knobs: dict[str, Any]
) -> None:
    answers = CanonicalCompletions(harness.source_id, **knobs)
    lying = _ClaimsBlocked(_module_provider(harness, answers))
    assert _run_route(harness, lying) is RefusalCode.HANDOFF_BLOCKED
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)
    assert _events(harness, "RUN_BLOCKED") == 0
    _still_running(harness)


def test_readers_verify_the_record_against_its_markdown(harness: _Harness) -> None:
    from server.engine.runtime import accepted_artifacts

    answers = CanonicalCompletions(harness.source_id)
    assert _run_route(harness, _module_provider(harness, answers)) is None
    gate = _node(harness, "CP-0").route_node_id
    args = (harness.conn, harness.blobs, harness.route, harness.run_id)
    body = accepted_artifacts(*args, bundle=harness.bundle)[gate]
    harness.conn.rollback()
    assert body.readiness == (("CP-5", "READY"), ("CP-L10", "READY"))
    with pytest.raises(Refusal) as unbundled:
        accepted_artifacts(*args)
    harness.conn.rollback()
    assert unbundled.value.code is RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE
    rows = {row[0]: row for row in accepted_rows(harness.conn, harness.run_id)}
    harness.conn.rollback()
    assert sorted(rows) == sorted(n.route_node_id for n in harness.route.nodes)
    _node_id, attempt, artifact, record = rows[gate]
    assert record is not None
    # A record in canonical form, bound to the right Markdown and identity, whose
    # projections the Markdown does not say.
    decoded = _decoded_record(harness.blobs.get(record))
    lying = replace(
        decoded,
        projections=replace(decoded.projections, readiness=(("CP-5", "READY"),)),
    )
    with pytest.raises(Refusal) as mismatch:
        accepted_projections(
            harness.conn,
            harness.blobs,
            harness.bundle,
            harness.route,
            run_id=harness.run_id,
            route_node_id=gate,
            attempt_id=attempt,
            artifact_sha256=artifact,
            record_sha256=harness.blobs.put(record_bytes(lying)),
        )
    harness.conn.rollback()
    assert mismatch.value.code is RefusalCode.ARTIFACT_RECORD_MISMATCH


# P2-2: the post-call guarantees, through ModuleProvider.


def _accepted_first(harness: _Harness) -> tuple[str, str]:
    """Accept the route's first node for real; return the second node's ids."""
    first, second = harness.route.nodes[:2]
    attempt, result = _run(harness, first.module_id, _answers(harness))
    _accept(harness, attempt, result)
    return second.route_node_id, second.module_id


def _execute(
    harness: _Harness, module_id: str, completions: CompletionProvider
) -> tuple[RefusalCode, UUID]:
    attempt = _reserved(harness, module_id)
    node = _node(harness, module_id)
    with pytest.raises(Refusal) as refused:
        _module_provider(harness, completions).execute(
            node.route_node_id, module_id, attempt_id=attempt
        )
    assert refused.value.__cause__ is None and refused.value.__context__ is None
    return refused.value.code, attempt


def test_upstream_rewritten_during_transport_is_refused_keeping_the_bill(
    harness: _Harness,
) -> None:
    _node_id, module_id = _accepted_first(harness)
    first = harness.route.nodes[0].route_node_id

    def rewrite() -> None:
        with connect(harness.url) as other:
            lock_run(other, harness.run_id)
            other.execute(
                "UPDATE artifacts SET artifact_sha256=%s WHERE route_node_id=%s",
                (harness.blobs.put(b"other accepted bytes"), first),
            )
            other.commit()

    answers = _answers(harness, during=rewrite)
    code, _attempt = _execute(harness, module_id, answers)
    assert (code, answers.calls) == (RefusalCode.ROUTE_IDENTITY_INVALID, 1)
    assert _counts(harness) == (2, [REPORTED] * 2, 1, 2, 2)


def test_host_identity_changed_during_transport_is_refused_keeping_the_bill(
    harness: _Harness,
) -> None:
    """Only the host identity moves: the attempt's stored ordinal."""

    def renumber() -> None:
        with connect(harness.url) as other:
            other.execute("UPDATE run_attempts SET ordinal = ordinal + 1")
            other.commit()

    answers = _answers(harness, during=renumber)
    code, _attempt = _execute(harness, "CP-0", answers)
    assert (code, answers.calls) == (RefusalCode.ROUTE_IDENTITY_INVALID, 1)
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)


@pytest.mark.parametrize(
    ("facts", "billed"),
    [({"charge": None}, []), ({"generation_id": "not a handle!"}, [REPORTED])],
)
def test_an_unknown_charge_or_generation_is_refused_keeping_the_bill(
    harness: _Harness, facts: dict[str, Any], billed: list[Any]
) -> None:
    answers = _answers(harness, facts=facts)
    module_id = harness.route.nodes[0].module_id
    code, _attempt = _execute(harness, module_id, answers)
    assert code is RefusalCode.PROVIDER_RESPONSE_INVALID
    assert _counts(harness) == (1, billed, 0, 1, 1)
    _still_running(harness)


def test_a_known_provider_refusal_keeps_precedence_over_stale_authority(
    harness: _Harness,
) -> None:
    completion = _RefusedCompletion(lambda: _revoke_during_transport(harness))
    module_id = harness.route.nodes[0].module_id
    code, _attempt = _execute(harness, module_id, completion)
    assert (code, completion.calls) == (RefusalCode.PROVIDER_REFUSED, 1)
    assert _counts(harness) == (1, [REPORTED], 0, 1, 1)
    _still_running(harness)


@pytest.mark.parametrize("failure", ["sql", "interrupt"])
@pytest.mark.parametrize("stage", ["evidence", "upstream"])
def test_a_failure_while_deriving_context_makes_no_call(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch, stage: str, failure: str
) -> None:
    module_id = harness.route.nodes[0].module_id
    if stage == "upstream":
        _node_id, module_id = _accepted_first(harness)
    owner = canonical
    name = {"evidence": "_delivered", "upstream": "upstream_markdown"}[stage]
    real = getattr(owner, name)

    def failing(*args: object, **kwargs: object) -> object:
        real(*args, **kwargs)
        if failure == "sql":
            harness.conn.execute("SELECT (%s)::int", (QUOTE,))
        raise KeyboardInterrupt

    monkeypatch.setattr(owner, name, failing)
    answers = _answers(harness)
    attempt = _reserved(harness, module_id)
    node = _node(harness, module_id)
    with pytest.raises((Refusal, KeyboardInterrupt)) as raised:
        _module_provider(harness, answers).execute(
            node.route_node_id, module_id, attempt_id=attempt
        )
    if failure == "sql":
        assert isinstance(raised.value, Refusal)
        assert raised.value.code is RefusalCode.STORE_UNAVAILABLE
    else:
        assert type(raised.value) is KeyboardInterrupt
    assert answers.calls == 0
    with connect(harness.url) as observer:
        row = observer.execute(
            "SELECT count(*) FROM call_outcomes WHERE attempt_id=%s", (attempt,)
        ).fetchone()
    assert row == (0,)
    _still_running(harness)
