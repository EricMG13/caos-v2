import type { ViewProps } from "@/app/views";

// Placeholder until the section lands in its own slice.
export function CommitteeSection({ document }: ViewProps<"committee">) {
  return <p className="note">{document.observed_at}</p>;
}
