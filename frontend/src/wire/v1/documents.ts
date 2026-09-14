// The v1 section documents and the refusal body, one shape per model in
// `server/api/wire.py`, named as there. `schema.json` beside this file is the
// backend's emitted schema; tests/unit/wire-contract.test.ts proves these
// shapes normalise to it exactly.
import {
  type Infer,
  array,
  bool,
  datetime,
  enumOf,
  int,
  literal,
  nullable,
  number,
  object,
  parse,
  string,
  uuid,
} from "./shape";

const SHORT = 256;
const TEXT = 4096;
const hash = string({ max: 64, pattern: "^[0-9a-f]{64}$" });
const short = string({ max: SHORT });
const text = string({ max: TEXT });
const RUN_STATUSES = [
  "RUNNING",
  "COMPLETE",
  "FAILED",
  "BLOCKED",
  "CANCELLED",
] as const;

const GlobalRole = enumOf(["READER", "ANALYST", "ADMIN"]);
const Standing = enumOf(["READER", "WRITER", "APPROVER", "ADMIN"]);
const SectionNote = enumOf(["LIST_TRUNCATED", "ROUTE_NOT_PINNED", "HANDOFFS_PENDING"]);
const NodeState = enumOf(["COMPLETE", "RUNNABLE", "RESTRICTED", "BLOCKED"]);
const EdgeType = enumOf(["REQUIRED", "CONDITIONAL", "QA_GATE", "OPTIONAL", "ADVISORY"]);
const Gate = enumOf(["SOURCE_SET", "RESEARCH_PLAN"]);
const GateState = enumOf(["OPEN", "RELEASED"]);

const Subject = object({ case_id: uuid, title: text });
const ServedRole = object({ global_role: GlobalRole, standing: nullable(Standing) });
const Chrome = object({ subject: nullable(Subject), served_role: ServedRole });

function sectionDocument<B extends ReturnType<typeof object>>(body: B) {
  return object({
    chrome: Chrome,
    body,
    observed_at: datetime,
    observed_empty: bool,
    status: enumOf(["complete", "partial"]),
    notes: array(SectionNote, 3),
  });
}

const RunSummary = object({
  run_id: uuid,
  status: enumOf(RUN_STATUSES),
  created_at: datetime,
  profile_id: nullable(short),
  selection_id: nullable(short),
});
const CaseRow = object({
  case_id: uuid,
  title: text,
  created_at: datetime,
  standing: Standing,
  live_sources: int(),
  latest_run: nullable(RunSummary),
});
const DirectoryBody = object({ cases: array(CaseRow, 200) });
const DirectoryDocument = sectionDocument(DirectoryBody);

const SourceRow = object({
  source_id: uuid,
  filename: text,
  document_sha256: hash,
  admitted_at: datetime,
  withdrawn_at: nullable(datetime),
  extractor_identity: nullable(text),
  set_versions: array(int(), 1000),
});
const SetVersion = object({ version: int(), fingerprint: hash, member_count: int() });
const UploadBody = object({
  case_id: uuid,
  sources: array(SourceRow, 1000),
  set_versions: array(SetVersion, 1000),
});
const UploadDocument = sectionDocument(UploadBody);

const RunSubjectView = object({
  issuer_id: string({ max: 128 }),
  issuer_name: text,
  reporting_period: text,
  analysis_date: string({ max: 10, pattern: "^\\d{4}-\\d{2}-\\d{2}$" }),
});
const GateView = object({ gate: Gate, state: GateState });
const EdgeView = object({ source: short, type: EdgeType });
const NodeView = object({
  route_node_id: short,
  module_id: short,
  stage: int(),
  state: NodeState,
  waiting_on: array(EdgeView, 256),
  awaiting_gate: bool,
  gate_verdict: nullable(short),
});
const AttemptView = object({
  attempt_id: uuid,
  route_node_id: short,
  ordinal: nullable(int()),
  started_at: datetime,
  accepted: bool,
});
const RunView = object({
  run_id: uuid,
  status: enumOf(RUN_STATUSES),
  created_at: datetime,
  route_digest: nullable(hash),
  build_id: nullable(short),
  source_set_version: nullable(int()),
  subject: nullable(RunSubjectView),
  gates: array(GateView, 2),
  nodes: array(NodeView, 256),
  attempts: array(AttemptView, 4096),
});
const RunBody = object({
  case_id: uuid,
  latest_run_id: nullable(uuid),
  displayed_run_id: nullable(uuid),
  runs: array(RunSummary, 200),
  run: nullable(RunView),
});
const RunSectionDocument = sectionDocument(RunBody);

