// CP-5: the ranked evidence trace. Every row carries its confidence as a
// number and a tier, and its anchor as a chip that opens the one drawer.
import { confidenceTier } from "./tone";
import { CitationChip } from "@/evidence/CitationChip";
import type { TraceRow } from "@/wire/analysis";

export function EvidenceTrace({ rows }: { rows: TraceRow[] }) {
  return (
    <section className="pnl" data-trace>
      <header>
        <h2>Evidence trace</h2>
        <span className="cp">CP-5</span>
        <span className="right">
          <span className="tag">{rows.length} RANKED</span>
        </span>
      </header>
      <ol className="pb flush plain">
        {rows.map((row) => {
          const tier = confidenceTier(row.confidence);
          return (
            <li key={row.rank} className="ev" data-trace-row={row.rank}>
              <span className="h">
                #{row.rank} {row.heading}
              </span>
              <span className={`tag ${tier.tone}`} title="Confidence">
                {row.confidence}% · {tier.word}
              </span>
              <span className="m">
                {row.module_id} · <CitationChip citation={row.citation} />
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
