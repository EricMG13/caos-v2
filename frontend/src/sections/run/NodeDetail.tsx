// The right column is about the selected node: its state and reason, the
// edges in, its attempts, the artifact digest, the limitation when RESTRICTED,
// and the node-level Accept — visible, refused NODE_NOT_ACCEPTABLE until COMPLETE.
import { severityOf } from "./RouteGraph";
import { SeverityMark, toneOf } from "@/chrome/SeverityMark";
import { RefusedControl } from "@/controls/RefusedControl";
import type { Attempt, RouteEdge, RouteNode, Stage } from "@/wire/run";
import type { Refusal } from "@/wire";

const ATTEMPT_TONE: Record<Attempt["state"], string> = {
  ACCEPTED: "ok",
  INDETERMINATE: "run",
  REFUSED: "crit",
};

export function nodeAccept(node: RouteNode): Refusal | null {
  if (node.state === "COMPLETE") return null;
  return {
    code: "NODE_NOT_ACCEPTABLE",
    clears: `${node.module_id} has an accepted attempt and is COMPLETE; it is ${node.state} — ${node.reason}`,
  };
}

export function NodeDetail({
  node,
  edges,
  attempts,
  stages,
}: {
  node: RouteNode;
  edges: RouteEdge[];
  attempts: Attempt[];
  stages: Stage[];
}) {
  const edgesIn = edges.filter((edge) => edge.to === node.module_id);
  const severity = severityOf(node);
  const stage = stages.find((s) => s.n === node.stage)?.label ?? `Stage ${node.stage}`;
  return (
    <>
      <section className="pnl" data-node-detail={node.module_id}>
        <header>
          <h2>Selected node</h2>
          <span className="cp">
            {node.module_id} · {node.name}
          </span>
          <span className={`tag ${toneOf(severity)} right`}>
            <SeverityMark severity={severity} pulse={node.running} />
            {node.state}
          </span>
        </header>
        <div className="pb">
          <dl className="kv">
            <dt>Reason</dt>
            <dd className="wrap">{node.reason}</dd>
            <dt>Stage</dt>
            <dd>{stage}</dd>
            <dt>Edges in</dt>
            <dd>
              {edgesIn.length
                ? edgesIn.map((edge) => `${edge.type} ${edge.from}`).join(" · ")
                : "none"}
            </dd>
            <dt>Artifact</dt>
            <dd>{node.artifact_sha256 ? `sha256:${node.artifact_sha256.slice(0, 12)}…` : "—"}</dd>
            {node.extension ? (
              <>
                <dt>Placed by</dt>
                <dd>host extension · stage {node.stage}</dd>
              </>
            ) : null}
          </dl>
          {node.limitation ? (
            <div className="note limitation" data-limitation>
              <b>Limitation carried forward.</b> {node.limitation}
            </div>
          ) : null}
          <div className="actions">
            <RefusedControl refusal={nodeAccept(node)} className="rb solid">
              Accept
            </RefusedControl>
          </div>
        </div>
      </section>
      <section className="pnl">
        <header>
          <h2>Attempts — {node.module_id}</h2>
          <span className="cp">one row per try</span>
        </header>
        <div className="pb flush">
          {attempts.length ? (
            attempts.map((attempt) => (
              <div key={attempt.n} className="att" data-attempt={attempt.n}>
                <span className="a">attempt {attempt.n}</span>
                <span>
                  started {attempt.started_at} · charge {attempt.charge ?? "—"} ·{" "}
                  {attempt.generation_id ?? "gen_—"}
                </span>
                <span className={`t-${ATTEMPT_TONE[attempt.state]}`}>{attempt.state}</span>
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
