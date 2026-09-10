// The right column of Model: the driver rows with their evidence, the first
// covenant breach per case, the tolerance, and the accepted CP-CF artifact.
// No worksheet, no assumptions editor, no sign-off, no download.
import { CitationChip } from "@/evidence/CitationChip";
import type { Breach, DriverRow, ProjectionCase } from "@/wire/model";

export function DriverRows({ drivers }: { drivers: DriverRow[] }) {
  return (
    <div className="pb flush" data-drivers={drivers.length}>
      {drivers.map((row) => (
        <div key={row.driver} className="driver" data-driver={row.driver.slice(0, 4)}>
          <span className="h">
            {row.driver} · <code>{row.value}</code>
          </span>
          <span className={`tag ${row.state === "OPEN" ? "warn" : "ok"}`}>{row.state}</span>
          <span className="m">
            {row.rationale} · <CitationChip citation={row.citation} />
          </span>
        </div>
      ))}
    </div>
  );
}

export function ModelDetail({
  cases,
  drivers,
  breaches,
  tolerance,
  artifact,
  acceptedAt,
}: {
  cases: ProjectionCase[];
  drivers: DriverRow[];
  breaches: Breach[];
  tolerance: string;
  artifact: string;
  acceptedAt: string;
}) {
  return (
    <>
      <section className="pnl">
        <header>
          <h2>Drivers</h2>
          <span className="cp">CP-2G · authored, with evidence</span>
          <span className="tag right">{drivers.length}</span>
        </header>
        <DriverRows drivers={drivers} />
      </section>
      <section className="pnl">
        <header>
          <h2>Reconciliation</h2>
          <span className="cp">CP-CF · accepted</span>
        </header>
        <div className="pb">
          <dl className="kv">
            <dt>Tolerance</dt>
            <dd>{tolerance}</dd>
            {cases.map((projection) => {
              const breach = breaches.find((b) => b.case === projection.case);
              return (
                <div key={projection.case} className="contents" data-breach={projection.case}>
                  <dt>First breach · {projection.case}</dt>
                  <dd className="wrap">
                    {breach
                      ? `${breach.period_id} · ${breach.covenant}`
                      : `none in ${projection.periods.filter((p) => p.state === "available").length} available periods`}
                  </dd>
                </div>
              );
            })}
            <dt>Artifact</dt>
            <dd className="wrap">sha256:{artifact}</dd>
            <dt>Accepted</dt>
            <dd>
              <time dateTime={acceptedAt}>{acceptedAt}</time>
            </dd>
          </dl>
        </div>
        <div className="absent">
          <b>Not on this page, by decision.</b> No worksheet, assumptions, scenarios to edit,
          sign-off or download: the workbook build went with CP-MODEL. What remains is read.
        </div>
      </section>
    </>
  );
}
