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
import type { Section } from "@/wire";
import type {
  AnalysisDocument,
  CommitteeDocument,
  DirectoryDocument,
  ModelDocument,
  ReportDocument,
  RunSectionDocument,
  UploadDocument,
} from "@/wire/v1";

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

/** Book and Admin are unavailable in every mode and are never mounted with a
    document, so `never` is what their shells are typed on (decision D2). */
export type DocumentFor<S extends Section> = S extends keyof V1Documents ? V1Documents[S] : never;

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
