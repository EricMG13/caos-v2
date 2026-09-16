# Decision record

Binding. Later entries override earlier ones. Every entry is dated, states what
was decided, and states the reason — a decision without a reason cannot be
revisited intelligently.

---

## 2026-09-08 §1 — Rebuild rather than refactor

The predecessor tree (29k lines of server code, 35k of tests) is sound in its
invariants and wrong in three structural choices: a precompiled LangGraph per
route, a SQLite/Postgres split, and route resolution built from the catalog's
untyped display list. The first two are removable; the third invalidates every
route the system has ever run. Rebuilding is cheaper than unpicking, and the
invariants transfer intact.

## 2026-09-08 §2 — Runtime DAG follows legacy

The route is resolved from `profile["edges"]` with typed edges
(`REQUIRED`/`CONDITIONAL`/`QA_GATE` blocking, `OPTIONAL`/`ADVISORY` soft until
the source is READY), node states `COMPLETE`/`BLOCKED`/`RESTRICTED`/`RUNNABLE`,
and a frontier of runnable plus restricted. Invariant 10 is not weakened but
re-pinned: the *resolved* route is digested at the gate and execution reads only
the pin.

**Reason.** The predecessor read `navigation.dependencies` — 97 untyped pairs
meant for display — so 25 OPTIONAL and 22 ADVISORY edges were enforced as
mandatory, the single QA_GATE did not gate, and RESTRICTED could not occur.

## 2026-09-08 §3 — No checkpointer

Execution state is the accepted-attempt ledger. Recovery is recomputation of
`node_states`, not restoration of a checkpoint.

**Reason.** A legacy-style route cannot be precompiled, so a graph framework's
checkpoint buys nothing the run store does not already own — and the split
between checkpoint and domain state was the source of most of the
predecessor's recovery machinery.

## 2026-09-08 §4 — PostgreSQL only

One database from the first commit, including run state. No SQLite tier.

**Reason.** Five entries on the predecessor's known-gaps ledger existed only
because of that split.

## 2026-09-08 §5 — CP-PARSE stays a separate host node

The upstream bundle merges CP-PARSE into CP-0. The host keeps them as separate
stage-0 nodes via an `_ALIASES` carve-out, overriding both the new
`superseded_module_ids["CP-PARSE"]` entry and `preparation_stage.runnable:
false`.

**Reason.** CP-PARSE owns the `document_parse_manifest` over the host's own
already-extracted immutable blocks. That object is host territory. Revisit if a
future bundle collapses the two schemas.

**Consequence.** `assemble_authority` must not slice `SKILL.md` on section
markers — the merged skill has dropped `## CP-PARSE runnable profile`, which
would break CP-0 as well as CP-PARSE. CP-PARSE receives the whole CP-0 skill
plus its own reference files.

## 2026-09-08 §6 — Never edit an upstream bundle file

New behaviour goes in new skill folders. New route nodes ride a host-declared
extension mirroring `research_extension`, never a catalog edit.

**Reason.** One Deploy V release changed 175 files including 21 of 22
`SKILL.md`. Every upstream file we touch becomes a permanent merge and moves the
whole-tree pin.

## 2026-09-08 §7 — LibreOffice is required, not optional

`soffice` is the workbook's formula verification engine and is installed in the
worker image. The build fails closed without it.

**Reason.** Reverses an earlier recommendation made before reading
`cp_model_v3/builder.py`. Legacy recalculates through soffice and then validates
the sheet registry, the formula inventory and every computed value against an
independently computed expectation. The predecessor shipped LibreOffice and
never invoked it, so its workbooks were never evaluated at all — a formula
resolving to `#DIV/0!` shipped silently.

## 2026-09-08 §8 — `cash_flow_forecast` and CP-CF

A deterministic forecast calculator, and the module that declares it, both in a
new skill folder.

**Reason.** CP-2G states its roll-forward rules in prose and emits 42 driver
rows; no host code computed the projection, so leverage and coverage were
recomputed deterministically over arithmetic a model performed.

## 2026-09-08 §9 — Coordinate-anchored citations (invariant 11)

A citation is `{document_sha256, page, bbox, matched_text}`, re-located by the
host in its token index.

**Reason.** The predecessor's locators were line ranges over extracted text.
"One click from its evidence" meant one click to a line range, not to a region
on a page.

## 2026-09-08 §10 — Phase 0 toolchain

`uv` compiles and installs every lock. Three locks: `requirements.txt` (runtime,
empty until Phase 1), `requirements-dev.txt` (ruff 0.14.0, mypy 1.18.2,
pytest 9.0.3, resolved for 3.14) and `requirements-security.txt` (bandit 1.7.10,
pip-audit 2.9.0, resolved for 3.12). All three carry `--generate-hashes`;
nothing installs without `--require-hashes`.

pytest is pinned at 9.0.3 rather than 8.4.2 because 8.4.2 carries
PYSEC-2026-1845. A red vulnerability gate is answered by recompiling, not by
waiving (`SYSTEM_SPEC.md` §11) — this is the first instance of that rule.

**Reason.** `uv` resolves and hashes in one step and needs no bootstrap
dependency of its own, so the lock and the installer cannot disagree. The two
interpreter versions are forced by §4 of `docs/AI_CODE_QUALITY.md`.

## 2026-09-12 §10a — Pre-commit is part of the pinned development toolchain

Pre-commit 4.6.2 is locked in `requirements-dev.txt`, and `make venv` installs
hooks through `.venv/bin/pre-commit`. It does not install or invoke a global
tool and does not hide installation failure.

**Reason.** The hook runner enforces repository gates, so its version and
installation must be reproduced by the same hashed, wheels-only development
lock as the hooks it drives.

## 2026-09-08 §11 — A CI job arrives with the code it scans

Phase 0 ships `lint`, `types`, `test`, `security` and `size`. `postgres`,
`model`, `frontend` and `image` are added by Phases 1, 7, 9 and the phase that
introduces the Dockerfile respectively, each with its scan floor.

**Reason.** `docs/REBUILD_PLAN.md` Phase 0 lists `image` among the Phase 0 jobs,
but there is no image to scan and no runtime lock with packages in it; `trivy fs`
over this tree reports every target as *not scanned*. A gate that passes because
it found nothing is precisely the failure §4 of `docs/AI_CODE_QUALITY.md`
forbids, so the job waits for its subject rather than shipping vacuous.

## 2026-09-10 §12 — CAOS v2 is seeded from the CAOS-Final zip; its later specifications are lifted, not its code

Seed: the CAOS-Final snapshot of 2026-09-08 (38 files: the contract, the
vocabulary, the specifications, the Phase 0 gates and their tests), copied
verbatim into a fresh repository. The live `github.com/EricMG13/CAOS-Final`
reached `cf8c3a9` on 2026-09-09 with Phases 0–5 exited by their tests. The
owner chose to build those phases again here and to adopt from the fork only
the decisions they accepted. Lifted from `cf8c3a9` byte for byte:
`docs/IA_SPEC.md`, `docs/REBUILD_PLAN.md`, `docs/SYSTEM_SPEC.md`, `DESIGN.md`,
`CONTEXT.md`, `docs/archive/MODEL_BUILDER_SPEC.md`,
`docs/archive/REPORT_BUILDER_SPEC.md`, `tests/test_bundle_pin.py`, and the
vendor exclusion in `scripts/tracked.py`. `docs/AI_CODE_QUALITY.md`,
`docs/INITIALISATION_PROMPT.md`, `CLAUDE.md` and `README.md` are the seed's,
corrected in place.

Those pages cite CAOS-Final decision numbers this record does not carry. Each
resolves here:

| Cited | Subject | Here |
|---|---|---|
| §17 | the bundle is vendored at build `a43cb903` | §13 |
| §18 | no bootstrap cycle; readiness is CP-0's accepted artifact | adopted with Phase 3 |
| §21 | provider-call recovery: the attempt row is the call identity | adopted with Phase 4 |
| §23 | the model extension placed CP-MODEL beside CP-CF | overridden by §48 → §14; CP-CF alone |
| §24 | the catalog says what is live, the manifest what its bytes are | adopted with Phase 5 |
| §25 | a module selects only a calculator its own folder ships | adopted with Phase 5; host folders per §17 here |
| §31, §41 | SonarQube as the third reviewer; CI analysis with coverage | §15 |
| §38 | the plan is kept true; an exited phase's debt is the current phase's | adopted here, below |
| §45 | `live_sources` view; the first logger owes the sentinel test | adopted with Phases 1–2 and 5 |
| §48 | no model build, no publication module; the host renders the deliverable | §14 |

Adopted process rule (their §38): when an entry overrides a specification, the
overridden text is corrected in place and cites the entry; a phase is exited
by its named tests; a deliverable an exited phase did not ship is owed by the
current phase, never added back to the exited one.

**Reason.** The seed is small enough to read in full and its gates are the
definition of done; the fork's five exited phases are the work this plan
chooses to do again, frontend first, against the corrected specification. A
lifted page that cited a number nobody could look up would be exactly the
drift `docs/AI_CODE_QUALITY.md` §1 measures, so the map above is part of the
seed.

## 2026-09-10 §13 — The Deploy V bundle is vendored at build `a43cb903`

`vendor/deploy-v/`, copied verbatim from `/Users/ericguei/Documents/caos test/deploy_v`,
minus `.DS_Store`; upstream `github.com/EricMG13/Deploy-V@c4d2e356`. Build id
`a43cb903ca2751f79e77b6da71f6ea131b8462a32e1b549d65fd0f67389d185f` from the
bundle's own `DEPLOY_V_INTEGRITY_v1.json`, whose SHA-256 is
`2fc17570822e33365722dbbab8c408babba1d3d3de0a267ab47009436eae2823` — the one
vendored file the manifest cannot cover. The host does not mint an identity
for something that ships with one.

`tests/test_bundle_pin.py` hashes every file the manifest covers and asserts
the facts the specification rests on: typed edges live in
`catalog.profiles.*.edges` of
`skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json` (25
OPTIONAL, 22 ADVISORY, one QA_GATE, 44 REQUIRED, and no CONDITIONAL edge in
this build); `navigation.dependencies` is 97 untyped pairs; 18 pathways, 10
FULL and 8 LITE; CP-PARSE absorbed by CP-0; `preparation_stage.runnable:
false`; `research_extension` at stage 99. A second verifier runs the bundle's
own `verify_package.py` read-only. Gates do not scan `vendor/`: it is
authority we never edit (§6), so a finding inside it names something no PR is
allowed to fix.

**Reason.** `docs/ADVERSARIAL_REVIEW.md` W2: the authoritative bundle could
not be checked from the checkout, and no acquisition location or expected
digest was recorded. Both are recorded here, and the pin test fails before any
route the system runs can change under it.

## 2026-09-10 §14 — The host places no model build and no publication module; the deliverable is rendered by the host

Adopted from CAOS-Final §48 (2026-09-09), whose reasoning is retained in full
in `docs/archive/` banners and summarised here. CP-MODEL and CP-MEMO are not
placed. The model extension appends CP-CF alone. The deliverable is one HTML
file the host renders from the frozen snapshot — the accepted artifacts in
route order, every figure carrying its citation — never overwriting, printing
to paper. The host's chain around it is unchanged: opinion on the exact
revision, freeze, filing that refuses the signer and the freezer, the detached
receipt, the package verifiable with the standard library. The original
one-process deployment is superseded for repair Phase 4 by §39's single API
plus one PostgreSQL-backed worker; no workbook/publication service is restored.
Nothing installs LibreOffice or poppler. The Model section shows CP-CF's
projection, read-only. The workbook and publication contracts are archived
verbatim under `docs/archive/` for a build that brings them back; `make
test-model` and the `model_parity` marker leave with them.

**Reason.** The image: LibreOffice, poppler and a font are 482 MB across 176
packages, 63 % of a 763 MB image against 281 MB without, and 176 packages of
standing CVE triage `pip-audit` does not cover. Nothing smaller conforms: both
modules mandate the binaries in their own hard gates and have no Python-only
mode. Not placing them is no deviation: both are `navigable: false` and appear
in no pathway's node list. The cost is no workbook an analyst can stress and
no Word memo for a committee pack; the day a committee needs either, this
entry is what a later one overrides, with the 482 MB coming back with it.

## 2026-09-10 §15 — SonarQube Cloud is the third reviewer

SonarQube Cloud, project `EricMG13_caos-v2` in organisation `ericmg13`, bound
to the repository. Until Phase 1 lands code with a coverage report it runs as
automatic analysis, configured on SonarQube Cloud's side; the required check on
`main` is `SonarCloud Code Analysis`. Phase 1 moves the analysis into a
`sonarqube` CI job that reads `sonar-project.properties`
(`sonar.sources=scripts,server,methodology`, `sonar.tests=tests`,
`sonar.exclusions=vendor/**`, `sonar.python.version=3.14`, the coverage
report), refuses to run with an empty `SONAR_TOKEN`, and pins the scan action
to a commit — the shape CAOS-Final reached in its §31 and §41. The seed's
CodeRabbit configuration is removed with this entry.

**Reason.** The owner's choice, made with the alternatives in view: CodeRabbit
needs its app installed on a new repository and a configuration nobody here
had measured; no third reviewer at all loses the one reviewer with a different
blind spot from the two agent passes. Automatic analysis first because a CI
analysis with nothing to cover is a job that scans nothing.

## 2026-09-10 §16 — The provider is OpenRouter, called with the standard library

`server/provider.py` (Phase 5) posts to
`${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}/chat/completions` with
`urllib.request` and `json`: `Authorization: Bearer`, `stream: false`,
`provider: {"allow_fallbacks": false}` so one run has one provider identity.
The model id comes from `OPENROUTER_MODEL`, with no default — unset means there
is no live provider. Each configured model carries a dated `(input, output)`
price as `Decimal` that drives the reservation ceiling (invariant 8); the
charge is the `usage.cost` the provider reports, parsed with
`parse_float=Decimal` (invariant 7); the response id is kept on the attempt
row as `generation_id` for later reconciliation. Refusals are a closed set:
`PROVIDER_CALL_INVALID` (400, 401, 402, 403, 404, 413, 422 — never retried),
`PROVIDER_UNAVAILABLE` (408, 429, 5xx, a transport error, a timeout — the
attempt stays indeterminate with its reservation), `PROVIDER_OUTPUT_TRUNCATED`
(`finish_reason` `length`), `PROVIDER_REFUSED` (`content_filter`),
`PROVIDER_RESPONSE_INVALID` (a body that is not JSON, or no `usage.cost`). The
body is never quoted: it can echo the prompt.

