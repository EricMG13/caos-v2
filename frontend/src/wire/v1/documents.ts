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
  type Shape,
} from "./shape";

const SHORT = 256;
const TEXT = 4096;
const hash = string({ max: 64, pattern: "^[0-9a-f]{64}$" });
const short = string({ max: SHORT });
const text = string({ max: TEXT });
const RUN_STATUSES = ["RUNNING", "COMPLETE", "FAILED", "BLOCKED", "CANCELLED"] as const;

const GlobalRole = enumOf(["READER", "ANALYST", "ADMIN"]);
const Standing = enumOf(["READER", "WRITER", "APPROVER", "ADMIN"]);
const SectionNote = enumOf(["LIST_TRUNCATED", "ROUTE_NOT_PINNED", "HANDOFFS_PENDING"]);
const NodeState = enumOf(["COMPLETE", "RUNNABLE", "RESTRICTED", "BLOCKED"]);
const EdgeType = enumOf(["REQUIRED", "CONDITIONAL", "QA_GATE", "OPTIONAL", "ADVISORY"]);
const Gate = enumOf(["SOURCE_SET", "RESEARCH_PLAN"]);
const GateState = enumOf(["OPEN", "RELEASED"]);

/** A shape declared further down this file, resolved only when first used. */
function later<T>(get: () => Shape<T>): Shape<T> {
  return {
    check: (value, path): value is T => get().check(value, path),
    toSchema: () => get().toSchema(),
  };
}

const ActionName = enumOf([
  "CREATE_CASE",
  "ADMIT_SOURCES",
  "CREATE_RUN",
  "PIN_RUN_INPUT",
  "APPROVE_SOURCE_SET",
  "APPROVE_RESEARCH_PLAN",
  "START_RUN",
  "RETRY_RUN",
  "CANCEL_RUN",
]);

const Subject = object({ case_id: uuid, title: text });
const ServedRole = object({ global_role: GlobalRole, standing: nullable(Standing) });
// Server-computed and advisory: a refused action is shown with its code, and
// the command rechecks at commit (brief 4.2, decision 10).
const ActionView = object({
  action: ActionName,
  refusal: nullable(later(() => RefusalBody)),
});
const Chrome = object({
  subject: nullable(Subject),
  served_role: ServedRole,
  actions: array(ActionView, 9),
});

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
const WorkView = object({
  state: enumOf(["QUEUED", "CLAIMED", "STOPPED", "DONE"]),
  stop_code: nullable(later(() => RefusalCode)),
  cancel_requested: bool,
});
const RouteChoice = object({ profile_id: short, selection_id: short });
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
  work: nullable(WorkView),
});
const RunBody = object({
  case_id: uuid,
  latest_run_id: nullable(uuid),
  displayed_run_id: nullable(uuid),
  runs: array(RunSummary, 200),
  run: nullable(RunView),
  route_choices: array(RouteChoice, 16),
});
const RunSectionDocument = sectionDocument(RunBody);

