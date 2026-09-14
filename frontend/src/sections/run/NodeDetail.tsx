// The right column is about the selected node: its state and reason, the
// edges in, the gate's own verdict when it named one, and its attempts.
// No accept action here (brief 4.1: commands are 4.2).
import { severityOf } from "./RouteGraph";
import { reasonOf, runningOf } from "./reason";
import { SeverityMark, toneOf } from "@/chrome/SeverityMark";
import type { AttemptView } from "./types";
import type { NodeView } from "@/wire/v1";

export function NodeDetail({ node, attempts }: { node: NodeView; attempts: AttemptView[] }) {
  const running = runningOf(node, attempts);
  const severity = severityOf(node, running);
  const mine = attempts.filter((attempt) => attempt.route_node_id === node.route_node_id);
  return (
    <>
      <section className="pnl" data-node-detail={node.module_id}>
        <header>
          <h2>Selected node</h2>
          <span className="cp">
            {node.module_id} · {node.route_node_id}
          </span>
          <span className={`tag ${toneOf(severity)} right`}>
            <SeverityMark severity={severity} pulse={running} />
            {node.state}
          </span>
        </header>
        <div className="pb">
          <dl className="kv">
            <dt>Reason</dt>
            <dd className="wrap">{reasonOf(node)}</dd>
            <dt>Stage</dt>
            <dd>{node.stage}</dd>
            <dt>Edges in</dt>
            <dd>
              {node.waiting_on.length
                ? node.waiting_on.map((edge) => `${edge.type} ${edge.source}`).join(" · ")
                : "none"}
            </dd>
            <dt>Awaiting gate</dt>
            <dd>{node.awaiting_gate ? "yes" : "no"}</dd>
            {node.gate_verdict ? (
              <>
                <dt>Gate verdict</dt>
                <dd data-gate-verdict>{node.gate_verdict}</dd>
              </>
            ) : null}
          </dl>
        </div>
      </section>
      <section className="pnl">
        <header>
          <h2>Attempts — {node.module_id}</h2>
          <span className="cp">one row per try</span>
        </header>
        <div className="pb flush">
          {mine.length ? (
            mine.map((attempt) => (
              <div key={attempt.attempt_id} className="att" data-attempt={attempt.ordinal ?? "—"}>
                <span className="a">attempt {attempt.ordinal ?? "unassigned"}</span>
                <span>started {attempt.started_at}</span>
                <span className={attempt.accepted ? "t-ok" : "t-run"}>
                  {attempt.accepted ? "ACCEPTED" : "NOT ACCEPTED"}
                </span>
              </div>
            ))
          ) : (
            <div className="att">
              <span className="a">none</span>
              <span>no attempt recorded for {node.module_id}</span>
              <span>—</span>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
