// The step outputs of the module, as a grid. A RESTRICTED step carries its
// limitation in the cell; the state word is the bundle's.
import type { StepOutput } from "@/wire/analysis";

const STATE_CLASS: Record<StepOutput["state"], string> = {
  COMPLETE: "",
  RESTRICTED: "w",
  BLOCKED: "c",
};

export function Steps({ steps }: { steps: StepOutput[] }) {
  const complete = steps.filter((step) => step.state === "COMPLETE").length;
  return (
    <section className="pnl" data-steps>
      <header>
        <h2>Step outputs</h2>
        <span className="cp">CP-1</span>
        <span className="right">
          <span className={`tag ${complete === steps.length ? "ok" : "warn"}`}>
            {complete} OF {steps.length} COMPLETE
          </span>
        </span>
      </header>
      <ol className="pb flush steps plain">
        {steps.map((step) => (
          <li key={step.n} className="stepcell" data-step={step.n} data-step-state={step.state}>
            <span className="n">{step.n}</span>
            <span>
              {step.name}
              {step.limitation ? <span className="why"> — {step.limitation}</span> : null}
            </span>
            <span className={`st ${STATE_CLASS[step.state]}`}>{step.state}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
