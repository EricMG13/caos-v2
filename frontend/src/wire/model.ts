import type { Citation, Passport } from "./shared";

export type LineGroup = "operating" | "investing" | "financing" | "debt" | "cash" | "metrics";

export interface ProjectionLine {
  key: string;
  label: string;
  group: LineGroup;
  /** One value per period; null when the period is unavailable. */
  values: (string | null)[];
  passport_ids: (string | null)[];
}
export interface ProjectionPeriod {
  period_id: string;
  fiscal_year: string;
  residual: string | null;
  state: "available" | "unavailable";
  unavailable_reason: string | null;
  /** True when unavailable by propagation from an earlier period. */
  propagated: boolean;
}
export interface ProjectionCase {
  case: string;
  periods: ProjectionPeriod[];
  lines: ProjectionLine[];
}
export interface DriverRow {
  driver: string;
  value: string;
  rationale: string;
  state: string;
  citation: Citation;
}
export interface Breach {
  case: string;
  period_id: string;
  covenant: string;
}
export interface ModelBody {
  module_id: "CP-CF";
  accepted_at: string;
  artifact_sha256: string;
  tolerance: string;
  cases: ProjectionCase[];
  drivers: DriverRow[];
  first_breach: Breach[];
  passports: Record<string, Passport>;
}
