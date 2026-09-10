// The book: one row per credit, grouped by the active key. Every metric cell
// opens the passport; a deviating cell is marked; a stale row is colour and
// date (IA_SPEC.md 4.4).
import { MetricCell } from "./MetricCell";
import { SeverityMark, toneOf } from "@/chrome/SeverityMark";
import type { Passport, Severity } from "@/wire";
import type { BookRow, Column } from "@/wire/book";

const STATUS_SEVERITY: Record<string, Severity> = {
  COMPLETE: "SUCCESS",
  RUNNABLE: "RUNNING",
  RUNNING: "RUNNING",
  RESTRICTED: "WARNING",
  BLOCKED: "CRITICAL",
};

function groupsOf(rows: BookRow[], groupKey: string, activeKey: string): [string, BookRow[]][] {
  const groups = new Map<string, BookRow[]>();
  for (const row of rows) {
    const name = groupKey === activeKey ? row.group : (row.attributes[groupKey] ?? "Not served");
    groups.set(name, [...(groups.get(name) ?? []), row]);
  }
  return [...groups.entries()];
}

function CaseRow({
  row,
  columns,
  passports,
  compared,
  selected,
  onSelect,
}: {
  row: BookRow;
  columns: Column[];
  passports: Record<string, Passport>;
  compared: boolean;
  selected: string | null;
  onSelect: (passportId: string, opener: HTMLElement) => void;
}) {
  const deviations = Object.values(row.cells).filter((cell) => cell.deviation).length;
  const stale = row.freshness.state === "stale";
  const status = row.attributes["status"] ?? "NOT SERVED";
  const severity = STATUS_SEVERITY[status] ?? "IDLE";
  return (
    <tr
      className={compared ? "cmp" : undefined}
      data-case={row.case_id}
      data-deviates={deviations > 0 || undefined}
      data-stale={stale || undefined}
    >
      <td className="l wrap">
        {row.issuer}
        {deviations ? (
          <span
            className="defmark"
            role="img"
            aria-label={`deviates from the house definition on ${deviations} cells`}
            title={`Deviates from the house definition on ${deviations} cells`}
          />
        ) : null}
        <div className="lbl">{row.case_id}</div>
      </td>
      <td className="l">
        <span className={`tag ${toneOf(severity)}`}>
          <SeverityMark severity={severity} /> {status}
        </span>
      </td>
      {columns.map((column) => {
        const cell = row.cells[column.key];
        if (!cell) {
          return (
            <td key={column.key} className="l">
              <span className="tag">NOT SERVED</span>
            </td>
          );
        }
        const classes = [cell.stale ? "stale" : "", selected === cell.passport_id ? "cellsel" : ""]
          .filter(Boolean)
          .join(" ");
        return (
          <td key={column.key} className={classes || undefined}>
            <MetricCell
              cell={cell}
              passport={passports[cell.passport_id] ?? null}
              selected={selected === cell.passport_id}
              onSelect={onSelect}
            />
          </td>
        );
      })}
      <td className="l">
        <code>{row.snapshot}</code>
      </td>
      <td className={stale ? "l stale" : "l"} data-freshness={row.freshness.state}>
        <time dateTime={row.freshness.date}>{row.freshness.date}</time>
        {stale ? (
          <>
            {" "}
            <span className="tag warn">
              <SeverityMark severity="WARNING" /> STALE
            </span>
          </>
        ) : null}
      </td>
    </tr>
  );
}

export function CasesTable({
  rows,
  total,
  columns,
  groupKey,
  activeKey,
  passports,
  compared,
  selected,
  onSelect,
}: {
  rows: BookRow[];
  total: number;
  columns: Column[];
  groupKey: string;
  activeKey: string;
  passports: Record<string, Passport>;
  compared: ReadonlySet<string>;
  selected: string | null;
  onSelect: (passportId: string, opener: HTMLElement) => void;
}) {
  const span = columns.length + 4;
  return (
    <section className="pnl" data-book-panel>
      <header>
        <h2>Book</h2>
        <span className="cp">GROUPED BY {groupKey.toUpperCase().replace(/_/g, " ")}</span>
        <span className="right">
          <span className="tag acc">{compared.size} COMPARED</span>
          <span className="tag">
            {rows.length} OF {total} CREDITS
          </span>
        </span>
      </header>
      <div className="pb flush tscroll">
        <table className="cases" data-book data-grouped-by={groupKey}>
          <thead>
            <tr>
              <th scope="col" className="l">
                Credit
              </th>
              <th scope="col" className="l">
                Status
              </th>
              {columns.map((column) => (
                <th key={column.key} scope="col">
                  {column.label}
                </th>
              ))}
              <th scope="col" className="l">
                Snapshot
              </th>
              <th scope="col" className="l">
                Evidence date
              </th>
            </tr>
          </thead>
          {groupsOf(rows, groupKey, activeKey).map(([name, members]) => (
            <tbody key={name}>
              <tr className="grp" data-group={name}>
                <td colSpan={span}>
                  {name} · {members.length} {members.length === 1 ? "credit" : "credits"}
                </td>
              </tr>
              {members.map((row) => (
                <CaseRow
                  key={row.case_id}
                  row={row}
                  columns={columns}
                  passports={passports}
                  compared={compared.has(row.case_id)}
                  selected={selected}
                  onSelect={onSelect}
                />
              ))}
            </tbody>
          ))}
        </table>
      </div>
      {rows.length === 0 ? (
        <div className="pb note">
          No credit matches the facets. Nothing is inferred from silence.
        </div>
      ) : null}
    </section>
  );
}
