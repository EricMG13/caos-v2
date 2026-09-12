// The resolved route as a DAG: one column per stage, one row per node in the
// stage, typed edges as SVG lines, the one QA_GATE drawn through a diamond.
// Node states are the bundle's four, each with its reason under it.
import { RouteLegend } from "./RouteLegend";
import { SeverityMark } from "@/chrome/SeverityMark";
import type { RouteEdge, RouteNode, Stage } from "@/wire/run";
import type { EdgeType, NodeState, Severity } from "@/wire";

export const NODE_W = 128;
// Tall enough for the id, the name, the state and two whole lines of reason;
// at 62 the second reason line was cut through the middle. Both sizes are set
// on each node and stage header here, not in caos.css, so each is one number.
export const NODE_H = 76;
export const COL_GAP = 40;
export const ROW_H = NODE_H + 12;
const PAD_X = 14;
// Below a stage header clamped at two lines: 8px down, two 9.4px lines.
const TOP = 30;
const PAD_BOTTOM = 10;

export interface PlacedNode {
  module_id: string;
  stage: number;
  col: number;
  row: number;
  x: number;
  y: number;
}
export interface RouteLayout {
  nodes: PlacedNode[];
  columns: { stage: number; x: number }[];
  width: number;
  height: number;
}

/** Pure: columns by ascending stage, rows in the given order within a stage. */
export function layoutRoute(nodes: Pick<RouteNode, "module_id" | "stage">[]): RouteLayout {
  const stages = [...new Set(nodes.map((node) => node.stage))].sort((a, b) => a - b);
  const columns = stages.map((stage, col) => ({ stage, x: PAD_X + col * (NODE_W + COL_GAP) }));
  const rows = new Map<number, number>();
  const placed = nodes.map((node) => {
    const col = stages.indexOf(node.stage);
    const row = rows.get(node.stage) ?? 0;
    rows.set(node.stage, row + 1);
    return {
      module_id: node.module_id,
      stage: node.stage,
      col,
      row,
      x: PAD_X + col * (NODE_W + COL_GAP),
      y: TOP + row * ROW_H,
    };
  });
  const deepest = Math.max(0, ...rows.values());
  return {
    nodes: placed,
    columns,
    width: PAD_X * 2 + stages.length * NODE_W + Math.max(0, stages.length - 1) * COL_GAP,
    height: TOP + deepest * ROW_H + PAD_BOTTOM,
  };
}

const EDGE_CLASS: Record<EdgeType, string> = {
  REQUIRED: "req",
  OPTIONAL: "opt",
  ADVISORY: "adv",
  QA_GATE: "gate",
  CONDITIONAL: "cond",
};

export function severityOf(node: Pick<RouteNode, "state" | "running">): Severity {
  const by: Record<NodeState, Severity> = {
    COMPLETE: "SUCCESS",
    RUNNABLE: node.running ? "RUNNING" : "IDLE",
    RESTRICTED: "WARNING",
    BLOCKED: "CRITICAL",
  };
  return by[node.state];
}

function stateWord(node: RouteNode): string {
  if (node.state === "RUNNABLE") return node.running ? "RUNNABLE · RUNNING" : "RUNNABLE · FRONTIER";
  return node.state;
}

interface Segment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}
function segment(from: PlacedNode, to: PlacedNode): Segment {
  if (from.col === to.col) {
    const down = to.row > from.row;
    return {
      x1: from.x + NODE_W / 2,
      y1: down ? from.y + NODE_H : from.y,
      x2: to.x + NODE_W / 2,
      y2: down ? to.y : to.y + NODE_H,
    };
  }
  return { x1: from.x + NODE_W, y1: from.y + NODE_H / 2, x2: to.x, y2: to.y + NODE_H / 2 };
}

export function RouteGraph({
  nodes,
  edges,
  stages,
  selected,
  onSelect,
}: {
  nodes: RouteNode[];
  edges: RouteEdge[];
  stages: Stage[];
  selected: string | null;
  onSelect: (moduleId: string) => void;
}) {
  const layout = layoutRoute(nodes);
  const at = new Map(layout.nodes.map((placed) => [placed.module_id, placed]));
  const labelOf = new Map(stages.map((stage) => [stage.n, stage.label]));
  const lines: { key: string; cls: string; seg: Segment; gate: boolean }[] = [];
  let gate: { seg: Segment; from: string; to: string } | null = null;
  for (const edge of edges) {
    const from = at.get(edge.from);
    const to = at.get(edge.to);
    if (!from || !to) continue;
    const seg = segment(from, to);
    if (edge.type === "QA_GATE" && !gate) gate = { seg, from: edge.from, to: edge.to };
    lines.push({
      key: `${edge.from}→${edge.to}`,
      cls: EDGE_CLASS[edge.type],
      seg,
      gate: edge.type === "QA_GATE",
    });
  }
  const gateMid = gate
    ? { x: (gate.seg.x1 + gate.seg.x2) / 2, y: (gate.seg.y1 + gate.seg.y2) / 2 }
    : null;
  return (
    <>
      <div className="dag" data-route={`${nodes.length} nodes · ${edges.length} edges`}>
        <div className="dagbox" style={{ width: layout.width, height: layout.height }}>
          <svg
            className="edges"
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {lines.map(({ key, cls, seg }) => (
              <line key={key} className={cls} x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2} />
            ))}
          </svg>
          {layout.columns.map((column) => {
            // Two lines fit above the nodes; a longer name is clamped and whole in its title.
            const label = labelOf.get(column.stage) ?? `Stage ${column.stage}`;
            return (
              <span
                key={column.stage}
                className="stagehdr"
                style={{ left: column.x, width: NODE_W }}
                title={label}
              >
                {label}
              </span>
            );
          })}
          {nodes.map((node) => {
            const placed = at.get(node.module_id);
            if (!placed) return null;
            const on = node.module_id === selected;
            const cls = `node ${node.state.toLowerCase()}${node.running ? " running" : ""}${node.is_gate ? " gate" : ""}${on ? " sel" : ""}`;
            return (
              <button
                key={node.module_id}
                type="button"
                className={cls}
                data-node={node.module_id}
                data-state={node.state}
                aria-pressed={on}
                style={{ left: placed.x, top: placed.y, width: NODE_W, height: NODE_H }}
                onClick={() => onSelect(node.module_id)}
              >
                <span className="id">{node.module_id}</span>
                <span className="nm">{node.name}</span>
                <span className="st">
                  <SeverityMark severity={severityOf(node)} pulse={node.running} />
                  {stateWord(node)}
                </span>
                <span className="why">{node.reason}</span>
              </button>
            );
          })}
          {gate && gateMid ? (
            <div
              className="gatemark"
              data-gate={`${gate.from} → ${gate.to}`}
              style={{ left: gateMid.x, top: gateMid.y }}
            >
              <span className="gatebox" aria-hidden="true" />
              <span className="gatelbl">QA_GATE</span>
            </div>
          ) : null}
        </div>
      </div>
      <RouteLegend />
    </>
  );
}
