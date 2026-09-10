import type { Citation } from "./shared";

export type Grade = "A" | "B" | "C";
export type Disposition = "ADMITTED" | "EXCLUDED_LOW_VALUE" | "PENDING" | "WITHDRAWN";

export interface SourceRow {
  source_id: string;
  label: string;
  file_name: string;
  family: string;
  grade: Grade;
  disposition: Disposition;
  pages: number;
  sha256: string;
  set_versions: string[];
  withdrawn_at: string | null;
  /** Withdrawal is checked live at every use (invariant 1). */
  withdrawal_checked_at: string;
}
export interface SetVersion {
  version: string;
  sources: number;
  pinned_at: string;
  pinned: boolean;
}
/** Restatement across intakes is surfaced as a conflict, never merged. */
export interface Restatement {
  item: string;
  readings: { source_label: string; value: string; citation: Citation }[];
  divergence: string;
}
export interface UploadBody {
  pinned_set: string;
  set_versions: SetVersion[];
  sources: SourceRow[];
  restatements: Restatement[];
}
