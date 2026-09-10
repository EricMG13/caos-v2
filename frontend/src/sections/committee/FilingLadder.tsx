// The right column: the host's chain around the deliverable — opinion →
// freeze → filing → receipt (SYSTEM_SPEC.md 7). File stays visible and
// refused for the signer and the freezer (APPROVER_NOT_INDEPENDENT); the
// receipt, once written, is detached and immutable. Nothing here edits the
// deliverable.
import type { ReactNode } from "react";
import { RefusalNote, RefusedControl } from "@/controls/RefusedControl";
import type { ServedRole } from "@/wire";
import type { CommitteeBody, LadderStep, Receipt } from "@/wire/committee";

const TONE: Record<LadderStep["state"], string> = { done: "ok", cur: "acc", ref: "crit", todo: "" };
const DONE: Record<LadderStep["key"], string> = {
  opinion: "SIGNED",
  freeze: "FROZEN",
  filing: "FILED",
  receipt: "WRITTEN",
};
const PENDING: Record<Exclude<LadderStep["state"], "done">, string> = {
  cur: "CURRENT",
  ref: "REFUSED",
  todo: "PENDING",
};

export function stepLabel(step: LadderStep): string {
  return step.state === "done" ? DONE[step.key] : PENDING[step.state];
}

function actorOf(ladder: LadderStep[], key: LadderStep["key"]): string {
  return ladder.find((step) => step.key === key)?.actor ?? "—";
}

function ReceiptBlock({ receipt }: { receipt: Receipt }) {
  return (
    <div className="receipt" data-receipt={receipt.filing_id}>
      <div>
        <span className="k">filing </span>
        {receipt.filing_id}
      </div>
      <div>
        <span className="k">deliverable sha256 </span>
        {receipt.deliverable_sha256}
      </div>
      <div>
        <span className="k">filed by </span>
        {receipt.filed_by}
      </div>
      <div>
        <span className="k">at </span>
        <time dateTime={receipt.filed_at}>{receipt.filed_at}</time>
      </div>
      <div>
        <span className="k">independence </span>
        {receipt.independence}
      </div>
    </div>
  );
}

function Step({
  step,
  index,
  children,
}: {
  step: LadderStep;
  index: number;
  children?: ReactNode;
}) {
  return (
    <li className={`step ${step.state}`} data-step={step.key} data-step-state={step.state}>
      <span className="n tabular" aria-hidden="true">
        {index + 1}
      </span>
      <div>
        <h3>
          {step.title} <span className={`tag ${TONE[step.state]}`}>{stepLabel(step)}</span>
        </h3>
        <div className="m">
          {step.actor ? (
            <>
              <b>{step.actor}</b> ·{" "}
            </>
          ) : null}
          {step.at ? (
            <>
              <time dateTime={step.at}>{step.at}</time> ·{" "}
            </>
          ) : null}
          {step.detail}
        </div>
        {children}
        {step.refusal ? <RefusalNote refusal={step.refusal} /> : null}
      </div>
    </li>
  );
}

export function FilingLadder({ body, role }: { body: CommitteeBody; role: ServedRole }) {
  const { ladder, file, receipt, deliverable } = body;
  return (
    <section className="pnl" aria-labelledby="filing-title">
      <header>
        <h2 id="filing-title">The filing</h2>
        <span className="cp">OPINION → FREEZE → FILING → RECEIPT</span>
        <span className="right">
          {deliverable.filed ? (
            <span className="tag ok">FILED</span>
          ) : (
            <span className="tag warn">NOT FILED</span>
          )}
        </span>
      </header>
      <ol className="pb flush ladder" aria-label="Filing chain">
        {ladder.map((step, index) => (
          <Step key={step.key} step={step} index={index}>
            {step.key === "filing" && !deliverable.filed ? (
              <div className="mt-2">
                <RefusedControl
                  refusal={file}
                  className="rb solid"
                  reasonDisplay="hidden"
                  aria-label="File the deliverable"
                >
                  File
                </RefusedControl>
              </div>
            ) : null}
            {step.key === "receipt" && receipt ? <ReceiptBlock receipt={receipt} /> : null}
          </Step>
        ))}
      </ol>
      <div className="sec">
        <p className="note" data-independence>
          The deliverable is{" "}
          <b>filed by an approver who neither signed the opinion nor froze the snapshot</b>. Opinion
          signer <b>{actorOf(ladder, "opinion")}</b> · freeze actor{" "}
          <b>{actorOf(ladder, "freeze")}</b> · you{" "}
          <b>
            {role.role} · {role.standing}
          </b>
          . Standing is checked where the commit is, not at this screen: the section composes the
          view and grants nothing.
        </p>
      </div>
      <div className="sec">
        <p className="note" data-output={deliverable.output}>
          <b>The output is one HTML file</b> — <code className="tabular">{deliverable.output}</code>{" "}
          — rendered by the host from <span className="tabular">{deliverable.snapshot}</span>,
          printing to paper, never overwritten. The frozen bytes read PENDING APPROVAL; the receipt
          is detached. Nothing on this section edits the deliverable — a material change starts a
          new revision in Report.
        </p>
      </div>
    </section>
  );
}
