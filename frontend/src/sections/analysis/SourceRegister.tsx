// CP-0: the pinned sources, each with its grade, disposition and page count.
import type { RegisterRow } from "@/wire/analysis";
import type { Disposition } from "@/wire/upload";

const DISPOSITION_TONE: Record<Disposition, string> = {
  ADMITTED: "ok",
  EXCLUDED_LOW_VALUE: "",
  PENDING: "warn",
  WITHDRAWN: "crit",
};

export function SourceRegister({ rows }: { rows: RegisterRow[] }) {
  const admitted = rows.filter((row) => row.disposition === "ADMITTED").length;
  return (
    <section className="pnl" data-register>
      <header>
        <h2>Source register</h2>
        <span className="cp">CP-0</span>
        <span className="right">
          <span className="tag ok">{admitted} ADMITTED</span>
        </span>
      </header>
      <ul className="pb flush plain">
        {rows.map((row) => (
          <li key={row.source_id} className="srow" data-source={row.label}>
            <span className={`gr ${row.grade.toLowerCase()}`} title={`Grade ${row.grade}`}>
              <span className="sr-only">Grade </span>
              {row.grade}
            </span>
            <div style={{ minWidth: 0 }}>
              <div className="nm" title={row.title}>
                {row.title}
              </div>
              <div className="mt tabular">
                {row.label} · {row.pages} P
              </div>
            </div>
            <span className={`tag ${DISPOSITION_TONE[row.disposition]}`}>
              {row.disposition.replace(/_/g, " ")}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
