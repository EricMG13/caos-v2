// Every route the gates drive: the nine sections in their default fixture, the
// fixture states each section must render distinctly, and the two page-level
// wordings. One list, so the a11y matrix and the workbench share it.
export const SECTIONS = [
  "directory",
  "upload",
  "analysis",
  "book",
  "run",
  "model",
  "report",
  "committee",
  "admin",
];

/** The four sections served in every mode; the other five render `unavailable`
    with no request (brief 4.1, decision 9). Mirrors src/app/sections.ts. */
export const ENABLED_SECTIONS = ["directory", "upload", "run", "analysis"];
export const DISABLED_SECTIONS = SECTIONS.filter((section) => !ENABLED_SECTIONS.includes(section));

/** The demo fixtures' case, for a section still on the legacy wire. A case
    section with no case sends no request. */
export const DEMO_CASE = "CASE-2026-CVNA01";

/** Upload's v1 fixture (slice 4.1h) carries the case as a UUID; Run and
    Analysis stay on the legacy string until their own slices cut over. */
export const DEMO_CASE_BY_SECTION = { upload: "ff1fbf5a-e56f-4f84-a983-2f5a507675f0" };

/** A section's page, with the demo case where the section is case-scoped.
    @param {string} section
    @param {string | null} [fixture] */
export function sectionRoute(section, fixture = null) {
  const params = new URLSearchParams();
  if (["upload", "run", "analysis"].includes(section)) {
    params.set("case", DEMO_CASE_BY_SECTION[section] ?? DEMO_CASE);
  }
  if (fixture) params.set("fixture", fixture);
  const search = params.toString();
  return `/${section}/${search ? `?${search}` : ""}`;
}

export const STATE_ROUTES = [
  sectionRoute("directory", "observed-empty"),
  sectionRoute("upload", "partial"),
  sectionRoute("analysis", "partial"),
  sectionRoute("analysis", "stale"),
  sectionRoute("analysis", "offline"),
  sectionRoute("analysis", "unavailable"),
  sectionRoute("analysis", "error"),
  sectionRoute("run", "gate"),
  "/analysis/",
  "/nothing/",
];

export const ROUTES = [...SECTIONS.map((section) => sectionRoute(section)), ...STATE_ROUTES];

export const VIEWPORTS = ["1440x900", "1280x800", "1024x768"];
export const ENGINES = ["chromium", "firefox", "webkit"];

/** The page has settled: the loading marker is gone and either the chrome
    or a state region is on screen. Both are required, so a skeleton is never
    scanned as a page. */
export const LOADING = "main#body [data-surface-state='loading']";
export const SETTLED = "header.ribbon, main#body [data-surface-state]";
