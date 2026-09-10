// The right column, about the case: CP-5 clearance with the blocking finding
// named, and the route frontier — module id, state, reason. Acceptance lives
// in Run; this column reads.
import { NODE_SEVERITY, nodeTone } from "./tone";
import { SeverityMark, toneOf } from "@/chrome/SeverityMark";
import { CitationChip } from "@/evidence/CitationChip";
import type { Severity } from "@/wire";
import type { Clearance as ClearanceBody, FrontierItem } from "@/wire/analysis";

const CLEARANCE_SEVERITY: Record<ClearanceBody["state"], Severity> = {
  CLEAR: "SUCCESS",
  CONDITIONAL: "WARNING",
  BLOCKED: "CRITICAL",
};

export function Clearance({ clearance }: { clearance: ClearanceBody }) {
  const severity = CLEARANCE_SEVERITY[clearance.state];
  const blocking = clearance.findings.find((finding) => finding.id === clearance.blocking) ?? null;
  const others = clearance.findings.filter((finding) => finding !== blocking);
  return (
    <section
      className={`pnl ${toneOf(severity)}`}
      data-clearance
      data-clearance-state={clearance.state}
    >
      <header>
        <SeverityMark severity={severity} />
        <h2>Clearance: {clearance.state.toLowerCase()}</h2>
        <span className="cp">CP-5</span>
      </header>
      <div className="pb col">
        {clearance.blocking ? (
          <div
            className="note"
            data-blocking={clearance.blocking}
            data-finding={blocking?.id ?? undefined}
          >
            {blocking ? <SeverityMark severity={blocking.severity} /> : null}{" "}
            <b>{clearance.blocking} blocks.</b>{" "}
            {blocking?.text ?? "The blocking finding is not served."}{" "}
            {blocking?.citation ? <CitationChip citation={blocking.citation} /> : null}
          </div>
        ) : (
          <div className="note">
            <b>Nothing blocks.</b> Every finding is cleared.
          </div>
        )}
        <ul className="plain">
          {others.map((finding) => (
            <li key={finding.id} className="trig" data-finding={finding.id}>
              <SeverityMark severity={finding.severity} />
              <span>
                <b>{finding.id}</b> · {finding.text}{" "}
                {finding.citation ? <CitationChip citation={finding.citation} /> : null}
              </span>
            </li>
          ))}
        </ul>
        <div className="note">
          <b>CP-5 → CP-6 is the route&apos;s one QA_GATE.</b> A conditional clearance lets CP-6 run;
          publication stays blocked until the finding is repaired or withdrawn.
        </div>
      </div>
    </section>
  );
}

export function Frontier({ items, runState }: { items: FrontierItem[]; runState: string | null }) {
  return (
    <section className="pnl" data-frontier>
      <header>
        <h2>Route frontier</h2>
        <span className="cp">{runState?.split(" · ")[0] ?? "PINNED"}</span>
        <span className="right">
          <span className="tag">ACCEPT LIVES IN RUN</span>
        </span>
      </header>
      <ul className="pb flush plain">
        {items.map((item) => (
          <li
            key={item.module_id}
            className="frontier"
            data-frontier-item={item.module_id}
            data-state={item.state}
          >
            <span className="id">{item.module_id}</span>
            <span>{item.name}</span>
            <span className={`tag ${nodeTone(item.state)}`}>
              <SeverityMark severity={NODE_SEVERITY[item.state]} /> {item.state}
            </span>
            <span className="why">{item.reason}</span>
          </li>
        ))}
      </ul>
      {items.length === 0 ? <div className="pb note">The frontier is empty.</div> : null}
    </section>
  );
}
