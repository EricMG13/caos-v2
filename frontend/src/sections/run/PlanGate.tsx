// The plan-approval interrupt (card 4b): the resolved route digest, the input
// fingerprint, whether it is pinned, what is reserved (nothing, before
// approval), and Approve plan — live only while the route is not yet pinned.
import { RefusedControl } from "@/controls/RefusedControl";
import type { PlanGate as PlanGateWire } from "@/wire/run";

const STATE_LABEL: Record<PlanGateWire["state"], string> = {
  RESOLVED_NOT_PINNED: "RESOLVED · NOT PINNED",
  PINNED: "PINNED",
};

export function PlanGate({
  gate,
  runId,
  nodeCount,
  edgeCount,
}: {
  gate: PlanGateWire;
  runId: string;
  nodeCount: number;
  edgeCount: number;
}) {
  const pinned = gate.state === "PINNED";
  return (
    <section className="pnl" data-plan-gate={runId} data-gate-state={gate.state}>
      <header>
        <h2>{pinned ? "Plan — approved and pinned" : "Approve the plan"}</h2>
        <span className="cp">digest-bound</span>
        <span className={`tag ${pinned ? "ok" : "warn"} right`}>{STATE_LABEL[gate.state]}</span>
      </header>
      <div className="pb">
        <dl className="kv">
          <dt>{pinned ? "Route digest" : "Binds preview digest"}</dt>
          <dd className="wrap">{gate.route_digest}</dd>
          <dt>{pinned ? "Input fingerprint" : "Binds input fingerprint"}</dt>
          <dd>{gate.input_fingerprint}</dd>
          <dt>Route</dt>
          <dd>
            {nodeCount} nodes · {edgeCount} typed edges
          </dd>
          <dt>Reserved</dt>
          <dd data-reserved={gate.reserved ?? "none"}>
            {gate.reserved ?? "nothing reserved — no provider call until the plan is approved"}
          </dd>
        </dl>
        <div className="note">
          {pinned ? (
            <>
              <b>Execution reads only the pin.</b> Replay from the same digest and fingerprint takes
              the same path; a changed source set or brief is a new run, not an edit.
            </>
          ) : (
            <>
              <b>Approving writes the route and the pin event in one transaction.</b> If the source
              set or the brief changes before you approve, the digest no longer matches and the
              approval is refused, not applied to something you did not see.
            </>
          )}
        </div>
        <div className="actions">
          <RefusedControl refusal={gate.approve} className="rb solid">
            Approve plan
          </RefusedControl>
        </div>
      </div>
    </section>
  );
}