The repository reads `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` and
`OPENROUTER_BASE_URL` from the environment and nothing else — no dotenv
library, no profile on disk. Locally the developer keeps them in an untracked
`.env` that `.claude/settings.json` denies to `Read` and refuses to every Bash
command; `make test-provider` exports the two names and echoes nothing. A test
that needs the credential skips with its reason when it is absent, and
`CAOS_REQUIRE_PROVIDER=1` turns that skip into a failure — the `provider` CI
job runs on a schedule and on dispatch, never on a pull request, with the key
as a repository secret and the model id as a repository variable. The key
never appears in a file this repository tracks, in a log, or in a refusal.

**Reason.** The owner's provider, and their key. The standard library is
chosen over a vendor SDK because retries are unwanted (a retry is a new
reservation, CAOS-Final §21 and §37, adopted with Phase 4), a non-streaming
call returns one JSON body, and the chat-completions shape is stable; a
provider suite that never called the provider would be the vacuous pass
`docs/AI_CODE_QUALITY.md` §4 forbids, hence the required nightly run.

## 2026-09-10 §17 — Host skill folders live beside the bundle, not inside it

A host-authored module (the first is CP-CF, Phase 7) lives at
`methodology/skills/<slug>/` with `SKILL.md`, `references/` and `scripts/`,
and a generated `methodology/skills/HOST_INTEGRITY_v1.json` in the same
`{bytes, sha256}` record shape as the bundle's own integrity file, written by
`scripts/host_manifest.py` and never by hand. The bundle reader merges that
manifest into the digests it verifies at use, so host bytes are checked
exactly as upstream bytes; a run's pinned build is the pair
`build_id:sha256(HOST_INTEGRITY_v1.json)`.

**Reason.** `SYSTEM_SPEC.md` §3 wants additions in new skill folders with
regenerated manifests, and inside `vendor/deploy-v/skills/` that is impossible
without editing upstream: `verify_package.py` refuses an unindexed skill
folder, and its `--refresh` rewrites six upstream files and moves the build id
away from the one §13 pins. Beside the bundle, upstream stays byte-identical
and the host addition is still authority verified on the bytes at use.

## 2026-09-10 §18 — The workspace consumes the design system as vendored source and tokens

`frontend/src/ds/` carries the predecessor's shared primitives copied from
`github.com/EricMG13/Credit-Operating-System` at `f454c654f`
(`caos/frontend/src/components/shared/{TextInput,ActionReason,SurfaceState}`,
`components/pipeline/atoms.tsx` for `Tag`, `lib/use-modal-a11y.ts`,
`lib/pipeline/sev.ts`), each with its blob hash and the change made to it in
`frontend/src/ds/VENDORED.md`; `Panel`, `StatCard`, `SectionHeader` and
`StatusGlyph` were read and not carried, because the sections draw the design
project's panel markup and no surface needs the other three. Two changes are substantive:
`useModalA11y` takes the opener as an argument and never reads
`document.activeElement` (`IA_SPEC.md` §7), and `SurfaceState`'s kinds are the
seven of `IA_SPEC.md` §6 with the `DESIGN.md` severity shapes. The shell
stylesheet `frontend/src/styles/caos.css` is the design project's
`caos-shell.css`, `caos-shell.additions.css` and `caos-evidence.css`
(`docs/design/DESIGN_HANDOFF.md`) ported with every colour bound to a token.

Tokens are the bound design system's values as `DESIGN.md` lists them
(`--caos-accent #4f8cff`, `--caos-border #262633`, `--caos-muted #8a8a9a`,
`--caos-panel #12121a`, `--caos-elevated #1a1a24`). The predecessor's
`globals.css` re-tuned four of them (`#63a1ff`, `#34384a`, `#a1a1b5`,
`#11131d`); that tuning was a contrast finding in the critique, not a token
source, and is not adopted. Four on-dark text tints
(`--caos-{success,warning,critical,accent}-bright`) are derived here for
status copy; they are signal, never decoration. The app declares
`--font-sans|mono|display` as system stacks; no web font. Nothing loads the
design system's `_ds_bundle.js` (a React 18 IIFE built for the old
information architecture) and nothing depends on the private `caos-frontend`
package.

**Reason.** The primitives worth keeping are the critique's preserve column
(`docs/design/BRIEF.md`): the refused-but-visible action, the measured
scroll-region focus, the modal focus stack. Copying source with a recorded
hash keeps them auditable without a dependency on a package this repository
cannot pin; the bundle runtime would carry the discarded rails, palette and
persona shell with it.

## 2026-09-10 §19 — The frontend toolchain and its dependencies

`frontend/` is `caos-workspace`: Vite 6, React 19, TypeScript 5.9, Tailwind 4
through `@tailwindcss/vite`, `react-router` 7 — a single-page application
exported statically, `scripts/export-sections.mjs` copying `dist/index.html`
to `dist/<slug>/index.html` for the nine section URLs and every pre-v2 slug in
`src/app/routes.json`. No Node in production. Dev and preview serve the
fixtures at the wire's routes from `vite.config.ts`; the production build
carries none of them.

Dependencies, pinned exactly in `frontend/package.json` and hashed in
`package-lock.json`: `react`, `react-dom`, `react-router`, `tailwindcss`,
`@tailwindcss/vite`. Development only: `vite`, `@vitejs/plugin-react`,
`typescript`, `vitest`, `jsdom`, `@testing-library/{react,dom,jest-dom}`,
`@playwright/test`, `playwright`, `axe-core`, `eslint`, `typescript-eslint`,
`eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`, `prettier`, and the
type packages `@types/{react,react-dom,node}`. Nothing else: no HTTP client,
no icon set, no chart library, no motion library, no PDF or canvas export,
no model SDK — the predecessor carried all of those and the workspace needs
none (`IA_SPEC.md` §8: no chart that carries a number the passport cannot
explain). A new package is a new entry here.

Gates that arrive with this code: the TypeScript vocabulary gate
(`frontend/scripts/check-vocabulary.mjs`, the same `ENFORCED` set as
`scripts/check_vocabulary.py`, asserted by
`tests/test_vocabulary_rules.py::test_ts_gate_enforces_the_same_tokens`), an
axe matrix over three engines, nine routes plus every fixture state and three
viewports with a completeness floor, and a Playwright workbench smoke with
`retries: 0`; the `frontend` CI job runs them (`docs/DECISIONS.md` §11).
`playwright` is pinned to the release whose browsers this machine already
caches.

**Reason.** The owner chose Vite + React 19 + TypeScript over the
predecessor's Next.js (`docs/DECISIONS.md` §12): a static export has no server
to trust, and one process is the deployment shape (`SYSTEM_SPEC.md` §11).
Exact pins because a floating range is a dependency change nobody recorded.

## 2026-09-10 §20 — The store is psycopg 3 over hand-written SQL, and its schema is applied rather than migrated

`psycopg[binary]==3.2.12`, the first entry in `requirements.in` and the only
runtime dependency Phase 1 adds. `requirements-dev.in` now ends with
`-r requirements.in`, because a suite that exercises the store needs what the
runtime installs. No ORM and no migration framework.

`server/store/schema.sql` is the declared schema and carries no `IF NOT EXISTS`.
`apply_schema` takes a transaction-scoped advisory lock, applies the whole file
against a database nothing has applied a schema to, and records the SHA-256 of
the text it applied in a `store_schema` bookkeeping row. A database built from a
different declared schema is refused — `STORE_SCHEMA_DRIFT`, the code alone,
never a schema body — rather than reconciled.

The suite runs against a real PostgreSQL named by `CAOS_TEST_POSTGRES_URL`,
taking a database of its own per test and dropping it after. Absent the
variable it skips with its reason; `CAOS_REQUIRE_POSTGRES=1` turns that skip
into a failure, which is what the `test` CI job sets against a digest-pinned
`postgres:17-alpine` service (§11: a job arrives with the code it scans).

Correction in place, per §12's adopted process rule: `CLAUDE.md`'s "where things
live" listed `storage/`. `SYSTEM_SPEC.md` §2 names `server/store/schema.sql`
explicitly and is the specific statement, so the contract's line is corrected to
`server/store/` rather than a second location being created to satisfy it.

**Reason.** The transactional rules Phase 1 exists to honour are written in SQL
terms — the run row lock that orders `run_events.seq`, the conditional update
whose zero rows mean no event (`SYSTEM_SPEC.md` §2) — and hiding exactly those
is what an ORM is for. The binary wheel keeps a build toolchain out of the
image. Drift is refused rather than migrated because `IF NOT EXISTS` over an
older database succeeds statement by statement while leaving the missing column
unmentioned until the first write to it, which is the one failure applying a
schema at startup exists to catch. This repository has never deployed, so there
is no data a migration would have to carry; the day there is, that is the entry
which overrides this one.

## 2026-09-12 §20a — Ordered PostgreSQL migrations preserve the legacy baseline

Supersedes §20's refusal-only upgrade policy for REPAIR_PLAN Phase 2.
`server/store/schema.sql` remains byte-for-byte the legacy baseline. The explicit
host-owned `MIGRATIONS` tuple starts with `0001_legacy`; append reviewed SQL files
under `server/store/` in order. Never modify an applied entry. No ORM, dependency,
application table, or externally selected migration SQL is added by this slice.

`store_migrations` records ordered version, name, SHA-256 and application time.
The singleton `store_schema.applied_digest` becomes the SHA-256 of the JSON
encoding of all ordered `(version, name, digest)` entries. This also binds history
length, so a missing final row cannot masquerade as an older prefix. A verified
legacy schema digest with no history is adopted without rerunning its DDL.
Fresh creation and legacy adoption then use the same prefix advancement path.
Unknown, edited, reordered, missing, or newer applied history refuses startup.

The existing advisory transaction lock serializes starters. Migration DDL,
history, and the head digest commit together; failures roll back and release
the lock, including interruptions. Schema/PostgreSQL failures carry only the
typed `STORE_SCHEMA_DRIFT` code. Autocommit refuses before mutation. Startup
continues to use a fresh connection. `apply_schema` owns and finishes the caller's
transaction, including an implicit read transaction, as it did before; call it
before business writes. There is no new pre-commit. Repeat startup does not
update existing history timestamps or business records.

Checksums detect declared migration/history disagreement, not arbitrary DBA
changes to both schema and metadata. Migrations must be transactional SQL with
no transaction-control statements or external effects. Future migrations must
preserve existing data and pass the populated-database tests. No automatic
downgrade exists. See [the backup/restore procedure](MIGRATIONS.md).

## 2026-09-10 §21 — PDF text is extracted with `pdfminer.six`

`pdfminer.six==20260107`, the second runtime dependency. It is what turns a real
PDF into the tokens invariant 11 needs: it exposes a layout tree of
`LTTextBox` → `LTTextLine` → `LTChar`, which maps onto the three things a token
must carry — the region a quote may not leave, the line it sits on, and a
rectangle taken from the characters themselves rather than estimated.

`server/evidence/pdf.py` implements the same `Extractor` protocol the plain-text
extractor does, so nothing above the seam changes: ingestion, block packing,
citation anchoring and the refusals are all unaltered.
`docs/REBUILD_PLAN.md` owes `test_citations_anchor_in_an_extracted_pdf` from
Phase 2 and this is what pays it.

It brings `cryptography` transitively, for encrypted PDFs. That is the real cost
of this entry and it is worth stating plainly: a large compiled dependency with
its own CVE stream, in an image that otherwise has none. It is accepted because
the alternative is a coordinate index the host derives from something other than
the document — which is invariant 11 with the evidence taken out. Both install
wheels-only under `--require-hashes --only-binary :all:`, checked on 3.14 before
this entry was written.

The fixture the exit test reads is a PDF this repository builds byte by byte
rather than a binary checked into the tree. It is a real PDF — `pdfminer` parses
it through the same path as any other — and it is one a reviewer can read.

**Reason.** The predecessor's locators were line ranges over extracted text (§9),
so "one click from its evidence" meant one click to a line range. Coordinates are
the fix, and coordinates have to come from the document. The choice of library
follows CAOS-Final, which reached the same requirement and the same answer.

## 2026-09-10 §22 — The HTTP surface is FastAPI, and it fails closed on identity

`fastapi==0.141.1` and `uvicorn==0.52.4` at runtime, `httpx==0.28.1` in the
development toolchain for `TestClient`. FastAPI brings `starlette` and
`pydantic`; the last of those is the reason it is the right choice rather than a
default one. `SYSTEM_SPEC.md` §9 asks that every JSON success serve a *named*
model with `extra="forbid"` in both directions, and a pinned key set asserted by
a contract test. That is a description of a pydantic model, and writing it by
hand would be re-implementing a library this repository would then have to
maintain.

**Identity fails closed.** `SYSTEM_SPEC.md` §8 allows development to trust a role
header and requires production to derive role from OIDC groups only. The switch
is `CAOS_TRUST_ROLE_HEADER`, and it is **off unless explicitly set to `1`** — the
convenience is opt-in, not opt-out. An environment variable that has to be set
to *disable* trust is one a misconfigured deployment forgets, and the failure is
silent and total. With it off, a client-supplied role header cannot escalate:
`test_production_never_trusts_role_header`.

**Unknown and unauthorised are the same answer.** Both are 404
(`test_unauthorised_case_is_private_404`). A 403 on a case a stranger may not see
tells them the case exists, which is the whole of what they were trying to learn.

`uvicorn` is installed but nothing in this repository calls it: the image's
entrypoint gains a process with this entry, and `make dev` stops failing.

**Reason.** The alternative to a framework here is hand-rolled routing, request
parsing and response validation, which is the part of a web stack most likely to
be got subtly wrong and least interesting to own. The dependency is accepted for
the model layer specifically; the routing is what comes with it.

## 2026-09-11 §23 — The body a verdict is measured against is a **qualification set**

`docs/REBUILD_PLAN.md` Phase 10 was written around a *corpus*: "the corpus
harness", "corpus digest", and an exit test named
`test_a_verdict_binds_provider_corpus_build_date_expiry_and_reviewer`.
`CONTEXT.md` lists **corpus** as a synonym for **source set**, and
`scripts/check_vocabulary.py` enforces it on identifiers — so that exit test
could not be written under the name the plan gave it. Two of this repository's
own controls contradicted each other, and the phase could not start until one
of them moved.

**The gate was right and the plan was wrong.** Not because a gate outranks a
plan, but because the concept the plan meant is genuinely not a source set. A
source set is immutable, versioned, and pinned to one run (`SYSTEM_SPEC.md` §5).
The thing a verdict is measured against is a body of *cases* and their answer
keys that spans runs and outlives any one of them. `CONTEXT.md` had no term for
it, which is why the plan reached for the nearest available word and picked one
that was already taken.

