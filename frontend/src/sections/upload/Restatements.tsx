// A restatement across intakes is a conflict row: both readings, both
// citations, the divergence. It is surfaced, never merged (IA_SPEC.md 4.2).
import { useId } from "react";
import { CitationChip } from "@/evidence/CitationChip";
import type { Restatement } from "@/wire/upload";

export function Restatements({ restatements }: { restatements: Restatement[] }) {
  const headingId = useId();
  const open = restatements.length > 0;
  return (
    <section className="pnl" aria-labelledby={headingId} data-restatements>
      <header>
        <h2 id={headingId}>Restatements</h2>
        <span className="cp">ACROSS INTAKES</span>
        <span className="right">
          <span className={`tag${open ? " warn" : ""}`}>{open ? "NOT RESOLVED" : "NONE"}</span>
        </span>
      </header>
      <div className="pb flush">
        <table className="reg">
          <thead>
            <tr>
              <th scope="col">Restated figure</th>
              <th scope="col">Readings</th>
            </tr>
          </thead>
          <tbody>
            {restatements.map((restatement) => (
              <tr key={restatement.item} className="conflict" data-restatement={restatement.item}>
                <td className="wrap">
                  {restatement.item}
                  <span className="sub">{restatement.divergence}</span>
                </td>
                <td className="wrap">
                  <ul className="readings">
                    {restatement.readings.map((reading) => (
                      <li key={reading.citation.chip}>
                        <span className="sub">{reading.source_label}</span>
                        <b className="tabular">{reading.value}</b>
                        <CitationChip citation={reading.citation} />
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="absent">
        <b>Both readings stand.</b> The pack does not choose, and no conclusion is rewritten behind
        you. Pinning a set that admits only one of them is the choice — and it is a new run, because
        leverage, coverage and every covenant test downstream read a different number.
      </p>
    </section>
  );
}
