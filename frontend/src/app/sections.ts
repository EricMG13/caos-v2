// The nine sections and the forwarding table (IA_SPEC.md 1). A pre-v2 slug
// forwards to its new home with the query string intact, replacing history so
// the entry stays router-owned.
import routes from "./routes.json";
import { SECTIONS, type Section } from "@/wire/shared";

export const SECTION_LABELS: Record<Section, string> = {
  directory: "Directory",
  upload: "Upload",
  analysis: "Analysis",
  book: "Book",
  run: "Run",
  model: "Model",
  report: "Report",
  committee: "Committee",
  admin: "Admin",
};

/** The one word per section a strip rail shows at 1024 px. */
export const SECTION_ABBREVIATIONS: Record<Section, string> = {
  directory: "Di",
  upload: "Up",
  analysis: "An",
  book: "Bk",
  run: "Rn",
  model: "Md",
  report: "Rp",
  committee: "Cm",
  admin: "Ad",
};

export function sectionPath(section: Section): string {
  return `/${section}/`;
}

export function sectionFromPath(pathname: string): Section | null {
  const match = /^\/([a-z-]+)\/$/.exec(pathname);
  const slug = match?.[1];
  return slug && (SECTIONS as readonly string[]).includes(slug) ? (slug as Section) : null;
}

const FORWARDS: Record<string, string> = routes.forwards;
const RENAMES: Record<string, Record<string, string>> = routes.query_renames;

export interface Forward {
  to: string;
  replace: true;
}

/** The query with a slug's renames applied; untouched when there are none. */
function renamed(search: string, renames: Record<string, string> | undefined): string {
  if (!renames) return search;
  const params = new URLSearchParams(search);
  for (const [from, to] of Object.entries(renames)) {
    const value = params.get(from);
    if (value !== null) {
      params.delete(from);
      params.set(to, value);
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** Where a pathname forwards, with its query carried over, or null. */
export function forward(pathname: string, search: string): Forward | null {
  if (sectionFromPath(pathname)) return null;
  const bare = pathname.replace(/\/+$/, "") || "/";
  // Root → Directory; a listed slug → its home; a section without its
  // trailing slash → the same section. Anything else is absent.
  const target =
    bare === "/" ? "/directory/" : (FORWARDS[bare] ?? (sectionFromPath(`${bare}/`) && `${bare}/`));
  if (!target) return null;
  return { to: `${target}${renamed(search, RENAMES[bare])}`, replace: true };
}
