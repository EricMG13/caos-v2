// `useCommand` and `useRunRefetch` (controls.tsx) are exercised end-to-end
// below: every click on a rendered control drives `useCommand`'s intent
// lifecycle, and every command's success drives `useRunRefetch`'s
// GET-after-success — neither is imported directly, since a hook is reached
// by the component that calls it, not by its own name. `actionOf` is
// imported directly below and given its own small, direct test.
import { readFileSync } from "node:fs";
import { fireEvent, render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { actionOf } from "@/sections/run/controls";
import { RunSection } from "@/sections/run/RunSection";
import { COL_GAP, NODE_H, NODE_W, ROW_H, edgesOf, layoutRoute } from "@/sections/run/RouteGraph";
import { parseRunSectionDocument } from "@/wire/v1";
import type { NodeState } from "@/wire";
import type { RunSectionDocument } from "@/wire/v1";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

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

/** A document with exactly these served actions, everything else unchanged —
    every action absent from the list is `ACTION_UNPLACED`. */
function withActions(
  document: RunSectionDocument,
  actions: RunSectionDocument["chrome"]["actions"],
): RunSectionDocument {
  return { ...document, chrome: { ...document.chrome, actions } };
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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

  test("test_a_refused_action_renders_its_code_and_clearance_and_is_not_hidden", () => {
    const doc = withActions(running, [
      {
        action: "PIN_RUN_INPUT",
        refusal: { code: "RUN_NOT_RUNNING", clears: "the run is RUNNING" },
      },
    ]);
    const { container } = mount(doc);
    const pin = container.querySelector('[data-action="PIN_RUN_INPUT"]')!;
    expect(pin).not.toBeNull();
    expect(pin).toHaveAttribute("aria-disabled", "true");
    expect(pin).toHaveAttribute("data-refusal", "RUN_NOT_RUNNING");
    const reason = pin.nextElementSibling;
    expect(reason).toHaveTextContent("RUN_NOT_RUNNING");
    expect(reason).toHaveTextContent("clears when the run is RUNNING");
  });

  test("test_an_action_absent_from_served_actions_is_action_unplaced_not_available", () => {
    // A served `refusal: null` and an entry missing entirely both look
    // "not refused" if coerced together; they must not be. Absent here means
    // unavailable, shown the same visible way as any other refusal.
    const doc = withActions(running, []);
    const { container } = mount(doc);
    const pin = container.querySelector('[data-action="PIN_RUN_INPUT"]')!;
    expect(pin).toHaveAttribute("aria-disabled", "true");
    expect(pin).toHaveAttribute("data-refusal", "ACTION_UNPLACED");
  });

  test("test_no_run_offers_a_create_run_control_from_route_choices", () => {
    const empty: RunSectionDocument = withActions(
      {
        ...routeNotPinned,
        body: {
          case_id: routeNotPinned.body.case_id,
          latest_run_id: null,
          displayed_run_id: null,
          runs: [],
          run: null,
          route_choices: [{ profile_id: "FULL_CREDIT_ASSESSMENT", selection_id: "default" }],
        },
      },
      [{ action: "CREATE_RUN", refusal: null }],
    );
    const { container } = mount(empty);
    expect(container.querySelector("[data-run-empty]")).not.toBeNull();
    expect(container.querySelector("[data-create-run]")).not.toBeNull();
    const select = container.querySelector("[data-route-select]") as HTMLSelectElement;
    expect(select.options.length).toBe(1);
    const button = container.querySelector('[data-action="CREATE_RUN"]')!;
    expect(button).not.toHaveAttribute("aria-disabled");
  });

  test("test_pinning_a_subject_sends_the_run_subject_view_shows_success_then_refetches", async () => {
    const run = running.body.run!;
    const caseId = running.body.case_id;
    const receipt = {
      run_id: run.run_id,
      source_set_version: run.source_set_version,
      input_fingerprint: "c".repeat(64),
    };
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(receipt))
      .mockResolvedValueOnce(jsonResponse(running));
    vi.stubGlobal("fetch", fetchSpy);
    try {
      const doc = withActions(running, [{ action: "PIN_RUN_INPUT", refusal: null }]);
      const { container } = mount(doc);
      const issuerId = container.querySelector('[data-field="issuer_id"]') as HTMLInputElement;
      expect(issuerId.value).toBe(run.subject!.issuer_id);
      fireEvent.click(container.querySelector('[data-action="PIN_RUN_INPUT"]')!);

      await waitFor(() => {
        const note = container.querySelector("[data-command-success]");
        expect(note).not.toBeNull();
      });
      const [, init] = fetchSpy.mock.calls[0]!;
      expect(JSON.parse((init as RequestInit).body as string)).toEqual({ subject: run.subject });
      expect(
        UUID.test(
          ((init as RequestInit).headers as Record<string, string>)["Idempotency-Key"] ?? "",
        ),
      ).toBe(true);

      // One refetch, through the same transport and parser every load uses.
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
      const [refetchUrl] = fetchSpy.mock.calls[1]!;
      expect(refetchUrl).toBe(`/api/v1/cases/${caseId}/run?run=${run.run_id}`);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test("test_the_idempotency_key_is_reused_for_a_retry_of_the_same_body", async () => {
    const fetchSpy = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(
        jsonResponse({
          run_id: running.body.run!.run_id,
          source_set_version: running.body.run!.source_set_version,
          input_fingerprint: "d".repeat(64),
        }),
      )
      // The pin's own success also triggers one refetch (finding 2); a
      // benign fallback answers it so this test, which is about the key
      // alone, need not assert anything about that second read.
      .mockResolvedValue(jsonResponse(running));
    vi.stubGlobal("fetch", fetchSpy);
    try {
      const doc = withActions(running, [{ action: "PIN_RUN_INPUT", refusal: null }]);
      const { container } = mount(doc);
      const pinButton = container.querySelector('[data-action="PIN_RUN_INPUT"]')!;
      fireEvent.click(pinButton); // offline
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
      fireEvent.click(pinButton); // retry of the identical, unedited subject
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
      const key1 = (fetchSpy.mock.calls[0]![1] as RequestInit).headers as Record<string, string>;
      const key2 = (fetchSpy.mock.calls[1]![1] as RequestInit).headers as Record<string, string>;
      expect(key2["Idempotency-Key"]).toBe(key1["Idempotency-Key"]);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test("test_the_idempotency_key_is_replaced_when_the_body_changes_even_after_an_offline_answer", async () => {
    const fetchSpy = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchSpy);
    try {
      const doc = withActions(running, [{ action: "PIN_RUN_INPUT", refusal: null }]);
      const { container } = mount(doc);
      const pinButton = container.querySelector('[data-action="PIN_RUN_INPUT"]')!;
      fireEvent.click(pinButton);
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
      fireEvent.change(container.querySelector('[data-field="issuer_name"]')!, {
        target: { value: "A different name entirely" },
      });
      fireEvent.click(pinButton);
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
      const key1 = (fetchSpy.mock.calls[0]![1] as { headers: Record<string, string> }).headers[
        "Idempotency-Key"
      ];
      const key2 = (fetchSpy.mock.calls[1]![1] as { headers: Record<string, string> }).headers[
        "Idempotency-Key"
      ];
      expect(key2).not.toBe(key1);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test("test_create_run_shows_a_success_note_and_refetches_so_a_second_click_is_never_a_silent_duplicate", async () => {
    const caseId = routeNotPinned.body.case_id;
    const newRunId = "11111111-1111-4111-8111-111111111111";
    const created = { case_id: caseId, run_id: newRunId, route_digest: "f".repeat(64) };
    const refreshed: RunSectionDocument = {
      ...routeNotPinned,
      chrome: { ...routeNotPinned.chrome, actions: [] },
      body: {
        case_id: caseId,
        latest_run_id: newRunId,
        displayed_run_id: newRunId,
        runs: [
          {
            run_id: newRunId,
            status: "RUNNING",
            created_at: "2026-09-14T10:00:00Z",
            profile_id: "FULL_CREDIT_ASSESSMENT",
            selection_id: "default",
          },
        ],
        run: { ...routeNotPinned.body.run!, run_id: newRunId },
        route_choices: [],
      },
    };
    // The refetch is held open deliberately: real network latency separates
    // the command's own answer from the read that follows it, and asserting
    // the transient success note is only deterministic if this test controls
    // that gap itself rather than racing the mock's own resolution.
    let resolveRefetch!: (response: Response) => void;
    const refetchResponse = new Promise<Response>((resolve) => {
      resolveRefetch = resolve;
    });
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(created, 201))
      .mockImplementationOnce(() => refetchResponse);
    vi.stubGlobal("fetch", fetchSpy);
    try {
      const empty: RunSectionDocument = withActions(
        {
          ...routeNotPinned,
          body: {
            case_id: caseId,
            latest_run_id: null,
            displayed_run_id: null,
            runs: [],
            run: null,
            route_choices: [{ profile_id: "FULL_CREDIT_ASSESSMENT", selection_id: "default" }],
          },
        },
        [{ action: "CREATE_RUN", refusal: null }],
      );
      const { container } = mount(empty);
      fireEvent.click(container.querySelector('[data-action="CREATE_RUN"]')!);

      // The success note is transient — the refetch it also triggers may
      // replace this whole branch as soon as it lands — so both checks are
      // made together, not across a second `await`.
      await waitFor(() => {
        const note = container.querySelector("[data-command-success]");
        expect(note).not.toBeNull();
        expect(note).toHaveTextContent("Run created");
      });

      const [createUrl, createInit] = fetchSpy.mock.calls[0]!;
      expect(createUrl).toBe(`/api/v1/cases/${caseId}/runs`);
      expect((createInit as RequestInit).method).toBe("POST");
      expect(JSON.parse((createInit as RequestInit).body as string)).toEqual({
        profile_id: "FULL_CREDIT_ASSESSMENT",
        selection_id: "default",
      });
      expect(
        UUID.test(
          ((createInit as RequestInit).headers as Record<string, string>)["Idempotency-Key"] ?? "",
        ),
      ).toBe(true);

      // One refetch, by the id the server just handed back — the analyst
      // never has to guess whether the click landed.
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
      const [refetchUrl] = fetchSpy.mock.calls[1]!;
      expect(refetchUrl).toBe(`/api/v1/cases/${caseId}/run?run=${newRunId}`);

      resolveRefetch(jsonResponse(refreshed));
      await waitFor(() => expect(container.querySelector("[data-run-empty]")).toBeNull());
      expect(container.querySelector(`[data-run="${newRunId}"]`)).not.toBeNull();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test("test_action_of_finds_the_one_entry_for_a_served_action_by_name", () => {
    const actions = [
      { action: "PIN_RUN_INPUT" as const, refusal: null },
      {
        action: "CREATE_RUN" as const,
        refusal: { code: "NOT_AUTHORISED" as const, clears: "the caller holds WRITER standing" },
      },
    ];
    expect(actionOf(actions, "PIN_RUN_INPUT")).toEqual(actions[0]);
    expect(actionOf(actions, "CREATE_RUN")).toEqual(actions[1]);
    expect(actionOf(actions, "CANCEL_RUN")).toBeUndefined();
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
