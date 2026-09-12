import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { ReportSection, nextRevisionId } from "@/sections/report/ReportSection";
import { segments } from "@/sections/report/text";
import type { DocumentOf } from "@/wire";

// Vitest runs from frontend/; the fixtures sit beside the tests' package root.
const report = JSON.parse(
  readFileSync(resolve(process.cwd(), "fixtures/report.json"), "utf8"),
) as DocumentOf<"report">;

function mount(tab: string | null = null) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <ReportSection document={report} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

function q<E extends Element = HTMLElement>(container: HTMLElement, selector: string): E {
  const element = container.querySelector<E>(selector);
  if (!element) throw new Error(`missing ${selector}`);
  return element;
}

describe("Report", () => {
  test("test_freeze_refusal_names_the_uncited_figure", () => {
    const { container } = mount();
    const figure = q(container, ".ed [data-uncited-figure]");
    const name = figure.getAttribute("data-uncited-figure") ?? "";
    expect(name).not.toBe("");
    expect(figure).toHaveTextContent(name);
    expect(figure).toHaveClass("figure");
    expect(figure.closest("p")?.getAttribute("data-kind")).toBe("ANALYST_JUDGMENT");
    // only a judgment paragraph asserts an uncited figure, and only one does
    expect(container.querySelectorAll("[data-uncited-figure]")).toHaveLength(1);
    // the freeze refusal names it, as a RefusalNote
    const note = q(container, '.refusal[data-refusal="UNCITED_FIGURE_IN_JUDGMENT"]');
    expect(note).toHaveTextContent(name);
    expect(note).toHaveTextContent("Clears when");
    expect(report.body.freeze?.clears).toContain(name);
    // and so does the ribbon primary, Sign opinion
    const primary = report.chrome.ribbon.actions.find((action) => action.primary);
    expect(primary?.label).toBe("Sign opinion");
    expect(primary?.refusal?.code).toBe("UNCITED_FIGURE_IN_JUDGMENT");
    expect(primary?.refusal?.clears).toContain(name);
    expect(report.chrome.ribbon.actions.filter((action) => action.primary)).toHaveLength(1);
  });

  test("test_opinion_binds_the_exact_revision", () => {
    const { container } = mount();
    expect(report.body.opinion).toBeNull();
    const prior = report.body.prior_opinion;
    if (!prior) throw new Error("the fixture carries the prior opinion on rev_3");
    const bound = report.body.revisions.find((revision) => revision.id === prior.revision_id);
    expect(bound?.digest).toBe(prior.digest);
    expect(prior.digest).not.toBe(report.body.revision.digest);
    // no opinion on the draft; the prior opinion is shown with signer, digest and time
    expect(q(container, '[data-opinion="none"]')).toHaveTextContent(report.body.revision.id);
    const block = q(container, `[data-prior-opinion="${prior.revision_id}"]`);
    expect(block).toHaveTextContent(prior.signed_by);
    expect(block).toHaveTextContent(prior.signed_at);
    expect(block).toHaveTextContent(prior.digest.slice(0, 8));
    expect(block).toHaveTextContent("does not carry forward");
    expect(block.querySelector("code")?.getAttribute("title")).toBe(prior.digest);
    // the panel binds the current revision by its digest, and the next edit is rev_5
    expect(q(container, "#opinion-title")).toHaveTextContent("Opinion and freeze");
    expect(q(container, ".kv")).toHaveTextContent(report.body.revision.digest.slice(0, 8));
    expect(q(container, "[data-next-revision]").getAttribute("data-next-revision")).toBe("rev_5");
    expect(nextRevisionId("rev_12")).toBe("rev_13");
  });

  test("the opinion panel names the viewer as the viewer, never as the signer", () => {
    const { container } = mount();
    const panel = q(container, "section[aria-labelledby='opinion-title']");
    const labels = [...panel.querySelectorAll("dt")].map((dt) => dt.textContent);
    // rev_4 is unsigned: a 'Signer' row holding the viewer's role says they signed.
    expect(report.body.opinion).toBeNull();
    expect(labels).not.toContain("Signer");
    expect(labels).toContain("You");
  });

  test("test_report_surface_is_not_paper", () => {
    const { container } = mount();
    expect(container.querySelector(".rd-paper")).toBeNull();
    expect(container.querySelector(".papergutter")).toBeNull();
    expect(container.querySelector("[data-paper]")).toBeNull();
    expect(container.querySelector('[class^="rd-"], [class*=" rd-"]')).toBeNull();
    const editor = q(container, '.ed[data-revision="rev_4"]');
    expect(editor.getAttribute("contenteditable")).toBe("false");
  });

  test("the draft shows every paragraph with its kind tag and its cited figures as chips", () => {
    const { container } = mount();
    const editor = q(container, ".ed");
    for (const paragraph of report.body.paragraphs) {
      const element = q(editor, `[data-paragraph="${paragraph.id}"]`);
      expect(element).toHaveTextContent(
        paragraph.kind === "MODULE" ? `MODULE · ${paragraph.module_id}` : "ANALYST_JUDGMENT",
      );
      const cited = paragraph.figures.filter((figure) => figure.citation !== null);
      expect(element.querySelectorAll(".chip")).toHaveLength(cited.length);
      for (const figure of cited) expect(element).toHaveTextContent(figure.text);
    }
    fireEvent.click(q(editor, '[data-chip="D-04 p.68 ¶2"]'));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("D-04 · 8-K Senior Secured Notes Indenture");
    expect(dialog.querySelector("img")?.getAttribute("src")).toBe("/api/pages/D-04-p68.svg");
  });

  test("the revision list carries digests and saved times and marks the current one", () => {
    const { container } = mount();
    const items = container.querySelectorAll("[data-revision-item]");
    expect(items).toHaveLength(report.body.revisions.length);
    expect([...items].map((item) => item.getAttribute("data-revision-item"))).toEqual([
      "rev_4",
      "rev_3",
      "rev_2",
      "rev_1",
    ]);
    for (const revision of report.body.revisions) {
      const item = q(container, `[data-revision-item="${revision.id}"]`);
      expect(item).toHaveTextContent(revision.saved_at);
      expect(item).toHaveTextContent(revision.digest.slice(0, 8));
    }
    const current = q(container, '[data-revision-item="rev_4"]');
    expect(current).toHaveAttribute("aria-current", "true");
    expect(current).toHaveTextContent("DRAFT");
    expect(q(container, '[data-revision-item="rev_3"]')).toHaveTextContent("OPINION SIGNED");
  });

  test("the lineage rows name module, artifact digest and state", () => {
    const { container } = mount();
    const rows = container.querySelectorAll("[data-lineage]");
    expect(rows).toHaveLength(report.body.lineage.length);
    for (const row of report.body.lineage) {
      const element = q(container, `[data-lineage="${row.module_id}"]`);
      expect(element).toHaveTextContent(row.artifact_sha256.slice(0, 8));
      expect(element).toHaveTextContent(row.state);
      expect(element.querySelector("[title]")?.getAttribute("title")).toBe(row.artifact_sha256);
    }
    expect(q(container, '[data-lineage="CP-1C"]')).toHaveTextContent("RESTRICTED");
  });

  test("the left column lists the deliverable's sections and marks the one this revision feeds", () => {
    const { container } = mount();
    const rows = container.querySelectorAll(".secrow");
    expect(rows).toHaveLength(report.body.sections.length);
    const feeds = q(container, '.secrow[data-section-kind="NARRATIVE"]');
    expect(feeds).toHaveClass("on");
    expect(feeds).toHaveTextContent("rev_4 FEEDS");
    expect(q(container, '.secrow[data-section-kind="MODULE"]')).toHaveTextContent("CP-0");
  });

  test("the tabs switch the centre between draft, revisions and figures", () => {
    const revisions = mount("revisions");
    expect(revisions.container.querySelector(".ed")).toBeNull();
    expect(revisions.container.querySelectorAll("[data-revision-row]")).toHaveLength(4);
    expect(revisions.container.querySelector('[data-revision-row="rev_4"]')).toHaveAttribute(
      "aria-current",
      "true",
    );
    revisions.unmount();
    const figures = mount("figures");
    const rows = figures.container.querySelectorAll("[data-figure-row]");
    const total = report.body.paragraphs.reduce((n, p) => n + p.figures.length, 0);
    expect(rows).toHaveLength(total);
    expect(figures.container.querySelector('[data-figure-row="$95M"]')).toHaveTextContent(
      "UNCITED",
    );
  });

  test("segments place each figure where it sits in the sentence", () => {
    const figures = [
      { text: "$58M" },
      { text: "$1.5 billion" },
      { text: "$58M" },
      { text: "absent" },
    ];
    const out = segments("Drawn $58M of a $1.5 billion line; $58M again.", figures);
    expect(out.map((s) => s.text)).toEqual([
      "Drawn ",
      "$58M",
      " of a ",
      "$1.5 billion",
      " line; ",
      "$58M",
      " again.",
      "",
    ]);
    expect(out.filter((s) => s.figure).map((s) => s.figure?.text)).toEqual([
      "$58M",
      "$1.5 billion",
      "$58M",
      "absent",
    ]);
  });
});
