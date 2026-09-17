// The application entry point is the only root. A component under
// `src/sections/` that nothing reachable from `src/main.tsx` imports is dead
// even when a test names it -- the test is what keeps it alive, and the
// untested-definition gate cannot tell that case from a covered one. This is
// the rule `frontend/scripts/check-tested.mjs` enforces in `npm run lint`;
// here it is asserted where the `typescript` it imports is installed.
import { readdirSync } from "node:fs";
import { relative, resolve } from "node:path";
import { importGraph } from "../../scripts/check-tested.mjs";

const SRC = resolve(process.cwd(), "src");

function components(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = resolve(directory, entry.name);
    if (entry.isDirectory()) return components(full);
    return entry.name.endsWith(".tsx") ? [full] : [];
  });
}

test("test_every_component_under_sections_is_reachable_from_main", () => {
  const graph = importGraph(resolve(SRC, "main.tsx"), SRC);
  const unreachable = components(resolve(SRC, "sections"))
    .filter((file) => !graph.has(file))
    .map((file) => relative(SRC, file));
  expect(unreachable).toEqual([]);
});

test("the graph follows `@/` and relative specifiers alike, and stops at a file it cannot resolve", () => {
  const graph = importGraph(resolve(SRC, "main.tsx"), SRC);
  expect(graph.has(resolve(SRC, "app/App.tsx"))).toBe(true);
  expect(graph.has(resolve(SRC, "chrome/Rail.tsx"))).toBe(true);
  expect(graph.has(resolve(SRC, "styles/caos.css"))).toBe(true);
  expect(importGraph(resolve(SRC, "does-not-exist.tsx"), SRC).size).toBe(0);
});
