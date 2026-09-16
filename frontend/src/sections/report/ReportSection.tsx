// The saved Report payload, read only. Text stays text: this surface never
// interprets markdown, follows evidence, or offers a legacy draft action.
import type { ReportDocument } from "@/wire/v1";
import { SavedArtifact } from "@/sections/saved/SavedArtifact";

export function ReportSection({ document }: { document: ReportDocument; tab: string | null }) {
  const { body } = document;
  return (
    <div
      className="col"
      data-report-v1
      data-revision={body.revision_id}
      data-payload={body.payload_sha256}
    >
      <section className="pnl">
        <header>
          <h2>{body.case_title}</h2>
          <span className="cp">SAVED REPORT</span>
        </header>
        <div className="pb">
          <dl className="kv">
            <dt>Case</dt>
            <dd>{body.case_id}</dd>
            <dt>Run</dt>
            <dd>{body.displayed_run_id}</dd>
            <dt>Revision</dt>
            <dd>{body.revision_id}</dd>
            <dt>Payload</dt>
            <dd>sha256:{body.payload_sha256}</dd>
          </dl>
        </div>
      </section>
      {body.artifacts.map((artifact) => (
        <SavedArtifact section="report" key={artifact.route_node_id} artifact={artifact} />
      ))}
      <section className="pnl" data-report-narrative>
        <header>
          <h2>Narrative</h2>
          <span className="tag">{body.narrative.length}</span>
        </header>
        <div className="pb">
          {body.narrative.map((spans, index) => (
            <p key={index} data-report-paragraph={index}>
              {spans.map((span, spanIndex) => (
                <span key={spanIndex}>
                  {span.text}
                  {span.figure
                    ? ` [${span.figure.route_node_id} · p.${span.figure.page} · ${span.figure.matched_text}]`
                    : null}
                </span>
              ))}
            </p>
          ))}
        </div>
      </section>
    </div>
  );
}
