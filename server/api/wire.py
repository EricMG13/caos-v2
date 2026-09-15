"""The wire contract under `/api/`: the one refusal body.

Phase 4 Task 4.1, decision 3. Every non-success response carries
`RefusalBody{code, clears}`; `clears` is `CLEARS[code]`, a host constant that
says what would clear the refusal. It is never formatted, so no request or
document text can reach it. `server/refusals.py` stays code-only.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from server.refusals import RefusalCode

IO_BUDGET = 0


class RefusalBody(BaseModel):
    """Everything a declined request says: the code and what clears it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: RefusalCode
    clears: str


_C = RefusalCode

# Total over `RefusalCode` (`test_every_refusal_code_has_a_constant_clearance`).
# A code no route answers today still gets its sentence, so the first route to
# raise it cannot ship a body without one.
CLEARS: Mapping[RefusalCode, str] = {
    _C.BOUNDARY_TEXT_INVALID: "Remove control, bidirectional or surrogate characters.",
    _C.BOUNDARY_TEXT_TOO_LONG: "Shorten the text to within its bound.",
    _C.BLOB_DIGEST_MISMATCH: "An operator must restore the stored bytes.",
    _C.BLOB_NOT_FOUND: "An operator must restore the blob store.",
    _C.BLOB_ADDRESS_INVALID: "An operator must repair the stored address.",
    _C.RUN_NOT_FOUND: "Name a run you may read.",
    _C.RUN_NOT_RUNNING: "Act only on a running run.",
    _C.LEASE_NOT_HELD: "Reclaim the lease before acting on the node.",
    _C.RUN_CANCEL_REQUESTED: "Nothing; the run is being cancelled.",
    _C.RUN_NODES_UNACCEPTED: "Accept every pinned node first.",
    _C.RUN_TERMINAL_STALE: "Re-read the run and decide again.",
    _C.ATTEMPT_NOT_FOUND: "An operator must repair the attempt ledger.",
    _C.ATTEMPT_LIMIT_REACHED: "Start a new run.",
    _C.CALL_OUTCOME_INVALID: "Record a well-formed call outcome.",
    _C.CALL_OUTCOME_CONFLICT: "Nothing; a different outcome is already recorded.",
    _C.CALL_OUTCOME_LEGACY: "Start a new run.",
    _C.NODE_ALREADY_ACCEPTED: "Nothing; the node is already accepted.",
    _C.MONEY_NOT_DECIMAL: "State the amount as a decimal.",
    _C.MONEY_INVALID: "State a finite, non-negative amount.",
    _C.BUDGET_ALREADY_RESERVED: "Nothing; the reservation already exists.",
    _C.BUDGET_NOT_RESERVED: "Reserve budget before the call.",
    _C.BUDGET_CEILING_REACHED: "Raise the ceiling or start a new run.",
    _C.PROVIDER_NOT_CONFIGURED: "An operator must configure the provider.",
    _C.PROVIDER_CALL_INVALID: "Correct the provider call parameters.",
    _C.CONTEXT_OVER_CEILING: "Deliver less context to the module.",
    _C.PROVIDER_UNAVAILABLE: "Retry when the provider answers.",
    _C.PROVIDER_OUTPUT_TRUNCATED: "Retry the attempt.",
    _C.PROVIDER_REFUSED: "Retry the attempt or revise the evidence.",
    _C.PROVIDER_RESPONSE_INVALID: "Retry the attempt.",
    _C.AUTHORITY_BYTES_MISMATCH: "An operator must restore the pinned bundle.",
    _C.AUTHORITY_MODULE_UNKNOWN: "Name a module the bundle declares.",
    _C.ENVELOPE_INVALID: "Retry the attempt.",
    _C.ENVELOPE_UNDECLARED_FIELD: "Retry the attempt.",
    _C.ENVELOPE_UNCITED_CLAIM: "Retry the attempt.",
    _C.HANDOFF_MALFORMED: "An operator must verify the stored handoff.",
    _C.HANDOFF_BLOCKED: "Change the input that blocked the module.",
    _C.HANDOFF_IDENTITY_MISMATCH: "An operator must verify the stored handoff.",
    _C.HANDOFF_INCOMPLETE: "An operator must verify the stored handoff.",
    _C.HANDOFF_UNDECLARED_FIELD: "An operator must verify the stored handoff.",
    _C.HANDOFF_MODULE_UNSUPPORTED: "Select a route the adapter executes.",
    _C.ARTIFACT_RECORD_MISMATCH: "An operator must verify the stored record.",
    _C.READINESS_INVALID: "An operator must verify the gate artifact.",
    _C.READINESS_INCOMPLETE: "Retry the gate attempt.",
    _C.NOT_AUTHENTICATED: "Sign in.",
    _C.ENDPOINT_NOT_FOUND: "Use a declared path and method.",
    _C.NOT_AUTHORISED: "Obtain the required standing on the case.",
    _C.METHODOLOGY_INPUT_INVALID: "Correct the calculation inputs.",
    _C.FORECAST_CHAIN_BROKEN: "Link each period to the one before it.",
    _C.FORECAST_RESIDUAL_UNRECONCILED: "Reconcile the balances within tolerance.",
    _C.FORECAST_DRIVER_NOT_READY: "Complete the driver first.",
    _C.DELIVERABLE_PAYLOAD_INVALID: "Correct the deliverable payload.",
    _C.DELIVERABLE_UNCITED_FIGURE: "Cite every figure.",
    _C.DELIVERABLE_NOT_SIGNED: "Sign the deliverable first.",
    _C.DELIVERABLE_NOT_FROZEN: "Freeze the deliverable first.",
    _C.DELIVERABLE_MOVED_SINCE_SIGNING: "Review and sign the current revision.",
    _C.DELIVERABLE_ALREADY_FILED: "Nothing; the deliverable is filed.",
    _C.DELIVERABLE_ALREADY_FROZEN: "Nothing; the deliverable is frozen.",
    _C.APPROVER_NOT_INDEPENDENT: "Ask an approver who did not author it.",
    _C.CASE_NOT_FOUND: "Name a case you may read.",
    _C.SOURCE_PACK_EMPTY: "Supply at least one document.",
    _C.SOURCE_NOT_READABLE: "Supply a readable document.",
    _C.SOURCE_ENCRYPTED: "Supply the document without encryption.",
    _C.SOURCE_HAS_NO_TEXT: "Supply a document with extractable text.",
    _C.SOURCE_TOO_LARGE: "Supply a smaller document or pack.",
    _C.SOURCE_EXTRACTION_TIMEOUT: "Supply a simpler document.",
    _C.SOURCE_IDENTITY_INVALID: "Readmit the document.",
    _C.EVIDENCE_NOT_AVAILABLE: "Pin a live source for the evidence.",
    _C.CITATION_NOT_LOCATED: "Quote whole tokens from delivered evidence.",
    _C.CITATION_AMBIGUOUS: "Quote enough text to locate it once.",
    _C.CITATION_NOT_DELIVERED: "Cite only delivered evidence.",
    _C.ROUTE_PROFILE_UNKNOWN: "Name a profile the catalog declares.",
    _C.ROUTE_SELECTION_UNKNOWN: "Name a pathway the profile declares.",
    _C.ROUTE_EXTENSION_OWNER_MISSING: "Include the extension's owning module.",
    _C.ROUTE_HAS_A_CYCLE: "Select a route without a cycle.",
    _C.ROUTE_DUPLICATE_MODULE: "Select a route naming each module once.",
    _C.ROUTE_ALREADY_PINNED: "Nothing; the route is already pinned.",
    _C.ROUTE_IDENTITY_INVALID: "An operator must verify the pinned route.",
    _C.ROUTE_PIN_TOO_LATE: "Start a new run.",
    _C.RUN_INPUT_INVALID: "An operator must verify the run input.",
    _C.RUN_INPUT_ALREADY_PINNED: "Nothing; the input is already pinned.",
    _C.RUN_INPUT_TOO_LATE: "Start a new run.",
    _C.GATE_APPROVAL_MISMATCH: "Approve the content currently shown.",
    _C.QUALIFICATION_SET_EMPTY: "Add at least one case to the set.",
    _C.QUALIFICATION_KEY_UNANSWERABLE: "Key only modules on the case's route.",
    _C.QUALIFICATION_SET_AMBIGUOUS: "Give each case a distinct identity.",
    _C.QUALIFICATION_RUN_MISSING: "Perform every case in the set.",
    _C.QUALIFICATION_SET_FILE_INVALID: "Correct the set manifest.",
    _C.QUALIFICATION_SET_PATH_ESCAPES: "Keep documents inside the set directory.",
    _C.QUALIFICATION_SET_OVER_CEILING: "Raise the set ceiling or remove cases.",
    _C.ORCHESTRATION_NOTHING_TO_PROVE: "Accept at least one artifact first.",
    _C.ORCHESTRATION_ROUTE_NOT_PINNED: "Pin the route first.",
    _C.ORCHESTRATION_NODE_NOT_IN_ROUTE: "An operator must verify the run's artifacts.",
    _C.ORCHESTRATION_BUILD_MOVED: "Rerun under the current bundle.",
    _C.ORCHESTRATION_SOURCE_NOT_PINNED: "Rerun against live pinned sources.",
    _C.ORCHESTRATION_CITATION_LOST: "Rerun against live pinned sources.",
    _C.ORCHESTRATION_ARTIFACT_UNREADABLE: "An operator must restore the artifact.",
    _C.VERDICT_INCOMPLETE: "Supply every verdict binding.",
    _C.VERDICT_BINDING_INVALID: "Correct the verdict bindings.",
    _C.VERDICT_UNDECLARED_FIELD: "Remove undeclared verdict fields.",
    _C.VERDICT_EXPIRED: "Obtain a current verdict.",
    _C.STORE_SCHEMA_DRIFT: "An operator must reconcile the schema.",
    _C.STORE_NOT_TRANSACTIONAL: "An operator must fix the store connection.",
    _C.STORE_NOT_CONFIGURED: "An operator must configure the store.",
    _C.STORE_UNAVAILABLE: "Retry when the store answers.",
}
