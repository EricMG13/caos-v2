# CAOS v2 — design brief

The one hand-written design page. Purpose, audience and rules are not restated here:
`docs/IA_SPEC.md` (nine sections, four bands, states, refused controls), `DESIGN.md`
(the committee terminal), `CONTEXT.md` (vocabulary), `docs/DECISIONS.md` §14 (no
workbook, no `.docx`; the host renders the deliverable) and §18 (tokens).

## Where this comes from

`/impeccable critique` of the predecessor frontend — `github.com/EricMG13/Credit-Operating-System`,
local clone `Alpha/Final @ f454c654f`, `caos/frontend` 2.0.0 — run 2026-09-10, dual-agent,
snapshots in `docs/design/critique/`:

| Target | Score | P0 | P1 | Trend (last runs) |
|---|---|---|---|---|
| `caos/frontend/src/app`, nine v2-mapped routes | **26/40** | 2 | 2 | 29 → 32 → 24 → 26 → 26 |
| `/model/` | **27/40** | 1 | 2 | 24 → 28 → 23 → 27 |

Deterministic scan: zero anti-pattern findings across 293 files (the visual system is
clean; every point lost is composition and truth). The old app's Content Security Policy
(`script-src 'self'` plus hashes, no `unsafe-inline`) blocked the overlay — v2's static
export keeps that posture.

## Priority order (owner's answers, 2026-09-10)

1. **Composition at rest first.** The decision brief and the evidence rail are open by default; the identity band never clips the case name; the four bands are invariant on every section.
2. **Truth on the Book and Committee.** No unguarded object ever reaches a cell; `observed-empty` when there is nothing; a reference or seeded marker never sits above live rows — the section renders `unavailable` instead.
3. **The Model's residual and the reference primary.** Residual as its own column with forward-propagating unavailability; a seeded fixture can never be checkpointed, accepted or filed as live.

Scope carried into the design turns: **every P0 and P1** from both snapshots. P2 findings (server-classified intake, paper at proofing size, a glossary for `CP-*` codes, the second-inspector rails) are recorded in the disposition table and picked up by the section that owns them, not pulled forward.

Decided here: the **CP-6A Bull / Bear / Chair debate lives in Analysis** as a module tab — it is a module output like any other, rendered in the centre column with the Chair's weighting matrix as its table; Committee shows it only as an accepted artifact in the deliverable. **Nothing from the old app is off-limits**: the redesign replaces composition; the primitives worth keeping are the preserve column below.

## Five principles the new design inherits

1. **The reader is the centre.** Module output is read, cited and disputed before anything is accepted; acceptance binds what was seen.
2. **Capability-gate honestly.** A section, control or mode this deployment cannot serve renders `unavailable` and names what is missing — never a marker over live data, never a placeholder that looks operational.
3. **One vocabulary.** `CONTEXT.md` terms only, one name per object, human names beside `CP-*` ids; no `pipeline`, `workflow`, `deal`, `chunk` in chrome.
4. **One error-and-ceremony idiom.** Refused controls stay visible with their typed code and what clears it; one styled confirmation; one drawer; one refusal component.
5. **Accept only after inspection.** The primary action is never offered before the thing it binds is on screen.

## What each section must show (IA_SPEC §4) and the card that shows it

| Section | Must show | Card id |
|---|---|---|
| Directory `/directory/` | case register: search, one filter, one action per row; document-first intake with labelled suggestions; completed intake opens for review | 5a · 5b |
| Upload `/upload/` | per source: grade, disposition, page count, digest, set versions; withdrawal checked live; restatement surfaced as a conflict | 6a · 6b |
| Analysis `/analysis/` | three columns: register + evidence trace · module output with formula bar, conflict register, adjusted-vs-reported · clearance, frontier, capital structure, triggers; chip `D-04 p.68 ¶2` | 2a · 9a |
| Book `/book/` | facets, grouping, compare 2–4 on one stated basis; ten-field passport; definition deviation everywhere; stale = colour and date | 2b · 9b |
| Run `/run/` | the resolved route as a DAG; node states with reasons; the one `QA_GATE` as a gate; plan approval and acceptance live here only | 4a · 4b |
| Model `/model/` | CP-CF's projection read-only; residual as its own column; unavailable-with-reason cascading forward; driver + evidence per figure | 3b · 9c |
| Report `/report/` | draft revision; opinion binding the exact revision; `ANALYST_JUDGMENT` refused at freeze naming the figure | 7a · 7b |
| Committee `/committee/` | the host-rendered deliverable on paper, `DRAFT — NOT FILED`; rail of accepted artifacts; opinion → freeze → filing (independence) → receipt | 3a · 11a |
| Admin `/admin/` | explicit unavailable capability naming what is missing | 8a |

Cross-cutting cards: 10a–10c the seven states · 11a–11c refused controls · 12a the rail and served role · 13a–13b responsive collapse.

## Disposition (from the critique, verbatim)

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
