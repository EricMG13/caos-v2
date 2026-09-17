"""Small, typed performed qualification evidence for store/API regressions."""

from uuid import UUID, uuid4

from server.qualification.harness import Performed, PerformedSet, PreparedCase
from server.qualification.matrix import Matrix, MatrixRow
from server.qualification.proof import OrchestrationProof
from server.qualification.store import PerformedEvidence, performed_evidence
from server.store import RunStatus
from server.store.run_inputs import RunInput


def qualification_performed() -> PerformedEvidence:
    run_id = UUID("00000000-0000-0000-0000-000000000001")
    prepared = PreparedCase(
        "case",
        RunInput(
            run_id=run_id,
            case_id=UUID("00000000-0000-0000-0000-000000000002"),
            source_version=1,
            source_fingerprint="c" * 64,
            route_digest="d" * 64,
            build_id="b" * 64,
            manifest_sha256="e" * 64,
            adapter_version="canonical-markdown-v3",
            research_json=None,
            input_fingerprint="f" * 64,
        ),
        "a" * 64,
        "openrouter/google-ai-studio/high/65536",
        "google/gemini-3.8-flash",
    )
    result = PerformedSet(
        performed=(
            Performed(
                "case",
                run_id,
                RunStatus.COMPLETE,
                None,
                OrchestrationProof(
                    run_id=run_id,
                    route_digest="d" * 64,
                    build_id="b" * 64,
                    artifacts=1,
                    citations=1,
                    anchored=frozenset({("CP-0", "c" * 64, "quoted text")}),
                ),
                None,
                (),
            ),
        ),
        matrix=Matrix(
            qualification_set_sha256="a" * 64,
            build_id="b" * 64,
            rows=(
                MatrixRow(
                    case_label="case",
                    proven=True,
                    refusal=None,
                    met=(),
                    missed=(),
                    forecast_met=None,
                    expected_refusal_met=None,
                ),
            ),
        ),
    )
    return performed_evidence(prepared=(prepared,), performed=result)


def record_runs(
    conn: object,
    performed: PerformedEvidence,
    *,
    model: str | None = None,
    outcome: bool = True,
) -> None:
    """The case, run, accepted attempt and recorded call behind a snapshot.

    `record_verdict` reads the models the runs actually called, so a snapshot
    a reviewer may sign needs those rows to exist. `model` records a model
    other than the one the harness configured; `outcome=False` accepts the
    artifact and records no call at all.
    """
    execute = conn.execute  # type: ignore[attr-defined]
    for case in performed.prepared:
        pin = case.input
        execute(
            "INSERT INTO cases (case_id,title) VALUES (%s,%s)"
            " ON CONFLICT (case_id) DO NOTHING",
            (pin.case_id, case.case_label),
        )
        execute(
            "INSERT INTO runs (run_id,case_id,status,budget_ceiling)"
            " VALUES (%s,%s,'COMPLETE',1) ON CONFLICT (run_id) DO NOTHING",
            (pin.run_id, pin.case_id),
        )
        attempt = uuid4()
        execute(
            "INSERT INTO run_attempts (attempt_id,run_id,route_node_id)"
            " VALUES (%s,%s,'CP-0')",
            (attempt, pin.run_id),
        )
        execute(
            "INSERT INTO artifacts (attempt_id,run_id,case_id,artifact_sha256,"
            "route_node_id,model,generation_id) VALUES (%s,%s,%s,%s,'CP-0',%s,%s)",
            (attempt, pin.run_id, pin.case_id, "1" * 64, model or case.model, "gen-1"),
        )
        if outcome:
            execute(
                "INSERT INTO call_outcomes (attempt_id,run_id,model) VALUES (%s,%s,%s)",
                (attempt, pin.run_id, model or case.model),
            )
