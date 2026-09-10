# Design handoff — the workspace, section by section

The design lives in Claude Design project
[CAOS v2 — Persona Workbench](https://claude.ai/design/p/69d37748-8595-4309-9b06-bc5f9529a29c),
the project `DESIGN.md` and `docs/IA_SPEC.md` already cite. Cards carry stable ids
(`2a`, `3a`, `4b` …) that never move; a later turn refers to an earlier card by id.

Bound design system: **CAOS** (`caos-frontend`). It declares `--caos-*` and not the
font families, so `caos-shell.css` declares `--font-sans|mono|display` first
(`DESIGN.md`). Token values are the design system's and `DESIGN.md`'s, unchanged
(`docs/DECISIONS.md` §18 records why the predecessor's re-tuned values are not adopted).

## Files in the design project

| File | What it is |
|---|---|
| `caos-v2-personas.html` | Turns 1–2. Turn 1 (persona-as-shell) is superseded; Turn 2 conformed the layout to `IA_SPEC.md`. |
| `caos-shell.css` | The workspace shell every card draws: four bands, the nine-section rail, panels, tags, severity glyphs, the projection table, the paper, the route DAG. One stylesheet so no two cards drift. |
| `caos-shell.additions.css` | The register, intake and source-pack idioms, and the rule that keeps a decision brief from ever overflowing. |
| `caos-evidence.css` | The one evidence surface: the drawer, the page render with its rectangle, and the passport. |
| `03 Committee and Model.dc.html` | Turn 3 — the two sections `docs/DECISIONS.md` §14 rewrote. |
| `04 Run.dc.html` | Turn 4 — `/run/`, running and at the plan gate. |
| `05 Directory and Upload.dc.html` | Turn 5 — where evidence enters, and what the machine may assert. |
| `06 Report and Admin.dc.html` | Turn 6 — the opinion, and the section that does not pretend. |
| `07 Evidence and passport.dc.html` | Turn 7 — the drawer at 1280 px and the ten-field passport. |
| `08 States and refusals.dc.html` | Turn 8 — specimen boards: the seven states, the page-level states, the refused controls. |
| `09 Rail and responsive.dc.html` | Turn 9 — the rail's local groups, 1080 px and 1024 px. |

## Card map

Every section is drawn. Cards `2c` and `2d` are superseded by `3a`/`3b` and `3c`:
they drew a `.docx` publication gate and a workbook builder, neither of which this
build produces.

| Section | URL | Card | State it shows |
|---|---|---|---|
| Directory | `/directory/` | **`5a`** | Case register: search, one filter, one action per row, no batch state |
| Directory | `/directory/` | **`5b`** | Document-first intake: six labelled suggestions, one corrected, nothing committed |
| Upload | `/upload/` | **`5c`** | Source pack: grade, disposition, pages, digest, set versions; one withdrawn, one restated |
| Analysis | `/analysis/` | `2a` · **`7a`** | Module output and evidence trace; the drawer open at 1280 px |
| Book | `/book/` | `2b` · **`7b`** | Facets and comparison; the ten-field passport over an actual cell |
| Run | `/run/` | **`4a`** | Route pinned and running; accept refused `RUN_NOT_TERMINAL` |
| Run | `/run/` | **`4b`** | The plan gate: resolved not pinned, approval digest-bound, nothing reserved |
| Model | `/model/` | **`3c`** | CP-CF's projection read-only, residual column, unavailable propagating |
| Report | `/report/` | **`6a`** | Draft revision; sign-off refused `UNCITED_FIGURE_IN_JUDGMENT`, the figure named |
| Committee | `/committee/` | **`3a`** | Deliverable on paper `DRAFT — NOT FILED`; filing refused `APPROVER_NOT_INDEPENDENT` |
| Committee | `/committee/` | **`3b`** | Filed by an independent approver; receipt, watermark gone |
| Admin | `/admin/` | **`6b`** | An explicit unavailable capability naming the four things that are missing |

### Cross-cutting contracts

| Contract | Card | What it fixes |
|---|---|---|
| The seven states | **`8a`** | One region eight times; `ready` is the one with no marker |
| Page-level states | **`8b`** | The offline sentence; a private case and an absent route share one wording |
| Refused controls | **`8c`** | Six typed codes, each with the condition that clears it |
| The rail | **`9a`** | Nine sections, three section-local groups, two foot controls |
| Responsive | **`9b`** · **`9c`** | 1080 px folds the right column into the drawer; 1024 px collapses the rail to a strip |

## Open design questions, answered by the build (2026-09-10)

1. **Sign out at 1024 px.** The strip keeps both foot controls, stacked, as two
   full-width 26 px buttons showing `ASK` and `OUT` (`frontend/src/chrome/Rail.tsx`,
   `caos.css` `@media (max-width: 1024px)`). Two remains the maximum `IA_SPEC.md` §3 sets.
2. **Below 1024 px.** Nothing reflows further: the strip rail and the bands persist and
   the body scrolls. No honest sentence is drawn because nothing is hidden.
3. **The CP-6 debate's home.** An Analysis module tab, `CP-6A`, in the centre column
   (`frontend/src/sections/analysis/`), as `docs/design/BRIEF.md` decided.

Both foot controls are refused in this build with the phase that clears them named
(`PROVIDER_UNPLACED`, `IDENTITY_UNPLACED`): a control that did nothing would be a
placeholder that looks operational.

## What the build inherits from the cards

- **Chrome** — `Ribbon`, `DecisionBrief` (four cells, always open), `SectionTabs`, `VerdictStrip`, `Rail` (nine entries, count + one-line state), `ServedRole` (read-only, never a control).
- **Refusal idiom** — every governed action renders visible and refused with its typed code and what clears it: `APPROVER_NOT_INDEPENDENT`, `RUN_NOT_TERMINAL`, `PLAN_APPROVAL_PENDING`, `NODE_NOT_ACCEPTABLE`, `FORECAST_RESIDUAL_UNRECONCILED`.
- **Severity is shape and hue** — disc (success, running), triangle (warning), rounded square (critical), flat dot (idle). Never hue alone.
- **Paper is for filed output only** — the Committee document, nowhere else.
- **Projection** — residual as its own column; an unreconciled period unavailable with its reason; every later period in that case unavailable by propagation, never zero growth.
- **Route** — node states are the bundle's four with the reason named; the one `QA_GATE` is drawn as a gate; edges are typed from `profile["edges"]`.
- **Suggestions are labelled** — anything the machine proposes carries a dashed `SUGGESTED` chip until a person commits it, and the browser posts files and nothing else.
- **The states machinery** — `RegionState` takes one of seven kinds plus `ready`; `ready` renders children with no marker; `observed-empty` requires a timestamp; `unavailable` uses the fixed wording.
