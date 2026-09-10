import type { ViewProps } from "@/app/views";

// Placeholder until the section lands in its own slice.
export function ReportSection({ document }: ViewProps<"report">) {
  return <p className="note">{document.observed_at}</p>;
}
