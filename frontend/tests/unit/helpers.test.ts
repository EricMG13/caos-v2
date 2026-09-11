// The pure helpers each section exports. Reached by import rather than by
// rendering, which is why `frontend/scripts/check-tested.mjs` asks for them by
// name and why the section-level tests beside this file did not cover them:
// rendering a section exercises a helper without ever naming it, so a helper
// that quietly returned the wrong thing would still leave the section green.
import { sectionPath } from "@/app/sections";
import { EVENT_NAMES, eventsUrl } from "@/app/sse";
import { OFFLINE_WORDING, UNAVAILABLE_WORDING } from "@/app/transport";
import { toneOf } from "@/chrome/SeverityMark";
import { fallbackChrome } from "@/chrome/fallback";
import { refusalText } from "@/controls/RefusedControl";
import { SEV_COLOR, sevSurface, sevVar } from "@/ds/sev";
import { NODE_SEVERITY, confidenceTier, nodeTone } from "@/sections/analysis/tone";
import { stepLabel } from "@/sections/committee/FilingLadder";
import { caseHref, filledColumns } from "@/sections/directory/CaseRegister";
import { figureCounts, isUncited, kindLabel } from "@/sections/report/RevisionEditor";
import { shortDigest } from "@/sections/report/text";
import { nodeAccept } from "@/sections/run/NodeDetail";
import { severityOf } from "@/sections/run/RouteGraph";
import { clock, withdrawRefusal } from "@/sections/upload/SourcePack";
import { CHROME_KEYS, REQUIRED_KEYS } from "@/wire/keys";
import type { CaseRow } from "@/wire/directory";
import type { LadderStep } from "@/wire/committee";
import type { Figure, Paragraph } from "@/wire/report";
import type { SourceRow } from "@/wire/upload";

describe("severity is shape and hue, never hue alone", () => {
  test("every severity carries a class, and the four node states map onto them", () => {
    expect(toneOf("CRITICAL")).toBe("crit");
    expect(toneOf("IDLE")).toBe("idle");
    // The bundle's four, each read through a severity shape (DESIGN.md).
    expect(Object.keys(NODE_SEVERITY)).toEqual(["COMPLETE", "RUNNABLE", "RESTRICTED", "BLOCKED"]);
    expect(nodeTone("BLOCKED")).toBe("crit");
    expect(nodeTone("COMPLETE")).toBe("ok");
  });

  test("an unknown severity token falls back to idle rather than to nothing", () => {
    expect(sevVar("critical")).toBe(SEV_COLOR.critical);
    expect(sevVar("not-a-severity")).toBe("var(--caos-idle)");
  });

  test("a tinted surface mixes the severity colour and keeps it as the text colour", () => {
    const surface = sevSurface("warning", { border: 40, wash: 12 });
    expect(surface.color).toBe(SEV_COLOR.warning);
    expect(surface.borderColor).toContain("40%");
    expect(surface.background).toContain("12%");
  });

  test("a RUNNABLE node is only RUNNING while it is actually running", () => {
    expect(severityOf({ state: "RUNNABLE", running: true })).toBe("RUNNING");
    expect(severityOf({ state: "RUNNABLE", running: false })).toBe("IDLE");
    expect(severityOf({ state: "BLOCKED", running: false })).toBe("CRITICAL");
  });

  test("a confidence tier is the number's band, at its boundaries", () => {
    expect(confidenceTier(85).word).toBe("HIGH");
    expect(confidenceTier(84).word).toBe("MEDIUM");
    expect(confidenceTier(60).word).toBe("MEDIUM");
    expect(confidenceTier(59).word).toBe("LOW");
  });
});

describe("the wire contract and the states around it", () => {
  test("the pinned key sets are what classify() measures a document against", () => {
    expect(REQUIRED_KEYS).toEqual(["chrome", "body", "observed_at"]);
    expect(CHROME_KEYS).toContain("served_role");
    // Every required key is also pinned; the reverse is not true.
    expect(CHROME_KEYS.length).toBeGreaterThan(REQUIRED_KEYS.length);
  });

  test("offline and unavailable are one sentence each, and never the same one", () => {
    expect(OFFLINE_WORDING).not.toBe(UNAVAILABLE_WORDING);
    expect(OFFLINE_WORDING).not.toMatch(/error|exception|stack/i);
  });

  test("a refusal reads as its code and what clears it", () => {
    expect(refusalText({ code: "SOURCE_ALREADY_WITHDRAWN", clears: "it is re-admitted" })).toBe(
      "SOURCE_ALREADY_WITHDRAWN — clears when it is re-admitted",
    );
  });

  test("fallback chrome carries the state and invents no subject, action or role", () => {
    const offline = fallbackChrome({ kind: "offline" });
    expect(offline.verdict.conclusion).toBe("Offline");
    expect(offline.verdict.severity).toBe("CRITICAL");
    expect(offline.ribbon.actions).toEqual([]);
    expect(offline.ribbon.execution).toBe("—");
    expect(offline.brief.change).toBe("Nothing observed.");

    const refused = fallbackChrome({
      kind: "error",
      refusal: { code: "WIRE_KEYS_MISMATCH", clears: "the document carries the pinned keys" },
    });
    expect(refused.ribbon.chips[0]?.label).toBe("WIRE_KEYS_MISMATCH");
    expect(refused.brief.action).toContain("the document carries the pinned keys");
  });
});

