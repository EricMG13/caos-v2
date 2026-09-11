// One transport for every section document. A response becomes a RegionStatus,
// never an exception: the seven states of IA_SPEC.md 6 plus `ready`.
import { keysMatch } from "@/wire/keys";
import type { AnyDocument, Refusal, Section } from "@/wire";

export type RegionStatus<D = AnyDocument> =
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
  fixture?: string | null;
}

export function sectionUrl(section: Section, query: SectionQuery): string {
  const params = new URLSearchParams();
  if (query.case) params.set("case", query.case);
  if (query.fixture) params.set("fixture", query.fixture);
  const search = params.toString();
  return `/api/sections/${section}${search ? `?${search}` : ""}`;
}

function refusalOf(body: unknown): Refusal {
  if (
    typeof body === "object" &&
    body !== null &&
    typeof (body as Refusal).code === "string" &&
    typeof (body as Refusal).clears === "string"
  ) {
    return { code: (body as Refusal).code, clears: (body as Refusal).clears };
  }
  return { code: "RESPONSE_INVALID", clears: "the server answers with a typed refusal" };
}

async function bodyOf(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function classify(document: unknown): RegionStatus {
  if (typeof document !== "object" || document === null || Array.isArray(document)) {
    return { kind: "error", refusal: refusalOf(null) };
  }
  const record = document as Record<string, unknown>;
  if (!keysMatch(record)) {
    return {
      kind: "error",
      refusal: { code: "WIRE_KEYS_MISMATCH", clears: "the document carries the pinned keys" },
    };
  }
  const typed = record as unknown as AnyDocument;
  if (typed.observed_empty === true) {
    if (typeof typed.observed_at !== "string" || typed.observed_at === "") {
      return {
        kind: "error",
        refusal: {
          code: "OBSERVED_EMPTY_UNTIMED",
          clears: "an observed-empty response carries the time it was observed",
        },
      };
    }
    return { kind: "observed-empty", observed_at: typed.observed_at, document: typed };
  }
  if (typed.status === "partial") {
    return { kind: "partial", document: typed, notes: typed.notes ?? [] };
  }
  return { kind: "ready", document: typed };
}

export async function fetchSection(
  section: Section,
  query: SectionQuery,
  signal?: AbortSignal,
): Promise<RegionStatus> {
  let response: Response;
  try {
    response = await fetch(sectionUrl(section, query), {
      signal,
      headers: { accept: "application/json" },
    });
  } catch {
    // A request that never reached the server. No engine text.
    return { kind: "offline" };
  }
  if (response.status === 404) return { kind: "unavailable" };
  if (!response.ok) return { kind: "error", refusal: refusalOf(await bodyOf(response)) };
  return classify(await bodyOf(response));
}
