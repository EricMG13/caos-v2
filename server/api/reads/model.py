"""Model values are projections of the accepted CP-CF pair, never UI calculations."""

from typing import Any

from fastapi import APIRouter

from server.api.deps import Blobs, Caller, Methodology, Store
from server.api.reads.analysis import RunQuery, read_analysis
from server.api.reads.upload import CasePath
from server.api.wire import (
    ModelBody,
    ModelDocument,
    ModelForecast,
    ModelPeriod,
    ModelValue,
)
from server.methodology.forecast import forecast_projection
from server.refusals import Refusal, RefusalCode
from server.store.source_sets import pinned_live_sources

# Analysis' ten-node forecast route, including CP-CF's four owner proofs,
# plus the live source pin. Moves with Analysis' own budget, which this route
# pays in full before adding to it. Measured by
# test_model_http_actor_matrix_and_declared_io.
IO_BUDGET = 194
router = APIRouter()


@router.get("/api/v1/cases/{case_id}/model", response_model=ModelDocument)
def read_model(  # noqa: PLR0913 -- authenticated case/run before dependencies
    actor: Caller,
    case_id: CasePath,
    run: RunQuery,
    conn: Store,
    blobs: Blobs,
    bundle: Methodology,
) -> ModelDocument:
    analysis = read_analysis(actor, case_id, run, conn, blobs, bundle)
    body = analysis.body
    accepted = next((h for h in body.handoffs if h.module_id == "CP-CF"), None)
    forecast = None
    if accepted is not None and body.displayed_run_id is not None:
        live = pinned_live_sources(conn, body.displayed_run_id)
        if any(
            c.document_sha256 not in live for h in body.handoffs for c in h.source_facts
        ):
            raise Refusal(RefusalCode.ARTIFACT_RECORD_MISMATCH)
        result = forecast_projection(accepted.model_analysis.encode("utf-8"))
        forecast = ModelForecast(
            **accepted.model_dump(
                include={
                    "route_node_id",
                    "artifact_sha256",
                    "record_sha256",
                    "accepted_at",
                    "qa_status",
                    "limitation_flags",
                    "validation_warnings",
                }
            ),
            **result["units"],
            perimeter=result["perimeter"],
            periods=[_period(row) for row in result["rows"]],
        )
    return ModelDocument(
        **analysis.model_dump(exclude={"body", "status", "observed_empty"}),
        body=ModelBody(
            #  is the Analysis section's; the Model
            # section has the same blindness to an ended run and will want
            # its own field when that is addressed (ledgered).
            **body.model_dump(exclude={"handoffs", "pending", "displayed_run_status"}),
            forecast=forecast,
            unavailable_reason="NO_ACCEPTED_FORECAST" if forecast is None else None,
        ),
        observed_empty=forecast is None,
        status="partial" if forecast is None else "complete",
    )


def _period(row: dict[str, Any]) -> ModelPeriod:
    """Flatten named result groups without arithmetic, preserving ratio reasons."""
    identity = {
        k: row[k]
        for k in ("case", "period_id", "fiscal_year", "days", "unavailable_reason")
    }
    values = []
    for group, data in row.items():
        if group in identity:
            continue
        for name, value in data.items() if isinstance(data, dict) else [("", data)]:
            values.append(
                ModelValue(
                    name=f"{group}.{name}" if name else group,
                    value=value["value"] if isinstance(value, dict) else value,
                    unavailable_reason=value["reason"]
                    if isinstance(value, dict)
                    else None,
                )
            )
    return ModelPeriod(**identity, values=values)
