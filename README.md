# CAOS

Turns governed source documents into committee-ready credit conclusions for
institutional leveraged-finance analysts.

Every number is one click from its evidence — and the evidence is a rectangle on
a page of a pinned document, not a text match.

## Read in this order

| | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | the engineering contract and the eleven invariants |
| [`docs/REBUILD_PLAN.md`](docs/REBUILD_PLAN.md) | what gets built, in what order, and what "done" means per phase |
| [`docs/SYSTEM_SPEC.md`](docs/SYSTEM_SPEC.md) | components, data model, route resolution, publication |
| [`docs/IA_SPEC.md`](docs/IA_SPEC.md) | one workspace, nine sections, and their contracts |
| [`docs/archive/`](docs/archive/) | the workbook and `.docx` contracts this build does not produce (`docs/DECISIONS.md` §14) |
| [`docs/AI_CODE_QUALITY.md`](docs/AI_CODE_QUALITY.md) | what agent-written code costs, and the control for each failure mode |
| [`DESIGN.md`](DESIGN.md) · [`CONTEXT.md`](CONTEXT.md) | visual language · vocabulary |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | the binding record; later entries override earlier |

Starting the build: [`docs/INITIALISATION_PROMPT.md`](docs/INITIALISATION_PROMPT.md).

## Status

Phase 9 in progress (`frontend/`, `docs/DECISIONS.md` §18–§19). Seeded on 2026-09-10 from the CAOS-Final specification
(`docs/DECISIONS.md` §12); no application code exists yet. This is deliberate —
the predecessor tree reached 29k lines of server code before its route
resolution was found to be reading the wrong table.
