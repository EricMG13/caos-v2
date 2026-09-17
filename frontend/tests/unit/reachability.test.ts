// The application entry point is the only root. A component under
// `src/sections/` that nothing reachable from `src/main.tsx` imports is dead
// even when a test names it -- the test is what keeps it alive, and the
// untested-definition gate cannot tell that case from a covered one. This is
// the rule `frontend/scripts/check-tested.mjs` enforces in `npm run lint`;
// here it is asserted where the `typescript` it imports is installed.
import { mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, resolve } from "node:path";
import { importGraph, unreachableSections } from "../../scripts/check-tested.mjs";

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

test("a type-only import does not reach: the bundler erases it, so the file ships nothing", () => {
  const root = mkdtempSync(join(tmpdir(), "reach-"));
  mkdirSync(join(root, "sections"), { recursive: true });
  writeFileSync(
    join(root, "sections", "Planted.tsx"),
    "export function Planted() { return null; }\n",
  );
  writeFileSync(join(root, "sections", "Live.tsx"), "export function Live() { return null; }\n");
  writeFileSync(
    join(root, "main.tsx"),
    'import type { Planted } from "@/sections/Planted";\nimport { Live } from "./sections/Live";\nexport { Live };\nexport type { Planted };\n',
  );
  // A types-only module is erased whole, so it is reached by nothing and
  // ships nothing: not a finding.
  writeFileSync(join(root, "sections", "types.ts"), "export interface Shape {\n  id: string;\n}\n");
  const graph = importGraph(join(root, "main.tsx"), root);
  expect(graph.has(join(root, "sections", "Live.tsx"))).toBe(true);
  expect(graph.has(join(root, "sections", "Planted.tsx"))).toBe(false);
  const files = ["Live.tsx", "Planted.tsx", "types.ts"].map((name) => join(root, "sections", name));
  expect(unreachableSections(files, root)).toEqual([join(root, "sections", "Planted.tsx")]);
  rmSync(root, { recursive: true, force: true });
});
