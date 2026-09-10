import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { CommitteeSection } from "@/sections/committee/CommitteeSection";
import { WATERMARK } from "@/sections/committee/Paper";
import type { DocumentOf } from "@/wire";

// Vitest runs from frontend/; the fixtures sit beside the tests' package root.
function load(name: string): DocumentOf<"committee"> {
  return JSON.parse(readFileSync(resolve(process.cwd(), "fixtures", name), "utf8"));
}
const signer = load("committee.json");
const reader = load("states/committee.reader.json");
const filed = load("states/committee.filed.json");

function mount(doc: DocumentOf<"committee">, tab: string | null = null) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <CommitteeSection document={doc} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

function q<E extends Element = HTMLElement>(container: HTMLElement, selector: string): E {
  const element = container.querySelector<E>(selector);
  if (!element) throw new Error(`missing ${selector}`);
  return element;
}

describe("Committee", () => {
  test("test_deliverable_is_watermarked_until_filed", () => {
    expect(WATERMARK).toBe("DRAFT — NOT FILED");
    const draft = mount(signer);
    expect(signer.body.deliverable.filed).toBe(false);
    const watermark = q(draft.container, "[data-paper] [data-watermark]");
    expect(watermark.textContent).toBe("DRAFT — NOT FILED");
    expect(watermark).toHaveClass("rd-wm");
    expect(draft.container.querySelector(".rd-stamp")).toBeNull();
    draft.unmount();
    const asReader = mount(reader);
    expect(q(asReader.container, "[data-watermark]").textContent).toBe("DRAFT — NOT FILED");
    asReader.unmount();
    const after = mount(filed);
    expect(after.container.querySelector("[data-watermark]")).toBeNull();
  });

  test("test_file_is_visible_and_refused_for_the_signer", () => {
    const { container } = mount(signer);
    expect(signer.chrome.served_role).toEqual({ role: "Analyst", standing: "APPROVER" });
    const step = q(container, '.ladder [data-step="filing"]');
    expect(step.getAttribute("data-step-state")).toBe("ref");
    const file = q<HTMLButtonElement>(step, 'button[data-refusal="APPROVER_NOT_INDEPENDENT"]');
    expect(file).toBeVisible();
    expect(file).toHaveAttribute("aria-disabled", "true");
    expect(file).not.toHaveAttribute("disabled");
    expect(file).not.toHaveAttribute("hidden");
    expect(file).toHaveTextContent("File");
    expect(file).toHaveClass("rb", "solid");
    // the refusal states the independence rule and what clears it
    const note = q(step, '.refusal[data-refusal="APPROVER_NOT_INDEPENDENT"]');
    expect(note).toHaveTextContent("neither the opinion signer nor the freeze actor");
    expect(q(container, "[data-independence]")).toHaveTextContent(
      "filed by an approver who neither signed the opinion nor froze the snapshot",
    );
    // the ribbon primary is File, refused the same way
    const primary = signer.chrome.ribbon.actions.find((action) => action.primary);
    expect(primary).toMatchObject({ label: "File", refusal: { code: "APPROVER_NOT_INDEPENDENT" } });
    expect(signer.body.receipt).toBeNull();
  });

  test("test_reader_sees_file_refused_not_hidden", () => {
    expect(reader.chrome.served_role).toEqual({ role: "Reader", standing: "READER" });
    expect(reader.body.deliverable).toEqual(signer.body.deliverable);
    const { container } = mount(reader);
    const file = q(
      container,
      '.ladder [data-step="filing"] button[data-refusal="APPROVER_NOT_INDEPENDENT"]',
    );
    expect(file).toBeVisible();
    expect(file).toHaveAttribute("aria-disabled", "true");
    expect(file).not.toHaveAttribute("disabled");
    expect(reader.body.file?.clears).toMatch(/READER/);
    expect(reader.body.file?.clears).toMatch(/independent approver/);
    expect(q(container, '.refusal[data-refusal="APPROVER_NOT_INDEPENDENT"]')).toHaveTextContent(
      "READER standing cannot file",
    );
    expect(q(container, "[data-independence]")).toHaveTextContent("Reader · READER");
    const primary = reader.chrome.ribbon.actions.find((action) => action.primary);
    expect(primary).toMatchObject({ label: "File", refusal: { code: "APPROVER_NOT_INDEPENDENT" } });
    expect(primary?.refusal?.clears).toMatch(/READER/);
  });

  test("test_filed_deliverable_shows_receipt_and_no_watermark", () => {
    const { container } = mount(filed);
    const receipt = filed.body.receipt;
    if (!receipt) throw new Error("the filed fixture carries a receipt");
    expect(filed.body.deliverable.filed).toBe(true);
    expect(filed.body.deliverable.watermark).toBeNull();
    expect(q(container, "[data-paper] .rd-stamp")).toHaveTextContent("FILED");
    expect(container.querySelector("[data-watermark]")).toBeNull();
    const block = q(container, ".ladder .receipt");
    for (const value of [
      receipt.filing_id,
      receipt.deliverable_sha256,
      receipt.filed_by,
      receipt.filed_at,
      receipt.independence,
    ]) {
      expect(block).toHaveTextContent(value);
    }
    const line = q(container, "[data-paper] .rd-filed-line");
    expect(line).toHaveTextContent(receipt.filing_id);
    expect(line).toHaveTextContent(receipt.filed_by);
    expect(line).toHaveTextContent(receipt.filed_at);
    const steps = container.querySelectorAll(".ladder [data-step]");
    expect(steps).toHaveLength(4);
    for (const step of steps) expect(step.getAttribute("data-step-state")).toBe("done");
    expect(q(container, '.ladder [data-step="filing"]')).toHaveTextContent(receipt.filed_by);
    // filed: File is done, not refused; the primary becomes Open receipt, live
    expect(filed.body.file).toBeNull();
    expect(container.querySelector(".ladder button[data-refusal]")).toBeNull();
    const primary = filed.chrome.ribbon.actions.find((action) => action.primary);
    expect(primary).toEqual({ label: "Open receipt", primary: true, refusal: null });
  });

  test("test_artifacts_are_in_route_order", () => {
    const { container } = mount(signer);
    const route = signer.body.artifacts.map((artifact) => artifact.module_id);
    const rows = [...container.querySelectorAll("[data-artifact]")].map((row) =>
      row.getAttribute("data-artifact"),
    );
    expect(rows).toEqual(route);
    expect(route.indexOf("CP-6")).toBe(route.indexOf("CP-5") + 1);
    // every row shows module id, name and disposition
    for (const artifact of signer.body.artifacts) {
      const row = q(container, `[data-artifact="${artifact.module_id}"]`);
      expect(row).toHaveTextContent(artifact.name);
      expect(row).toHaveTextContent(artifact.disposition);
    }
    expect(q(container, '[data-artifact="CP-1C"]')).toHaveTextContent("RESTRICTED");
    expect(q(container, '[data-artifact="CP-3"]')).toHaveTextContent("SCREENING_ONLY");
    // the paper's sections follow the same order, then the narrative and the index
    const positions = [...container.querySelectorAll("[data-paper] .rd-sec[data-module]")].map(
      (section) => route.indexOf(section.getAttribute("data-module") ?? ""),
    );
    expect(positions.length).toBeGreaterThan(8);
    expect(positions.every((position) => position >= 0)).toBe(true);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
    const trailing = [...container.querySelectorAll("[data-paper] .rd-sec")].slice(-2);
    expect(trailing[0]?.hasAttribute("data-narrative")).toBe(true);
    expect(trailing[1]?.hasAttribute("data-provenance-section")).toBe(true);
    const entries = [...container.querySelectorAll("[data-artifact], [data-entry]")].slice(-2);
    expect(entries.map((entry) => entry.getAttribute("data-entry"))).toEqual([
      "narrative",
      "provenance",
    ]);
  });

  test("test_paper_is_only_inside_the_deliverable", () => {
    const { container } = mount(signer);
    const papers = container.querySelectorAll(".rd-paper");
    expect(papers).toHaveLength(1);
    expect(container.querySelector(".rd-paper:not([data-paper])")).toBeNull();
    expect(papers[0]?.closest(".papergutter")).not.toBeNull();
    for (const element of container.querySelectorAll('[class^="rd-"], [class*=" rd-"]')) {
      expect(element.closest("[data-paper]")).not.toBeNull();
    }
    expect(q(container, "table.prov").closest("[data-paper]")).not.toBeNull();
    expect(container.querySelector(".ladder")?.closest("[data-paper]")).toBeNull();
  });

  test("every figure on the paper carries a citation button that opens the one evidence drawer", () => {
    const { container } = mount(signer);
    const cites = container.querySelectorAll("[data-paper] button.rd-cite");
    const figures = signer.body.paper.reduce(
      (n, section) => n + section.paragraphs.reduce((m, p) => m + p.figures.length, 0),
      0,
    );
    expect(cites).toHaveLength(figures);
    for (const cite of cites) expect(cite.getAttribute("aria-label")).toMatch(/^Evidence /);
    const p68 = q(container, '[data-paper] button.rd-cite[data-chip="D-04 p.68 ¶2"]');
    fireEvent.click(p68);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("D-04 · 8-K Senior Secured Notes Indenture");
    expect(dialog.querySelector("img")?.getAttribute("src")).toBe("/api/pages/D-04-p68.svg");
    expect(p68).toHaveAttribute("aria-expanded", "true");
  });

  test("the masthead, the ladder order and the one-HTML-file line", () => {
    const { container } = mount(signer);
    expect(q(container, "[data-paper] .rd-mast")).toHaveTextContent(
      /ORIGIN.*METHOD.*APPROVAL.*snp_cvna_q2_2026/,
    );
    expect(q(container, "[data-paper] .rd-title")).toHaveTextContent(signer.body.deliverable.title);
    expect(q(container, "[data-paper] .rd-sub")).toHaveTextContent("rev_3");
    expect(
      [...container.querySelectorAll(".ladder [data-step]")].map((step) =>
        step.getAttribute("data-step"),
      ),
    ).toEqual(["opinion", "freeze", "filing", "receipt"]);
    expect(q(container, '.ladder [data-step="opinion"]')).toHaveTextContent("A. Reyes");
    expect(q(container, '.ladder [data-step="opinion"]')).toHaveTextContent("rev_3");
    const output = q(container, "[data-output]");
    expect(output).toHaveTextContent("The output is one HTML file");
    expect(output.getAttribute("data-output")).toBe(signer.body.deliverable.output);
    expect(q(container, "[data-paper] .rd-table")).toHaveTextContent("Total funded debt");
  });

  test("the tabs scope the paper without leaving it", () => {
    const provenance = mount(signer, "provenance");
    expect(provenance.container.querySelector("[data-paper] table.prov")).not.toBeNull();
    expect(provenance.container.querySelector("[data-paper] [data-narrative]")).toBeNull();
    expect(provenance.container.querySelector("[data-paper] [data-watermark]")).not.toBeNull();
    provenance.unmount();
    const narrative = mount(signer, "narrative");
    expect(narrative.container.querySelector("[data-paper] [data-narrative]")).not.toBeNull();
    expect(narrative.container.querySelector("[data-paper] table.prov")).toBeNull();
    expect(narrative.container.querySelector(".ladder")).not.toBeNull();
  });
});
