import type { ViewProps } from "@/app/views";

// Placeholder until the section lands in its own slice.
export function RunSection({ document }: ViewProps<"run">) {
  return <p className="note">{document.observed_at}</p>;
}
