import type { Citation, Refusal } from "./shared";

export interface Figure {
  text: string;
  citation: Citation | null;
}
export interface Paragraph {
  id: string;
  kind: "MODULE" | "ANALYST_JUDGMENT";
  module_id: string | null;
  text: string;
  figures: Figure[];
}
export interface Revision {
  id: string;
  digest: string;
  saved_at: string;
  author: string;
}
export interface Opinion {
  signed_by: string;
  revision_id: string;
  digest: string;
  signed_at: string;
}
export interface LineageRow {
  module_id: string;
  artifact_sha256: string;
  state: string;
}
/** One section of the deliverable this revision feeds, in route order
    (IA_SPEC.md 4.8). The narrative row is the one the revision becomes. */
export interface DeliverableSection {
  n: number;
  title: string;
  module_id: string | null;
  kind: "MODULE" | "NARRATIVE" | "PROVENANCE";
}
export interface ReportBody {
  revision: Revision;
  revisions: Revision[];
  paragraphs: Paragraph[];
  /** The opinion on the current revision, or null while it is unsigned. */
  opinion: Opinion | null;
  /** The latest opinion on an earlier revision. It binds that revision only
      and never carries forward (IA_SPEC.md 4.7). */
  prior_opinion: Opinion | null;
  /** Freeze refused: the code, and the figure named in `clears`. */
  freeze: Refusal | null;
  lineage: LineageRow[];
  sections: DeliverableSection[];
}
