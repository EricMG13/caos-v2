"""The actual extended route accepts CP-CF only from anchored owner inputs."""

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from canonical_fixtures import AUTHORED, CATALOG, CONTRACT, fields_from_prompt, wire
from canonical_route_fixtures import LIMITATION, PACK, RouteCompletions
from forecast_fixtures import forecast_request
from lite_route_fixtures import _yaml
from test_canonical_runtime import _module_provider, _run_route, _status
from test_execution_freshness import _Harness
from test_relative_value_route import harness as _harness

from server.calculators.cash_flow import cash_flow_forecast
from server.engine.route import ResolvedRoute, RouteExtensions, resolve_route
from server.methodology.forecast import forecast_projection
from server.provider import Completion
from server.refusals import RefusalCode

harness = _harness


def request_data() -> dict[str, Any]:
    request = forecast_request()
    request["periods"] = request["periods"][:1]
    request["periods"][0]["period_id"] = "FY2026"
    request["drivers"] = request["drivers"][:1]
    request["drivers"][0].update(
        period_id="FY2026",
        acquisitions_disposals="0",
        distributions="0",
        stated_closing_debt="600",
        stated_closing_cash="145",
    )
    request["opening"]["debt_by_facility"] = [{"facility_id": "TERM", "amount": "600"}]
    request["contractual"]["amortisation"] = request["contractual"]["amortisation"][:1]
    request["contractual"]["amortisation"][0]["period_id"] = "FY2026"
    return request


def assignment_rows(value: object, pointer: str = "") -> dict[str, str]:
    if isinstance(value, dict) and value:
        return {
            p: v
            for k, item in value.items()
            for p, v in assignment_rows(item, pointer + "/" + k).items()
        }
    if isinstance(value, list) and value:
        return {
            p: v
            for i, item in enumerate(value)
            for p, v in assignment_rows(item, pointer + "/" + str(i)).items()
        }
    return {pointer: pointer + " = " + json.dumps(value)}


ROWS = assignment_rows(request_data())
OWNER = {
    p: (
        "CP-4"
        if p.startswith("/contractual/")
        else "CP-2G"
        if p.startswith("/drivers/")
        else "CP-1"
    )
    for p in ROWS
}
OWNER_QUOTES = {
    m: "\n".join(v for p, v in ROWS.items() if OWNER[p] == m)
    for m in ("CP-1", "CP-2G", "CP-4")
}


@pytest.fixture
def route(monkeypatch: pytest.MonkeyPatch) -> ResolvedRoute:
    import test_relative_value_route

    monkeypatch.setattr(
        test_relative_value_route,
        "PACK",
        PACK + b"\n" + "\n".join(OWNER_QUOTES.values()).encode(),
    )
    return resolve_route(
        CATALOG,
        "FULL_CREDIT_32",
        "RELATIVE_VALUE",
        extensions=RouteExtensions(model_extension=True),
    )


class ForecastCompletions(RouteCompletions):
    def __init__(self, source_id: UUID, *, defect: str = "") -> None:
        super().__init__(source_id, quotes_by_module=OWNER_QUOTES)
        self.defect = defect

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        fields = fields_from_prompt(prompt)
        if fields["module_id"] != "CP-CF":
            return super().complete(prompt, json_object=json_object)
        self.prompts.append(prompt)
        request = request_data()
        bindings = {
            p: {"module_id": OWNER[p], "quote": OWNER_QUOTES[OWNER[p]]} for p in ROWS
        }
        result = cash_flow_forecast(request)
        if self.defect == "missing":
            del bindings["/opening/cash"]
        elif self.defect == "wrong-owner":
            bindings["/opening/cash"]["module_id"] = "CP-2G"
        elif self.defect == "result":
            result["rows"][0]["closing_cash"] = "999"
        document = {"request": request, "bindings": bindings, "forecast": result}
        front = {
            **fields,
            "confidence_score": 90,
            "confidence_band": "High",
            "committee_status": "Draft Only",
            "limitation_flags": [],
            "validation_warnings": [],
            "downstream_consumers": [],
            **AUTHORED["Passed"],
            "qa_status": "Passed",
        }
        if self.defect == "retain-restriction":
            front.update(AUTHORED["Restricted"])
            front.update(qa_status="Restricted", limitation_flags=[LIMITATION])
        quotes = "\n".join(OWNER_QUOTES.values())
        body = "".join(
            "## "
            + h
            + "\n\n"
            + (
                "```caos-forecast-v1\n" + json.dumps(document) + "\n```\n\n"
                if h == "Analysis"
                else ""
            )
            + quotes
            + "\n\n"
            for h in CONTRACT.validate_handoff.CANONICAL_HEADINGS
        )
        markdown = ("---\n" + _yaml(front) + "\n---\n" + body).encode()
        self.answers.append(markdown)
        return Completion(
            wire(
                markdown,
                [
                    {"source_id": str(self.source_id), "page": 1, "matched_text": q}
                    for q in OWNER_QUOTES.values()
                ],
            ),
            Decimal("0.0000041"),
            "gen-forecast",
        )


def test_forecast_route_accepts_real_host_calculated_artifact(
    harness: _Harness,
) -> None:
    from conftest import priced
    from test_loop_charges import ESTIMATE

    from server.deliverable.revisions import save_revision
    from server.engine.runtime import Execution, accepted_artifacts, run_route

    answers = ForecastCompletions(harness.source_id)
    run_route(
        harness.conn,
        harness.blobs,
        run_id=harness.run_id,
        route=harness.route,
        execution=Execution(
            _module_provider(harness, answers), priced(ESTIMATE), harness.bundle
        ),
    )
    assert _status(harness) == "COMPLETE"
    assert (
        len(
            accepted_artifacts(
                harness.conn,
                harness.blobs,
                harness.route,
                harness.run_id,
                bundle=harness.bundle,
            )
        )
        == 10
    )
    result = forecast_projection(answers.answers[-1])
    assert result["rows"][0]["cash"]["closing"] == "145.000000"
    revision = save_revision(
        harness.conn,
        harness.blobs,
        harness.bundle,
        case_id=harness.case_id,
        run_id=harness.run_id,
        actor_id=harness.approver,
        narrative=[],
    )
    assert isinstance(revision, UUID)


@pytest.mark.parametrize("defect", ["missing", "wrong-owner", "result"])
def test_forecast_route_refuses_unbound_or_altered_projection(
    harness: _Harness, defect: str
) -> None:
    answers = ForecastCompletions(harness.source_id, defect=defect)
    assert (
        _run_route(harness, _module_provider(harness, answers))
        is RefusalCode.HANDOFF_INCOMPLETE
    )
    assert _status(harness) != "COMPLETE"


def test_forecast_cannot_drop_an_accepted_owner_restriction(harness: _Harness) -> None:
    answers = ForecastCompletions(harness.source_id)
    answers.qa_by_module = {"CP-1": "Restricted"}
    assert (
        _run_route(harness, _module_provider(harness, answers))
        is RefusalCode.HANDOFF_INCOMPLETE
    )


def test_forecast_retains_an_accepted_owner_restriction(harness: _Harness) -> None:
    answers = ForecastCompletions(harness.source_id, defect="retain-restriction")
    answers.qa_by_module = {"CP-1": "Restricted"}
    assert _run_route(harness, _module_provider(harness, answers)) is None
    assert _status(harness) == "COMPLETE"
