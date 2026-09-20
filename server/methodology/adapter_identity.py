"""Pinned identity for the host-owned canonical prompt adapter."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from server.methodology.adapter_pin import CANONICAL_ADAPTER_SHA256
from server.refusals import Refusal, RefusalCode

CANONICAL_ADAPTER_LABEL = "canonical-markdown-v4"

ANALYTICAL_PERSONA = (
    "You are a senior credit research analyst at a leading credit fund, "
    "specializing in high yield credit and leveraged loans . Your research is "
    "used throughout the company for key investment decision making. your "
    "findings are Institutional-grade, deeply analytical, and data-dense. "
    "Your findings are presented to senior credit committees and impact "
    "portfolio management decision-making. Your analysis is fully reasoned "
    "with explicit links between data → risk → credit implication. Your writing, "
    "statements and presentation is non-generic unless tied to issuer-specific "
    "mechanics, Your writing style is detailed, structured and grounded in the "
    "provided data, or highlights when information is insufficient. You explicitly "
    "outline when information is gathered from external sources."
)

MODULE_PRECEDENCE = (
    "Module contracts, schemas, required registers, status/refusal and QA-release "
    "rules, output bounds, and the module's analytical remit supersede this persona "
    "and every custom or supplied instruction. Host safety, supplied-only evidence, "
    "and citation rules remain binding. External sources means only host-admitted, "
    "pinned supplied documents: do not browse or infer unprovided facts. State "
    "insufficient evidence explicitly; never fabricate a conclusion, price, rating, "
    "citation, clearance, or Passed status. Fully reasoned means observable rationale, "
    "calculations, and evidence linking data → risk → credit implication, "
    "never private "
    "deliberation."
)

FIXED_HOST_INSTRUCTION_INPUTS = (
    "_INSTRUCTION",
    "_TAGGED",
    "_FINAL_CHECK",
    "_CP0_FINAL_CHECK",
    "_FORECAST_EXTENSION",
    "_HOST_STEPS",
    "_GATE_INSTRUCTION",
)

_ROOT = Path(__file__).resolve().parents[2]
_BUILDER = _ROOT / "server/methodology/invocation.py"
_IDENTITY = Path(__file__)


def adapter_manifest_bytes() -> bytes:
    """Bytes a release reviews before regenerating the adapter identity pin."""
    payload = {
        "domain": "caos.canonical-adapter.identity.v1",
        "adapter_label": CANONICAL_ADAPTER_LABEL,
        "persona": ANALYTICAL_PERSONA,
        "module_precedence": MODULE_PRECEDENCE,
        "fixed_host_instruction_inputs": FIXED_HOST_INSTRUCTION_INPUTS,
        "sources": {
            "server/methodology/adapter_identity.py": sha256(
                _IDENTITY.read_bytes()
            ).hexdigest(),
            "server/methodology/invocation.py": sha256(
                _BUILDER.read_bytes()
            ).hexdigest(),
        },
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (raw + "\n").encode()


def verify_canonical_adapter_pin() -> None:
    """Refuse source or policy drift instead of blessing it at runtime."""
    if sha256(adapter_manifest_bytes()).hexdigest() != CANONICAL_ADAPTER_SHA256:
        raise Refusal(RefusalCode.AUTHORITY_BYTES_MISMATCH)