const RectView = object({ x0: number, y0: number, x1: number, y1: number });
const CitationView = object({
  document_sha256: hash,
  source_id: uuid,
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

const ModelValue = object({
  name: short,
  value: nullable(string({ max: 64, pattern: "^-?[0-9]+(\\.[0-9]+)?$" })),
  unavailable_reason: nullable(literal("ZERO_OR_NEGATIVE_DENOMINATOR")),
});
const ModelPeriod = object({
  case: text,
  period_id: text,
  fiscal_year: text,
  days: string({ max: 3, pattern: "^[0-9]+$" }),
  values: array(ModelValue, 40),
  unavailable_reason: nullable(text),
});
const ModelForecast = object({
  route_node_id: short,
  artifact_sha256: hash,
  record_sha256: hash,
  accepted_at: datetime,
  qa_status: short,
  limitation_flags: array(text, 256),
  validation_warnings: array(text, 256),
  currency: string({ max: 3, pattern: "^[A-Z]{3}$" }),
  scale: enumOf(["units", "thousands", "millions", "billions"]),
  perimeter: text,
  periods: array(ModelPeriod, 240),
});
const ModelBody = object({
  case_id: uuid,
  latest_run_id: nullable(uuid),
  displayed_run_id: nullable(uuid),
  subject: nullable(RunSubjectView),
  forecast: nullable(ModelForecast),
  unavailable_reason: nullable(literal("NO_ACCEPTED_FORECAST")),
});
const ModelDocument = sectionDocument(ModelBody);

const NarrativeFigure = object({
  route_node_id: short,
  citation_index: int({ min: 0 }),
  document_sha256: hash,
  page: int({ min: 1 }),
  matched_text: string({ max: 65536 }),
});
const NarrativeSpan = object({
  text: nullable(string({ max: 2000 })),
  figure: nullable(NarrativeFigure),
});
const ReportArtifact = object({
  route_node_id: short,
  artifact_sha256: hash,
  record_sha256: hash,
  markdown: string({ max: 26214400 }),
  record: string({ max: 26214400 }),
  qa_status: short,
  committee_status: short,
  decision_scope: short,
  limitation_flags: array(text, 256),
  validation_warnings: array(text, 256),
});
const reportFields = {
  case_id: uuid,
  displayed_run_id: uuid,
  revision_id: uuid,
  payload_sha256: hash,
  case_title: text,
  artifacts: array(ReportArtifact, 256),
  narrative: array(array(NarrativeSpan, 64), 64),
};
const ReportBody = object(reportFields);
const ReportDocument = sectionDocument(ReportBody);
const FiledReceipt = object({
  case_id: uuid,
  run_id: uuid,
  revision_id: uuid,
  payload_sha256: hash,
  signed_by: uuid,
  frozen_by: uuid,
  filed_by: uuid,
  renderer_sha256: hash,
  filed_event_sha256: hash,
});
const CommitteeBody = object({
  ...reportFields,
  state: enumOf(["frozen", "filed"]),
  signed_by: array(uuid, 1000),
  frozen_by: uuid,
  filed_by: nullable(uuid),
  receipt: nullable(FiledReceipt),
});
const CommitteeDocument = sectionDocument(CommitteeBody);

// Events and evidence pages (brief 4.4, decisions 2, 7 and 8).
/** The closed event names a case stream carries; a name only says what to refetch. */
export const EVENT_NAMES = [
  "run_progress",
  "handoff_accepted",
  "run_terminal",
  "sources_changed",
  "runs_changed",
] as const;
const EventName = enumOf(EVENT_NAMES);
const FrameView = object({
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  y_axis: enumOf(["down", "up"]),
});
const PageLine = object({
  text: string({ max: 65536 }),
  x0: number,
  y0: number,
  x1: number,
  y1: number,
});
const PageBody = object({
  case_id: uuid,
  run_id: uuid,
  source_id: uuid,
  document_sha256: hash,
  page: int({ min: 1, max: 500 }),
  frame: FrameView,
  lines: array(PageLine, 2000),
});
// Not a section document: no chrome.
const PageDocument = object({
  body: PageBody,
  observed_at: datetime,
  status: enumOf(["complete", "partial"]),
  notes: array(SectionNote, 3),
});

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
  "EDGE_NOT_TRUSTED",
  "ORIGIN_REFUSED",
  "EDGE_CONFIG_INVALID",
  "INTERNAL_FAULT",
  "NOT_AUTHORISED",
  "REQUEST_INVALID",
  "IDEMPOTENCY_KEY_REQUIRED",
  "IDEMPOTENCY_KEY_REUSED",
  "RUN_INPUT_NOT_PINNED",
  "RUN_ALREADY_STARTED",
  "RUN_NOT_STOPPED",
  "ROUTE_NOT_ENABLED",
  "COMMAND_EXPECTATION_STALE",
  "METHODOLOGY_INPUT_INVALID",
  "FORECAST_CHAIN_BROKEN",
  "FORECAST_RESIDUAL_UNRECONCILED",
  "FORECAST_DRIVER_NOT_READY",
  "DELIVERABLE_PAYLOAD_INVALID",
  "DELIVERABLE_NOT_FOUND",
  "NARRATIVE_FIGURE_UNREFERENCED",
  "NARRATIVE_REFERENCE_INVALID",
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
  "PAGE_NOT_AVAILABLE",
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
  NarrativeFigure,
  NarrativeSpan,
  ReportArtifact,
  ReportBody,
  ReportDocument,
  FiledReceipt,
  CommitteeBody,
  CommitteeDocument,
  ModelValue,
  ModelPeriod,
  ModelForecast,
  ModelBody,
  ModelDocument,
  ActionName,
  ActionView,
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
  EventName,
  FrameView,
  Gate,
  GateState,
  GateView,
  GlobalRole,
  HandoffView,
  NodeState,
  NodeView,
  PageBody,
  PageDocument,
  PageLine,
  PendingNode,
  RectView,
  RefusalBody,
  RefusalCode,
  RouteChoice,
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
  WorkView,
};

export type DirectoryDocument = Infer<typeof DirectoryDocument>;
export type UploadDocument = Infer<typeof UploadDocument>;
export type RunSectionDocument = Infer<typeof RunSectionDocument>;
export type AnalysisDocument = Infer<typeof AnalysisDocument>;
export type ModelDocument = Infer<typeof ModelDocument>;
export type ReportDocument = Infer<typeof ReportDocument>;
export type CommitteeDocument = Infer<typeof CommitteeDocument>;
export type RefusalBody = Infer<typeof RefusalBody>;
export type RefusalCode = Infer<typeof RefusalCode>;
export type Chrome = Infer<typeof Chrome>;
export type CaseRow = Infer<typeof CaseRow>;
export type SourceRow = Infer<typeof SourceRow>;
export type RunView = Infer<typeof RunView>;
export type NodeView = Infer<typeof NodeView>;
export type HandoffView = Infer<typeof HandoffView>;
export type CitationView = Infer<typeof CitationView>;
export type PendingNode = Infer<typeof PendingNode>;
export type EventName = Infer<typeof EventName>;
export type FrameView = Infer<typeof FrameView>;
export type PageLine = Infer<typeof PageLine>;
export type PageDocument = Infer<typeof PageDocument>;
export type ActionView = Infer<typeof ActionView>;
export type WorkView = Infer<typeof WorkView>;
export type RouteChoice = Infer<typeof RouteChoice>;
export type SectionDocument =
  | DirectoryDocument
  | UploadDocument
  | RunSectionDocument
  | AnalysisDocument
  | ModelDocument
  | ReportDocument
  | CommitteeDocument;

export const parseDirectoryDocument = (value: unknown): DirectoryDocument =>
  parse(DirectoryDocument, value);
export const parseUploadDocument = (value: unknown): UploadDocument => parse(UploadDocument, value);
export const parseRunSectionDocument = (value: unknown): RunSectionDocument =>
  parse(RunSectionDocument, value);
export const parseAnalysisDocument = (value: unknown): AnalysisDocument =>
  parse(AnalysisDocument, value);
export const parseModelDocument = (value: unknown): ModelDocument => parse(ModelDocument, value);
export const parseReportDocument = (value: unknown): ReportDocument => parse(ReportDocument, value);
export const parseCommitteeDocument = (value: unknown): CommitteeDocument =>
  parse(CommitteeDocument, value);
export const parseRefusalBody = (value: unknown): RefusalBody => parse(RefusalBody, value);
export const parsePageDocument = (value: unknown): PageDocument => parse(PageDocument, value);

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
  expected: { caseId: string | null; runId?: string | null; revisionId?: string },
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
  if (expected.revisionId !== undefined) {
    if (!("revision_id" in doc.body) || !sameId(doc.body.revision_id, expected.revisionId)) {
      throw new WireIdentityError();
    }
  }
  if ("receipt" in doc.body && doc.body.receipt !== null) {
    const receipt = doc.body.receipt;
    if (
      !sameId(receipt.case_id, doc.body.case_id) ||
      !sameId(receipt.run_id, doc.body.displayed_run_id) ||
      !sameId(receipt.revision_id, doc.body.revision_id) ||
      receipt.payload_sha256 !== doc.body.payload_sha256
    )
      throw new WireIdentityError();
  }
}

/** Refuse an evidence page answering for another case, run, source or page. */
export function requirePageIdentity(
  doc: PageDocument,
  expected: { caseId: string; runId: string; sourceId: string; page: number },
): void {
  const body = doc.body;
  if (
    !sameId(body.case_id, expected.caseId) ||
    !sameId(body.run_id, expected.runId) ||
    !sameId(body.source_id, expected.sourceId) ||
    body.page !== expected.page
  ) {
    throw new WireIdentityError();
  }
}
