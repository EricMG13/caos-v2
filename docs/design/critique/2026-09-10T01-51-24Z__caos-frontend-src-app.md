---
target: caos/frontend/src/app — the pre-v2 CAOS frontend, nine v2-mapped routes
total_score: 26
max_score: 40
na_heuristics:
p0_count: 2
p1_count: 2
timestamp: 2026-09-10T01-51-24Z
slug: caos-frontend-src-app
---
# Design critique — `caos/frontend/src/app` (the pre-v2 CAOS frontend, all nine v2-mapped routes)

Method: dual-agent (A: general-purpose design review · B: general-purpose detector + browser evidence, isolated; A finished before B's findings entered the synthesis)

**Provenance.** `/Users/ericguei/Claude/Projects/Credit Operating System` @ `f454c654f` (`Alpha/Final`), dirty working tree 967 entries at scan time; `caos/frontend` = caos-frontend 2.0.0, static export rebuilt 2026-09-10 00:54 and served by the FastAPI server at `127.0.0.1:8000` (SQLite, no provider keys used; the server was started for this critique and stopped afterwards). Both assessments browsed read-only: nothing was run, uploaded, dispatched or generated; no analyst profile was created (the server admitted a local non-profile identity). The clone was not edited. This report is the input to CAOS v2's design brief (`docs/design/BRIEF.md`); the old frontend is being replaced, not polished, so no score threshold applies.


## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Strong ladder (`CompletionStateSummary`, `SurfaceState`, `as of` stamps). But `/settings/` sits on **"ANALYSIS CONTEXT · RESOLVING"** forever with `aria-busy="true"`: `AnalysisContextStrip.tsx` tests `pathname === "/settings"` while `next.config.js` sets `trailingSlash: true`. IC Book header count flips 0 → "1 agenda items" during load. |
| 2 | Match between system and real world | 2 | Internal codes are the user-facing language: tags `CP-RENDER`, `CP-PORT`, `IC`, `CP-0 · L0`; badges `MODEL M-118`, `RUN #2641`. `/upload/` context strip names the credit view by raw UUID (`Credit view a71f0000-0000-…`). Deep-Dive titles the page by the *tranche* (`2L TL '31 — new issue review`, `dealLabel`) not the issuer. Owner renders as `Owner local-de` (`ICBookWorkbench.tsx:1170` slices the id to 8 chars). |
| 3 | User control and freedom | 3 | Armed two-step actions (sign-out, restore checkpoint, finalize), Escape + focus-return in `MoreDrawer`, unsaved-model navigation guard. No way back from a batch `Run pipeline (n)` once confirmed beyond the per-row outcome list. |
| 4 | Consistency and standards | 2 | One object, three names on `/issuers/`: "Issuer register" (header), "Coverage register · SHARED WORKLIST" (toolbar), "Issuer Register · coverage universe" (panel). `USA` and `United States` in the same column. Action casing is three-way: `+ NEW ISSUER`, `Upload documents`, `⋯ Directory utilities`. Two class families for one thing (`caos-action-primary` / `caos-primary-action`). IC Book meeting time printed twice in two formats (`29 Jul 2026, 15:00 · 2026-07-29 14:00 UTC`). Two effort scales for one concept in Settings (`Test/Lite/Balanced/Max` vs `Max/Standard/Lite`). |
| 5 | Error prevention | 3 | The `Button`→`ActionReason` contract (never native `disabled`, always a reason) is the best thing in the codebase; batch confirmation says "This can consume external model capacity"; finalize copy names everything it locks. Against it: `/upload/` lets the browser declare **Origin = LIVE** and **Method = REPORTED** by dropdown before anything is checked; `GENERATE CITED BRIEF` (Command, Portfolio Lab) is a spend with no cost statement. |
| 6 | Recognition rather than recall | 2 | The Decision brief is **collapsed by default** on Deep-Dive, Model and IC Book (`defaultOpen={false}`), and the Source Register / Evidence Trace pane is collapsed to a vertical tab on Deep-Dive in the default Analyst view — the two things the analyst must recognise are the two things hidden. Hotkeys live in dismissable `TIP` banners (`Alt — ,/. cycle modules, C collapse panes, K Ask`, `⌘M`, `F2`). Compact nav (<1280px) is icon-only with tooltips. |
| 7 | Flexibility and efficiency of use | 4 | ⌘K palette, `Alt+←/→` concept cycle, `Alt+K` Ask, arrow-key worksheet with Enter/Escape release, `F2` row actions, per-column sort+filter, batch bar, Summary/Report/Dense layouts, role-view presets persisted server-side. Genuinely power-user grade. |
| 8 | Aesthetic and minimalist design | 1 | Header overload clips the identity on 6/10 routes (see §2). Command's Decision brief repeats `as of …` and 3–4 authority chips in each of four cells. Pipeline renders the dependency map **and** a STAGE/MODULE/STATE table of the same 27 modules side by side, and offers `DOCUMENT INTAKE` (header) and `START DOCUMENT INTAKE` (body) on one screen. `TIP` banners on three routes. Daily Digest column squeezed to ~100px so issuer names collapse to `A. never run`, `C. never run`. |
| 9 | Help users recognise, diagnose, recover | 3 | `SurfaceState` carries detail + retry; `✗ SAVED ELSEWHERE · RELOAD`; the publish ladder names the missing rung ("Save an immutable Model checkpoint before publishing."). But Portfolio Lab prints **`undefined · undefined`** for Authority and a raw 64×`3` `source_fingerprint` in a `<code>` (`PortfolioLabWorkbench.tsx:701,711`); error copy leaks engine names ("Autonomy engine unreachable"). |
| 10 | Help and documentation | 3 | Tooltips on nearly every control, table/grid keyboard instructions, env-var hints per setting, `ShortcutHelp`. No glossary anywhere for `CP-*`, `E-xx`, `D-04 p.68`, `QA-117`, `MNPI`, `WARF`, `DM`, `■`/`▲`. |
| | **Total** | **26 / 40** | **Band: competent but strained (65%)** — the primitives are right; the composition defeats them. |

---

## Design Specificity Verdict

### LLM assessment (Assessment A)

**Authored for this product — in the bodies. Category-interchangeable — in the chrome. And the chrome is winning.**

The parts that could only belong to a leveraged-finance credit desk are real and strong: the CP-code route taxonomy, `E-xx` evidence chips that carry a QA flag (`E-44 ⚠`), the Bull / Bear / Chair debate with an evidence-weighting matrix (`components/deepdive/tabs.tsx`), the formula bar that decodes a selected cell into definition, derivation, compliance-cert tie-out and a named gap (`components/model/ModelSheet.tsx` `FormulaBar`), the `BUILT FROM` manifest chips, authority chips (`LIVE · UNKNOWN · DERIVED · UNRATIFIED`), the paper inversion for the deliverable, tranche hues. Coherent palette (`--caos-*`), one sans + one mono, glyph-plus-hue status. This is a product with a point of view.

But every one of those moments sits under an identical 3-band header (`SubHeader` → `AnalysisContextStrip` → `WorkbenchToolbar`/`PersonaWorkbench`) that was designed as a contract (`identity … ≤5 contextual … one primary`) and is broken by its own routes: on **6 of the 10 routes at 1440×900 the identity band clips or loses the page title** (Upload "…source readin…", Deep-Dive "2L TL '31 …", Command "Command Center — GDPR P…", Model "Atlas Forg…" + badge "DEM", Pipeline shows only "PIPE", Report Studio shows no title at all). Structural sameness where it costs (the header) and structural divergence where it should be uniform: `.portfolio-lab` (88 CSS rules) and `.ic-book` (53) ship their own panel headers, buttons and disabled styling instead of `Panel`/`Button`.

Missed opportunities for character: the one display-scale moment in the product (`CONSTRUCTIVE`, IC Verdict) is a green headline in a right-hand column; the deliverable — the reason the product exists — renders at 81% with a `△ BELOW PROOFING SIZE` warning on a 1440 screen; the Book (Portfolio Lab) has no idiom of its own at all — generic filter row, empty chart, and a raw 64-character fingerprint.

---

### Deterministic scan (Assessment B)

`detect.mjs --json` over `src/app` and ten `src/components/*` groups: **exit 0, zero findings** across **293 scannable files** (71 tsx / 5 ts / 1 css in `app`; 112 in `shared`; 25 `deepdive`; 20 `model`; 5 `pipeline`; 4 `decisions`; 11 `upload`; 17 `command`; 4 `portfolio`; 16 `reports`; 2 `settings`), with and without the project config; `.impeccable/config.json` carries no ignore rules and the tree has no inline waivers. The clean result is real, not vacuous: a scratch fixture with Inter, gradient text, a glow shadow and bounce easing produced exit 2 with seven findings from the same binary. Model-only scan (`src/app/model` + `src/components/model`): zero findings. No false positives to record.

### Visual overlays

None. On all five injected routes (`/deepdive/`, `/model/`, `/pipeline/`, `/decisions/`, `/upload/`) the page's own Content Security Policy (`caos/server/main.py:296-316`: `script-src 'self'` plus 67 hashes, no `unsafe-inline`, no localhost allowance) blocked both the inline preflight script and `http://localhost:8400/detect.js`; `securitypolicyviolation` events were captured on every route and the `impeccable` console channel stayed empty. This is the server's policy, not a tooling fault — and, noted for v2, it is the right policy. Fallback evidence: one screenshot per route from the served static export (Deep-Dive three-pane debate in reference mode; Model M-118 grid with selected cell Q43; Pipeline reference plan with every status tile `N/A`; IC Book with one agenda row; Document Intake step rail with the 37-issuer picker).

### Where the two assessments meet

They agree by absence: the detector measures anti-pattern *decoration* (fonts, gradients, glow, easing, card clichés) and found none, which matches the design review's verdict that the palette, type and status grammar are coherent and product-specific. Everything the review scored down is *composition and truth* — a clipped identity band, collapsed evidence and brief, a lying reference marker, unguarded objects on the Book, analyst-declared authority on Upload — which no static detector measures. The detector caught nothing the review missed.


## Overall Impression

The bodies are a credit desk's; the chrome is a template's. The debate matrix, the formula-bar passport and the anchored driver rows show a product that knows exactly what an analyst needs to see — and then hides the decision brief and the evidence rail by default, clips its own page title on six of ten routes, and lets the Book print `undefined · undefined`. The single biggest opportunity for v2 is structural, not visual: keep the primitives (`ActionReason`, `SurfaceState`, the formula bar, the chip grammar) and rebuild the composition around IA_SPEC's four bands and nine sections so that what is strongest is what is on screen at rest.

## What's Working

1. **The refused-control contract** — `components/ui/Button.tsx` + `components/shared/ActionReason.tsx`: no native `disabled`, always a reason, keyboard- and screen-reader-discoverable, with `reasonDisplay` for inline vs sr-only. This is IA_SPEC §2 already implemented; keep the pattern, add the typed code.
2. **The Model formula bar as a metric passport** — `components/model/ModelSheet.tsx` `FormulaBar`: `Q43 · Total Net Leverage · Mar-26 · 5.68x · = (Total Debt − Cash) / Adj. EBITDA · ties to Q1-26 compliance cert 5.68x · ▸ derived period — Q4-25 management accounts missing (gap G-02) · CP-1 T4.7 · E-103`. Seven of the ten passport fields in one strip.
3. **Evidence chips with QA state and drivers with anchors** — `E-44 ⚠` in `components/deepdive/tabs.tsx`; Pipeline's CP-5B driver rows (`VERIFIED · D-01 p.214 → CP-1 calc register K-09 → CP-4C add-back analysis · CONF 92%`) in `components/pipeline/views.tsx`. The chip form `D-04 p.68 ¶2` that IA_SPEC §4.3 demands is already half-built here.

---

## Priority Issues

1. **[P0] Book renders garbage and `undefined`** · `/portfolios/` Deterministic scenario → `BYSTANDER STRESS … 3333…3333` (raw `source_fingerprint`), `AUTHORITY undefined · undefined`, plus `POSITIONS 0` beside `AUTHORITY published`. The PM/approver surface shows an unguarded object. · Fix: never print an authority object without both fields; render fingerprints as `sha:3333…3333` behind a tooltip or not at all; if positions are 0, the authority cell reads `observed-empty`, not `published`. · `/impeccable harden`

2. **[P0] The identity band loses the page title on 6/10 routes at 1440×900** · `components/shared/SubHeader.tsx` gives the identity `min-w-28 overflow-hidden` and lets badges keep width; `ShellIdentity` truncates the title first. Result: `PIPE|`, no title on Report Studio, `Atlas Forg…`, `DEM`. · Fix: the title is the one non-negotiable; badges collapse into a single count chip (`+3`) before the title loses a character; move `CompletionStateSummary` (4 chips) and `status` out of the identity row into the v2 ribbon's right-aligned execution/persistence/approval slot; enforce the ≤5-control contract at build time. · `/impeccable layout`

3. **[P1] The reference marker lies on Book and Committee** · `/command/?mode=reference`, `/portfolios/?mode=reference`, `/decisions/?mode=reference` show `REFERENCE · SEEDED, NOT ISSUER DATA` above live rows (GDPR Portfolio, a real agenda item, `Owner local-de`). `DataModeMarker` is hoisted into `EnterprisePage` structurally, but these routes never honour the mode. · Fix: a route that cannot render reference data renders the `unavailable` state under the marker ("Reference mode is not available for this section") — or drops the marker. Never both. · `/impeccable harden`

4. **[P1] The wrong things are collapsed** · Decision brief `defaultOpen={false}` on Deep-Dive (`app/deepdive/page.tsx:650`), Model (`page.tsx:1330`), IC Book (`ICBookWorkbench.tsx:1227`); Source Register / Evidence Trace collapsed to a vertical tab in Deep-Dive's default Analyst composition. IA_SPEC §3 makes the brief an invariant band and §4.3 makes evidence one click from every figure. · Fix: brief always open, four cells or `observed-empty`; evidence rail open at rest in Analysis; collapse the `TIP` banners and the Pipeline duplicate table instead. · `/impeccable distill`

5. **[P2] Analyst-declared authority and browser-side classification on Upload** · `components/upload/steps.tsx` `AuthorityDeclaration` (Origin `LIVE / REFERENCE / DEMO`, Method `REPORTED / DERIVED / MODELLED`) and `RunModePicker` (labelled "Source classification", called "run mode" in the TIP) are typed into the manifest from a dropdown. IA_SPEC §4.1: issuer, types, periods, dispositions and route come back as labelled suggestions. · Fix: the panel posts files; the server classifies; every declared value renders as `SUGGESTED` until committed; one word for the control. · `/impeccable clarify`

## Persona Red Flags

**Alex (power user).**
- `Alt+←/→` cycles 15 concepts including six that are not part of the analyst loop; there is no `Alt` jump to the five priorities.
- Three navigation surfaces (rail, ⌘K palette, compact chip nav) plus lateral `MODEL →` / `REPORT →` — four ways to move, none of them fast to the *same issuer* from Directory (row → profile overlay → then the concept).
- Deep-Dive hotkeys (`,` `.` `C` `K`, `⌘M`) are only discoverable in a dismissable `TIP`; once dismissed they are gone.
- `/issuers/` Tab order: 12 header sort/filter buttons before the first row.

**Sam (screen reader / keyboard).**
- `/settings/` strip is a permanent `role="status" aria-busy="true"` ("Analysis context · resolving") — announced as busy on every visit (trailing-slash bug).
- Refused primaries use `reasonDisplay="hidden"` (sr-only); the sighted user sees a dimmed button and no reason unless hovering — the reverse asymmetry hurts low-vision keyboard users who neither hover nor read sr-only.
- `focus-ring` is a 2px inset outline (`outline-offset: -2px`) on 24–28px chips with 1px borders; on `bg-caos-elevated` active chips the accent ring merges with the accent border.
- Unicode glyphs in chrome carry meaning with no text alternative: `⚖ IC CHAIR`, `⛨ CP-5 CLEARANCE`, `⬓ EXPORT TO VAULT`, `■6.61x`, `✓`/`✗` in `ModelSaveState`; `DecisionHeader` glyphs are `aria-hidden` but the `■`/`▲` distress marks in the worksheet are not.
- Command's four Decision cells each announce `as of 2026-09-10 01:38 UTC · LIVE · UNKNOWN · DERIVED` — 16 chips of repetition before any content.
- Compact nav (<1280px) is icon-only with `title` tooltips; Sam gets `aria-label`, but a sighted keyboard user gets nothing until hover.

**Buy-side analyst under time pressure (PRODUCT.md primary).**
- Page title clipped on the four routes they live in (Deep-Dive, Model, Reports, Upload) — every hop starts with re-orientation.
- Deep-Dive is titled by tranche (`2L TL '31 — new issue review`); with three issuers open in tabs, the tab title `Credit Agent OS (CAOS)` and the header do not name the issuer.
- Evidence pane collapsed at rest; the brief collapsed at rest; the `TIP` covers the first row of the debate.
- `Upload` makes them declare origin/method/classification/portfolio for every pack before a file lands.
- Report Studio: three different primary labels for one publish path; sheet unreadable without zooming.

**PM / approver (PRODUCT.md secondary).**
- Portfolio Lab (their compare surface) shows `undefined · undefined` and a raw fingerprint; `POSITIONS 0` under `AUTHORITY published`.
- Command's Live Coverage rows: seven issuers at an identical `4.5x / 2.6x` with `RV POSTURE —`, `FRAGILITY —`, `QA Not Reviewed`; the Daily Digest list collapses names to initials (`A. never run`). Nothing here supports a decision.
- IC Book is a meeting register (Meeting / Recommendation / Conviction % / Owner / Readiness), not a deliverable with a filing; the approver's independence rule (`APPROVER_NOT_INDEPENDENT`) has no surface.
- `View: PM` re-composes panels but grants nothing — correct — yet the rail heading changes to "PM priorities" and the wordmark routes to `/command`, which reads as authority.

---

## Minor Observations

- [P2] Paper below proofing size by default — `/reports/` at 1440×900 renders the fixed 980px sheet at 81% (`△ BELOW PROOFING SIZE`, ~9px table type) with `WATERMARK · none` on a draft; v2 needs a fit-to-width floor and the `DRAFT — NOT FILED` watermark (IA_SPEC §4.8), and `COAS THESIS` (`lib/reports/builders.ts:507`) is a typo.
- `1 agenda items` (no singular, `ICBookWorkbench.tsx:1210`).
- `Rating` column on `/issuers/` is `—` for all 37 rows in reference mode; `Sub-sector` likewise — a column that is always empty should not be a column.
- `USA` vs `United States` in one column.
- Model support `aside` for `evidence` shows "Select a model cell citation to inspect its source." in a 320px panel — a second inspector alongside the Deep-Dive evidence modal (IA_SPEC §5: one evidence drawer).
- `Settings › Model builder safeguards` sits on "Loading profile…" indefinitely on a non-profile identity; `SAVE CHANGES` refused with "Loading profile…" then "No unsaved changes".
- `.caos-action-primary` and `.caos-primary-action` are both live in `globals.css:601–626`.
- `analyst_signup_code` is a shared default in `caos/server/config.py`; the login form calls it "Invite code" while the product calls it an access code.
- Pipeline dependency map overflows horizontally: only 3 of 7 stages visible at 1440.
- `caos-workspace` rail hides below 1280px; at 1024×768 the Deep-Dive header becomes three stacked rows (~90px) before content.
- "Ask CAOS phone utility" label leaks a device word into the aria-label.

## Questions to Consider

- Is checkpointing the reference fixture intended (`checkpointActionTitle` returns the live title when `hasIssuerModel` is true on ATLF)? If not, the primary must be refused there like every other reference primary.
- Who owns "Source classification" — the analyst (current dropdown) or CP-0 (the TIP says CP-0 classifies on ingest)? Both claims are on the same screen.
- Why does `Deep-Dive` need three layouts (Summary / Report / Dense) if Report Studio owns the report form and Dense is the audit view? Which one is the v2 Analysis body?
- Is the debate (CP-6A) an Analysis artifact or a Committee artifact in v2? It is the product's best moment and the spec's §4.3 does not name it.

---

## Cognitive Load

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Exactly one page-level primary action | **FAIL** | `/upload/` announces "No page actions available" while the real commit (`UPLOAD FILES & PROCESS`) sits at the bottom of a scrolling panel; `/pipeline/` shows `OPEN RUN` + `DOCUMENT INTAKE` + `START DOCUMENT INTAKE`; `/settings/` has `SAVE CHANGES` plus a second `Save` inside Research defaults. |
| 2 | ≤ 7 visible options at any decision point | **FAIL** | See list below. |
| 3 | Progressive disclosure hides the right things | **FAIL** | Hidden: Decision brief (Deep-Dive, Model, IC Book), Source Register / Evidence Trace (Deep-Dive). Exposed: Pipeline's duplicate module table, four repeated authority-chip rows in Command. |
| 4 | One name per object | **FAIL** | Directory naming ×3; "run mode" (TIP copy) vs "Source classification" (control label) on Upload step 02; Pipeline / route / run / workflow interchanged. |
| 5 | Status readable without reading | **PASS** | Glyph + hue + text everywhere (`StatusGlyph`, `SurfaceState`, completion chips). |
| 6 | Vocabulary the persona already owns | **FAIL** | Analyst vocabulary is fine (`DM`, `OID`, `WARF`); product-internal vocabulary is not (`CP-6A-06 / 07`, `CP-5B`, `K-09`, `T4.7`, `QA-117`, `L0`, `CP-RENDER`). |
| 7 | Forms ask only what the server cannot infer | **FAIL** | Upload step 02 asks Origin, Method, Source classification and Portfolio context before a file is dropped; `IA_SPEC §4.1` says these come back as labelled suggestions. |
| 8 | Every overlay has Escape + focus return | **PASS** | `MoreDrawer`, `useModalA11y`, `PersonaDrawer`; skip links to content / navigation / page actions. |

**Decision points with more than 4 visible options**

- Rail: 5 priority links + `All 15 workflows` + Settings + Ask + 3-way View radiogroup.
- `/issuers/`: 6 sortable/filterable columns (12 header controls) + 37 identical per-row `UPLOAD` buttons + search + select-all.
- `/deepdive/` header: `ASK ATLF`, `MODEL →`, `REPORT →`, layout ×3, sim controls, export; module strip: FOUNDATION / ANALYSIS / GOVERNANCE & DEBATE / QA / Traceability / IC / Portfolio + `⌘M FIND MODULE…` (8).
- `/model/` header: Inputs / Cases / Sources / History / Model tools / Report → / Save (7); worksheet 24 columns.
- `/command/`: Live Coverage tabs (4) + portfolio select + `OPEN CROSS-ISSUER QUERY` + `OPEN GOVERNANCE QUEUE` + `GENERATE CITED BRIEF` + ▾ CONTEXT / ▾ INSPECTOR.
- `/pipeline/` utility drawer: run-mode toggle ×4, view toggle, `DIM ✓`, play/pause/speed/reset.
- `/reports/`: Compose list of 10 sections + Export panel (6 rows) + Lineage list (8 chips) + `EDIT REPORT` + `EXPORT TO VAULT` + paper/zoom controls.
- `/upload/` step 02: Source classification ×5, Origin ×3, Method ×3, Portfolio ×3, two entry paths (drop zone, EDGAR URL).
- `/settings/`: Analysis depth ×4, Query answer source ×3, AI mode ×3, Default scope ×2, three tabs.

---

## Emotional Journey

**Peak.** Deep-Dive in reference mode: the debate columns, the Chair's weighting matrix (`▲ 35 | 65 ▼`), `CP-5 CLEARANCE · CONDITIONAL · QA-117 (HIGH) open — citation E-44 page mismatch`, and the IC Verdict with a named "single greatest uncertainty". An analyst sees their own job reflected back at them with receipts. The Model formula bar is a second, quieter peak.

**End.** Report Studio — where the work should feel finished — ends on `△ BELOW PROOFING SIZE`, `WATERMARK · none`, a section titled `COAS THESIS` (typo in `lib/reports/builders.ts:507`), and a refused primary. Peak-end rule: the session ends flat.

**Valleys.**
- Portfolio Lab: `POSITIONS 0`, `AS OF Unavailable`, yet `AUTHORITY published`; then `BYSTANDER STRESS … 3333…3333 … AUTHORITY undefined · undefined`. This is the PM's screen. Trust drops to zero in one glance.
- Command with `?mode=reference`: the header says `REFERENCE · SEEDED, NOT ISSUER DATA` while the table shows the live GDPR Portfolio with seven issuers at an identical `4.5x / 2.6x`. The marker and the data contradict each other; the analyst cannot tell which one is lying.
- Every route whose title is clipped: the first half-second of each page is "where am I?".

**Reassurance at the high-stakes moments.**
- *Uploading*: good copy at the declaration ("written into the immutable source manifest and follows the evidence downstream"; "CAOS does not detect MNPI"), and `UPLOAD FILES & PROCESS` stays visible-and-refused with `Add at least one file first`. But no cost or duration statement, and the analyst is asked to *assert* `LIVE · analyst source` with a dropdown — the opposite of reassurance.
- *Accepting a run / affirming*: `AFFIRM THESIS` carries a plain-language refusal ("Reference output cannot be ratified") and the tooltip says what it will do ("Append an immutable thesis version and pin the affirmed view"). Right idea; the reason is prose, not a typed code.
- *Freezing / publishing*: IC Book's confirm is exemplary — "Freeze this committee record? Finalization creates one immutable decision and locks the linked run, report, context, portfolio, and evidence snapshot." Report Studio's ladder is honest but the button label mutates through three states (`Review frozen preview` → `Publish reviewed preview` → `Apply editorial changes to frozen preview`) so the analyst never learns one verb.

---

## Disposition for CAOS v2

| Route → v2 section | Preserve (idiom · source) | Discard (IA_SPEC rule) | Carry-over findings the new design must answer |
|---|---|---|---|
| `/issuers/` → **Directory** | Row keyboard model (arrow / Enter / F2 / Escape) with spoken instructions · `components/shared/DominantTableRegion.tsx`; per-column sort+filter header · `TableColumnFilter.tsx`; `Demo coverage` badge naming sample data · `app/issuers/page.tsx:363` | Batch bar and `Run pipeline (n)` (§4.1 "no batch state"); 37 per-row `UPLOAD` buttons (§4.1 "one action per row" — that action is *open a case*); `⋯ Directory utilities` drawer (§3 "no utility drawer"); three names for one register | Empty columns (`Rating`, `Sub-sector`) must not render; one name for the register; country normalisation; the New-issuer modal's 6 fields become server-suggested from the first pack (§4.1). |
| `/upload/` → **Upload** | `UPLOAD FILES & PROCESS` visible-and-refused with `Add at least one file first` · `components/upload/steps.tsx`; MNPI limitation stated at the point of declaration · `steps.tsx` `AuthorityDeclaration` copy; drop zone + EDGAR URL as two inputs to one intake | `AuthorityDeclaration` Origin/Method dropdowns and `RunModePicker` as analyst assertions (§4.1 suggestions are labelled, never taken from the browser); 3-step wizard strip (§4.2 per-document grade/disposition/page count/digest/set versions, no wizard); `TIP` banner; "deal documents" | No page-level primary on the intake screen; title clipped at 1440; context strip shows a raw UUID; withdrawal and restatement (§4.2) have no surface at all today. |
| `/deepdive/` → **Analysis** | Bull/Bear/Chair debate with weighting matrix and Chair memo · `components/deepdive/tabs.tsx`; `E-xx` chip carrying QA state (`E-44 ⚠`); `CP-5 CLEARANCE · CONDITIONAL` block with the blocking finding named · `rails.tsx`; `SEEDED RUN #2641 · 24/24 modules` caveat grammar · `app/deepdive/page.tsx:574`; Triggers Armed → CP-MON list | Summary/Report/Dense layout picker and `SimControls` (§3 no utility drawer; §7 motion only for live state); collapsed brief (§3 band 2 is invariant); vertical-tab collapse of Source Register (§4.3 left column is the register + trace); `Note agreement / Revise` personal annotations mixed into the standing-view strip (§4.3 conflicts shown, never resolved — annotations are not conclusions); `⚖`/`⛨` glyphs (DESIGN.md no emoji) | Page identity must be the case, not the tranche; evidence chip must resolve to `D-04 p.68 ¶2` form with rectangle, not `E-44` alone; the `TIP` hotkey sheet must become a real, persistent help surface; 1024-wide composition collapses to one column with a 3-row header. |
| `/portfolios/` + `/command/` → **Book** | `ConclusionAuthority` / `LIVE · CURRENT · DERIVED · UNRATIFIED` chip grammar · `components/shared/ConclusionAuthority.tsx`; `Evidence health` cell counting `stale · due · unknown · current` · `app/command/page.tsx`; scope labels `THIS BROWSER / ANALYST PROFILE / WORKSPACE` · `components/shared/ScopeLabel.tsx` (use on saved views) | Portfolio Lab's bespoke `.portfolio-lab__*` chrome (88 rules; DESIGN.md one panel system); `GENERATE CITED BRIEF` on a summary surface (§8 no summary tiles without a stated basis); Command's Daily Digest / Governance summary tiles (§8 no dashboard); `Live Coverage` sub-tabs (§3 tabs are section views, but four panels of the same data are not); ranked-changes worklist on the Book (§4.5 acceptance lives in Run) | `undefined · undefined` and raw fingerprints; `POSITIONS 0` with `published` authority; identical `4.5x / 2.6x` rows read as fabricated — the passport (§4.4) must make period/scenario/snapshot per cell explicit; stale = colour **and** date on every row; definition deviation marked on every affected cell; reference mode either works for the Book or is refused. |
| `/pipeline/` → **Run** | CP-5B driver rows with `VERIFIED/OPEN`, anchor chain `D-01 p.214 → CP-1 K-09 → CP-4C`, confidence bar · `components/pipeline/views.tsx` `LineagePanel`; stage-lane grouping (7 stages) as the frontier's spatial model | Simulation modes (`COMMITTEE / EARNINGS / LEGAL / RV`), play/pause/speed, `DIM ✓` (§7 motion only for live state; §3 no utility drawer); duplicate STAGE/MODULE/STATE table beside the map; `OPEN RUN` + `DOCUMENT INTAKE` + `START DOCUMENT INTAKE` (§4 exactly one primary); the word Pipeline (CONTEXT.md → route) | Node states must be the bundle's `COMPLETE / RUNNABLE / RESTRICTED / BLOCKED` with reason (today: `planned / skip`); the `QA_GATE` must read as a gate (today a `⛨` glyph); the map must not overflow at 1440; title fully lost in header. |
| `/model/` → **Model** | Formula bar passport · `components/model/ModelSheet.tsx` `FormulaBar`; `BUILT FROM` manifest chips · `ModelSheet.tsx:583`; derived-period marking `*` + warning hue + gap named; worksheet keyboard model; `SAVED ELSEWHERE · RELOAD` conflict handling · `app/model/page.tsx:940` | Editing, checkpoints, assumptions/scenario rails, `Save model checkpoint`, `.xlsx` export (§4.6 what remains is read, never edited; workbook build went with CP-MODEL); `Inputs / Cases / Sources / History` toggles as a second inspector (§5 one evidence drawer); the "Resolving model authority" interstitial | Residual as its own column and unavailable-with-reason cascade for later periods (§4.6); passport must hold for forecast cells (driver + driver evidence); `■`/`▲` need shape+text legend or removal; header must not clip the issuer; fixture values (>100% tax) must not ship as reference. |
| `/reports/` → **Report** | Paper inversion on a dark gutter with masthead `ORIGIN · METHOD · APPROVAL` line · `components/reports/ReportDoc.tsx`, `.rd-paper`; `Lineage — built from` rail with `SELECTED/REGISTERED` and `OPEN SOURCE`; publish-block ladder naming the missing rung · `app/reports/page.tsx:936` | Paper/Warm/Cool colour picker, zoom slider, `EDIT REPORT` composition mode, Compose section toggles, `EXPORT TO VAULT` as PDF/XLSX (§4.8 output is one HTML file; §8 no inline editing of a filed deliverable); three mutating primary labels (§1 ribbon: one primary, one verb); `⬓` glyph | Sign-off must bind an exact saved revision; uncited `ANALYST_JUDGMENT` refused at freeze naming the figure (§4.7); `DRAFT — NOT FILED` watermark; proofing-size floor; fix `COAS THESIS`. |
| `/decisions/` → **Committee** | Finalize confirmation copy naming everything it locks · `ICBookWorkbench.tsx:355`; armed vote confirm with issuer and action named · `:478`; `Ready for immutable finalization · review run evidence` link | Meeting-centric agenda register (Meeting / Conviction % / Owner / Readiness) and vote recording (§4.8 the object is the deliverable rendered from the frozen snapshot); `Add agenda item` primary; bespoke `.ic-book__*` chrome and its own disabled styling (`globals.css:1786`); `Refresh` button; `Owner local-de` | Rail = accepted artifacts in route order; centre = paper; right = opinion → freeze → filing with independence stated and receipt; File present-and-refused with `APPROVER_NOT_INDEPENDENT` (§2, §4.8); one time format per timestamp. |
| `/settings/` → **Admin** | Scope chips per panel (`THIS BROWSER / ANALYST PROFILE / WORKSPACE`) · `ScopeLabel.tsx`; env-var hint per read-only workspace value · `app/settings/page.tsx` `configGroups` | Everything else: effort/mode selectors (two scales), research defaults, query answer source, portfolio import, `SAVE CHANGES` (§4.9 Admin is an explicit unavailable capability that names what is missing) | The permanently "resolving" context strip; "Loading profile…" without a terminal state; the workspace-config mirror is the one thing that could become the honest "what is missing" list. |

**Vocabulary offenders seen in UI copy or labels** (word · route · exact label)

- **pipeline** · rail (every route) · `Pipeline` (`lib/nav.ts:30`)
- **pipeline** · `/upload/` · `Document Intake — Pipeline L0 source readiness`
- **pipeline** · `/upload/` (result step, `components/upload/steps.tsx:504,605`) · `VIEW IN PIPELINE →`, `WATCH RUN IN PIPELINE →`
- **pipeline** · `/pipeline/` · tag `PIPELINE`; `Pipeline completion`; `A run appears here once documents are attached to an issuer and the pipeline is started.`; aria `Ordered pipeline stages and modules with current route state`
- **pipeline** · `/issuers/` batch bar · `Run pipeline (n)` and confirmation `Queue n new pipeline runs for the selected issuers…` (`components/issuers/batchActions.ts:22`)
- **workflow** · rail · `All 15 workflows`; aria `Analyst priority workflows`, `All Workflows`; compact drawer trigger `Workflows`
- **workflow** · `/deepdive/` · `CP-6A REQUIRED OUTPUTS · 11 WORKFLOW STEPS`; layout tooltips `…no model outputs or workflow cards` / `…plus consolidated workflow cards` / `…plus every workflow card packed tight`; `OutputRegister` metadata row `Workflow step`
- **workflow** · `/monitor/` (glance) · `Persisted alerts by workflow state`, `Alert workflow state counts`
- **deal** · `/upload/` · TIP `Drop all of an issuer's deal documents at once…`; drop zone `Drop all deal documents here, or click to browse`; aria `Upload deal documents (PDF or XLSX)`
- **deal** · `/deepdive/` · page title is `dealLabel` (`2L TL '31 — new issue review`)
- **deal** · `/reports/` · tooltip `Report Studio renders the Atlas Forge reference deal as a committee-ready template…`
- **chunk** · `/command/` · aria `Source document chunk` (`components/command/CitationViewer.tsx:44`)
- **chunk** · `/reports/` evidence modal · `No source chunk is linked to this citation — lineage is unresolved.`
- **chunk** · `/monitor/` (glance) · `Zero-chunk documents · vaulted, unusable`
- **user** · `/settings/` · none in labels; **dashboard**, **AI-powered**, **corpus**, **fragment**, **passage**, **footnote**, **ready set** · not found in any rendered label or `aria-label` across `src/app` and `src/components` (non-test).

Non-banned but v2-conflicting terms seen: `run mode` vs `Source classification` (same control, `/upload/`), `Vault` / `VAULT URL` / `EXPORT TO VAULT`, `Autonomy engine`, `Command Center`, `IC Book`, `Model Builder`, `Report Studio`, `Portfolio Lab` (section names that v2 replaces with one-word URLs).
