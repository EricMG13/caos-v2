import type { AdminBody } from "./admin";
import type { BookBody } from "./book";
import type { SectionDocument } from "./shared";

// Every enabled section -- Directory, Upload, Run, Analysis, Model, Report and
// Committee -- reads the v1 wire only (brief 4.1, decision 9; slices 4.1h-k
// and Phase 4), and their legacy body types are retired. `Bodies` types only
// Book and Admin, the two sections unavailable in every mode, which still
// compile against their legacy fixtures.
export interface Bodies {
  book: BookBody;
  admin: AdminBody;
}
export type DocumentOf<S extends keyof Bodies> = SectionDocument<Bodies[S]>;
export type AnyDocument = SectionDocument<Bodies[keyof Bodies]>;

export * from "./shared";
