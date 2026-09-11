// The definition conflict register — both readings, both citations, the size
// of the divergence, a restatement offered. Shown, never resolved
// (IA_SPEC.md 4.3) — and the adjusted-vs-reported comparison beside it.
import { SeverityMark } from "@/chrome/SeverityMark";
import { CitationChip } from "@/evidence/CitationChip";
import type { AdjustedRow, Conflict } from "@/wire/analysis";

export function Conflicts({ conflicts }: { conflicts: Conflict[] }) {
  // Colour is signal: an empty register has nothing to warn about.
  const open = conflicts.length > 0;
  return (
    <section className="pnl" data-conflicts>
      <header>
        {open ? <SeverityMark severity="WARNING" /> : null}
        <h2>Definition conflict register</h2>
        <span className="cp">CP-1B</span>
        <span className="right">
          <span className={`tag${open ? " warn" : ""}`}>
            {conflicts.length} PRESERVED · NONE RESOLVED
          </span>
        </span>
      </header>
      <ul className="pb flush plain">
        {conflicts.map((conflict) => (
          <li
            key={conflict.term}
            className="sec"
            data-conflict={conflict.term}
            data-resolved="false"
          >
            <h3>{conflict.term}</h3>
            <ol className="plain">
              {conflict.readings.map((reading, index) => (
                <li key={reading.source_label} className="reading" data-reading={index + 1}>
                  <span className="lbl">
                    Reading {index + 1} · {reading.source_label}
                  </span>
                  <div>
                    {reading.value} <CitationChip citation={reading.citation} />
                  </div>
                </li>
              ))}
            </ol>
            <div className="note">
              <b>Divergence {conflict.divergence}.</b> Restatement offered: {conflict.restatement}
            </div>
          </li>
        ))}
      </ul>
      {conflicts.length === 0 ? (
        <div className="pb note">No definition conflict is served for this module.</div>
      ) : null}
    </section>
  );
}

export function Adjusted({ rows }: { rows: AdjustedRow[] }) {
  const disputed = rows.filter((row) => row.disputed).length;
  return (
    <section className="pnl" data-adjusted>
      <header>
        <h2>Adjusted vs reported</h2>
        <span className="cp">CP-1D</span>
        <span className="right">
          <span className={`tag ${disputed ? "warn" : ""}`}>{disputed} DISPUTED</span>
        </span>
      </header>
      <div className="pb flush tscroll">
        <table className="fin">
          <thead>
            <tr>
              <th scope="col">Component</th>
              <th scope="col">Reported</th>
              <th scope="col">Adjustment</th>
              <th scope="col">Normalised</th>
              <th scope="col" className="l">
                Citation
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.component} data-adjusted-row data-disputed={row.disputed || undefined}>
                <td className="wrap">
                  {row.component}
                  <span className="lbl"> · {row.category}</span>
                  {row.disputed ? (
                    <>
                      {" "}
                      <span className="tag warn">
                        <SeverityMark severity="WARNING" /> DISPUTED
                      </span>
                    </>
                  ) : null}
                </td>
                <td>{row.reported}</td>
                <td>{row.adjustment}</td>
                <td>{row.normalised}</td>
                <td className="l">
                  <CitationChip citation={row.citation} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
