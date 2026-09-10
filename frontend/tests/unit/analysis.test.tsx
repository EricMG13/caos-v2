// Analysis, /analysis/ (IA_SPEC.md 4.3): every figure one click from its
// evidence, conflicts shown never resolved, RESTRICTED output with its
// limitation, the formula bar on the selected cell.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { AnalysisSection } from "@/sections/analysis/AnalysisSection";
import { PASSPORT_FIELDS, type DocumentOf } from "@/wire";

const fixture = JSON.parse(
  readFileSync(join(__dirname, "../../fixtures/analysis.json"), "utf8"),
) as DocumentOf<"analysis">;
const RENDERED_CHIP = "D-04 p.68 ¶2";

function renderAnalysis(tab: string | null = null) {
  const view = render(
    <MemoryRouter>
      <EvidenceProvider>
        <AnalysisSection document={fixture} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
  const one = (selector: string): HTMLElement => {
    const element = view.container.querySelector<HTMLElement>(selector);
    if (!element) throw new Error(`missing ${selector}`);
    return element;
  };
  const all = (selector: string) => [...view.container.querySelectorAll<HTMLElement>(selector)];
  return { ...view, one, all };
}

describe("analysis", () => {
  test("test_every_figure_is_one_click_from_its_evidence", () => {
    const { one, all } = renderAnalysis();
    const table = one("table.fin[data-financials]");
    const rows = [...table.querySelectorAll("tbody tr[data-row]")];
    expect(rows).toHaveLength(fixture.body.financials.rows.length);
    for (const row of rows) {
      expect(row.querySelector("button[data-chip]")).not.toBeNull();
    }
    expect(table.querySelector(`[data-chip="${RENDERED_CHIP}"]`)).not.toBeNull();
    expect(one("[data-trace]").querySelector(`[data-chip="${RENDERED_CHIP}"]`)).not.toBeNull();
    // The chip opens the one drawer on the document, page and rectangle.
    fireEvent.click(all(`[data-chip="${RENDERED_CHIP}"]`)[0] as HTMLElement);
    const drawer = document.querySelector("[data-evidence-drawer]");
    expect(drawer).not.toBeNull();
    expect(drawer?.querySelector("img")?.getAttribute("src")).toBe("/api/pages/D-04-p68.svg");
    expect(drawer?.querySelector(".bbox")).not.toBeNull();
  });

  test("test_conflicts_are_shown_never_resolved", () => {
    const { one, all } = renderAnalysis();
    const register = one("[data-conflicts]");
    const conflicts = all("[data-conflict]");
    expect(conflicts).toHaveLength(fixture.body.conflicts.length);
    expect(fixture.body.conflicts.length).toBeGreaterThanOrEqual(2);
    fixture.body.conflicts.forEach((conflict, index) => {
      const item = conflicts[index] as HTMLElement;
      expect(item.dataset["conflict"]).toBe(conflict.term);
      expect(item.dataset["resolved"]).toBe("false");
      const readings = item.querySelectorAll("[data-reading]");
      expect(readings).toHaveLength(conflict.readings.length);
      conflict.readings.forEach((reading, at) => {
        const shown = readings[at] as HTMLElement;
        expect(shown.textContent).toContain(reading.value);
        expect(shown.querySelector(`[data-chip="${reading.citation.chip}"]`)).not.toBeNull();
      });
      expect(item.textContent).toContain(conflict.divergence);
      expect(item.textContent).toContain(conflict.restatement);
    });
    const buttons = [...register.querySelectorAll("button")];
    expect(buttons.some((button) => /resolve|accept|dismiss/i.test(button.textContent ?? ""))).toBe(
      false,
    );
  });

  test("test_restricted_output_carries_its_limitation", () => {
    const restricted = fixture.body.modules.find((module) => module.state === "RESTRICTED");
    if (!restricted) throw new Error("the fixture carries no RESTRICTED module");
    const tab = fixture.chrome.tabs.find((entry) => entry.cp === restricted.module_id);
    const { one, container } = renderAnalysis(tab?.id ?? null);
    const output = one(`[data-module="${restricted.module_id}"]`);
    expect(output.dataset["moduleState"]).toBe("RESTRICTED");
    const limitation = output.querySelector("[data-limitation]");
    expect(limitation?.querySelector(".tag.warn")?.textContent).toContain("RESTRICTED");
    expect(limitation?.textContent).toContain(restricted.limitation);
    // Rendered, not hidden and not promoted to an error.
    expect(output.querySelector(`[data-artifact="${restricted.module_id}"]`)).not.toBeNull();
    expect(container.querySelector('[data-surface-state="error"]')).toBeNull();
    expect(container.querySelector(".rs.crit")).toBeNull();
  });

  test("test_formula_bar_shows_selected_cell_derivation", () => {
    const { one } = renderAnalysis();
    const passport = fixture.body.passports["adj_ebitda:3"];
    if (!passport) throw new Error("fixture passport adj_ebitda:3 missing");
    const cell = one('button[data-cell="adj_ebitda:3"]');
    fireEvent.click(cell);
    const bar = one(".formulabar[data-formula-bar]");
    expect(bar.dataset["cell"]).toBe("adj_ebitda:3");
    expect(bar.querySelector(".coord")?.textContent).toContain("ADJ_EBITDA");
    expect(bar.querySelector("code")?.textContent).toContain(passport.derivation);
    for (const citation of passport.citations) {
      expect(bar.querySelector(`[data-chip="${citation.chip}"]`)).not.toBeNull();
    }
    expect(cell.closest("td")?.classList.contains("sel")).toBe(true);
    expect(cell.getAttribute("aria-pressed")).toBe("true");
    // The cell carries a passport, so the click also opened it: ten fields.
    const fields = [...document.querySelectorAll("[data-passport] [data-passport-field]")]
      .map((field) => (field as HTMLElement).dataset["passportField"])
      .filter((field) => (PASSPORT_FIELDS as readonly string[]).includes(field ?? ""));
    expect(fields).toEqual([...PASSPORT_FIELDS]);
  });

  test("three columns: register and trace, module output, clearance and frontier", () => {
    const { one, all } = renderAnalysis();
    expect(one(".cols.three .col.left [data-register]")).toBeInTheDocument();
    expect(all("[data-register] [data-source]")).toHaveLength(fixture.body.register.length);
    const trace = all("[data-trace] [data-trace-row]");
    expect(trace).toHaveLength(fixture.body.trace.length);
    for (const row of trace) {
      expect(row.querySelector("[data-chip]")).not.toBeNull();
      expect(row.textContent).toMatch(/\d+% · (HIGH|MEDIUM|LOW)/);
    }
    expect(one('.cols.three .col.centre [data-module="CP-1"]')).toBeInTheDocument();
    expect(one(".cols.three .col.right [data-clearance]")).toBeInTheDocument();
    expect(one("[data-adjusted]")).toBeInTheDocument();
    expect(all("[data-steps] [data-step]")).toHaveLength(fixture.body.steps.length);
  });

  test("clearance names its state and the blocking finding, with severity as shape", () => {
    const { one, all } = renderAnalysis();
    const clearance = one("[data-clearance]");
    expect(clearance.dataset["clearanceState"]).toBe(fixture.body.clearance.state);
    expect(
      clearance.querySelector(`[data-blocking="${fixture.body.clearance.blocking}"]`),
    ).not.toBeNull();
    const findings = all("[data-clearance] [data-finding]");
    expect(findings).toHaveLength(fixture.body.clearance.findings.length);
    for (const finding of findings) {
      expect(finding.querySelector("[data-severity][data-shape]")).not.toBeNull();
    }
  });

  test("the route frontier lists module id, state and reason", () => {
    const { all } = renderAnalysis();
    const items = all("[data-frontier] .frontier");
    expect(items).toHaveLength(fixture.body.frontier.length);
    fixture.body.frontier.forEach((item, index) => {
      const shown = items[index] as HTMLElement;
      expect(shown.querySelector(".id")?.textContent).toBe(item.module_id);
      expect(shown.dataset["state"]).toBe(item.state);
      expect(shown.textContent).toContain(item.state);
      expect(shown.querySelector(".why")?.textContent).toBe(item.reason);
    });
  });

  test("capital structure carries seniority and leverage-through; triggers are armed", () => {
    const { all } = renderAnalysis();
    const tranches = all("[data-capital] [data-tranche]");
    expect(tranches).toHaveLength(fixture.body.capital.length);
    fixture.body.capital.forEach((tranche, index) => {
      const shown = tranches[index] as HTMLElement;
      expect(shown.dataset["seniority"]).toBe(tranche.seniority);
      expect(shown.querySelector(`.sw.${tranche.seniority.toLowerCase()}`)).not.toBeNull();
      expect(shown.textContent).toContain(tranche.leverage_through);
      expect(shown.querySelector("[data-chip]")).not.toBeNull();
    });
    const triggers = all("[data-triggers] [data-trigger]");
    expect(triggers).toHaveLength(fixture.body.triggers.length);
    for (const trigger of triggers) {
      expect(trigger.querySelector("[data-severity][data-shape]")).not.toBeNull();
    }
  });

  test("the CP-6A tab is the debate's home: turns with citations, the weighting matrix", () => {
    const tab = fixture.chrome.tabs.find((entry) => entry.cp === "CP-6A");
    const { one, all } = renderAnalysis(tab?.id ?? null);
    expect(one('[data-module="CP-6A"]')).toBeInTheDocument();
    const turns = all("[data-debate] [data-turn]");
    expect(turns).toHaveLength(fixture.body.debate.turns.length);
    expect(turns.map((turn) => turn.dataset["turn"])).toEqual(
      fixture.body.debate.turns.map((turn) => turn.role),
    );
    expect(all("[data-debate] [data-chip]").length).toBeGreaterThan(0);
    const matrix = all("[data-weighting] table.fin tbody tr");
    expect(matrix).toHaveLength(fixture.body.debate.weighting.length);
    expect(one("[data-weighting] table.fin th[scope='col']")).toBeInTheDocument();
    expect(one("[data-memo]").textContent).toContain(fixture.body.debate.memo);
    expect(one("[data-module='CP-6A']").querySelector("[data-financials]")).toBeNull();
  });
});
