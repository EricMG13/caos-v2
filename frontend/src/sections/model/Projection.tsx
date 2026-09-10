// One case of CP-CF's projection, read-only: a row per period, a column per
// line, and the residual as its own column. A period whose residual exceeds
// tolerance is unavailable with its reason; every later period in the case is
// unavailable by propagation and never shows a number.
import type { MouseEvent } from "react";
import type { ProjectionCase, ProjectionLine, ProjectionPeriod } from "@/wire/model";
import type { Passport } from "@/wire";

export interface Cell {
  case: string;
  period_id: string;
  key: string;
  passport_id: string;
}

/** The earliest unreconciled period the propagation comes from. */
export function propagatedFrom(periods: ProjectionPeriod[], index: number): string | null {
  for (let i = index - 1; i >= 0; i -= 1) {
    const period = periods[i];
    if (period && period.state === "unavailable" && !period.propagated) return period.period_id;
  }
  return null;
}

function splitLines(lines: ProjectionLine[]): {
  figures: ProjectionLine[];
  metrics: ProjectionLine[];
} {
  return {
    figures: lines.filter((line) => line.group !== "metrics"),
    metrics: lines.filter((line) => line.group === "metrics"),
  };
}

export function Projection({
  projection,
  passports,
  selected,
  onSelect,
}: {
  projection: ProjectionCase;
  passports: Record<string, Passport>;
  selected: Cell | null;
  onSelect: (cell: Cell, passport: Passport, event: MouseEvent<HTMLButtonElement>) => void;
}) {
  const { figures, metrics } = splitLines(projection.lines);
  const columns = figures.length + metrics.length + 2;
  const reconciled = projection.periods.filter((p) => p.state === "available").length;
  const firstUnavailable = projection.periods.find((p) => p.state === "unavailable");
  const caption = firstUnavailable
    ? `${projection.case} · ${reconciled} of ${projection.periods.length} reconciled · unavailable from ${firstUnavailable.period_id}`
    : `${projection.case} · ${reconciled} of ${projection.periods.length} reconciled`;

  const cell = (line: ProjectionLine, period: ProjectionPeriod, index: number) => {
    const value = line.values[index] ?? null;
    const passportId = line.passport_ids[index] ?? null;
    const passport = passportId ? passports[passportId] : undefined;
    if (value === null || !passportId || !passport) return <td key={line.key}>{value ?? "—"}</td>;
    const on =
      selected?.case === projection.case &&
      selected.period_id === period.period_id &&
      selected.key === line.key;
    return (
      <td key={line.key} className={on ? "selc" : undefined}>
        <button
          type="button"
          className="cellbtn"
          data-passport-id={passportId}
          aria-pressed={on}
          aria-label={`${line.label} ${period.period_id} ${projection.case} ${value}`}
          onClick={(event) =>
            onSelect(
              {
                case: projection.case,
                period_id: period.period_id,
                key: line.key,
                passport_id: passportId,
              },
              passport,
              event,
            )
          }
        >
          {value}
        </button>
      </td>
    );
  };

  return (
    <table className="proj" data-projection={projection.case} data-case={projection.case}>
      <thead>
        <tr>
          <th scope="col">Period</th>
          {figures.map((line) => (
            <th key={line.key} scope="col">
              {line.label}
            </th>
          ))}
          <th scope="col" className="resid">
            RESIDUAL
          </th>
          {metrics.map((line) => (
            <th key={line.key} scope="col">
              {line.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr className="grp">
          <td colSpan={columns}>{caption}</td>
        </tr>
        {projection.periods.map((period, index) => {
          if (period.propagated) {
            const origin = propagatedFrom(projection.periods, index) ?? "an earlier period";
            return (
              <tr
                key={period.period_id}
                className="prop"
                data-period={period.period_id}
                data-propagated="true"
              >
                <td>{period.period_id} · UNAVAILABLE</td>
                <td colSpan={columns - 1}>
                  unavailable · propagated from {origin} — never read as zero growth ·
                  FORECAST_RESIDUAL_UNRECONCILED
                </td>
              </tr>
            );
          }
          const unavailable = period.state === "unavailable";
          return (
            <tr
              key={period.period_id}
              className={unavailable ? "unav" : undefined}
              data-period={period.period_id}
              data-reason={unavailable ? (period.unavailable_reason ?? "unavailable") : undefined}
            >
              <td>
                {period.period_id}
                {unavailable ? " · UNAVAILABLE" : ""}
                {unavailable ? <span className="why">{period.unavailable_reason}</span> : null}
              </td>
              {figures.map((line) => cell(line, period, index))}
              <td
                className="resid"
                data-residual={period.state === "available" ? "within" : "exceeds"}
              >
                {period.residual ?? "—"}
              </td>
              {metrics.map((line) => cell(line, period, index))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
