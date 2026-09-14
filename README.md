# CAOS

Turns governed source documents into committee-ready credit conclusions for
institutional leveraged-finance analysts.

Every number is one click from its evidence — and the evidence is a rectangle on
a page of a pinned document, not a text match.

## Read in this order

| | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | the engineering contract and the eleven invariants |
| [`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md) | the exact Phase 2 continuation checkpoint, gates and review timing |
| [`docs/REPAIR_PLAN.md`](docs/REPAIR_PLAN.md) | current repair order and phase acceptance rules |
| [`docs/REBUILD_PLAN.md`](docs/REBUILD_PLAN.md) | historical rebuild phases and retained test references |
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
by [`docs/REPAIR_PLAN.md`](docs/REPAIR_PLAN.md). Phase 1 was accepted at
`e3964e6ec1d64a7d7059eef4211b251e1a2fe9e9`; Phase 2 is in progress.
The [tracked handoff](docs/CLAUDE_CODE_HANDOFF.md) owns the current task and
accepted checkpoint; an implementation commit alone is not acceptance.
For later phases, use the [Phase 3–6 goal prompt](docs/PHASE_3_ONWARDS_GOAL_PROMPT.md)
and its linked phase cards/reasoning settings.

## Local development

Python 3.14 and Node 24 run the application toolchain; security tools stay in
their separately locked Python 3.12 environment. Install the host prerequisites
first: Git, uv, Node 24/npm, Docker with Compose, installed GitNexus, Gitleaks,
and Trivy 0.70.0. Bootstrap installs project packages, not these host tools.
Do not overwrite an existing `.env`; the copy step is for a fresh checkout.
The first setup is:

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

The API, worker and UI are separate processes. `make dev-api` serves the
guarded site application on `127.0.0.1:8000` and answers only loopback
requests. The ordinary UI proxies `/api` to it and asserts the local actor
itself: `CAOS_DEV_USER` (a UUID) and `CAOS_DEV_ROLE` (`READER`, `ANALYST` or
`ADMIN`; default `ANALYST`), set in the environment file the setup copied.
Without `CAOS_DEV_USER` the API answers 401. An absent or unknown API route
fails visibly rather than falling back to sample data. The worker needs a
configured provider and a dated `CAOS_MODEL_PRICE`, and refuses to start
without them:

```sh
make dev-api     # http://127.0.0.1:8000; `make dev` is an alias
make dev-worker  # the one polling worker
make dev-ui      # http://127.0.0.1:5173
```

Sample screens are available only in explicit demonstration mode. They carry a
prominent read-only banner and fixture handlers reject commands:

```sh
make dev-ui-demo
npm --prefix frontend run build:demo
npm --prefix frontend run preview:demo
```

Production and demonstration exports are separate (`frontend/dist` and
`frontend/dist-demo`). Production preview never serves fixture middleware or a
stale demonstration build.

The local services are deliberately isolated: the least-privilege application
database is on `127.0.0.1:55436`, the disposable test-admin instance is on
`127.0.0.1:55437`, and blobs stay under `.dev-data/blobs`. Port collisions fail
visibly. `make dev-down` stops only the `caos-workbench-dev` Compose project and
preserves the development database volume and blob directory; test database
storage is ephemeral.

`make check-fast` is intentionally partial: it omits PostgreSQL, browser,
security and image coverage. The complete offline gate requires the disposable
test PostgreSQL from `make dev-up`, pinned Playwright browsers, and Trivy 0.70.0.
The separate PR-size gate additionally requires an exact PR base:

```sh
./frontend/node_modules/.bin/playwright install
TRIVY=/path/to/trivy IMAGE=caos-workbench:check make check
PR_BASE=<exact-pr-base> make check-size
```

`make check` runs backend checks, the explicit two-connection race suite,
frontend production and fixture checks, security, image scanning and
`make smoke-production` sequentially. The separate PR-only size command requires the exact proposed
base. The offline gate removes inherited provider credentials and
never makes paid calls. It cannot manufacture the hosted Sonar or required
GitHub statuses described in [`docs/CI_GATE_CONTRACT.md`](docs/CI_GATE_CONTRACT.md).
`make index` uses an installed GitNexus executable with
`--index-only`; it never downloads, embeds, injects instructions, or publishes.
If GitNexus reports the known incremental `file_fts` index failure, rebuild only
that local index with `gitnexus analyze --force --index-only`, then confirm it
with `gitnexus status`.

## Production image

One image runs as two containers: the API
(`server.api.site:application`, serving `/api` and the static export from one
origin) and the worker (`python -m server.engine.worker`). It expects an
authenticating edge in front of it that sets `x-caos-user`,
`x-forwarded-groups` and the shared `x-caos-edge-token`; the contract is in
`server/api/edge.py` and `docs/DECISIONS.md` §53. In edge mode the API needs
`CAOS_EDGE_TOKEN` (at least 32 bytes), `CAOS_PUBLIC_ORIGIN`, and no
`CAOS_TRUST_ROLE_HEADER`, or it refuses to start. Started without a token, it
answers only `GET /api/health`.

The disposable local proof builds the image, boots it on its own database and
blob volume (`compose.smoke.yaml`, project `caos-workbench-smoke`), runs the
image tests, then the real-browser journey through a test edge, and removes
the stack with its volumes. It needs Docker and never touches the development
database or blobs:

```sh
make smoke-production
```

The journey step refuses until its Playwright configuration lands (see the
handoff); no CI job runs this target.
