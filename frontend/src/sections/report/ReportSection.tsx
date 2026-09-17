// The saved Report payload, read only. Text stays text: this surface never
// interprets markdown, follows evidence, or offers a legacy draft action.
import type { ReportDocument } from "@/wire/v1";
import { SavedArtifact, SavedHeader } from "@/sections/saved/SavedArtifact";

export function ReportSection({ document }: { document: ReportDocument; tab: string | null }) {
  const { body } = document;
  return (
    <div
      className="col"
      data-report-v1
      data-revision={body.revision_id}
      data-payload={body.payload_sha256}
    >
      <SavedHeader
        label="SAVED REPORT"
        caseTitle={body.case_title}
        caseId={body.case_id}
        runId={body.displayed_run_id}
        revisionId={body.revision_id}
        payloadSha256={body.payload_sha256}
      />
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
