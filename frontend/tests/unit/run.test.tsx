import { readFileSync } from "node:fs";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { RunSection } from "@/sections/run/RunSection";
import { COL_GAP, NODE_H, NODE_W, ROW_H, layoutRoute } from "@/sections/run/RouteGraph";
import type { DocumentOf, NodeState } from "@/wire";

const load = (path: string): DocumentOf<"run"> =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const running = load("../../fixtures/run.json");
const gate = load("../../fixtures/states/run.gate.json");
const frames = [1, 2, 3, 4].map((n) => load(`../../fixtures/run/frames/${n}.json`));

function mount(document: DocumentOf<"run">, tab: string | null = null) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <RunSection document={document} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

const BUNDLE: NodeState[] = ["COMPLETE", "RUNNABLE", "RESTRICTED", "BLOCKED"];

describe("Run", () => {
  test("test_node_states_are_the_bundles_four_with_reasons", () => {
    const { container } = mount(running);
    const nodes = container.querySelectorAll<HTMLButtonElement>("button.node[data-node]");
    expect(nodes.length).toBe(32);
    const seen = new Set<string>();
    for (const node of nodes) {
      const state = node.dataset["state"] as NodeState;
      expect(BUNDLE).toContain(state);
      seen.add(state);
      expect(node.className).toContain(state.toLowerCase());
      // The state word and the reason are on the node itself.
      expect(node.querySelector(".st")?.textContent).toContain(state);
      expect(node.querySelector(".why")?.textContent?.trim().length).toBeGreaterThan(0);
      expect(node.querySelector(".glyph[data-severity]")).not.toBeNull();
    }
    expect([...seen].sort()).toEqual([...BUNDLE].sort());
    const cp6 = container.querySelector('button.node[data-node="CP-6"]');
    expect(cp6).toHaveAttribute("data-state", "RUNNABLE");
    expect(cp6).toHaveAttribute("aria-pressed", "true");
    expect(cp6?.querySelector(".glyph")).toHaveAttribute("data-severity", "RUNNING");
    // Every BLOCKED reason names the upstream and the edge type.
    for (const blocked of container.querySelectorAll('button.node[data-state="BLOCKED"]')) {
      const why = blocked.querySelector(".why")?.textContent ?? "";
      expect(why).toMatch(/REQUIRED|OPTIONAL|ADVISORY|QA_GATE|CONDITIONAL/);
      expect(why).toMatch(/CP-6/);
    }
    const restricted = container.querySelector('button.node[data-state="RESTRICTED"]');
    expect(restricted?.querySelector(".glyph")).toHaveAttribute("data-severity", "WARNING");
    expect(container.querySelector(".dag[data-route]")).not.toBeNull();
    expect(container.querySelector(".legend")).not.toBeNull();
  });

  test("test_the_one_qa_gate_reads_as_a_gate", () => {
    const { container } = mount(running);
    const gates = container.querySelectorAll("[data-gate]");
    expect(gates.length).toBe(1);
    const mark = gates[0]!;
    expect(mark).toHaveTextContent("QA_GATE");
    expect(mark.querySelector(".gatebox")).not.toBeNull();
    expect(mark.querySelector(".gatelbl")).toHaveTextContent("QA_GATE");
    expect(mark.getAttribute("data-gate")).toBe("CP-5 → CP-6");
    expect(container.querySelectorAll("svg.edges line.gate").length).toBe(1);
    expect(container.querySelectorAll("svg.edges line.req").length).toBeGreaterThan(30);
    expect(container.querySelectorAll("svg.edges line.opt").length).toBeGreaterThan(0);
    expect(container.querySelectorAll("svg.edges line.adv").length).toBeGreaterThan(0);
  });

  test("test_layout_places_nodes_by_stage_without_overlap", () => {
    const layout = layoutRoute(running.body.nodes);
    expect(layout.columns.map((c) => c.stage)).toEqual([0, 1, 2, 3, 4, 5, 100]);
    const byId = new Map(layout.nodes.map((n) => [n.module_id, n]));
    for (const node of running.body.nodes) {
      const placed = byId.get(node.module_id)!;
      expect(placed.col).toBe(layout.columns.findIndex((c) => c.stage === node.stage));
      expect(placed.x).toBe(layout.columns[placed.col]!.x);
      expect(placed.y).toBe(30 + placed.row * ROW_H);
    }
    // No two nodes share a slot; columns are NODE_W + COL_GAP apart.
    const slots = new Set(layout.nodes.map((n) => `${n.x},${n.y}`));
    expect(slots.size).toBe(layout.nodes.length);
    const xs = layout.columns.map((c) => c.x);
    for (let i = 1; i < xs.length; i += 1) expect(xs[i]! - xs[i - 1]!).toBe(NODE_W + COL_GAP);
    expect(ROW_H).toBeGreaterThan(NODE_H);
    // The box fits every node.
    for (const placed of layout.nodes) {
      expect(placed.x + NODE_W).toBeLessThanOrEqual(layout.width);
      expect(placed.y + NODE_H).toBeLessThanOrEqual(layout.height);
    }
    expect(layoutRoute([])).toEqual({ nodes: [], columns: [], width: 28, height: 40 });
  });

  test("test_accept_is_visible_and_refused_while_not_terminal", () => {
    const { container } = mount(running);
    const accept = screen.getByRole("button", { name: "Accept" });
    expect(accept).toBeVisible();
    expect(accept).toHaveAttribute("aria-disabled", "true");
    expect(accept).toHaveAttribute("data-refusal", "NODE_NOT_ACCEPTABLE");
    expect(accept).not.toHaveAttribute("disabled");
    expect(container).toHaveTextContent(/NODE_NOT_ACCEPTABLE — clears when/);
    // The run-level refusal is the chrome's; the body carries it typed.
    expect(running.body.accept).toEqual(expect.objectContaining({ code: "RUN_NOT_TERMINAL" }));
    expect(running.chrome.ribbon.actions.find((a) => a.primary)?.refusal?.code).toBe(
      "RUN_NOT_TERMINAL",
    );
    // A COMPLETE node is acceptable, and nothing in this build accepts: the
    // control stays visible and refused with what clears it.
    fireEvent.click(container.querySelector('button.node[data-node="CP-1"]')!);
    const acceptable = screen.getByRole("button", { name: "Accept" });
    expect(acceptable).toHaveAttribute("data-refusal", "ACTION_UNPLACED");
    expect(acceptable).not.toHaveAttribute("disabled");
  });

  test("an attempt with no generation id says so rather than inventing one", () => {
    const { container } = mount(running);
    expect(running.body.attempts["CP-6"]?.[0]?.generation_id).toBeNull();
    const attempt = container.querySelector(".att[data-attempt='1']");
    expect(attempt).toHaveTextContent("no generation id");
    expect(attempt).not.toHaveTextContent("gen_—");
  });

  test("the selected node's attempts, digest and limitation are in the right column", () => {
    const { container } = mount(running);
    const detail = container.querySelector('[data-node-detail="CP-6"]')!;
    expect(detail).toHaveTextContent("QA_GATE CP-5");
    const attempts = container.querySelectorAll(".att[data-attempt]");
    expect(attempts.length).toBe(1);
    expect(attempts[0]).toHaveTextContent("attempt 1");
    expect(attempts[0]).toHaveTextContent("INDETERMINATE");
    fireEvent.click(container.querySelector('button.node[data-node="CP-1C"]')!);
    expect(container.querySelector("[data-limitation]")).toHaveTextContent("Peer set limited");
    expect(container.querySelector('[data-node-detail="CP-1C"]')).toHaveTextContent("sha256:");
  });

  test("the stream's frames advance CP-6 to COMPLETE and CP-7 to RUNNABLE", () => {
    const { container, rerender } = mount(frames[0]!);
    expect(container.querySelector('button.node[data-node="CP-6"]')).toHaveAttribute(
      "data-state",
      "RUNNABLE",
    );
    expect(container.querySelectorAll(".att[data-attempt]").length).toBe(2);
    rerender(
      <MemoryRouter>
        <EvidenceProvider>
          <RunSection document={frames[2]!} tab={null} />
        </EvidenceProvider>
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
    expect(frames[3]!.chrome.ribbon.execution).toBe("IDLE");
    expect(screen.getByRole("button", { name: "Accept" })).toHaveAttribute(
      "data-refusal",
      "ACTION_UNPLACED",
    );
  });

  test("the plan gate is live at RESOLVED_NOT_PINNED and refused once pinned", () => {
    const { container, unmount } = mount(gate);
    const panel = container.querySelector("[data-plan-gate]")!;
    expect(panel).toHaveAttribute("data-gate-state", "RESOLVED_NOT_PINNED");
    expect(panel).toHaveTextContent("RESOLVED · NOT PINNED");
    expect(panel).toHaveTextContent("nothing reserved");
    expect(panel).toHaveTextContent(gate.body.gate.route_digest);
    expect(panel).toHaveTextContent(gate.body.gate.input_fingerprint);
    // Approval is the gate's to give and this build has no gate to give it:
    // visible, refused, the clearing phase named — never a live no-op.
    const approve = within(panel as HTMLElement).getByRole("button", { name: "Approve plan" });
    expect(approve).toHaveAttribute("data-refusal", "ACTION_UNPLACED");
    expect(approve).not.toHaveAttribute("disabled");
    expect(gate.chrome.tabs[0]?.label).toBe("Plan");
    expect(gate.chrome.verdict.blocked_on).toBe("plan approval");
    unmount();
    const pinned = mount(running, "plan");
    const refused = within(
      pinned.container.querySelector("[data-plan-gate]") as HTMLElement,
    ).getByRole("button", { name: "Approve plan" });
    expect(refused).toHaveAttribute("data-refusal", "PLAN_ALREADY_PINNED");
    expect(pinned.container.querySelector("[data-gate-state]")).toHaveAttribute(
      "data-gate-state",
      "PINNED",
    );
  });
});
