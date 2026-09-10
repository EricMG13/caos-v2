import type { Passport } from "./shared";

export interface FacetOption {
  value: string;
  count: number;
  on: boolean;
}
export interface Facet {
  key: string;
  label: string;
  options: FacetOption[];
}
export interface BookCell {
  value: string;
  passport_id: string;
  /** Definition deviation is marked on every affected cell, with its size. */
  deviation: string | null;
  stale: boolean;
}
export interface Freshness {
  state: "current" | "stale";
  date: string;
}
export interface BookRow {
  case_id: string;
  issuer: string;
  group: string;
  snapshot: string;
  freshness: Freshness;
  /** The row's value under every facet and grouping key, so the book filters
   *  and regroups on what was served; `group` is its value under the active key. */
  attributes: Record<string, string>;
  cells: Record<string, BookCell>;
}
export interface CompareBasis {
  period: string;
  scenario: string;
  accepted_only: boolean;
}
export interface CompareCase {
  case_id: string;
  issuer: string;
  /** The accepted snapshot this comparison binds for the case. */
  snapshot: string;
  cells: Record<string, BookCell>;
}
export interface Compare {
  basis: CompareBasis;
  metrics: string[];
  cases: CompareCase[];
}
export interface Column {
  key: string;
  label: string;
}
export interface SavedView {
  name: string;
  scope: "THIS BROWSER" | "ANALYST PROFILE" | "WORKSPACE";
}
export interface BookBody {
  facets: Facet[];
  grouping: { keys: string[]; active: string };
  columns: Column[];
  rows: BookRow[];
  compare: Compare;
  saved_views: SavedView[];
  passports: Record<string, Passport>;
}
