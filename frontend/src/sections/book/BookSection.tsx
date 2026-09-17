// Book, /book/ (IA_SPEC.md 4.4). The section is unavailable in every mode
// (`@/app/sections`): the workspace sends no request for it and opens no tail,
// so this view is never mounted with a document, and what a reader sees in the
// body is the one `unavailable` surface `RegionState` renders in its place --
// which `tests/workbench/chrome.spec.ts` asserts for every disabled section.
// The registry types one view per section, so this shell is what stands here.
// The portfolio table, the comparison and its facets were reduced to it on the
// owner's D2 decision of 17 September 2026; git holds them for the day a
// deployment serves the section.
export function BookSection() {
  // ponytail: null, not a second unavailable surface. The region already
  // renders exactly one, and the chrome suite asserts exactly one.
  return null;
}
