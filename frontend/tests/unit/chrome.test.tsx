import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Rail } from "@/chrome/Rail";
import { Ribbon } from "@/chrome/Ribbon";
import { SeverityMark } from "@/chrome/SeverityMark";
import { VerdictStrip } from "@/chrome/VerdictStrip";
import { SECTIONS, type AnyDocument, type Severity } from "@/wire";

const FIXTURES = `${resolve(process.cwd(), "fixtures")}/`;
const documents = (): [string, AnyDocument][] =>
  [
    ...SECTIONS.map((section) => `${section}.json`),
    ...readdirSync(`${FIXTURES}states`).map((name) => `states/${name}`),
  ].map((name) => [name, JSON.parse(readFileSync(`${FIXTURES}${name}`, "utf8"))]);

describe("the chrome", () => {
  test("test_rail_lists_nine_sections_with_state_lines", () => {
    const [, doc] = documents()[0]!;
    render(
      <MemoryRouter>
        <Rail
          section="analysis"
          entries={doc.chrome.rail}
          local={null}
          servedRole={doc.chrome.served_role}
          search=""
        />
      </MemoryRouter>,
    );
    const nav = screen.getByRole("navigation", { name: "Workspace" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("data-section"))).toEqual([...SECTIONS]);
    for (const entry of doc.chrome.rail) {
      expect(within(nav).getByText(entry.state)).toBeInTheDocument();
    }
    // The served role is read-only: not a control.
    const role = nav.querySelector("[data-served-role]")!;
    expect(role.querySelector("button, a, select, input")).toBeNull();
    // Two foot controls and no more.
    expect(nav.querySelectorAll(".railfoot button")).toHaveLength(2);
  });

  test("test_ribbon_has_exactly_one_primary_action", () => {
    for (const [name, doc] of documents()) {
      const { unmount } = render(
        <Ribbon ribbon={doc.chrome.ribbon} subject={doc.chrome.subject} />,
      );
      const banner = screen.getByRole("banner");
      expect(banner.querySelectorAll("[data-primary]"), name).toHaveLength(1);
      expect(doc.chrome.ribbon.actions.length, name).toBeLessThanOrEqual(3);
      expect(
        doc.chrome.ribbon.actions.filter((a) => a.primary),
        name,
      ).toHaveLength(1);
      unmount();
    }
  });

  test("test_severity_renders_shape_and_hue", () => {
    const expected: Record<Severity, [string, string]> = {
      SUCCESS: ["ok", "disc"],
      RUNNING: ["run", "disc"],
      WARNING: ["warn", "triangle"],
      CRITICAL: ["crit", "rounded-square"],
      IDLE: ["idle", "flat-dot"],
    };
    for (const [severity, [hue, shape]] of Object.entries(expected) as [
      Severity,
      [string, string],
    ][]) {
      const { unmount } = render(<SeverityMark severity={severity} />);
      const mark = screen.getByRole("img", { name: severity });
      expect(mark).toHaveClass("glyph", hue);
      expect(mark).toHaveAttribute("data-shape", shape);
      unmount();
    }
    render(
      <VerdictStrip
        verdict={{ severity: "WARNING", conclusion: "Conditional", blocked_on: "CP-6" }}
      />,
    );
    expect(screen.getByLabelText("Verdict")).toHaveClass("verdict", "warn");
    expect(screen.getByLabelText("Verdict")).toHaveTextContent("blocked on CP-6");
  });
});
