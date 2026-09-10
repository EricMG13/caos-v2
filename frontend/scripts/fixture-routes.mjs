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

export const STATE_ROUTES = [
  "/directory/?fixture=observed-empty",
  "/upload/?fixture=partial",
  "/analysis/?fixture=partial",
  "/analysis/?fixture=stale",
  "/analysis/?fixture=offline",
  "/analysis/?fixture=unavailable",
  "/analysis/?fixture=error",
  "/book/?fixture=observed-empty",
  "/run/?fixture=gate",
  "/committee/?fixture=reader",
  "/committee/?fixture=filed",
  "/nothing/",
];

export const ROUTES = [...SECTIONS.map((section) => `/${section}/`), ...STATE_ROUTES];

export const VIEWPORTS = ["1440x900", "1280x800", "1024x768"];
export const ENGINES = ["chromium", "firefox", "webkit"];

/** The page has settled: the loading marker is gone and either the chrome
    or a state region is on screen. Both are required, so a skeleton is never
    scanned as a page. */
export const LOADING = "main#body [data-surface-state='loading']";
export const SETTLED = "header.ribbon, main#body [data-surface-state]";
