import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render } from "@testing-library/react";
import { ReportSection } from "@/sections/report/ReportSection";
import { segments } from "@/sections/report/text";
import { parseReportDocument } from "@/wire/v1";

const report = () =>
  parseReportDocument(
    JSON.parse(readFileSync(resolve(process.cwd(), "fixtures/report-v1.json"), "utf8")),
  );

describe("Report v1", () => {
  test("segments keeps the shared Committee text helper covered", () => {
    expect(segments("source text", [{ text: "text" }])).toEqual([
      { text: "source ", figure: null, placed: true },
      { text: "text", figure: { text: "text" }, placed: true },
    ]);
  });

  test("renders only the exact saved payload as escaped read-only text", () => {
    const document = report();
    const hostile = '<img src=x onerror="window.pwned=1">';
    const { container } = render(<ReportSection document={document} tab={null} />);

    const root = container.querySelector("[data-report-v1]")!;
    expect(root).toHaveAttribute("data-revision", document.body.revision_id);
    expect(root).toHaveAttribute("data-payload", document.body.payload_sha256);
    expect(root).toHaveTextContent(hostile);
    expect(
      root.querySelector("img, script, a, button, input, textarea, [contenteditable]"),
    ).toBeNull();
    expect(root).toHaveTextContent(document.body.artifacts[0]!.record);
    expect(root).toHaveTextContent(document.body.narrative[0]![1]!.figure!.matched_text);
    expect(root.querySelectorAll("[data-report-artifact]")).toHaveLength(
      document.body.artifacts.length,
    );
  });
});
