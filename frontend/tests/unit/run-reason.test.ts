// The Run section's node reasons, recomputed from v1 wire fields (slice 4.1i).
import { reasonOf, runningOf } from "@/sections/run/reason";
describe("the reasons a node draws", () => {
  test("reasonOf names the gate's verdict first, then the typed edges; runningOf needs an unaccepted attempt", () => {
    const waiting = [{ source: "CP-L10", type: "ADVISORY" as const }];
    expect(
      reasonOf({ state: "BLOCKED", waiting_on: waiting, gate_verdict: null, awaiting_gate: false }),
    ).toBe("waits on ADVISORY CP-L10");
    expect(
      reasonOf({
        state: "BLOCKED",
        waiting_on: [],
        gate_verdict: "NOT_READY",
        awaiting_gate: false,
      }),
    ).toBe("NOT_READY");
    const node = { route_node_id: "N1", state: "RUNNABLE" as const };
    const attempt = {
      attempt_id: "a",
      route_node_id: "N1",
      ordinal: 1,
      started_at: "2026-09-14T10:00:00Z",
    };
    expect(runningOf(node, [{ ...attempt, accepted: false }])).toBe(true);
    expect(runningOf(node, [{ ...attempt, accepted: true }])).toBe(false);
  });
});
