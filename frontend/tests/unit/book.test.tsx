// Book, /book/ (IA_SPEC.md 4.4): one basis and one bound snapshot per compared
// case, definition deviation on every affected cell, stale as colour and date,
// the ten-field passport from any cell.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { LedgerProvider } from "@/app/ledger";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { BookSection } from "@/sections/book/BookSection";
import { PASSPORT_FIELDS, type DocumentOf } from "@/wire";

const fixture = JSON.parse(
  readFileSync(join(__dirname, "../../fixtures/book.json"), "utf8"),
) as DocumentOf<"book">;
const empty = JSON.parse(
  readFileSync(join(__dirname, "../../fixtures/states/book.observed-empty.json"), "utf8"),
) as DocumentOf<"book">;

function renderBook(tab: string | null = null, document: DocumentOf<"book"> = fixture) {
  const view = render(
    <MemoryRouter>
      <LedgerProvider>
        <EvidenceProvider>
          <BookSection document={document} tab={tab} />
        </EvidenceProvider>
      </LedgerProvider>
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

const deviatingCells = (cells: Record<string, { deviation: string | null; passport_id: string }>) =>
  Object.values(cells).filter((cell) => cell.deviation !== null);

describe("book", () => {
  test("test_compare_states_one_basis_and_binds_one_snapshot_per_case", () => {
    const { one, all } = renderBook("compare");
    const grid = one(".cmpgrid[data-compare]");
    const { basis } = fixture.body.compare;
    for (const stated of [basis.period, basis.scenario, "accepted only"]) {
      expect(grid.dataset["basis"]).toContain(stated);
      expect(one("[data-basis]").textContent).toContain(stated);
    }
    const bound = all("[data-bound-snapshot]");
    expect(bound.map((cell) => cell.dataset["boundSnapshot"])).toEqual([
      "snp_cvna_q2_2026",
      "snp_chtr_q2_2026",
    ]);
    expect(bound.map((cell) => cell.dataset["case"])).toEqual([
      "CASE-2026-CVNA01",
      "CASE-2026-CHTR03",
    ]);
    expect(fixture.body.compare.cases).toHaveLength(2);
    expect(all(".cmpgrid button.cellbtn[data-passport-id]")).toHaveLength(
      2 * fixture.body.compare.metrics.length,
    );
  });

  test("test_definition_deviation_is_marked_on_every_affected_cell", () => {
    const affected = fixture.body.rows.filter((row) => deviatingCells(row.cells).length > 0);
    expect(affected.length).toBeGreaterThanOrEqual(1);
    const table = renderBook();
    for (const row of affected) {
      const shown = table.one(`tr[data-case="${row.case_id}"]`);
      expect(shown.dataset["deviates"]).toBe("true");
      expect(shown.querySelector("td.l .defmark")).not.toBeNull();
      for (const cell of deviatingCells(row.cells)) {
        const button = shown.querySelector<HTMLElement>(
          `button.cellbtn[data-passport-id="${cell.passport_id}"]`,
        );
        expect(button?.querySelector(".defmark")).not.toBeNull();
        expect(button?.title).toContain(cell.deviation ?? "");
        expect(button?.dataset["deviation"]).toBe(cell.deviation);
      }
    }
    table.unmount();
    const compare = renderBook("compare");
    const compared = fixture.body.compare.cases.flatMap((entry) => deviatingCells(entry.cells));
    expect(compared.length).toBeGreaterThanOrEqual(1);
    for (const cell of compared) {
      const button = compare.one(`.cmpgrid button.cellbtn[data-passport-id="${cell.passport_id}"]`);
      expect(button.querySelector(".defmark")).not.toBeNull();
      expect(button.title).toContain(cell.deviation ?? "");
      expect(compare.one(`[data-deviation-note="${cell.passport_id}"]`).textContent).toContain(
        cell.deviation ?? "",
      );
    }
  });

  test("test_stale_is_colour_and_date", () => {
    const stale = fixture.body.rows.filter((row) => row.freshness.state === "stale");
    expect(stale.length).toBeGreaterThanOrEqual(1);
    const { one } = renderBook();
    for (const row of stale) {
      const shown = one(`tr[data-case="${row.case_id}"]`);
      const staleCells = Object.values(row.cells).filter((cell) => cell.stale);
      expect(staleCells.length).toBeGreaterThan(0);
      for (const cell of staleCells) {
        const button = shown.querySelector<HTMLElement>(
          `button[data-passport-id="${cell.passport_id}"]`,
        );
        expect(button?.closest("td")?.classList.contains("stale")).toBe(true);
        expect(button?.title).toContain(row.freshness.date);
      }
      const date = shown.querySelector<HTMLTimeElement>("td.stale time");
      expect(date?.getAttribute("datetime")).toBe(row.freshness.date);
      expect(shown.textContent).toContain("STALE");
    }
    const current = fixture.body.rows.find((row) => row.freshness.state === "current");
    expect(one(`tr[data-case="${current?.case_id}"]`).querySelector("td.stale")).toBeNull();
  });

  test("test_selecting_a_cell_opens_the_passport", () => {
    const { one } = renderBook();
    fireEvent.click(one('button.cellbtn[data-passport-id="cvna.net_leverage"]'));
    const passport = document.querySelector("[data-passport]");
    expect(passport).not.toBeNull();
    const fields = [...(passport?.querySelectorAll("[data-passport-field]") ?? [])]
      .map((field) => (field as HTMLElement).dataset["passportField"])
      .filter((field) => (PASSPORT_FIELDS as readonly string[]).includes(field ?? ""));
    expect(fields).toHaveLength(10);
    expect(fields).toEqual([...PASSPORT_FIELDS]);
    // An actual cell has no driver.
    expect(fixture.body.passports["cvna.net_leverage"]?.driver).toBeNull();
    expect(passport?.querySelector('[data-passport-field="driver"]')).toBeNull();
  });

  test("facets are real checkbox groups and filter what was served", () => {
    const { all, one } = renderBook();
    const options = fixture.body.facets.flatMap((facet) => facet.options);
    const boxes = all("fieldset.facet input[type='checkbox']");
    expect(boxes).toHaveLength(options.length);
    for (const box of boxes) expect(box.closest("label")?.textContent).not.toBe("");
    expect(all("fieldset.facet legend").map((legend) => legend.textContent)).toEqual(
      fixture.body.facets.map((facet) => facet.label),
    );
    expect(all("table.cases[data-book] tr[data-case]")).toHaveLength(fixture.body.rows.length);
    fireEvent.click(one("input[data-facet-option='BLOCKED']"));
    expect(all("tr[data-case]")).toHaveLength(fixture.body.rows.length - 1);
    expect(one("[data-book-panel]").querySelector('tr[data-case="CASE-2026-FLYYQ04"]')).toBeNull();
  });

  test("grouping keys are pressed pills that regroup the rows", () => {
    const { all, one } = renderBook();
    const pills = all("button.pill[data-group-key]");
    expect(pills.map((pill) => pill.dataset["groupKey"])).toEqual(fixture.body.grouping.keys);
    expect(
      one(`button.pill[data-group-key="${fixture.body.grouping.active}"]`).getAttribute(
        "aria-pressed",
      ),
    ).toBe("true");
    expect(all("tr.grp").length).toBeGreaterThan(0);
    fireEvent.click(one('button.pill[data-group-key="pathway"]'));
    expect(one('button.pill[data-group-key="pathway"]').getAttribute("aria-pressed")).toBe("true");
    expect(
      one(`button.pill[data-group-key="${fixture.body.grouping.active}"]`).getAttribute(
        "aria-pressed",
      ),
    ).toBe("false");
    expect(one("table.cases[data-book]").dataset["groupedBy"]).toBe("pathway");
    expect(all("tr.grp").map((group) => group.textContent)).toContain("FULL_CREDIT_32 · 3 credits");
  });

  test("saved views carry their scope label; every cell is a passport button", () => {
    const { all } = renderBook();
    const scopes = all("[data-saved-view] [data-scope]").map((tag) => tag.textContent);
    expect(scopes).toEqual(fixture.body.saved_views.map((view) => view.scope));
    for (const scope of scopes) {
      expect(["THIS BROWSER", "ANALYST PROFILE", "WORKSPACE"]).toContain(scope);
    }
    const cells = all("table.cases[data-book] button.cellbtn[data-passport-id]");
    expect(cells).toHaveLength(fixture.body.rows.length * fixture.body.columns.length);
    for (const cell of cells) {
      expect(fixture.body.passports[cell.dataset["passportId"] ?? ""]).toBeDefined();
    }
  });

  test("an observed-empty book renders nothing as a row and infers nothing", () => {
    expect(empty.observed_empty).toBe(true);
    expect(empty.body.rows).toHaveLength(0);
    expect(empty.body.compare.cases).toHaveLength(0);
    const table = renderBook(null, empty);
    expect(table.all("tr[data-case]")).toHaveLength(0);
    expect(table.one("[data-book-panel]").textContent).toContain(
      "Nothing is inferred from silence",
    );
    table.unmount();
    const compare = renderBook("compare", empty);
    expect(compare.all("[data-bound-snapshot]")).toHaveLength(0);
    expect(compare.one("[data-compare-panel]").textContent).toContain("No credit is compared");
  });
});

describe("the snapshot binding", () => {
  test("a later document carrying a different snapshot for a bound case is refused until the lens is switched", () => {
    const view = render(
      <MemoryRouter>
        <LedgerProvider>
          <EvidenceProvider>
            <BookSection document={fixture} tab="compare" />
          </EvidenceProvider>
        </LedgerProvider>
      </MemoryRouter>,
    );
    expect(view.container.querySelector("[data-refusal='SNAPSHOT_MISMATCH']")).toBeNull();
    const moved = structuredClone(fixture);
    const chtr = moved.body.compare.cases.find((entry) => entry.case_id === "CASE-2026-CHTR03")!;
    chtr.snapshot = "snp_chtr_q3_2026";
    moved.observed_at = "2026-09-10T09:00:00Z";
    view.rerender(
      <MemoryRouter>
        <LedgerProvider>
          <EvidenceProvider>
            <BookSection document={moved} tab="compare" />
          </EvidenceProvider>
        </LedgerProvider>
      </MemoryRouter>,
    );
    const refusal = view.container.querySelector("[data-refusal='SNAPSHOT_MISMATCH']");
    expect(refusal).not.toBeNull();
    expect(refusal).toHaveTextContent(/snp_chtr_q2_2026/);
    // The other case is untouched, and the refused case's cells are not rendered as figures.
    expect(view.container.querySelectorAll("[data-refusal='SNAPSHOT_MISMATCH']")).toHaveLength(1);
    fireEvent.click(view.getByRole("button", { name: /Switch lens to snp_chtr_q3_2026/ }));
    expect(view.container.querySelector("[data-refusal='SNAPSHOT_MISMATCH']")).toBeNull();
    expect(view.container.querySelector("[data-case='CASE-2026-CHTR03']")).toHaveAttribute(
      "data-bound-snapshot",
      "snp_chtr_q3_2026",
    );
  });
});
