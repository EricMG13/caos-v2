// The v1 command requests, receipts and the gate preview, one shape per model
// in `server/api/wire.py`'s `V1_COMMANDS` (brief 4.2, decision 11). Every
// receipt and preview is validated here before use; nothing is cast.
//
// A request carries no actor, case, run or approver: the server derives them
// from the caller and the path. Digests it carries are expectations.
import { V1_SHAPES } from "./documents";
import { type Infer, array, datetime, enumOf, int, object, parse, string, uuid } from "./shape";

const hash = string({ max: 64, pattern: "^[0-9a-f]{64}$" });
const short = string({ max: 256 });
const RUN_STATUSES = ["RUNNING", "COMPLETE", "FAILED", "BLOCKED", "CANCELLED"] as const;

const CreateCase = object({ title: string({ max: 256 }) });
const CaseCreated = object({ case_id: uuid });
const SourcesAdmitted = object({ case_id: uuid, source_ids: array(uuid, 50) });
const CreateRun = object({ profile_id: short, selection_id: short });
const RunCreated = object({ case_id: uuid, run_id: uuid, route_digest: hash });
const PinRunInput = object({ subject: V1_SHAPES.RunSubjectView });
const RunInputPinned = object({ run_id: uuid, source_set_version: int(), input_fingerprint: hash });
const GatePreviewDocument = object({
  run_id: uuid,
  gate: V1_SHAPES.Gate,
  content: string({ max: 26214400 }),
  preview_sha256: hash,
  input_fingerprint: hash,
  observed_at: datetime,
});
const ApproveGate = object({ preview_sha256: hash, input_fingerprint: hash });
const GateApproved = object({
  run_id: uuid,
  gate: V1_SHAPES.Gate,
  preview_sha256: hash,
  input_fingerprint: hash,
});
const StartRun = object({ input_fingerprint: hash });
const RetryRun = object({ input_fingerprint: hash });
const CancelRun = object({});
const RunWork = object({
  run_id: uuid,
  run_status: enumOf(RUN_STATUSES),
  work: V1_SHAPES.WorkView,
});

/** Every command model `schema.json` declares, under its backend name. */
export const V1_COMMAND_SHAPES = {
  ApproveGate,
  CancelRun,
  CaseCreated,
  CreateCase,
  CreateRun,
  GateApproved,
  GatePreviewDocument,
  PinRunInput,
  RetryRun,
  RunCreated,
  RunInputPinned,
  RunWork,
  SourcesAdmitted,
  StartRun,
};

export type CreateCase = Infer<typeof CreateCase>;
export type CaseCreated = Infer<typeof CaseCreated>;
export type SourcesAdmitted = Infer<typeof SourcesAdmitted>;
export type CreateRun = Infer<typeof CreateRun>;
export type RunCreated = Infer<typeof RunCreated>;
export type PinRunInput = Infer<typeof PinRunInput>;
export type RunInputPinned = Infer<typeof RunInputPinned>;
export type GatePreviewDocument = Infer<typeof GatePreviewDocument>;
export type ApproveGate = Infer<typeof ApproveGate>;
export type GateApproved = Infer<typeof GateApproved>;
export type StartRun = Infer<typeof StartRun>;
export type RetryRun = Infer<typeof RetryRun>;
export type CancelRun = Infer<typeof CancelRun>;
export type RunWork = Infer<typeof RunWork>;

export const parseCaseCreated = (value: unknown): CaseCreated => parse(CaseCreated, value);
export const parseSourcesAdmitted = (value: unknown): SourcesAdmitted =>
  parse(SourcesAdmitted, value);
export const parseRunCreated = (value: unknown): RunCreated => parse(RunCreated, value);
export const parseRunInputPinned = (value: unknown): RunInputPinned => parse(RunInputPinned, value);
export const parseGatePreviewDocument = (value: unknown): GatePreviewDocument =>
  parse(GatePreviewDocument, value);
export const parseGateApproved = (value: unknown): GateApproved => parse(GateApproved, value);
export const parseRunWork = (value: unknown): RunWork => parse(RunWork, value);
