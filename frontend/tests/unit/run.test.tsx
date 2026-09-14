import { readFileSync } from "node:fs";
import { fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { RunSection } from "@/sections/run/RunSection";
import { COL_GAP, NODE_H, NODE_W, ROW_H, edgesOf, layoutRoute } from "@/sections/run/RouteGraph";
import { parseRunSectionDocument } from "@/wire/v1";
import type { NodeState } from "@/wire";
import type { RunSectionDocument } from "@/wire/v1";

const load = (path: string): unknown =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));

const running = parseRunSectionDocument(load("../../fixtures/run.json"));
const routeNotPinned = parseRunSectionDocument(load("../../fixtures/states/run.gate.json"));
const superseded = parseRunSectionDocument(load("../../fixtures/states/run.superseded.json"));
const frames = [1, 2, 3, 4].map((n) =>
  parseRunSectionDocument(load(`../../fixtures/run/frames/${n}.json`)),
);

function mount(document: RunSectionDocument) {
  return render(
    <MemoryRouter>
      <RunSection document={document} tab={null} />
    </MemoryRouter>,
  );
}

const BUNDLE: NodeState[] = ["COMPLETE", "RUNNABLE", "RESTRICTED", "BLOCKED"];

describe("Run", () => {
  test("test_node_states_are_the_bundles_four_with_reasons", () => {
    const { container } = mount(running);
    const nodes = container.querySelectorAll<HTMLButtonElement>("button.node[data-route-node]");
    expect(nodes.length).toBe(running.body.run!.nodes.length);
    const seen = new Set<string>();
    for (const node of nodes) {
      const state = node.dataset["state"] as NodeState;
      expect(BUNDLE).toContain(state);
      seen.add(state);
      expect(node.className).toContain(state.toLowerCase());
      expect(node.querySelector(".st")?.textContent).toContain(state);
      expect(node.querySelector(".why")?.textContent?.trim().length).toBeGreaterThan(0);
      expect(node.querySelector(".glyph[data-severity]")).not.toBeNull();
    }
    expect([...seen].sort()).toEqual([...BUNDLE].sort());
    const cp6 = container.querySelector('button.node[data-node="CP-6"]');
    expect(cp6).toHaveAttribute("data-state", "RUNNABLE");
    expect(cp6?.querySelector(".glyph")).toHaveAttribute("data-severity", "RUNNING");
    // Every BLOCKED reason names the upstream and the edge type.
    for (const blocked of container.querySelectorAll('button.node[data-state="BLOCKED"]')) {
      const why = blocked.querySelector(".why")?.textContent ?? "";
      expect(why).toMatch(/REQUIRED|OPTIONAL|ADVISORY|QA_GATE|CONDITIONAL/);
    }
    const restricted = container.querySelector('button.node[data-state="RESTRICTED"]');
    expect(restricted?.querySelector(".glyph")).toHaveAttribute("data-severity", "WARNING");
    expect(container.querySelector(".dag[data-route]")).not.toBeNull();
    expect(container.querySelector(".legend")).not.toBeNull();
  });

  test("test_gate_verdict_is_shown_as_the_cause", () => {
    const { container } = mount(running);
    const restricted = container.querySelector('button.node[data-node="CP-1C"]')!;
    expect(restricted.querySelector(".why")?.textContent).toContain("READY_WITH_LIMITATIONS");
    fireEvent.click(restricted);
    const detail = container.querySelector('[data-node-detail="CP-1C"]')!;
    expect(detail.querySelector("[data-gate-verdict]")).toHaveTextContent("READY_WITH_LIMITATIONS");
  });

  test("test_the_one_qa_gate_reads_as_a_gate", () => {
    const { container } = mount(running);
    const gates = container.querySelectorAll("[data-gate]");
    expect(gates.length).toBe(1);
    const mark = gates[0]!;
    expect(mark).toHaveTextContent("QA_GATE");
    expect(mark.querySelector(".gatebox")).not.toBeNull();
    expect(mark.getAttribute("data-gate")).toBe("CP-5 → CP-6");
    expect(container.querySelectorAll("svg.edges line.gate").length).toBe(1);
    expect(container.querySelectorAll("svg.edges line.req").length).toBeGreaterThan(0);
    expect(container.querySelectorAll("svg.edges line.cond").length).toBe(1);
  });

  test("test_layout_places_nodes_by_stage_without_overlap", () => {
    const nodes = running.body.run!.nodes;
    const layout = layoutRoute(nodes);
    expect(layout.columns.map((c) => c.stage)).toEqual([0, 1, 2, 3, 4, 5, 100]);
    const byId = new Map(layout.nodes.map((n) => [n.route_node_id, n]));
    for (const node of nodes) {
      const placed = byId.get(node.route_node_id)!;
      expect(placed.col).toBe(layout.columns.findIndex((c) => c.stage === node.stage));
      expect(placed.x).toBe(layout.columns[placed.col]!.x);
      expect(placed.y).toBe(30 + placed.row * ROW_H);
    }
    const slots = new Set(layout.nodes.map((n) => `${n.x},${n.y}`));
    expect(slots.size).toBe(layout.nodes.length);
    const xs = layout.columns.map((c) => c.x);
    for (let i = 1; i < xs.length; i += 1) expect(xs[i]! - xs[i - 1]!).toBe(NODE_W + COL_GAP);
    expect(ROW_H).toBeGreaterThan(NODE_H);
    for (const placed of layout.nodes) {
      expect(placed.x + NODE_W).toBeLessThanOrEqual(layout.width);
      expect(placed.y + NODE_H).toBeLessThanOrEqual(layout.height);
    }
    expect(layoutRoute([])).toEqual({ nodes: [], columns: [], width: 28, height: 40 });
  });

  test("test_edges_are_derived_from_each_node_s_waiting_on_not_a_separate_list", () => {
    const nodes = running.body.run!.nodes;
    const edges = edgesOf(nodes);
    expect(edges.length).toBe(nodes.reduce((n, node) => n + node.waiting_on.length, 0));
    expect(edges.filter((edge) => edge.type === "QA_GATE").length).toBe(1);
    for (const edge of edges) {
      expect(nodes.some((node) => node.route_node_id === edge.to)).toBe(true);
    }
  });

  test("the selected node's edges, attempts and gate verdict are in the right column", () => {
    const { container } = mount(running);
    fireEvent.click(container.querySelector('button.node[data-node="CP-6"]')!);
    const detail = container.querySelector('[data-node-detail="CP-6"]')!;
    expect(detail).toHaveTextContent("QA_GATE rn-cp-5");
    const attempts = container.querySelectorAll(".att[data-attempt]");
    expect(attempts.length).toBe(2);
    expect(attempts[0]).toHaveTextContent("attempt 1");
    expect(attempts[0]).toHaveTextContent("NOT ACCEPTED");
    expect(attempts[1]).toHaveTextContent("attempt unassigned");
  });

  test("test_displayed_run_is_labelled_separately_from_latest", () => {
    const { container } = mount(superseded);
    const row = container.querySelector(`[data-run-row="${superseded.body.displayed_run_id}"]`)!;
    expect(row).toHaveAttribute("data-displayed", "true");
    expect(row).toHaveAttribute("data-latest", "false");
    const latestRow = container.querySelector(`[data-run-row="${superseded.body.latest_run_id}"]`)!;
    expect(latestRow).toHaveAttribute("data-displayed", "false");
    expect(latestRow).toHaveAttribute("data-latest", "true");
    const stale = container.querySelector("[data-stale-run]");
    expect(stale).not.toBeNull();
    expect(stale).toHaveTextContent(superseded.body.displayed_run_id!);
    expect(stale).toHaveTextContent(superseded.body.latest_run_id!);
  });

  test("test_route_not_pinned_is_rendered_as_a_preview", () => {
    expect(routeNotPinned.status).toBe("partial");
    expect(routeNotPinned.notes).toContain("ROUTE_NOT_PINNED");
    const { container } = mount(routeNotPinned);
    expect(container.querySelector("[data-route-not-pinned]")).not.toBeNull();
    expect(container.querySelectorAll("button.node").length).toBe(0);
    expect(container.querySelector(".dag[data-route]")).toHaveAttribute(
      "data-route",
      "0 nodes · 0 edges",
    );
  });

  test("test_run_null_renders_the_defensive_empty_state_rather_than_crashing", () => {
    const empty: RunSectionDocument = {
      ...routeNotPinned,
      body: {
        case_id: routeNotPinned.body.case_id,
        latest_run_id: null,
        displayed_run_id: null,
        runs: [],
        run: null,
        route_choices: [],
      },
      observed_empty: true,
    };
    const { container } = mount(empty);
    expect(container.querySelector("[data-run-empty]")).not.toBeNull();
  });

  test("the stream's frames advance CP-6 to COMPLETE and CP-7 to RUNNABLE", () => {
    const { container, rerender } = mount(frames[0]!);
    expect(container.querySelector('button.node[data-node="CP-6"]')).toHaveAttribute(
      "data-state",
      "RUNNABLE",
    );
    rerender(
      <MemoryRouter>
        <RunSection document={frames[2]!} tab={null} />
      </MemoryRouter>,
    );
    expect(container.querySelector('button.node[data-node="CP-6"]')).toHaveAttribute(
      "data-state",
      "COMPLETE",
    );
    expect(container.querySelector('button.node[data-node="CP-7"]')).toHaveAttribute(
      "data-state",
      "RUNNABLE",
    );
  });

  test("test_every_enabled_demo_fixture_is_a_valid_v1_document", () => {
    const fixtures = [
      "../../fixtures/run.json",
      "../../fixtures/states/run.gate.json",
      "../../fixtures/states/run.superseded.json",
      "../../fixtures/run/frames/1.json",
      "../../fixtures/run/frames/2.json",
      "../../fixtures/run/frames/3.json",
      "../../fixtures/run/frames/4.json",
    ];
    for (const path of fixtures) {
      expect(() => parseRunSectionDocument(load(path))).not.toThrow();
    }
  });
});
