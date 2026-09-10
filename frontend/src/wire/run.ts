import type { EdgeType, NodeState, Refusal } from "./shared";

export interface RouteNode {
  node_id: string;
  module_id: string;
  name: string;
  stage: number;
  state: NodeState;
  running: boolean;
  /** Which upstream, which edge type, which gate. Always named. */
  reason: string;
  is_gate: boolean;
  extension: boolean;
  artifact_sha256: string | null;
  limitation: string | null;
}
export interface RouteEdge {
  from: string;
  to: string;
  type: EdgeType;
}
export interface Stage {
  n: number;
  label: string;
}
export interface Attempt {
  n: number;
  started_at: string;
  state: "ACCEPTED" | "INDETERMINATE" | "REFUSED";
  charge: string | null;
  generation_id: string | null;
}
export interface PlanGate {
  state: "RESOLVED_NOT_PINNED" | "PINNED";
  route_digest: string;
  input_fingerprint: string;
  approve: Refusal | null;
  reserved: string | null;
}
export interface RunBody {
  run_id: string;
  build_id: string;
  profile: string;
  stages: Stage[];
  nodes: RouteNode[];
  edges: RouteEdge[];
  selected: string | null;
  attempts: Record<string, Attempt[]>;
  gate: PlanGate;
  accept: Refusal | null;
}
