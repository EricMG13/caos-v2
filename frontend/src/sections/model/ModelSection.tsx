// Model — CP-CF's accepted projection, read-only (IA_SPEC.md 4.6). Centre: the
// formula bar over the selected cell, then one table per case. Right: the
// drivers, the first breach per case, the tolerance and the accepted artifact.
import { useState, type MouseEvent } from "react";
import { DriverRows, ModelDetail } from "./ModelDetail";
import { Projection, type Cell } from "./Projection";
import type { ViewProps } from "@/app/views";
import { useEvidence } from "@/evidence/EvidenceContext";
import type { ModelBody } from "@/wire/model";
import type { Passport } from "@/wire";

function firstCell(body: ModelBody): Cell | null {
  for (const projection of body.cases) {
    const line =
      projection.lines.find((l) => l.key === "closing_cash") ?? projection.lines[0] ?? null;
    if (!line) continue;
    const index = line.passport_ids.findIndex((id) => id !== null);
    const passportId = line.passport_ids[index];
    const period = projection.periods[index];
    if (index >= 0 && passportId && period) {
      return {
        case: projection.case,
        period_id: period.period_id,
        key: line.key,
        passport_id: passportId,
      };
    }
  }
  return null;
}

function FormulaBar({
  cell,
  passport,
  residual,
  available,
}: {
  cell: Cell | null;
  passport: Passport | null;
  residual: string | null;
  /** The served state of the selected period; never recomputed here. */
  available: boolean;
}) {
  if (!cell || !passport) {
    return (
      <div className="formulabar">
        <span className="coord">NO CELL SELECTED</span>
        <code>select a figure to read its derivation</code>
      </div>
    );
  }
  const ok = available;
  return (
    <div className="formulabar" data-formula={cell.passport_id}>
      <span className="coord">
        {cell.case} · {cell.period_id} · {passport.label.toUpperCase()}
      </span>
      <code>{passport.derivation}</code>
      <span className={`tag ${ok ? "ok" : "crit"} right`}>RESIDUAL {residual ?? "—"}</span>
    </div>
  );
}

export function ModelSection({ document, tab }: ViewProps<"model">) {
  const body = document.body;
  const view = tab ?? document.chrome.tabs[0]?.id ?? "projection";
  const { openPassport } = useEvidence();
  const [choice, setChoice] = useState<Cell | null>(null);
  const cell = choice && body.passports[choice.passport_id] ? choice : firstCell(body);
  const passport = cell ? (body.passports[cell.passport_id] ?? null) : null;
  const selectedPeriod = cell
    ? (body.cases
        .find((projection) => projection.case === cell.case)
        ?.periods.find((period) => period.period_id === cell.period_id) ?? null)
    : null;
  const residual =
    (cell
      ? body.cases
          .find((c) => c.case === cell.case)
          ?.periods.find((p) => p.period_id === cell.period_id)?.residual
      : null) ?? null;
  const unavailable = body.cases.flatMap((c) =>
    c.periods.filter((p) => p.state === "unavailable" && !p.propagated).map((p) => ({ c, p })),
  );

  const select = (next: Cell, subject: Passport, event: MouseEvent<HTMLButtonElement>) => {
    setChoice(next);
    openPassport(subject, event.currentTarget);
  };

  return (
    <div className="cols two" data-model={body.module_id}>
      <div className="col">
        {view === "drivers" ? (
          <section className="pnl">
            <header>
              <h2>Drivers — CP-2G</h2>
              <span className="cp">read, never edited</span>
            </header>
            <DriverRows drivers={body.drivers} />
          </section>
        ) : (
          <>
            <FormulaBar
              cell={cell}
              passport={passport}
              residual={residual}
              available={selectedPeriod?.state === "available"}
            />
            <section className="pnl">
              <header>
                <h2>Projection — per case-period</h2>
                <span className="cp">CP-CF · cash_flow_forecast</span>
                <span className="tag right">$M</span>
              </header>
              <div className="pb flush scroll">
                {body.cases.map((projection) => (
                  <Projection
                    key={projection.case}
                    projection={projection}
                    passports={body.passports}
                    selected={cell}
                    onSelect={select}
                  />
                ))}
              </div>
            </section>
            {unavailable.map(({ c, p }) => (
              <div
                key={`${c.case}-${p.period_id}`}
                className="note"
                data-unavailable={`${c.case} ${p.period_id}`}
              >
                <b>
                  Why {p.period_id} {c.case} is unavailable.
                </b>{" "}
                {p.unavailable_reason} — the residual is explicit and never forced to zero. Every
                later period in {c.case} is unavailable by propagation, never read as zero growth.
              </div>
            ))}
          </>
        )}
      </div>
      <div className="col right">
        <ModelDetail
          cases={body.cases}
          drivers={body.drivers}
          breaches={body.first_breach}
          tolerance={body.tolerance}
          artifact={body.artifact_sha256}
          acceptedAt={body.accepted_at}
        />
      </div>
    </div>
  );
}
