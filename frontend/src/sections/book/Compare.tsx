// Two to four credits side by side on one stated basis — period, scenario,
// accepted-only — each binding the one accepted snapshot it names. Definition
// deviation is marked in the comparison, with the size and a restatement.
import type { ReactNode } from "react";
import { MetricCell } from "./MetricCell";
import { SeverityMark } from "@/chrome/SeverityMark";
import { RefusalNote } from "@/controls/RefusedControl";
import type { Passport, Refusal } from "@/wire";
import type { Column, Compare as CompareBody, CompareCase } from "@/wire/book";

function basisOf(compare: CompareBody): string {
  const { period, scenario, accepted_only } = compare.basis;
  return `${period} · ${scenario} · ${accepted_only ? "accepted only" : "all snapshots"}`;
}

function evidenceDateOf(
  entry: CompareCase,
  metrics: string[],
  passports: Record<string, Passport>,
): string | null {
  const first = metrics.map((metric) => entry.cells[metric]).find((cell) => cell !== undefined);
  return first ? (passports[first.passport_id]?.evidence_date ?? null) : null;
}

export function Compare({
  compare,
  columns,
  passports,
  selected,
  onSelect,
  refusedLens,
  onSwitchLens,
}: {
  compare: CompareBody;
  columns: Column[];
  passports: Record<string, Passport>;
  selected: string | null;
  onSelect: (passportId: string, opener: HTMLElement) => void;
  /** A compared case whose served snapshot differs from the one it is bound to. */
  refusedLens: Record<string, Refusal>;
  onSwitchLens: (caseId: string) => void;
}) {
  const labels = new Map(columns.map((column) => [column.key, column.label]));
  const labelOf = (metric: string) => labels.get(metric) ?? metric;
  const basis = basisOf(compare);
  const cases = compare.cases;
  const deviating = cases.flatMap((entry) =>
    compare.metrics.flatMap((metric) => {
      const cell = entry.cells[metric];
      return cell?.deviation ? [{ entry, metric, cell }] : [];
    }),
  );
  const rowCells = (render: (entry: CompareCase) => ReactNode) =>
    cases.map((entry) => <div key={entry.case_id}>{render(entry)}</div>);
  return (
    <section className="pnl" data-compare-panel>
      <header>
        <h2>Compare</h2>
        <span className="cp" data-basis>
          {basis}
        </span>
        <span className="right">
          <span className="tag">{cases.length} CREDITS · ONE BASIS</span>
          {deviating.length ? (
            <span className="tag warn">
              <SeverityMark severity="WARNING" /> {deviating.length} DEVIATING CELLS
            </span>
          ) : null}
        </span>
      </header>
      {cases.length === 0 ? (
        <div className="pb note">No credit is compared. Nothing is inferred from silence.</div>
      ) : (
        <div className="pb flush tscroll">
          <div
            className="cmpgrid"
            data-compare
            data-basis={basis}
            style={{
              gridTemplateColumns: `minmax(120px, 1fr) repeat(${cases.length}, minmax(0, 1fr))`,
            }}
          >
            <div className="lb hdc">Metric</div>
            {cases.map((entry) => (
              <div
                key={entry.case_id}
                className="hdc"
                data-bound-snapshot={entry.snapshot}
                data-case={entry.case_id}
              >
                {entry.issuer}
                <br />
                <code className="lbl">{entry.snapshot}</code>
                {refusedLens[entry.case_id] ? (
                  <>
                    <RefusalNote refusal={refusedLens[entry.case_id]!} />
                    <button
                      type="button"
                      className="rb acc mt-1"
                      onClick={() => onSwitchLens(entry.case_id)}
                    >
                      Switch lens to {entry.snapshot}
                    </button>
                  </>
                ) : null}
              </div>
            ))}
            {compare.metrics.map((metric) => {
              return (
                <div key={metric} className="contents" data-metric={metric}>
                  <div className="lb">{labelOf(metric)}</div>
                  {cases.map((entry) => {
                    const cell = entry.cells[metric];
                    if (refusedLens[entry.case_id]) {
                      return (
                        <div key={entry.case_id} className="lb">
                          <span className="tag crit">LENS PINNED</span>
                        </div>
                      );
                    }
                    if (!cell) {
                      return (
                        <div key={entry.case_id} className="lb">
                          <span className="tag">NOT SERVED</span>
                        </div>
                      );
                    }
                    const classes = [
                      cell.stale ? "stale" : "",
                      selected === cell.passport_id ? "cellsel" : "",
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <div key={entry.case_id} className={classes || undefined}>
                        <MetricCell
                          cell={cell}
                          passport={passports[cell.passport_id] ?? null}
                          name={`${entry.issuer} ${labelOf(metric)} ${cell.value}`}
                          selected={selected === cell.passport_id}
                          onSelect={onSelect}
                        />
                      </div>
                    );
                  })}
                </div>
              );
            })}
            <div className="lb">Period</div>
            {rowCells(() => compare.basis.period)}
            <div className="lb">Scenario</div>
            {rowCells(() => compare.basis.scenario)}
            <div className="lb">Snapshot bound</div>
            {rowCells((entry) => (
              <code>{entry.snapshot}</code>
            ))}
            <div className="lb">Evidence date</div>
            {rowCells((entry) => evidenceDateOf(entry, compare.metrics, passports) ?? "not served")}
            <div className="lb">Definition</div>
            {cases.map((entry) => {
              const count = compare.metrics.filter(
                (metric) => entry.cells[metric]?.deviation,
              ).length;
              return (
                <div key={entry.case_id} className={count ? "stale" : undefined}>
                  {count ? (
                    <>
                      Deviates on {count}
                      <span className="defmark" role="img" aria-label="deviates" />
                    </>
                  ) : (
                    "House standard"
                  )}
                </div>
              );
            })}
          </div>
          {deviating.map(({ entry, metric, cell }) => {
            const passport = passports[cell.passport_id];
            return (
              <div key={cell.passport_id} className="absent" data-deviation-note={cell.passport_id}>
                <span className="defmark" aria-hidden="true" /> <b>{entry.issuer}</b> reports{" "}
                {labelOf(metric).toLowerCase()} on its own definition — {cell.value};{" "}
                {passport?.deviation?.restatement ?? "no restatement is served"}. The difference is{" "}
                <b>{cell.deviation}</b>; the mark is on the credit, on the cell and in this
                comparison.
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
