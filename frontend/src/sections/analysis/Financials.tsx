// CP-1: the normalised financials. Selecting a cell drives the formula bar
// and, when the cell carries a passport, opens it with the opener passed.
import { useState } from "react";
import { FormulaBar } from "./FormulaBar";
import { CitationChip } from "@/evidence/CitationChip";
import { useEvidence } from "@/evidence/EvidenceContext";
import type { Passport } from "@/wire";
import type { FinancialRow, Financials } from "@/wire/analysis";

interface Selection {
  key: string;
  col: number;
}

const cellId = (key: string, col: number) => `${key}:${col}`;

/** At rest the bar reads the headline total in the latest period. */
function initial(financials: Financials, passports: Record<string, Passport>): Selection | null {
  const last = financials.periods.length - 1;
  const row =
    financials.rows.find((entry) => entry.total && passports[cellId(entry.key, last)]) ??
    financials.rows.find((entry) => entry.total) ??
    financials.rows[0];
  return row && last >= 0 ? { key: row.key, col: last } : null;
}

export function FinancialsPanel({
  financials,
  passports,
}: {
  financials: Financials;
  passports: Record<string, Passport>;
}) {
  const [selection, setSelection] = useState<Selection | null>(() =>
    initial(financials, passports),
  );
  const { openPassport } = useEvidence();
  const row = selection
    ? (financials.rows.find((entry) => entry.key === selection.key) ?? null)
    : null;
  const passport = selection ? (passports[cellId(selection.key, selection.col)] ?? null) : null;

  const select = (entry: FinancialRow, col: number, opener: HTMLElement) => {
    setSelection({ key: entry.key, col });
    const next = passports[cellId(entry.key, col)];
    if (next) openPassport(next, opener);
  };

  return (
    <section className="pnl" data-financials-panel>
      <header>
        <h2>Normalised financials</h2>
        <span className="cp">CP-1</span>
        <span className="right">
          <span className="tag">$M UNLESS STATED</span>
          <span className="tag">{financials.rows.length} ROWS · ONE CITATION EACH</span>
        </span>
      </header>
      <div className="pb col">
        <FormulaBar
          row={row}
          col={selection?.col ?? null}
          periods={financials.periods}
          passport={passport}
        />
        <div className="tscroll">
          <table className="fin" data-financials>
            <thead>
              <tr>
                <th scope="col">Line item</th>
                {financials.periods.map((period) => (
                  <th key={period} scope="col">
                    {period}
                  </th>
                ))}
                <th scope="col" className="l">
                  Citation
                </th>
              </tr>
            </thead>
            <tbody>
              {financials.rows.map((entry) => (
                <tr
                  key={entry.key}
                  className={entry.total ? "tot" : undefined}
                  data-row={entry.key}
                >
                  <td className="wrap">{entry.line_item}</td>
                  {entry.values.map((value, col) => {
                    const on = selection?.key === entry.key && selection.col === col;
                    const id = cellId(entry.key, col);
                    return (
                      <td key={id} className={on ? "sel" : undefined}>
                        <button
                          type="button"
                          className="cellbtn"
                          aria-pressed={on}
                          data-cell={id}
                          data-passport-id={passports[id] ? id : undefined}
                          onClick={(event) => select(entry, col, event.currentTarget)}
                        >
                          {value}
                        </button>
                      </td>
                    );
                  })}
                  <td className="l">
                    <CitationChip citation={entry.citation} />{" "}
                    <span className="lbl" title="Confidence">
                      {entry.confidence}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {financials.rows.length === 0 ? (
          <div className="note">No financial row is served for this module.</div>
        ) : null}
      </div>
    </section>
  );
}
