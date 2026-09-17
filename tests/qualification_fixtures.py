"""Small, typed performed qualification evidence for store/API regressions."""

from uuid import UUID

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
            adapter_version="canonical-markdown-v2",
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
