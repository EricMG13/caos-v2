// The capital structure, each tranche with its seniority as hue and word and
// its leverage-through; and the armed triggers with their cushions.
import { SeverityMark, toneOf } from "@/chrome/SeverityMark";
import { CitationChip } from "@/evidence/CitationChip";
import type { Seniority, Tranche, Trigger } from "@/wire/analysis";

const SENIORITY_WORD: Record<Seniority, string> = {
  FIRST_LIEN: "1L",
  SECOND_LIEN: "2L",
  SENIOR_UNSEC: "SR UNSEC",
  SUBORDINATED: "SUB",
  EQUITY: "EQUITY",
};

export function Capital({ tranches, triggers }: { tranches: Tranche[]; triggers: Trigger[] }) {
  return (
    <>
      <section className="pnl" data-capital>
        <header>
          <h2>Capital structure</h2>
          <span className="cp">CP-1A / CP-4</span>
          <span className="right">
            <span className="tag">{tranches.length} TRANCHES</span>
          </span>
        </header>
        <ul className="pb flush plain">
          {tranches.map((tranche) => (
            <li
              key={tranche.instrument}
              className="srow"
              data-tranche
              data-seniority={tranche.seniority}
            >
              <span className={`sw ${tranche.seniority.toLowerCase()}`} aria-hidden="true" />
              <div style={{ minWidth: 0 }}>
                <div className="nm" title={tranche.instrument}>
                  {tranche.instrument}
                </div>
                <div className="mt">
                  {SENIORITY_WORD[tranche.seniority]} · {tranche.coupon} · {tranche.maturity} ·{" "}
                  <CitationChip citation={tranche.citation} />
                </div>
              </div>
              <div className="amt">
                <div className="nm tabular">{tranche.amount}</div>
                <div className="mt tabular">THRU {tranche.leverage_through}</div>
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="pnl" data-triggers>
        <header>
          <h2>Triggers armed</h2>
          <span className="cp">CP-MON</span>
          <span className="right">
            <span className="tag">{triggers.length} ARMED</span>
          </span>
        </header>
        <ul className="pb plain">
          {triggers.map((trigger) => (
            <li key={trigger.id} className="trig" data-trigger={trigger.id}>
              <SeverityMark severity={trigger.severity} />
              <span>
                <b>{trigger.id}</b> · {trigger.description}
                <br />
                <span className="lbl">
                  Threshold {trigger.threshold} · now {trigger.current}
                </span>{" "}
                <CitationChip citation={trigger.citation} />
              </span>
              <span className="sp">
                <span className={`tag ${toneOf(trigger.severity)}`}>{trigger.cushion}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
