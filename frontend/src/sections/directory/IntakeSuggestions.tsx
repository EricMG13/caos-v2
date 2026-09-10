// Document-first intake (IA_SPEC.md 4.1, card 5b). The panel posts files and
// nothing else; everything the server decided comes back as a labelled
// suggestion until a person commits it. A completed intake run is opened for
// review, never accepted on the analyst's behalf.
import { useId, useState } from "react";
import { Link } from "react-router";
import { RefusedControl } from "@/controls/RefusedControl";
import type { Refusal } from "@/wire";
import type { Intake, IntakeSuggestion } from "@/wire/directory";

const ALREADY_COMMITTED: Refusal = {
  code: "SUGGESTION_ALREADY_COMMITTED",
  clears: "a new intake proposes a different value",
};
/** A person commits a suggestion in the store; the browser proposes nothing and commits nothing. */
const STORE_UNPLACED: Refusal = {
  code: "STORE_UNPLACED",
  clears: "Phase 2 admits the pack and records the analyst's commit (docs/REBUILD_PLAN.md)",
};

function SuggestionRow({
  suggestion,
  committed,
}: {
  suggestion: IntakeSuggestion;
  committed: boolean;
}) {
  return (
    <div className="sugrow" data-suggestion={suggestion.key} data-committed={committed}>
      <span className="k">{suggestion.key.replace(/_/g, " ")}</span>
      <span className="v">{suggestion.value}</span>
      <span className="act">
        {committed ? (
          <span className="tag ok">COMMITTED</span>
        ) : (
          <span className="sug">SUGGESTED</span>
        )}
        <RefusedControl
          refusal={committed ? ALREADY_COMMITTED : STORE_UNPLACED}
          className="rowact"
          reasonDisplay="hidden"
        >
          Commit
        </RefusedControl>
      </span>
      <span className="why">{suggestion.why}</span>
    </div>
  );
}

export function IntakeSuggestions({ intake, caseId }: { intake: Intake; caseId: string | null }) {
  const headingId = useId();
  const committed = new Set(intake.suggestions.filter((s) => s.committed).map((s) => s.key));
  const open = intake.suggestions.filter((s) => !committed.has(s.key)).length;
  const runHref = `/run/?case=${encodeURIComponent(caseId ?? "")}`;
  return (
    <section className="pnl" aria-labelledby={headingId} data-intake-suggestions>
      <header>
        <h2 id={headingId}>What the server proposes</h2>
        <span className="cp">CP-PARSE · CP-0</span>
        <span className="right">
          <span className={`tag ${open ? "warn" : "ok"}`}>
            {open ? `${open} UNCOMMITTED` : "ALL COMMITTED"}
          </span>
        </span>
      </header>
      <div className="pb flush">
        {intake.suggestions.map((suggestion) => (
          <SuggestionRow
            key={suggestion.key}
            suggestion={suggestion}
            committed={committed.has(suggestion.key)}
          />
        ))}
      </div>
      {intake.run_id ? (
        <div className="pb note" data-intake-run={intake.run_id}>
          <b>A completed intake run is opened for review, never accepted.</b> Run{" "}
          <code>{intake.run_id}</code> parsed and read this pack for readiness; committing writes
          the case, the source set and the route selection — not the analysis.{" "}
          <Link className="rowact" to={runHref}>
            Open {intake.run_id} in Run
          </Link>
        </div>
      ) : null}
    </section>
  );
}

/** The drop region: a real file input with a label. The browser posts files and nothing else. */
export function IntakeDrop() {
  const id = useId();
  const [names, setNames] = useState<string[]>([]);
  return (
    <div className="drop" data-intake-drop>
      <label htmlFor={id} className="big">
        Drop documents for a case
      </label>
      <p className="sm" id={`${id}-why`}>
        The panel posts files and nothing else. The server creates or resolves the case, admits
        every file or none, classifies, selects a route and starts the run. Issuer, label, types,
        periods, dispositions and route come back here as suggestions — never taken from the
        browser, and never from an instruction found inside a document.
      </p>
      <input
        id={id}
        type="file"
        multiple
        className="tin"
        aria-describedby={`${id}-why`}
        onChange={(event) =>
          setNames(Array.from(event.currentTarget.files ?? [], (file) => file.name))
        }
      />
      {names.length ? (
        <p className="sm" data-selected-files={names.length}>
          {names.length} {names.length === 1 ? "file" : "files"} selected · admitted as one pack, or
          none
        </p>
      ) : null}
    </div>
  );
}
