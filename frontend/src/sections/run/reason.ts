// Node states are the bundle's, recomputed from accepted attempts — never
// stored (CLAUDE.md invariant 10, "recovery is recomputation"). `reasonOf`
// renders the wire's own words: `gate_verdict` when the gate named one
// (CLAUDE.md Phase 5 ledger, "the workspace cannot show the cause" — now it
// can), else the typed edges this node is waiting on.
import type { AttemptView } from "./types";
import type { NodeView } from "@/wire/v1";

/** Every direct edge this node names, as `TYPE source`. */
function edgesOf(node: Pick<NodeView, "waiting_on">): string {
  return node.waiting_on.map((edge) => `${edge.type} ${edge.source}`).join(" · ");
}

/** The cause the wire carries for this node's state: the gate's own verdict
    when the gate named one, else the typed edges it names. Never invented. */
export function reasonOf(
  node: Pick<NodeView, "state" | "waiting_on" | "gate_verdict" | "awaiting_gate">,
): string {
  const edges = edgesOf(node);
  if (node.gate_verdict) return edges ? `${node.gate_verdict} · ${edges}` : node.gate_verdict;
  if (node.state === "BLOCKED") return edges ? `waits on ${edges}` : "blocked with no named edge";
  if (node.state === "RUNNABLE") {
    if (node.awaiting_gate) return edges ? `awaiting the gate · ${edges}` : "awaiting the gate";
    return edges ? `in the frontier · ${edges}` : "in the frontier";
  }
  if (node.state === "COMPLETE") return edges ? `accepted · ${edges}` : "accepted";
  return edges || "restricted";
}

/** A node is drawn running while it holds an attempt not yet accepted —
    recomputed from the attempts the wire carries, never a stored flag. */
export function runningOf(
  node: Pick<NodeView, "route_node_id" | "state">,
  attempts: readonly AttemptView[],
): boolean {
  return (
    node.state === "RUNNABLE" &&
    attempts.some((attempt) => attempt.route_node_id === node.route_node_id && !attempt.accepted)
  );
}
