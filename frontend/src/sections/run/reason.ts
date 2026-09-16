// Node states are the bundle's, recomputed from accepted attempts — never
// stored (CLAUDE.md invariant 10, "recovery is recomputation"). `reasonOf`
// renders the wire's own words: `gate_verdict` when the gate named one
// (CLAUDE.md Phase 5 ledger, "the workspace cannot show the cause" — now it
// can), else the typed edges this node is waiting on.
import type { AttemptView } from "./types";
import type { NodeView, RunView } from "@/wire/v1";

/** Every direct edge this node names, as `TYPE source`. */
function edgesOf(node: Pick<NodeView, "waiting_on">): string {
  return node.waiting_on.map((edge) => `${edge.type} ${edge.source}`).join(" · ");
}

/** Whether the run has stopped moving. `RUNNING` is the only state with work
    ahead of it; the other four are ends, and a node's readiness on an ended run
    says what was ready when it stopped, not what happens next. */
function ended(status: RunView["status"]): boolean {
  return status !== "RUNNING";
}

/** The cause the wire carries for this node's state: the gate's own verdict
    when the gate named one, else the typed edges it names. Never invented.

    The run's status is read too, because a node state alone cannot say it. Node
    states are recomputed from accepted artifacts (invariant 10), so a node the
    run never reached is RUNNABLE on an ended run exactly as it would be on a
    live one -- and the page said "in the frontier" beside a Status of BLOCKED.
    The state is right; reading it without the run's status was not. */
export function reasonOf(
  node: Pick<NodeView, "state" | "waiting_on" | "gate_verdict" | "awaiting_gate">,
  status: RunView["status"],
): string {
  const edges = edgesOf(node);
  // Before the gate's verdict, because the verdict is about whether this node
  // *could* run and the run has stopped either way. CP-5 on a blocked run reads
  // `gate_verdict: READY` with every input met, and "READY" alone beside a
  // Status of BLOCKED tells a reader the opposite of what happened. The verdict
  // is kept, after the fact that overrides it.
  if (ended(status) && node.state === "RUNNABLE") {
    const rest = [node.gate_verdict, edges].filter(Boolean).join(" · ");
    return rest ? `did not run · ${rest}` : "did not run";
  }
  if (node.gate_verdict) return edges ? `${node.gate_verdict} · ${edges}` : node.gate_verdict;
  if (node.state === "BLOCKED") return edges ? `waits on ${edges}` : "blocked with no named edge";
  if (node.state === "RUNNABLE") {
    // Ready, and the run stopped first. Said without a cause, because the cause
    // belongs to whichever node ended the run and this one cannot name it.
    if (ended(status)) return edges ? `did not run · ${edges}` : "did not run";
    if (node.awaiting_gate) return edges ? `awaiting the gate · ${edges}` : "awaiting the gate";
    return edges ? `in the frontier · ${edges}` : "in the frontier";
  }
  if (node.state === "COMPLETE") return edges ? `accepted · ${edges}` : "accepted";
  return edges || "restricted";
}

/** A node is drawn running while it holds an attempt not yet accepted —
    recomputed from the attempts the wire carries, never a stored flag.

    An ended run has nothing running, whatever its nodes hold. A validated
    Blocked verdict accepts nothing, so the very node whose answer ended the run
    keeps an unaccepted attempt and was drawn pulsing next to a Status of
    BLOCKED. */
export function runningOf(
  node: Pick<NodeView, "route_node_id" | "state">,
  attempts: readonly AttemptView[],
  status: RunView["status"],
): boolean {
  return (
    !ended(status) &&
    node.state === "RUNNABLE" &&
    attempts.some((attempt) => attempt.route_node_id === node.route_node_id && !attempt.accepted)
  );
}
