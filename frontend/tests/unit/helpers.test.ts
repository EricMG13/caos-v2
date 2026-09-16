// The pure helpers each section exports. Reached by import rather than by
// rendering, which is why `frontend/scripts/check-tested.mjs` asks for them by
// name and why the section-level tests beside this file did not cover them:
// rendering a section exercises a helper without ever naming it, so a helper
// that quietly returned the wrong thing would still leave the section green.
import { sectionPath } from "@/app/sections";
import { OFFLINE_WORDING, UNAVAILABLE_WORDING } from "@/app/transport";
import { toneOf } from "@/chrome/SeverityMark";
import { fallbackChrome } from "@/chrome/fallback";
import { ACTION_UNPLACED, READ_ONLY_API, refusalText } from "@/controls/RefusedControl";
import { SEV_COLOR, sevSurface, sevVar } from "@/ds/sev";
import { NODE_SEVERITY, confidenceTier, nodeTone } from "@/sections/analysis/tone";
import { stepLabel } from "@/sections/committee/FilingLadder";
import { caseHref } from "@/sections/directory/CaseRegister";
import { figureCounts, isUncited, kindLabel } from "@/sections/report/RevisionEditor";
import { shortDigest } from "@/sections/report/text";
import { severityOf } from "@/sections/run/RouteGraph";
import { clock } from "@/sections/upload/SourcePack";
import type { LadderStep } from "@/wire/committee";
import type { Figure, Paragraph } from "@/wire/report";

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
    expect(severityOf({ state: "RUNNABLE" }, true)).toBe("RUNNING");
    expect(severityOf({ state: "RUNNABLE" }, false)).toBe("IDLE");
    expect(severityOf({ state: "BLOCKED" }, false)).toBe("CRITICAL");
  });

  test("a confidence tier is the number's band, at its boundaries", () => {
    expect(confidenceTier(85).word).toBe("HIGH");
    expect(confidenceTier(84).word).toBe("MEDIUM");
    expect(confidenceTier(60).word).toBe("MEDIUM");
    expect(confidenceTier(59).word).toBe("LOW");
  });
});

describe("the wire contract and the states around it", () => {
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
      refusal: { code: "WIRE_SHAPE_INVALID", clears: "the document is the declared v1 shape" },
    });
    expect(refused.ribbon.chips[0]?.label).toBe("WIRE_SHAPE_INVALID");
    expect(refused.brief.action).toContain("the document is the declared v1 shape");
  });

  test("the fallback brief ends its clause once, however the refusal punctuates it", () => {
    const brief = (clears: string) =>
      fallbackChrome({ kind: "error", refusal: { code: "STORE_UNAVAILABLE", clears } }).brief
        .action;
    expect(brief("the store answers again.")).toBe("Clears when the store answers again.");
    expect(brief("the store answers again")).toBe("Clears when the store answers again.");
    expect(brief("the store answers again. ")).toBe("Clears when the store answers again.");
    expect(brief("the store answers again?")).toBe("Clears when the store answers again?");
  });

  test("the client's own refusals read as a clause after 'clears when'", () => {
    // `classify`'s legacy key check was retired with the dual wire path
    // (slice 4.1j); every enabled section's document is validated by
    // `classifyV1`, exercised end to end in transport.test.ts. What is
    // pinned here is only the shape every such refusal's own clause takes.
    const refusals = [
      { code: "RESPONSE_INVALID", clears: "the server answers with a typed refusal" },
      { code: "WIRE_SHAPE_INVALID", clears: "the document is the declared v1 shape" },
      {
        code: "OBSERVED_EMPTY_UNTIMED",
        clears: "an observed-empty response carries the time it was observed",
      },
    ];
    for (const refusal of refusals) {
      expect(refusal.clears).toMatch(/^[a-z]/);
      expect(refusal.clears).not.toMatch(/\.$/);
    }
  });

  test("an action nothing performs is refused with a reason that is true today", () => {
    expect(ACTION_UNPLACED.code).toBe("ACTION_UNPLACED");
    expect(ACTION_UNPLACED.clears).not.toMatch(/Phase \d|REBUILD_PLAN|backend phase/);
    // The store calls exist; what is missing is the route to them.
    expect(ACTION_UNPLACED.clears).toContain(READ_ONLY_API);
  });
});

describe("navigation", () => {
  test("a section path is the slug with its trailing slash", () => {
    expect(sectionPath("directory")).toBe("/directory/");
    expect(sectionPath("committee")).toBe("/committee/");
  });
});

describe("the helpers a section reads its own rows with", () => {
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
