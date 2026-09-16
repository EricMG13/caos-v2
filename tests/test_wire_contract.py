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

from pydantic import BaseModel

from server.api import wire
from server.api.reads import analysis, directory, run, upload
from server.api.wire import (
    V1_DOCUMENTS,
    AnalysisBody,
    AnalysisDocument,
    AttemptView,
    CaseRow,
    Chrome,
    CitationView,
    DirectoryBody,
    DirectoryDocument,
    EdgeView,
    GateView,
    HandoffView,
    NodeView,
    PendingNode,
    RectView,
    RefusalBody,
    RunBody,
    RunSectionDocument,
    RunSubjectView,
    RunSummary,
    RunView,
    SectionNote,
    ServedRole,
    SetVersion,
    SourceRow,
    Subject,
    UploadBody,
    UploadDocument,
    wire_schema,
)

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
    Chrome: frozenset({"subject", "served_role"}),
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
        }
    ),
    RunBody: frozenset({"case_id", "latest_run_id", "displayed_run_id", "runs", "run"}),
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
}

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
    models: tuple[type[BaseModel], ...] = (*V1_DOCUMENTS, RefusalBody)
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