So `CONTEXT.md` gains a term — **qualification set**, "the immutable cases and
answer keys one verdict is measured against" — and Phase 10 is corrected in
place to use it, per §12's adopted process rule, the same way §20 corrected
`storage/` to `server/store/`. The exit test is
`test_verdict_binds_provider_qualification_set_build_date_expiry_and_reviewer`.
`docs/AI_CODE_QUALITY.md` §5 is corrected in the same breath; it was the only
other page spelling the concept the old way.

**`corpus` stays banned, and stays pointing at source set.** It is not listed
again under the new term. `banned_terms` maps a synonym to a term last-wins by
token, so a second listing would silently re-point it, and the gate would start
telling a reader who wrote `corpus` meaning the pinned documents of one run to
spell it "qualification set". The cost of leaving it where it is: someone who
writes `corpus` meaning the qualification set is refused and told to use
"source set", which is the wrong half of the answer. That is a worse message
and a better outcome than a wrong word admitted — the identifier is refused
either way, and the reader who reads this entry finds the right term one line
below the one they were pointed at.

`benchmark` and `golden set` are the synonyms the new term displaces, both
ENFORCED in both halves of the gate (`scripts/check_vocabulary.py` and
`frontend/scripts/check-vocabulary.mjs`, kept equal by
`tests/test_vocabulary_rules.py::test_ts_gate_enforces_the_same_tokens`).
Neither carries an ordinary technical meaning in this repository: nothing here
measures performance, and no tracked file names either word today.

**Reason.** A glossary with a hole in it is how a synonym gets minted: the word
that was reached for was not chosen over the right one, it was chosen because
the right one did not exist. Adding an exemption for `corpus` would have kept
the plan's wording at the price of the one token the gate most needs to hold —
the two spellings of the pinned source set are exactly the two lineages
`CONTEXT.md` exists to prevent. The plan is the cheaper thing to correct, and
correcting it in place is what §12 already says to do.

## 2026-09-11 §24 — A qualification set has a declared on-disk form: a manifest and the documents beside it

`CLAUDE.md`'s Phase 10 ledger asked for this in two entries and blocked two more
on it. A set that lives only in memory is enough for a digest to be checkable
and not enough for two people to be sure they hold the same set without
comparing digests by hand — and once §23's **qualification set** grew to carry
each case's documents as bytes, writing one in Python stopped being reasonable
at any size a reviewer would care about.

**A directory, not a single file.** A case carries documents and documents are
bytes. Base64 inside one JSON file would keep the form self-contained at the
price of the thing it exists for: a reviewer handed a set must be able to open
the documents it is measured over. So the form is a manifest naming its cases,
and the documents beside it:

    acme-q3/
      qualification.json
      documents/acme-2026/report.txt

**The digest does not move.** `qualification_set_digest` already covers each
document's filename and the hash of its bytes, so a set read from disk digests
exactly as the same set built in Python. That is the property the form rests on
and the reason it is worth having: a verdict's `qualification_set_sha256` can
name a directory somebody is holding. `server/qualification/on_disk.py` adds
nothing to the digest and takes nothing away — it produces the same dataclasses
from bytes rather than from a literal, and a test asserts the two agree.

**A document's filename is its path's last segment.** One field rather than
two. Two would be two things that can disagree, and the digest covers the
filename: a manifest naming a document `report.txt` while reading `other.txt`
would digest as the first and admit the second.

**Read the way a signed verdict is read.** The manifest is authored, possibly
not here and possibly years later, so it gets `read_verdict`'s treatment — a
closed shape, undeclared keys refused, nothing coerced. Malformed is one code,
`QUALIFICATION_SET_FILE_INVALID`, because it has one remedy: fix the file. A
document path leaving the set's own directory is kept apart as
`QUALIFICATION_SET_PATH_ESCAPES`, because its remedy differs and so does its
seriousness — it is the one refusal here about safety rather than shape, and it
is decided by resolving the path and comparing it to the resolved root rather
than by inspecting the string for `..`, which only answers the spellings someone
thought of.

**No new dependency.** `json`, `pathlib` and `hashlib`, all standard library.
The form is readable by anything, which is the same promise
`server/deliverable/package.py` makes about an audit package.

**Reason.** The alternative was leaving the set a Python literal and letting
each caller invent its own serialisation, which is how two people end up
measuring against sets they believe are the same. A declared form with one
loader makes "do we hold the same set" a question with a mechanical answer, and
it is the precondition three other ledger entries were waiting on.

## 2026-09-11 §25 — An accepted artifact records the model that produced it, from the host's own configuration

`CLAUDE.md`'s Phase 10 ledger: a verdict binds `provider` — a string in a
document this repository did not write — and nothing could compare it against
what the runs behind it actually called, because nothing a run left behind named
a model. The charge was recorded and the artifact was recorded; who produced
them was not. Invariant 3 says the host owns identity, and in this one place it
did not.

**The identity is the host's configuration, not the provider's report of
itself.** `OpenRouter._post` sets `"provider": {"allow_fallbacks": false}`
precisely so that the model asked for is the model that answers, so the host
already holds the fact. Reading `model` back out of the response body would be
taking a claim where a fact was available — the same mistake invariant 3 names
about provider-claimed frontmatter, and it would have made every live call
depend on a response shape this repository cannot verify without a credential.
`CompletionProvider` therefore declares `model` and `OpenRouter` already had it.

**A read-only protocol member.** Declared as a property rather than as
`model: str`, because a plain annotation on a `Protocol` is a read-write member
and `OpenRouter` is a frozen dataclass — the mutable form would have left the
real provider failing to satisfy its own protocol. The type checker caught that
before a caller did, which is the argument for `mypy --strict` in one line.

**On the artifact, not on the attempt.** `run_attempts` exists before the call
and knows nothing yet; `artifacts` is the row `accept_attempt` writes when a
call has completed. Recording the producer there is one insert rather than an
insert and an update, keeps the `ON CONFLICT DO NOTHING` replay semantics
exactly as they were, and lets both columns be `NOT NULL` — an artifact whose
producer is unknown is what they exist to make impossible. An attempt that was
charged but never accepted has no producer recorded, which is the same case as
having no artifact.

**`generation_id` travels beside `model` and is not the same kind of thing.**
The model is the host's fact; the generation id is the provider's own handle for
the call, kept so a bill can be reconciled against a run. They are stored
together and read apart.

**`Accepted` groups what one completed call produced.** Four keyword arguments
tripped the argument ceiling, and the answer is the one `Execution` and
`Harness` already use: none of artifact, charge, model and generation id is
meaningful without the others. It lives in `server/store/runs.py` rather than
beside `ProviderResult`, so the store does not import from the engine above it.

**Reason.** Without this the harness holds one half of a comparison it can never
complete: it knows which runs a verdict covers and cannot know what they called.
The alternative — trusting the reviewer's `provider` string — is what the ledger
entry already calls a binding rather than a fact. This makes the other half a
fact the store holds, and is the precondition for refusing a verdict that names
a model the runs behind it never used. That refusal is a separate change.

## 2026-09-11 §26 — A quote that does not anchor refuses its claim, not the module's answer

The first live run over a real issuer — Virgin Media O2's Q4 2025 and Q1 2026
earnings releases and its Q1 2026 bond report, `FULL_CREDIT_ASSESSMENT` on
`openai/gpt-4.1-mini` — stopped at CP-1 after three attempts. The answers were
mostly sound: in the one inspected, twelve of sixteen citations anchored. The
four that did not were wrapped sentences whose second line the extractor put
in another region, and table rows assembled from cells that are not adjacent
in reading order. `execute_module` refused the whole envelope on the first of
them, so twelve good citations bought nothing — and at one miss in four, a
module with a dozen claims almost never passes, and nineteen in a row never
will.

**The claim goes, not the answer.** A citation refused `CITATION_NOT_LOCATED`
or `CITATION_AMBIGUOUS` refuses the claim resting on it, and a claim survives
only when every citation it carries anchors: a figure keeps all of its
evidence or none of it. Invariant 11 is unchanged — the quote is still refused
before it reaches the artifact, which is all `SYSTEM_SPEC.md` §5 and
`CLAUDE.md` say. Refusing the whole envelope was `execute_module`'s rule, not
the invariant's.

**Everything else still refuses the answer.** A statement `BoundaryText`
refuses, a citation naming undelivered evidence, an undeclared key, a claim
carrying no citation: those are the module breaking the contract rather than
missing a quote, and they refuse the envelope as before. An answer left with
no claim is refused with its first quote's code, which is what a module that
anchored nothing always got.

**The artifact counts what it refused.** `claims_refused` is the host's fact,
stored in the canonical envelope and so covered by its digest: a reader
holding only the artifact can see that the module asserted more than it
established. A silent drop would have made a thin answer indistinguishable
from a short one.

**Reason.** The alternatives were a matcher loose enough to accept the rows
and the wrapped lines — the phrase assembled across a gutter that §5 exists to
refuse — or re-asking the model, a second call per module to recover claims
already known not to anchor. Refusing per claim keeps the matcher exactly as
strict as it was and gives up only what it could never have kept.
## 2026-09-12 §27 — The gate's verdict reaches the store, and decides what runs

`server/engine/route.py` has carried `readiness_from` since route resolution
landed, and nothing could reach it: `ENVELOPE_KEYS` refused every key but
`claims`, so the only readiness the host had ever seen came from a test
fixture, and CP-0's verdict on a nineteen-node route decided nothing.

**The bundle's key, not a host invention.** The envelope carries
`content_to_module_map`, the name CP-0's own payload schema declares, so the
reader that exists is the reader that runs. Rows keep three of the schema's
five fields; `evidence_demand` and `active_representation_ids` are what
per-module evidence selection will need and are recorded as not kept.

**Bounded, and complete.** Module ids must be the pinned route's, less the gate
itself; statuses are the bundle's four; the effect is `BoundaryText`. Coverage
is required — `READINESS_INCOMPLETE` — because CP-0's instructions make
identifying the runnable modules its job, and a gate that silently said nothing
about a module would be a gate that cleared it by omission.

