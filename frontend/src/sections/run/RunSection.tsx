// Run — the resolved route and its frontier (IA_SPEC.md 4.5). Centre: the DAG
// (tab "route") or the plan gate above it (tab "plan"). Right: the selected node.
// Compilation, acceptance and plan approval live only here.
import { useState } from "react";
import { NodeDetail } from "./NodeDetail";
import { PlanGate } from "./PlanGate";
import { RouteGraph } from "./RouteGraph";
import type { ViewProps } from "@/app/views";
import type { NodeState } from "@/wire";

interface Choice {
  run: string;
  module_id: string;
}

const STATES: NodeState[] = ["COMPLETE", "RUNNABLE", "RESTRICTED", "BLOCKED"];

export function RunSection({ document, tab }: ViewProps<"run">) {
  const body = document.body;
  const view = tab ?? document.chrome.tabs[0]?.id ?? "route";
  const [choice, setChoice] = useState<Choice | null>(null);
  // The reader's choice survives a stream refetch of the same run; it is
  // dropped for another run and falls back to the document's own selection.
  const chosen = choice?.run === body.run_id ? choice.module_id : null;
  const selectedId =
    (chosen && body.nodes.some((node) => node.module_id === chosen) ? chosen : null) ??
    body.selected ??
    body.nodes[0]?.module_id ??
    null;
  const selected = body.nodes.find((node) => node.module_id === selectedId) ?? null;
  const pinned = body.gate.state === "PINNED";
  const tally = STATES.map(
    (state) => `${body.nodes.filter((node) => node.state === state).length} ${state}`,
  ).join(" · ");

  return (
    <div className="cols two" data-run={body.run_id}>
      <div className="col">
        {view === "plan" ? (
          <PlanGate
            gate={body.gate}
            runId={body.run_id}
            nodeCount={body.nodes.length}
            edgeCount={body.edges.length}
          />
        ) : null}
        <section className="pnl">
          <header>
            <h2>
              {pinned
                ? "Resolved route — pinned at the plan gate"
                : "Resolved route — preview, not yet pinned"}
            </h2>
            <span className="cp">
              {body.profile} · build {body.build_id}
            </span>
            <span className="tag right">
              {body.nodes.length} NODES · {body.edges.length} EDGES
            </span>
            <span className="tag acc">{tally}</span>
          </header>
          <div className="pb flush">
            <RouteGraph
              nodes={body.nodes}
              edges={body.edges}
              stages={body.stages}
              selected={selectedId}
              onSelect={(module_id) => setChoice({ run: body.run_id, module_id })}
            />
          </div>
        </section>
        <div className="note">
          <b>States are the bundle&apos;s, recomputed from accepted attempts — never stored.</b>{" "}
          COMPLETE has an accepted artifact. RUNNABLE has every blocking edge satisfied and is in
          the frontier. RESTRICTED runs and carries its limitation forward. BLOCKED names the edge
          and the upstream it waits on. Recovery is recomputation: kill the process and the frontier
          is the same.
        </div>
      </div>
      <div className="col right">
        {selected ? (
          <NodeDetail
            node={selected}
            edges={body.edges}
            attempts={body.attempts[selected.module_id] ?? []}
            stages={body.stages}
          />
        ) : null}
        <section className="pnl">
          <header>
            <h2>Run</h2>
            <span className="cp">{body.run_id}</span>
          </header>
          <div className="pb">
            <dl className="kv">
              <dt>Route digest</dt>
              <dd className="wrap">{body.gate.route_digest}</dd>
              <dt>Build</dt>
              <dd>{body.build_id}</dd>
              <dt>Profile</dt>
              <dd>{body.profile}</dd>
              <dt>Plan</dt>
              <dd>{pinned ? "PINNED" : "RESOLVED · NOT PINNED"}</dd>
              <dt>Reserved</dt>
              <dd>{body.gate.reserved ?? "nothing reserved"}</dd>
            </dl>
          </div>
        </section>
      </div>
    </div>
  );
}
