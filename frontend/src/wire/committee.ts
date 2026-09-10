import type { Citation, Refusal } from "./shared";

export interface ArtifactRow {
  module_id: string;
  name: string;
  disposition: "ACCEPTED" | "RESTRICTED" | "SCREENING_ONLY";
  artifact_sha256: string;
}
export interface PaperFigure {
  text: string;
  citation: Citation;
}
export interface PaperParagraph {
  text: string;
  figures: PaperFigure[];
}
export interface PaperTable {
  columns: string[];
  rows: string[][];
}
export interface PaperSection {
  n: number;
  title: string;
  module_id: string | null;
  paragraphs: PaperParagraph[];
  table: PaperTable | null;
}
export interface LadderStep {
  key: "opinion" | "freeze" | "filing" | "receipt";
  state: "done" | "cur" | "ref" | "todo";
  title: string;
  detail: string;
  actor: string | null;
  at: string | null;
  refusal: Refusal | null;
}
export interface Receipt {
  filing_id: string;
  deliverable_sha256: string;
  filed_by: string;
  filed_at: string;
  independence: string;
}
export interface ProvenanceRow {
  module_id: string;
  build_id: string;
  artifact_sha256: string;
  accepted_at: string;
}
export interface Deliverable {
  title: string;
  issuer: string;
  snapshot: string;
  revision_id: string;
  filed: boolean;
  watermark: string | null;
  output: string;
}
export interface CommitteeBody {
  deliverable: Deliverable;
  artifacts: ArtifactRow[];
  narrative: { title: string; paragraphs: string[] };
  provenance: ProvenanceRow[];
  paper: PaperSection[];
  ladder: LadderStep[];
  receipt: Receipt | null;
  /** File is present and refused while the freeze has no current opinion or
      the actor signed or froze it (APPROVER_NOT_INDEPENDENT). */
  file: Refusal | null;
}