**A module's own verdict decides its state.** CONDITIONAL and BLOCKED are both
"not cleared"; READY_WITH_LIMITATIONS is RESTRICTED, which runs and carries the
limitation; READY leaves the edges in charge. A blocked node costs no call and
no charge. Repair decision §39 supersedes the original blocked-but-complete
rule: unresolved required obligations keep the run recoverably blocked. This
is a repair target until its implementation and phase exit tests are accepted. The run surface carries
the verdict as `NodeView.gate_verdict`, because a node the gate blocked has no
unmet edge for `waiting_on` to name — and a state with no cause is the thing
`NodeView` ("a node's state and the reason for it") and `waiting_on` ("a surface
reporting BLOCKED with no cause tells a reader the run is stuck without telling
them what it is stuck on") each exist to prevent. `SYSTEM_SPEC.md` §9 is the
wire's strictness rules and says nothing about it; those two docstrings do.

**Only the gate may answer.** For every other module the host asks for no map,
and one returned anyway is an undeclared field — the same answer `extra=forbid`
gives any other stray key.

**Reason.** The alternative was a host-side gate reading document types, which
puts methodology in the host against invariant 4, with no classifier to read
them anyway.

## 2026-09-12 §28 — A module is handed its direct predecessors, as context

The first live run over a real issuer executed nineteen modules as nineteen
independent reads of the same documents. The bundle's own chain is the opposite:
each module consumes the registers of the modules before it, which is what the
co-pilot runs show and what `**Upstream:** CP-1 …` in every SKILL.md asks for.

**Direct predecessors, from the pin.** The sources of every edge into the node,
in route order, read from the pinned route. Not transitive: a module sees what
it was meant to build on, and the route is what says so.

**From the store, not from memory.** `ModuleProvider` reads each predecessor's
accepted artifact through `artifact_digests`, the same reader the frontier uses
to decide what is accepted, so the chain and the frontier cannot disagree about
what a run has produced. A run resumed in another process has only the store,
and a caller's copy of what a module said is a claim rather than a fact
(invariant 3).

**Context, never evidence.** The section says so, and the rule that enforces it
was already there: a citation must name delivered evidence, so a module quoting
an earlier module's sentence is refused `CITATION_NOT_LOCATED`. On this tree
that refusal takes the module's whole answer with it; §26 is what narrows it to
the claim the quote rests on, and until §26 lands a chained module that mistakes
its context for evidence loses the answer rather than the sentence.

**What it is not.** The upstream section carries statements and quotes, because
that is what the envelope holds. The bundle's registers — the tables a module's
own payload schema declares — are a later phase, and until then a chained module
inherits sentences rather than a financial base.

## 2026-09-12 §29 — Canonical Markdown is the authoritative handoff

Deploy V's exact, validated canonical Markdown remains the analytical authority
and the downstream handoff. Typed UI fields are closed, validated sidecar
projections of it. The UI and host-rendered report are presentations of the
accepted Markdown and projections, not a second model-authored authority.

The host owns identities a module cannot establish: run, immutable source set,
extractor and extraction manifest, resolved route, bundle manifest/build,
adapter version, and accepted upstream artifacts. Those identities travel with
the handoff and are checked by the adapter; provider-claimed identity is never
substituted for them.

The catalog-selected CP-0 remains the single executable preparation/readiness
node. The host's extraction manifest is preparation metadata supplied to CP-0,
not another LLM route stage. `CP-PARSE` remains only as an authority alias for
archived compatibility; it is not inserted into the catalog route, so extraction
and preparation do not run twice. The no-Excel/no-Word decision and archived
workbook/publication contracts remain unchanged.

**Reason.** The current claims JSON discards the bundle's complete registers and
cannot become canonical merely because the host stores it. Adding a second model
summary would create competing authority; preserving the exact validated
Markdown and deriving presentation fields mechanically preserves one handoff.

## 2026-09-12 §30 — Local development uses one project-scoped Compose stack

Development uses the CI-pinned PostgreSQL image in two isolated services: a
persistent database reached by a least-privilege application role, and a
tmpfs-backed test-admin database. Both bind loopback-only deterministic ports;
blobs remain in the ignored project-local `.dev-data/blobs` directory. Stopping
the named Compose project removes neither the development volume nor blobs.

Python 3.14, security Python 3.12, Node 24, and pinned pre-commit remain the
existing toolchain; no dependency was added. GitNexus indexing uses only a
runner already present locally or installed on the machine and runs
`--index-only`.

**Reason.** Separate named resources make test cleanup unable to reach durable
development data, while one native Compose file is the smallest reproducible
service layer. Fixed synthetic local credentials are configuration examples,
not deployable secrets or permission to call a provider.

## 2026-09-12 §31 — Repair the pinned runtime base with four exact OS upgrades

The live official `python:3.14-slim` tag still resolved to the image's existing
digest, so changing the pin would not repair its twelve fixable HIGH/CRITICAL
OS findings. The image instead upgrades only the four affected installed
packages to the fixed trixie candidates: `gzip=1.13-1+deb13u1`,
`libpcre2-8-0=10.46-1~deb13u2`, `libsqlite3-0=3.46.1-7+deb13u2`, and
`perl-base=5.40.1-6+deb13u1`. `--only-upgrade` keeps the package set closed;
the verified simulation and build each reported four upgrades, zero additions,
and zero removals.

The dated provenance is Debian's package index plus its primary security
tracker entries for [gzip](https://security-tracker.debian.org/tracker/source-package/gzip),
[pcre2](https://security-tracker.debian.org/tracker/source-package/pcre2),
[sqlite3](https://security-tracker.debian.org/tracker/source-package/sqlite3),
and [perl](https://security-tracker.debian.org/tracker/source-package/perl).
The local image gate requires the same Trivy 0.70.0 as CI, proves that the JSON
scan examined targets, then rejects any fixable HIGH/CRITICAL finding with
`--ignore-unfixed`; no suppression or policy relaxation is permitted.

**Reason.** A no-op base re-pin leaves the findings in place, while a broad
unpinned OS upgrade changes unrelated runtime state. Four exact in-place
security upgrades are the smallest reproducible repair until an official fixed
base digest replaces them.

## 2026-09-12 §32 — Existing case row orders all case mutations

Case writes acquire the existing `cases` row before membership, run, audit or
gate rows. This includes source admission after CPU extraction and packing,
source withdrawal, grant/revoke, run creation, and run/route transitions through
`lock_run`. An absent audit head cannot serialize first approvals. Standing is
read after the case lock and retained through the governed commit, so revocation
and governed writes have one observable commit order. The whole governed unit,
including digest generation and audit/head insertion, rolls back on failure.

Supported mutations require explicit transactions at READ COMMITTED. The lock
helper checks the actual transaction isolation, including caller SQL settings;
autocommit and other isolation levels refuse `STORE_NOT_TRANSACTIONAL`. A
REPEATABLE READ snapshot taken before waiting could otherwise retain revoked
standing even after obtaining an unchanged case row. No automatic retries are
introduced. Existing implicit read transactions at READ COMMITTED remain valid.

Grant/revoke, admission and run creation leave commit/rollback to their caller.
Governed writes and existing run/route transitions complete their own units.
Callers must follow this order for all case mutations and must finish a setup
transaction before provider I/O. Runtime attempt creation and reservation each
commit before the provider call. Governed callbacks must not commit or perform
provider/network I/O. Source extraction occurs before taking the admission lock;
a caller already holding a setup lock remains responsible for its transaction.

**Ceiling.** Writes within one case serialize; different cases remain independent.
Finer locks are warranted only by measured throughput, not speculative parallelism.
No table, dependency, migration or global mutex is needed for this repair.

## 2026-09-12 §33 — Record extraction provenance without inventing legacy history

Migration `0002_extraction` adds append-only `source_extractions`, keyed by the
admitted source. A missing row explicitly means UNKNOWN; migration never guesses
which adapter produced historical tokens. Existing live-source evidence remains
readable. Recovery for future executable source sets is explicit readmission and
re-extraction by a known host adapter, never a provenance backfill.

Format version 1 stores canonical extractor identity JSON (`name`, algorithm
`version`, flat effective `config`, maximum 4096 characters), an output SHA-256,
and an extraction SHA-256. Config values are finite JSON scalars; text must
already satisfy BoundaryText normalization and bounds. Host implementations own
this identity: plain text declares its UTF-8/fixed-cell/page settings; PDF declares
its algorithm and installed pdfminer version/default layout settings. Filename
does not select an adapter. Custom host extractors explicitly declare an identity.

The output digest hashes a JSON object with `format_version: 1`, ordered `tokens`
(each token's text/page/region_id/line_id/x0/y0/x1/y1) and ordered `blocks`
(`[block_id, page, text]`). Coordinates are finite exact binary64 values before
both hashing and writing. Token text is recorded exactly as stored; packing still
applies the existing BoundaryText normalization. The extraction digest hashes
`format_version: 1`, document SHA-256, the extractor identity object and output
SHA-256. Both serializations use sorted keys, compact separators, UTF-8 with
`ensure_ascii=False` and `allow_nan=False`. Source/case IDs and preview metadata
will belong to the subsequent immutable source-set identity, not this content
identity.

All preparation and identity validation precede the shared case lock and writes.
Admission retains caller-owned commit/rollback; it adds no provider operation.
Database triggers refuse updates, deletes and truncation of provenance. These
constraints protect normal SQL mutations, not privileged schema/trigger removal.

This is a storage prerequisite only. Immutable source sets, run bindings and
runtime approval enforcement are subsequent slices; F04 remains open. The old
whole-case `source_set_fingerprint` remains compatibility behavior and is not an
enforced execution pin. Mixed-PDF dispatch and geometry fidelity remain Phase 3.

## 2026-09-12 §34 — Immutable source-set versions retain complete membership

Migration `0003_source_sets` stores a case-local positive version, format version
1, fingerprint and positive member count, with explicit immutable member rows.
`snapshot_source_set` takes Task6's shared case-first lock at READ COMMITTED,
captures all live sources and owns commit/rollback, including unchanged replay.
Call it after unrelated setup has committed. No provider/network I/O or retries
occur under its lock. `load_source_set` reads an exact case/version with a
caller-owned transaction and verifies count, provenance bindings and fingerprint.

The fingerprint uses §33's canonical JSON serialization and hashes an object
with `format_version: 1`, string `case_id`, and `members` ordered by source UUID.
Each member includes string source UUID, document SHA-256, filename, admission
timestamp normalized to UTC ISO-8601, canonical extractor identity JSON string,
output SHA-256 and extraction SHA-256. These fields are captured, not reloaded
from mutable source metadata. The stored extraction binding is recomputed from
document/extractor/output identity; output text/geometry remain bound by §33.
Empty, UNKNOWN and malformed sets refuse. No legacy identities are fabricated.

Unchanged current content returns the latest version. Changed content allocates
latest version plus one; returning to an earlier content state creates another
version with the same content fingerprint. Later admission never joins existing
membership; withdrawal preserves history. Historical loading does not authorize
withdrawn evidence: the existing live read predicate and one-query reads remain.
The old whole-case fingerprint remains compatibility behavior, not a run pin.
Run/approval/UI integration and automatic snapshots remain subsequent work.

Native PK/FKs enforce source/case consistency. UPDATE/DELETE/TRUNCATE refuse;
deferred INSERT checks on both tables require the exact immutable positive
count. A completed set cannot accept another member: every inserter sees at
least its existing complete membership plus its own row, so even concurrent
extra insertions fail. Missing headers refuse. This protects normal SQL changes,
not privileged trigger removal. The row checks cost O(N²) counts over sources,
not tokens; batch validation is warranted only by measured throughput.

## 2026-09-12 §35 — One immutable raw manifest governs bundle authority

`Bundle` selects its manifest during construction, before sharing with callers.
It retains only immutable raw bytes: the build ID, manifest SHA-256, selected
module entry and file hash expectations all derive from that one snapshot.
Parsed dictionaries returned to callers are fresh copies, never mutable cached
authority. Every identity/entry/file read verifies the current manifest against
the snapshot; verification also runs after assembly, immediately before provider
completion and after qualification matrix rows. A changed manifest refuses; an
existing Bundle never adopts a replacement, including whitespace-only changes.

The manifest ceiling is exactly 131,072 bytes (128 KiB), above the pinned
68,657-byte document. Each read requests at most the ceiling plus one byte and
refuses excess before JSON parsing. The consumed form requires authority
`DEPLOY_V_INTEGRITY_v1`, schema version `1.0`, a lower-case 64-hex build ID,
nonempty skills with unique module IDs, single-component folder names, and
file-hash objects including nonempty `SKILL.md`. Hashes are lower-case 64-hex;
declared lengths are nonnegative integers (not booleans), positive for the skill.
Duplicate JSON keys, non-JSON numeric constants, malformed/missing metadata,
invalid text and decoder failures refuse `AUTHORITY_BYTES_MISMATCH`. The byte
cap is the only explicit resource ceiling; no independent JSON nesting limit is
enforced. An absent module in an otherwise valid manifest remains
`AUTHORITY_MODULE_UNKNOWN`.
Refusals carry only the existing code, with underlying parse/filesystem errors
suppressed. Additional legitimate manifest fields remain intact and unconsumed;
this is no format upgrade or manifest rewrite.

Manifest-supplied paths are canonical relative POSIX names. Absolute paths,
parent traversal, alternate separator/normalization spellings and resolved
symlink escapes refuse before reading outside the manifest root, skills root or
selected module. `Path.resolve`/containment uses the standard library pattern
already present in the qualification loader without importing that layer.
Authority reads require resolved targets to be regular files, so static special
files refuse before open. This assumes host-owned paths are not maliciously
replaced concurrently between the file-type check and open; it is not a
privileged filesystem adversary sandbox. Module bytes are still read whole and
checked against both declared length and SHA-256; this slice introduces no
general module-file size ceiling.

Whole skill and module reference delivery, host CP-PARSE carve-out and the
existing `authority_digest` serialization are unchanged. Parsing a fresh copy
costs O(manifest bytes) per entry lookup; there is no additional cache or lock.
Persisted run comparisons, source/research/approval bindings, shared root
reference delivery and the §29 canonical Markdown runtime remain subsequent
work. This prerequisite does not close F01/F04 or change the claims-only runtime.

## 2026-09-12 §36 — Verify stored route identity and refuse late pin creation

Both `resolved_route` and `pinned_route` use one verified read of stored JSON,
profile, selection and digest. Decode the exact consumed object shape without
string/integer coercion; require nonempty unique route-node/module identities,
known unique typed edges with present endpoints, an acyclic closed graph in the
existing dependency order, and unique predicate keys paired with bounded text.
Malformed or inconsistent state refuses `ROUTE_IDENTITY_INVALID`; API readers
report this as the established sanitized 503 store failure. Missing pins remain
`None`; read transactions stay owned by their caller.

The installed catalog was measured: 18 selectable routes, at most 19 nodes and
88 edges, stages 1–19, node IDs at most 57 characters and module IDs at most 6.
Resource bounds are 128 nodes, 1024 edges, 128 predicates, 128-character ASCII
identifiers, stages 1–100 and the existing 4096-character `BoundaryText` predicate
value limit. Host research/model slots 99/100 remain supported. The coarse JSON
parse ceiling is 8,388,608 **characters**, enough for all bounded fields even
with worst-case ASCII Unicode escapes; this is not a byte-size claim or a
database transfer limit. Exact field/count bounds are the primary validation.
The vendor identity helper's two-digit stage grammar is not substituted.

The existing `route_digest` contract is unchanged: node arrays, sorted edge
arrays and the original predicate ordering. Stored JSON keeps its object shape;
predicate containers reach JSON serialization directly so malformed strings or
mapping pairs cannot become valid pairs through iteration. No second route
hash, catalog upgrade or generic serialization framework is introduced.

`pin_route` validates the same invariants, takes the shared case-first/run lock,
and owns one commit for the row and ROUTE_PINNED event. A valid exact replay
checks actual stored content and can return the historical digest after the run
is terminal, without adding an event. A new pin requires RUNNING and no attempt;
otherwise it refuses RUN_NOT_RUNNING or ROUTE_PIN_TOO_LATE. Conflicts leave the
existing pin/event intact. Autocommit is refused; refusal, database failure and
cancellation roll back or close the connection, including commit-time failures.

Append-only migration `0004_route_integrity` forbids normal UPDATE, DELETE and
TRUNCATE of route pins, including TRUNCATE CASCADE. Historical rows are preserved
without guessed inputs or automatic repair. Privileged trigger removal remains
outside this guarantee; corruption regressions explicitly disable only the
named row guard inside a transaction in their own disposable test databases,
restore it before asserting reader/proof outcomes, and verify failure cleanup.
Both legacy-upgrade and already-migrated backup/restore proofs retain native
catalogs, original rows and synthetic blobs; see MIGRATIONS.md.

This is a Phase2 prerequisite for complete run-input pins. It does not enforce
execution approvals, certify methodology selection, change canonical handoffs,
or close F01. Source version/fingerprint, coherent bundle identity, host adapter
and actual research content still need one complete run binding; runtime must
later reject route-only legacy runs before execution.

## 2026-09-12 §37 — Complete immutable run-input storage

`run_inputs` holds at most one complete pin per run, separately from the existing
route and captured source-set stores. The host derives the owner from the real
run, loads the selected case-local source version through `load_source_set`,
verifies the recorded route through `resolved_route`, and derives build/manifest
identity from one coherent `Bundle`. The caller selects only the run, source
version and research content. The existing executor now declares its actual
adapter as `claims-json-v1`; this does not claim the future Markdown adapter.

The format-1 fingerprint reuses §33's sorted, compact, UTF-8, ensure_ascii=False,
finite JSON hashing helper. It binds case UUID, source version AND verified
source fingerprint, verified route digest, Bundle build ID, exact raw-manifest
SHA-256, adapter version and canonical research JSON string (or JSON null for
absence). Run UUID owns the row but is excluded from this content fingerprint;
two runs with identical inputs may therefore share the same fingerprint.
Returning from source A to A+B and then A preserves the later distinct source
version even though the first and last source-content fingerprints agree.

Research accepts an exact JSON object or None. Object keys must already be
strings; tuple/bytes/custom values are refused. Every key/string must already
satisfy BoundaryText and NFC: reject normalization changes, do not silently
change reviewed content. The storage bounds are depth 16 (root depth zero),
4096 visited values including object keys and containers, 4096 characters per
key/string, signed 64-bit integers, finite JSON floats, and 65,536 canonical
UTF-8 bytes. None, {}, empty strings, booleans, integers and floats remain
distinct. Canonical serialization sorts object keys only and preserves array
order and exact accepted Unicode/text. The frozen slotted RunInput retains
only the immutable canonical string; callers parse fresh copies when needed.
These are storage safety bounds, not validation of the CP_DR linked lifecycle,
approved-plan hash, CP-0 anchoring or any source/tool authorization.

`pin_run_input` owns the case-first/run-locked transaction. `pin_route` and
`snapshot_source_set` commit and must be prepared separately; neither is called
inside complete-pin creation. Missing/unverified dependencies refuse. New pins
require RUNNING and no attempts; a valid exact replay can return after terminal
status without another event. Changing any bound input refuses rather than
rewriting history. One INSERT and one INPUT_PINNED event commit together;
refusal, database failure, cancellation and commit failure roll back or close.
Autocommit is refused. There is no network/provider call under these locks.

The historical loader verifies stored shape and canonical research, recomputes
the input fingerprint and compares source/route identities with their verified
records and the real run owner. It retains the caller-owned read transaction.
It never adopts today's Bundle/adapter identity: runtime must later compare
the recorded identity with actual executing authority before spend.

Append-only migration 0005 uses native PK and composite FKs for real run/case,
source case/version/fingerprint and route run/digest consistency. Native
UPDATE/DELETE/TRUNCATE guards preserve pins; original migrations and legacy
rows are unchanged. Privileged trigger removal is outside normal SQL guarantees
and is used only in owned disposable corruption regressions.

Real PostgreSQL evidence covers independent fingerprint components (including
pairwise different research briefs), exact replay/one event, first/second-write
and deferred-commit failure, cancellation/closed connection cleanup, observed
blocking same/conflicting first pins, independent cases, malformed dependencies
and content, native FKs/immutability, populated current-prefix upgrade and native
catalog parity. The 94 focused storage/migration cases passed; the owned restore
probe additionally restored a complete input with real captured provenance.
See MIGRATIONS.md and the task report for executed gate details. Approval/API/
runtime/evidence integration remains sequential work. F01 is still open, and
route-only legacy runs receive no invented complete input or execution bypass.

## 2026-09-13 §38 — Provider transport resource ceilings

The host permits at most 1,048,576 bytes in the complete encoded UTF-8 JSON
request and 4,194,304 bytes in a response body. Non-string prompts and non-byte
transport bodies refuse. Oversized requests make no transport call; successful
and HTTP-error streams read at most the response ceiling plus one byte and close
on every path. Oversized responses refuse before JSON parsing; no prefix is
accepted as a complete answer. Injected transports face the same byte checks.
Incomplete native HTTP framing refuses `PROVIDER_UNAVAILABLE`, including when
the received prefix happens to be valid JSON; bounded reads retain this check.

Every request sets `max_completion_tokens: 32768`, `allow_fallbacks: false`, and
`require_parameters: true`. The current [OpenRouter chat contract](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion)
names `max_completion_tokens` and deprecates `max_tokens`; its [routing contract](https://openrouter.ai/docs/guides/routing/provider-selection)
documents the required-parameter restriction. HTTPS-only, no redirects or retries,
and the existing 120-second transport/socket timeout remain. That timeout is not
a newly guaranteed end-to-end deadline. Malformed URL errors remain code-only.

These are host resource ceilings, not vendor-mandated values or a guarantee that
every canonical handoff fits. The bundle requires complete Markdown and appendix
registers; its 90–150-word opening is expressly not a token budget. A handoff may
not be shortened to fit. Phase 3 must prove the selected canonical route fits or
deliberately revise the host policy. No live compatibility or pricing claim is
made. Attempt-bound billing propagation, ending database read transactions before
calls, conservative priced reservations, runtime authority/evidence binding,
generation fencing, and blocked/QA terminal semantics remain separate repairs.

## 2026-09-13 §39 — Reconcile the repair plan, acceptance and continuation

The user requested correction of the plan and supporting documents after an
adversarial documentation review. This entry records the already-requested
repair target; it does not certify implementation or expand enabled routes.

**Authority.** The user's current instructions govern. This decision record
resolves design choices; `docs/REPAIR_PLAN.md` owns repair phases 0–6.
`docs/REBUILD_PLAN.md` and its phase labels remain historical baseline/test
records. System and IA specifications describe the target, with unfinished
repairs labelled. `docs/CLAUDE_CODE_HANDOFF.md` alone owns current task status
and exact accepted checkpoints; other entry documents link to it. Tracked
task briefs contain enough scope and evidence to resume without ignored logs.
An implementation commit is not task acceptance. A saved copy of the plan
points to the maintained repository document.

**Terminal semantics, superseding §27's old completion rule.** A run is
successful only when all required selected obligations and gates are satisfied.
An empty frontier with unfinished required work is recoverably blocked.
Validated `RESTRICTED` output remains usable within its declared limitations;
it is not inherently malformed, blocked or QA-cleared. CP-5 clearance is
validated independently. These are pending Phase 2/3 implementation gates,
not statements that the existing loop already enforces them.

**Execution shape, superseding §14's one-process limit.** Phase 3 proves one
canonical route through the existing runtime/validation boundary using a
deterministic provider. Phase 4 adds one durable worker beside the API, using
PostgreSQL claims/leases and the same runtime/validator; no new broker,
checkpointer or database. Worker crash/restart and deployed authentication
proof belong to Phase 4. There is no Phase 3 dependency on that future worker.

**Phase acceptance.** Phase 3 engineering acceptance is offline and distinct
from live qualification. Every dependent phase still requires its predecessor's
recorded acceptance and the user's applicable authorization. Phase 6 release
acceptance requires capped, separately authorized live evaluation of the final
candidate and authenticated verdicts. Review-driven changes to candidate
identities invalidate affected evidence: rerun relevant engineering/hosted
checks, and repeat affected live qualification only within explicit spend
authorization. Without that evidence, release acceptance remains blocked.

**Forecast prerequisite.** Before enabling CP-CF in Phase 5, choose a catalog
route containing CP-1, CP-2G and CP-4 and prove their canonical contracts and
required predecessors. The LITE earnings route cannot supply those owners.
Do not invent upstream artifacts or weaken the extension's owner checks.

**Process.** Ordinary review closes each task. One confidence review, then one
separate adversarial code audit, close each whole phase with actual `xhigh`
reasoning. Neither runs per edit/task; rewrite tournaments are disabled.
Requested document audits do not certify those code gates. Opus planning-mode
preferences are recorded in the complementary plan's Reasoning Modes section:
`max` for an initial complex blueprint, `medium` for task/runbook drafting,
`low` for faithful formatting, and targeted `ultrathink` for plan stress tests.
Planning modes do not change code-review cadence.

**Coordinated implementation.** The coordinator may use at most three
concurrent implementers for disjoint concerns in isolated worktrees. Each has
an exact base, ownership boundary and isolated test resources; it cannot edit
the integration branch or invoke a provider. Task review follows each exact
concern range. The coordinator alone resolves findings, serially integrates,
runs cross-task/phase gates and records acceptance. Independent branch results
cannot satisfy an integrated task, PR or phase gate.

**Gate evidence.** Final size checks run after the candidate commit and review
remediation, over the actual proposed PR range, at the existing 800-line limit.
Pre-commit estimates cannot certify a committed-only size check. The documented
Claude hooks have an unresolved JSON-stdin input defect: repair and test them
in a dedicated Phase 2 prerequisite; do not treat prose as enforcement.

**Reason.** The audit found diverging plan copies, incompatible completion and
worker rules, restricted-output rejection, missing forecast predecessors,
untracked continuation records, and a size check run before its commit existed.
One maintained authority and explicit phase inputs/outputs prevent repeating
those mistakes without introducing a second build system.

## 2026-09-13 §40 — Reservations are priced at the configured model's worst case

**Decision.** A run executes with a dated `ModelPrice(model, input_per_token,
output_per_token, as_of)` instead of a caller estimate. Before any attempt,
`run_route` refuses `PROVIDER_NOT_CONFIGURED` unless the price names the
provider's configured model, and refuses invalid money as `validate_spend`
does. Every call reserves `worst_case(price) = MAX_REQUEST_BYTES × input +
MAX_COMPLETION_TOKENS × output`, computed exactly. This realises §16's price
clause for reservations and supersedes §38's "no pricing claim" for them.

**Why this bound.** Without a tokenizer, one token per request byte is the
conservative input bound the §38 request ceiling allows, and the output cap is
already sent with every request. The known charge is still reconciled after the
call; an overrun consumes the remaining capacity, so the next reservation is
refused (REPAIR_PLAN F06, Phase 2 budget exit). An application price cannot
guarantee a vendor bill.

**Not decided here.** The price's source. Phase 2 takes it from the caller, so a
real price for the live model is a user-supplied, dated fact; the byte bound is
large for a real model against the default ceiling, and pricing the encoded
request once it is built is the upgrade (CLAUDE.md known gaps).

## 2026-09-13 §41 — The canonical Markdown handoff's identity, storage and citations

(This repository's §41; the inherited table above maps CAOS-Final's own §41.)

**Decision.** For the Phase 3 adapter (`canonical-markdown-v1`, modules CP-0,
CP-L10 and CP-5 only):

1. **Host identity is pinned and reproduced.** A run's subject — issuer id and
   name, reporting period, analysis date — is immutable run input covered by
   the plan-gate fingerprint. The host derives the vendor run id
   (`COS-<UTC run creation>-<run id hex>`) and the attempt ordinal, builds the
   vendor invocation fields with the bundle's own envelope code, hands them to
   the module to copy, and checks them with the vendor's reproduce-and-match.
   Provider-claimed identity never survives (invariant 3).
2. **Storage.** The accepted artifact's `artifact_sha256` is the SHA-256 of the
   exact Markdown bytes, which are the only analytical authority and what
   downstream modules receive. A host record blob, referenced by
   `artifacts.record_sha256` and written in the same acceptance transaction,
   holds adapter/build/authority identity, the attempt ordinal, call-time
   upstream digests, typed projections and verified citations. Readers verify
   both blobs and their binding, re-parse projections from the Markdown and
   compare them; the record is never read back as fact.
3. **Citations.** The provider answers on a closed transport
   `{"canonical_markdown": ..., "citations": [{source_id, page, matched_text}]}`.
   Each quote must occur verbatim in the Markdown and anchor exactly once in
   the delivered evidence (invariant 11); any citation that fails refuses the
   whole handoff, since the Markdown cannot be edited, and a handoff with no
   citation is refused. The accepted identity is the pair of the Markdown hash
   and the host record hash; citations are a host-verified attachment bound by
   the record, not derived data. This refines §26 for Markdown. The transport is not JSON inside the
   Markdown, which the vendor forbids.

**Why.** §29 makes the exact Markdown the authority and names run, route,
bundle and upstream as host-owned; the vendor treats invocation reproduction as
a completion condition, so skipping the `credit_os_*` fields would be a quiet
non-conformance. Lineage requires the Markdown hash as the artifact identity.
Coordinates cannot be recovered from vendor register locators, and editing the
Markdown to add them is forbidden, so quotes travel beside it.

**Not decided here.** Vendor rules with no Python implementation are not
reimplemented by the host; they are recorded as known gaps when the adapter
lands.

## 2026-09-13 §42 — Migrating to the canonical adapter without a lasting bypass

**Decision.** Task 3.1 replaces the claims-JSON carrier in bounded, gate-green
slices (the binding re-slice in the Task 3.1 brief):

1. **Temporary dispatch from pinned facts.** Until slice f-1, the adapter
   version pinned in a run input is derived from the pinned route alone:
   `canonical-markdown-v1` when every node's module is a canonical adapter
   module, `claims-json-v1` otherwise. No flag, environment value or caller
   argument chooses it, and a canonical route cannot run as claims. Acceptance
   requires `artifacts.record_sha256` exactly when the pin is canonical. Slice
   f-1 makes the adapter a single constant and removes every claims branch;
   Task 3.1 is not accepted while `claims-json-v1` execution exists.
   *Retired 2026-09-13 (slice f-1c):* `adapter_for` is gone; every new pin is
   `canonical-markdown-v1` with a subject, a stored `claims-json-v1` pin
   refuses `RUN_INPUT_INVALID` at `execution_input`, runner and acceptance,
   acceptance always requires `record_sha256`, and the runtime, API, proof and
   matrix refuse a NULL record `ARTIFACT_RECORD_MISMATCH` rather than read a
   claims body. The unreachable claims executor and envelope parser remain for
   deletion in f-2a/f-2b.
2. **Other routes are disabled at execution, not at pinning.** After f-1,
   `execution_input` and acceptance refuse a route with a non-adapter module,
   before any attempt, reservation or call. Route resolution, pinning and gates
   stay general, because they are governance proven independently and Phase 5
   extends the adapter to further owners. *Implemented in f-1c:* both points
   call `gates.require_adapter_route` and refuse
   `HANDOFF_MODULE_UNSUPPORTED`; `run_route` reads `execution_input` before its
   first attempt.
3. **Blocked handoffs are diagnostics.** The canonical Markdown of every
   response is stored as a blob before validation and its hash recorded as the
   attempt's `diagnostic_sha256` with the call outcome; a response that
   validates with `qa_status: Blocked` ends the run `BLOCKED` and is never an
   accepted artifact. *Refined 2026-09-13 (c-5b remediation):* the diagnostic
   blob holds the exact response body (the whole closed transport), so the
   runtime re-derives a Blocked verdict -- identity, validation and anchoring --
   from committed facts before every attempt and before ending a run BLOCKED.
4. **Where citations are re-anchored.** Every reader verifies both blobs, their
   binding and the re-parsed projections. Citations are re-anchored against the
   token index by the proof, the qualification matrix and deliverable freezing,
   not on every frontier pass or API read, whose I/O budgets stay fixed.

**Why.** Moving tests first has nothing to run against, and one switch commit
would exceed 3,000 changed lines. Deriving the adapter from the pinned route
keeps each intermediate commit correct and replayable; the dated expiry and
acceptance blocker keep the dispatch from becoming a compatibility path.
`call_outcomes` is written before analysis and is immutable, so diagnostic bytes
must be addressed before validation.

**Rollback.** Before f-1 each slice reverts alone, and migration 0012 only adds
a nullable column. After f-1 rollback is a revert of commits, never a switch.

## 2026-09-14 §48 — CI build-speed pass: uv installs, one run per pull request, caches, and parallel tests

**Decision.** Eight changes, none touching a required check's name, a
threshold or a scanner rule:

1. **`push` runs on `main` only.** A branch with an open pull request is
   checked by its `pull_request` run; a push-triggered run of the same head
   sat in a different concurrency group and was never cancelled by it.
2. **The workflow token is `contents: read`** unless a job widens it; only
   `security` does, to read pull requests for gitleaks.
3. **One pin per action.** Every job uses `actions/checkout` v7.0.1 and
   `actions/setup-python` v7.0.0; `frontend`'s `actions/upload-artifact`
   matches `test`'s, v7.0.1. Each commit-pinned.
4. **`astral-sh/setup-uv` v10.1.0**, commit-pinned, installs uv 0.12.5 (the
   version `make venv` already installs with) with its download cache keyed
   on the job's lock. Every Python job runs `uv pip install --system
   --require-hashes --only-binary :all:` in place of `pip install`.
5. **`.mypy_cache`** is cached in the `types` job, keyed on the dev lock.
6. **Playwright's browsers** are cached in the `frontend` job, keyed on
   `frontend/package-lock.json`; `--with-deps` still installs the OS
   libraries the cache does not cover.
7. **`pytest-xdist==3.8.0`** (bringing `execnet==2.1.2`) joins the
   development lock, hashed and wheels-only. `make test` and the `test` CI
   job run `pytest -n auto`. Each worker builds its own migrated template
   database (below) and every test still mints a uniquely named database, so
   no worker shares state with another. `test-provider`, the `postgres` job
   and the live provider suite stay single-process.
8. **`tests/conftest.py`'s `case` fixture clones a session-scoped, already
   migrated template database** (`CREATE DATABASE ... TEMPLATE`) instead of
   applying every migration to a fresh database per test; `case` still calls
   `apply_schema`, which verifies the clone's recorded migration prefix.
   `empty_database` stays genuinely empty for every test that does not
   request `case`.
9. **`.dockerignore`** limits the `image` job's build context to what the
   Dockerfile copies (`requirements.txt`, `server/`, `vendor/`), and the
   `image` job builds with commit-pinned `docker/setup-buildx-action` v4.3.0
   and `docker/build-push-action` v7.3.0, with `cache-from/to: type=gha`.
   The image is loaded for Trivy and never pushed.

**Reason.** Measured locally against a real PostgreSQL: the offline suite ran
in a fraction of its serial time under `-n auto`, with the coverage floor
still holding, because most of its wall time is round trips to PostgreSQL
rather than CPU. A push to a branch with an open pull request started CI
twice for no reason `cancel-in-progress` could catch. The default workflow
token may carry write scopes no job needs. Mixed action versions are two
things to maintain per action, and `pip install` with no cache re-downloaded
every wheel on every run.

**Cost.** A test that depended on another test's side effects or on global
collection order could now fail intermittently under `-n auto`; every worker
must collect the identical test set, which `pytest-xdist` itself refuses if
they disagree. The GitHub Actions cache is a mutable input to the image
build, but every layer it restores is still keyed on the pinned base digest
and the hashed lock, and Trivy scans the loaded result either way.

**Rollback.** Each item reverts independently: drop `-n auto` from the two
call sites (the dependency can stay unused), restore `docker build -t
caos:ci .` in the `image` job, or drop any one cache block without touching
the others.

## 2026-09-14 §49 — `.sql` files are excluded from SonarCloud analysis, not run through a Data Dictionary

**Decision.** `sonar.exclusions` in `sonar-project.properties` adds `**/*.sql`
beside the existing `vendor/**`.

**Reason.** `sonar.sources` lists `scripts` and `server`, and both hold plain
PostgreSQL DDL: `server/store/schema.sql`, its thirteen numbered migrations,
and `scripts/dev-init.sql`. SonarCloud's PL/SQL sensor claims `.sql` files by
extension regardless of dialect, and the analysis logged: "The Data
Dictionary is not configured for the PLSQL analyzer, which prevents rule(s)
S3641, S3921, S3651, S3618 from raising issues." A Data Dictionary is an
imported catalog of Oracle schema metadata (SonarCloud's own PL/SQL docs);
this project has no Oracle database and nothing that would produce one. The
four rules cannot fire correctly against non-Oracle SQL even if one were
supplied, so excluding the files is the fix, not the dictionary the message
suggests.

**Cost.** Rule-based findings, if SonarCloud ever added a real PostgreSQL
sensor, would need this exclusion revisited. `test_dependency_pins.py`'s
class of gate does not cover `sonar-project.properties`, so nothing enforces
this file's shape in CI; the pre-existing `vendor/**` entry is the same kind
of unenforced exclusion.

**Rollback.** Drop `,**/*.sql` from the one line.

## 2026-09-14 §44 — Evidence admission limits, dispatch and PDF geometry

**Decision.** For Phase 3 Task 3.2:

1. **Limits (host policy).** Per pack at most 50 documents and 100 MiB; per
   document at most 20 MiB, 500 pages, 500,000 tokens and 60 s of extraction.
   Checked before the expensive step each bounds; refusals are typed
   (`SOURCE_TOO_LARGE`, `SOURCE_EXTRACTION_TIMEOUT`).
2. **Time.** The deadline is cooperative (checked per page and per line). A
   single pathological page can overrun it; that residual is recorded in the
   `CLAUDE.md` ledger. No process isolation or new dependency.
3. **Geometry.** PDF tokens are normalised to the CropBox origin, top-left,
   y down, in rotated displayed space; tokens not wholly inside the crop are
   dropped. The convention and the effective layout parameters are declared in
   extractor identity version 2. Output format v1 and its verifiers are
   unchanged; no migration.
4. **Existing v1 PDF extractions** still verify and re-anchor as recorded;
   readmission is how a source gains v2 geometry.
5. **Ambiguity** is counted over the whole page, delivered or not; glyph merging
   follows pdfminer's `word_margin` with no custom heuristic.
6. **Dispatch.** `admit_pack` chooses the extractor per document from its bytes;
   the single-extractor parameter is removed, not kept as a bypass.

**Why.** The repair plan requires limits before expensive work and specific safe
outcomes, without new dependencies or speculative infrastructure; option 3
keeps every v1 pin byte-identical while fixing the geometry new admissions carry.

## 2026-09-14 §45 — Delivered authority, lineage and context ceilings

**Decision.** For Phase 3 Task 3.3:

1. **Delivered authority** is every non-script file of the module's manifest
   entry plus every root file its verified `SKILL.md` names, each verified and
   delivered whole; the record binds exactly that set.
2. **No calculator is exposed.** No required computation on the LITE route has
   host-owned inputs; the vendor validators run host-side after the answer.
3. **Over-ceiling context refuses** `CONTEXT_OVER_CEILING` before any reservation
   or call; nothing is truncated or summarised. Retrieval arrives with Phase 5
   evidence selection.
4. **Record format v2** adds the delivered-authority digest and upstream lineage;
   pre-release v1 records refuse `ARTIFACT_RECORD_MISMATCH`, no backfill.
5. **CP-0 anchor.** A node whose route gives it no direct CP-0 ref refuses
   (fail-closed; LITE unaffected); a stored anchor field arrives with Phase 5.
6. **Read model.** Task 3.4 labels verified citations as source fact, model
   Markdown as analysis, host calculations as none; the host does not parse
   vendor lineage columns.

**Why.** Item 3 requires complete verified instructions and lineage without
summarising; the measured references fit the request bound; no speculative tool
loop or retrieval layer is added.

## 2026-09-14 §46 — The LITE route's named object, completion cap and read model

**Decision.** For Phase 3 Task 3.4:

1. **CP-5 over the named LITE object.** The host reads CP-5's verified LITE
   compatibility block (`NAMED_LITE_OBJECT_ACCEPTED`, `accepted_lite_object_ids`)
   and holds CP-5 BLOCKED, with no call, until an accepted upstream owns one of
   those objects. Driven by vendor fields, not a hardcoded graph.
2. **Completion cap.** `MAX_COMPLETION_TOKENS` stays 32,768; a length-truncated
   answer refuses `PROVIDER_OUTPUT_TRUNCATED`, keeps its bill and accepts
   nothing. Any raise needs authorized live evidence (Phase 6).
3. **Read model** labels land in the deliverable render only (source fact =
   host-verified citations; analysis = model Markdown; host calculation = none);
   API models arrive in Phase 4.
4. **No CP-5 content checks by the host** (e.g. T5.1 naming CP-L10); the vendor
   remains the conformance authority (invariant 4).
5. **LITE `required_payload_fields`** are not validated by the host; recorded in
   the ledger beside `semantic_rules`.

*Refined 2026-09-14 (3.4b review, Phase 3 confidence review):* an input meets
item 1's boundary when its catalog `owned_object` or the catalog edge's
`accepted_object_id` is an accepted id; a boundary no input on the pinned route
offers is not enforced (holding it forever would be a host-invented graph), and
is only reachable on routes the adapter refuses. Execution is also limited to
the pathways a contract test proves (`ADAPTER_ROUTES`, LITE earnings only), so
LITE portfolio decision (CP-0 -> CP-L10) stays disabled (REPAIR_PLAN work
item 6).

## 2026-09-14 §47 — PDF extraction runs in a killed, budgeted child

**Decision.** Supersedes §44.2 (Phase 3 adversarial audit):

1. **Isolation.** `PdfExtractor.extract` runs the page walk in a child
   interpreter (`python -I -c`, empty environment, stderr discarded); the
   parent kills it at the admission deadline and refuses
   `SOURCE_EXTRACTION_TIMEOUT`. Only a JSON token list or an allowlisted code
   crosses back. Not `multiprocessing`: `spawn` re-runs the caller's
   `__main__`, and a fork copies credentials and connections.
2. **Decoded bytes.** `AdmissionLimits.max_decoded_bytes` (256 MiB) bounds what
   one PDF's Flate streams inflate to, enforced in the child by replacing
   pdfminer's `zlib` with a budgeted inflater; over budget refuses
   `SOURCE_TOO_LARGE`.
3. **Plain text** stays in-process; a line stops building tokens one past
   `max_tokens`.

**Why.** A 16,926-byte PDF page overran a 2 s deadline to 23.2 s and a
261,529-byte page held 806 MiB, so a document inside every §44.1 ceiling could
exhaust the extracting process: REPAIR_PLAN Phase 3 exit check 1's "specific
safe outcomes" did not hold. A child uses only the standard library and touches
no transaction, so the failure mode §44.2 feared (a killed worker
mid-transaction) does not arise; the probes after the change refused at 2.0 s
and in 0.2 s.

## 2026-09-14 §48 — CI installs with uv, runs once per pull request update and holds a read-only token

**Decision.** Four changes to `.github/workflows/ci.yml`; no required check,
threshold, scanner rule or job name changes.

1. **`push` runs on `main` only.** A pull request's commits are checked by its
   `pull_request` run. A branch pushed with no pull request open gets no CI
   until one is opened.
2. **The workflow token is `contents: read`** unless a job widens it; only
   `security` does, to read pull requests for gitleaks.
3. **One pin per action.** Every job uses `actions/checkout` v7.0.1,
   `actions/setup-python` v7.0.0 and `actions/upload-artifact` v7.0.1, each
   commit-pinned.
4. **`astral-sh/setup-uv` v10.1.0**, commit-pinned, installs uv 0.12.5 (the
   version `make venv` uses locally) with its download cache keyed on the
   job's lock. Every Python job runs `uv pip install --system --require-hashes
   --only-binary :all:` into the interpreter `setup-python` provides, in place
   of `pip install` and its cache.

**Reason.** A push to a branch with an open pull request started two full
runs whose refs differ, so `cancel-in-progress` cancelled neither. The
default token may carry write scopes no job uses. Mixed action versions are
two things to maintain per action. uv is what the Makefile already installs
with, and it resolves and installs the same hashed, wheels-only locks faster.

**Rollback.** Revert the workflow commit; nothing outside the workflow
depends on these changes.

## 2026-09-14 §49 — One PostgreSQL worker: a claim per run fenced by a token

**Decision.** Phase 4 Task 4.3 (brief `docs/superpowers/plans/2026-09-14-phase-4-task-4.3-brief.md`):

1. **Claim per run.** Migration 0013's `run_work` row gives one lease holder
   the run's frontier, fenced by a token that every claim advances;
   `start_attempt`, `reserve`, acceptance and every terminal transition check it
   under `lock_run`. The bill (`record_outcome`) is never fenced.
2. **Lease.** 300 s, renewed by every fenced write; a test pins it above twice
   the provider's socket timeout. A trickling response can outlive a lease: at
   most one extra paid call, never a second acceptance.
3. **Cancellation is a request.** It never interrupts a call in flight; that
   call's bill commits and a valid answer is accepted; the next start or
   reservation refuses and the holder ends the run `CANCELLED` (`cancel_run`).
4. **Terminal decision under the lock.** COMPLETE requires every pinned node
   accepted (`RUN_NODES_UNACCEPTED`); a terminal snapshot that moved refuses
   `RUN_TERMINAL_STALE` and the runtime runs one more pass.
5. **Crash recovery replays the stored body.** `replay_billed` re-runs the live
   post-call checks over a billed, unaccepted attempt: answered is accepted with
   its original bill, Blocked ends the run, refused is written once to
   `attempt_refusals` and stops the run. No billed answer is paid for twice
   after a crash.
6. **Worker.** `server/engine/worker.py` polls (no LISTEN/NOTIFY, no broker),
   backs off on store faults, stops between passes on SIGTERM, and refuses to
   start without a configured provider and a dated `CAOS_MODEL_PRICE`
   (`model,input,output,YYYY-MM-DD`), the worker's price source under §40.

**Why.** One holder makes Phase 2's single-loop assumptions exact under
concurrency without predecessor fencing; the token, not the clock, decides
every stale write, and no lock is held across transport.

## 2026-09-14 §50 — One versioned section wire and refusal body

**Decision.** Phase 4 Task 4.1 (brief `docs/superpowers/plans/2026-09-14-phase-4-task-4.1-brief.md`):

1. **Paths.** `GET /api/v1/directory` and `/api/v1/cases/{case_id}/{upload,run,analysis}`
   (`?run=` for run and analysis); the case is the authorization resource and
   unknown, unauthorized, revoked and malformed cases are one private 404. The
   version lives in the path only. `GET /api/runs/{run_id}` is retired.
2. **One refusal body** `{code, clears}` for every non-success under `/api/`,
   with `clears` a host constant per code (`server/api/wire.py` `CLEARS`); an
   undeclared path or method answers `ENDPOINT_NOT_FOUND`.
3. **Documents** carry only facts the host holds after Phase 3; fixture-era
   fields with no host source are removed, not faked. The server computes only
   authority facts in `chrome` (subject, served role); persona grants nothing.
   Analysis carries each verified handoff with the §46.3 labels.
4. **Cross-language contract.** `python -m server.api.wire` prints the models'
   JSON Schema (committed, one definition per line); the browser's closed-shape
   DSL (`frontend/src/wire/v1/shape.ts`) is proven equal to it and validates
   every document whole and bound to its case and run. No cast, no dependency.
5. **Disabled sections.** Book, Model, Report, Committee and Admin render
   unavailable with no request in every mode; fixtures are served only in demo
   mode and the production export carries none.
6. **Shared dependencies.** Every section read depends on
   `server/api/deps.py`, so an override of the app's store reaches every route.

**Why.** The repair plan requires versioned models, settled identity and refusal
semantics, whole-document validation and no pretence that `/api/runs` was a
section document.

## 2026-09-14 §51 — Governed commands: one audited unit and one receipt per intent

**Decision.** Phase 4 Task 4.2 (brief `docs/superpowers/plans/2026-09-14-phase-4-task-4.2-brief.md`):

1. **Nine endpoints under `/api/v1/cases`.** Create case (`POST`), admit
   sources (`/{case}/sources`), create run (`/{case}/runs`, the route resolved
   and pinned in the same unit), pin input (`/runs/{run}/input`, snapshotting
   the case's live sources in the same unit), a gate preview (`GET
   /runs/{run}/gates/{gate}/preview`) and approval (`POST …/approval`) for
   `source-set` and `research-plan`, and start, retry and cancel. Start, retry
   and cancel are the only writers of `run_work`; none calls a provider, and
   `test_command_modules_import_no_runtime_provider_or_transport` holds that.
2. **Authority is derived, in order.** Identity (401), path ids, the
   `Idempotency-Key` header (400 `IDEMPOTENCY_KEY_REQUIRED`, before a body is
   read), visibility (no live standing is the private 404), the global role (a
   write needs ANALYST or ADMIN), the command's case floor (403
   `NOT_AUTHORISED`), the bounded body, then the governed write, which
   rechecks standing under the case lock; a `NOT_AUTHORISED` there answers
   `CASE_NOT_FOUND`. No request carries an actor, case, run or approver. Create
   case inserts the case, grants its creator ADMIN and writes `CASE_CREATED` in
   one transaction.
3. **Idempotency (migration 0014).** `command_requests` holds one immutable
   receipt per `(actor_id, scope, idempotency_key)`, scope the case or the nil
   UUID for create case, beside `request_sha256` -- canonical JSON of
   `{command, case_id, run_id, gate, body}`, an admission's body being
   `[{filename, sha256}]` in part order. Only committed successes are recorded,
   as the governed unit's last domain statement, so state, run events, the
   work row, the audit event and the receipt commit together or not at all. A
   key already committed replays its status and receipt with
   `Idempotency-Replayed: true` and writes nothing; under another digest it is
   409 `IDEMPOTENCY_KEY_REUSED`. A concurrent twin finds the first receipt
   under the case lock, or waits on the primary key's `ON CONFLICT DO NOTHING`
   under the nil scope, rolls back its whole unit and replays. A refusal burns
   no key.
4. **In-transaction store entry points.** `pin_route_in`, `pin_run_input_in`,
   `snapshot_in` and `release_gate_in` write in the caller's transaction (the
   committing wrappers call them); `release_gate_in` takes the run lock and
   refuses `RUN_NOT_RUNNING`. Lock order stays case, run, `run_work`.
5. **Conflicts, not faults.** Approval re-derives the preview under the case
   and run locks (`GATE_APPROVAL_MISMATCH`, `EVIDENCE_NOT_AVAILABLE`,
   `RUN_NOT_RUNNING`). Start and retry classify inside the unit: no pin
   `RUN_INPUT_NOT_PINNED`; another build, manifest or adapter
   `ORCHESTRATION_BUILD_MOVED`; then `execution_input`; a fingerprint other
   than the body's `COMMAND_EXPECTATION_STALE`; then `RUN_ALREADY_STARTED` or
   `RUN_NOT_STOPPED`. Cancel of an unqueued run enqueues and requests cancel in
   one unit. A route pair outside `ADAPTER_ROUTES` is `ROUTE_NOT_ENABLED`
   before resolution. Each is 409; oversize is 413 `SOURCE_TOO_LARGE`.
6. **Bodies.** JSON commands need `application/json` of at most 16 KiB; any
   failure is 400 `REQUEST_INVALID`, never FastAPI's 422 quoting the input.
   Admission needs `multipart/form-data` with a declared `Content-Length` no
   larger than `max_pack_bytes` plus 1 MiB and no `Transfer-Encoding`, checked
   from headers; after the floor the standing read's transaction is closed, the
   form is parsed (`max_files=50`, `max_fields=0`, the stream held to its
   declared length), only file parts named `document` are taken, each filename
   `BoundaryText` of at most 255 characters and not blank. The receipt is
   looked up before extraction; `prepare_pack` then extracts (the §47 child for
   a PDF) with no transaction open and no case lock held, and one unit runs
   `admit_prepared`, `SOURCES_ADMITTED` and the receipt. The pack is admitted
   whole or not at all.
7. **Dependency.** `python-multipart==0.0.32`, pinned and hashed in
   `requirements.txt` and `requirements-dev.txt`, authorized by the user on
   2026-09-14. Starlette's `Request.form` requires it; nothing else imports it.
8. **Availability is advisory.** `Chrome.actions` is computed by the pure
   functions of `server/api/commands/availability.py` from facts each read
   already holds, in the order the command checks them, so a refused action
   names the code its command would answer now. It grants nothing; the command
   rechecks at commit. The Run document adds `RunView.work` and
   `RunBody.route_choices` (at most 16, from `ADAPTER_ROUTES`).
9. **The browser.** `frontend/src/app/commands.ts` validates every receipt and
   preview whole. A control holds one `crypto.randomUUID()` key per intent,
   reused only when the previous call carried the identical body and never
   reached the server, and replaced after any answer. Controls render from
   `chrome.actions`, present and refused rather than hidden (an absent entry is
   `ACTION_UNPLACED`); a success refetches its section once.
10. **CSRF, first half.** No CORS middleware, exact content types and a
    mandatory custom header, so a cross-site simple form POST is refused before
    any effect. Origin and `Sec-Fetch-Site` are §53's.

**Why.** REPAIR_PLAN Phase 4 work item 3 asks for idempotent, server-authorized
commands with stale-preview and changed-authority conflicts. The committing
store pins could not share a transaction with an audit event or a receipt, and
`admit_pack` extracted before it locked, so neither could be governed as it
stood. A key per intent is what makes a retried request after a lost
acknowledgement safe to send, and recording only committed successes means a
refusal never has to be un-remembered.

## 2026-09-14 §52 — One name-only case stream, and evidence pages from the token index

**Decision.** Phase 4 Task 4.4 (brief `docs/superpowers/plans/2026-09-14-phase-4-task-4.4-brief.md`):

1. **One stream per case.** `GET /api/v1/cases/{case_id}/events?run=` needs
   READER standing (else the private 404; a run of another case is
   `RUN_NOT_FOUND`) and carries the case's audit actions plus the named run's
   `run_events`. `/api/runs/{run_id}/events` is retired. Directory opens no
   stream.
2. **Closed names, no payloads.** `EventName` is `run_progress`,
   `handoff_accepted`, `run_terminal`, `sources_changed` and `runs_changed`
   (`server/api/events.py` `STREAM_NAMES`). Admission and withdrawal are
   `sources_changed`; create run, pin input, both gate releases, start, retry
   and cancel are `runs_changed`; `CASE_CREATED`, `OPINION_SIGNED`,
   `DELIVERABLE_FROZEN` and `DELIVERABLE_FILED` are silent. A test fails a
   `RunEvent` or audit action that is neither named nor declared silent. The
   browser's `REFETCHES` table says which sections each name refetches;
   revocation has no name.
3. **Composite cursor.** Each frame is `id: {audit_seq}.{run_seq}`, `event:
   {name}`, `data: {}`; the first frame is the cursor alone, at the heads. A
   `Last-Event-ID` that is missing, not ASCII digits in that shape, longer than
   sixteen digits a half, or ahead of the heads resumes from the heads, and
   delivery is strictly after the marker. Silent rows advance the cursor.
4. **Lifetime.** Standing is rechecked before each named frame and on each
   poll; losing it closes the stream, and the reconnect's 404 closes the
   browser's `EventSource`. Once the run's terminal event is delivered, or the
   marker is past it, `run_events` is not read again (F16). The stream closes
   at `TAIL_DEADLINE` (300 s) and the browser reconnects with its marker.
5. **Refetch.** One fetch per section in flight; a name arriving mid-flight
   causes exactly one more. A case or run change closes the tail, aborts the
   fetch and discards any late answer. A refetch under the same analytical
   identity (Run: the shown run; Analysis: the displayed run and its sorted
   `record_sha256`s) replaces the view; another identity is held as pending
   until Reload, while withdrawals from the latest document still mark the
   shown one. The view mounts under `case|displayedRun`, so a refresh keeps
   selection, and a section that throws renders `RENDER_FAILED`.
6. **A closed stream refetches.** `EventSource` cannot tell a refusal from a
   connection that never opened (Firefox closes both), so a closed tail
   triggers a document read, and that answer decides: 404 is unavailable, no
   connection is offline. Every reopen refetches the visible documents.
7. **Evidence pages.**
   `GET /api/v1/cases/{case}/runs/{run}/sources/{source}/pages/{page}` checks
   identity, READER standing, then the run's case, and serves a source only
   while it is live and a member of the run's pinned source-set version with
   matching document, extractor identity and output digests. Anything else --
   a page outside 1..500, a malformed source id, a withdrawn or re-extracted
   source, bytes that no longer hash to the pin, a child that refuses -- is one
   404 `PAGE_NOT_AVAILABLE` with no text. It is a new code because
   `EVIDENCE_NOT_AVAILABLE` is a command's 409 (§51.5). Responses are
   `no-store`.
8. **A text layer, not a rendering.** The page is its `source_tokens` grouped
   by `(region_id, line_id)` into joined text and union rectangles in stored
   coordinates, at most 2,000 lines (else `partial`, `LIST_TRUNCATED`). The
   frame follows the stored identity: `caos.pdfminer` v2 is the crop with y
   down, v1 the layout crop with y up (§44.4), `caos.plain-text` its recorded
   cells; PDF frames come from the §47 child under the admission deadline and
   decoded-byte budget. The browser places lines and citation rectangles with
   one `toFraction`, draws no rectangle outside the frame and says how many it
   did not draw. The drawer is labelled "Text layer from the token index".
9. **The drawer is bound to the visible snapshot.** It holds a citation's
   identity `(record_sha256, source_id, page, index)` and the snapshot key it
   was opened on, and re-resolves both each render: another key or a citation
   no longer present closes it; a withdrawal shows in it; a pending document
   the user has not reloaded never reaches it.

**Why.** REPAIR_PLAN Phase 4 work items 1, 5 and 6. Withdrawal is an audit
action, which a run tail never read, so a stream per case is the one that can
say it. A payload would be a second copy of state the client is about to fetch
under its own authority check. A page renderer would put an untrusted-PDF
parser with its own CVE stream on a request path; the token index is the
coordinate space citations were anchored in (invariant 11).

## 2026-09-14 §53 — The edge guard, one site application, readiness and the smoke stack

**Decision.** Phase 4 Task 4.5 (brief `docs/superpowers/plans/2026-09-14-phase-4-task-4.5-brief.md`):

1. **The edge contract** (`server/api/edge.py`'s docstring). The operator's
   edge authenticates with OIDC and forwards only to a private listener. It
   strips inbound `x-caos-user`, `x-forwarded-groups`, `x-caos-role`,
   `x-caos-edge-token`, every header whose name contains `_`, and its own
   session cookie; it sets exactly one `x-caos-user`, `x-forwarded-groups` and
   `x-caos-edge-token`; it passes `origin`, `sec-fetch-*`, `idempotency-key`,
   `last-event-id`, `content-type` and `content-length`. Its cookie is
   `__Host-`, `Secure; HttpOnly; SameSite=Lax` (Strict breaks the OIDC
   return); SSE is unbuffered with an idle timeout above 300 s.
2. **Two modes, from the environment on every use.** *Edge mode*
   (`CAOS_EDGE_TOKEN` set): the token is at least 32 bytes,
   `CAOS_PUBLIC_ORIGIN` a bare `scheme://host[:port]`, and
   `CAOS_TRUST_ROLE_HEADER` absent, or the lifespan fails
   `EDGE_CONFIG_INVALID`; every request but `GET|HEAD /api/health` carries
   exactly one token equal under `hmac.compare_digest`, or is 403
   `EDGE_NOT_TRUSTED` before routing, identity or body. *Dev mode* (no token):
   both socket ends are loopback and `Host` is `localhost`, `127.0.0.1` or
   `[::1]`, or 403. A tokenless image on a published port answers health and
   nothing else. The token header is removed from the scope before anything
   downstream runs.
3. **Identity switch rule.** `actor_from_headers` believes `x-caos-role` only
   when the switch is `1` and no edge token is set; otherwise the role comes
   from groups.
4. **Header hygiene, both modes.** A repeated identity header, or a name that
   differs from one only by case or `_` for `-`, is 401 `NOT_AUTHENTICATED`.
5. **Origin, the second half of §51.10.** Under `/api`: an `Origin` outside
   the allowed set (`CAOS_PUBLIC_ORIGIN`, or `http://{localhost,127.0.0.1,[::1]}:{5173,8000}`
   in dev mode) is refused; a safe method needs `Sec-Fetch-Site` absent,
   `none` or `same-origin`; an unsafe one `same-origin`, or no
   `Sec-Fetch-Site` with an allowed `Origin`. Otherwise 403 `ORIGIN_REFUSED`.
   No CORS middleware.
6. **Every response** carries the CSP `default-src 'none'; script-src 'self';
   style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self';
   base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src
   'none'; require-trusted-types-for 'script'; trusted-types 'none'`,
   `nosniff`, `no-referrer`, COOP and CORP `same-origin`, and a cache policy
   (`/api` `no-store`, `/assets/` immutable for a year, else `no-cache`); any
   `set-cookie` or `access-control-*` header is dropped. FastAPI's docs,
   ReDoc and OpenAPI routes are not served. A directive is widened only for a
   named violation recorded here; none has been.
7. **One site application.** `server.api.site:application` is `EdgeGuard`
   over a dispatcher: `/api` and `/api/*` (and the lifespan) go to
   `server.api.app:app`, so routing's 404 and 405 there stay
   `ENDPOINT_NOT_FOUND`; everything else is a GET/HEAD read of
   `CAOS_SITE_ROOT` without symlinks, where `/` and each section path serve
   `index.html` and any other method is a bodiless 405. With the root unset
   non-API paths are 404; set without `index.html`, the lifespan fails.
8. **`GET /api/health`.** A closed `HealthDocument{status, store, bundle,
   blobs, checked_at}`, 200 only when all three probes are `OK` and the round
   is under 30 s old (`PROBE_STALE` after, `PROBE_NOT_RUN` before the first).
   One lifespan task probes every 10 s, each probe in a thread under 2 s
   (`PROBE_TIMEOUT`), never two rounds at once: store connects with a 2 s
   timeout and runs a read-only `verify_schema`; bundle compares a fresh
   manifest with the process's; blobs checks the root is a usable directory,
   writing nothing. The route needs no token or identity and does no I/O.
9. **One image, two commands, no proxy inside.** A digest-pinned
   `node:24-slim` build stage runs `npm ci --ignore-scripts && npm run build`
   and only `dist` reaches the runtime (`/app/site`, `CAOS_SITE_ROOT`). The
   API runs `uvicorn server.api.site:application --workers 1
   --no-proxy-headers --no-server-header --limit-concurrency 32`; the worker
   is `python -m server.engine.worker`. `make dev-api` serves the same
   application on 127.0.0.1 with `--no-proxy-headers`.
10. **Dev identity lives in the Vite proxy.** It removes every client
    `x-caos-*`, `x-forwarded-*`, `forwarded` and `_` header, then sets
    `x-caos-user` from `CAOS_DEV_USER` and `x-caos-role` from `CAOS_DEV_ROLE`
    (default ANALYST); without `CAOS_DEV_USER` it sets nothing and the API
    answers 401.
11. **Smoke stack.** `compose.smoke.yaml`, project `caos-workbench-smoke`: a
    digest-pinned PostgreSQL on tmpfs with no host port, the API on
    `127.0.0.1:18000` in edge mode with its own blob volume, a credential-less
    `worker` (profile `smoke`) and the deterministic `journey-worker` (profile
    `journey`, `./tests` mounted read-only at `/app/tests` -- not
    `/opt/caos-tests` as the brief wrote, because `tests/canonical_fixtures.py`
    finds `vendor/deploy-v` as its parent's sibling -- with its exit-once marker
    in the blob volume the image's uid owns; `tests/` is never in the image).
    The test edge retries a refused upstream connect for a GET for up to 30 s
    and answers 502 after, so a browser's stream reconnect meets a restarted
    API rather than an error Firefox and WebKit treat as final; an unsafe
    method is never retried.
    `make smoke-production` builds the image, runs `pytest -m production_image`
    with `CAOS_REQUIRE_IMAGE=1`, then `tests/journey/run.py`, which starts the
    stack, the host test edge on 127.0.0.1:18080 and Playwright, and always
    takes the stack down with its volumes. It is the last step of `make
    check`; `make test` deselects `production_image`.

**Why.** REPAIR_PLAN Phase 4 work item 7. The image listened on `0.0.0.0` and
believed any well-formed identity header, and nothing proved a request had
passed the edge; a shared token is the proof available with the standard
library alone (JWT verification needs a dependency, mTLS certificates).
Mounting static files inside FastAPI shadowed API refusals and served a CDN
script the policy refuses; a dispatcher keeps the two surfaces apart. A
proxy inside the image would be packages to scan and a supervisor to run for
what is operator infrastructure anyway.

## 2026-09-14 §51 refinement — one extraction deadline for the whole pack

**Decision.** `AdmissionLimits.max_pack_seconds` (300 s) bounds a pack's
extraction as a whole: each document's deadline is the earlier of its own
`max_seconds` (60 s, §44.1) and the pack's, and a pack past it refuses
`SOURCE_EXTRACTION_TIMEOUT` with nothing written.

**Why.** The Phase 4 adversarial audit found that only the per-document
deadline existed, so one authenticated writer's fifty-document pack could hold
an admission request, its thread and one of the image's 32 concurrency slots
for fifty minutes. 300 s matches the edge's idle timeout (§53.1), past which
the request would be cut anyway.

## 2026-09-14 §54 — The closed forecast contract and independent reconciliation

Task 5.1 repairs the dormant calculator's numerical contract; it does not
enable CP-CF, a route, or the Model section. The host extension and verified
execution binding remain Task 5.2. No upstream file changes.

**Inputs.** The top-level keys are exactly `opening`, `periods`, `drivers`,
`contractual`, `units`, `perimeter`, and optional `tolerance`. Every nested
object is closed. Opening requires `cash`, `as_of_period_id` and
`debt_by_facility[]` of `{facility_id, amount}`, with unique facilities.
Periods require `{case, period_id, fiscal_year, days}`; `(case, period_id)` is
unique, `days` is an integer string 1..366, and caller order is chain order
within each case. Text labels pass BoundaryText/NFC with a 64-character bound
and cannot be blank. Units require a three-uppercase-letter currency and scale
`units`, `thousands`, `millions` or `billions`; units and perimeter carry to output.

Drivers have unique requested `(case, period_id)`, required `status`,
`stated_closing_debt`, `stated_closing_cash`, and the movement fields:
`revenue`, `ebitda`, `cfo`, `capex`, `acquisitions_disposals`, `cash_interest`,
`cash_taxes`, `distributions`, `issuance`, `optional_repayment`, `pik`,
`capitalised_interest`, `fx_perimeter`. Every movement is required for READY.
An explicit zero is zero; a missing movement makes the row unavailable with
`DRIVER_FIELD_MISSING`. A missing driver is `DRIVER_MISSING`; an unready one is
`DRIVER_NOT_READY`. Later rows of that case are `PRIOR_PERIOD_UNAVAILABLE`.
Present invalid numerics refuse even in an unready or subsequently unavailable
row. Missing stated balances refuse: reconciliation needs independent claims.

Contractual input is exactly `amortisation[]` of
`{case, period_id, facility_id, amount}`; every pair is requested and facility
opened. Duplicate four-field entries (numeric amounts compared as Decimal)
refuse. Different payments for one facility-period sum. No payment rows means
zero repayment. `policy`, `maturities`, `coupons` and the old driver field
`financing_investing` refuse `METHODOLOGY_INPUT_INVALID` until implemented.

**Arithmetic.** Every numeric input must be a JSON string matching
`^-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?$`, matched over the entire string.
No exponent, whitespace, plus, bool, JSON number, null or Decimal object is
accepted. Amortisation, tolerance and movements are nonnegative, except signed
acquisitions/disposals and FX/perimeter movements. Opening and stated closing
balances may be negative: the movement sign rule does not constrain balances.
Every sum, subtraction, division,
comparison and quantization runs inside one fresh local
`Context(prec=38, rounding=ROUND_HALF_EVEN,
traps=[InvalidOperation, DivisionByZero, Overflow])`. Amounts emit six decimal
places, ratios four. The ambient context supplies no arithmetic settings.

```
closing_debt = opening_debt + issuance + pik + capitalised_interest
               - contractual_repayment - optional_repayment + fx_perimeter
financing_investing = issuance - contractual_repayment - optional_repayment
                      - acquisitions_disposals
fcf = cfo - capex - cash_interest - cash_taxes
closing_cash = opening_cash + fcf - distributions + financing_investing
residual_debt = stated_closing_debt - closing_debt
residual_cash = stated_closing_cash - closing_cash
```

Each case starts with the supplied opening debt sum and cash; subsequent
openings equal the previous computed closes, checked with
`FORECAST_CHAIN_BROKEN`. Either absolute residual above tolerance (default
`0.001`, explicitly in the supplied units) gives `RESIDUAL_UNRECONCILED` and
propagates unavailability. The failed row retains computed values/residuals as
diagnostics, never as an available forecast. Tolerance equality passes.

Gross leverage is closing debt/EBITDA, net leverage is (closing debt-closing
cash)/EBITDA, interest coverage is EBITDA/cash interest, FCF/debt is FCF/closing
debt; operating margin is EBITDA/revenue. Each ratio with a nonpositive
denominator is `{value: null, reason: "ZERO_OR_NEGATIVE_DENOMINATOR"}`;
otherwise it is `{value: "<four-place string>", reason: null}`. Accessible
cash equals closing cash: restricted cash is unsupported. Liquidity runway is
omitted because cash-sweep/minimum-cash/revolver/FX policy is unsupported.

**Output and ceilings.** `cash_flow_forecast` returns exactly
`{status, units, perimeter, rows, checks}`. Rows appear once per requested pair
in request order, with computed fields or an unavailable reason; status is
complete only when all rows are available. `forecast_bytes` serializes this
object as UTF-8 JSON with sorted keys, compact separators, no NaN and no ASCII
escaping. It is byte-identical under changed ambient Decimal contexts.
One residual check per requested row records PASS/FAIL and its unavailable
reason. Before any numeric parse, requests are bounded to 40 periods per case,
6 cases, 40 opening facilities, 2,000 amortisation entries, at most one driver
per requested pair, and `max_periods_per_case × cases × (1+facilities) <= 100000`.

**Evidence and limits.** `tests/forecast_fixtures.py` supplies the inputs;
the annual base/downside and quarterly base tests carry independent hand
tables, including financing, FCF, debt/cash, ratios and chain openings.
This proves arithmetic over supplied movements, not the economic validity of
chosen drivers or a provider's credit conclusions. A negative computed balance
is preserved; no unimplemented policy silently funds a cash deficit or floors
debt. A relative tolerance or restricted-cash model needs a later decision.

## 2026-09-14 §55 — A bounded audit package with its own portable verifier

**Decision.** Phase 5 Task 5.4a completes the package half of F15 without
changing §14's scope: internal consistency, not externally authenticated
signatures or proof that an entire receipt/audit chain was never replaced.

1. **Exactly five members:** `payload.json`, `receipt.json`,
   `deliverable.html`, `render.py`, `verify_package.py`. The two Python members
   are exact build-time source bytes. Names are unique and exact; extras,
   directory entries, traversal, absolute names, backslashes and embedded NULs
   refuse. Building uses sorted names, fixed ZIP timestamps/permissions/system,
   and DEFLATED level 9. Identical inputs and renderer/verifier bytes under the
   same Python/zlib build produce identical archive bytes.
2. **Portable render.** `render.py` imports only standard-library modules and
   raises local `RenderRefused(ValueError)` with its existing code as a string.
   `host.render_payload` maps this to the existing host `RefusalCode`/`Refusal`,
   with no exception chain. Its HTML output is unchanged.
3. **Portable verifier version 1.** `verify(archive: bytes)` returns
   `(bool, str | None)`; malformed input is a fixed failure reason, never an
   exception's text. The host `package.verify_package` wraps that result in the
   existing `Verification`. A reader may run
   `python -I -S verify_package.py <package.zip>` from any directory. The CLI
   prints `{"verified": true, "reason": null}` on success and exits 0, or a
   failed verdict and exits 1. It installs nothing, extracts nothing, and
   loads its renderer from the bounded archive bytes.
4. **Bounds before member reads.** Archive ≤64 MiB; payload ≤32 MiB; export ≤64
   MiB; receipt ≤64 KiB; each Python member ≤1 MiB. Exactly five central
   headers are checked before `ZipFile` can allocate member objects. The format
   is single-disk ZIP32 with no appended bytes; ZIP64/multi-disk containers are
   unnecessary at these ceilings and refuse. Only STORED and DEFLATED are
   accepted, with no encryption and a declared ratio ≤100:1. Every deflate
   output is capped at its limit plus one byte and must reach the end of its
   stream with no tail; actual size and CRC must match the directory.
5. **Safe renderer loading.** The verifier embeds `RENDERER_SHA256` for its
   trusted build and refuses different renderer bytes before executing them.
   If the receipt carries `renderer_sha256` (Task 5.3), it must also match.
   Update the pin with every renderer edit. This protects a trusted verifier
   from arbitrary archived code; no external trust anchor is introduced.
6. **Existing consistency checks remain:** receipt is a JSON object, payload
   hashes to `payload_sha256`, three named roles contain three distinct people,
   canonical Markdown/record digest pairs bind, and the archived renderer
   reproduces the export byte for byte. Store verification owns live chain
   proof.
7. **Exclusive creation.** `write_package` opens `xb`, atomically refusing an
   existing path. Two concurrent writers leave one complete winner under
   successful filesystem writes; crash durability is not promised.

**Evidence.** `tests/test_deliverable_package.py` proves isolated `-I -S`
execution with only a package in the temporary directory, stdlib imports,
metadata-before-read bounds, duplicate/extra/missing/traversal names,
encryption/method rejection, compression-ratio rejection, total malformed-input
handling, concurrent exclusive writes, deterministic members, renderer-pin
checks, and forged declared lengths/CRC/counts. Existing render, filing and
LITE route tests remain required; this decision does not enable filing routes.

## 2026-09-14 §56 — Prove the smallest forecast-owner catalog pathway

**Decision.** Phase 5.2a selects `FULL_CREDIT_32` / `RELATIVE_VALUE`, the
nine-node pathway containing CP-1, CP-2G, CP-4 and every required predecessor.
`DISTRESSED_RESTRUCTURING` needs thirteen nodes and `FULL_CREDIT_ASSESSMENT`
nineteen. Those larger pathways remain disabled. The adapter adds only this
pathway beside LITE earnings, after deterministic canonical contract proofs
for CP-1, CP-1C, CP-2, CP-4, CP-3D, CP-2A, CP-2G and CP-3.
Run choices continue to derive from the same adapter allowlist.

The real runtime must preserve every direct accepted upstream digest, exact
Markdown and anchored citation; Restricted limitations survive downstream;
Blocked CP-1 accepts nothing and prevents further calls. OPTIONAL and ADVISORY
edges retain the catalog engine's semantics. The request ceiling is unchanged.
Offline structural and lineage evidence does not qualify economic conclusions
or authorize live-provider evaluation.

**CP-2G boundary.** Its vendor schema declares twelve columns and exactly 42
rows: BASE/DOWNSIDE, three fiscal years, three division-growth slots plus four
financing/investing drivers. Its `driver_id` vocabulary is `division_growth`,
`acquisitions_disposals`, `net_equity_issue_repay`, `dividends_paid`,
`other_investing_financing`; `status` is READY/NOT_APPLICABLE. This is not the
CP-CF movement vocabulary. Task 5.2b must map it explicitly and obtain any
missing operational movements from accepted owners; 5.2a does not rename
vendor columns, fabricate missing inputs or enable CP-CF.

**Binary authority.** CP-3's manifest lists two XLSX references,
`REF_CP-3B_Portfolio_Constraints.xlsx` and `REF_CP-3_Sector_RV.xlsx`. The
UTF-8-only prompt previously refused them. These exact CP-3 references now
retain their complete verified bytes as explicitly labelled base64 in the
authority section; both the manifest and delivered-authority digests still
bind the original bytes. Invalid ZIP containers and other non-UTF-8 authority
still refuse. No workbook is executed, extracted or restored as a deliverable;
the existing whole-request ceiling also bounds the encoded representation.
**Evidence.** `tests/test_deliverable_package.py` covers isolated `-I -S`
execution, stdlib imports, metadata-before-read bounds, duplicate/extra/
missing/traversal names, encryption/method rejection, compression-ratio
rejection, total malformed-input handling, concurrent exclusive writes,
deterministic members, renderer-pin checks, and forged declared lengths/CRC/
count failures. Existing render, filing and LITE route tests remain required;
this decision does not enable filing routes.
