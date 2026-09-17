// The application entry point is the only root. A component under
// `src/sections/` that nothing reachable from `src/main.tsx` imports is dead
// even when a test names it -- the test is what keeps it alive, and the
// untested-definition gate cannot tell that case from a covered one. This is
// the rule `frontend/scripts/check-tested.mjs` enforces in `npm run lint`;
// here it is asserted where the `typescript` it imports is installed.
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve, sep } from "node:path";
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

// Book and Admin are unavailable in every mode (`src/app/sections.ts`), and on
// 17 September 2026 the owner decided to reduce both to the shell
// `tests/workbench/chrome.spec.ts` asserts rather than keep implementations
// nothing mounts. Their wire types and the Book's snapshot ledger went with
// them; git keeps the code for the day either section is served. The walk
// above cannot see this on its own: a `import type` is erased, so a retired
// wire module is unreachable and still shipped as a file, and a reduction that
// left one importer behind would compile clean. This is what says the deletion
// was complete rather than merely compiling.
// Both spellings of each: `src/wire/index.ts` reached its two by a relative
// specifier and `src/app/Workspace.tsx` reached the ledger by one, so a list
// of `@/` paths alone would have read clean over three live importers. No
// other `ledger`, `book` or `admin` module exists under `src/`.
const RETIRED = [
  ["@/app/ledger", "./ledger"],
  ["@/wire/book", "./book"],
  ["@/wire/admin", "./admin"],
];

function typescriptSources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = resolve(directory, entry.name);
    if (entry.isDirectory()) return typescriptSources(full);
    return /\.tsx?$/.test(entry.name) ? [full] : [];
  });
}

// `RETIRED` above is a list, and a list only sees what somebody wrote into it.
// The three wire modules this wave deleted were reachable from nothing, and
// neither the section walk above (scoped to `src/sections/`) nor the lint rule
// beside it would have said so -- a wire module is not a component. This is the
// rule rather than the list: a module under `src/wire/` that no other file
// under `src/` names is orphaned, whether or not anyone remembered to add it.
//
// Text, not the import graph, because a wire module is mostly types and a
// type-only import is erased before the graph can see it. A barrel is named by
// its directory (`@/wire/v1`), so an `index` file answers to that too.
function wireSpecifiers(file: string): string[] {
  const path = relative(SRC, file).replace(/\.tsx?$/, "");
  const spellings = [`@/${path}`];
  if (basename(path) === "index") spellings.push(`@/${dirname(path)}`);
  return spellings;
}

test("test_every_module_under_wire_is_named_by_something_under_src", () => {
  const files = typescriptSources(SRC);
  const orphans = files
    .filter((file) => relative(SRC, file).startsWith(`wire${sep}`))
    .filter((file) => {
      const own = basename(file).replace(/\.tsx?$/, "");
      return !files.some((other) => {
        if (other === file) return false;
        const source = readFileSync(other, "utf8");
        if (wireSpecifiers(file).some((s) => source.includes(`"${s}"`))) return true;
        return dirname(other) === dirname(file) && source.includes(`"./${own}"`);
      });
    })
    .map((file) => relative(SRC, file));
  expect(orphans).toEqual([]);
});

test("nothing under src/ imports the retired Book and Admin modules", () => {
  const importers = typescriptSources(SRC).flatMap((file) => {
    const source = readFileSync(file, "utf8");
    return RETIRED.filter((spellings) =>
      spellings.some((spelling) => source.includes(`"${spelling}"`)),
    ).map(([module]) => `${relative(SRC, file)} imports ${module}`);
  });
  expect(importers).toEqual([]);
});