const RectView = object({ x0: number, y0: number, x1: number, y1: number });
const CitationView = object({
  document_sha256: hash,
  filename: text,
  page: int(),
  matched_text: string({ max: 65536 }),
  rects: array(RectView, 256),
  withdrawn_at: nullable(datetime),
});
const HandoffView = object({
  route_node_id: short,
  module_id: short,
  artifact_sha256: hash,
  record_sha256: hash,
  accepted_at: datetime,
  qa_status: short,
  committee_status: short,
  confidence_score: int(),
  confidence_band: short,
  limitation_flags: array(text, 256),
  validation_warnings: array(text, 256),
  decision_scope: short,
  screening_only: bool,
  source_facts: array(CitationView, 1024),
  model_analysis: string({ max: 26214400 }),
  host_calculation: literal("NONE"),
});
const PendingNode = object({ route_node_id: short, module_id: short, state: NodeState });
const AnalysisBody = object({
  case_id: uuid,
  latest_run_id: nullable(uuid),
  displayed_run_id: nullable(uuid),
  subject: nullable(RunSubjectView),
  handoffs: array(HandoffView, 256),
  pending: array(PendingNode, 256),
});
const AnalysisDocument = sectionDocument(AnalysisBody);

const RefusalCode = enumOf([
  "BOUNDARY_TEXT_INVALID",
  "BOUNDARY_TEXT_TOO_LONG",
  "BLOB_DIGEST_MISMATCH",
  "BLOB_NOT_FOUND",
  "BLOB_ADDRESS_INVALID",
  "RUN_NOT_FOUND",
  "RUN_NOT_RUNNING",
  "LEASE_NOT_HELD",
  "RUN_CANCEL_REQUESTED",
  "RUN_NODES_UNACCEPTED",
  "RUN_TERMINAL_STALE",
  "ATTEMPT_NOT_FOUND",
  "ATTEMPT_LIMIT_REACHED",
  "CALL_OUTCOME_INVALID",
  "CALL_OUTCOME_CONFLICT",
  "CALL_OUTCOME_LEGACY",
  "NODE_ALREADY_ACCEPTED",
  "MONEY_NOT_DECIMAL",
  "MONEY_INVALID",
  "BUDGET_ALREADY_RESERVED",
  "BUDGET_NOT_RESERVED",
  "BUDGET_CEILING_REACHED",
  "PROVIDER_NOT_CONFIGURED",
  "PROVIDER_CALL_INVALID",
  "CONTEXT_OVER_CEILING",
  "PROVIDER_UNAVAILABLE",
  "PROVIDER_OUTPUT_TRUNCATED",
  "PROVIDER_REFUSED",
  "PROVIDER_RESPONSE_INVALID",
  "AUTHORITY_BYTES_MISMATCH",
  "AUTHORITY_MODULE_UNKNOWN",
  "ENVELOPE_INVALID",
  "ENVELOPE_UNDECLARED_FIELD",
  "ENVELOPE_UNCITED_CLAIM",
  "HANDOFF_MALFORMED",
  "HANDOFF_BLOCKED",
  "HANDOFF_IDENTITY_MISMATCH",
  "HANDOFF_INCOMPLETE",
  "HANDOFF_UNDECLARED_FIELD",
  "HANDOFF_MODULE_UNSUPPORTED",
  "ARTIFACT_RECORD_MISMATCH",
  "READINESS_INVALID",
  "READINESS_INCOMPLETE",
  "NOT_AUTHENTICATED",
  "ENDPOINT_NOT_FOUND",
  "NOT_AUTHORISED",
  "METHODOLOGY_INPUT_INVALID",
  "FORECAST_CHAIN_BROKEN",
  "FORECAST_RESIDUAL_UNRECONCILED",
  "FORECAST_DRIVER_NOT_READY",
  "DELIVERABLE_PAYLOAD_INVALID",
  "DELIVERABLE_UNCITED_FIGURE",
  "DELIVERABLE_NOT_SIGNED",
  "DELIVERABLE_NOT_FROZEN",
  "DELIVERABLE_MOVED_SINCE_SIGNING",
  "DELIVERABLE_ALREADY_FILED",
  "DELIVERABLE_ALREADY_FROZEN",
  "APPROVER_NOT_INDEPENDENT",
  "CASE_NOT_FOUND",
  "SOURCE_PACK_EMPTY",
  "SOURCE_NOT_READABLE",
  "SOURCE_ENCRYPTED",
  "SOURCE_HAS_NO_TEXT",
  "SOURCE_TOO_LARGE",
  "SOURCE_EXTRACTION_TIMEOUT",
  "SOURCE_IDENTITY_INVALID",
  "EVIDENCE_NOT_AVAILABLE",
  "CITATION_NOT_LOCATED",
  "CITATION_AMBIGUOUS",
  "CITATION_NOT_DELIVERED",
  "ROUTE_PROFILE_UNKNOWN",
  "ROUTE_SELECTION_UNKNOWN",
  "ROUTE_EXTENSION_OWNER_MISSING",
  "ROUTE_HAS_A_CYCLE",
  "ROUTE_DUPLICATE_MODULE",
  "ROUTE_ALREADY_PINNED",
  "ROUTE_IDENTITY_INVALID",
  "ROUTE_PIN_TOO_LATE",
  "RUN_INPUT_INVALID",
  "RUN_INPUT_ALREADY_PINNED",
  "RUN_INPUT_TOO_LATE",
  "GATE_APPROVAL_MISMATCH",
  "QUALIFICATION_SET_EMPTY",
  "QUALIFICATION_KEY_UNANSWERABLE",
  "QUALIFICATION_SET_AMBIGUOUS",
  "QUALIFICATION_RUN_MISSING",
  "QUALIFICATION_SET_FILE_INVALID",
  "QUALIFICATION_SET_PATH_ESCAPES",
  "QUALIFICATION_SET_OVER_CEILING",
  "ORCHESTRATION_NOTHING_TO_PROVE",
  "ORCHESTRATION_ROUTE_NOT_PINNED",
  "ORCHESTRATION_NODE_NOT_IN_ROUTE",
  "ORCHESTRATION_BUILD_MOVED",
  "ORCHESTRATION_SOURCE_NOT_PINNED",
  "ORCHESTRATION_CITATION_LOST",
  "ORCHESTRATION_ARTIFACT_UNREADABLE",
  "VERDICT_INCOMPLETE",
  "VERDICT_BINDING_INVALID",
  "VERDICT_UNDECLARED_FIELD",
  "VERDICT_EXPIRED",
  "STORE_SCHEMA_DRIFT",
  "STORE_NOT_TRANSACTIONAL",
  "STORE_NOT_CONFIGURED",
  "STORE_UNAVAILABLE",
]);
const RefusalBody = object({ code: RefusalCode, clears: text });

