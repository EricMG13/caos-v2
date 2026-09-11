import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { CitationChip } from "@/evidence/CitationChip";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { MetricPassport } from "@/evidence/MetricPassport";
import { CommitteeSection } from "@/sections/committee/CommitteeSection";
import { PASSPORT_FIELDS, type Citation, type DocumentOf, type Passport } from "@/wire";

const CITATION: Citation = {
  chip: "D-04 p.68 ¶2",
  document_sha256: "a".repeat(64),
  source_label: "D-04 · 8-K Senior Secured Notes Indenture",
  page: 68,
  bboxes: [[0.085, 0.41, 0.83, 0.06]],
  matched_text:
    "the Issuer shall not permit the Consolidated Net Leverage Ratio to exceed 3.50 to 1.00",
  observed_at: "2026-09-09T14:30:00Z",
  render_url: "/api/pages/D-04-p68.svg",
};

const ACTUAL: Passport = {
  label: "Net leverage",
  value: "1.2x",
  unit: "x",
  definition: "Net debt over LTM adjusted EBITDA, per the indenture definition",
  period: "LTM to 2026-06-30",
  scenario: "Base",
  evidence_date: "2026-08-04",
  computed_at: "2026-09-09T14:30:00Z",
  snapshot: "snp_cvna_q2_2026",
  method: "leverage_ratio · verified",
  derivation: "(total_debt − cash) / ltm_adjusted_ebitda",
  citations: [CITATION],
  supporting_research: [
    { title: "CP-1 canonical data foundation", module_id: "CP-1", state: "ACCEPTED" },
  ],
  driver: null,
  deviation: null,
};

const PROJECTED: Passport = {
  ...ACTUAL,
  label: "Net leverage · FY2027 Q2",
  value: "1.4x",
  period: "FY2027 Q2",
  scenario: "Downside",
  method: "cash_flow_forecast · verified",
  derivation: "closing_debt − closing_cash / ebitda",
  driver: { name: "EBITDA margin", value: "9.1%", citation: CITATION },
};

describe("the evidence surface", () => {
  test("test_dialog_opener_is_explicit", () => {
    render(
      <EvidenceProvider>
        <button type="button">elsewhere</button>
        <CitationChip citation={CITATION} />
      </EvidenceProvider>,
    );
    const chip = screen.getByRole("button", { name: "Evidence D-04 p.68 ¶2" });
    // WebKit does not focus a button on click: focus is elsewhere when the click lands.
    screen.getByRole("button", { name: "elsewhere" }).focus();
    fireEvent.click(chip);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog.querySelector("img")).toHaveAttribute("src", "/api/pages/D-04-p68.svg");
    expect(dialog.querySelectorAll(".bbox")).toHaveLength(1);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(chip);
  });

  test("a citation of a withdrawn source is marked on the chip and in the drawer", () => {
    const withdrawn: Citation = {
      ...CITATION,
      chip: "D-06 p.1 ¶3",
      withdrawn_at: "2026-09-09T09:41:00Z",
    };
    render(
      <EvidenceProvider>
        <CitationChip citation={withdrawn} />
      </EvidenceProvider>,
    );
    const chip = screen.getByRole("button", { name: "Evidence D-06 p.1 ¶3 · source withdrawn" });
    expect(chip).toHaveClass("withdrawn");
    fireEvent.click(chip);
    const dialog = screen.getByRole("dialog");
    expect(dialog.querySelector("[data-withdrawn]")).toHaveTextContent("2026-09-09T09:41:00Z");
  });

  test("every citation of a source Upload shows withdrawn carries the withdrawal", () => {
    const fixtures = `${resolve(process.cwd(), "fixtures")}/`;
    const upload = JSON.parse(
      readFileSync(`${fixtures}upload.json`, "utf8"),
    ) as DocumentOf<"upload">;
    const withdrawn = new Map(
      upload.body.sources
        .filter((source) => source.withdrawn_at !== null)
        .map((source) => [source.source_id, source.withdrawn_at]),
    );
    expect(withdrawn.size).toBeGreaterThan(0);
    const files = [
      ...readdirSync(fixtures).filter((name) => name.endsWith(".json")),
      ...readdirSync(`${fixtures}states`).map((name) => `states/${name}`),
    ];
    let checked = 0;
    const walk = (value: unknown): void => {
      if (Array.isArray(value)) return value.forEach(walk);
      if (typeof value !== "object" || value === null) return;
      const record = value as Record<string, unknown>;
      if (typeof record["chip"] === "string" && Array.isArray(record["bboxes"])) {
        const source = (record["chip"] as string).split(" ")[0]!;
        if (withdrawn.has(source)) {
          expect(record["withdrawn_at"], `${record["chip"]}`).toBe(withdrawn.get(source));
          checked += 1;
        }
      }
      Object.values(record).forEach(walk);
    };
    for (const name of files) walk(JSON.parse(readFileSync(`${fixtures}${name}`, "utf8")));
    expect(checked).toBeGreaterThan(0);
  });

  test("the committee paper marks a figure whose source has been withdrawn", () => {
    const committee = JSON.parse(
      readFileSync(`${resolve(process.cwd(), "fixtures")}/committee.json`, "utf8"),
    ) as DocumentOf<"committee">;
    const { container } = render(
      <MemoryRouter>
        <EvidenceProvider>
          <CommitteeSection document={committee} tab={null} />
        </EvidenceProvider>
      </MemoryRouter>,
    );
    const cite = container.querySelector<HTMLElement>('.rd-cite[data-chip^="D-06"]');
    expect(cite).toHaveClass("withdrawn");
    expect(cite).toHaveAccessibleName(/source withdrawn$/);
  });

  test("test_passport_contract", () => {
    for (const passport of [ACTUAL, PROJECTED]) {
      const { unmount } = render(
        <EvidenceProvider>
          <MetricPassport passport={passport} opener={null} onClose={() => {}} />
        </EvidenceProvider>,
      );
      const fields = [...document.querySelectorAll("[data-passport] > [data-passport-field]")].map(
        (el) => el.getAttribute("data-passport-field"),
      );
      for (const field of PASSPORT_FIELDS) expect(fields).toContain(field);
      expect(
        fields.filter((f) => (PASSPORT_FIELDS as readonly string[]).includes(f!)),
      ).toHaveLength(10);
      expect(screen.getByText("Supporting research")).toBeInTheDocument();
      const chips = screen.getAllByRole("button", { name: "Evidence D-04 p.68 ¶2" });
      if (passport.driver) {
        expect(fields).toContain("driver");
        expect(screen.getByText(/EBITDA margin/)).toBeInTheDocument();
        expect(chips).toHaveLength(2);
      } else {
        expect(chips).toHaveLength(1);
        expect(fields).not.toContain("driver");
      }
      unmount();
    }
  });
});
