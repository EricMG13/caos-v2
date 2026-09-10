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
import type { AnyDocument, Bodies, Section, SectionDocument } from "@/wire";

export interface ViewProps<S extends Section> {
  document: SectionDocument<Bodies[S]>;
  tab: string | null;
}

type AnyView = ComponentType<{ document: AnyDocument; tab: string | null }>;

// Each view is typed on its own body; the registry erases that so the
// workspace can mount any of the nine without a switch.
export const SECTION_VIEWS: Record<Section, AnyView> = {
  directory: DirectorySection as unknown as AnyView,
  upload: UploadSection as unknown as AnyView,
  analysis: AnalysisSection as unknown as AnyView,
  book: BookSection as unknown as AnyView,
  run: RunSection as unknown as AnyView,
  model: ModelSection as unknown as AnyView,
  report: ReportSection as unknown as AnyView,
  committee: CommitteeSection as unknown as AnyView,
  admin: AdminSection as unknown as AnyView,
};
