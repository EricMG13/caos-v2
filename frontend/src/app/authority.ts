// The one authority machine (IA_SPEC.md 5, "Route replay"). A forwarded slug,
// a back navigation and a cross-case race are all resolved here against stale
// responses: a late response for a case the user has left is discarded, and
// the Book binds one accepted snapshot per compared case. Pure; no I/O.
import type { Refusal } from "@/wire";

export interface Authority {
  /** The case on screen, or null when the section is not about one case. */
  case: string | null;
  /** Monotonic per navigation; a response carries the seq it was sent under. */
  seq: number;
  /** The snapshot each compared case is bound to, by case id. */
  bound: Readonly<Record<string, string>>;
}

export interface Ticket {
  case: string | null;
  seq: number;
}

export const INITIAL: Authority = { case: null, seq: 0, bound: {} };

export function navigate(authority: Authority, caseId: string | null): Authority {
  return { ...authority, case: caseId, seq: authority.seq + 1 };
}

/** A new request under the current case: only the latest issued one renders. */
export function issue(authority: Authority): Authority {
  return { ...authority, seq: authority.seq + 1 };
}

export function ticket(authority: Authority): Ticket {
  return { case: authority.case, seq: authority.seq };
}

/** True only for the response of the current (case, seq). Anything else is late. */
export function accepts(authority: Authority, sent: Ticket): boolean {
  return sent.seq === authority.seq && sent.case === authority.case;
}

export interface Binding {
  authority: Authority;
  refusal: Refusal | null;
}

/** Bind a compared case to the snapshot a response carries. A late response
    carrying a different snapshot for an already-bound case is refused. */
export function bind(authority: Authority, caseId: string, snapshot: string): Binding {
  const held = authority.bound[caseId];
  if (held !== undefined && held !== snapshot) {
    return {
      authority,
      refusal: {
        code: "SNAPSHOT_MISMATCH",
        clears: `The comparison stays on ${held} for ${caseId}; switch the lens explicitly to move it.`,
      },
    };
  }
  if (held === snapshot) return { authority, refusal: null };
  return {
    authority: { ...authority, bound: { ...authority.bound, [caseId]: snapshot } },
    refusal: null,
  };
}

/** An explicit lens switch is the only way a binding moves. */
export function release(authority: Authority, caseId: string): Authority {
  const bound = { ...authority.bound };
  delete bound[caseId];
  return { ...authority, bound };
}
