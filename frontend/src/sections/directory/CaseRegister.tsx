// The case register (IA_SPEC.md 4.1, card 5a): one action per row and it is
// the same action — open the case. No batch state, no checkboxes, no second
// selection model. A column nothing fills is not drawn.
import { Link } from "react-router";
import { SeverityMark } from "@/chrome/SeverityMark";
import type { CaseRow } from "@/wire/directory";

type ColumnKey = Exclude<keyof CaseRow, "severity" | "standing">;

interface Column {
  key: ColumnKey;
  label: string;
  mono?: boolean;
  right?: boolean;
  wrap?: boolean;
}

export const COLUMNS: readonly Column[] = [
  { key: "case_id", label: "Case", mono: true },
  { key: "issuer", label: "Issuer", wrap: true },
  { key: "sector", label: "Sector", wrap: true },
  { key: "rating", label: "Rating", mono: true, wrap: true },
  { key: "pathway", label: "Pathway", mono: true },
  { key: "snapshot", label: "Snapshot", mono: true },
  { key: "state", label: "State" },
  { key: "net_leverage", label: "Net leverage", mono: true, right: true, wrap: true },
  { key: "updated_at", label: "Updated", mono: true, right: true, wrap: true },
];

/** `2026-09-09T14:30:00Z` reads `2026-09-09 14:30Z`. */
export function stamp(iso: string): string {
  return iso.replace("T", " ").replace(/:\d\d(?:\.\d+)?Z$/, "Z");
}

/** The columns at least one row fills. An empty column is not rendered. */
export function filledColumns(rows: CaseRow[]): Column[] {
  return COLUMNS.filter((column) => rows.some((row) => row[column.key].trim() !== ""));
}

/** The one action a row has: open the case in Analysis. */
export function caseHref(caseId: string): string {
  return `/analysis/?case=${encodeURIComponent(caseId)}`;
}

function classOf(column: Column): string | undefined {
  const classes = [column.mono ? "m" : "", column.right ? "r" : "", column.wrap ? "wrap" : ""]
    .filter(Boolean)
    .join(" ");
  return classes || undefined;
}

function Cell({ row, column }: { row: CaseRow; column: Column }) {
  if (column.key === "state") {
    // Severity is shape and hue beside the word; never hue alone.
    return (
      <span className="state">
        <SeverityMark severity={row.severity} />
        {row.state}
      </span>
    );
  }
  if (column.key === "updated_at") {
    return <time dateTime={row.updated_at}>{stamp(row.updated_at)}</time>;
  }
  return <>{row[column.key]}</>;
}

export function CaseRegister({ rows }: { rows: CaseRow[] }) {
  const columns = filledColumns(rows);
  return (
    <table className="reg" data-register>
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={column.key}
              scope="col"
              className={[column.right ? "r" : "", column.wrap ? "wrap" : ""].join(" ").trim()}
            >
              {column.label}
            </th>
          ))}
          <th scope="col" className="r">
            <span className="sr-only">Action</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.case_id} data-case={row.case_id}>
            {columns.map((column) => (
              <td key={column.key} className={classOf(column)}>
                <Cell row={row} column={column} />
              </td>
            ))}
            <td className="r">
              <Link className="rowact" to={caseHref(row.case_id)}>
                Open case
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