/** Every model `schema.json` declares, under its backend name. */
export const V1_SHAPES = {
  AnalysisBody,
  AnalysisDocument,
  AttemptView,
  CaseRow,
  Chrome,
  CitationView,
  DirectoryBody,
  DirectoryDocument,
  EdgeType,
  EdgeView,
  Gate,
  GateState,
  GateView,
  GlobalRole,
  HandoffView,
  NodeState,
  NodeView,
  PendingNode,
  RectView,
  RefusalBody,
  RefusalCode,
  RunBody,
  RunSectionDocument,
  RunSubjectView,
  RunSummary,
  RunView,
  SectionNote,
  ServedRole,
  SetVersion,
  SourceRow,
  Standing,
  Subject,
  UploadBody,
  UploadDocument,
};

export type DirectoryDocument = Infer<typeof DirectoryDocument>;
export type UploadDocument = Infer<typeof UploadDocument>;
export type RunSectionDocument = Infer<typeof RunSectionDocument>;
export type AnalysisDocument = Infer<typeof AnalysisDocument>;
export type RefusalBody = Infer<typeof RefusalBody>;
export type RefusalCode = Infer<typeof RefusalCode>;
export type Chrome = Infer<typeof Chrome>;
export type CaseRow = Infer<typeof CaseRow>;
export type SourceRow = Infer<typeof SourceRow>;
export type RunView = Infer<typeof RunView>;
export type NodeView = Infer<typeof NodeView>;
export type HandoffView = Infer<typeof HandoffView>;
export type CitationView = Infer<typeof CitationView>;
export type SectionDocument =
  DirectoryDocument | UploadDocument | RunSectionDocument | AnalysisDocument;

export const parseDirectoryDocument = (value: unknown): DirectoryDocument =>
  parse(DirectoryDocument, value);
export const parseUploadDocument = (value: unknown): UploadDocument => parse(UploadDocument, value);
export const parseRunSectionDocument = (value: unknown): RunSectionDocument =>
  parse(RunSectionDocument, value);
export const parseAnalysisDocument = (value: unknown): AnalysisDocument =>
  parse(AnalysisDocument, value);
export const parseRefusalBody = (value: unknown): RefusalBody => parse(RefusalBody, value);

export class WireIdentityError extends Error {
  readonly code = "WIRE_IDENTITY_MISMATCH";
  constructor() {
    super("WIRE_IDENTITY_MISMATCH");
    this.name = "WireIdentityError";
  }
}

function sameId(a: string | null | undefined, b: string | null | undefined): boolean {
  return (a ?? null)?.toLowerCase() === (b ?? null)?.toLowerCase();
}

/**
 * Refuse a document answering for another case or run than the one requested.
 * `caseId: null` is the case-less directory. `runId`, when given, must be the
 * displayed run; the latest run is a separate identity and is not compared.
 */
export function requireIdentity(
  doc: SectionDocument,
  expected: { caseId: string | null; runId?: string | null },
): void {
  const subject = doc.chrome.subject;
  if (!sameId(subject?.case_id, expected.caseId)) throw new WireIdentityError();
  if ("case_id" in doc.body && !sameId(doc.body.case_id, expected.caseId)) {
    throw new WireIdentityError();
  }
  if (expected.runId !== undefined) {
    if (!("displayed_run_id" in doc.body)) throw new WireIdentityError();
    if (!sameId(doc.body.displayed_run_id, expected.runId)) throw new WireIdentityError();
  }
}
