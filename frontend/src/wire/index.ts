import type { AdminBody } from "./admin";
import type { AnalysisBody } from "./analysis";
import type { BookBody } from "./book";
import type { CommitteeBody } from "./committee";
import type { DirectoryBody } from "./directory";
import type { ModelBody } from "./model";
import type { ReportBody } from "./report";
import type { RunBody } from "./run";
import type { SectionDocument } from "./shared";
import type { UploadBody } from "./upload";

export interface Bodies {
  directory: DirectoryBody;
  upload: UploadBody;
  analysis: AnalysisBody;
  book: BookBody;
  run: RunBody;
  model: ModelBody;
  report: ReportBody;
  committee: CommitteeBody;
  admin: AdminBody;
}
export type DocumentOf<S extends keyof Bodies> = SectionDocument<Bodies[S]>;
export type AnyDocument = SectionDocument<Bodies[keyof Bodies]>;

export * from "./shared";
