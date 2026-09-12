import { readFileSync } from "node:fs";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { DirectorySection } from "@/sections/directory/DirectorySection";
import type { DocumentOf } from "@/wire";

const load = (path: string): DocumentOf<"directory"> =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const fixture = load("../../fixtures/directory.json");
const empty = load("../../fixtures/states/directory.observed-empty.json");

function mount(document: DocumentOf<"directory">, tab: string | null = null) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <DirectorySection document={document} tab={tab} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

const rowsOf = (container: HTMLElement) =>
  Array.from(container.querySelectorAll<HTMLElement>("table.reg[data-register] tbody tr"));

describe("Directory", () => {
  test("test_register_has_one_action_per_row_and_no_batch_state", () => {
    const { container } = mount(fixture);
    expect(container.querySelector("table.reg[data-register]")).not.toBeNull();
    const rows = rowsOf(container);
    expect(rows).toHaveLength(fixture.body.cases.length);
    for (const row of rows) {
      const links = within(row).getAllByRole("link");
      expect(links).toHaveLength(1);
      expect(links[0]).toHaveTextContent("Open case");
      expect(links[0]).toHaveClass("rowact");
      expect(within(row).queryAllByRole("button")).toHaveLength(0);
    }
    // No batch state: no checkboxes, no select-all, no "n selected".
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    expect(screen.queryByText(/select all|selected/i)).toBeNull();
    const cvna = container.querySelector<HTMLElement>('tr[data-case="CASE-2026-CVNA01"]');
    expect(cvna).not.toBeNull();
    expect(within(cvna!).getByRole("link", { name: "Open case" })).toHaveAttribute(
      "href",
      "/analysis/?case=CASE-2026-CVNA01",
    );
  });

  test("search plus exactly one filter narrow the register", () => {
    const { container } = mount(fixture);
    expect(container.querySelectorAll("select")).toHaveLength(1);
    fireEvent.change(screen.getByLabelText("Search cases"), { target: { value: "hertz" } });
    expect(rowsOf(container)).toHaveLength(1);
    expect(rowsOf(container)[0]).toHaveAttribute("data-case", "CASE-2026-HTZ02");
    fireEvent.change(screen.getByLabelText("Search cases"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText(fixture.body.filter.label), {
      target: { value: "BLOCKED" },
    });
    expect(rowsOf(container)).toHaveLength(1);
    expect(rowsOf(container)[0]).toHaveAttribute("data-case", "CASE-2026-FLYYQ04");
  });

  test("state is shape and word, never hue alone", () => {
    const { container } = mount(fixture);
    const row = container.querySelector<HTMLElement>('tr[data-case="CASE-2026-HTZ02"]')!;
    expect(row.querySelector('[data-severity="WARNING"]')).toHaveAttribute(
      "data-shape",
      "triangle",
    );
    expect(row).toHaveTextContent("RESTRICTED");
    expect(row).toHaveTextContent("5.9x");
    expect(row).toHaveTextContent("2026-09-08 17:15Z");
  });

  test("test_intake_suggestions_are_labelled_until_committed", () => {
    const { container } = mount(fixture, "intake");
    const intake = container.querySelector<HTMLElement>("[data-intake]");
    expect(intake).not.toBeNull();
    const suggestions = fixture.body.intake!.suggestions;
    const open = suggestions.filter((s) => !s.committed);
    expect(intake!.querySelectorAll(".sugrow")).toHaveLength(suggestions.length);
    expect(intake!.querySelectorAll(".sug")).toHaveLength(open.length);
    for (const chip of intake!.querySelectorAll(".sug"))
      expect(chip).toHaveTextContent("SUGGESTED");
    // The one the analyst already corrected carries no SUGGESTED chip.
    const issuer = intake!.querySelector<HTMLElement>('[data-suggestion="issuer"]')!;
    expect(issuer.querySelector(".sug")).toBeNull();
    expect(issuer).toHaveTextContent("COMMITTED");
    // Committing a suggestion removes its label and refuses a second commit.
    const label = intake!.querySelector<HTMLElement>('[data-suggestion="label"]')!;
    expect(label.querySelector(".sug")).not.toBeNull();
    // Nothing in this build commits: the control is visible and refused with
    // what clears it -- true today, never a build phase -- and a click changes
    // nothing.
    const commit = within(label).getByRole("button", { name: "Commit" });
    expect(commit).toHaveAttribute("aria-disabled", "true");
    expect(commit).toHaveAttribute("data-refusal", "STORE_UNPLACED");
    expect(commit.getAttribute("title")).not.toMatch(/Phase \d|REBUILD_PLAN|backend phase/);
    fireEvent.click(commit);
    expect(label.querySelector(".sug")).not.toBeNull();
    expect(within(issuer).getByRole("button", { name: "Commit" })).toHaveAttribute(
      "data-refusal",
      "SUGGESTION_ALREADY_COMMITTED",
    );
    expect(intake!.querySelectorAll(".sug")).toHaveLength(open.length);
  });

  test("a completed intake run is opened for review, never accepted", () => {
    const { container } = mount(fixture, "intake");
    const note = container.querySelector('[data-intake-run="run_2643"]');
    expect(note).not.toBeNull();
    expect(note).toHaveTextContent(/opened for review, never accepted/);
    expect(screen.getByRole("link", { name: "Open run_2643 in Run" })).toHaveAttribute(
      "href",
      "/run/?case=CASE-2026-CVNA01",
    );
    expect(screen.queryByRole("button", { name: /accept/i })).toBeNull();
  });

  test("the intake panel posts files and nothing else", () => {
    const { container } = mount(fixture, "intake");
    const input = container.querySelector<HTMLInputElement>('.drop input[type="file"]');
    expect(input).not.toBeNull();
    expect(input!.multiple).toBe(true);
    expect(screen.getByLabelText("Drop documents for a case")).toBe(input);
    // Nothing the browser could assert: no issuer, type, period or route fields.
    expect(container.querySelectorAll(".drop select, .drop textarea")).toHaveLength(0);
    expect(container.querySelectorAll(".drop input")).toHaveLength(1);
  });

  test("chosen files are said not to be sent, beside an admit control refused with its reason", () => {
    const { container } = mount(fixture, "intake");
    const drop = container.querySelector<HTMLElement>("[data-intake-drop]")!;
    const admit = within(drop).getByRole("button", { name: "Admit pack" });
    expect(admit).toHaveAttribute("aria-disabled", "true");
    expect(admit).toHaveAttribute("data-refusal", "INTAKE_UNPLACED");
    expect(admit.getAttribute("title")).not.toMatch(/Phase \d|REBUILD_PLAN|backend phase/);
    const input = drop.querySelector<HTMLInputElement>('input[type="file"]')!;
    fireEvent.change(input, { target: { files: [new File(["a"], "a.txt")] } });
    expect(drop.querySelector("[data-selected-files]")).toHaveTextContent(
      "1 file selected · not sent",
    );
  });

  test("no row of the register is drawn selected: the register has no selection", () => {
    const { container } = mount(fixture);
    const selected = () => container.querySelectorAll("table.reg[data-register] tbody tr.on");
    expect(selected()).toHaveLength(0);
    fireEvent.change(screen.getByLabelText("Search cases"), { target: { value: "spirit" } });
    expect(selected()).toHaveLength(0);
  });

  test("an intake of one small file reads in the singular and in bytes", () => {
    const intake = fixture.body.intake!;
    const one: DocumentOf<"directory"> = {
      ...fixture,
      body: {
        ...fixture.body,
        intake: { ...intake, files: [{ name: "memo.txt", bytes: 512, sha256: "b".repeat(64) }] },
      },
    };
    const register = mount(one);
    expect(register.container.querySelector("[data-intake-open]")).toHaveTextContent(
      "1 file admitted as one pack",
    );
    register.unmount();
    const { container } = mount(one, "intake");
    expect(container.querySelector(".attlist")).toHaveTextContent("512 B");
  });

  test("a file of megabytes reads in megabytes, not thousands of kilobytes", () => {
    const intake = fixture.body.intake!;
    const large: DocumentOf<"directory"> = {
      ...fixture,
      body: {
        ...fixture.body,
        intake: {
          ...intake,
          files: [{ name: "annual-report.pdf", bytes: 5 * 1024 ** 2, sha256: "c".repeat(64) }],
        },
      },
    };
    const { container } = mount(large, "intake");
    expect(container.querySelector(".attlist")).toHaveTextContent("5.0 MB");
  });

  test("test_empty_columns_are_not_rendered", () => {
    const headersOf = (container: HTMLElement) =>
      Array.from(container.querySelectorAll("table.reg[data-register] th")).map((th) =>
        th.textContent?.trim(),
      );
    const full = mount(fixture);
    expect(headersOf(full.container)).toEqual(
      expect.arrayContaining([
        "Case",
        "Issuer",
        "Sector",
        "Rating",
        "Pathway",
        "Snapshot",
        "State",
      ]),
    );
    full.unmount();
    const blank: DocumentOf<"directory"> = {
      ...fixture,
      body: {
        ...fixture.body,
        cases: fixture.body.cases.map((row) => ({ ...row, sector: "", rating: "" })),
      },
    };
    const { container } = mount(blank);
    const headers = headersOf(container);
    expect(headers).not.toContain("Sector");
    expect(headers).not.toContain("Rating");
    expect(headers).toContain("Issuer");
    const cells = container
      .querySelector('tr[data-case="CASE-2026-CVNA01"]')!
      .querySelectorAll("td");
    expect(cells).toHaveLength(headers.length);
  });

  test("an observed-empty register renders no rows and no intake", () => {
    expect(empty.observed_empty).toBe(true);
    expect(empty.body.intake).toBeNull();
    const { container } = mount(empty);
    expect(rowsOf(container)).toHaveLength(0);
    expect(screen.getByText("No intake is open.")).toBeInTheDocument();
  });
});
