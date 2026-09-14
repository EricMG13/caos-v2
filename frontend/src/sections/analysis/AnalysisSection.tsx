// Analysis (IA_SPEC.md 4.3), v1 wire (brief 4.1, slice 4.1j). Every accepted
// handoff in route order carries the host's own facts, the model's own
// analysis and the reminder that the host performs no calculation; a pending
// node is named with the state the route left it in, never invented.
//
// The evidence drawer is not mounted here: `CitationView.rects` are page
// points, not the fractions `EvidenceDrawer` expects, and normalising them
// needs the page's own dimensions -- rendering a page is 4.4. Citations are
// shown inline instead.
import { NODE_SEVERITY, nodeTone } from "./tone";
import { SeverityMark } from "@/chrome/SeverityMark";
import type { AnalysisDocument, CitationView, HandoffView, PendingNode } from "@/wire/v1";

const SCREENING_NOTICE = "SCREENING ONLY: a screen, not committee clearance.";

function SourceFacts({ facts }: { facts: readonly CitationView[] }) {
  return (
    <section className="pnl" data-source-facts>
      <header>
        <h3>Source facts (host-verified citations)</h3>
        <span className="tag">{facts.length}</span>
      </header>
      {facts.length === 0 ? (
        <div className="pb note">No citation is carried on this handoff.</div>
      ) : (
        <ul className="pb flush plain">
          {facts.map((fact, index) => (
            <li
              key={`${fact.document_sha256}-${index}`}
              className="ev"
              data-citation
              data-withdrawn={fact.withdrawn_at !== null}
            >
              <span className="h">
                {fact.filename} · p.{fact.page}
              </span>
              <blockquote className="matched" style={{ margin: 0 }}>
                {fact.matched_text}
              </blockquote>
              {fact.withdrawn_at !== null ? (
                <div className="note limitation" data-withdrawn-at={fact.withdrawn_at}>
                  <b>This source has been withdrawn</b> at {fact.withdrawn_at}. The citation stays
                  so the conclusion that rests on it stays explicable.
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** The model's own prose, rendered as text. Markdown syntax is never parsed
    into markup: a heading or emphasis character reaches the page as itself. */
function ModelAnalysis({ text }: { text: string }) {
  return (
    <section className="pnl" data-model-analysis>
      <header>
        <h3>Analysis (model-authored, not host-verified)</h3>
      </header>
      <div className="pb">
        <pre className="model-text">{text}</pre>
      </div>
    </section>
  );
}

function HostCalculation() {
  return (
    <section className="pnl" data-host-calculation>
      <header>
        <h3>Deterministic calculations: none performed by the host</h3>
      </header>
    </section>
  );
}

function HandoffCard({ handoff }: { handoff: HandoffView }) {
  return (
    <section className="pnl" data-handoff={handoff.module_id}>
      <header>
        <h2>{handoff.module_id}</h2>
        <span className="cp">{handoff.route_node_id}</span>
        <span className="right">
          <span className="tag" data-qa-status>
            {handoff.qa_status}
          </span>
        </span>
      </header>
      <div className="pb col">
        <dl className="kv">
          <dt>Committee status</dt>
          <dd data-committee-status>
            {handoff.committee_status} · {handoff.decision_scope}
          </dd>
          <dt>Confidence</dt>
          <dd data-confidence>
            {handoff.confidence_score} · {handoff.confidence_band}
          </dd>
          <dt>Accepted</dt>
          <dd>
            <time dateTime={handoff.accepted_at}>{handoff.accepted_at}</time>
          </dd>
        </dl>
        {handoff.screening_only ? (
          <div className="note" data-screening-only>
            <b>{SCREENING_NOTICE}</b>
          </div>
        ) : null}
        <div className="note" data-limitation-flags>
          <b>Limitation flags.</b>{" "}
          {handoff.limitation_flags.length ? handoff.limitation_flags.join(", ") : "none"}
        </div>
        {handoff.validation_warnings.length ? (
          <div className="note" data-validation-warnings>
            <b>Validation warnings.</b> {handoff.validation_warnings.join(", ")}
          </div>
        ) : null}
        <SourceFacts facts={handoff.source_facts} />
        <ModelAnalysis text={handoff.model_analysis} />
        <HostCalculation />
      </div>
    </section>
  );
}

function PendingList({ pending }: { pending: readonly PendingNode[] }) {
  return (
    <section className="pnl" data-pending>
      <header>
        <h2>Pending nodes</h2>
        <span className="cp">not yet accepted</span>
        <span className="right">
          <span className="tag">{pending.length}</span>
        </span>
      </header>
      {pending.length === 0 ? (
        <div className="pb note">Every pinned node on this run has been accepted.</div>
      ) : (
        <ul className="pb flush plain">
          {pending.map((node) => (
            <li
              key={node.route_node_id}
              className="frontier"
              data-pending-node={node.module_id}
              data-state={node.state}
            >
              <span className="id">{node.module_id}</span>
              <span className="cp">{node.route_node_id}</span>
              <span className={`tag ${nodeTone(node.state)}`}>
                <SeverityMark severity={NODE_SEVERITY[node.state]} /> {node.state}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function AnalysisSection({ document }: { document: AnalysisDocument; tab: string | null }) {
  const { body } = document;
  const stale =
    body.displayed_run_id !== null &&
    body.latest_run_id !== null &&
    body.displayed_run_id !== body.latest_run_id;
  return (
    <div className="col" data-analysis>
      {stale ? (
        <div className="note" data-stale-run>
          <b>This is not the latest run.</b> Displayed run {body.displayed_run_id}; the latest run
          for this case is {body.latest_run_id}.
        </div>
      ) : null}
      <section className="pnl">
        <header>
          <h2>Handoffs</h2>
          {body.subject ? (
            <span className="cp">
              {body.subject.issuer_name} · {body.subject.reporting_period}
            </span>
          ) : null}
          <span className="right">
            <span className="tag ok">{body.handoffs.length} ACCEPTED</span>
          </span>
        </header>
        {body.handoffs.length === 0 ? (
          <div className="pb note">No handoff has been accepted on this run yet.</div>
        ) : null}
      </section>
      {body.handoffs.map((handoff) => (
        <HandoffCard key={handoff.route_node_id} handoff={handoff} />
      ))}
      <PendingList pending={body.pending} />
    </div>
  );
}
