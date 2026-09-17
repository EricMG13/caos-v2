// One saved artifact, drawn the same way wherever it is read. The shape is
// keyed by `section` from the start -- Committee's own saved view (next)
// reads the identical panel over the identical v1 shape, differing only in
// the `data-` prefix its own specs select on, so the panel lives here rather
// than once per section: two copies drift, and a reader comparing a filing
// against the report behind it would be comparing two renderers.
import type { KeyboardEvent } from "react";

/** The saved-artifact shape every saved-view section reads; narrower than any one document. */
export interface SavedArtifactView {
  route_node_id: string;
  qa_status: string;
  committee_status: string;
  artifact_sha256: string;
  record_sha256: string;
  decision_scope: string;
  markdown: string;
  record: string;
  limitation_flags: readonly string[];
  validation_warnings: readonly string[];
}

function scrollArtifact(event: KeyboardEvent<HTMLPreElement>) {
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    event.currentTarget.scrollBy({ left: event.key === "ArrowRight" ? 40 : -40 });
  }
}

/** A named list, or "none" -- never a blank that reads as absence. `mark` is
    the section's own `data-` hook, which its specs select the line by. */
export function Values({
  label,
  values,
  mark,
}: {
  label: string;
  values: readonly string[];
  mark?: string;
}) {
  return (
    <div className="note" {...(mark ? { [mark]: true } : {})}>
      <b>{label}</b> {values.length ? values.join(", ") : "none"}
    </div>
  );
}

/** Wide canonical text, kept reachable by keyboard scroll rather than left a
    plain block. `.artifact-scroll{min-height:24px}` (caos.css) is what keeps
    a one-line body at the WCAG 2.5.8 target size; without it, a `pre` given
    `tabIndex` here is an interactive control that reads 17px tall to the a11y
    layout probe. */
/* eslint-disable jsx-a11y/no-noninteractive-element-interactions */
function ArtifactBody({ mark, label, text }: { mark: string; label: string; text: string }) {
  return (
    <pre
      className="tscroll artifact-scroll"
      {...{ [mark]: true }}
      aria-label={label}
      role="region"
      tabIndex={0}
      onKeyDown={scrollArtifact}
    >
      {text}
    </pre>
  );
}
/* eslint-enable jsx-a11y/no-noninteractive-element-interactions */

/** The case summary panel both sections open with -- same four fields, same
    shape, differing only in the badge naming which saved view this is. */
export function SavedHeader({
  label,
  caseTitle,
  caseId,
  runId,
  revisionId,
  payloadSha256,
}: {
  label: string;
  caseTitle: string;
  caseId: string;
  runId: string;
  revisionId: string;
  payloadSha256: string;
}) {
  return (
    <section className="pnl">
      <header>
        <h2>{caseTitle}</h2>
        <span className="cp">{label}</span>
      </header>
      <div className="pb">
        <dl className="kv">
          <dt>Case</dt>
          <dd>{caseId}</dd>
          <dt>Run</dt>
          <dd>{runId}</dd>
          <dt>Revision</dt>
          <dd>{revisionId}</dd>
          <dt>Payload</dt>
          <dd>sha256:{payloadSha256}</dd>
        </dl>
      </div>
    </section>
  );
}

export function SavedArtifact({
  artifact,
  section,
}: {
  artifact: SavedArtifactView;
  section: "report" | "committee";
}) {
  return (
    <section className="pnl" {...{ [`data-${section}-artifact`]: artifact.route_node_id }}>
      <header>
        <h2>{artifact.route_node_id}</h2>
        <span className="cp">
          {artifact.qa_status} · {artifact.committee_status}
        </span>
      </header>
      <div className="pb">
        <dl className="kv">
          <dt>Artifact</dt>
          <dd>sha256:{artifact.artifact_sha256}</dd>
          <dt>Record</dt>
          <dd>sha256:{artifact.record_sha256}</dd>
          <dt>Scope</dt>
          <dd>{artifact.decision_scope}</dd>
        </dl>
        <ArtifactBody
          mark={`data-${section}-artifact-text`}
          label="Saved artifact markdown"
          text={artifact.markdown}
        />
        <ArtifactBody
          mark={`data-${section}-artifact-record`}
          label="Saved artifact record"
          text={artifact.record}
        />
        <Values
          label="Limitations."
          values={artifact.limitation_flags}
          mark={`data-${section}-limitations`}
        />
        <Values
          label="Validation warnings."
          values={artifact.validation_warnings}
          mark={`data-${section}-warnings`}
        />
      </div>
    </section>
  );
}
