// Section → view. Each view receives the section's whole document and the
// active tab id; it composes the body and nothing above it.
import type { ComponentType } from "react";
import { AdminSection } from "@/sections/admin/AdminSection";
import { AnalysisSection } from "@/sections/analysis/AnalysisSection";
import { BookSection } from "@/sections/book/BookSection";
import { CommitteeSection } from "@/sections/committee/CommitteeSection";
import { DirectorySection } from "@/sections/directory/DirectorySection";
import { ModelSection } from "@/sections/model/ModelSection";
import { ReportSection } from "@/sections/report/ReportSection";
import { RunSection } from "@/sections/run/RunSection";
import { UploadSection } from "@/sections/upload/UploadSection";
import type { Bodies, Section, SectionDocument } from "@/wire";
import type {
  AnalysisDocument,
  CommitteeDocument,
  DirectoryDocument,
  ModelDocument,
  ReportDocument,
  RunSectionDocument,
  UploadDocument,
} from "@/wire/v1";

/** The two sections still on the legacy wire type -- Book and Admin, which
    are unavailable in every mode and never mounted with a served document. */
export interface ViewProps<S extends keyof Bodies> {
  document: SectionDocument<Bodies[S]>;
  tab: string | null;
}

/** Each enabled section's v1 document, by section. */
interface V1Documents {
  directory: DirectoryDocument;
  upload: UploadDocument;
  run: RunSectionDocument;
  analysis: AnalysisDocument;
  model: ModelDocument;
  report: ReportDocument;
  committee: CommitteeDocument;
}

export type DocumentFor<S extends Section> = S extends keyof V1Documents
  ? V1Documents[S]
  : S extends keyof Bodies
    ? SectionDocument<Bodies[S]>
    : never;

/** Each view typed on exactly its own document, so a section wired to the
    wrong parser is a compile error here rather than a render error later.
    The workspace erases the key at its one lookup site. */
export const SECTION_VIEWS: {
  [S in Section]: ComponentType<{ document: DocumentFor<S>; tab: string | null }>;
} = {
  directory: DirectorySection,
  upload: UploadSection,
  analysis: AnalysisSection,
  book: BookSection,
  run: RunSection,
  model: ModelSection,
  report: ReportSection,
  committee: CommitteeSection,
  admin: AdminSection,
};
