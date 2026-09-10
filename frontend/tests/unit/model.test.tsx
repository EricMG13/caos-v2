import { readFileSync } from "node:fs";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { ModelSection } from "@/sections/model/ModelSection";
import { propagatedFrom } from "@/sections/model/Projection";
import { PASSPORT_FIELDS, type DocumentOf } from "@/wire";

const load = (path: string): DocumentOf<"model"> =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const doc = load("../../fixtures/model.json");

function mount(tab: string | null = null) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <ModelSection document={doc} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

const table = (container: HTMLElement, name: string) =>
  container.querySelector<HTMLTableElement>(`table.proj[data-projection][data-case="${name}"]`)!;

describe("Model", () => {
  test("test_projection_unavailable_propagates_forward", () => {
    const { container } = mount();
    const downside = table(container, "DOWNSIDE");
    expect(downside).not.toBeNull();
    const rows = [...downside.querySelectorAll<HTMLTableRowElement>("tbody tr[data-period]")];
    expect(rows.length).toBe(8);
    const unav = downside.querySelector<HTMLTableRowElement>("tr.unav[data-reason]")!;
    expect(unav).toHaveAttribute("data-period", "2027Q2");
    expect(unav.dataset["reason"]).toContain("residual 0.700 > tolerance 0.001");
    expect(unav).toHaveTextContent("residual 0.700 > tolerance 0.001");
    expect(unav.querySelector("td.resid")).toHaveTextContent("0.700");
    const later = rows.slice(rows.indexOf(unav) + 1);
    expect(later.length).toBe(4);
    for (const row of later) {
      expect(row).toHaveClass("prop");
      expect(row).toHaveAttribute("data-propagated", "true");
      expect(row).toHaveTextContent("unavailable · propagated from 2027Q2");
      expect(row.querySelectorAll(".cellbtn").length).toBe(0);
      expect(row.querySelector("td.resid")).toBeNull();
      // No number is read from a propagated period: no figure cell at all.
      expect(row.querySelectorAll("td").length).toBe(2);
      expect(row).not.toHaveTextContent(/0\.000|\b0\b/);
    }
    for (const row of rows.slice(0, rows.indexOf(unav))) expect(row).not.toHaveClass("unav");
    // BASE is unaffected.
    const base = table(container, "BASE");
    expect(base.querySelectorAll("tr.unav, tr.prop").length).toBe(0);
    expect(base.querySelectorAll("tbody tr[data-period]").length).toBe(8);
    for (const cell of base.querySelectorAll("td.resid")) expect(cell).toHaveTextContent("0.000");
    expect(container).toHaveTextContent("Why 2027Q2 DOWNSIDE is unavailable.");
  });

  test("test_residual_is_its_own_column", () => {
    const { container } = mount();
    for (const name of ["BASE", "DOWNSIDE"]) {
      const t = table(container, name);
      const heads = [...t.querySelectorAll("thead th")];
      const resid = t.querySelector("th.resid")!;
      expect(resid).toHaveTextContent("RESIDUAL");
      expect(resid).toHaveAttribute("scope", "col");
      const index = heads.indexOf(resid);
      expect(index).toBeGreaterThan(0);
      for (const row of t.querySelectorAll("tbody tr[data-period]:not(.prop)")) {
        const cells = row.querySelectorAll("td");
        expect(cells[index]).toHaveClass("resid");
        expect(row.querySelectorAll("td.resid").length).toBe(1);
      }
    }
    const periods = doc.body.cases[1]!.periods;
    expect(propagatedFrom(periods, 7)).toBe("2027Q2");
    expect(propagatedFrom(periods, 2)).toBeNull();
  });

  test("test_projected_cell_opens_a_passport_with_driver", () => {
    const { container } = mount();
    const button = table(container, "DOWNSIDE").querySelector<HTMLButtonElement>(
      'tr[data-period="2027Q1"] button.cellbtn[data-passport-id]',
    )!;
    expect(button).not.toBeNull();
    expect(doc.body.passports[button.dataset["passportId"]!]).toBeDefined();
    fireEvent.click(button);
    const dialog = screen.getByRole("dialog");
    const passport = dialog.querySelector("[data-passport]")!;
    expect(passport).not.toBeNull();
    for (const field of PASSPORT_FIELDS) {
      expect(passport.querySelector(`[data-passport-field="${field}"]`)).not.toBeNull();
    }
    expect(passport.querySelectorAll("[data-passport-field]").length).toBe(
      PASSPORT_FIELDS.length + 1,
    );
    const driver = passport.querySelector('[data-passport-field="driver"]')!;
    expect(driver).toHaveTextContent(/d-0\d/);
    expect(driver.querySelector("button.chip[data-chip]")).not.toBeNull();
    expect(dialog).toHaveTextContent("PROJECTED");
    // The formula bar follows the selection.
    expect(container.querySelector(".formulabar")).toHaveTextContent("DOWNSIDE · 2027Q1");
    expect(container.querySelector(".formulabar code")?.textContent?.startsWith("=")).toBe(true);
  });

  test("every figure cell is a passport button and every id resolves", () => {
    const { container } = mount();
    const buttons = container.querySelectorAll<HTMLButtonElement>(
      "button.cellbtn[data-passport-id]",
    );
    expect(buttons.length).toBeGreaterThan(100);
    for (const button of buttons) {
      expect(doc.body.passports[button.dataset["passportId"]!]).toBeDefined();
    }
    expect(container.querySelector("th.resid")).not.toBeNull();
  });

  test("the right column reads drivers, first breach, tolerance and the accepted artifact", () => {
    const { container } = mount();
    const drivers = container.querySelectorAll(".driver");
    expect(drivers.length).toBe(7);
    for (const row of drivers) expect(row.querySelector("button.chip[data-chip]")).not.toBeNull();
    expect(container.querySelector('[data-driver="d-05"] [data-chip]')).toHaveAttribute(
      "data-chip",
      "D-04 p.68 ¶2",
    );
    expect(container.querySelector('[data-breach="DOWNSIDE"]')).toHaveTextContent("2027Q1");
    expect(container.querySelector('[data-breach="BASE"]')).toHaveTextContent(
      "none in 8 available periods",
    );
    expect(container).toHaveTextContent(`sha256:${doc.body.artifact_sha256}`);
    expect(container).toHaveTextContent(doc.body.accepted_at);
    expect(container).toHaveTextContent("Tolerance0.001");
    expect(container).toHaveTextContent("Not on this page, by decision.");
    expect(screen.queryByRole("button", { name: /download|sign|save|edit/i })).toBeNull();
  });

  test("the drivers tab shows the driver rows in the centre", () => {
    const { container } = mount("drivers");
    expect(container.querySelector("table.proj")).toBeNull();
    expect(container.querySelectorAll(".driver").length).toBe(14);
  });
});
