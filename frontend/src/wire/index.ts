import type { AdminBody } from "./admin";
import type { BookBody } from "./book";
import type { CommitteeBody } from "./committee";
import type { ModelBody } from "./model";
import type { ReportBody } from "./report";
import type { SectionDocument } from "./shared";

// Directory, Upload, Run and Analysis are enabled sections and read the v1
// wire only (brief 4.1, decision 9; slices 4.1h-j) -- their legacy body types
// and the dual-path marker they used are retired. `Bodies` now types only the
// five sections that are unavailable in every mode and still compile against
// their legacy fixtures.
export interface Bodies {
  book: BookBody;
  model: ModelBody;
  report: ReportBody;
  committee: CommitteeBody;
  admin: AdminBody;
}
export type DocumentOf<S extends keyof Bodies> = SectionDocument<Bodies[S]>;
export type AnyDocument = SectionDocument<Bodies[keyof Bodies]>;

export * from "./shared";
