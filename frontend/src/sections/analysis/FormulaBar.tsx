// The formula bar: the selected cell's coordinate, its derivation in the
// expression language (evaluated server-side), and the lineage of every
// operand as chips (IA_SPEC.md 4.3).
import { CitationChip } from "@/evidence/CitationChip";
import type { Passport } from "@/wire";
import type { FinancialRow } from "@/wire/analysis";

export function FormulaBar({
  row,
  col,
  periods,
  passport,
}: {
  row: FinancialRow | null;
  col: number | null;
  periods: string[];
  passport: Passport | null;
}) {
  if (!row || col === null) {
    return (
      <div className="formulabar" data-formula-bar>
        <span className="coord">—</span>
        <code>Select a cell to read its derivation.</code>
      </div>
    );
  }
  const period = periods[col] ?? "";
  const expression = passport?.derivation ?? row.formula;
  const lineage = passport?.citations ?? [row.citation];
  return (
    <div className="formulabar" data-formula-bar data-cell={`${row.key}:${col}`}>
      <span className="coord">
        {row.key.toUpperCase()} · {period.toUpperCase()}
      </span>
      <code title={expression}>= {expression}</code>
      <span className="lineage">
        {lineage.map((citation) => (
          <CitationChip key={citation.chip} citation={citation} />
        ))}
        <span className="tag">
          {passport ? passport.method : `${row.confidence.toUpperCase()} · ${row.variance}`}
        </span>
      </span>
    </div>
  );
}
