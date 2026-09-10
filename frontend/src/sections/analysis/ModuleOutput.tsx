// The centre column: the module output for the selected tab. CP-1 is the
// normalised financials with the formula bar, the conflict register, the
// adjusted-vs-reported comparison and the step outputs; CP-6A is the debate;
// any other module renders its accepted artifact in summary. A RESTRICTED
// module renders with its limitation attached, never hidden, never an error.
import { Adjusted, Conflicts } from "./Conflicts";
import { Debate } from "./Debate";
import { FinancialsPanel } from "./Financials";
import { Steps } from "./Steps";
import { NODE_SEVERITY, nodeTone } from "./tone";
import { SeverityMark } from "@/chrome/SeverityMark";
import { CitationChip } from "@/evidence/CitationChip";
import type { AnalysisBody, ModuleTab, TraceRow } from "@/wire/analysis";

function Limitation({ module }: { module: ModuleTab }) {
  if (!module.limitation) return null;
  return (
    <div className="note" data-limitation data-limitation-state={module.state}>
      <span className={`tag ${nodeTone(module.state)}`}>
        <SeverityMark severity={NODE_SEVERITY[module.state]} /> {module.state}
      </span>{" "}
      {module.limitation}
    </div>
  );
}

function ArtifactSummary({ module, trace }: { module: ModuleTab; trace: TraceRow[] }) {
  const anchored = trace.filter((row) => row.module_id === module.module_id);
  return (
    <section className="pnl" data-artifact={module.module_id}>
      <header>
        <h2>{module.name}</h2>
        <span className="cp">{module.module_id}</span>
        <span className="right">
          <span className={`tag ${nodeTone(module.state)}`}>
            <SeverityMark severity={NODE_SEVERITY[module.state]} /> {module.state}
          </span>
        </span>
      </header>
      <div className="pb col">
        <dl className="kv">
          <dt>Module</dt>
          <dd>{module.module_id}</dd>
          <dt>State</dt>
          <dd>{module.state}</dd>
          <dt>Anchored in the trace</dt>
          <dd>{anchored.length}</dd>
        </dl>
        {anchored.length ? (
          <ul className="plain">
            {anchored.map((row) => (
              <li key={row.rank} className="ev">
                <span className="h">
                  #{row.rank} {row.heading}
                </span>
                <span className="tag">{row.confidence}%</span>
                <span className="m">
                  <CitationChip citation={row.citation} />
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="note">This module anchors no ranked row in the evidence trace.</div>
        )}
        <div className="note">
          Accepted artifact, read here. Acceptance and the compile form live in Run.
        </div>
      </div>
    </section>
  );
}

export function ModuleOutput({ module, body }: { module: ModuleTab | null; body: AnalysisBody }) {
  if (!module) {
    return (
      <div className="note" data-module="none">
        No module output is served for this tab.
      </div>
    );
  }
  return (
    <div className="col" data-module={module.module_id} data-module-state={module.state}>
      <Limitation module={module} />
      {module.module_id === "CP-1" ? (
        <>
          <FinancialsPanel financials={body.financials} passports={body.passports} />
          <Conflicts conflicts={body.conflicts} />
          <Adjusted rows={body.adjusted} />
          <Steps steps={body.steps} />
        </>
      ) : module.module_id === "CP-6A" ? (
        <Debate debate={body.debate} />
      ) : (
        <ArtifactSummary module={module} trace={body.trace} />
      )}
    </div>
  );
}
