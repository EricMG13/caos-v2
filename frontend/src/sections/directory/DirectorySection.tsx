import type { ViewProps } from "@/app/views";

// Placeholder until the section lands in its own slice.
export function DirectorySection({ document }: ViewProps<"directory">) {
  return <p className="note">{document.observed_at}</p>;
}
