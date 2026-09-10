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
| `03 Committee and Model.dc.html` | Turn 3 — the two sections `docs/DECISIONS.md` §14 rewrote. |
| `04 Run.dc.html` | Turn 4 — `/run/`. |

## Card map

| Section | URL | Card | State it shows |
|---|---|---|---|
| Directory | `/directory/` | — | Turn 5 |
| Upload | `/upload/` | — | Turn 5 |
| Analysis | `/analysis/` | `2a` | Module output, evidence trace, clearance |
| Book | `/book/` | `2b` | Facets, comparison, passport |
| Run | `/run/` | **`4a`** | Route pinned, running; accept refused `RUN_NOT_TERMINAL` |
| Run | `/run/` | **`4b`** | The plan gate: resolved not pinned, approval digest-bound, nothing reserved |
| Model | `/model/` | **`3c`** | CP-CF's projection read-only, residual column, unavailable propagating |
| Report | `/report/` | — | Turn 6 |
| Committee | `/committee/` | **`3a`** | Deliverable on paper `DRAFT — NOT FILED`; filing refused `APPROVER_NOT_INDEPENDENT` |
| Committee | `/committee/` | **`3b`** | Filed by an independent approver; receipt, watermark gone |
| Admin | `/admin/` | — | Turn 6 |

Cards `2c` and `2d` are superseded by `3a`/`3b` and `3c`: they drew a `.docx`
publication gate and a workbook builder, neither of which this build produces.

## Remaining turns

| Turn | Cards | What it must show |
|---|---|---|
| 5 | Directory, Upload | Case register (one action per row, no batch); document-first intake with **labelled suggestions**; per-source grade, disposition, page count, digest, set-version membership; withdrawal checked live; restatement as a conflict row |
| 6 | Report, Admin | Draft revision and the opinion binding the exact revision; freeze refused on an uncited `ANALYST_JUDGMENT` figure; Admin as an explicit unavailable capability naming what is missing |
| 7 | Evidence drawer, passport | Analysis at 1280 px with the drawer open (`D-04 p.68 ¶2`, page render, rectangle, matched text, observation time); the ten-field passport over an actual cell and over a projected cell |
| 8 | States | One region in all seven states side by side; the page-level offline sentence; private 404 and absent route sharing one wording |
| 9 | Refused controls | Filing, run accept and a ribbon primary each visible and refused with its typed code |
| 10 | Rail, served role | Nine count/state lines; the section-local group in three variants; the two foot controls |
| 11 | Responsive | 1080 px (right column folds into the drawer) and 1024 px (rail strip). Nothing below 1024 |

## What the build inherits from the cards

- **Chrome** — `Ribbon`, `DecisionBrief` (four cells, always open), `SectionTabs`, `VerdictStrip`, `Rail` (nine entries, count + one-line state), `ServedRole` (read-only, never a control).
- **Refusal idiom** — every governed action renders visible and refused with its typed code and what clears it: `APPROVER_NOT_INDEPENDENT`, `RUN_NOT_TERMINAL`, `PLAN_APPROVAL_PENDING`, `NODE_NOT_ACCEPTABLE`, `FORECAST_RESIDUAL_UNRECONCILED`.
- **Severity is shape and hue** — disc (success, running), triangle (warning), rounded square (critical), flat dot (idle). Never hue alone.
- **Paper is for filed output only** — the Committee document, nowhere else.
- **Projection** — residual as its own column; an unreconciled period unavailable with its reason; every later period in that case unavailable by propagation, never zero growth.
- **Route** — node states are the bundle's four with the reason named; the one `QA_GATE` is drawn as a gate; edges are typed from `profile["edges"]`.
