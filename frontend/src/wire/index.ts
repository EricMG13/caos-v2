import type { AdminBody } from "./admin";
import type { BookBody } from "./book";
import type { CommitteeBody } from "./committee";
import type { ReportBody } from "./report";
import type { SectionDocument } from "./shared";

// Directory, Upload, Run, Analysis and Model are enabled sections and read the
// v1 wire only (brief 4.1, decision 9; slices 4.1h-k) -- their legacy body types
// and the dual-path marker they used are retired. `Bodies` now types only the
// four sections that are unavailable in every mode and still compile against
// their legacy fixtures.
export interface Bodies {
  book: BookBody;
  report: ReportBody;
  committee: CommitteeBody;
  admin: AdminBody;
}
export type DocumentOf<S extends keyof Bodies> = SectionDocument<Bodies[S]>;
export type AnyDocument = SectionDocument<Bodies[keyof Bodies]>;

export * from "./shared";
