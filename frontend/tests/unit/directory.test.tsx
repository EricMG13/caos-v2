import { readFileSync } from "node:fs";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { DirectorySection } from "@/sections/directory/DirectorySection";
import { parseDirectoryDocument, parseUploadDocument, type DirectoryDocument } from "@/wire/v1";

const load = (path: string): unknown =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));

const fixture = parseDirectoryDocument(load("../../fixtures/directory.json"));
const empty = parseDirectoryDocument(load("../../fixtures/states/directory.observed-empty.json"));

function mount(document: DirectoryDocument) {
  return render(
    <MemoryRouter>
      <DirectorySection document={document} tab={null} />
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
    const first = fixture.body.cases[0]!;
    const row = container.querySelector<HTMLElement>(`tr[data-case="${first.case_id}"]`);
    expect(row).not.toBeNull();
    expect(within(row!).getByRole("link", { name: "Open case" })).toHaveAttribute(
      "href",
      `/analysis/?case=${first.case_id}`,
    );
  });

  test("test_directory_draws_no_sector_rating_or_leverage", () => {
    const { container } = mount(fixture);
    const text = container.textContent ?? "";
    // Neither the dropped columns' headers nor any of the legacy sample
    // values they used to carry (issuer sector, rating, net leverage,
    // pathway or snapshot) reach the page — the v1 CaseRow does not carry
    // them, so nothing here can fake them.
    expect(screen.queryByText("Sector")).toBeNull();
    expect(screen.queryByText("Rating")).toBeNull();
    expect(screen.queryByText("Pathway")).toBeNull();
    expect(screen.queryByText("Snapshot")).toBeNull();
    expect(text).not.toMatch(/Automotive Retail|Car Rental|Telecommunications/);
    expect(text).not.toMatch(/B3 \/ B-|B2 \/ B|Ba1 \/ BB\+/);
    // Net leverage read "5.9x"; nothing on the v1 CaseRow carries a ratio.
    expect(text).not.toMatch(/\d+\.\d+x/);
  });

  test("every case row draws its title, created time, standing, live sources and latest run", () => {
    const { container } = mount(fixture);
    const row = fixture.body.cases[0]!;
    const tr = container.querySelector<HTMLElement>(`tr[data-case="${row.case_id}"]`)!;
    expect(tr).toHaveTextContent(row.title);
    expect(tr).toHaveTextContent(row.standing);
    expect(tr).toHaveTextContent(String(row.live_sources));
    expect(tr).toHaveTextContent(row.latest_run!.status);
    expect(tr).toHaveTextContent(row.latest_run!.profile_id!);
    expect(tr).toHaveTextContent(row.latest_run!.selection_id!);
    expect(tr.querySelector("time")).toHaveAttribute("dateTime", row.created_at);
  });

  test("a case with no run yet reads 'No runs yet' rather than a blank cell", () => {
    const one: DirectoryDocument = {
      ...fixture,
      body: {
        cases: [{ ...fixture.body.cases[0]!, latest_run: null }],
      },
    };
    const { container } = mount(one);
    const row = container.querySelector<HTMLElement>(
      `tr[data-case="${one.body.cases[0]!.case_id}"]`,
    )!;
    expect(row).toHaveTextContent("No runs yet");
  });

  test("an observed-empty register renders no rows", () => {
    expect(empty.observed_empty).toBe(true);
    expect(empty.body.cases).toHaveLength(0);
    const { container } = mount(empty);
    expect(rowsOf(container)).toHaveLength(0);
    expect(container).toHaveTextContent("No case matches.");
  });

  test("test_every_enabled_demo_fixture_is_a_valid_v1_document", () => {
    const directoryFixtures = [
      "../../fixtures/directory.json",
      "../../fixtures/states/directory.observed-empty.json",
    ];
    for (const path of directoryFixtures) {
      expect(() => parseDirectoryDocument(load(path))).not.toThrow();
    }
    const uploadFixtures = [
      "../../fixtures/upload.json",
      "../../fixtures/states/upload.partial.json",
    ];
    for (const path of uploadFixtures) {
      expect(() => parseUploadDocument(load(path))).not.toThrow();
    }
  });
});
