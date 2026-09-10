---
target: /model/ — caos/frontend/src/app/model/page.tsx
total_score: 27
max_score: 40
na_heuristics:
p0_count: 1
p1_count: 2
timestamp: 2026-09-10T01-51-24Z
slug: caos-frontend-src-app-model-page-tsx
---
# Design critique — `/model/` (`caos/frontend/src/app/model/page.tsx`, `ModelV2Workbench.tsx`, `ModelAuthorityRoute.tsx`)

Method: dual-agent (A: general-purpose design review · B: general-purpose detector + browser evidence, isolated; A finished before B's findings entered the synthesis)

**Provenance.** `/Users/ericguei/Claude/Projects/Credit Operating System` @ `f454c654f` (`Alpha/Final`), dirty working tree 967 entries at scan time; `caos/frontend` = caos-frontend 2.0.0, static export rebuilt 2026-09-10 00:54 and served by the FastAPI server at `127.0.0.1:8000` (SQLite, no provider keys used; the server was started for this critique and stopped afterwards). Both assessments browsed read-only: nothing was run, uploaded, dispatched or generated; no analyst profile was created (the server admitted a local non-profile identity). The clone was not edited. This report is the input to CAOS v2's design brief (`docs/design/BRIEF.md`); the old frontend is being replaced, not polished, so no score threshold applies.


## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | `Model draft` / `● UNSAVED` / `SAVED hh:mm` / `✗ SAVE FAILED` ladder; derived periods marked `*` in warning hue with `derived period — Q4-25 management accounts missing (gap G-02)` in the formula bar. Every load passes through a full-screen "Resolving model authority" interstitial (`ModelAuthorityRoute.tsx` `ModelAuthorityState`) — observed still on screen 5s after navigation. No residual / balance-check row, so an unbalanced period is invisible. |
| 2 | Match with real world | 3 | Reads like a desk model (`YE 31-DEC · $M`, QUARTERLY / YTD / HISTORIC / LTM / PF / BASE / DOWNSIDE, parentheses negatives, `5.68x`). Support buttons relabelled `Inputs / Cases / Sources / History` for 2.5.3. Against: reference fixture shows **Tax Rate 133.7%, 154.1%, 157.4%** and DSO/DSI/DPO/D&A% flat across 24 periods — reads as a calc error, not a fixture. |
| 3 | User control and freedom | 3 | Unsaved-leave guard (opt-out in Settings), server checkpoints with armed restore when dirty, conflict → reload. No cell-level undo. |
| 4 | Consistency and standards | 2 | Header carries 11 items; title clips to `Atlas Forg…` and the `DEMO` badge to `DEM` at 1440. `SAVE MODEL CHECKPOINT` renders full-accent (live) on a `REFERENCE · SEEDED, NOT ISSUER DATA` surface while every other route's reference primary is refused and dimmed. |
| 5 | Error prevention | 2 | `checkpointActionTitle` returns the live title on the reference issuer, so a seeded fixture can be checkpointed into the analyst's context. `■` (warn) / `▲` (crit) distress glyphs (`cell-style.ts`) have no legend. No residual column (IA_SPEC §4.6). |
| 6 | Recognition rather than recall | 3 | Formula bar decodes the selected cell (definition · derivation · tie-out · gap · `CP-1 T4.7` · `E-103`) — the best passport prototype in the app. Decision brief collapsed; support rails hidden behind toggles; 24 lettered columns `A–X`. |
| 7 | Flexibility and efficiency | 4 | Arrow-key grid, Enter edit / Escape release, `QUARTERS` toggle, `.xlsx` export, checkpoints + history, lateral `Report →` carrying context. |
| 8 | Aesthetic and minimalist design | 2 | The grid is disciplined (mono, accent only on derived %, frozen row labels). The header is not, and it costs the page its name. |
| 9 | Diagnose and recover | 3 | Save conflict / save failed / restore retry / authority-unavailable each carry cause and action. |
| 10 | Help and documentation | 2 | Tooltips on support buttons and grid instructions; nothing explains `PF`, `LTM`, `*`, `■`, `▲`, `K-09`, `T4.7`. |
| | **Total** | **27 / 40** | (Prior 24 → 28 → 23 not used as an anchor.) |

---

## Design Specificity Verdict

**LLM assessment.** A desk model, not a spreadsheet clone: `YE 31-DEC · $M`, QUARTERLY / YTD / HISTORIC / LTM / PF / BASE / DOWNSIDE column groups, parentheses negatives, `5.68x`, derived periods marked `*` in warning hue with the gap named in the formula bar (`derived period — Q4-25 management accounts missing (gap G-02)`), `BUILT FROM` manifest chips. The formula bar decodes a selected cell into definition · derivation · tie-out · gap · `CP-1 T4.7` · `E-103` — seven of IA_SPEC's ten passport fields in one strip. What is not authored is the header (11 items, clipped title) and the editing apparatus (checkpoints, assumptions, scenario rails, `.xlsx` export) that CAOS-Final §48 removes from the Model section altogether.

**Deterministic scan.** `detect.mjs --json caos/frontend/src/app/model caos/frontend/src/components/model`: exit 0, zero findings, with and without the project config.

**Visual overlays.** None — the app's CSP blocked `detect.js`; the fallback screenshot shows the full-width grid on dark ground with the selected row and cell highlighted and the cases strip at right.

## What's Working

1. The formula bar as a metric passport (`components/model/ModelSheet.tsx` `FormulaBar`).
2. The save ladder (`● UNSAVED` / `SAVED hh:mm` / `✗ SAVE FAILED` / `✗ SAVED ELSEWHERE · RELOAD`) with cause and action on every failure (`app/model/page.tsx:940`).
3. The worksheet keyboard model: arrow keys, Enter to edit, Escape to release, frozen row labels, mono numerics with accent only on derived percentages.


## Priority Issues

1. **[P0] The identity band drops the model's name** · at 1440×900 the header carries 11 items and the title clips to `Atlas Forg…`, the `DEMO` badge to `DEM` (`components/shared/SubHeader.tsx`, `ShellIdentity`). · Fix: the title never loses a character; badges collapse into one count chip; execution/persistence/approval chips move to the ribbon's right-aligned slot. · `/impeccable layout`
2. **[P1] A reference fixture can be checkpointed as live** · `checkpointActionTitle` returns the live title when `hasIssuerModel` is true on the seeded issuer, so `SAVE MODEL CHECKPOINT` renders as a live primary on a `REFERENCE · SEEDED, NOT ISSUER DATA` surface while every other route refuses its reference primary. · Fix: refuse with a typed reason, like the rest. · `/impeccable harden`
3. **[P1] No residual, no legend** · the projection has no balance-check or residual column, so an unbalanced period is invisible; the `■` (warn) / `▲` (crit) distress glyphs (`cell-style.ts`) have no legend or text alternative; the reference fixture's Tax Rate rows read 133–157 % and DSO/DSI/DPO/D&A% are flat across 24 periods, which reads as a calculation error. · Fix: IA_SPEC §4.6 — residual as its own column, unavailable-with-reason cascading forward; shape + text for every glyph; fixtures that pass a sanity check. · `/impeccable harden`
4. **[P2] The passport is hidden behind toggles** · the formula bar is the best passport prototype in the app, yet the decision brief is `defaultOpen={false}` (`page.tsx:1330`) and the support rails (`Inputs / Cases / Sources / History`) form a second inspector (IA_SPEC §5: one evidence drawer). · Fix: brief open at rest; one drawer. · `/impeccable distill`
5. **[P2] Every load passes through a full-screen "Resolving model authority" interstitial** (`ModelAuthorityRoute.tsx`), still on screen 5 s after navigation. · Fix: resolve authority in the ribbon's state chips, never as a page-blocking screen. · `/impeccable optimize`

## Disposition for CAOS v2 (Model → `/model/`)

Preserve: the formula-bar passport, the `BUILT FROM` chips, derived-period marking with the gap named, the worksheet keyboard model, the conflict handling. Discard (IA_SPEC §4.6 after CAOS-Final §48): editing, checkpoints, assumptions and scenario rails, `Save model checkpoint`, `.xlsx` export, the `Inputs / Cases / Sources / History` second inspector, the authority interstitial. Carry-over: the residual column with forward-propagating unavailability; the passport holding for forecast cells (driver + driver evidence); a shape-and-text legend or removal for `■`/`▲`; a header that never clips the case; fixtures that pass a sanity check.
