import type { CommitteeDocument } from "@/wire/v1";

function Values({ label, values }: { label: string; values: readonly string[] }) {
  return (
    <div className="note">
      <b>{label}</b> {values.length ? values.join(", ") : "none"}
    </div>
  );
}

function Artifact({ artifact }: { artifact: CommitteeDocument["body"]["artifacts"][number] }) {
  return (
    <section className="pnl" data-committee-artifact={artifact.route_node_id}>
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
        <div data-committee-artifact-text>{artifact.markdown}</div>
        <div data-committee-artifact-record>{artifact.record}</div>
        <Values label="Limitations." values={artifact.limitation_flags} />
        <Values label="Validation warnings." values={artifact.validation_warnings} />
      </div>
    </section>
  );
}

function Filing({ document }: { document: CommitteeDocument }) {
  const { body } = document;
  const receipt = body.receipt;
  return (
    <section className="pnl" data-committee-filing data-state={body.state}>
      <header>
        <h2>Committee state</h2>
        <span className="tag">{body.state}</span>
      </header>
      <div className="pb">
        <dl className="kv">
          <dt>Signers</dt>
          <dd>{body.signed_by.join(", ")}</dd>
          <dt>Frozen by</dt>
          <dd>{body.frozen_by}</dd>
          <dt>Filed by</dt>
          <dd>{body.filed_by ?? "—"}</dd>
        </dl>
        {receipt ? (
          <dl className="kv" data-committee-receipt>
            <dt>Receipt case</dt>
            <dd>{receipt.case_id}</dd>
            <dt>Receipt run</dt>
            <dd>{receipt.run_id}</dd>
            <dt>Receipt revision</dt>
            <dd>{receipt.revision_id}</dd>
            <dt>Receipt payload</dt>
            <dd>sha256:{receipt.payload_sha256}</dd>
            <dt>Receipt signer</dt>
            <dd>{receipt.signed_by}</dd>
            <dt>Receipt freezer</dt>
            <dd>{receipt.frozen_by}</dd>
            <dt>Receipt filer</dt>
            <dd>{receipt.filed_by}</dd>
            <dt>Renderer</dt>
            <dd>sha256:{receipt.renderer_sha256}</dd>
            <dt>Filed event</dt>
            <dd>sha256:{receipt.filed_event_sha256}</dd>
          </dl>
        ) : null}
      </div>
    </section>
  );
}

export function CommitteeSection({
  document,
}: {
  document: CommitteeDocument;
  tab: string | null;
}) {
  const { body } = document;
  return (
    <div
      className="col"
      data-committee-v1
      data-case={body.case_id}
      data-run={body.displayed_run_id}
      data-revision={body.revision_id}
      data-payload={body.payload_sha256}
    >
      <section className="pnl">
        <header>
          <h2>{body.case_title}</h2>
          <span className="cp">SAVED COMMITTEE</span>
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
        <Artifact key={artifact.route_node_id} artifact={artifact} />
      ))}
      <Filing document={document} />
    </div>
  );
}
