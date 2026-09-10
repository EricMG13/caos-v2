import type { ViewProps } from "@/app/views";

// Placeholder until the section lands in its own slice.
export function BookSection({ document }: ViewProps<"book">) {
  return <p className="note">{document.observed_at}</p>;
}
