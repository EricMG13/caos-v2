// The right column is always about the selected thing: the opinion this
// revision would carry, what refuses the freeze, every saved revision, and
// the lineage the draft rests on.
import { shortDigest } from "./text";
import { RefusalNote, RefusedControl } from "@/controls/RefusedControl";
import type { ServedRole } from "@/wire";
import type { LineageRow, Opinion, ReportBody, Revision } from "@/wire/report";

const STATE_TONE: Record<string, string> = { ACCEPTED: "ok", RESTRICTED: "warn" };

function OpinionFacts({ opinion, prior }: { opinion: Opinion; prior: boolean }) {
  const mark = prior
    ? { "data-prior-opinion": opinion.revision_id }
    : { "data-opinion": opinion.revision_id };
  return (
    <p className="note mt-2" {...mark}>
      <b>{prior ? "Prior opinion" : "Opinion"}</b> · signed by <b>{opinion.signed_by}</b> at{" "}
      <time dateTime={opinion.signed_at}>{opinion.signed_at}</time> on <b>{opinion.revision_id}</b>{" "}
      · digest{" "}
      <code className="tabular" title={opinion.digest}>
        sha256:{shortDigest(opinion.digest)}
      </code>
      {prior ? <> · binds {opinion.revision_id} only and does not carry forward.</> : "."}
    </p>
  );
}

function OpinionPanel({ body, role }: { body: ReportBody; role: ServedRole }) {
  const { revision, opinion, prior_opinion: prior, freeze } = body;
  return (
    <section className="pnl" aria-labelledby="opinion-title">
      <header>
        <h2 id="opinion-title">{opinion ? "Opinion" : "Opinion and freeze"}</h2>
        <span className="cp">BINDS {revision.id} EXACTLY</span>
        <span className="right">
          {opinion ? (
            <span className="tag ok">SIGNED</span>
          ) : freeze ? (
            <span className="tag crit">REFUSED</span>
          ) : (
            <span className="tag">UNSIGNED</span>
          )}
        </span>
      </header>
      <div className="pb">
        <dl className="kv">
          <dt>Revision</dt>
          <dd>{revision.id}</dd>
          <dt>Digest</dt>
          <dd title={revision.digest}>sha256:{shortDigest(revision.digest)}</dd>
          <dt>Saved</dt>
          <dd>
            <time dateTime={revision.saved_at}>{revision.saved_at}</time>
          </dd>
          <dt>Signer</dt>
          <dd>
            {role.role} · {role.standing}
          </dd>
        </dl>
        {opinion ? (
          <OpinionFacts opinion={opinion} prior={false} />
        ) : (
          <p className="note mt-2" data-opinion="none">
            No opinion on <b>{revision.id}</b>. Signing binds this exact saved revision by digest
            (expected-head CAS); a later edit is a new revision, never an amendment.
          </p>
        )}
        {!opinion && prior ? <OpinionFacts opinion={prior} prior /> : null}
        {freeze ? <RefusalNote refusal={freeze} /> : null}
        <div className="mt-2">
          <RefusedControl
            refusal={freeze}
            className="rb"
            reasonDisplay="hidden"
            aria-label="Freeze the revision"
          >
            Freeze
          </RefusedControl>
        </div>
      </div>
    </section>
  );
}

function RevisionsPanel({
  revisions,
  current,
  opinions,
}: {
  revisions: Revision[];
  current: string;
  opinions: Opinion[];
}) {
  return (
    <section className="pnl" aria-labelledby="revlist-title">
      <header>
        <h2 id="revlist-title">Revisions</h2>
        <span className="cp">{revisions.length} SAVED</span>
      </header>
      <ul className="pb flush" aria-label="Saved revisions">
        {[...revisions].reverse().map((revision) => {
          const on = revision.id === current;
          const signed = opinions.some((o) => o.revision_id === revision.id);
          return (
            <li
              key={revision.id}
              className="ev"
              data-revision-item={revision.id}
              aria-current={on ? "true" : undefined}
            >
              <span className="h tabular">{revision.id}</span>
              {on ? (
                <span className="tag warn">CURRENT · DRAFT</span>
              ) : signed ? (
                <span className="tag ok">OPINION SIGNED</span>
              ) : (
                <span className="tag">SAVED</span>
              )}
              <span className="m">
                <time dateTime={revision.saved_at}>{revision.saved_at}</time> · {revision.author} ·{" "}
                <span title={revision.digest}>sha256:{shortDigest(revision.digest)}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function LineagePanel({ rows }: { rows: LineageRow[] }) {
  return (
    <section className="pnl" aria-labelledby="lineage-title">
      <header>
        <h2 id="lineage-title">Lineage</h2>
        <span className="cp">BUILT FROM {rows.length} ARTIFACTS</span>
      </header>
      <div className="pb flush">
        <table className="prov">
          <thead>
            <tr>
              <th scope="col">Module</th>
              <th scope="col">Artifact</th>
              <th scope="col">State</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.module_id} data-lineage={row.module_id}>
                <td>{row.module_id}</td>
                <td title={row.artifact_sha256}>sha256:{shortDigest(row.artifact_sha256)}</td>
                <td>
                  <span className={`tag ${STATE_TONE[row.state] ?? ""}`}>{row.state}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function OpinionColumn({ body, role }: { body: ReportBody; role: ServedRole }) {
  const opinions = [body.opinion, body.prior_opinion].filter((o): o is Opinion => o !== null);
  return (
    <>
      <OpinionPanel body={body} role={role} />
      <RevisionsPanel revisions={body.revisions} current={body.revision.id} opinions={opinions} />
      <LineagePanel rows={body.lineage} />
    </>
  );
}
