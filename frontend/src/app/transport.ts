// One transport for every section document. A response becomes a RegionStatus,
// never an exception: the seven states of IA_SPEC.md 6 plus `ready`.
//
// URLs are versioned and case-scoped (brief 4.1, decision 1). A section reads
// the v1 wire only when its `sections/<s>/wire.ts` marker says so; until then
// its document keeps the legacy key check. Nothing parsed here is cast: every
// body is narrowed by a validator or a type predicate.
import { isEnabledSection, type EnabledSection } from "./sections";
import { WIRE as ANALYSIS_WIRE } from "@/sections/analysis/wire";
import { WIRE as DIRECTORY_WIRE } from "@/sections/directory/wire";
import { WIRE as RUN_WIRE } from "@/sections/run/wire";
import { WIRE as UPLOAD_WIRE } from "@/sections/upload/wire";
import { keysMatch } from "@/wire/keys";
import type { AnyDocument, Refusal, Section } from "@/wire";
import {
  WireIdentityError,
  WireShapeError,
  parseAnalysisDocument,
  parseDirectoryDocument,
  parseRefusalBody,
  parseRunSectionDocument,
  parseUploadDocument,
  requireIdentity,
  type SectionDocument as V1Document,
} from "@/wire/v1";

/** What a section region can hold while the legacy and v1 wires coexist. */
export type WorkspaceDocument = AnyDocument | V1Document;

export type RegionStatus<D = WorkspaceDocument> =
  | { kind: "loading" }
  | { kind: "ready"; document: D }
  | { kind: "observed-empty"; observed_at: string; document: D }
  | { kind: "error"; refusal: Refusal }
  | { kind: "unavailable" }
  | { kind: "stale"; document: D }
  | { kind: "offline" }
  | { kind: "partial"; document: D; notes: string[] };

export type StateKind = RegionStatus["kind"];

/** A private 404 and an absent route share one neutral wording. */
export const UNAVAILABLE_WORDING = "Unavailable or not permitted.";
/** An offline request renders one sentence and never engine text. */
export const OFFLINE_WORDING = "The request did not reach the server.";

export interface SectionQuery {
  case?: string | null;
  run?: string | null;
  fixture?: string | null;
}

const WIRES: Record<EnabledSection, "legacy" | "v1"> = {
  directory: DIRECTORY_WIRE,
  upload: UPLOAD_WIRE,
  run: RUN_WIRE,
  analysis: ANALYSIS_WIRE,
};

const V1_PARSERS: Record<EnabledSection, (value: unknown) => V1Document> = {
  directory: parseDirectoryDocument,
  upload: parseUploadDocument,
  run: parseRunSectionDocument,
  analysis: parseAnalysisDocument,
};

/** The section's document URL, or null when no request may be sent: a
    disabled section, or a case section with no case. */
export function sectionUrl(section: Section, query: SectionQuery): string | null {
  if (!isEnabledSection(section)) return null;
  const params = new URLSearchParams();
  if ((section === "run" || section === "analysis") && query.run) params.set("run", query.run);
  // Only the demo build names a fixture; production folds this branch away.
  if (import.meta.env.MODE === "demo" && query.fixture) params.set("fixture", query.fixture);
  const search = params.toString();
  const suffix = search ? `?${search}` : "";
  if (section === "directory") return `/api/v1/directory${suffix}`;
  if (!query.case) return null;
  return `/api/v1/cases/${encodeURIComponent(query.case)}/${section}${suffix}`;
}

const RESPONSE_INVALID: Refusal = {
  code: "RESPONSE_INVALID",
  clears: "the server answers with a typed refusal",
};

function refusalOf(body: unknown): Refusal {
  try {
    const refusal = parseRefusalBody(body);
    return { code: refusal.code, clears: refusal.clears };
  } catch (error) {
    if (error instanceof WireShapeError) return RESPONSE_INVALID;
    throw error;
  }
}

async function bodyOf(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isLegacyDocument(
  value: Record<string, unknown>,
): value is Record<string, unknown> & AnyDocument {
  return keysMatch(value);
}

/** The legacy wire: the pinned top-level and chrome keys, nothing deeper. */
export function classify(document: unknown): RegionStatus<AnyDocument> {
  if (!isRecord(document)) return { kind: "error", refusal: RESPONSE_INVALID };
  if (!isLegacyDocument(document)) {
    return {
      kind: "error",
      refusal: { code: "WIRE_KEYS_MISMATCH", clears: "the document carries the pinned keys" },
    };
  }
  if (document.observed_empty === true) {
    if (typeof document.observed_at !== "string" || document.observed_at === "") {
      return {
        kind: "error",
        refusal: {
          code: "OBSERVED_EMPTY_UNTIMED",
          clears: "an observed-empty response carries the time it was observed",
        },
      };
    }
    return { kind: "observed-empty", observed_at: document.observed_at, document };
  }
  if (document.status === "partial") {
    return { kind: "partial", document, notes: document.notes ?? [] };
  }
  return { kind: "ready", document };
}

/** The v1 wire: the whole document validated, then bound to the request. */
function classifyV1(section: EnabledSection, body: unknown, query: SectionQuery): RegionStatus {
  let document: V1Document;
  try {
    document = V1_PARSERS[section](body);
    const runId = section === "run" || section === "analysis" ? query.run : null;
    requireIdentity(document, {
      caseId: section === "directory" ? null : (query.case ?? null),
      ...(runId ? { runId } : {}),
    });
  } catch (error) {
    if (error instanceof WireShapeError) {
      return {
        kind: "error",
        refusal: { code: "WIRE_SHAPE_INVALID", clears: "the document is the declared v1 shape" },
      };
    }
    if (error instanceof WireIdentityError) {
      return {
        kind: "error",
        refusal: {
          code: "WIRE_IDENTITY_MISMATCH",
          clears: "the document answers for the case and run requested",
        },
      };
    }
    throw error;
  }
  if (document.observed_empty) {
    return { kind: "observed-empty", observed_at: document.observed_at, document };
  }
  if (document.status === "partial") {
    return { kind: "partial", document, notes: [...document.notes] };
  }
  return { kind: "ready", document };
}

export async function fetchSection(
  section: Section,
  query: SectionQuery,
  signal?: AbortSignal,
): Promise<RegionStatus> {
  const url = sectionUrl(section, query);
  if (url === null || !isEnabledSection(section)) return { kind: "unavailable" };
  let response: Response;
  try {
    response = await fetch(url, { signal, headers: { accept: "application/json" } });
  } catch {
    // A request that never reached the server. No engine text.
    return { kind: "offline" };
  }
  if (response.status === 404) return { kind: "unavailable" };
  if (!response.ok) return { kind: "error", refusal: refusalOf(await bodyOf(response)) };
  const body = await bodyOf(response);
  return WIRES[section] === "v1" ? classifyV1(section, body, query) : classify(body);
}
