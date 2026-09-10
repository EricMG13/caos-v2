import type { Citation, NodeState, Passport, Severity } from "./shared";
import type { Disposition, Grade } from "./upload";

export interface RegisterRow {
  source_id: string;
  label: string;
  title: string;
  grade: Grade;
  disposition: Disposition;
  pages: number;
}
export interface TraceRow {
  rank: number;
  heading: string;
  module_id: string;
  confidence: number;
  citation: Citation;
}
export interface FinancialRow {
  key: string;
  line_item: string;
  category: string;
  values: string[];
  formula: string;
  variance: string;
  citation: Citation;
  confidence: "High" | "Medium" | "Low";
  total: boolean;
}
export interface Financials {
  periods: string[];
  rows: FinancialRow[];
}
/** Both readings, both citations, the size of the divergence. Never resolved. */
export interface Conflict {
  term: string;
  readings: { source_label: string; value: string; citation: Citation }[];
  divergence: string;
  restatement: string;
}
export interface AdjustedRow {
  component: string;
  reported: string;
  adjustment: string;
  normalised: string;
  category: string;
  citation: Citation;
  disputed: boolean;
}
export interface StepOutput {
  n: string;
  name: string;
  state: "COMPLETE" | "RESTRICTED" | "BLOCKED";
  limitation: string | null;
}
export interface DebateTurn {
  role: "BULL" | "BEAR" | "CHAIR";
  text: string;
  citation: Citation | null;
}
export interface Weighting {
  factor: string;
  bull: string;
  bear: string;
  chair: string;
}
export interface Debate {
  turns: DebateTurn[];
  weighting: Weighting[];
  memo: string;
}
export interface Finding {
  id: string;
  text: string;
  severity: Severity;
  citation: Citation | null;
}
export interface Clearance {
  state: "CLEAR" | "CONDITIONAL" | "BLOCKED";
  blocking: string | null;
  findings: Finding[];
}
export interface FrontierItem {
  module_id: string;
  name: string;
  state: NodeState;
  reason: string;
}
export type Seniority = "FIRST_LIEN" | "SECOND_LIEN" | "SENIOR_UNSEC" | "SUBORDINATED" | "EQUITY";
export interface Tranche {
  instrument: string;
  seniority: Seniority;
  amount: string;
  coupon: string;
  maturity: string;
  leverage_through: string;
  citation: Citation;
}
export interface Trigger {
  id: string;
  description: string;
  threshold: string;
  current: string;
  cushion: string;
  severity: Severity;
  citation: Citation;
}
export interface ModuleTab {
  module_id: string;
  name: string;
  state: NodeState;
  limitation: string | null;
}
export interface AnalysisBody {
  modules: ModuleTab[];
  register: RegisterRow[];
  trace: TraceRow[];
  financials: Financials;
  conflicts: Conflict[];
  adjusted: AdjustedRow[];
  steps: StepOutput[];
  debate: Debate;
  clearance: Clearance;
  frontier: FrontierItem[];
  capital: Tranche[];
  triggers: Trigger[];
  passports: Record<string, Passport>;
}
