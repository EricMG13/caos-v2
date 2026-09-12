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

The repository was seeded on 2026-09-10 from the CAOS-Final specification
(`docs/DECISIONS.md` §12) and now contains the rebuilt application plus the
Phase 9 workspace. Its gates are being repaired in the ordered slices tracked
by [`docs/REPAIR_PLAN.md`](docs/REPAIR_PLAN.md); Phase 1 is not yet complete.

## Local development

Python 3.14 and Node 24 run the application toolchain; security tools stay in
their separately locked Python 3.12 environment. The first setup is:

```sh
cp .env.example .env
make bootstrap
make doctor
make dev-up
```

`make bootstrap` installs both Python environments from hashed, wheels-only
locks, installs the pinned local pre-commit runner, and runs
`npm ci --ignore-scripts`. `make doctor` reports versions and whether named
configuration is present; it never prints values. Live-provider variables are
optional and should remain absent during ordinary development.

The API and UI are separate processes and remain unconnected until a later
phase:

```sh
make dev-api  # http://127.0.0.1:8000; `make dev` is an alias
make dev-ui   # http://127.0.0.1:5173
```

The local services are deliberately isolated: the least-privilege application
database is on `127.0.0.1:55436`, the disposable test-admin instance is on
`127.0.0.1:55437`, and blobs stay under `.dev-data/blobs`. Port collisions fail
visibly. `make dev-down` stops only the `caos-workbench-dev` Compose project and
preserves the development database volume and blob directory; test database
storage is ephemeral.

Run `make test` for the current backend suite and `make check` for the binding
gate order described in [`docs/CI_GATE_CONTRACT.md`](docs/CI_GATE_CONTRACT.md).
Fixture-mode separation and full frontend gate parity arrive in the next Phase
1 slice. `make index` uses an installed GitNexus executable with
`--index-only`; it never downloads, embeds, injects instructions, or publishes.
