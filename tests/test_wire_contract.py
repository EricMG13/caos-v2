"""The v1 section wire: the committed schema is the models' schema, every model
is closed and bounded, and the key sets are pinned (Task 4.1, decisions 5, 6, 8).

No store: these read the models and the committed file only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from server.api import wire
from server.api.reads import analysis, directory, run, upload
from server.api.wire import (
    V1_COMMANDS,
    V1_DOCUMENTS,
    ActionName,
    ActionView,
    AnalysisBody,
    AnalysisDocument,
    ApproveGate,
    AttemptView,
    CancelRun,
    CaseCreated,
    CaseRow,
    Chrome,
    CitationView,
    CreateCase,
    CreateRun,
    DirectoryBody,
    DirectoryDocument,
    EdgeView,
    GateApproved,
    GatePreviewDocument,
    GateView,
    HandoffView,
    NodeView,
    PendingNode,
    PinRunInput,
    RectView,
    RefusalBody,
    RetryRun,
    RouteChoice,
    RunBody,
    RunCreated,
    RunInputPinned,
    RunSectionDocument,
    RunSubjectView,
    RunSummary,
    RunView,
    RunWork,
    SectionNote,
    ServedRole,
    SetVersion,
    SourceRow,
    SourcesAdmitted,
    StartRun,
    Subject,
    UploadBody,
    UploadDocument,
    WorkView,
    wire_schema,
)
from server.methodology.handoff import MAX_FILE_BYTES

REPO = Path(__file__).resolve().parents[1]
COMMITTED = REPO / "frontend" / "src" / "wire" / "v1" / "schema.json"

ENVELOPE = frozenset(
    {"chrome", "body", "observed_at", "observed_empty", "status", "notes"}
)

# A new field is a model change, a regenerated schema and an edit here.
PINNED: dict[type[BaseModel], frozenset[str]] = {
    RefusalBody: frozenset({"code", "clears"}),
    Subject: frozenset({"case_id", "title"}),
    ServedRole: frozenset({"global_role", "standing"}),
    Chrome: frozenset({"subject", "served_role", "actions"}),
    ActionView: frozenset({"action", "refusal"}),
    WorkView: frozenset({"state", "stop_code", "cancel_requested"}),
    RouteChoice: frozenset({"profile_id", "selection_id"}),
    DirectoryDocument: ENVELOPE,
    UploadDocument: ENVELOPE,
    RunSectionDocument: ENVELOPE,
    AnalysisDocument: ENVELOPE,
    RunSummary: frozenset(
        {"run_id", "status", "created_at", "profile_id", "selection_id"}
    ),
    CaseRow: frozenset(
        {"case_id", "title", "created_at", "standing", "live_sources", "latest_run"}
    ),
    DirectoryBody: frozenset({"cases"}),
    SourceRow: frozenset(
        {
            "source_id",
            "filename",
            "document_sha256",
            "admitted_at",
            "withdrawn_at",
            "extractor_identity",
            "set_versions",
        }
    ),
    SetVersion: frozenset({"version", "fingerprint", "member_count"}),
    UploadBody: frozenset({"case_id", "sources", "set_versions"}),
    RunSubjectView: frozenset(
        {"issuer_id", "issuer_name", "reporting_period", "analysis_date"}
    ),
    GateView: frozenset({"gate", "state"}),
    AttemptView: frozenset(
        {"attempt_id", "route_node_id", "ordinal", "started_at", "accepted"}
    ),
    EdgeView: frozenset({"source", "type"}),
    NodeView: frozenset(
        {
            "route_node_id",
            "module_id",
            "stage",
            "state",
            "waiting_on",
            "awaiting_gate",
            "gate_verdict",
        }
    ),
    RunView: frozenset(
        {
            "run_id",
            "status",
            "created_at",
            "route_digest",
            "build_id",
            "source_set_version",
            "subject",
            "gates",
            "nodes",
            "attempts",
            "work",
        }
    ),
    RunBody: frozenset(
        {
            "case_id",
            "latest_run_id",
            "displayed_run_id",
            "runs",
            "run",
            "route_choices",
        }
    ),
    RectView: frozenset({"x0", "y0", "x1", "y1"}),
    CitationView: frozenset(
        {
            "document_sha256",
            "filename",
            "page",
            "matched_text",
            "rects",
            "withdrawn_at",
        }
    ),
    HandoffView: frozenset(
        {
            "route_node_id",
            "module_id",
            "artifact_sha256",
            "record_sha256",
            "accepted_at",
            "qa_status",
            "committee_status",
            "confidence_score",
            "confidence_band",
            "limitation_flags",
            "validation_warnings",
            "decision_scope",
            "screening_only",
            "source_facts",
            "model_analysis",
            "host_calculation",
        }
    ),
    PendingNode: frozenset({"route_node_id", "module_id", "state"}),
    AnalysisBody: frozenset(
        {
            "case_id",
            "latest_run_id",
            "displayed_run_id",
            "subject",
            "handoffs",
            "pending",
        }
    ),
    # Commands (Task 4.2, decisions 1 and 11): requests, then receipts.
    CreateCase: frozenset({"title"}),
    CaseCreated: frozenset({"case_id"}),
    SourcesAdmitted: frozenset({"case_id", "source_ids"}),
    CreateRun: frozenset({"profile_id", "selection_id"}),
    RunCreated: frozenset({"case_id", "run_id", "route_digest"}),
    PinRunInput: frozenset({"subject"}),
    RunInputPinned: frozenset({"run_id", "source_set_version", "input_fingerprint"}),
    GatePreviewDocument: frozenset(
        {
            "run_id",
            "gate",
            "content",
            "preview_sha256",
            "input_fingerprint",
            "observed_at",
        }
    ),
    ApproveGate: frozenset({"preview_sha256", "input_fingerprint"}),
    GateApproved: frozenset({"run_id", "gate", "preview_sha256", "input_fingerprint"}),
    StartRun: frozenset({"input_fingerprint"}),
    RetryRun: frozenset({"input_fingerprint"}),
    CancelRun: frozenset(),
    RunWork: frozenset({"run_id", "run_status", "work"}),
}

REQUESTS: tuple[type[BaseModel], ...] = (
    CreateCase,
    CreateRun,
    PinRunInput,
    ApproveGate,
    StartRun,
    RetryRun,
    CancelRun,
)

# What `frontend/src/wire/v1/shape.ts` can express. `title` and `description`
# are carried and ignored.
DSL_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "enum",
        "const",
        "anyOf",
        "maxLength",
        "maxItems",
        "pattern",
        "format",
        "$ref",
        "$defs",
        "items",
        "additionalProperties",
        "title",
        "description",
    }
)


def _wire_models() -> list[type[BaseModel]]:
    return [
        value
        for value in vars(wire).values()
        if isinstance(value, type)
        and issubclass(value, BaseModel)
        and value is not BaseModel
        and value.__module__ == wire.__name__
    ]


def _schemas(node: object) -> Iterator[dict[str, Any]]:
    """Every schema object in the document, depth first, `$defs` included."""
    if isinstance(node, dict):
        yield node
        for key, value in node.items():
            if key in {"properties", "$defs"}:
                for child in value.values():
                    yield from _schemas(child)
            elif key == "items" or key == "anyOf":
                yield from _schemas(value)
    elif isinstance(node, list):
        for child in node:
            yield from _schemas(child)


def test_the_committed_wire_schema_is_the_models_schema() -> None:
    printed = subprocess.run(
        [sys.executable, "-m", "server.api.wire"],
        cwd=REPO,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert printed == wire_schema()
    assert printed.endswith("}\n")
    assert not printed.endswith("\n\n")
    assert COMMITTED.read_text(encoding="utf-8") == printed
    defs = json.loads(printed)["$defs"]
    models: tuple[type[BaseModel], ...] = (*V1_DOCUMENTS, *V1_COMMANDS, RefusalBody)
    for model in models:
        assert model.__name__ in defs


def test_every_v1_model_forbids_undeclared_fields_and_bounds_every_collection() -> None:
    models = _wire_models()
    assert set(models) == set(PINNED), "a wire model the key-set pin does not name"
    for model in models:
        assert model.model_config.get("extra") == "forbid", model.__name__
        assert model.model_config.get("frozen") is True, model.__name__

    schema = json.loads(wire_schema())
    checked = 0
    for node in _schemas(schema):
        kind = node.get("type")
        if kind == "object" or "properties" in node:
            assert node.get("additionalProperties") is False, node.get("title")
            assert set(node["required"]) == set(node["properties"]), node["title"]
        if kind == "array":
            assert isinstance(node.get("maxItems"), int), node
            checked += 1
        if kind == "string" and not {"enum", "const", "format"} & set(node):
            assert isinstance(node.get("maxLength"), int), node
            checked += 1
        if node.get("format") in {"date-time", "uuid"}:
            assert node.get("type") == "string", node
    assert checked > 50, "the walk reached almost nothing"

    hashes = [
        props[name]
        for model in schema["$defs"].values()
        for props in [model.get("properties", {})]
        for name in props
        if name.endswith("sha256") or name in {"route_digest", "fingerprint"}
    ]
    assert len(hashes) >= 6
    for field in hashes:
        options = field.get("anyOf", [field])
        (text,) = [option for option in options if option.get("type") == "string"]
        assert text["pattern"] == "^[0-9a-f]{64}$"


def test_the_v1_wire_key_sets_are_pinned() -> None:
    for model, keys in PINNED.items():
        assert frozenset(model.model_fields) == keys, model.__name__
    assert set(SectionNote) == {
        SectionNote.LIST_TRUNCATED,
        SectionNote.ROUTE_NOT_PINNED,
        SectionNote.HANDOFFS_PENDING,
    }
    assert {action.value for action in ActionName} == {
        "CREATE_CASE",
        "ADMIT_SOURCES",
        "CREATE_RUN",
        "PIN_RUN_INPUT",
        "APPROVE_SOURCE_SET",
        "APPROVE_RESEARCH_PLAN",
        "START_RUN",
        "RETRY_RUN",
        "CANCEL_RUN",
    }
    assert [model.__name__ for model in V1_DOCUMENTS] == [
        "DirectoryDocument",
        "UploadDocument",
        "RunSectionDocument",
        "AnalysisDocument",
    ]


def test_the_wire_schema_uses_only_keywords_the_browser_validator_understands() -> None:
    schema = json.loads(wire_schema())
    assert set(schema) == {"$defs"}
    seen: set[str] = set()
    nodes = [node for model in schema["$defs"].values() for node in _schemas(model)]
    for node in nodes:
        seen |= set(node)
        assert set(node) <= DSL_KEYWORDS, sorted(set(node) - DSL_KEYWORDS)
        if "additionalProperties" in node:
            assert node["additionalProperties"] is False
        if "anyOf" in node:
            # Nullability only: one schema and `null`.
            assert len(node["anyOf"]) == 2
            assert {"type": "null"} in node["anyOf"]
    assert {"$ref", "anyOf", "maxLength", "maxItems", "pattern", "format"} <= seen


def test_every_section_router_declares_its_store_budget() -> None:
    for module in (directory, upload, run, analysis):
        assert isinstance(module.IO_BUDGET, int) and module.IO_BUDGET >= 0


def test_v1_command_models_are_closed_bounded_and_in_the_committed_schema() -> None:
    assert set(REQUESTS) <= set(V1_COMMANDS)
    assert len(V1_COMMANDS) == len(set(V1_COMMANDS)) == 14
    defs = json.loads(COMMITTED.read_text(encoding="utf-8"))["$defs"]
    for model in V1_COMMANDS:
        assert model.__name__ in defs, model.__name__
        assert model.model_config.get("extra") == "forbid", model.__name__
        assert model.model_config.get("frozen") is True, model.__name__
        # Every object, the empty `CancelRun` included, states `required`.
        assert set(defs[model.__name__]["required"]) == set(model.model_fields)

    # T1: a request names no actor, case, run or approver; the server derives them.
    authority = {"actor_id", "actor", "case_id", "run_id", "approver", "approver_id"}
    for request in REQUESTS:
        assert not authority & set(request.model_fields), request.__name__

    # Undeclared fields refused, and the bounds the brief names hold.
    fingerprint = "a" * 64
    for bad in ({"input_fingerprint": fingerprint, "actor_id": "x"}, {}):
        with pytest.raises(ValidationError):
            StartRun.model_validate(bad)
    with pytest.raises(ValidationError):
        CancelRun.model_validate({"run_id": fingerprint})
    assert defs["CreateCase"]["properties"]["title"]["maxLength"] == 256
    assert defs["SourcesAdmitted"]["properties"]["source_ids"]["maxItems"] == 50
    content = defs["GatePreviewDocument"]["properties"]["content"]["maxLength"]
    assert content == wire.PREVIEW_CHARS == MAX_FILE_BYTES
    assert defs["Chrome"]["properties"]["actions"]["maxItems"] == len(ActionName)
    choices = defs["RunBody"]["properties"]["route_choices"]
    assert choices["maxItems"] == 16
    for request in (StartRun, RetryRun, ApproveGate):
        field = defs[request.__name__]["properties"]["input_fingerprint"]
        assert field["pattern"] == "^[0-9a-f]{64}$"
