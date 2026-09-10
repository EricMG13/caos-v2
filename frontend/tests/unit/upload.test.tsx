import { readFileSync } from "node:fs";
import { fireEvent, render, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { UploadSection } from "@/sections/upload/UploadSection";
import type { DocumentOf } from "@/wire";

const load = (path: string): DocumentOf<"upload"> =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const fixture = load("../../fixtures/upload.json");
const partial = load("../../fixtures/states/upload.partial.json");

function mount(document: DocumentOf<"upload">, tab: string | null = null) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <UploadSection document={document} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

const sourceRow = (container: HTMLElement, id: string) =>
  container.querySelector<HTMLElement>(`table.reg[data-source-pack] tr[data-source="${id}"]`)!;

describe("Upload", () => {
  test("test_source_rows_show_grade_disposition_pages_digest_and_set_versions", () => {
    const { container } = mount(fixture);
    expect(container.querySelector("table.reg[data-source-pack]")).not.toBeNull();
    expect(container.querySelectorAll("tr[data-source]")).toHaveLength(fixture.body.sources.length);
    const source = fixture.body.sources.find((s) => s.source_id === "D-04")!;
    const row = sourceRow(container, "D-04");
    expect(row.querySelector(".grade")).toHaveClass("a");
    expect(row.querySelector(".grade")).toHaveTextContent("A");
    expect(row).toHaveTextContent(source.label);
    expect(row).toHaveTextContent(source.file_name);
    expect(row).toHaveTextContent(source.family);
    expect(row).toHaveTextContent("ADMITTED");
    expect(row).toHaveTextContent(String(source.pages));
    const digest = row.querySelector("[data-digest]")!;
    expect(digest).toHaveTextContent(source.sha256.slice(0, 12));
    expect(digest).toHaveAttribute("title", source.sha256);
    const pills = Array.from(row.querySelectorAll(".pill")).map((pill) => pill.textContent);
    expect(pills).toEqual(source.set_versions);
    expect(row.querySelector('.pill[data-version="SET-v4"]')).toHaveClass("on");
    // Every grade is drawn as its letter.
    for (const s of fixture.body.sources) {
      expect(sourceRow(container, s.source_id).querySelector(".grade")).toHaveTextContent(s.grade);
    }
  });

  test("test_withdrawal_is_checked_live_and_shown", () => {
    const { container } = mount(fixture);
    const live = sourceRow(container, "D-04");
    expect(live).toHaveTextContent(/checked live at 14:30Z/);
    expect(live).not.toHaveClass("wd");
    // The store withdraws; the browser never does, and never mints a timestamp.
    const withdraw = within(live).getByRole("button", { name: "Withdraw" });
    expect(withdraw).toHaveAttribute("data-refusal", "STORE_UNPLACED");
    const withdrawn = fixture.body.sources.find((s) => s.withdrawn_at !== null)!;
    const wd = container.querySelector<HTMLElement>("table.reg[data-source-pack] tr.wd")!;
    expect(wd).toHaveAttribute("data-source", withdrawn.source_id);
    expect(wd).toHaveTextContent("WITHDRAWN");
    expect(wd).toHaveTextContent(/Withdrawn 2026-09-09 09:41Z/);
    expect(wd).toHaveTextContent(/checked live at 14:30Z/);
    const refused = within(wd).getByRole("button", { name: "Withdraw" });
    expect(refused).toHaveAttribute("aria-disabled", "true");
    expect(refused).toHaveAttribute("data-refusal", "SOURCE_ALREADY_WITHDRAWN");
    expect(refused).toHaveAccessibleDescription(/SOURCE_ALREADY_WITHDRAWN/);
    // A click changes nothing on screen: no row flips, no time is invented.
    fireEvent.click(withdraw);
    expect(live).not.toHaveClass("wd");
    expect(container.querySelectorAll("tr.wd")).toHaveLength(1);
    expect(live).toHaveTextContent(/checked live at 14:30Z/);
  });

  test("the withdrawals tab shows only withdrawn sources with the refusal at use", () => {
    const { container } = mount(fixture, "withdrawals");
    expect(container.querySelectorAll("tr[data-source]")).toHaveLength(1);
    expect(container.querySelector("tr[data-source]")).toHaveClass("wd");
    expect(container.querySelector('.refusal[data-refusal="SOURCE_WITHDRAWN"]')).not.toBeNull();
  });

  test("test_restatement_is_a_conflict_row_never_merged", () => {
    const { container } = mount(fixture);
    const restatement = fixture.body.restatements[0]!;
    const conflicts = container.querySelectorAll<HTMLElement>("tr.conflict");
    expect(conflicts).toHaveLength(fixture.body.restatements.length);
    const conflict = conflicts[0]!;
    expect(conflict).toHaveTextContent(restatement.item);
    expect(conflict).toHaveTextContent(restatement.divergence);
    expect(restatement.readings).toHaveLength(2);
    for (const reading of restatement.readings) {
      expect(conflict).toHaveTextContent(reading.source_label);
      expect(conflict).toHaveTextContent(reading.value);
      expect(conflict.querySelector(`[data-chip="${reading.citation.chip}"]`)).not.toBeNull();
    }
    // Both readings stand in one row: two chips, no single merged value.
    expect(conflict.querySelectorAll(".chip")).toHaveLength(2);
    expect(within(conflict).getAllByRole("listitem")).toHaveLength(2);
    expect(container.querySelector("[data-restatements]")).toHaveTextContent(/Both readings stand/);
  });

  test("the pinned set is marked and pinning it again is refused with its code", () => {
    const { container } = mount(fixture);
    expect(container.querySelectorAll("[data-set-version]")).toHaveLength(
      fixture.body.set_versions.length,
    );
    const pinned = container.querySelector<HTMLElement>(
      '[data-set-version="SET-v4"][data-pinned="true"]',
    )!;
    expect(pinned).not.toBeNull();
    expect(within(pinned).getByRole("button", { name: "Pin set" })).toHaveAttribute(
      "data-refusal",
      "SET_ALREADY_PINNED",
    );
    expect(pinned).toHaveTextContent("SET_ALREADY_PINNED");
    const other = container.querySelector<HTMLElement>('[data-set-version="SET-v3"]')!;
    expect(other).toHaveAttribute("data-pinned", "false");
    expect(within(other).getByRole("button", { name: "Pin set" })).toHaveAttribute(
      "data-refusal",
      "STORE_UNPLACED",
    );
  });

  test("a partial document names the source whose withdrawal check is pending", () => {
    expect(partial.status).toBe("partial");
    expect(partial.notes?.join(" ")).toMatch(/withdrawal check for D-06/);
    const { container } = mount(partial);
    expect(container.querySelector("tr.wd")).toBeNull();
    expect(sourceRow(container, "D-06")).toHaveTextContent(/checked live at 09:41Z/);
  });
});