describe("navigation and the event tail", () => {
  test("a section path is the slug with its trailing slash", () => {
    expect(sectionPath("directory")).toBe("/directory/");
    expect(sectionPath("committee")).toBe("/committee/");
  });

  test("the tail url carries the case and the fixture, and neither when absent", () => {
    expect(eventsUrl(null, null)).toBe("/api/events");
    expect(eventsUrl("CASE-2026-CVNA01", null)).toBe("/api/events?case=CASE-2026-CVNA01");
    expect(eventsUrl(null, "gate")).toBe("/api/events?fixture=gate");
  });

  test("the six event names are the whole set the client listens for", () => {
    // Name-only: the client reads the name and refetches, never a payload.
    expect(EVENT_NAMES).toEqual([
      "node_state_changed",
      "attempt_recorded",
      "gate_opened",
      "run_terminal",
      "source_withdrawn",
      "authority_changed",
    ]);
  });
});

describe("the helpers a section reads its own rows with", () => {
  // Every column `COLUMNS` names, empty, so a test can fill exactly one.
  const row = (over: Partial<CaseRow> = {}): CaseRow =>
    ({
      case_id: "",
      issuer: "",
      sector: "",
      rating: "",
      pathway: "",
      snapshot: "",
      state: "",
      severity: "IDLE",
      net_leverage: "",
      updated_at: "",
      standing: "READER",
      ...over,
    }) as CaseRow;

  test("a column no row fills is not rendered", () => {
    const columns = filledColumns([row({ issuer: "Acme" })]);
    const keys = columns.map((column) => column.key);
    expect(keys).toContain("issuer");
    expect(keys).not.toContain("sector");
    // Whitespace is not a filled cell.
    expect(filledColumns([row({ issuer: "   " })]).map((c) => c.key)).not.toContain("issuer");
  });

  test("a case opens in Analysis, with its id escaped", () => {
    expect(caseHref("CASE/2026")).toBe("/analysis/?case=CASE%2F2026");
  });

  test("a digest is elided in the middle, and a short one is left alone", () => {
    expect(shortDigest("0b582ff0aaaaaaaaaaaaaaaa30df")).toBe("0b582ff0…30df");
    expect(shortDigest("0b582ff0")).toBe("0b582ff0");
  });

  test("the clock part of a stamp is the hours and minutes, marked UTC", () => {
    expect(clock("2026-09-09T14:30:00Z")).toBe("14:30Z");
  });

  test("a filing step reads as what it is, done or pending", () => {
    const step = (state: LadderStep["state"]): LadderStep => ({
      key: "opinion",
      state,
      actor: "—",
      title: "Opinion",
      detail: "",
      at: null,
      refusal: null,
    });
    expect(stepLabel(step("done"))).not.toBe("PENDING");
    expect(stepLabel(step("ref"))).toBe("REFUSED");
    expect(stepLabel(step("todo"))).toBe("PENDING");
    expect(stepLabel(step("cur"))).toBe("CURRENT");
  });
});

describe("what the report section refuses by name", () => {
  const figure = (citation: unknown): Figure => ({ citation }) as Figure;
  const paragraph = (over: Partial<Paragraph>): Paragraph =>
    ({ kind: "MODULE", figures: [], ...over }) as Paragraph;

  test("a module paragraph names its module; a judgment names itself", () => {
    expect(kindLabel(paragraph({ kind: "MODULE", module_id: "CP-1" }))).toBe("MODULE · CP-1");
    expect(kindLabel(paragraph({ kind: "MODULE", module_id: undefined }))).toBe("MODULE · —");
    expect(kindLabel(paragraph({ kind: "ANALYST_JUDGMENT" }))).toBe("ANALYST_JUDGMENT");
  });

  test("only a judgment can assert an uncited figure — what freeze refuses", () => {
    expect(isUncited(paragraph({ kind: "ANALYST_JUDGMENT" }), figure(null))).toBe(true);
    // A module figure with no citation is the envelope's problem, not this one's.
    expect(isUncited(paragraph({ kind: "MODULE" }), figure(null))).toBe(false);
    expect(isUncited(paragraph({ kind: "ANALYST_JUDGMENT" }), figure({}))).toBe(false);
  });

  test("the counter counts every figure and the uncited among them", () => {
    expect(
      figureCounts([
        paragraph({ kind: "ANALYST_JUDGMENT", figures: [figure(null), figure({})] }),
        paragraph({ kind: "MODULE", figures: [figure(null)] }),
      ]),
    ).toEqual({ total: 3, uncited: 1 });
  });
});

describe("the actions a run and an upload refuse", () => {
  test("a node that is not COMPLETE cannot be accepted, and says which state it is in", () => {
    expect(nodeAccept({ state: "COMPLETE" } as never)).toBeNull();
    const refusal = nodeAccept({
      state: "BLOCKED",
      module_id: "CP-4",
      reason: "waiting on CP-1",
    } as never);
    expect(refusal?.code).toBe("NODE_NOT_ACCEPTABLE");
    expect(refusal?.clears).toContain("CP-4");
    expect(refusal?.clears).toContain("waiting on CP-1");
  });

  test("a source already withdrawn refuses a second withdrawal, by either mark", () => {
    const source = (over: Partial<SourceRow>): SourceRow =>
      ({ source_id: "SRC-1", disposition: "ADMITTED", withdrawn_at: null, ...over }) as SourceRow;
    expect(withdrawRefusal(source({}))).toBeNull();
    expect(withdrawRefusal(source({ withdrawn_at: "2026-09-09T14:30:00Z" }))?.code).toBe(
      "SOURCE_ALREADY_WITHDRAWN",
    );
    expect(withdrawRefusal(source({ disposition: "WITHDRAWN" }))?.code).toBe(
      "SOURCE_ALREADY_WITHDRAWN",
    );
  });
});
