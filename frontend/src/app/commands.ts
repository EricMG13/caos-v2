// The minimal governed command wiring the journey needs (brief 4.2, decision
// 12). One `crypto.randomUUID()` key per user intent: reused when the caller
// retries the same intent after a network failure, and replaced by the
// caller after any server answer (success or refusal) for the next intent.
//
// Every result is a discriminated union, never an exception the caller must
// catch: `ok` (a validated receipt), `refused` (a typed refusal with its
// clearance), `error` (a body that is neither) or `offline` (the request
// never reached the server). Nothing parsed here is cast — every receipt is
// narrowed by its matching v1 parser.
import type {
  ApproveGate,
  CancelRun,
  CaseCreated,
  CreateCase,
  CreateRun,
  GateApproved,
  GatePreviewDocument,
  Infer,
  PinRunInput,
  RunCreated,
  RunInputPinned,
  RunWork,
} from "@/wire/v1";
import {
  WireShapeError,
  parseCaseCreated,
  parseGateApproved,
  parseGatePreviewDocument,
  parseRefusalBody,
  parseRunCreated,
  parseRunInputPinned,
  parseRunWork,
  parseSourcesAdmitted,
  type RefusalBody,
  type SourcesAdmitted,
  type V1_SHAPES,
} from "@/wire/v1";

/** Drawn from the shared shapes rather than redeclared here. */
type Gate = Infer<typeof V1_SHAPES.Gate>;
type RunSubjectView = Infer<typeof V1_SHAPES.RunSubjectView>;

/** One key per user intent. Reuse it to retry after `{ kind: "offline" }`;
    draw a fresh one (`newIntent`) once any server answer has been seen. */
export interface Intent {
  readonly key: string;
}

export function newIntent(): Intent {
  return { key: crypto.randomUUID() };
}

export type CommandResult<R> =
  | { kind: "ok"; status: number; receipt: R; replayed: boolean }
  | { kind: "refused"; refusal: RefusalBody }
  | { kind: "error"; code: "RESPONSE_INVALID" }
  | { kind: "offline" };

interface CommandRequest {
  method: "GET" | "POST";
  url: string;
  body?: BodyInit;
  contentType?: string;
}

const RESPONSE_INVALID = { kind: "error", code: "RESPONSE_INVALID" } as const;

async function bodyOf(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

/** The primitive every command below builds on: one fetch, classified into
    the four-way result above. A POST carries the intent's key; a GET (the
    gate preview) carries none, since it makes no governed write to replay. */
export async function sendCommand<R>(
  intent: Intent,
  request: CommandRequest,
  parseReceipt: (value: unknown) => R,
): Promise<CommandResult<R>> {
  const headers: Record<string, string> = { accept: "application/json" };
  if (request.contentType !== undefined) headers["content-type"] = request.contentType;
  if (request.method === "POST") headers["Idempotency-Key"] = intent.key;

  let response: Response;
  try {
    response = await fetch(request.url, {
      method: request.method,
      headers,
      ...(request.body === undefined ? {} : { body: request.body }),
    });
  } catch {
    return { kind: "offline" };
  }

  const body = await bodyOf(response);
  if (response.ok) {
    try {
      return {
        kind: "ok",
        status: response.status,
        receipt: parseReceipt(body),
        replayed: response.headers.get("Idempotency-Replayed") === "true",
      };
    } catch (error) {
      if (error instanceof WireShapeError) return RESPONSE_INVALID;
      throw error;
    }
  }
  try {
    return { kind: "refused", refusal: parseRefusalBody(body) };
  } catch (error) {
    if (error instanceof WireShapeError) return RESPONSE_INVALID;
    throw error;
  }
}

function jsonCommand<R>(
  intent: Intent,
  url: string,
  request: object,
  parseReceipt: (value: unknown) => R,
): Promise<CommandResult<R>> {
  return sendCommand(
    intent,
    { method: "POST", url, body: JSON.stringify(request), contentType: "application/json" },
    parseReceipt,
  );
}

const GATE_SLUG: Record<Gate, string> = {
  SOURCE_SET: "source-set",
  RESEARCH_PLAN: "research-plan",
};

function casePath(caseId: string): string {
  return `/api/v1/cases/${encodeURIComponent(caseId)}`;
}

function runPath(caseId: string, runId: string): string {
  return `${casePath(caseId)}/runs/${encodeURIComponent(runId)}`;
}

export function createCase(
  title: CreateCase["title"],
  intent: Intent = newIntent(),
): Promise<CommandResult<CaseCreated>> {
  return jsonCommand(intent, "/api/v1/cases", { title }, parseCaseCreated);
}

/** Multipart, with every file carried as a `document` part; brief 4.2
    decision 4. The browser draws its own boundary, so no content type is
    declared here. */
export function admitSources(
  caseId: string,
  files: readonly File[],
  intent: Intent = newIntent(),
): Promise<CommandResult<SourcesAdmitted>> {
  const form = new FormData();
  for (const file of files) form.append("document", file);
  return sendCommand(
    intent,
    { method: "POST", url: `${casePath(caseId)}/sources`, body: form },
    parseSourcesAdmitted,
  );
}

export function createRun(
  caseId: string,
  request: CreateRun,
  intent: Intent = newIntent(),
): Promise<CommandResult<RunCreated>> {
  return jsonCommand(intent, `${casePath(caseId)}/runs`, request, parseRunCreated);
}

export function pinRunInput(
  caseId: string,
  runId: string,
  subject: RunSubjectView,
  intent: Intent = newIntent(),
): Promise<CommandResult<RunInputPinned>> {
  const request: PinRunInput = { subject };
  return jsonCommand(intent, `${runPath(caseId, runId)}/input`, request, parseRunInputPinned);
}

/** The one GET among these commands: a preview grants nothing and carries no
    idempotency key (brief 4.2, decisions 1 and 6). */
export function fetchGatePreview(
  caseId: string,
  runId: string,
  gate: Gate,
  intent: Intent = newIntent(),
): Promise<CommandResult<GatePreviewDocument>> {
  const url = `${runPath(caseId, runId)}/gates/${GATE_SLUG[gate]}/preview`;
  return sendCommand(intent, { method: "GET", url }, parseGatePreviewDocument);
}

export function approveGate(
  caseId: string,
  runId: string,
  gate: Gate,
  approval: ApproveGate,
  intent: Intent = newIntent(),
): Promise<CommandResult<GateApproved>> {
  const url = `${runPath(caseId, runId)}/gates/${GATE_SLUG[gate]}/approval`;
  return jsonCommand(intent, url, approval, parseGateApproved);
}

export function startRun(
  caseId: string,
  runId: string,
  request: { input_fingerprint: string },
  intent: Intent = newIntent(),
): Promise<CommandResult<RunWork>> {
  return jsonCommand(intent, `${runPath(caseId, runId)}/start`, request, parseRunWork);
}

export function retryRun(
  caseId: string,
  runId: string,
  request: { input_fingerprint: string },
  intent: Intent = newIntent(),
): Promise<CommandResult<RunWork>> {
  return jsonCommand(intent, `${runPath(caseId, runId)}/retry`, request, parseRunWork);
}

export function cancelRun(
  caseId: string,
  runId: string,
  intent: Intent = newIntent(),
): Promise<CommandResult<RunWork>> {
  const request: CancelRun = {};
  return jsonCommand(intent, `${runPath(caseId, runId)}/cancel`, request, parseRunWork);
}
