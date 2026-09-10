// The pinned key set of a section document, the client half of `extra="forbid"`.
// A document whose top-level keys are not a subset of PINNED_KEYS that still
// includes REQUIRED_KEYS is refused with WIRE_KEYS_MISMATCH before rendering.
export const REQUIRED_KEYS = ["chrome", "body", "observed_at"] as const;
export const PINNED_KEYS = [...REQUIRED_KEYS, "observed_empty", "status", "notes"] as const;

export const CHROME_KEYS = [
  "subject",
  "ribbon",
  "brief",
  "tabs",
  "verdict",
  "rail",
  "rail_local",
  "served_role",
] as const;

export function keysMatch(document: Record<string, unknown>): boolean {
  const keys = Object.keys(document);
  const pinned = new Set<string>(PINNED_KEYS);
  const requiredPresent = REQUIRED_KEYS.every((key) => key in document);
  const chrome = document["chrome"];
  const chromeOk =
    typeof chrome === "object" &&
    chrome !== null &&
    CHROME_KEYS.every((key) => key in chrome) &&
    Object.keys(chrome).every((key) => (CHROME_KEYS as readonly string[]).includes(key));
  return requiredPresent && chromeOk && keys.every((key) => pinned.has(key));
}
