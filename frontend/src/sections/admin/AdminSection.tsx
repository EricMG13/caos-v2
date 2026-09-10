// Admin (IA_SPEC.md 4.9): an explicit unavailable capability. One panel, the
// unavailable state, and the list of what is missing. Nothing here is a control.
import { useId } from "react";
import { UnavailableCapability } from "./UnavailableCapability";
import type { ViewProps } from "@/app/views";

export function AdminSection({ document }: ViewProps<"admin">) {
  const headingId = useId();
  return (
    <section className="pnl" aria-labelledby={headingId} data-admin>
      <header>
        <h2 id={headingId}>Admin</h2>
        <span className="cp">/admin/</span>
        <span className="right">
          <span className="tag warn">UNAVAILABLE</span>
        </span>
      </header>
      <div className="pb">
        <UnavailableCapability body={document.body} observedAt={document.observed_at} />
      </div>
    </section>
  );
}
