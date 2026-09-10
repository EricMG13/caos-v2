import type { Severity, Standing } from "./shared";

export interface CaseRow {
  case_id: string;
  issuer: string;
  sector: string;
  rating: string;
  pathway: string;
  snapshot: string;
  state: string;
  severity: Severity;
  net_leverage: string;
  updated_at: string;
  standing: Standing;
}

/** Anything the machine proposes is a suggestion until a person commits it. */
export interface IntakeSuggestion {
  key: string;
  value: string;
  why: string;
  committed: boolean;
}
export interface IntakeFile {
  name: string;
  bytes: number;
  sha256: string;
}
export interface Intake {
  /** The case the server created or resolved for the pack; null until it did. */
  case_id: string | null;
  files: IntakeFile[];
  suggestions: IntakeSuggestion[];
  run_id: string | null;
}
export interface DirectoryFilter {
  label: string;
  options: string[];
  active: string | null;
}
export interface DirectoryBody {
  search: string;
  filter: DirectoryFilter;
  cases: CaseRow[];
  intake: Intake | null;
}
