import { readFileSync } from "node:fs";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { UploadSection } from "@/sections/upload/UploadSection";
import { parseUploadDocument, type UploadDocument } from "@/wire/v1";

const load = (path: string): unknown =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));

const fixture = parseUploadDocument(load("../../fixtures/upload.json"));
const partial = parseUploadDocument(load("../../fixtures/states/upload.partial.json"));

function mount(document: UploadDocument) {
  return render(
    <MemoryRouter>
      <UploadSection document={document} tab={null} />
    </MemoryRouter>,
  );
}

const sourceRow = (container: HTMLElement, id: string) =>
  container.querySelector<HTMLElement>(`table.reg[data-source-pack] tr[data-source="${id}"]`)!;

describe("Upload", () => {
  test("test_source_rows_show_filename_digest_admitted_time_extractor_identity_and_set_versions", () => {
    const { container } = mount(fixture);
    expect(container.querySelector("table.reg[data-source-pack]")).not.toBeNull();
    expect(container.querySelectorAll("tr[data-source]")).toHaveLength(fixture.body.sources.length);
    const source = fixture.body.sources[0]!;
    const row = sourceRow(container, source.source_id);
    expect(row).toHaveTextContent(source.filename);
    expect(row).toHaveTextContent(source.extractor_identity!);
    const digest = row.querySelector("[data-digest]")!;
    expect(digest).toHaveTextContent(source.document_sha256.slice(0, 12));
    expect(digest).toHaveAttribute("title", source.document_sha256);
    const pills = Array.from(row.querySelectorAll(".pill")).map((pill) => pill.textContent);
    expect(pills).toEqual(source.set_versions.map(String));
    // No disposition tag, grade, page count, label or family on the row
    // itself: the v1 SourceRow does not carry them. (The header's own
    // "N WITHDRAWN" count is a different thing — not a per-row disposition.)
    expect(row).not.toHaveTextContent(/ADMITTED|EXCLUDED_LOW_VALUE|PENDING/);
    expect(row.querySelector(".grade")).toBeNull();
  });

  test("a null extractor identity reads as an em dash, not a blank cell", () => {
    const { container } = mount(fixture);
    const withdrawn = fixture.body.sources.find((s) => s.extractor_identity === null)!;
    const row = sourceRow(container, withdrawn.source_id);
    expect(row.querySelectorAll("td")[3]).toHaveTextContent("—");
  });

  test("test_withdrawal_is_checked_live_and_shown", () => {
    const { container } = mount(fixture);
    const live = sourceRow(container, fixture.body.sources[0]!.source_id);
    const clock = `${fixture.observed_at.slice(11, 16)}Z`;
    expect(live).toHaveTextContent(new RegExp(`checked live at ${clock}`));
    expect(live).not.toHaveClass("wd");
    const withdrawn = fixture.body.sources.find((s) => s.withdrawn_at !== null)!;
    const wd = container.querySelector<HTMLElement>("table.reg[data-source-pack] tr.wd")!;
    expect(wd).toHaveAttribute("data-source", withdrawn.source_id);
    expect(wd).toHaveTextContent("Withdrawn");
    expect(wd).toHaveTextContent(new RegExp(`checked live at ${clock}`));
  });

  test("an empty pack says the pack is empty", () => {
    const { container } = mount({ ...fixture, body: { ...fixture.body, sources: [] } });
    expect(container).toHaveTextContent("The pack holds no source.");
  });

  test("set versions show their fingerprint and member count, with no pin state", () => {
    const { container } = mount(fixture);
    const rows = container.querySelectorAll("[data-set-version]");
    expect(rows).toHaveLength(fixture.body.set_versions.length);
    const top = fixture.body.set_versions[0]!;
    const row = container.querySelector<HTMLElement>(`[data-set-version="${top.version}"]`)!;
    expect(row).toHaveTextContent(String(top.member_count));
    expect(row).toHaveTextContent(top.fingerprint.slice(0, 12));
    // No pinning affordance: 4.1 offers no actions (brief decision 5).
    expect(container.querySelectorAll("[data-set-versions] button")).toHaveLength(0);
  });

  test("a partial document with LIST_TRUNCATED still renders its sources", () => {
    expect(partial.status).toBe("partial");
    expect(partial.notes).toEqual(["LIST_TRUNCATED"]);
    const { container } = mount(partial);
    expect(container.querySelectorAll("tr[data-source]")).toHaveLength(partial.body.sources.length);
  });
});
