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

`canonical-markdown-v3` makes that delivery concrete. Before CP-0 is called,
the canonical adapter verifies every pinned member remains delivered and each
original BlobStore object still hashes to its pinned digest. It gives CP-0 a
tagged, non-citable `HOST SOURCE PREPARATION` context with source-set identity,
the content-addressed original root and provenance fields. The same original
checks recur before accepting or replaying the response. This is enough to
establish host-held preparation facts, but it does not certify the model-owned
P1–P8 workflow; CP-0 still authors and validates those registers. The context
does not reach downstream modules. An original blob lost after billing is a
store fault, not an answer verdict: the worker releases the run and replay uses
the already billed diagnostic once the operator restores the blob.

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

Every request sets `max_completion_tokens: 65536`, `allow_fallbacks: false`, and
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

*Retired in part by Completion Phase 8 Task 8.2 (`0d31a67`, `9c7f161`):* the
upgrade this entry named is taken. A call no longer reserves `worst_case(price)`;
it reserves `priced_request(price, request_size(provider, prompt))` over the
request `check_context` built and bounded, and `canonical._within_reservation`
re-prices the rebuilt request against the reservation's stored price before the
call. `worst_case` stays as the run's admission check against its **ceiling**,
not its remainder. Migration `0024` stores the dated price beside the amount.
Unchanged: the byte-per-token bound, the reconciliation after the call, and
"an application price cannot guarantee a vendor bill" -- the reservation's output
component is still the completion cap at the configured rate, so a vendor billing
reasoning tokens beyond it still overruns. The price's source remains the owner's
and is still not decided here. Recorded in place rather than as a new entry
because this is one clause of §40 becoming untrue, and the Phase 8 confidence
review found that no later entry said so.

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

## 2026-09-14 §43 — The suite runs across processes, and CI caches image layers

**Decision.** Two build-time additions, neither reaching the runtime image:

1. **`pytest-xdist==3.8.0`** (bringing `execnet==2.1.2`) joins the development
   lock, hashed and wheels-only. `make test` and the `test` CI job run
   `pytest -n auto`. Each worker builds its own migrated template and every
   test still mints a uniquely named database, so no worker shares state with
   another. `test-fast`, `test-postgres-races`, the `postgres` job and the live
   provider suite stay single-process. Parametrize ids must be deterministic,
   since every worker must collect the same tests.
2. **`docker/setup-buildx-action` v4.3.0 and `docker/build-push-action`
   v7.3.0**, commit-pinned, build the `image` job's image with
   `cache-from/to: type=gha` and `load: true`. Nothing is pushed. Local
   `make image` keeps the plain `docker build`.

**Reason.** Measured locally on 2026-09-14 (10 cores): the full suite took
5:45 serially without coverage and 1:43 with `-n auto` and coverage, 2,199
passed, 97% coverage, and the Cobertura floor held. The serial run used about
a third of one CPU: its time is PostgreSQL round trips, which parallel workers
spread. The image job rebuilt the apt and pip layers on every run.

**Cost.** A test that depends on another test's side effects or on global
ordering can now fail intermittently; none did. The GitHub cache is a mutable
input to the image build, but every layer it restores is keyed on the pinned
base digest and hashed lock, and Trivy scans the loaded result either way.

**Rollback.** Drop `-n auto` from the two call sites (the dependency can stay
unused), or restore `docker build -t caos:ci .` in the `image` job.

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
2. **Completion cap.** The initial 32,768-token cap refused a length-truncated
   answer, kept its bill and accepted nothing. §59 raises the current cap to
   65,536 after authorized live evidence; length truncation still refuses and
   accepts nothing.
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
5. **`.mypy_cache`** is cached in the `types` job, keyed on the dev lock.

**Reason.** A push to a branch with an open pull request started two full
runs whose refs differ, so `cancel-in-progress` cancelled neither. The
default token may carry write scopes no job uses. Mixed action versions are
two things to maintain per action. uv is what the Makefile already installs
with, and it resolves and installs the same hashed, wheels-only locks faster.

**Rollback.** Revert the workflow commit; nothing outside the workflow
depends on these changes.

**Addendum, from reconciling with `main`'s independent CI work (18 September
2026).** `main` wrote its own version of this entry as its own §48, with two
items this one lacked: the `.mypy_cache` caching folded in above, and a
separate `sonar.exclusions` change adding `**/*.sql` -- `sonar.sources` lists
`scripts` and `server`, both holding plain PostgreSQL DDL
(`server/store/schema.sql`, its numbered migrations,
`scripts/dev-init.sql`), and SonarCloud's PL/SQL sensor claims `.sql` files by
extension regardless of dialect: the analysis logged "The Data Dictionary is
not configured for the PLSQL analyzer," which four rules need and which this
project, having no Oracle database, cannot supply. Folded into
`sonar-project.properties` here rather than given its own entry, because it
is one line beside the existing `vendor/**` exclusion and the same kind of
unenforced exception.

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
   `handoff_accepted`, `run_terminal`, `sources_changed`, `runs_changed` and
   `filing_changed` (`server/api/events.py` `STREAM_NAMES`). Admission and withdrawal are
   `sources_changed`; create run, pin input, both gate releases, start, retry
   and cancel are `runs_changed`; sign, freeze and file are `filing_changed`,
   which refetches Report and Committee; `CASE_CREATED` and `REVISION_SAVED`
   are silent. A test fails a
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
   from groups. **Superseded by §70.2:** the "otherwise" covered the case with
   neither set, in which a request's own groups header chose its global role.
   With no edge token and no switch the role is now READER.
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
   `host.render_payload` (**deleted as dead in §74.5**; nothing in `server/`
   catches `RenderRefused`, so the guarantee below has no subject left to
   violate) maps this to the existing host `RefusalCode`/`Refusal`,
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

**Evidence.** `tests/test_deliverable_package.py` covers isolated `-I -S`
execution, stdlib imports, metadata-before-read bounds, duplicate/extra/
missing/traversal names, encryption/method rejection, compression-ratio
rejection, total malformed-input handling, concurrent exclusive writes,
deterministic members, renderer-pin checks, and forged declared lengths/CRC/
count failures. Existing render, filing and LITE route tests remain required;
this decision does not enable filing routes.
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

## 2026-09-14 §57 — Save the host revision before sign, freeze and file

Task 5.3 replaces caller-supplied revision labels, digests and freeze payloads
with a host-minted UUID and immutable stored payload. `save_revision` derives
every accepted canonical artifact in pinned route order under the governed
case lock, obtains the case title from the store, validates the narrative and
stores its canonical bytes in the content-addressed blob store. An incomplete
or refused route cannot be saved; accepted restrictions and limitations remain
in the exact records and render. No provider is involved.

Migration `0015_revisions` adds immutable `deliverable_revisions` rows. The
legacy opinion/publication keys are text, so a generated canonical UUID text
key enables composite `(case_id, revision_id)` foreign keys without converting
legacy labels. `NOT VALID` preserves existing history while enforcing every
new signature/publication's saved case/revision ownership. No old labels are
backfilled with fabricated revisions.

Narrative is at most 64 paragraphs of 1–64 spans: bounded text or an accepted
artifact's `(route_node_id, citation_index)` reference. Text is normalized by
BoundaryText with a 2,000-character ceiling; ASCII digits refuse
`NARRATIVE_FIGURE_UNREFERENCED`. References resolve to the accepted anchored
document, page and matched text, with unknown/malformed references refused.
This syntactic control is not semantic detection of numbers spelled in words
or misleading qualitative prose; the independent human review still owns that.

Sign reads the stored digest under the lock. Freeze re-proves the stored
revision inside the same governed write, compares exact bytes and the current
signature, then records the frozen digest. No signer can freeze; no signer or
freezer can file. A frozen revision admits no later signature and can freeze
and file only once. `read_revision` and `prove_revision` participate in their
caller's transaction; the latter requires the caller to hold the case lock
for a governed transition. Live withdrawal or moved authority refuses re-proof;
archived package consistency remains independent of live source availability.

Filing returns case/run/revision identity, all three actors, payload and
renderer digests, and `filed_event_sha256` returned by its own governed write.
The receipt never reads the possibly advanced audit head after commit. The
renderer digest is computed before filing and included in its audit payload.
The portable renderer accepts the new spans, and its verifier pin changes with
its exact source bytes; historical string narratives remain renderable only
for old payloads, never accepted by the new save boundary.

Codex execution uses Astra high for this high-risk revision boundary. Ordinary
task review and scoped gates precede integration; phase confidence/adversarial
reviews remain coordinator-owned at actual xhigh after the whole phase.

## 2026-09-15 §58 — Qualification binds OpenRouter endpoint and reasoning profile

The September 15 DeepSeek qualification calls exposed a false premise in §16
and §25: `allow_fallbacks: false` prevents a second endpoint after the selected
one fails, but OpenRouter still chooses that first endpoint by price and
availability. Reconciliation showed that all three calls ran on Ionstream and
used zero reasoning tokens. They therefore test `openrouter/ionstream/default`,
not DeepSeek's first-party reasoning profile.

`OpenRouter` now accepts optional `OPENROUTER_PROVIDER` and
`OPENROUTER_REASONING_EFFORT`. A provider value is sent as the sole ordered
endpoint with fallbacks disabled; the reasoning value is sent through
OpenRouter's reasoning-effort contract. A pinned qualification provider
identity includes both settings and the completion ceiling (for example
`openrouter/deepseek/max/65536`), while an unset legacy profile remains
`openrouter`. Invalid values refuse before transport.
The model id and dated conservative price remain separately bound.
The qualification harness refuses that unpinned legacy profile; automatic
routing remains available only to ordinary calls that cannot mint a verdict.

The canonical prompt changed during citation remediation, so the adapter is
advanced from `canonical-markdown-v1` to `canonical-markdown-v2`. Old v1 pins
remain historical and cannot execute as v2. A new positive qualification must
prepare a fresh v2 run; it cannot reuse the three cross-revision failures.

OpenRouter provider routing takes the endpoint catalog's lowercase `tag`, not
its display name, so mixed-case values refuse before transport. The configured
account returned `404 No endpoints found` for the live first-party `deepseek`
tag even without reasoning or JSON constraints. An `ionstream`/`xhigh` JSON
probe did succeed and reconciliation recorded 15 native reasoning tokens, but a
probe is not a qualification run.

The authorized frozen-v2 `ionstream`/`xhigh` qualification then used 6,286
native reasoning tokens and finished with `stop`; the host still refused CP-0
as `CITATION_NOT_DELIVERED`. No downstream module ran and no qualification
evidence or verdict was created. This rules out automatic routing, absent
reasoning and truncation for that failure. A same-input temperature-zero repeat
would change no controlled variable, so the run was not repeated.

At that checkpoint, this did not qualify DeepSeek or raise the 32,768
completion cap. It made a controlled endpoint/reasoning experiment possible
through the existing runtime and kept ordinary/offline gates credential-free.

## 2026-09-15 §59 — Gemini replacement is bounded by the shipped output ceiling

The authorized replacement candidate is `google/gemini-3.8-flash` through the
pinned OpenRouter `google-ai-studio` endpoint at reasoning effort `high`.
Google supports structured output and up to 65,536 output tokens for this
model; the exact shipped CAOS runtime initially requested at most 32,768.

The frozen VMO2 CP-0 call was served by Google AI Studio, used 29,454 native
reasoning tokens, exhausted 32,761 native completion tokens, and finished with
`length`. The host therefore recorded `PROVIDER_OUTPUT_TRUNCATED` before any
artifact or qualification evidence existed. The `$0.25356225` charge remains
inside the authorized `$22.00` ceiling.

Do not repeat that same high-reasoning, 32,768-token request. The authorized
remediation raises the shared CAOS ceiling to the model's 65,536 maximum, which
also raises each run's conservative reservation. The changed ceiling is bound
in the fresh execution profile identity
`openrouter/google-ai-studio/high/65536`; it requires verification before the
one authorized paid retry.

That retry reached the temporary qualification collector, which returned from
`perform()` but then failed while JSON-encoding a proof's `frozenset` of anchored
citations. Cleanup dropped its disposable database before it emitted generation
or charge data. The account cannot use OpenRouter's aggregate activity endpoint
for reconciliation without a management key (`403`). Its actual route outcome
is therefore indeterminate and creates no artifact, evidence or verdict. The
next execution persists its immutable performed snapshot and its bound evidence
identity in the migrated store before `perform()` returns; the collector only
confirms and retains that state for external review. Do not repeat this paid
attempt without fresh authorization.

## 2026-09-15 §60 — Preserve literal quotation at the canonical boundary

The recovery run at profile `openrouter/google-ai-studio/high/65536` completed
normally and retained its performed snapshot and bound evidence. Its CP-0
response was valid closed JSON, its four citations were all delivered and
uniquely anchored, and its canonical Markdown passed the vendor validator. The
host refused it only because none of those evidence quotations occurred
character-for-character in the Markdown body. Safe structural comparison found
case-only variation for three quotations and punctuation-normalized variation
for all four, including the required Evidence Trace section.

This is a Gemini 3.8 Flash one-shot protocol incompatibility. It is not a
reason to relax `parse_response`: a citation needs both an exact source anchor
and an exact occurrence in the model's handoff, so a reviewer can see the same
words supporting the claim. General punctuation/case normalization would admit
meaning-changing edits and would weaken the pinned canonical contract. The
model is therefore unqualified; its performed evidence cannot mint a verdict.
Any future spend must be a separately authorized, materially different
candidate or protocol experiment.

## 2026-09-16 §61 — Two authorised edits inside the vendored bundle, and the build they produce

Invariant 4 says never edit a file that exists upstream. On 16 September 2026
the repository's owner authorised two edits to `vendor/deploy-v/`, these and no
others, after the VMO2 qualification runs (`qualification/vmo2-fy2025/RESULT.md`)
showed both to be defects in the methodology itself rather than in the host's
reading of it. This entry is the override, scoped to the two changes below, and
§13's pin moves to the build they produce. Upstream
`github.com/EricMG13/Deploy-V@c4d2e356` does not carry either change: the
vendored tree is now that build plus these two, and the next upstream pull
either carries them forward or supersedes them with an entry here.

**Change 1 — `CONDITIONAL` is a source condition.** CP-0 defined the verdict
only by its effect (`exact_command = DO NOT RUN`), and a live run marked CP-5
`CONDITIONAL` on "CP-L10 must first produce the selected-route analytical
handoff", ending the route BLOCKED after two modules had been paid for. The rule
is now stated in each of the three places CP-0 reads it —
`skills/cp-0-source-readiness/SKILL.md` (the T8 contract),
`references/REF_CP-0_STEPS.md` (step I, the verdict and rule 4 of the command
sheet) and `references/CP-0__SourceReadiness__payload.schema.txt` (the
`recommended_run_commands` rules) — in the same words: `CONDITIONAL` names a
source, or the prepared representation of one, that the effective-source set
does not carry; it is discharged only when that named source is supplied and
CP-0 is re-run; an upstream analytical handoff that has not yet been produced is
never a readiness ground, because navigation and the catalog's edges sequence
modules and `readiness` does not. "Or the prepared representation of one" is
what keeps `CP0_CAPACITY_RESUME_CONTRACT_v1.md` consistent, where readiness
stays `CONDITIONAL` while a required parse is still running.
`tests/test_bundle_pin.py::test_cp0_defines_conditional_as_a_source_condition_everywhere_it_is_read`
fails the day any of the three copies stops saying so.

**Change 2 — the validator derives the status floor from the findings.**
`CANON_SHARED.md § CP_CONFIDENCE_SCORE.md` and CP-5A step 11 say any MATERIAL
finding is at least `Restricted` and any CRITICAL one is `Blocked`, and
`confidence_score.py` applies exactly that — to counts the module passes it.
`validate_handoff.py` checked only the score caps given the declared status, so
a CP-0 declaring `Passed`, `Committee Ready`, 93 over its own
`SOURCE_GAP | MATERIAL` row was conformant, and a second live CP-0 declared
`Passed`, 78 over two CRITICAL rows. The validator now reads every unfenced
pipe table whose column is headed `Severity` (emphasis and backticks stripped,
case-folded, the header may carry a qualifier), takes a cell that begins with
one of the canon's three words as a finding, and refuses a CRITICAL finding
under any status but `Blocked` and a MATERIAL finding under `Passed`. It is a
floor, never a ceiling: `Restricted` or `Blocked` with no finding row stays the
module's own stricter call, a fenced table is not a finding, and a column
headed anything else is not read. Vendor errors go to the host as
`HANDOFF_MALFORMED`, which is what a `confidence_band` inconsistent with its
score already is.

**How the edit was made.** The validator was changed once, at the `SHARED`
owner the bundle declares (`cp-0-source-readiness/scripts/validate_handoff.py`),
and `verify_package.py --refresh` — the bundle's own procedure for an
intentional edit — synchronised the 24 byte-identical copies, ran its 52 unit
tests and 10 helper self-checks, and regenerated `DEPLOY_V_INTEGRITY_v1.json`,
`DEPLOY_V_MANIFEST.json`, `DEPLOY_V_BASELINE.json`,
`CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json` and the two Copilot memory prompts. The
host loads only the `cp-os-credit-os` copy (`server/methodology/vendor.py`),
but the refresh refuses "shared implementation drift", so editing one copy was
never an option. Build id
`cdea0c9fbb046321fdd6d0fb526b6bc74cf4c9e9e2ea4b381f1c4a61081e9d22`; the
manifest's own SHA-256 is
`087bbdf8421aca31cac4e04adf3c85d779cc4822cff748e0715d24a82157b1da`, still
68,657 bytes, so §35's ceiling reasoning is unchanged. The five host pins that
compare against the bundle moved with it (`tests/test_bundle_pin.py`,
`tests/test_methodology_bundle.py`, `tests/test_qualification_matrix.py`,
`tests/test_loop_charges.py`, `tests/test_canonical_proof.py`), and
`tests/test_delivered_authority.py` re-measures CP-0's delivered authority at
145,928 bytes, 1,061 more than at `a43cb903` — exactly the three prose additions.

**What it costs.** Every run pinned to `a43cb903` — including the VMO2 runs
`RESULT.md` rests on — now refuses `ORCHESTRATION_BUILD_MOVED` on re-proof.
That is the Phase 10 gap read strictly and the fail-closed direction: their
artifacts, charges and citations stand as recorded, and their proofs are no
longer re-derivable against this tree. A qualification set's digest covers
documents, keys and route selection, not the build, so sets are unaffected.

**Decided against, here.** `completeness_check.load_contract` reads only the
`critical_cell_*` disqualifiers and never `frontmatter_limitation_flags`,
`frontmatter_validation_warnings` or `document_substrings_casefold`. That is a
second rule with its own semantics — envelope flags that name a fixture as not
a current golden, and whole-document substrings — which
`server/methodology/handoff.py` already records as a host gap; it is not the
canon's severity rule, and folding it in would make one authorised edit into
two. It stays open, with its own entry the day it is authorised. The bundle's
own `tests/` were not extended, being upstream files outside the
authorisation; the named tests live in the host suite
(`tests/test_canonical_handoff.py`, `tests/test_bundle_pin.py`).
`CANON_SHARED.md` is untouched: the rule was already there, unenforced.

## 2026-09-16 §62 — Phase 6 accepted by the owner, with the gap stated

The owner accepted Phase 6 on 16 September 2026 and deferred CP-5 until the
other modules are deployed. This entry records that decision and exactly what it
does and does not assert, because `docs/REPAIR_PLAN.md` Phase 6's exit checks
are not all met and a later reader must not mistake acceptance for satisfaction.

**What is true.** A complete `make check` is green: lint, mypy over 227 files,
2899 tests, 21 race tests, bandit, pip-audit, gitleaks, the frontend half, the
image half under pinned Trivy 0.70.0, and the production smoke stack on three
engines. Seven authorised live runs were performed against a real provider and
every one of them is recorded in `qualification/vmo2-fy2025/RESULT.md` with its
charges, generation ids and outcome. Run `42e17048-8b50-48cc-94ff-833d894a68cb`
produced the first `qualification_performed.complete` snapshot: route COMPLETE,
three artifacts, eight citations all re-located, the citation key met, the
readiness key met, every declared conclusion met.

**What is not true, and is being accepted anyway.**

1. **No verdict exists.** `qualification_verdicts` is empty in every run
   database. Phase 6 item 3 wants an authenticated review verdict over exact
   performed evidence; nobody has signed one. Nothing in this repository may
   describe any build, model or pathway as QUALIFIED.
2. **The one complete snapshot is pinned to a retired build.** It was performed
   under `a43cb903`; §61 moved the bundle to `cdea0c9f`, so that run refuses
   `ORCHESTRATION_BUILD_MOVED` on re-proof. There is no complete snapshot on the
   build the tree now carries.
3. **CP-5 does not currently complete on this corpus.** Run `36d87283…` refused
   it three times for writing "insufficient information" and "not calculable
   from provided materials" in a column its own contract calls critical — the
   honest answer, refused. Deferred by this decision, not solved.
4. **Phase 6 item 4 wants qualification on every route intended to be
   advertised.** One pathway, `LITE_CREDIT_22 / LITE_EARNINGS_UPDATE`, has been
   run. The other seventeen have not.

**What the deferral commits to.** CP-5 is revisited once the other modules are
deployed. The mechanism is known and recorded in `CLAUDE.md`:
`disqualifier_exempt_columns` already exists and T5B.6 uses it, so the question
is which of CP-5's status columns should carry it. That is a bundle change and
needs its own authorisation under §61's precedent.

**Standing constraint.** This entry is an acceptance of a phase, not a
qualification of a build. The guardrail in `docs/REPAIR_PLAN.md` — no shipping
unqualified pathways behind a generic success label — is unaffected by it, and
any surface that reports qualification status must continue to report that
there is none.

## 2026-09-16 §63 — CP-5 may say a claim is not calculable: T5B.5's status columns exempted

§62 deferred CP-5 until the other modules were deployed. On 16 September 2026
the owner instructed that its completion be resolved now, which supersedes that
deferral, and authorised **one** further edit to `vendor/deploy-v/` under §61's
precedent — this one and no other. Upstream `github.com/EricMG13/Deploy-V@c4d2e356`
does not carry it; the vendored tree is that build plus §61's two changes plus
this one, and the next upstream pull either carries all three forward or
supersedes them with an entry here. The edit and the pins it moves landed in
`bb47f12`; this entry is the record that was still owed when that commit was
made.

**The change.** In `skills/cp-5-evidence-trace-validator/SKILL.md`, register
T5B.5's `disqualifier_exempt_columns` moves from `none` to `Status; Claim
Status`. Nothing else in the file, and nothing else in the bundle, changes.

**Why.** `full_run_disqualifiers.critical_cell_values_casefold` lists
`insufficient information`, `not calculable from provided materials`, `not
assessable` and `unavailable`, and every column of T5B.5 — the calculation and
assumption register — was critical with none exempt. T5B.5 is where CP-5
reproduces a calculation and records what became of it, so "not calculable" in
its `Status` column is the answer the runbook asks for when the sources carry
none. Run `36d87283-ef92-49a2-a2b1-ef5928aaa5d2` refused CP-5 three times,
each billed, with exactly `T5B.5 row 3: critical column 'Claim Status' holds a
disqualifying placeholder 'Insufficient Information'` (attempts 1 and 2) and
`T5B.5 row 2/3: critical column 'Status' holds a disqualifying placeholder
'Not Calculable from Provided Materials'` (attempt 3). In each refused row the
seven substantive columns were filled — the item, where it is used, the inputs,
the formula or the reason there is none, the confidence, the credit relevance
and the source trace — and the only cells that tripped the rule were the two
that state the claim's standing. Handed two earnings releases, CP-5 said that
covenant leverage is not calculable without the executed debt definitions and
was refused for saying so; a validator that cannot write that there can pass
only by overstating what the evidence supports. The precedent is in the same
contract: T5.2 exempts `Evidence Status`, T5B.3 exempts `Classification` and
`Claim Status`, T5B.6 exempts `Classification` — each the column that records
the state of a thing rather than the thing.

**Proved, not assumed.** The three refused bodies are retained in the run's
blob root (`caos-qualify-9r7nyozi`, the `diagnostic_sha256` values in
`qualification/vmo2-fy2025/v3-run7-capture.json`). Replayed through the
bundle's own `completeness_check.check(skill_text, body, "CP-5")` — the call
`server/methodology/handoff.py` makes — against the SKILL.md at `449750c` they
produce one, one and two violations, the messages above verbatim; against the
edited SKILL.md all three produce none. The same body with a placeholder moved
into a substantive T5B.5 cell is still refused (`TBD` in `Formula or Logic`,
`Unavailable` in `Source Trace`, `[Insufficient Information]` in `Item`), a
T5B.5 with its rows removed is refused for having none, and `Not Assessable` in
T5B.4's `Source Quality` — an unexempted register — is refused. No provider was
called; the replay is against the checker and cost nothing.
`tests/test_bundle_pin.py::test_cp5_exempts_only_its_status_columns_from_the_disqualifiers`
holds the contract: exactly those two columns exempt, all nine still critical,
the four phrases still in the blocklist, and a placeholder in any of the seven
substantive columns of the LITE fixture's CP-5 handoff refused by name.

**Judged and not widened.** Every one of the seventeen registers was read for a
status-shaped critical column with the same problem. T5.1's `QA Status` and
`Envelope / Headings Status` describe upstream handoffs that exist and take
the QA vocabulary, T5.9's `Status` is an issue's open/closed state, and T5B.3's
`Citation Present?` is a yes/no — none can honestly hold one of the four
phrases. Two could: T5B.3's `Traceability Status` and T5B.7's `Assessment`,
where "not assessable" is a plausible honest answer. Neither has been observed
failing, and exempting a column on a hypothesis is how an exemption becomes the
register; they stay critical, and the day a run refuses one of them for the
honest answer is the day it gets its own line here.

**What it costs.** An exempt column skips both the value blocklist and the
substring rule, and the empty string is in the blocklist — so an empty `Status`
or `Claim Status` cell now passes where it was refused before. That is exactly
the property T5.2's, T5B.3's and T5B.6's exemptions already have, and the seven
substantive columns still refuse an empty cell. Every run pinned to `cdea0c9f`
— `36d87283…` and the re-run `RESULT.md` records against that build — now
refuses `ORCHESTRATION_BUILD_MOVED` on re-proof, as §61 did to the runs before
it. No live run has yet been made on the new build.

**How the edit was made.** `verify_package.py --refresh` — the bundle's own
procedure for an intentional edit — ran its 52 unit tests (2 skipped) and 10
helper self-checks and regenerated `DEPLOY_V_INTEGRITY_v1.json`,
`DEPLOY_V_MANIFEST.json`, `DEPLOY_V_BASELINE.json`,
`CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json` and the two Copilot memory prompts; the
only content that moved is CP-5's entry, 23,285 to 23,301 bytes. Build id
`30222a494a5a1035c7955cb1ccfbe0b3b0fbbfa7d6426930f5dcf4d35aa1fc18`. The
manifest the host verifies at rest is `DEPLOY_V_INTEGRITY_v1.json`
(`server/methodology/bundle.py::MANIFEST_NAME`); its SHA-256 is now
`8ccc8ed035745b5fb3a18d1176f0bfbbbc2c7e337357bbf25828c3611f3d110e`, still
68,657 bytes, so §35's ceiling reasoning is unchanged. The six host pins moved
with it: `tests/test_bundle_pin.py` (`BUILD_ID`), `tests/test_methodology_bundle.py`
(build id and manifest digest), `tests/test_qualification_matrix.py`,
`tests/test_loop_charges.py`, `tests/test_canonical_proof.py`, and
`tests/test_delivered_authority.py`, which re-measures CP-5's delivered
authority at 165,548 bytes — the sixteen bytes of the edit. `docs/REPAIR_PLAN.md`
line 40 still names `cdea0c9f`; that file is the owner's and is not edited
here.

**Decided against, here.** Widening to the two candidate columns above, for
the reason given. The `completeness_check.load_contract` half §61 left open —
the frontmatter and document-substring disqualifiers the host never reads —
is a different rule and stays open. The bundle's own `tests/` were not
extended, being upstream files outside the authorisation; the named test lives
in the host suite.

## 2026-09-16 §64 — The three repair-plan findings that had no trace, traced

`docs/REPAIR_PLAN.md` Phase 6's exit check wants each F01-F18 finding linked to
its regression and fix. F05, F07 and F17 appeared nowhere in this tree outside
the plan: the work was done under other names and the F-numbers were never
carried into a commit message or a test. Two are finished and were merely
unlabelled; the third is finished in part and its remainder is stated here
rather than left to be rediscovered.

**F05 — governed writes have two concurrency holes. Fixed; §32, `f4ff307`.**
`server/store/audit.py::governed_write` takes `lock_case` before `_lock_head`
and before `_require_standing`, and `members.py::grant/revoke` take the same
lock, so a revocation and a governed write have one commit order and two first
writes on a case serialise on the case row rather than on an absent audit head.
A raw `UniqueViolation` is now `STORE_UNAVAILABLE` with rollback. The
regressions are in `tests/test_case_ordering.py`, which proves real two-connection
blocking through `pg_blocking_pids` and fails if the waiter never blocks:
`test_membership_change_first_refuses_waiting_approval[revoke|downgrade]` for the
first hole, `test_two_first_approvals_serialize` for the second.

**F07 — PDF admission and word extraction are incorrect. Fixed; §44, §47,
`83fe083`, `e292238`.** `server/evidence/pdf.py::_runs` ends a run on pdfminer's
virtual whitespace, so `A B` no longer extracts as `AB`
(`tests/test_pdf_extraction.py::test_words_separated_by_positioning_are_separate_tokens`,
which returns `["AlphaBeta"]` if reverted). `extract.py::dispatch_by_content`
reads the bytes rather than the name
(`tests/test_extractor_dispatch.py::test_a_pdf_named_txt_is_still_read_as_pdf`,
and at the harness boundary
`tests/test_qualification_prepare.py::test_the_harness_admits_pdfs_through_the_pdf_extractor`).
Encrypted and unreadable documents get typed codes, and rectangles are
top-left in displayed space at every quarter turn
(`test_rotated_page_rectangles_are_top_left_in_displayed_space`).

**F17 — qualification can certify the wrong identity. Fixed in part.**

- *Run-to-case binding:* `harness.py::_eligible` re-reads the pinned `RunInput`
  and refuses `RUN_INPUT_INVALID` unless title, ceiling, profile, selection,
  research, model-extension presence and the pinned source-set members all match
  the case; `perform` binds provider and model identity.
  `tests/test_qualification_execution.py::test_real_approved_input_transplants_are_refused`
  substitutes each of ten bindings in turn and requires a refusal with no prompt
  sent. Fixed, `1f86f02` and `f95e8ba`.
- *Verdict time:* `read_verdict` refuses a naive `now` and a future
  `decided_at`. Fixed, `373ee07`; `tests/test_qualification.py`.
- *Preflight before spend:* `prepare` resolves every route and builds every
  label before the first `create_case`
  (`test_whole_set_pure_defects_leave_no_setup`). Fixed.
- *Unbounded on-disk reads:* fixed today. `on_disk.py::_bounded_bytes` stats the
  path, refuses anything that is not a regular file, and refuses a document
  larger than `admit_pack`'s own ceiling before reading it -- so a multi-gigabyte
  document is not read into memory to be rejected afterwards, and a FIFO at a
  declared path no longer blocks the loader.
- *No authenticated producer:* **open.** `record_verdict` exists, is bound and is
  tested, and `server/api/reads/qualification.py` serves the consumer, but
  nothing in `server/` or `scripts/` calls it and `reviewer_id` is a
  caller-supplied UUID with no OIDC derivation. This is why §62 records that
  `qualification_verdicts` is empty everywhere: there is no route by which a
  reviewer can sign. Recorded in `CLAUDE.md` as the open half.
- *Caller-dependent binding:* `build_matrix` still accepts any `runs` mapping and
  checks only label presence; the binding lives in `_eligible`, its only caller.
  Recorded in `CLAUDE.md`.

## 2026-09-16 §65 — A reviewer can sign a verdict; the host still cannot call itself qualified

F17's open half (§64) is closed by `server/api/commands/qualification.py`:
`POST /api/v1/qualification/{evidence_sha256}/verdict`. Before this there was no
route by which a person asserted a verdict, which is why §62 recorded
`qualification_verdicts` empty everywhere and the final check listed it first.

The body is the reviewer's six-binding document (`SignVerdict`, closed at the
wire), and `read_verdict` remains its only reader, judged against the store's
clock — so the moments travel as text and what the document *means*, a naive or
future `decided_at` or a passed expiry, is decided in one place rather than
twice. `reviewer_id` is `Actor.user_id` as the edge derived it, from OIDC groups
in production and from the trusted header only in development, and from nowhere
else; it is not a field of the request, and a body naming one is an undeclared
field refused before a connection opens.

The floor is `ADMIN`, by `at_least` over `_RANK`. A verdict is the first
authority in this system that is genuinely account-wide: every other write by an
`ANALYST` also requires standing on the case, and here there is no case for
standing to attach to, so the global role would be the sole authority and the
lowest writing rank has never been sufficient alone. Below the floor, and for
evidence the store does not hold, the answer is one private 404
(`QUALIFICATION_EVIDENCE_NOT_FOUND`), so a caller cannot probe which evidence
digests exist — the same shape the read route gives a `READER`.

`record_verdict`'s bindings — provider against the host-recorded `provider:model`,
set digest, build, and `complete` — are not repeated here, only mapped to the
wire. The write is one transaction and a refusal rolls it back.

**What this does not assert.** Nothing here lets the system call itself
qualified. The route records a person's assertion over evidence the harness
already produced and `record_verdict` already binds, and the label a reader sees
is still `current_verdict` re-validating that document. Two limits were recorded
here and both are closed by Completion Phase 8 Task 8.3 (`cf3d805`): a second
signature is now `VERDICT_ALREADY_RECORDED` at 409, mapped by the one-verdict
constraint's declared name, and the write records a `command_requests` receipt
under the nil scope in the verdict's own transaction, with the evidence digest in
the request digest so one key replayed against other evidence is an idempotency
conflict rather than that evidence's receipt. The same task added a binding this
entry did not have: a verdict must name a model the runs recorded, which is
"no run contradicts and one confirms" rather than "every run confirms", because a
signable snapshot may hold a case whose declared refusal was met and whose run
accepted nothing. *Retired in place, for the reason under §40 above.* Verified
against a
throwaway clone of the retained `caos_qualify_5a47243d…`; that database still
holds no verdict, because signing the evidence behind a final check is the
reviewer's act and not this change's.

## 2026-09-16 §66 — The frontmatter disqualifiers stay unenforced, and why

§61 fixed one half of the completeness contract and left the other open:
`completeness_check.load_contract` reads only the `critical_cell_*`
disqualifiers, never `frontmatter_limitation_flags`,
`frontmatter_validation_warnings` or `document_substrings_casefold`, which every
`SKILL.md` declares. It was listed in `docs/FINAL_CHECK.md` as owed. It was
implemented, measured, and **rejected**; this entry is the rejection, because a
declared rule nobody enforces needs a reason recorded as much as a rule that
changes.

**What the change did.** It read all three lists, from `full_run_disqualifiers`
and CP-L10's `screening_run_disqualifiers`, and reported a handoff declaring one
of those flags — or carrying one of those substrings in its unfenced text — as a
completeness violation, which the host maps to `HANDOFF_INCOMPLETE`.

**Why it was rejected.** Replayed against all 25 real handoff bodies this
repository has retained, it newly refuses **seven**: CP-0 and CP-L10 from runs
`33ca320e`, `729b0682`, `42e17048` and `54ec3752`. Every one of them for the
same reason — `limitation_flags` declaring `SOURCE_LIMITED_NOT_COMMITTEE_READY`.
Two of the seven are the accepted artifacts of `42e17048`, the first complete
qualification snapshot this project produced.

That flag is *true* of this corpus. Two earnings releases are source-limited and
are not committee ready, and a module saying so is doing its job. Refusing a
handoff for an honest declaration about its own evidence is exactly the defect
§63 had just repaired in CP-5, where "not calculable from provided materials"
was refused in the same spirit. The bundle's list conflates a **fixture** marker
(`INTEGRATION_FIXTURE_ONLY`, `PRESENTATION_FIXTURE_NOT_CURRENT_GOLDEN`,
`SYNTHETIC_FORWARD_ASSUMPTIONS`) with a **thin-evidence** marker
(`SOURCE_LIMITED_NOT_COMMITTEE_READY`); only the first is a completeness
question. Honouring the list whole refuses honest work, and honouring it in part
would be the host choosing which of the bundle's declared rules count, which
invariant 4 forbids.

**And the rule is already enforced, in the right place.** `limitation_flags` is
projected by `server/methodology/handoff.py::Projections` and is one of
`matrix.PROJECTION_FIELDS`, so a qualification key can assert on it directly —
visible to a reader, checkable by a set, and no refusal. A flag that says "not
committee ready" belongs in what a reader is told, not in whether the document
parses.

**What stays open.** The conflation is the bundle's, and the honest fix is
upstream: split the fixture markers from the evidence-status markers so the
first can be enforced and the second projected. Recorded in `CLAUDE.md` as a
gap against the bundle rather than against this host.

**Corroboration.** The one `document_substrings_casefold` hit across every
retained body was a CP-5 describing an upstream as "LITE, preliminary and
source-limited" — an accurate description of another module's output, which is
the same conflation seen from the other side.

## 2026-09-16 §67 — The insufficient-evidence case is demonstrated through the built UI

`docs/REPAIR_PLAN.md` Phase 6 asks that "a real PDF case and a deliberately
restricted/insufficient-evidence case are demonstrated through the
production-built UI". The PDF half was met by the journey's mixed text-and-PDF
pack and its citation-highlight check. The second half was not, and a test named
for the reader-role RESTRICTED state of the qualification strip was easy to
mistake for it — that is a permission state, not a run whose evidence was thin.

`frontend/tests/journey/journey.spec.ts` now carries *"journey: an
insufficient-evidence run ends BLOCKED and is shown as such, not as success"*.
It admits a deliberately thin pack, pins the input, takes both gates, starts the
run, and waits for the route's own rule to end it: the fake provider returns a
validated `Blocked` QA verdict, so the run ends BLOCKED by
`runtime._end_blocked` rather than by an error. It then asserts what a person
sees — the run page reads BLOCKED and **not** COMPLETE, while the two upstream
nodes that did produce artifacts read COMPLETE.

That last pair of assertions is the point. A blocked run must not be presented
as a finished one, and must not be presented as a failure either: the modules
that answered did answer. Under `make smoke-production` it runs against the
production image through the real edge on all three engines — 15 journey tests
each, where there were 14.

The case is a one-note pack with no covenant certificate
(`tests/journey/pack.py::insufficient_pack`), and the journey worker keys its
answer on the evidence the run pinned rather than on a flag: that document's
digest gets the Blocked verdict, the certificate's gets `Passed`. So the case is
about the evidence, one worker serves both journeys on one stack, and no model
is called.

**Driving it found what reading had not.** The exit check is met — the status
cell, the case register's tag and the handoff count are honest, and those are
what the test asserts. But `node_states` is recomputed from accepted artifacts
alone, and a validated Blocked accepts nothing, so CP-5 comes back `RUNNABLE`
and the workspace draws it pulsing "in the frontier" beside a `Status` of
BLOCKED; and the analysis document carries no run status at all, so that page is
indistinguishable from a run still in flight. Nothing on either page names the
verdict. Those two are recorded in `CLAUDE.md`'s Phase 9 ledger with their
upgrade — the run document carrying the blocking node, the analysis document the
run status — and are deliberately left unasserted rather than asserted as though
they were correct. A test that asserted them would pin the misleading behaviour
in place.

## 2026-09-16 §68 — Why a run ended BLOCKED is recorded by the transition, not re-derived

**Context.** Two commits made a BLOCKED run *look* blocked: nothing is drawn
running on an ended run (`093828f`), and the analysis page says the run ended
rather than "pending" (`78b1e61`). Neither page said *why*. On the
insufficient-evidence journey a reader saw BLOCKED, saw CP-5 "did not run", and
was left to infer that CP-5 was the cause — which is backwards. CP-5 ran, and
its answer was a validated `Blocked`. `node_states` is recomputed from accepted
artifacts (invariant 10) and a Blocked verdict accepts nothing, so the node's
state is RUNNABLE and always will be. The state is right; it cannot carry the
cause, and nothing else on the wire did.

**The obvious shape, and why it does not work.** The fact exists at the moment
the run ends: `runtime._end_blocked` asks `blocked_verdict`, which re-derives
the verdict from the stored bill and response body through `replay_billed`,
the same reader crash recovery uses. The first design was for the run document
to do the same. It cannot. `replay_billed` judges an answer through
`check_attempt`, which refuses `RUN_NOT_RUNNING` once the run has ended — and
takes the run's row lock to say so. That is not an accident to be worked
around: the replay is an execution-path check whose identity comparisons
(`call_time_identity`, `_assert_originals`, the lineage check) hold the world
still while the run is live. After the run, a source may be withdrawn
(invariant 1) or the bundle moved (invariant 4), and a reader that re-derived
the verdict would refuse the whole document over a fact that had not changed.
Why a run ended is a fact about the moment it ended, of the same kind as
`runs.status`, and it belongs beside it.

**Decision.** `block_run` takes `verdict`, the attempt whose validated Blocked
answer ended the run, and `_transition` writes it to `run_blocking_verdicts`
(migration `0021_blocking_verdicts.sql`) in the transaction that moves the
status and appends `RUN_BLOCKED`, riding the same conditional update — zero
rows moved, nothing recorded. The row is immutable (triggers, as the store's
other records), at most one per run (the primary key), and only an attempt of
that run: the insert selects the attempt through its own `run_id`, and
anything else refuses `ATTEMPT_NOT_FOUND` with the whole transaction rolled
back, so a run is never ended with a reason that names somebody else's answer.
Both paths that act on a Blocked verdict record it — the live one
(`_end_blocked`) and the replayed one (`_settle`, a crash in the commit gap) —
and `blocked_verdict` returns the attempt rather than a bool, since the caller
now records which answer it was. The end-of-loop path, §39's empty frontier
with required work unfinished, records nothing: no node's verdict ended it.

**The wire.** `RunView.blocked_by: BlockedByView | null`, where the view is
`{route_node_id, module_id, attempt_id}`. Nullable, and the docstring says why:
a run ends BLOCKED two ways, and the wire must not claim a blocking node when
the frontier emptied and none exists — the two are different things to a
reader. `reads/run.py` reads the row only on a BLOCKED run with a pinned route
(`BLOCKED_BY_IO = 1`, measured in `test_run_section.py`; `IO_BUDGET` moved by
one), resolves the module through the immutable pinned route, and refuses
`ORCHESTRATION_NODE_NOT_IN_ROUTE` (503) for a recorded attempt at a node the
route does not carry — rows this server wrote disagreeing with pins it wrote,
served as a fault rather than under a guessed module. The verdict's *text* is
not on the wire. It lives in an unaccepted attempt's body that passed
validation and not acceptance, and nothing serves un-accepted provider text.
The pinned key sets, the TypeScript mirror, the committed `schema.json` and
every fixture carrying a run body moved with it; the seven fixtures carry
`null`, since none is a BLOCKED run.

**The page.** The graph draws the blocking node `RUNNABLE · BLOCKED THE RUN`
in the run's own tone (CRITICAL), with the reason `answered Blocked · ended the
run`; its detail says the same and marks the attempt `BLOCKED · NOT ACCEPTED`
beside the verdict rather than instead of it; the run panel gains `Blocked by:
CP-5 answered Blocked on attempt 1 · <node>`, or, on a run the frontier
emptied, `no node's verdict — the frontier emptied with required work
unfinished`. Every one of those reads the wire's `blocked_by`; none is inferred
from an unaccepted attempt, which a node the run never reached holds too. In
passing, the graph's state word no longer says FRONTIER on an ended run — the
defect `093828f` fixed in the detail had been left in the state word.

**What this does not do.** The analysis page still lists CP-5 under "Nodes that
did not run": `AnalysisBody` carries no `blocked_by`, and the Model section
derives its body from it. Recorded in `CLAUDE.md`'s Phase 9 ledger with the
upgrade, which is the same field on that body. The stored verdict is served,
not re-verified, by the reader: what makes it trustworthy is that it was
written by the transition that had just re-derived it, under the row lock, in
the same transaction as the status — the same trust `runs.status` itself rests
on, and no less.

**Tests.** `test_a_validated_blocked_handoff_ends_the_run_blocked_without_retry`
and the crash-recovery test assert the row names CP-5's attempt on both paths;
`test_a_blocking_verdict_names_only_an_attempt_of_the_run_it_ends` is the store
guard; `test_a_node_the_gate_blocked_costs_no_call_and_no_charge` asserts no
row on the empty frontier;
`test_the_run_document_names_the_node_whose_blocked_verdict_ended_it` and
`test_a_run_the_frontier_emptied_names_no_blocking_node` are the document, with
the IO pinned; the two workspace unit tests cover the helpers and the section;
and the insufficient-evidence journey asserts the node, the detail, the attempt
row and the run panel through the production image on three engines.

## 2026-09-17 §69 — Phase 6 signed off, and what that signature is not

The owner signed `docs/FINAL_CHECK.md` on 17 September 2026. §62 had accepted
the phase with its gaps stated; this is the sign-off over the account of it,
after the work of 16 September closed four of the seven items, restated two that
were never work, and left one.

**What it asserts.** That the final check is an accurate account and that its
items are accepted as stated: a complete green `make check`; eleven authorised
live runs at `$7.75`, each recorded with its charges and generation ids,
including the failures; and one `complete` snapshot, run
`62308d4e-70b5-4793-abb0-7be62d2ceba6`, bound to build `30222a49`.

**What it does not.** It is not a qualification verdict. A verdict is a signed
document over exact evidence, bound to provider, set and build, recorded through
the route §65 built by an authenticated `ADMIN` whose identity the host derives.
`qualification_verdicts` is empty in every database, including the one holding
the complete snapshot. No build, model or pathway is QUALIFIED, and signing this
page did not make one so.

**One item stays open.** One pathway of eighteen is qualified. The other
seventeen each need an answer key authored from their own documents before their
run, and several need evidence this corpus does not hold — `CP-4` wants executed
debt documents, `CP-2D` a cash-flow pack. That is a corpus-and-answer-key
programme, not a run, and no amount of spending shortens it.

**The signature block is recorded, not derived.** The host vouches for nothing
in it: the identity is the owner's configured git identity, written down on
their instruction, and theirs to correct.

## 2026-09-17 §70 — The audit remediation's first wave: a read takes no lock, a tokenless API grants no role, and four boundaries answer in their own words

`docs/reviews/2026-09-17-gemini-audit-adversarial-review.md` re-verified a
third-party audit against this tree and promoted three findings to critical.
This entry records the six changes that answer them, and what each one gave up.
The plan is `docs/superpowers/plans/2026-09-17-audit-remediation.md`.

### 70.1 Section reads never take the case lock

`server/api/reads/reports.py::_read` took `lock_case` — `SELECT … FOR UPDATE`
on the case row — for the whole of a Report or Committee read, so every
governed write and every worker transition on that case waited behind a `GET`
for the length of its live proof: both blobs, the identity rebuild, the vendor
validator per node, and the re-anchoring of every recorded citation. A read is
not a governed write. It commits nothing, it appends no audit event, and no
reader of the store can tell the lock was ever held. It is removed, with the
second `standing_of` that existed only to re-read standing after waiting on it.

**What replaces it, stated precisely, because the first draft of this entry
overclaimed.** The served payload is digest-bound on *both* paths, by two
different comparisons in two modules: `reports.py` compares
`sha256(prove_revision(...))` against the revision row's `payload_sha256` for a
frozen revision, and `server/deliverable/receipts.py` makes the same comparison
for a filed one, which the frozen path never reaches. A mixed-snapshot
derivation can only produce bytes that *differ*, so the failure direction is
refusal, never a wrong document. The Committee publication envelope — state,
signers, freezer, filer — is covered by no digest at all; it is protected
instead by single-statement reads and fail-closed cross-checks, and no ordering
serves an internally inconsistent envelope. A filing landing after the
publication read serves `frozen` for a now-filed revision, which is stale by at
most the read's length and identical to the read having returned a moment
earlier.

**Accepted cost.** The audit-head comparison now spans snapshots, so *any*
governed write on the case committing mid-read — not only a freeze or a filing,
because `governed_write` appends to the chain unconditionally — makes the read
refuse `DELIVERABLE_PAYLOAD_INVALID` where it previously waited. The same
construct exists a second time on the filed path in `receipts.py`. This is
fail-closed and recoverable: the workspace offers an explicit reload, and a
re-read succeeds. A revocation can also now commit mid-read, so a caller whose
membership is revoked during the live proof is still served — which makes this
read consistent with `analysis.py`, `upload.py` and `run.py`, all of which read
standing once without a lock and always did.

`IO_BUDGET` falls by three round trips per served path, not two: `lock_case`
costs its isolation assertion as well as its `FOR UPDATE`, and the duplicate
standing read is the third. `{"report": 52, "committee": 63, "frozen": 57}`
becomes `{"report": 49, "committee": 60, "frozen": 54}`, measured against the
declared-I/O test rather than fitted to it.
`tests/test_postgres_races.py::test_a_report_read_never_blocks_a_governed_write_on_its_case`
proves it on two connections: while the read is inside its unit, a second
connection's `FOR UPDATE NOWAIT` on the case row succeeds. It failed
`[False] == [True]` against the code this entry replaces.

`read_filed_receipt`'s and `prove_revision`'s docstrings said the caller holds
the case lock. They now say the caller owns its own unit, that a write caller
holds the lock and a section read holds none, and that the head comparison is
therefore a check across snapshots. The first of those docstrings was
load-bearing: it was the only place saying what made that comparison sound.

### 70.2 A tokenless API believes no groups header — superseding §53.3

§53.3 said `actor_from_headers` believes `x-caos-role` only when the switch is
`1` and no edge token is set, *"otherwise the role comes from groups"*. That
"otherwise" included the case with no edge token and no switch, so a process
started without `CAOS_EDGE_TOKEN` derived a caller's global role from an
`x-forwarded-groups` request header with no opt-in at all. Any peer that passed
the loopback and Host checks could assert `caos-admins` and be ADMIN, and
`x-caos-user` is trusted verbatim in that mode, so the subject came free with
it. The documented deployment is an authenticating edge that sets both and a
private listener, and a remote peer is refused before identity — but the switch
that exists to be the opt-in protected only the third header, which is the
narrower one.

**The rule now.** With an edge token set, the role comes from groups, as it
always did, and the switch is never believed whatever it says. With no token,
the role comes from `x-caos-role` when the switch is `1`, and is READER
otherwise — never from groups. The token branch is first, so the switch cannot
win in edge mode. The local developer loop is unaffected: the dev proxy sets
the subject and role headers and never groups, and `.env.example` already
carried the switch.

**What survives, which this entry did not say.** The rule fixes the *role*. The
*subject* is still `x-caos-user` taken verbatim in tokenless mode -- it is
parsed as a UUID and believed. Writes are closed, because every governed
command refuses a global READER, but per-case standing resolves from that
subject, so a peer that passes the loopback and Host checks and knows a
member's UUID reads that member's cases: sections, the event stream, evidence
pages and the deliverables. That is read-only and it needs the host itself, not
the documented image. The plan's deferred table rejects a signed-assertion edge
on the grounds that "C3's one-line fix removes the only unrecorded hole"; it
removes the role hole, and this is the one the sentence overlooked. Recorded in
`CLAUDE.md`'s known gaps at the phase adversarial audit, which found it.

**What this is not.** No test in the tree asserts the new rule over HTTP. The
HTTP escalation test reads as though it does, and does not: under the switch it
passed identically before this change. Exactly one test fails if this change is
reverted, and it is a unit test on `actor_from_headers`. That is acceptable
because that function is the single funnel — it is the only producer of an
`Actor`, and the groups header is read for authority nowhere else — but the
guarantee rests on that structural fact, not on coverage.

Nine existing tests were rewritten, and a tenth in a second round. Four of them
had been hollowed out rather than broken: they still passed, for reasons their
names no longer described. Three suites' `caos-admins` row was the only
remaining proof that a global ADMIN without case standing still gets the
private 404 on the event stream, the analysis section and evidence pages; under
the new rule that row became a duplicate of the plain-stranger row, and each
was restored to assert its property again.

### 70.3 One outcome record per accepted node, less one that is still there

Every accepted node recorded its provider call's outcome three times: in the
executor immediately after the call, again in the frontier loop, and again
inside acceptance. The second was a knowing no-op that still cost a `COMMIT`
and took `cases` and `runs` row-exclusive — twice per accepted node, against
the lock every governed write on that case needs. It is deleted.

Nothing about recovery moves. The bill, the diagnostic and the single
`CALL_OUTCOME_RECORDED` event are committed by the executor before the loop
resumes; `replay_billed` reads exactly those rows; the lease is fenced inside
`_accept_artifact`; and `CALL_OUTCOME_LEGACY` reaches `_legacy_replay` more
readily than before, since the deleted call let that refusal escape ahead of
acceptance. The strongest statement is one of ordering: `_accept` commits the
bill before `_accept_artifact` is entered, so an unbilled accepted artifact is
impossible by construction rather than by a provider's good behaviour.

**Two remain, not one, and the heading says so now.** `server/store/runs.py`'s
`_accept` still records beside the executor's authoritative call. It is not
free -- it goes through `committed_unit`, `_locked_attempt` and `lock_run`, so
it costs a `COMMIT` and takes `cases` and `runs` row-exclusive, which is the
cost W1 complained of. It is kept because it is load-bearing: it is the
`CALL_OUTCOME_LEGACY` replay detector, and it is what makes the
bill-before-accept ordering this entry leans on true. So W1 is closed by one
deletion of three sites, not by reduction to one. Corrected at the phase
confidence review, which found the heading claiming more than the body.

**What is given up.** The loop no longer enforces that a returned call was
billed; each `Provider` owes it, and that obligation is now a docstring plus
its tests. For every implementation that ships it holds structurally -- but not
for the reason this entry first gave. It said `check_call` refuses a second
recorder, which is true and is *at-most-once*: it cannot make a provider bill
at all. What actually holds the obligation is `execute_handoff` calling
`record_outcome` unconditionally, ahead of every post-call refusal, on a path
that cannot return with a `None` charge. The conclusion stood; the mechanism
named did not support it. Corrected at the phase adversarial audit. The cost of a future implementation
forgetting is not a refusal: a provider that returns without billing and then
crashes before acceptance leaves no `call_outcomes` row, so neither
`replay_billed` nor `unexplained_charge` matches, and the node is re-attempted
and paid for a second time with nobody deciding to. The only upgrade that
closes that window is a record adjacent to the call; nothing inside the
acceptance unit can reach it.

### 70.4 A store fault is not drift, and not a parked run

Four boundaries let a raw error or an untyped exception past the typed-refusal
edge, or gave a distinct failure the wrong name.

`start_attempt` gains the `psycopg.Error` / `BaseException` pair every sibling
in its file already had. `apply_schema` stops labelling an inner store fault as
schema drift — but only for the two codes that mean the store could not answer.
Everything else a migration refuses, including a malformed row that its own
verification finds and raises from another module, is a drift finding and says
so, because §20a says schema and PostgreSQL failures carry only that code. The
worker prints an exception's class and its last frame's file and line instead
of the class alone, and the PDF child's exit status now reaches the refusal
path, so an interpreter that died on import is reported to the operator as such
rather than as a corrupt document. The extraction deadline is computed before
the child is spawned, so an already-expired deadline costs no interpreter
start.

The worker does **not** park a cancel that refuses a store fault. That was
prescribed in the plan and was wrong: `cancel_run` cannot raise a stale
terminal at all, so the reachable refusal was the transient one, and parking it
would turn a run that heals itself — released, the lease left to expire, the
run reclaimed, the cancel retried — into a stop an operator must requeue by
hand. It takes the back-off the worker already gives that class. `cancel_run`
refuses three classes and no others: a store fault, `LEASE_NOT_HELD` from its
lease fence, and `RUN_NOT_FOUND` for a run row that is not there.

Nothing any of these prints can carry document-derived text: a SQLSTATE class,
a refusal code, an exit status, a file and a line. The frame's filename is a
host path even for vendored code, which is compiled under a fixed map rather
than under any name a document or an admitter chose.

### 70.5 Every refusal code has a status

`server/api/app.py` looked up a refusal's HTTP status with a `400` default, so
75 of the 122 declared codes answered 400 by falling through rather than by
decision, and the next code added would have joined them silently. The table is
now total and the lookup is unguarded; a test compares its keys against the
live enum in both directions. No status moved: the 47 codes that had an entry
keep it, and the 75 added are 400, which is what they already answered.

This encodes today's behaviour rather than judging it. Several of the added
codes are store or bundle faults by nature, and whether they should answer 503
or 500 is a separate decision — one the table now makes answerable in one
place, with a test that fails the day the set drifts. Twenty-two of the 23
codes served 503 today are permanent rather than transient, and no
`Retry-After` is emitted anywhere.

A store outage while a reviewer signs a qualification verdict no longer answers
400. The duplicate-signature case keeps `VERDICT_BINDING_INVALID`; every other
driver error on that route is `STORE_UNAVAILABLE`, and the three reads that ran
outside the handler — the clock, the evidence lookup and the evidence record —
are inside it.

## 2026-09-17 §71 — The audit remediation's second wave: one citation rule, one query for a run's evidence, one token index

Wave 2 of `docs/superpowers/plans/2026-09-17-audit-remediation.md`, answering
the second critical finding of
`docs/reviews/2026-09-17-gemini-audit-adversarial-review.md` and two of its
warnings. **Every prompt identity in the system moves with 71.1.**

### 71.1 The citation-candidate mechanism is retired, and the prompt states one rule

`citation_candidates` kept the three longest anchorable lines of each page and
marked every other delivered line `citation_candidate: false`. The final check
then told the model two things at once: use only lines the host flagged, and
cite the lines that support the claims you wrote. On a filings page the three
longest lines are boilerplate, so for numeric evidence those sentences were
jointly unsatisfiable — the phase-6 confidence review measured 93 flagged lines
of 1,751 anchorable ones. Nothing enforced the flag: a model that ignored it
was accepted and a model that obeyed it was refused. The flag also rode inside
the evidence block that the tag rule tells the model is untrusted text, so a
document line reading `citation_candidate: true` rendered indistinguishably
from the host's own.

The function is deleted, not orphaned. `_context` loses its candidate
parameter and `build_handoff_prompt` is down to nine. `TokenIndex` and
`verify_citations` are untouched: the candidate filter was the mechanism, the
anchoring is the invariant.

**The prompt now states the citation rule once.** Before, three host-authored
statements disagreed about how much of a line to quote and where the quote had
to appear, and a fourth named the flag. The single rule asks for the complete
text of one evidence line, unique on its page, repeated verbatim in the body.

That is deliberately **stricter than the host enforces, and the prompt no
longer claims otherwise.** `verify_citations` accepts any whole-token run that
is unique on its page and lies within one reading region — a fragment of a
line, or a run spanning lines inside a region. **Two** enforced constraints the
prompt does not state: the quote must lie within one reading region; and a
citation may not be repeated, which `server/methodology/handoff.py`'s transport
check refuses as `HANDOFF_MALFORMED` before form is judged. This entry first
counted a third -- that ambiguity is judged over the whole page including
undelivered lines -- and that one the prompt *does* state, in the words "that
line must appear exactly once on its cited page". Corrected at the phase
confidence review. A third constraint, finer and real: uniqueness is of the
token run, not of the line, so a once-only line whose words also occur as a run
crossing a line break inside the same region is refused `CITATION_AMBIGUOUS`
although it satisfies every sentence the prompt states. The instruction makes no claim about strictness in either direction,
because both the equality it first claimed and the one-sided bound that
replaced it were false.

**Every host section now opens and closes with a tagged marker**, including the
gate module's final check, which previously carried none at all. The tag rule
also now describes the markers the code emits: it used to say markers "end in
the tag" when in every real marker the tag sits mid-line. The tag itself is
unchanged — `sha256(front_matter + sections)[:16]`, a digest over content the
analysed document is itself part of, which is what stops a document embedding a
marker bearing its own prompt's tag.

**Evidence is grouped.** One `source_id`/`page` header per group replaces three
metadata lines per delivered block. Per-line overhead falls from about 84 bytes
to about 2, plus about 57 bytes per page; a prompt's END markers add a fixed
~250. So the evidence section shrinks for every page with at least one line —
line *length* was never the variable, the old metadata being constant per block
— but a prompt whose entire delivered evidence is **four lines or fewer grows**,
by at most ~225 bytes at one line. No qualification set here is near that: the
crossover becomes reachable only when per-node evidence selection narrows a
delivery to a handful of lines, and the measurement is owed then, against the
delivery row. These figures are arithmetic from the format strings, not two
measured prompts.

**The accepted trade.** Paying the header once per page means two consecutive
document lines reading `source_id: …` and `page: …` are the nearest
header-shaped text for every line that follows, where per-line headers
contradicted a forgery immediately. It is fail-closed: a mis-paged citation
refuses `CITATION_NOT_LOCATED` and takes the whole handoff with it, so the cost
is a billed attempt burned, never a wrong artifact. Markers themselves cannot
be forged, because of the tag.

**Unmeasured.** No live run has answered this prompt. Whether a real model does
better under one rule than under four is unknown, and the eleven recorded
qualification snapshots are not comparable to anything taken from here on.

*Addendum, 18 September 2026.* The reconciliation `04dd605` recorded main's
`citation_candidates` as not ported and "flagged for separate review". The
review found it retired here by this entry and `12e57b4`, with
`test_evidence_is_grouped_by_source_page_with_one_header` guarding its absence,
so it stays retired and the Model read's `IO_BUDGET` does not return to main's
196. Bringing it back would need a dated decision overriding this one that first
answers the flag-forgery and unsatisfiable-rule findings above.

### 71.2 A run's delivered evidence is one query, and a short read refuses

Building any module's prompt read every delivered block one at a time — a
six-table join per block, under the case lock — so a pack of twenty thousand
lines cost twenty thousand round trips per node call. One statement now reads
them all, proving clause for clause what the per-block join proved: the block
belongs to a source the run pinned, through the pinned source-set version, and
the source is still live.

The count check is inside that statement rather than beside it, so the
comparison and the rows come from one snapshot instead of two under READ
COMMITTED. It refuses `EVIDENCE_NOT_AVAILABLE` unless the read returns exactly
the blocks the pin captured — including when it captures none, which is the
shortest short delivery there is and the case the first implementation let
through. A store fault on that path answers `STORE_UNAVAILABLE`, which is what
the delivery path already answered, rather than the evidence code the
single-block reader used.

`read_run_block` is **deleted**. It had no production caller left once the
delivery path stopped using it, and keeping it would have left a second,
independently maintained copy of a six-table join that must stay in step with
this one. Its tests were not deleted with it: they assert properties of the
join, which survived, so they were ported onto the batched reader — later
admission, the four identity comparisons, equal bytes after the pin, argument
validation before any SQL, owned-unit cleanup, and a case-binding test written
as what each run delivers rather than as a foreign block refused.

This closes the known-gaps clause that asked for "a batched block query when
the first large PDF pack measures the hold". It arrived without waiting for the
measurement. Two near-verbatim twins of this join remain, in the same module
and in `server/evidence/page.py`.

### 71.3 The deliverable reader shares one token index

Of the three readers that verify accepted artifacts, the one used by the report
and committee reads re-read the same source pages once per pinned node instead
of once per run. It now shares a `TokenIndex`, as the proof reader already did.
The index is per reader instance, not module-global: caching across runs would
be a correctness bug, and caching three store results does not turn a
re-derivation into a trust, because uniqueness, delivered-block membership and
the rectangles are all still computed per citation.

`IO_BUDGET` for those reads falls by six per path, measured. It is the second
move of that number in one plan — §70.1 removed the case lock from the same
reads — and the two are unrelated: the first dropped a lock and a duplicate
standing read, this one deduplicates page reads.

**A new cost, recorded rather than fixed.** The shared index holds tokens for
every cited page of every node for the whole payload, where each node's index
was previously collected when its proof returned. A wide route citing many
pages of a large credit agreement now holds them all at once, on an API request
path. The proof reader has shared this trade since it gained its own index.

**On liveness, which the implementer's account was silent about.** The reads
run at READ COMMITTED, so strictly the uncached version could have seen a
withdrawal committed between the first node and the third and refused, where
the cached one cannot. Three things bound it: the payload already reads the
pinned live sources once for the whole unit, so the liveness view was fixed at
the top of the read and the per-page recheck made the reader inconsistently
fail-closed rather than reliably so; freezing and withdrawal both take the case
lock through a governed write, so the governed path is serialised against
withdrawal; and these reads write nothing, so the worst case is one read
serving a payload whose source was withdrawn mid-read, with the next read
refusing. The net is a more consistent snapshot, not a weaker check.
## 2026-09-17 §72 — A BLOCKED run is answered by a successor, not by a resume

**Context.** §39 called an empty frontier with unfinished required work
*recoverably* blocked, and `CLAUDE.md`'s ledger carried the upgrade "not a
resume" beside it without saying what the recovery then was. Two readings were
possible, and the Completion Phase 7 adversarial audit got both: that a BLOCKED
run would one day be moved back to RUNNING, and that it never would. §61 settles
the first half for the case it covers -- a `CONDITIONAL` readiness verdict names
a source, or the prepared representation of one, that the effective-source set
does not carry, and is discharged only when that named source is supplied and
CP-0 is re-run. A run's source set is pinned (`run_inputs.source_version`,
invariant 1) and its route is pinned and digested (invariant 10). Supplying a
source makes a new source-set version. So the discharge cannot happen inside the
run that asked for it: a CAS back to RUNNING would reopen a run under pins that
cannot change, and the run would then either execute against evidence its own
pin does not name or refuse for the same reason it refused before.

**Decision (a) -- resume is withdrawn in favour of a link.** Nothing moves a
BLOCKED run to RUNNING, and nothing is planned to. That withdrawal is decided
here and holds from here. What records the link instead is
`runs.supersedes_run_id` (migration `0025_supersedes.sql`): nullable, never a
run's own id (`runs_never_supersede_self`), at most one successor per
predecessor by the partial unique index `runs_one_successor`, and written once
by the insert that makes the successor -- the trigger
`runs_supersedes_write_once` refuses every UPDATE that would change the column,
to another run, to null, or from null onto a run after the fact, because a link
written later would bypass the checks the insert's unit makes. `start_run` takes
`supersedes` and, inside the caller's unit under the case lock, selects the
target `FOR SHARE` so no transition moves it while the link is written; it
refuses `RUN_NOT_FOUND` for a run of another case -- the same code, status and
clearance an unknown run gets, so neither answer tells a caller the other run
exists -- `RUN_NOT_BLOCKED` (409) for any status but BLOCKED, and
`RUN_ALREADY_SUPERSEDED` (409) for the second successor of one predecessor,
mapped from the index's declared name (`ONE_SUCCESSOR_PER_RUN`) and never from
a driver message. `POST /api/v1/cases/{case_id}/runs` carries `supersedes` on
every request, null for an ordinary run -- stated, not defaulted, because every
v1 request field is required (`test_v1_command_models_are_closed_bounded_and_in_the_committed_schema`)
-- and the audit payload binds it beside the selection and the route digest.
`RunView.supersedes` and `RunView.superseded_by` serve both ends, read in one
row for every displayed run (`SUPERSEDES_IO = 1`; the Run section's
`IO_BUDGET` moved from 50 to 51, and a successor's `CREATE_RUN` costs one
statement more than an ordinary run, `SUCCESSOR_RUN_IO`). The run panel names
each end as a link to that run, and the create-run control offers `supersedes`
pre-filled with the displayed run when it ended BLOCKED and nothing has
answered it yet; the analyst may clear it.

**What the control does not know.** The brief asked the offer to be made only
when the case's current source-set version is newer than the run's pinned one.
The run document carries no such fact: a source-set version is minted only when
a run pins its input (`snapshot_in`), so a source admitted after the blocked
run makes no new version until a successor pins, so the comparison as the brief
worded it has nothing to read. It is **not built** rather than unbuildable: the
run read already counts the case's live sources per request, and each version row
stores its own member count, so "the live sources differ from the pinned set" is
one more statement at most. Dropped because a prefill is a convenience and the
control is correct without it, not because the fact is unreachable -- the
distinction matters, because "cannot" closes a question that "did not" leaves
open. The control offers the link on the run's status alone. The server checks nothing about the successor's source set either, for
the reason under "What this does not do" below.

The other half of what a reader needs is *which* source the verdict asked for,
and that was being dropped: `parse_t8` returns `why_now_or_blocker` for every
readiness row and `_readiness` kept only `(module_id, readiness)`.
`Projections.blockers` now carries that cell for each row the gate did not clear
-- CONDITIONAL or BLOCKED, the vendor's own two non-runnable statuses -- each
through `BoundaryText` at `MAX_BLOCKER_CHARS` (512) and refused
`HANDOFF_MALFORMED` past it, with no document text on the refusal (invariant 2).
`NodeView.gate_reason` is that cell on the node it was written about, null for
every node the gate cleared or never ruled on, and the node detail shows it as
the gate's own statement. `matrix.PROJECTION_FIELDS` gains `blockers`, so a
qualification key can assert which condition a gate stated.

The record format does not move. `Projections` is serialised into the canonical
record, so adding a field would ordinarily invalidate every stored record the way
§45.4's v2 invalidated v1 -- and this field is empty for every non-gate record
and for every gate record of a run that ran. `record_bytes` therefore omits
`blockers` when it has no rows and `_decoded_record` reads its absence back as
the empty tuple: one value, one spelling, so `record_bytes(decoded) == data`
still holds, and `blockers: []` written out explicitly is refused as the
non-canonical form rather than accepted as a second spelling.

**Decision (b) is not taken here.** Whether a QA `Restricted` may release CP-6 as
RESTRICTED is the owner's to decide and is recorded as owed. It is a different
question with a different discharge: the QA_GATE case ends a run BLOCKED with the
frontier emptied, no source is named and nothing a successor supplies changes the
verdict -- the discharge there is a human decision under unchanged pins. The
Repair Phase 2 ledger entry "Only a QA `Passed` releases CP-6" owns that case;
this entry's withdrawal covers a readiness verdict and nothing else.

**The link, though, is offered on a run's status alone.** This sentence said it
was offered for the readiness case alone, which the code has never done and which
the ledger delta beside it contradicted: `start_run` refuses any status but
BLOCKED and reads nothing else, and the Run section pre-fills the control for a
BLOCKED run with no successor yet. The host has no cheap fact to narrow on --
`blocked_by` is `null` for both the readiness-CONDITIONAL case and the QA_GATE
case, so telling them apart means reading the gate verdicts -- and a successor for
a QA-blocked run is an ordinary new run an analyst chose, which nothing here
should refuse. So: the *withdrawal of resume* is scoped to a readiness verdict;
the *link* is not, and is built for the readiness case rather than restricted to
it. Corrected by the Task 10.3 acceptance review, which read this sentence
against `RunSection.tsx` and the store.

**What this does not do.** A successor is an ordinary new run: it resolves and
pins its own route, pins its own input over the case's sources as they are then,
and pays for every node again. Nothing carries an accepted artifact across the
link, and nothing checks that the successor's source set actually contains the
source the predecessor's verdict named -- the host cannot read a model's prose as
a source identifier, and inventing a match would be the host asserting a
readiness ground of its own (invariant 4). The link says which run a run answers;
whether it answers it is the reader's judgement. `AnalysisBody` carries neither
field, as it carries no `blocked_by` (Phase 9's ledger entry owns that).

**Tests.** `test_a_conditional_row_projects_its_blocker_text_bounded` and
`test_a_blocker_cell_past_its_bound_refuses_with_no_document_text` are the
projection and its bound; `test_blockers_are_read_only_from_the_cp0_artifact` is
that it is read from the gate and nowhere else;
`test_an_empty_blocker_list_is_absent_from_the_record_and_read_back_as_empty`,
`test_a_record_carrying_blockers_writes_them_and_reads_them_back` and
`test_an_explicitly_empty_blocker_list_is_not_the_canonical_form` are the record
format; `test_a_blocked_run_names_the_source_its_conditional_row_asked_for` is
the document over a real blocked LITE run;
the link's own are `test_a_successor_run_links_a_blocked_run_of_its_case` (the
command, the column, the audit payload's binding, both run documents, and the
serial `RUN_ALREADY_SUPERSEDED`),
`test_a_successor_for_a_running_run_or_another_case_is_refused` (`RUN_NOT_BLOCKED`,
the private 404 as one body for a foreign and an unknown run, nothing inserted,
no receipt, and the refused request's key still usable) and
`test_two_successors_for_one_blocked_run_commit_one` (the race on two
connections, the index refusing the loser inside its own unit);
`test_a_runs_predecessor_is_written_once_and_is_never_itself` is the trigger
and the CHECK; `test_each_run_command_meets_its_declared_store_budget` measures
the successor's extra statement. The workspace's
`test_a_gate_condition_is_shown_beside_the_verdict_it_qualifies` names the gate
condition on the node, `test_the_run_panel_names_the_run_a_successor_replaces`
names both ends of the link in the run panel, and
`test_a_blocked_run_not_yet_answered_offers_supersedes_prefilled` is the offer.

## 2026-09-17 §73 — The audit remediation's third wave: one commit, one check, one parse, one serialiser, and 1,216 fewer lines of unreachable workspace

Wave 3 of `docs/superpowers/plans/2026-09-17-audit-remediation.md`, answering
six warnings of
`docs/reviews/2026-09-17-gemini-audit-adversarial-review.md`. Every task in
this wave removes a second copy of something rather than adding a mechanism,
and each entry below says what the single copy gave up.

### 73.1 Only the store package root commits a transaction

Eleven functions under `server/store/` each spelled the same four-arm block:
call the body, `conn.commit()`, convert `psycopg.Error` to `STORE_UNAVAILABLE`
with no text, and roll back on any other exception including cancellation.
Eleven copies of the rule that makes transactional pairing hold is eleven
chances for one of them to drift. They now call `committed_unit`, one context
manager in `server/store/__init__.py` with those same four arms.

Eleven and not the seventeen the plan asked for. The other six roll back
without committing: the same refusal shape wearing a different unit, and
folding them in would have made the manager mean two things. **After the
change no module under `server/store/` outside `__init__.py` calls `commit()`
at all**, which is what makes the claim mechanical rather than a count —
`test_only_the_store_package_root_commits_a_transaction` asserts it
recursively against a fourteen-file floor, and names the three legitimate
callers outside the package in its docstring so nobody widens the scope by
accident.

**Two arms were unpinned and now are not.** Nothing asserted that the commit
sits inside the `try`, so moving it below the guard passed every test while
making a failed commit raise raw driver text out of eleven money and audit
paths; and the rollback arm was asserted by transaction status rather than by
effect, so replacing it with a commit also passed. One test each, asserting by
effect. They could not be one test: at a commit-time fault PostgreSQL has
already aborted the transaction, so the rollback mutation is unobservable
there.

`server/store/work.py` gained `require_running`, which folds the run lock and
the spend fence together. That also changed `start_attempt`'s `RUN_NOT_FOUND`
path, which previously propagated with the transaction left open.

### 73.2 One ten-step check of an accepted artifact, and the sibling check stays

Three readers verified an accepted canonical artifact independently: the
orchestration proof, the deliverable payload, and the runtime's accepted read.
Ten steps each, in the same order, with the same refusal codes — and three
places for one of them to fall behind. `server/methodology/verification.py`
now holds `verify_accepted`, and the three are its call sites. Their genuine
differences survive as parameters rather than being normalised away: whether
citations are re-anchored against pinned evidence, which vendor authority is
consulted, and which step the caller stops at.

The refactor moved no assertion in any of the three readers' suites, which is
the strongest available evidence that behaviour did not move: the only test
file that changed is the new module's own.

**One reachable code movement, kept and recorded.** A dual fault — a blob that
will not read together with an attempt the store cannot rebuild — now answers
the record-mismatch code rather than the older one. Both are refusals, the
proof already ordered it that way, and nothing in the tree names the old order.

**One defence was dropped in the first draft and restored.** The runtime's
accepted read reached `SKILL.md` through `assemble_authority`, which as a side
effect verifies every manifest file of that module; the shared step reads the
one file. A reference file beside `SKILL.md`, tampered on disk under an
unchanged manifest with a warm digest cache, would then have gone unrefused on
the read that serves the frontier, the Run and Analysis documents and the
matrix — not for the module about to run, whose every delivered byte the prompt
still reads, but for an **upstream** module's siblings. It is not a hole in
invariant 4, because a consumer's call does not use an upstream module's
reference files. It was restored anyway, for a reason worth stating: with
`verify_authority=False` the digests come from the cache, so the call costs
exactly what the parent paid. The cheaper read was not cheaper.

The restored call sits after the shared steps rather than at its old position
before validation, so the record checks keep their precedence. The corner that
gives up: a tampered sibling together with a Markdown that no longer validates
answers the validator's code rather than `AUTHORITY_BYTES_MISMATCH`. A dual
fault, both arms fail-closed.

### 73.3 The readers take a row, not five fields

Six functions across those readers took `run_id`, `route_node_id`,
`attempt_id`, `artifact_sha256` and `record_sha256` as five positional
neighbours of the same type. `AcceptedRow` — frozen, slotted — is one
argument. Eight call sites pass every field by keyword, so the transposition
risk this shape carried is now structurally absent rather than absent on
inspection.

The suppression budget did not reach the plan's number and could not:
ruff's `max-args` ceiling here is five, keyword-only parameters count toward
it, and raising the ceiling is forbidden. Four `noqa: PLR0913` markers remain
on functions that carry a unit's handles, its row and its pairs.

The floor moved from `> 100` against exactly 101 files to `>= 80`, because
this same plan deletes files and an unrelated deletion would otherwise turn the
budget red. What the budget *counts* changed too, at integration; §73.8.

### 73.4 Identity is declared before the store, in one place

Nine route modules hand-parsed a path id, six enforced case visibility with
their own spelling of one rule, and five spelled the governed envelope — the
digest, the governed write, the receipt — inline. `server/api/deps.py` now holds one parse and
one visibility dependency; the six sites enforce one rule — live standing at or
above READER, refused `CASE_NOT_FOUND`, before any byte is served — and two
keep a folded query for I/O reasons.

**The known-gaps entry this looks like it closes is not closed.** "Identity
before the store rests on parameter order" asks for
`dependencies=[Depends(actor_from_request)]` on each decorator, which FastAPI
puts at the front of the list whatever the parameters say. This task did not do
that. It regularised the order and added a store-touching dependency that
cannot be ahead of the actor even if a route declared it first, because its own
signature resolves the actor before the connection — which makes the property
hold more robustly while still resting on signature order. All twenty-one
routes were enumerated individually against that claim. The upgrade clause
stands.

Four of the nine old parsers leaked the client's input onto the exception's
`__context__`. The single parse raises outside the `except`, so none does.

**One behaviour change.** `server/api/reads/run.py`'s ordering was irregular,
so regularising it means a malformed run id is now refused before standing on
that route. The answer carries no bit about whether the case exists, so it
discloses nothing; it is recorded because it is a change.

Every `GovernedAction` literal is byte-for-byte unchanged, so stored receipts
still replay.

### 73.5 One canonical JSON serialiser, and one file that must never use it

Fifteen sites serialised JSON for hashing. Seven now call `server/digest.py`'s
one helper with the four flags they already shared — `sort_keys`, compact
separators, `ensure_ascii=False`, `allow_nan=False`. The other seven differ for
reasons, and are left alone.

The eighth is the reason this entry names the file. `server/calculators/
cash_flow.py` is a **byte-pinned host extension**: `HOST_INTEGRITY_v1.json`
pins it at 13,785 bytes under a digest, and any edit refuses
`AUTHORITY_BYTES_MISMATCH`. Converting it broke the forecast extension, and the
repair was to revert the file, **not** to regenerate the manifest — the
manifest's own digest is pinned in `server/methodology/host_pin.py`, and
`server/engine/route.py` writes it into a frozen route predicate covered by
`route_digest`, so re-pinning would move every stored route pin carrying CP-CF.
A host extension is not refactorable in place. That is the cost of pinning it,
and it is the correct cost.

Thirteen golden digests were computed before any edit and did not move; nine
were reproduced from scratch in a bare interpreter holding no repository code.
Three of the pins are blind to the flag they guard because their fixtures are
all-ASCII; the forecast one matters, because a facility name can carry
non-ASCII into those bytes.

Four private cross-package imports were made public in passing, `_digest_of`
and `_reported_charge` among them.

### 73.6 The workspace loses 1,216 lines nothing could reach

A reachability walk from `src/main.tsx` over the static import graph found 76
reachable files and eight unreachable components — 992 lines — plus a helper
module and three wire modules reachable only through a barrel export no live
section imported from. All are deleted, with the test cases that existed only
to name them. `shortDigest` moved to its intended home in the design system.

`frontend/tests/unit/reachability.test.ts` is what stops the next orphan: it
walks the same graph and fails on a file under `src/` nothing reaches. It walks
`.tsx` only while the lint rule beside it walks `.ts` too.

Nine rows of `docs/feature-status.csv` still cite deleted files.

### 73.7 What the integration found that six green branches did not

Recorded because it is the argument for the gate rather than a defect in any
task. All six branches were independently green and all six overlapped work
committed on the shared branch while they ran. Git reported four conflicts. It
also merged **four breakages silently**, with no marker, each caught by lint or
types over the combination and by nothing else:

one module lost the driver import that another commit's new `except` clause
needed; two test files named a symbol that a rename had made public; and one
called a function with the five fields another task had replaced by a row. A
branch cannot see either of these, because each is a disagreement between two
commits that were never in the same tree until this merge.

### 73.8 The suppression budget counts positional width, by the owner's decision

Integrating the wave failed the argument-count budget, 53 markers against a
ceiling of 52 whose own docstring said never to raise it. The rise was real and
perverse. Two of the wave's suppressions sit on functions that each replaced
several copies of themselves — the shared verification reader of §73.2, and
the one governed envelope of §73.4, which five routes had been spelling inline
while a module-local helper served the rest. The copies were never suppressed,
so the budget never counted them: about 346 lines of duplication left the tree
and the number went up by one.

Raising it to 53 would have been a threshold moved to obtain a pass, which the
engineering contract forbids, so the decision went to the owner. What was
checked first, because a stale measurement is the rationalisation this rule
exists to refuse: every one of the 53 markers was parsed and none was stale,
and `governed` takes a connection plus seven keyword-only arguments against a
ceiling of five, so no permitted move clears it.

**The owner's decision was to change the unit.** Two candidates were measured
and rejected before the one adopted. Charging only suppressions that are *not*
shared — a suppressed function called from three or more other modules counting
as consolidation rather than width — **rises** here, 47 to 49, because
consolidating callers drains other helpers' caller counts and pushes three
pre-existing shared functions across the threshold; it is unstable under the
refactor it was meant to reward. And any unit defined over raw marker counts
rises by construction, for the reason above.

What is charged now is a function taking more than five **positional**
parameters. That is the defect the rule exists for: a caller can transpose two
same-typed neighbours silently, and cannot when the surplus is keyword-only —
the exact property §73.3's narrowing established about its eight call sites.
Clearing a charge by making parameters keyword-only is the fix rather than an
evasion, which is the property worth having: gaming this metric means repairing
the hazard.

Positional width is **22 at the wave's base and 22 after it**. The wave added
no new way to call anything wrongly.

**The criterion that chose between the three is worth more than the unit it
chose.** Two of the three were gameable in the direction of making the code
*worse*: the caller-count unit rewarded the consolidation it was built to
reward the opposite of, and a count of named parameters would have let a
six-argument function go from charged to clear by becoming `(a, b, *rest)`.
The surviving unit is the one where gaming it is the fix. A gate should be
chosen by asking what its cheapest evasion does to the code, and kept only if
the answer is "improves it".

**The same class of error cost this wave an environment, and is worth the
comparison.** `.gitignore` excluded `.venv*/` and `node_modules/`, both with a
trailing slash, which matches a *directory*. An integration worktree reaches
the interpreter and the packages through symlinks to the main checkout, and a
symlink is not a directory — so the moment those paths became links the ignore
stopped covering them, `git add -A` swept them into the tree, and the merge
wrote the tracked links over the real ones, each resolving to its own path.
Every pre-commit hook and the whole type gate run through them. The rule
described the shape it expected rather than the thing it meant to exclude,
which is what the suppression budget did when it counted annotations instead
of hazards. Both rules now carry the bare form beside the directory form, and
no tracked symlink remains in the tree.

Every suppression is still parsed, and a marker ruff would no longer raise
fails its own assertion, so the keyword rule cannot become a hiding place for a
stale one. Both arms were mutation-checked. The test's docstring carries the
old unit, its 52, and both rejected alternatives with their numbers, so the
next reader does not have to reconstruct any of this.

Two leaks of the counter were closed after the peer session named them, and
neither moves the number today. A method's receiver is not an argument its
caller passes, so `self` and `cls` are dropped as ruff drops them; the two
constructors carrying a marker were each over-charged by one and stay charged
either way. And `*args` is unbounded positional width that a count of named
parameters reads as none, so it is charged outright — latent today, and the
worse of the two, because it would have let a six-argument function go from
charged to clear by getting strictly worse.

**What the number hides is a finding of its own.** The 22 are not scattered:
eighteen are under `server/api/` — the command handlers and the section reads
— at six to nine positional parameters, and twenty-one of the twenty-two
declare no keyword-only parameter at all. The other four are the proof and
deliverable constructors, `store/runs.py`'s `_transition` and
`evidence/page.py`'s `_frame`. The layer has not partially adopted the fix and
run out of road; the pattern was never reached for. No task in this plan owns
that layer, so nothing here changes it — it is recorded for the phase audit.

## 2026-09-17 §74 — The audit remediation's fourth wave: an index, a seal checked once, an operator told the name, two shells and the residue

Wave 4 of `docs/superpowers/plans/2026-09-17-audit-remediation.md`, answering
the plan's remaining notes and one owner decision. Five tasks, each small; two
of them changed something load-bearing and are the reason this entry is longer
than its diff deserves.

### 74.1 The directory's membership join has an index (migration 0026)

`case_members`'s primary key leads with `case_id`, so the directory's join on
the caller's `user_id` was served by scanning every membership row in the
store. `0026_case_members_by_user` indexes `user_id`, partial on
`revoked_at IS NULL` because a revoked membership lists nothing, so the index
holds exactly the rows the directory reads.

**The number this migration does not carry is `0022`.** The plan reserved that
ordinal for this task, and the concurrent session landed `0024` and `0025` while
the wave was in flight. `0022` and `0023` are now permanent gaps: `apply_schema`
verifies an ordered immutable prefix, so a migration inserted below the applied
head would not verify on any database already past `0025`. They stay gaps rather
than being recycled, and a reader who notices should find the reason here rather
than a number that means something different from what its position implies.

The test asserts the plan reaches the index **and** that the condition is on
`user_id`, because the index name alone would hold for an index of that name on
any column. What it does not assert is a latency, and it asserts over a proxy
query rather than the real statement, which carries a subquery, a lateral join
and an `ORDER BY … LIMIT` under which the planner may legitimately drive from
`cases` instead. The index is right for the shape this read has at scale; that
the statement it was added for reaches it is not proven.

### 74.2 The evidence seal is checked once per statement, not once per row (migration 0027)

Admitting a document fired the immutability check of migration `0008` once for
every row inserted. Measured before deciding, which the task was allowed to stop
on: the store write for a 100,000-token document took **12.1 s**, six times the
threshold at which the work was worth doing. `0027` makes the check an
`AFTER INSERT … FOR EACH STATEMENT` trigger with a transition table, and both
evidence writers use `COPY`.

| | before | after |
|---|---|---|
| store write, 100k tokens | 12.1 s | 4.4 s |
| seal checks, 10k lines | 30,001 | 2 |

The call count was read from PostgreSQL's own function statistics rather than
inferred from elapsed time.

**The lock mode changed, and that is the part worth reading twice.** The trigger
takes `FOR NO KEY UPDATE` where `0008` took `FOR UPDATE`. An `AFTER` trigger runs
after its own statement's foreign-key check has already taken `FOR KEY SHARE` on
the same `sources` row, so asking for `FOR UPDATE` is a lock upgrade, and two
writers of one unsealed source deadlock instead of queueing — observed, before
the mode was changed, not predicted after.

The claim that nothing is let through was checked by enumerating every writer
and every lock on a `sources` row from the live schema, and measuring the
exclusion matrix rather than reading the documentation. Exactly four foreign
keys reference `sources`. The seal is excluded by **lock order** rather than by
mode: its own trigger is `BEFORE`, so its `FOR UPDATE` lands first. Withdrawal
updates a non-key column and so takes an implicit `FOR NO KEY UPDATE`, which
conflicts. The one exclusion given up is against a bare `FOR KEY SHARE`, which
only a referencing insert's own check takes, and the one path that could reach
it needs a committed seal that commits in the same transaction as the evidence.

**That property was guarded in one direction only, and now is not.** The new
concurrency tests prove the permissive direction, which any weaker lock passes
automatically; replacing the mode with `FOR KEY SHARE` left every other
assertion in the file standing. A test now holds an evidence statement open and
requires a withdrawal of that source to block. It fails under exactly that
weakening.

**Two costs, recorded rather than fixed.** The statement's rows are materialised
into a transition tuplestore that can spill past `work_mem`, a cost the row
trigger did not have, bounded per document by the admission token ceiling. And a
refusal now arrives after the statement's rows are written rather than before the
first, so a sealed source's bulk insert writes its rows and discards them where
it used to refuse at row one. Nothing on the admission path meets that, because
a document's seal commits in the transaction that writes its evidence.

*Upgrade:* a declared `work_mem` floor for the admission path, the day a document
large enough to spill is admitted; and nothing for the refusal ordering, which is
the price of checking once.

### 74.3 An operator is told which variable is missing

Three surfaces under-reported. The development doctor and `.env.example` did not
name every variable the worker and the edge read, so an operator learned a
variable existed by meeting its failure. The package verifier exited without
usage when run with no argument. And the worker reported an unset price as a
misconfiguration.

The worker now prints the typed code with the **name** of the variable nobody
set beside it, and never a value — `unset` can only ever hold the empty string or
the module's own constant. The verifier gained a standard-library argument
parser; it must stay standard-library only, which an AST test asserts and which
was confirmed by watching that test fail with a third-party import inserted.

Packages built from here archive the new verifier while older packages keep their
own. Neither direction changes a verdict: the verifier's own bytes are never read
into one, only its presence and its size bound, and both directions were measured
— an old archived verifier over a new package, and a base-era verifier against the
new host reader, both verifying.

**What the completeness test is not.** It names five variables and would not
catch a sixth. That is the shape the plan asked for and it should not be read as
a gate. What does hold structurally is the neighbouring assertion that no
variable's *value* is ever printed, which iterates the configuration sets
dynamically and so covers every name added to them, including a real secret.

### 74.4 Book and Admin are the shells the chrome suite already asserted

The owner's decision D2. Both sections are specified and neither ever mounted:
the section gate excludes them, so the surface never requests a document and the
unavailable branch returns without invoking its children. 1,216 lines of
components, helpers and wire modules are deleted, with the tests that existed
only to name them, and the ledger provider stops wrapping every section. The
implementation returns from git history the day either section is served.

**Two things were deliberately not deleted, and the reason is a rule about
gates.** `bind`/`release` in the authority machine, and the metric-passport
overlay, both lost their only production caller. Both are the subject of a test
pinned **by name** in the phase-exit gate, whose own docstring says the cheapest
way to green that assertion would be to re-excuse the name — a gate turned off
to make a gate pass. Deleting either is therefore a gate edit rather than a
cleanup, and both sites now say so in a comment, because the next reader is as
likely to delete them wrongly as to read the Book as served.

An accepted Phase 4 exit-evidence record cites one of the deleted tests under a
sentence claiming the dormant sections carry their fixes. It is **not** corrected,
on the precedent this repository already holds for `docs/feature-status.csv`: a
dated record whose evidence is edited later stops being a record of that date.
It is carried into the handoff instead.

### 74.5 Residue, and one duplication that is not one

Five small things: a catalog loader spelled twice, a dead wrapper module, a route
digest recomputed on a read that had already derived it, a lock that raised
without ending its transaction, and one route serialiser apparently written
twice.

**The last is not a duplication, and finding that out was the task.** There are
two byte forms — the digest's and the stored pin's — and they differ
deliberately in row shape, edge order and predicate handling. **Both are pinned**,
the stored one by every existing route row that must still read back. So only a
field list is shared; unifying the forms would be a record-format version with no
backfill, and was not taken unasked. Both forms were held unchanged by goldens
computed at the base commit before any edit, and re-verified independently across
every route the vendored catalog can resolve.

Coercing predicates in the shared helper turned two malformed shapes the stored
pin refuses into shapes it accepts. Two store-integrity tests named it, and it
was fixed before the commit rather than after the review.

The plan's instruction to import the catalog loader into a command module was
**unimplementable**: a test bans that module for every command module. The loader
lives beside the other vendor readers instead, which narrows the command module's
import graph rather than widening it.

`lock_run` now ends its transaction before raising, a change to a primitive with
a dozen callers. Every caller was walked: the refusal propagates from all of
them, the one that catches it re-raises, and the one that catches and continues
rolls back first regardless.

### 74.6 What the wave got wrong, and where

Three of the five briefs were wrong, and all three were mine. One named a
migration ordinal the tree had moved past. One prescribed an import a gate
forbids. One described two pinned byte forms as one serialiser. None reached the
tree: each was caught by an implementer doing the instruction as written and
letting the suite answer, which is the right order and worth saying plainly,
because the alternative — an implementer silently correcting a brief — leaves
nobody knowing the plan was wrong.

## 2026-09-17 §75 — A permanent fault answers 500; only a transient one says come back later

Owner decision **D3**, and the reason it is a decision entry rather than a line
in §70.5 is that **it was never put to the owner until the phase adversarial
audit found it had not been.** D1 and D2 both reached the owner and are recorded
(§71.1, §74.4). D3 lived in the plan's own deferred table, and the plan's
self-review counted warning W5 as covered by "T5/D3". A self-review that counts
an undecided question as covered is a gate that has stopped measuring. Put to
the owner on 17 September 2026; decided: split, with `Retry-After`.

### What was there

Twenty-four refusal codes answered 503, **none** answered 500, and
`Retry-After` appeared nowhere in `server/` or `frontend/src/`. Among the 503s
were `BLOB_DIGEST_MISMATCH`, `ARTIFACT_RECORD_MISMATCH`, `AUTHORITY_BYTES_MISMATCH`
and `HANDOFF_MALFORMED` — faults no retry can clear, telling a proxy to come
back and try again.

§70.5 made the status map total so that every code answered by decision rather
than by falling through, and deliberately moved nothing. This is the move.

### The classification, and why a near-total move is believed

**One transient, twenty-three permanent.** The rule is one question per code:
would retrying the identical request later plausibly succeed, with nobody doing
anything in between? A fault only an *operator* can repair is not transient —
the client retrying changes nothing.

A rule that moves twenty-three of twenty-four is either a real finding or a rule
applied without reading, and the two look identical in a diff. It was stopped
on and re-read, and it is believed because **three records written by other
hands for other purposes already said the same thing**:

- `CLEARS`, the operator-facing clearance text, says "An operator must …" for
  **eighteen** of the twenty-four and "Retry when the store answers" for
  **exactly one**. It is fifteen distinct sentences over those eighteen, not one
  rule stamped eighteen times, and it varies precisely where `_STATUS` was
  constant — had the two shared a model, all twenty-four would have read
  "retry".
- §71.3, written weeks earlier by a different author, already recorded that
  "twenty-two of the 23 codes served 503 today are permanent rather than
  transient". It went uncited by the task and was found by the review.

The finding underneath all three: **the 503 block was a blame judgement wearing
a time status.** Every code in it meant "this server's fault, not the caller's",
which is a true statement about *whose* problem it is and says nothing about
*when* it clears. 5xx was right; 503 was the wrong 5xx.

### Three adjacent entries, three justifications, one status

`ROUTE_IDENTITY_INVALID`, `ROUTE_EDGE_UNSUPPORTED` and `READINESS_INVALID` sat
together at 503 with three different explanations. The concurrent session that
added the middle one **self-reported it as misfiled before anyone found it**,
and described how: it wrote the justification for one answer and filed it under
the neighbour's. The neighbour was wrong too. All three are permanent, all three
now state the same time test, and `ROUTE_IDENTITY_INVALID` carries the history
in a comment because it is the entry the copying started from.

That is worth recording as a mechanism rather than an incident: an entry
justified by its neighbour inherits the neighbour's error and hides it, because
the second entry now looks corroborated.

### What this does not fix, stated so the entry does not overclaim

**The contract this establishes is narrower than "503 on the wire means come
back later."** D3 fixed blame wearing time; it leaves **time wearing blame**
untouched. Nine codes sit at 400 with retry-shaped clearances —
`PROVIDER_UNAVAILABLE` says "Retry when the provider answers", `READINESS_INCOMPLETE`
says "Retry the attempt", `INTERNAL_FAULT` says "Retry; an operator must
investigate if it persists" — and the new partition test cannot see them,
because it defines its universe as the codes already at 500 or 503.

`INTERNAL_FAULT` is the sharpest case: it is 400 in `_STATUS` while
`server/api/edge.py` answers 500 for it, so its only real wire status is
outside the guard entirely, and nothing asserts the disagreement.

So what holds is the narrower claim: **of the codes this table serves at 5xx,
503 means come back later and 500 does not.** The 400 side is a separate
question that has not been asked. *Upgrade:* put the retry-shaped 400s to the
owner as D3's second half, and reconcile `INTERNAL_FAULT`'s two statuses first,
because it is both the clearest instance and the one the guard cannot reach.

`HANDOFF_MODULE_UNSUPPORTED` was escalated as possibly-4xx and is not: its 4xx
twin already exists as `ROUTE_NOT_ENABLED`, 400, with a verbatim identical
clearance, raised when the caller pins the route. This one is raised after the
pin exists, on stored state the request cannot re-choose. `HANDOFF_BLOCKED`
remains a fair question and was left alone.

### Residuals

`RETRY_AFTER_SECONDS` is five seconds. It is the implementer's number, not the
owner's, and it is a floor for a restarting PostgreSQL rather than a forecast.
`/api/health` still answers 503 with no `Retry-After` — defensible, since it is
a probe rather than a refusal and never passes through the refusal body, but the
wire now reads inconsistently. `STORE_UNAVAILABLE` genuinely spans both classes,
because `committed_unit` maps every `psycopg.Error` to it including constraint
violations; it is kept transient on asymmetric cost, and the retry it invites is
answered from the idempotency receipt on a command that already committed.

## 2026-09-17 §76 — Book is served over accepted CP-CF projections; D2's Book half is superseded

§74.4 reduced Book and Admin to unavailable shells because neither had a
document to render. Completion Phase 12 Task 12.3 gives Book one.

`GET /api/v1/book` is portfolio-scoped — no case in its path — and its rows are
the credits the caller holds live standing on, read through `cases_for_member`
exactly as Directory reads them and bounded at four, which is `docs/IA_SPEC.md`
4.4's "two to four credits side by side". Each row's cells are values the
accepted CP-CF projection already carries, re-derived by the Model section's own
reader rather than by a second one: `accepted_forecast` is extracted from
`read_model`, live-source check included, because two readers of one accepted
pair are two answers to a question invariant 3 says the host owns once. The
host computes no figure and reaches no verdict here.

**The columns are declared in host code** — six of them, the five whose operands
are the period's own accepted driver row and the EBITDA margin
`cash_flow_forecast` derives from two of those. That is not a second authority
beside the bundle: `caos-forecast-v1` is this host's calculator and its shape is
the host's to state, so invariant 4 is untouched. The debt and cash roll-forward
and the leverage metrics over it are **not** declared, because their lineage
reaches every earlier period and a passport naming only the local drivers would
understate it — which is the failure that matters on a leverage figure. The
cost is that Book ships without `metrics.net_leverage`, the figure IA_SPEC names
as a facet, and the honest-ledger entry records it as a gap rather than an
omission.

**The passport is closed at exactly ten fields**, IA_SPEC 4.4's, pinned in
`tests/test_wire_contract.py`; an eleventh would be this host asserting
something the accepted record does not say. That closure has a cost of its own,
also recorded: every Book cell is a projection and none carries the `PROJECTED`
marker, because there is no field for one.

**The scenario is the record's own `case`.** The first implementation served the
literal `NOT_DECLARED` on the stated ground that `caos-forecast-v1` declares no
scenario. It declares one, under that name: `server/qualification/matrix.py`
already matches `ExpectedForecast.scenario` against `item["case"]`,
`MAX_FORECAST_CASES` caps it, and the same document renders it as
`BookPeriod.case` and as each table's heading. So a credit carrying BASE and
DOWNSIDE produced two tables whose every cell opened a passport saying neither —
the one field whose whole job is telling them apart. The section names it, and
`BookBasis.scenario` says `EVERY_ACCEPTED_CASE`, which is what the comparison
spans. Found by the Task 12.3 acceptance review, which read the calculator
rather than the comment above the constant.

Admin stays at its shell and D2's Admin half stands. Book's `bind`/`release`
and the metric-passport overlay, which §74.4's ledger entry kept because
deleting a pinned gate's subject is a gate edit, now have their production
caller back; that entry is struck by the commit that gives them one.

## 2026-09-17 §77 — A per-section bound on an upstream handoff, the line group, and the closed element set

Three behaviour changes landed in Completion Phase 12's wave with no entry of
their own. The Phase 12 confidence review asked for them, and it is right that
a new refusal code and a new host policy bound over an accepted, immutable
artifact belong in the binding record rather than only in a code comment and a
struck ledger entry.

### 77.1 An upstream handoff is bounded at 32,768 bytes, and the bound answers after identity

`server/methodology/invocation.py` declares `MAX_UPSTREAM_HANDOFF_BYTES` and
refuses `UPSTREAM_SECTION_OVER_CEILING` when an accepted upstream's Markdown
exceeds it, in the prompt builder — so before any attempt, reservation or call.
Until now `MAX_REQUEST_BYTES` refused the whole request and could never say
*which* part was large.

The number is arithmetic, not a measurement of any handoff, and the arithmetic
has been corrected once. As first written it summed **raw** lengths and
compared them against `MAX_REQUEST_BYTES` — which bounds
`len(json.dumps(request).encode())` with `ensure_ascii=True`, so every
non-ASCII character costs six bytes and every quote and newline two, and the
vendored authority is full of em-dashes, section signs and curly quotes. The
test could therefore have passed while the real encoded request was over the
ceiling. Found by the Completion Phase 12 adversarial audit.

Measured through `provider.encode_request` instead, over every node of every
profile with the authority files' real bytes and the fixed host sections
included, the worst case is **CP-3 at 711,482 encoded bytes against the
1,048,576 ceiling — 32% of it left** for evidence. The raw-byte version named
CP-5, which was an artefact of the unit: CP-5 carries the most upstreams, CP-3
the heavier authority once escaping is paid. What the figure still excludes is
the citation register, which is explicitly unbounded, and the evidence section
itself, which is the room the assertion exists to prove is left.

It is a ceiling chosen so that a wide route cannot be refused wholesale for a
reason nobody can locate, not a figure any real handoff has approached — no
FULL module has ever produced one, and the only measurement in the tree is a
448,826-byte CP-0 *request* carrying no upstream at all. Against that, the host
asks for, accepts, validates, bills and stores a handoff up to `MAX_FILE_BYTES`
(26,214,400) and refuses to *use* one over 32,768, which is the asymmetry the
costs below describe.

**The bound answers after the digest comparison, not before it.** The size
check sits below `sha256(data) != ref.sha256` in `_utf8`'s caller, because the
host owns identity (invariant 3) and a host policy bound does not get to answer
ahead of it: bytes that are not the artifact they claim to be are refused as
that, not as too large.

**Three costs, recorded here because the ledger entry the bound closed did not
state them.** Nothing bounds a handoff at *acceptance* — `MAX_FILE_BYTES` is
26,214,400 — so the host will accept a 40 KiB handoff, bill it, and discover at
the *consumer's* prompt that it cannot use it, which lands the refusal on the
innocent node. The discharge is a new run, which calls the same model with the
same prompt and may reproduce the same size. And the operator meets a run
parked `STOPPED` whose stop code no surface renders, so the two entries compose
into "the run stopped and nothing says why".

### 77.2 A line past the group width is split, and the packing is re-derived in one direction

`SYSTEM_SPEC.md` §5 asks for one block per line while small and a bounded line
group once not. The splitting half is built: `GROUP_WIDTH` is `BoundaryText`'s
own `DEFAULT_LIMIT`, `ingest.line_groups` cuts a line at it, and
`verify_citations` requires every block a line was split into to have been
delivered. Before it, a line past 4,096 characters refused the whole pack, so
one wide table row in a text export meant no document carrying it could be
admitted.

The width is not a free parameter: anything narrower would re-number documents
already admitted under this one, whose `source_blocks` rows are immutable and
whose stored citations name the ids they were given. A cut falls wherever the
width falls, inside a word if that is where it falls, because cutting at a
token boundary would make the block count depend on the tokens and force
anchoring to read every token's text back to learn it.

`citations._line_blocks` re-derives the packing rather than storing a version,
and does so **in one direction only**: splitting writes more blocks than lines,
so only a source with more is repacked and checked against its stored count,
while one with fewer keeps the one-block-a-line reading it was admitted under.
That asymmetry is load-bearing, not tidiness — the two tests that demonstrate
`CITATION_NOT_DELIVERED` at all narrow a delivery by deleting a stored block
with the seal disabled, and reading that state as a disagreement about the rule
would answer about the host's own derivation where the honest answer is about
the citation, making the refusal unreachable in the tree.

### 77.3 The deliverable renders a closed element set, and everything else reaches the page as itself

Task 12.4 replaced `<pre>{escape(markdown)}</pre>` with a renderer over the
twelve prose constructs `ELEMENTS` names, so a register reads as a table. The
contract is that a construct outside the set has exactly two outcomes: it
reaches the page as the characters the model wrote, or the block refuses
`DELIVERABLE_MARKDOWN_UNSUPPORTED` because no faithful rendering of it exists.

**There is no third outcome, and there briefly was.** A line-leading HTML
comment was consumed and emitted nothing, and code-span contents and
out-of-order emphasis each dropped characters. A signer's `payload_sha256`
binds the record's bytes and this render is the only reading of them a
committee sees, so a construct that vanishes is text bound and unseen — the
invariant 5 shape read from the other side. Corrected at the Phase 12
confidence review, together with the gate that could not see it: a tag census
measures what the page *emits*, and a deleted construct emits no tag.

Consequence recorded when the renderer moved: `renderer_sha256` is stored on a
filing and compared against the renderer of the day a package is built, so a
revision filed before a renderer change cannot be packaged verifiably again.
Unreachable while no route serves a package, and owned by its own ledger entry.


## 2026-09-18 §78 — Two declared quote normalisations, tried only after the exact search finds nothing

Completion Phase 10 Task 10.5. `docs/COMPLETION_PLAN.md`'s Phase 10 exit check
asks that "a letter-spaced heading and a quote ending in a full stop anchor to
the rectangle a reader sees". Both are refused today, and both for a reason the
host created rather than one the document did: a quote is split on whitespace
and every word must equal a token, so a module that ends its sentence with a
full stop has quoted a word the page does not carry; and pdfminer inserts a
virtual word break between glyphs tracked past `word_margin` (§44.5), so a
heading tracked for display comes back one token per letter and the word cannot
be quoted as itself.

**The order between the two searches is the whole of the safety, and it is what
makes this a widening rather than a change.** The exact search runs first and is
untouched. A normalised search runs only where the exact one found *nothing*, so:

- every quote that anchored before this existed anchors to the same rectangles,
  and every stored record re-verifies — the proof, the deliverable and the
  runtime all re-anchor and none of them moves;
- a normalisation can never resolve an ambiguity, because an ambiguous exact
  match refuses before the second pass is reached;
- ambiguity is counted over the whole page in the normalised pass too, on the
  same rule, so two places a normalised quote could be is a refusal and not a
  choice.

**The two rules.** `EDGE_PUNCTUATION` may differ between the quote's *first and
last* word and its token — a module writing prose ends a sentence with a full
stop and wraps a quotation in quotation marks, which is the same trade the
handoff body check already took for `_QUOTATION`. An interior word must still
equal its token: forgiving punctuation there would let one quote stand for two
different sentences of the page. `_joined_tracking` joins each maximal run of
**single-character** tokens on one line of one region into the word a reader
sees, with the union of their rectangles.

**Why single characters is the axis and not a convenience.**
`test_widely_spaced_glyphs_refuse_the_joined_quote` holds that `Alpha` and
`Beta` kerned apart must not answer a quote of `AlphaBeta`, because that text is
on no rendered page. Those are tokens of five and four characters, so the
joining rule cannot reach them, and
`test_two_widely_spaced_words_still_refuse_their_concatenation` pins that in the
new rule's own file rather than trusting the old test to notice.

**Scoped to the extractor whose rule split the glyphs.** `TRACKING_EXTRACTORS`
is `caos.pdfminer` alone. In a plain-text document a single-character token is a
single-character *word*, and joining those would anchor a concatenation the file
does not contain. The extractor is read from `source_extractions` in the same
round trip as the document digest, so no section's declared `IO_BUDGET` moves;
a source with no extraction row, or an identity this build cannot parse, gets
the exact search alone — that table's own "no row means UNKNOWN" rule, read
fail-closed.

**Not versioned in the extractor identity, which is what O19 proposed.** The
identity records how *tokens* were produced, and these rules change no token: a
bump would force every source in every database to be re-admitted for a change
that did not alter a single extraction, and `apply_schema`-style verification
would then refuse rows that are entirely correct. The version is declared as
`NORMALISATION_VERSION` beside the rules it names, which is the thing a reader
asking "which rule anchored this quote" can actually be pointed at. O19's
repair clause is corrected rather than followed.

**What it does not claim.** Eleven authorized live runs produced no
`CITATION_NOT_LOCATED` from either cause — the one real typography refusal in
the record was the quotation-mark case, which `_QUOTATION` closed in a different
check. So these two rules are the plan's named cases and not a caller's measured
demand, which is the condition the Phase 2 ledger entry set. That is recorded in
the ledger rather than smoothed over, together with the residual the joining
rule buys: a genuine sequence of single-letter words is indistinguishable from
a tracked word, and a quote of their concatenation anchors over them.


## 2026-09-18 §79 — A worker says what it is doing; a stalled queue is not the API's unreadiness

Completion Phase 13.3, the readiness half. The ledger entry: the API's
`/api/health` probes the store, bundle and blob root it uses, and
`server/engine/worker.py` serves no listener — so a worker that exited
`PROVIDER_NOT_CONFIGURED` or is backing off on store faults is visible in its
exit code and its logs and nowhere else, while a queued run simply waits.

**No listener.** A process that already talks to PostgreSQL every poll does not
need a second protocol to say it is alive. Migration `0028` adds
`worker_heartbeats`, one row per worker, upserted: `(worker_id, beat_at, state,
consecutive_faults)`.

**The one deliberately mutable row in this store, and it says so.** Every other
table here is immutable by trigger because it carries a governed fact somebody
may later be held to. A beat is an observation with a shelf life of seconds,
and keeping each one would grow the table by a row per worker per poll forever
— the shape `command_requests` already carries a known-gaps entry for. So the
table is the size of the fleet rather than of the uptime, and no trigger
defends it. It also grants nothing: the lease in `run_work` is what fences a
run, and a worker that lies here still cannot write a run it does not hold.

**Three states, closed in the store.** `POLLING`, `WORKING`, `BACKOFF`, as a
`CHECK` rather than free text, so an operator alerting on `BACKOFF` can trust
that nothing else writes a different word meaning the same thing. `WORKING` is
said *before* the run is driven, because driving is the part that takes
minutes: "went quiet while working" is a different thing to a person than "went
quiet while idle". `BACKOFF` is said at the point the fault is handled and
before the connection is dropped — the first draft said it at the *next* poll,
and a worker looping claim-fault-claim then read `WORKING` for as long as it
kept failing, which is the exact signal the beat exists to carry.

**Saying so never stops the work.** `_beat` swallows a store fault and rolls
back. A heartbeat is for a person, not a fence; what answers a failing store is
the loop's own fault handling, by trying to claim a run, and a store that is
down cannot record that it is down — the staleness of the last beat says it
instead.

**A stalled queue does not make the API unready, and this is the load-bearing
decision.** `HealthDocument` gains `workers`, reported beside the other three
and deliberately **not** folded into `status`: the API is not the worker, and a
surface that reported itself unready because a queue was stalled would take
itself down for a fault it does not have. A load balancer reads `status`; an
operator alerts on `workers`. `WORKERS_ABSENT` (nothing has ever beaten, so a
queued run will wait), `WORKERS_STALE` (a worker beat and stopped — the row
names which), `WORKERS_BACKING_OFF` (every fresh worker is failing to reach the
store). A fresh worker driving a long run is `OK`, because its run's liveness is
the lease every fenced write renews, and a second clock on one question is how
two answers start disagreeing.

**No compose healthcheck, and the reason is not oversight.** The ledger entry
also asked for one on `compose.smoke.yaml`'s worker. That service runs
`journey.worker`, a test double; a healthcheck there would measure the double
and not the product, and the real worker is not in compose at all. It is owed
the day `server/engine/worker.py` itself runs in a compose stack.


## 2026-09-18 §80 — A frontier pass runs its independent nodes at once, on threads, opt-in

Completion Phase 13.1. `docs/REBUILD_PLAN.md` Phase 4 and `SYSTEM_SPEC.md` §4
both write the loop as `await gather(*(run_node(n) for n in ready))`, and the
ledger entry says "the loop's shape does not change, only the `for` becomes a
`gather`". Two of those three claims turn out to be wrong, and this entry is
what they are replaced by.

**Threads, not `asyncio`.** What a wide frontier waits on is a provider call,
and both that socket and psycopg's release the interpreter lock while they
block, so a `ThreadPoolExecutor` over the batch buys the whole of the overlap.
A `gather` buys the same overlap at the price of recolouring 152 store
functions and all 48 of their server-side callers, plus the 78 test modules
that drive them — a change whose blast radius is the entire store for a
latency win the stdlib already gives. O23's "async store" is therefore
**declined** rather than deferred: it is not what this exit check needs. What
would need it is an async *API* holding unpooled connections, which is a
different problem with its own entry.

**The loop's shape does change, because the frontier is not a safe batch.**
`frontier` offers every node whose *blocking* inputs are met, and a soft edge
does not block — so it can offer a node together with one of its own OPTIONAL
or ADVISORY upstreams. `execute_handoff` binds an attempt to the upstream
accepted when its prompt was built and refuses when another of its inputs is
accepted during the call, so running that pair together buys a billed attempt
that is then thrown away: money spent with nobody choosing to spend it.
`route.independent_batch` is the rule — greedy in route order over the
transitive closure of **every** edge type, dropping any node that reaches or is
reached by one already chosen. Reading only the blocking edges would call the
one dangerous pair independent, which is the single wrong answer available.

**Invariant 10 is untouched.** The batch is a pure function of the pinned route
and the frontier, and the frontier is recomputed from the store every pass, so
the same pins choose the same nodes in the same order. What changes is when
they run, never which. A node left out of a batch is not deferred or queued: it
is simply in the next pass's frontier.

**It shipped not reaching production, and the confidence review caught it.**
`module_execution` set `per_node`, and `work_once` then built a *fresh*
`Execution` listing the four fields that line happened to know about --
dropping the fifth. Nothing failed: a dropped field is not a type error, and
the run still completes, one node at a time. So the concurrent pass was built,
tested, documented and never reached a worker. It is fixed by `replace`, which
carries every field including one added tomorrow, and the guard is an assertion
on what the runtime is actually *handed*
(`test_the_worker_hands_the_runtime_a_concurrent_pass_and_a_stoppable_one`,
watched failing with the bug reintroduced). The same fix wraps each per-node
provider in `_Stoppable`, which the first version also missed: a SIGTERM would
have stopped the sequential loop between nodes and not a concurrent one.

**Opt-in, through one factory.** `Execution.per_node` returns a store
connection *and* a provider bound to it, because neither is any use alone — a
node's pre-call unit opens a transaction under the case lock, and
`ModuleProvider` reads the store to build its prompt. One field rather than two
so it cannot be half-configured. `None` — every direct caller, the harness and
the suite — keeps the loop exactly sequential, which matters because those
callers drive a run on a connection they own and hold open around it. The
worker supplies it. A batch of one opens no connection and starts no thread,
which is every LITE route this build enables.

**The lease is shared across those connections on purpose.** It fences the
*run*, and every write rechecks the token it was taken under, so two nodes of
one run writing under one lease is the claim working rather than a hole in it.

**Two nodes of one run cannot deadlock on the locks, and the reason is
structural rather than a convention anyone has to keep.** `lock_run` takes the
owner case's lock and *then* the run's, inside itself, so every path in this
tree acquires them in that order and no cycle can form -- a hazard that would
otherwise be invisible until a wide route hung in production, because a
deadlock needs two writers and until now there was one. It is also why the
concurrency is worth having: the locked stretches are store reads measured in
milliseconds and they serialise on the case, while `require_idle` holds the
provider call *outside* any transaction, so what overlaps is the part that
takes seconds.

**Every node is awaited even after one fails.** A call already in flight will
be billed whatever the loop decides, so abandoning its result would pay for an
answer nobody reads — the same reasoning the worker applies to SIGTERM. The
first failure is then re-raised, or `False` returned for a validated Blocked
handoff.

**What is proven and what is not.** Proven offline, on `RELATIVE_VALUE` —
the one enabled route with a wide frontier, which opens 1, then 2, then 4, then
2 nodes — by asserting that two calls' intervals *intersect*, which is the
property itself rather than a wall clock that measures the machine as much as
the loop. Not proven live: no wide route has ever run against a real provider,
and the routes that have are single-node at every pass, so production behaviour
for them is unchanged. This is **not** 13.2: one worker still claims one run,
and the I6 residual — a stale lease holder paying once — is untouched and still
what a second worker must answer first.

## 2026-09-18 §81 — No `ultrathink` and no `max`, for any model; `xhigh` is the ceiling, `high` for Fable 5.1

The owner, 18 September 2026: "No more use of ultrathink and Max reasoning for
any model, cap is xhigh." This overrides every earlier routing record that
asks for either — the goal prompts, the complementary plans, the task briefs,
`docs/AGENT_PROMPTS.md` and the review routing of 17 September — without
editing them, because each is a dated record of what was asked then.

- **Dispatch.** No implementer, reviewer or detector prompt contains
  `ultrathink`, and no dispatch sets effort `max`. `xhigh` is the most any
  model is given.
- **Fable 5.1 is capped lower, at `high`** — the owner, the same day: "Cap
  Fable 5.1 to high". The one Fable pin, `.claude/agents/final-phases-reviewer.md`,
  moves from `xhigh` to `high`.
- **The three Opus review definitions** under `.claude/agents/` already
  pinned `xhigh`; they no longer tell a review turn to open with `ultrathink`.
- **What ran before this entry keeps its recorded setting.** Three
  implementers of the completion remainder (slices A, C and D) were launched
  earlier the same day with `ultrathink` in their prompts and were not
  restarted; their reports are evidence about the tree, and the setting is
  recorded against them rather than re-run.

## 2026-09-18 §82 — A run states whether it carries the model extension

`CreateRun` gains a required `model_extension: StrictBool`. `create_run` passes
it to `resolve_route` as `RouteExtensions(model_extension=...)`, so CP-CF, its
synthesised REQUIRED edges and its `host_manifest_sha256` predicate are part of
the resolved route that `route_digest` covers and `server/store/routes.py`
pins. It is a route-*selection* input (invariant 10), carried by the node list,
edges and predicate rather than by a stored column, so no migration. Required
rather than defaulted because every v1 request field is (a missing key is a
malformed body), so the workspace's Create run form sends `false`; the
extension is API-only for now. A pathway missing any of CP-CF's `MODEL_OWNERS`
refuses it `ROUTE_EXTENSION_OWNER_MISSING` (400) before anything commits — every
LITE pathway does, and `FULL_CREDIT_32/RELATIVE_VALUE` is the one enabled
pathway that accepts it. A request made before this change, replayed as it was, carries no
`model_extension` and is refused `400 REQUEST_INVALID` before any digest is
taken; a client that adds the field under a receipt's old key digests
differently and is refused `IDEMPOTENCY_KEY_REUSED`
(`test_the_model_extension_is_stated_on_every_request` holds both). The Book
passport's `evidence_date` is renamed `reporting_period`, because it is the
analyst's declared period and never a date the host derived.

## 2026-09-18 §83 — Report is served without a revision

`GET /api/v1/cases/{case}/report` no longer requires `revision`. Named, it is
served exactly as before. Unnamed, it answers the run's head revision, or, when
the run has none, the accepted artifacts a first save would carry, with
`SAVE_REVISION` available and judged by the same `canonical_payload`
derivation the save makes — refused with that derivation's own code when it
cannot be made — and sign, freeze and file refused `DELIVERABLE_NOT_FOUND`. The
first save's success is what sets `?revision`, which is the filing chain's only
front door in the workspace. `ReportBody.revision_id` and `payload_sha256` are
nullable for that one state; `CommitteeBody` redeclares both required, and
Committee still needs a named frozen revision. On a named revision that is not
the head, `SAVE_REVISION` is refused `COMMAND_EXPECTATION_STALE`, the code its
commit answers; the head rides the revision's own statement at no round trip.
`IO_BUDGET["unsaved"] = 42`, measured on the LITE route and asserted with `==`.

## 2026-09-18 §84 — Two refusal codes and migration `0029`

- **`EVIDENCE_PACKING_MISMATCH`, 500, permanent.** Raised by
  `citations._line_blocks` when the host's packing rule no longer reproduces a
  source's stored block count. It replaces `EVIDENCE_NOT_AVAILABLE` there,
  whose clearance ("pin a live source") the caller could not discharge; its own
  names the operator's act, re-admitting the source under this build. Like the
  code it replaces it is not in `outcomes._NOT_AN_EXPLANATION`, so behaviour at
  a billed attempt is unchanged.
- **`DELIVERABLE_ALREADY_SIGNED`, 409.** Migration `0029` adds the named
  constraint `one_opinion_per_signer UNIQUE (case_id, revision_id, signed_by)`;
  `sign_opinion_in` inserts `ON CONFLICT ON CONSTRAINT ... DO NOTHING` and
  refuses when no row was written, leaving the transaction usable. A store that
  already holds a doubled signature refuses the migration `STORE_SCHEMA_DRIFT`
  before the DDL, in the pattern `0017` set, and deletes nothing: each row is
  evidence an `OPINION_SIGNED` audit event names. `0029` is the 27th entry of
  the ordered prefix because of the `0022`/`0023` gaps.
- **The two filing digest checks stay.** The Completion Phase 12 audit called
  them unreachable and proposed deleting them. They are unreachable through this
  code and reachable through a row altered outside it, so they are kept as
  tamper evidence, each with a test that gives it that cause.

## 2026-09-18 §85 — The owner's model matrix routes every dispatch

The owner, 18 September 2026, supplied a model-and-effort matrix and asked that
it govern all work. It supersedes the 17 September split (Sonnet detects, Opus
implements and reviews) and sits inside §81's caps.

| Model | Effort | Role |
|---|---|---|
| Sonnet 5 | `low` | configs, pre-commit rules, docstrings, regex, simple fixtures |
| Sonnet 5 | `medium` | routine endpoints, UI and wire integration, bug fixes, PR drafting |
| Sonnet 5 | `xhigh` | localized complex refactors and transformations |
| Opus 5 | `medium` | critical-path endpoints, deterministic calculation, strict diff size |
| Opus 5 | `high` | races, state transitions, spend reconciliation, row locking |
| Opus 5 | `xhigh` | adversarial audits, pre-merge security review, race verification |
| Fable 5.1 | `low`/`medium` | long-horizon autonomous passes, phased plan execution |
| Fable 5.1 | `high` | architecture, governance, end-of-phase reviews |

In this repository: the phase confidence review moves to Fable 5.1 at `high`
(`.claude/agents/phase-confidence-reviewer.md`), so a phase's two gates are read
by two models; the phase adversarial audit and task acceptance stay on Opus 5 at
`xhigh`; the final all-phases review stays on Fable 5.1 at `high`. Work already
dispatched keeps its recorded model.

## 2026-09-18 §86 — Fable 5.1 audits adversarially; Opus 5 reviews for confidence

The owner, amending §85 the same day: "Switch fable does adversarial review and
opus does confidence review." The phase adversarial audit
(`.claude/agents/phase-adversarial-auditor.md`) runs on Fable 5.1 at `high`,
Fable's ceiling; the phase confidence review
(`.claude/agents/phase-confidence-reviewer.md`) runs on Opus 5 at `xhigh`. This
overrides §85's rows that put end-of-phase reviews on Fable and adversarial
audits on Opus, for the two phase gates. Task acceptance stays on Opus 5 at
`xhigh`, and the final all-phases review stays on Fable 5.1 at `high`.

## 2026-09-18 §87 — One status per code, identity on every route, the extension offered where it succeeds

- **`INTERNAL_FAULT` is 500 and permanent at every layer.** It was 400 in the
  app's `_STATUS` and 500 at the edge guard, so its status depended on which
  layer caught it. The guard now declares its statuses once, `EDGE_STATUS`,
  asserted equal to the app's. §75's partition test covers the whole
  `RefusalCode` enum. The eight 400s whose clearance says retry are **named,
  not decided**, as `RETRY_SHAPED_400_PENDING_OWNER`: that is the owner's half
  of D3.
- **`RESERVATION_BELOW_REQUEST`, 500, permanent.** `canonical._within_reservation`
  no longer borrows `CONTEXT_OVER_CEILING`, whose clearance ("deliver less
  context") was false there. It is raised before `provider.complete`, so there is
  no call outcome, and it is not added to `outcomes._NOT_AN_EXPLANATION`,
  matching `CONTEXT_OVER_CEILING`; behaviour at a billed attempt is unchanged.
- **Identity on the decorator.** Every store-touching route declares
  `dependencies=[IDENTITY_FIRST]`, so identity resolves before the store
  connection whatever order a signature lists them in; the handler's `Caller`
  is the same per-request cached dependency. `/api/health` takes none by design.
- **`RouteChoice.accepts_model_extension`.** The Run read computes it by running
  the create command's own `resolve_route` with the extension requested; only
  `ROUTE_EXTENSION_OWNER_MISSING` makes it false, and any other refusal is
  raised rather than hidden. The Create run form offers the §82 extension where
  it is true. The command still re-checks at commit; the surface grants nothing.

## 2026-09-18 §88 — Three owner decisions: D3's second half, Task 10.1, Task 10.3(b)

The owner, on 18 September 2026: "resume plan to completion, apply your
recommendations". The plan left three questions to the owner. For two of them
(10.1, 10.3(b)) the record held a fail-closed default; for D3's second half it
held none -- the ledger said only that the owner decides each code -- so the
statuses below are the coordinator's recommendation, made under that
instruction. Each is stated so a later owner decision can reverse it cleanly.

### 88.1 The eight retry-shaped 400s get a status

`RETRY_SHAPED_400_PENDING_OWNER` (§87) is renamed `RETRY_SHAPED_400_DECIDED`
and becomes a code-to-status mapping rather than a bare set, closing the
question §75's partition left open on the 4xx side. §75's own question decides
each: is the identical request cleared by waiting (503, `TRANSIENT`), or does
it meet the same answer again (500, `PERMANENT`)? `PROVIDER_UNAVAILABLE` is the
one the provider itself may clear by answering next time, so 503, joining
`TRANSIENT`. The other seven are an answer the provider already gave --
truncated, refused, unreadable, or a handoff failing its own contract -- which
a retry without a new call cannot change, so 500: `PROVIDER_OUTPUT_TRUNCATED`,
`PROVIDER_REFUSED`, `PROVIDER_RESPONSE_INVALID`, `ENVELOPE_INVALID`,
`ENVELOPE_UNDECLARED_FIELD`, `ENVELOPE_UNCITED_CLAIM`, `READINESS_INCOMPLETE`.
None of the eight answers 400 any longer, so `test_no_400_tells_the_caller_to_retry`
replaces `test_the_retry_shaped_400s_are_named_as_pending_the_owner`: the
partition test (§75) already covers the whole enum, and this closes the one
carve-out it left.

No HTTP path raises any of the eight today: the four `PROVIDER_*` codes reach a
caller as a parked run's `stop_code`, and nothing under `server/` raises the
three `ENVELOPE_*` codes or `READINESS_INCOMPLETE` since the claims executor was
deleted (f-2a). They stay in `RefusalCode` because stored rows may name them;
the statuses are the answer the day a route does raise one.

**503 is not a licence for the worker to retry.** `PROVIDER_UNAVAILABLE` is 503
for a future synchronous route, where waiting is what clears it. The worker
parks a run on it deliberately and waits for an operator's Retry, because the
attempt may already have been billed; `app.TRANSIENT` says nothing about that
loop, and nothing should read it as saying release-and-retry.

### 88.2 Task 10.1: the host does not take ownership of a CP-0 register's shape

Declined. Per-node evidence selection stays with the vendor request
(`docs/requests/2026-09-17-t8-source-files-column.md`). The request's own
question decides it: narrowing is monotone downward on anchoring, so a
model-authored register deciding what a downstream node may cite can turn a
truthful quote of a pinned source into `CITATION_NOT_DELIVERED`, and the host
cannot tell that from a correct narrowing. Readiness is model-authored too but
fails closed; selection would fail open on what a later module may prove.
Invariant 4 is the tie-breaker. So Task 10.1 and Phase 11's Task 11.8 behind it
are **waiting on the vendor**, not pending an owner decision, and the plan and
the handoff say so. What does not change: `CONTEXT_OVER_CEILING` still refuses a
wide route whole rather than truncating it.

### 88.3 Task 10.3(b): only a QA `Passed` releases CP-6

Declined: `Restricted` does not release CP-6 as RESTRICTED. §39 calls restricted
output usable but not QA-cleared, and the QA status is the module's own verdict,
which text in the evidence can steer; letting it release the next module would
make a steerable value an authority. The fail-closed reading `route._unmet`
already implements stands, with no code change. The discharge of a QA-blocked
run stays a human decision under unchanged pins, recorded as a successor run
(§72). The Repair Phase 2 ledger entry keeps its upgrade -- the canonical QA
record and human QA approval -- and loses its "a dated decision if committee
practice wants restricted clearance to proceed" clause, which this entry
answers. The question is not reachable today: no enabled route carries the
CP-5 -> CP-6 QA_GATE (`ADAPTER_ROUTES`).

## 2026-09-18 §89 — Membership surfaces in Directory, on a panel of its own

O21 put membership in Directory; Task 12.2 placed no control for it, and the
ledger deferred it to "Completion Phase 13's Admin work", which Phase 13 does
not carry (Admin stays an unavailable shell, D2). Built here.

- **Wire.** `CaseRow` gains `members: list[MemberRow] | None` (at most
  `MEMBERS_MAX`, 64; past it the document is partial, `LIST_TRUNCATED`) and
  `actions`, the two membership commands judged for that case. `ActionName`
  gains `GRANT_STANDING` and `REVOKE_STANDING`. `members` is served only to the
  case's ADMIN, the one member who may change it; `null` means "not served",
  never "empty". A global READER holding ADMIN standing is served the list and
  shown both controls refused, because the global role refuses the commands.
- **Cost.** The members are a lateral aggregate in `cases_for_member`'s one
  query, so the Directory's declared budget stays 2. The Book passes
  `members_limit=0`: it reads no membership.
- **Surface.** The register keeps one action per row (IA_SPEC §4.1); grant and
  revoke live on a separate Case access panel, refused rather than hidden for a
  member below ADMIN, each case a named group. A member is named by id: the host
  holds no directory of people to pick from, and inventing one is not this
  change.
- **What it costs.** Past 64 live members a case's list is cut and the document
  says `partial` with no per-row signal, so a member past the bound cannot be
  revoked from the surface (the command still can). And showing an ADMIN every
  co-member's id widens the tokenless-host disclosure the ledger records: one
  ADMIN's id now yields each co-member's id, and so their cases.

## 2026-09-18 §90 — The image gate's Trivy is installed into the project, pinned by digest

The owner approved it on 18 September 2026, closing the Completion Phase 13
ledger entry "The image gate cannot run on a machine whose Trivy has moved off
the pin" by the upgrade it named.

- **What.** `scripts/install_trivy.sh` fetches Trivy 0.70.0's release archive
  for the running platform (macOS arm64/x86_64, Linux x86_64/arm64) from
  `github.com/aquasecurity/trivy` and refuses it unless its SHA-256 equals the
  digest pinned in the script, taken from the release's published
  `trivy_0.70.0_checksums.txt`. Only then is the `trivy` binary extracted, into
  `.tools/trivy-0.70.0/`, which git ignores.
- **Wiring.** `make trivy` installs it once; `make bootstrap` depends on it;
  `TRIVY` defaults to that binary, so `make check` runs whole on any machine
  that bootstrapped, whatever Trivy it carries. `TRIVY=` still overrides, and
  `image` still refuses any version but `TRIVY_VERSION`.
- **Why a script and not a lock.** Trivy is a Go binary, not a Python or Node
  package, so no existing lock can hash it; the digest table in the script is
  the lock. Moving the version means new digests from the new release's
  checksums file and an edit here, which is the point.
- **Not changed.** CI keeps `aquasecurity/trivy-action` pinned by commit with
  `version: v0.70.0`; it never ran `make image`.

## 2026-09-18 §91 — The qualification floor is one worst-case call per run

The owner authorized two portfolio runs at $5 each. At the live model's price
($2 / $12 per million) the harness's floor -- one worst-case call *per node* --
needed $5.77 for a two-node route and refused before spending, although no node
has reserved a worst case since Task 8.2. The Phase 5 ledger entry owed this
upgrade. `harness._affordable` now requires one worst-case call per run, the
same admission `runtime._affordable` makes; `reserve`, under the run lock,
refuses the next reservation past the ceiling, and that is what bounds spend.

What it gives up, stated: the old floor (the Phase 5 confidence review's F-1)
stopped a set whose route could not be finished at worst-case prices. Now such a
route may start and stop short at `BUDGET_CEILING_REACHED`, having spent at most
its ceiling -- the amount the owner authorized. Invariant 8 is unchanged: no
call without a reservation, and no reservation past the ceiling.

## 2026-09-18 §92 — One authorised bundle build answering the six vendor requests

Invariant 4 says never edit a file that exists upstream. On 18 September 2026
the owner wrote "Vendor files - approved to alter but keep a record of
changes", which overrides that rule for the edits below exactly as §61 and §63
did for theirs, and §13's pin moves to the build they produce:
`30222a494a5a1035c7955cb1ccfbe0b3b0fbbfa7d6426930f5dcf4d35aa1fc18` ->
`62a94ccd0ef6439f797d60ebb72e6a44e1d42db16cd8af217fc41b7f1d6ea72c`. The record
the owner asked for is `docs/VENDOR_CHANGES.md`, which lists every vendor file
each build touched; this entry is the decision. Upstream
`github.com/EricMG13/Deploy-V@c4d2e356` carries none of it. The six requests
are the `docs/requests/2026-09-17-*.md` files, each of which now states what
was done.

**1. T8's `Source files to attach` reaches the parsed row.** The vendor's
`parse_t8` validated the column for width and dropped it; `Recommendation`
now carries it as `source_files_to_attach`, so the per-module evidence demand
CP-0 already writes has one reader, the bundle's
(`tests/test_bundle_pin.py::test_the_t8_parser_keeps_the_source_files_column`,
current and legacy headers). The host reads nothing new: `Projections` and
the readiness row are unchanged, and per-node evidence selection is a later
task with the owner's question -- may a model-authored register decide what a
downstream node may cite -- still to answer.

**2. The fixture markers are split from the thin-evidence marker.** §66 found
that enforcing the declared lists refused seven of the 25 retained real bodies,
every one for declaring `SOURCE_LIMITED_NOT_COMMITTEE_READY` truthfully, and
that the one substring hit was `source-limited` in honest prose. In every
`SKILL.md` that declares them (21 files, 117 lists), the three mixed lists
become `fixture_limitation_flags`, `fixture_validation_warnings` and
`fixture_document_substrings_casefold`, holding only the markers that say a
document is not real work, and the thin-evidence markers move to a sibling
`projected_evidence_limitations` block that says what it is. The bundle's own
`completeness_check` now enforces the fixture lists -- a front-matter fixture
flag or warning, or a fixture substring in the unfenced document, is a
violation the host maps to `HANDOFF_INCOMPLETE` -- and returns the projected
lists for a reader without enforcing them
(`test_the_fixture_markers_are_split_from_the_thin_evidence_marker`). By
§66's own measurement none of the 25 bodies carries a fixture marker, so the
split refuses none of them; those bodies live in a retired blob root outside
this tree, so that is derived from §66's record rather than re-run, and the
host suite's own corpus of every fixture handoff passes the enforced lists.

**3. `decision_scope` maps to the committee statuses it permits.**
`validate_handoff.py` declares `COMMITTEE_STATUSES_BY_SCOPE` -- `FULL` permits
every D2 value, `SCREENING_ONLY` every value but `Committee Ready` -- and
`validate_text` refuses a status outside the named scope, or a scope it does
not declare; `CANON_SHARED.md` gains the one "D2 BY SCOPE" line saying so. The
host hands the vendor the scope it already reads from the catalog, so run
`ff71c457…`'s screening-only CP-0 declaring `Committee Ready` is now refused
`HANDOFF_MALFORMED` by the bundle's rule and not by one the host invented
(`test_screening_only_never_permits_committee_ready`,
`tests/test_canonical_handoff.py::test_a_screening_only_handoff_may_not_say_committee_ready`).
The permitted set for `SCREENING_ONLY` is the widest honest one -- `Draft
Only`, `Requires More Work`, `Insufficient Information`, `Restricted`,
`Blocked` -- because the request left narrowing it to the vendor and nothing
in the canon narrows it.

**4. Every LITE edge into a named-object consumer names the object it
carries (option 1).** The typed edges `CP-L10 -> CP-2A` and `CP-L10 -> CP-3C`
declare `accepted_object_id` -- `lite_fundamental_credit_screen` and
`lite_liquidity_sensitivity_screen` -- and `allowed_use: SCREENING_ONLY`, as
the sibling edges to CP-2H and CP-4C already did; CP-3C's unkeyed prose
heading becomes the keyed block the host reads, naming the three objects the
execution profiles already declared for it. Which of CP-3C's three the edge
carries is a judgement: the liquidity screen, first-named in CP-3C's own prose
and the one a refinancing assessment turns on. Every LITE route's digest that
carries either edge moves, which is a vendor fact arriving as one
(`test_every_lite_edge_into_a_named_object_consumer_declares_the_object_it_carries`,
and `tests/test_handoff_invocation.py`'s boundary test now runs
`LITE_COVENANT_REFINANCING` too). The three pathways stay disabled in
`ADAPTER_ROUTES`; what this removes is the boundary reason, not the adapter
one.

**5. The three unshipped rules are shipped in the bundle's own validators.**
`semantic_rules`: `completeness_check` reads each `structured item` as its own
mapping -- before, the vendor's parser collapsed CP-L10's three rules into one
-- and enforces the five kinds the profiles declare (`unique_columns`,
`required_values`, `allowed_values`, `exact_values`,
`at_least_one_row_populates`); an unknown kind is a violation, never a silent
pass (`test_the_vendor_enforces_cp_l10s_semantic_rules`).
`document_substrings_casefold`: the fixture half is enforced under change 2.
`required_payload_fields`: `check_payload` judges a JSON payload's
`runtime_output` against the profile's list
(`test_the_vendor_checks_a_lite_payloads_required_fields`). **What that last
one does not buy:** the canonical adapter never receives a payload --
`invocation._FINAL_CHECK` tells the model not to author `runtime_output` --
so the host calls `check_payload` for nothing today; it is shipped, callable
through the verified contract, and unreachable from any run, which the ledger
now says. The rules cost the fixtures their shortcut: every builder that
repeated one cell per register -- the host's three and the vendor's own two
test files -- now derives its rows from the profile's rules
(`canonical_fixtures.conforming_rows`), and one enum's tension is recorded
there: CP-2 permits `Not Assessable` in a column its placeholder blocklist
refuses, so a conforming fixture takes the first value that is not one.

**6. CP-0 gates each consumer; nothing changes.** The owner's recommendation
taken is the fail-closed reading recorded in the request: the bundle states
per-consumer readiness in four places and its own scripts refuse a non-ready
module, so the host enforcing it is invariant 4 working, and `route.py` is not
weakened. No vendor file moves for this request; the ledger entry that owed a
decision closes on this paragraph.

**How the edit was made.** The validators were changed once each at the
`SHARED` owner and `verify_package.py --refresh` synchronised the 24 copies of
`validate_handoff.py` and 22 of `completeness_check.py`, ran the bundle's 52
unit tests and 10 helper self-checks, and regenerated the manifests. The
catalog is a pinned component of the vendor's authority bundle, so the refresh
ran with `--rebuild-authorities`, the bundle's own release operation, and
`authority_bundle_sha256` moved `47fec65f…` -> `e3d0f8b2…` with the vendor's
`local_rebuild` provenance naming the previous digest. The manifest the host
verifies at rest, `DEPLOY_V_INTEGRITY_v1.json`, is now `4945d137…`, still
68,657 bytes, so §35's ceiling reasoning is unchanged. The six host pins moved
with it, and `tests/test_delivered_authority.py` re-measures all three
delivered authorities (CP-0 146,605, CP-L10 199,898, CP-5 165,973 bytes),
because every `SKILL.md` and the canon grew.

**What it costs.** Every run pinned to `30222a49` -- including run
`62308d4e…`, the one `qualification_performed.complete` snapshot this project
holds -- now refuses `ORCHESTRATION_BUILD_MOVED` on re-proof, as §61 and §63
did to the runs before them. Their artifacts, charges, citations and the
recorded proof stand as recorded: the snapshot is a true statement about build
`30222a49`, and no qualification record is rewritten. There is no complete
snapshot on `62a94ccd`, and nothing is qualified. Unlike §61 and §63, the
vendor's own `tests/` **were** edited, because the rules the bundle now
enforces refused its own test artifacts; that edit is in the record.

**Decided against, here.** Enforcing the projected evidence lists anywhere:
they stay a projection a reader and a qualification key see, which is the
whole point of the split. Reading `source_files_to_attach` on the host: that
is per-node evidence selection, a later task under its own decision. Option 2
of the producers request (five `owned_object`s on CP-L10): it needs a host
change and says less than the edges do.

## 2026-09-18 §93 — The edge proves each request: a signed assertion, a TLS test edge, and the smoke stack in CI

The owner authorized Task 13.4 on 18 September 2026 ("Tasks 13.4 and 13.6 -
authorised to apply your recommendations"), closing the Repair Phase 4 ledger
entries "The edge proves itself with one static shared secret", "The API
cannot tell whether the edge stripped a client's identity", "The test edge's
session cookie is weaker than the contract's" and "The production image and
journey are proven locally, not in CI", and the edge-mode half of the audit
remediation entry "A tokenless host believes the subject header". Supersedes
§53.1 and §53.2's static token, and §53.3/§70.2's reading of the groups header
in edge mode. Standard library only: no dependency, no lock moved.

1. **The assertion.** `CAOS_EDGE_TOKEN` keeps its name and its 32-byte floor
   and becomes the key of an HMAC-SHA256 the edge computes **per request**,
   `server/api/edge.py::sign_assertion`: `v1.<payload>.<mac>`, both base64url
   without padding, the payload the canonical JSON (sorted keys, no
   whitespace) of the subject, the groups sorted and unique, the method, the
   raw target (undecoded path and query, exactly what the client sent), an
   issued-at second and a 16-byte hex nonce; the MAC over a domain tag and
   those bytes. Sent as one `x-caos-edge-assertion`; `x-caos-edge-token` is
   gone. The signer lives beside the verifier so the two cannot drift, and
   the operator's edge implements exactly this string.
2. **The verifier** (`verify_assertion`) checks the MAC under
   `hmac.compare_digest` before it parses anything, then the payload's closed
   shape (every field typed and bounded, groups in canonical order, no comma
   in a group), the binding to this request's method and target, an age of
   at most `ASSERTION_MAX_AGE_SECONDS` (30) either side of now -- the edge
   and the API keep their own clocks -- and a nonce this process has not
   admitted while it could still verify. `NonceRegister` is bounded
   (`NONCE_CAPACITY`, 65,536) and **refuses when full** rather than
   forgetting a nonce early: a full register means far more than the image's
   own concurrency limit of requests inside one window, and a replay admitted
   under load is the one thing it exists to refuse. Every failure is the one
   constant 403 `EDGE_NOT_TRUSTED`; no new `RefusalCode`, no wire change.
3. **Identity is the assertion's.** On a verified request the guard removes
   every `x-caos-user`, `x-forwarded-groups` and `x-caos-role` the request
   carried and writes the first two from the assertion, so `identity.py`
   reads what it always read and a header a misconfigured proxy forwarded
   unsigned decides nothing -- the Phase 13 exit check, held by
   `tests/test_edge_assertion.py::test_a_forged_group_header_is_ignored_whatever_the_proxy_forwarded`.
   Header hygiene (§53.4) still refuses a doubled or lookalike identity
   header first, because an appending edge is still evidence of one. Dev mode
   is unchanged: no key, loopback only, the role header under the switch.
4. **The test edge signs and serves TLS.** `tests/journey/edge.py` forwards
   only its allow-list and one assertion -- no identity header at all -- and
   signs each connect attempt afresh, so no nonce is sent twice.
   `tests/journey/run.py` mints a one-day self-signed certificate with an IP
   subjectAltName for `127.0.0.1` into the run's temporary directory with the
   `openssl` CLI (present on macOS and the ubuntu runners), starts uvicorn
   under it, and probes readiness with a client that trusts exactly that
   certificate. The edge's cookie is now the contract's whole
   `__Host-caos_edge_session; Secure; HttpOnly; SameSite=Lax; Path=/`. The
   browser's origin is `https://127.0.0.1:18080` in the runner, the Playwright
   config (`ignoreHTTPSErrors` for the throwaway certificate) and the spec,
   pinned to one string by
   `tests/test_journey_tooling.py::test_the_edge_origin_is_tls_and_the_config_spec_and_api_agree_on_it`.
   No key material is tracked, and the runner now calls the lock's own
   Playwright binary rather than `npx`.
5. **CI.** `.github/workflows/ci.yml` gains `smoke`: the image built once by
   buildx, the image suite under `CAOS_REQUIRE_IMAGE=1`, then
   `tests/journey/run.py` on three engines -- on a push to `main`, the nightly
   schedule and dispatch, never per pull request, because it takes about
   twenty-five minutes. Every action stays pinned by commit.

**What is given up, stated.** The nonce register is one process's memory: the
image runs one uvicorn worker, and a second process would hold a register of
its own, so a replay across processes is bounded only by the 30 s window
(ledger entry under Completion Phase 13). A key rotation still restarts the
API. The tokenless host still believes the subject header under the
development switch, which is that mode's purpose; what §93 closes is the
edge mode, where the subject was a header's word and is now the identity
provider's, signed.

## 2026-09-18 §94 — The release pack is emitted from the suite, the tree and the store

The owner authorized Task 13.6 on 18 September 2026 ("authorised to apply your
recommendations"). This is its in-tree half; the first authorized nightly and
the hosted checks verified on `main` need a push and are not part of it.

- **What.** `scripts/release_pack.py` (`make release-pack`) writes
  `release-pack/release-pack.json` and `release-pack/RELEASE_PACK.md`: the
  methodology build id and manifest digest, the migration head digested exactly
  as a migrated store records `store_schema.applied_digest`, the SHA-256 of the
  four locks, the test inventory (every Python test `tests/` defines and every
  workspace title `frontend/tests/` defines, read from the source), and one row
  per pathway the vendored catalog advertises.
- **The pathway rule.** A pathway outside `ADAPTER_ROUTES` is `DISABLED` and
  says why, whatever was signed over it. An enabled one is `UNVERIFIED` when no
  store was read, `NOT_QUALIFIED` when one was and nothing covers it, and
  `QUALIFIED` only when a `qualification_verdicts` row reads back through
  `current_verdict` at the named moment, for this bundle's build, over a
  snapshot one of whose prepared runs is pinned in `run_routes` to that pathway
  under the route digest the snapshot names. Evidence that does not re-digest
  to its key refuses the pack rather than being skipped.
- **Reproducible.** Sorted everywhere, no clock, no host, no git state: two
  emissions over one tree are byte-identical, including across interpreters
  and hash seeds. A store read needs `AS_OF` for that reason -- currency is a
  decision taken at a moment, as `read_verdict` already takes `now` -- and
  names the store only through `CAOS_DATABASE_URL`, so no credential reaches an
  argument list.
- **Emitted, not committed.** `release-pack/` is ignored. A committed copy
  would move with every test added and turn each commit into a checksum edit,
  which is the thing the exit check forbids.
- **Inventory by definition, not collection.** `pytest --collect-only` imports
  every module and needs database configuration, and its parametrised ids can
  carry values; the definitions are what the ledger gate already resolves
  citations against. A parametrised test is one row and a computed workspace
  title is recorded as its template.
- **`docs/feature-status.csv`.** Kept, unedited, as the dated predecessor; the
  pack is the live answer, and the Completion Phase 7 ledger entry is struck
  with that said.

## 2026-09-18 §95 — Per-node evidence selection reads the gate's T8 row, at the source grain

§88.2 declined host ownership of a CP-0 register's shape and sent Task 10.1 to
the vendor; §92 answered it, so the vendor's own `parse_t8` now carries
`Recommendation.source_files_to_attach`. The owner's dispatch of Task 10.1 on
this base is the authorization to read it. This entry records how the host
reads it, the one rule it applies, and the question §88.2 left -- may a
model-authored register decide what a downstream node may cite -- answered for
the source grain and no finer.

**What is built.** `server/methodology/selection.py`, pure over pinned inputs.
`demand_cells` hands the accepted CP-0 Markdown to the vendor's `parse_t8` and
keeps, per consumer module, the `Source files to attach` cell as the vendor
parsed it -- no host table reader, no second reading of T8 (invariant 4).
`select_sources` maps the cell to the run's pinned `SourceSetMember`s: the
cell is split on `;`, `,`, a newline or `<br>`, each item stripped of
whitespace and wrapping quotation, and an item names a member by its admitted
filename exactly or by its document digest; a cell that is one filename
carrying a separator is matched whole first. `canonical._context` applies the
answer after the pre-call unit has verified the gate's record and read the
whole pin through `read_run_blocks`, so a withdrawn member still refuses before
anything is narrowed (invariant 1), and every reader that builds a context --
`check_context`, the attempt, `replay_billed` -- selects the same blocks from
the same pins (invariant 10). The gate itself is always handed the whole pin;
CP-CF has no T8 row and is handed the whole pin; the pinned members are read
only when a cell has items, so no API read's declared budget moved.

**The rule, and why each arm is the fail-closed one.** Three outcomes:

1. *Every item maps to exactly one member* -- the node is handed those members
   and nothing else. This is the narrowing §88.2 feared, taken on the owner's
   authority and at the vendor's grain: the cell is the bundle's own statement
   of what a consumer needs, and `verify_citations` then refuses
   `CITATION_NOT_DELIVERED` for a quote of an unnamed pinned source
   (`tests/test_evidence_selection.py::test_a_quote_on_an_undelivered_member_is_refused_on_a_real_run`,
   the first real run shape on which that code fires).
2. *No item maps, or the cell is empty* -- the whole pin, exactly as every run
   before this entry. The host cannot read the cell as a selection, and the
   direction that weakens no invariant is the one it already had: a wider
   delivery can never turn a truthful quote into a refusal, ambiguity is
   counted over the whole page from the live source regardless, and a prompt
   too wide for the ceiling still refuses `CONTEXT_OVER_CEILING` rather than
   truncating. This is the documented fallback, and it is what keeps every
   existing fixture and route unchanged: the fixtures' T8 writes `Source p1`.
3. *Some items map and some do not, or one item names two members* -- refused
   `EVIDENCE_DEMAND_UNRESOLVED` (500, permanent) before any attempt,
   reservation or call. Narrowing to the readable half is precisely §88.2's
   hazard -- a truthful quote of the unread half becomes `CITATION_NOT_DELIVERED`
   -- and widening to the whole discards a demand the gate did state; the host
   would be deciding either way. The discharge is a successor run (§72) whose
   CP-0 writes a cell the host can read, which is why the clearance says so
   and why the code is not `EVIDENCE_NOT_AVAILABLE`: every pinned source is
   live. The refusal carries no item text (invariant 2).

**Decided against.** A stored `attempt_deliveries` row and a v3 record
carrying `delivery_sha256`, both in the original brief: the selection is a
function of the accepted CP-0 Markdown and the pin, both immutable, so storing
it would add a second authority a reader has to compare, and re-deriving it is
what projections already do. The cost -- no row says which basis a node ran
under -- is in the ledger. Per-node re-anchoring in the proof and the
deliverable: both still anchor against the whole pin, which can neither admit
nor refuse anything acceptance did not, and reading the gate's row there would
move `freeze`'s and the committee read's declared budgets; also in the ledger.
The bounded line group and the per-section bound the brief listed as (c) and
(d): separate concerns, not this entry.

**What it does not do, stated plainly.** Boeing's 10-K text (1,177,234 bytes)
and Ford's (1,922,743 bytes) are each one source and each larger than
`MAX_REQUEST_BYTES` (1,048,576). A selection at the source grain delivers a
named member whole, so naming either delivers more than the ceiling and
naming neither delivers nothing of it; neither is runnable after this entry,
and the ledger entry under Completion Phase 10 records the page- or
section-level grain that would be needed and what has to answer for it first.

**Tests.** `tests/test_evidence_selection.py` holds the pure rule (empty,
unmapped, named, digest, separator-in-filename, half-readable, ambiguous,
order-independent) and the run shape (only the named members reach the
prompt; the whole pin when nothing is named; the refusal before any attempt;
the gate always whole; one delivery at every reader). The new code is
registered in `RefusalCode`, `app.PERMANENT`, `app._STATUS`, `wire.CLEARS`
and the workspace's closed enum, and `frontend/src/wire/v1/schema.json` is
regenerated from the models.

## 2026-09-18 §96 — `LITE_DEEP_RESEARCH`: the pinned brief reaches CP-DR, and one vendor condition is changed to let it

Completion Phase 9 Task 9.4 (`docs/superpowers/plans/2026-09-17-phase-9-task-9.4-brief.md`,
steps 1–6; step 7, the live run, is not taken). `docs/COMPLETION_PLAN.md` O01
(CP-DR), O02 (one pathway) and O04 (CP-DR cannot be invoked).

**1. A vendor change, under the owner's standing approval.** The pathway was
dead as authored in the bundle's own code. The catalog declares CP-DR
`navigable: true` with `layer_id: null`; `validate_catalog` admits exactly that
for CP-DR alone; CP-0's `SKILL.md` lists CP-DR among the ids T8 may name; and
`navigation.parse_t8` refused any layerless row, and an empty T8 too. On a
pathway whose one consumer is CP-DR no CP-0 handoff could validate. The first
implementer of this task stopped there and wrote
`docs/requests/2026-09-18-t8-cp-dr-row.md` -- the "request document" its last
note named -- rather than build a host reading the bundle refuses. The owner
had approved on 18 September 2026 altering vendor files with a record, so the
request is answered rather than left open: `parse_t8` makes the exemption
`validate_catalog` already makes (`module.layer_id is None and module_id !=
"CP-DR"`), and nothing else moves. The vendor test the request asked for is
`test_research_workflow.py::test_deep_research_pathway_recommends_cp_dr_alone`,
watched failing without the change. `verify_package.py --refresh` regenerated
the metadata; the build moves `62a94ccd` -> `6a5f1050`, the authority digest
does not (`navigation.py` is not a pinned authority component). Recorded in
`docs/VENDOR_CHANGES.md`; the host pins it in
`tests/test_bundle_pin.py::test_the_t8_parser_accepts_the_cp_dr_row_cp0s_contract_permits`.
Every run pinned to `62a94ccd` refuses `ORCHESTRATION_BUILD_MOVED` under this
build, as §92's move did (the ledger's "A bundle upgrade invalidates every
earlier run's proof").

**2. The brief is judged at the pin, by the vendor.** `pin_run_input` binds a
caller's brief to this run's vendor id, this bundle's authority digest and an
unanchored gate (`UNANCHORED_CP0`), and hands it to the vendor's own
`research.validate_brief` (against a CP-0 anchor built from the pinned subject)
and `routing.Route(..., research_brief=...)` (the placement). The host adds
three refusals of its own, each at its boundary rather than as methodology:
a brief carrying `run_id`, `cp0_sha256` or `authority_sha256` (invariant 3 --
the host writes them); a `source_mode` other than `supplied_only` (invariant 1
-- the vendor would accept `web_only` and `hybrid` and then block; a capability
nothing here has is refused rather than paid for); and a field
`CP_DR_RESEARCH_BRIEF_V1.md` does not declare (wire strictness -- the vendor
ignores extra fields, and caller text no rule reads would otherwise ride into
CP-DR's prompt). A brief on a route with no CP-DR node is refused (it reaches
nobody), and on an enabled pathway carrying CP-DR a brief-less input is
refused: the vendor's own `plan_from_cp0` refuses CP-DR without a run-scoped
brief, and asking it at the pin is before CP-0 is paid. The judgement runs for
a new pin only; a replay compares with what was judged. No vendor text reaches
a refusal.

**3. CP-DR's identity, front matter, prompt and acceptance.** `HostIdentity`
gains `research_brief`: for CP-DR only, the pinned brief re-bound to the
accepted CP-0's Markdown digest and judged again by the vendor, as canonical
JSON; `None` for every other module and absent from a record that carries
none, so no record written before this entry moved. `invocation_fields` adds
the research front matter exactly as `prepare_invocation.prepare` emits it
for a linked brief (`research_mode`, `research_question`, `approved_plan_hash`
by the vendor's own `envelope.digest`, `scope_type`, `scope_key`,
`subject_name`, `source_mode`), held equal to the vendor's preparer run in
its own interpreter
(`tests/test_handoff_invocation.py::test_cp_dr_receives_exactly_the_pinned_brief_with_host_filled_bindings`).
The host does not call `prepare` itself: it needs a snapshot of files the host
does not keep, and its fields are the envelope the host already builds plus
these seven. CP-DR's prompt carries the bound brief as one tagged host-owned
`RESEARCH BRIEF` section after the upstream sections, labelled a run control,
not evidence and not an instruction to search; every other module's prompt is
unchanged (`test_no_other_module_receives_a_research_section`). Acceptance
runs the vendor's `research.validate_dossier` after the Blocked check --
TDR.1 is the locked questions exactly, each finding cites its own question's
evidence, ANSWERED rests on primary evidence or two independent families,
coverage and status follow from the count -- through `HANDOFF_INCOMPLETE`.

**4. The pathway.** `("LITE_CREDIT_22", "LITE_DEEP_RESEARCH")` joins
`ADAPTER_ROUTES` behind `tests/test_lite_deep_research_route.py`: it
completes, proves and freezes over a two-document pack; the accepted CP-DR
record carries exactly the brief its prompt carried; both requests fit the
ceiling; a CP-0 verdict blocking CP-DR stops the run before any CP-DR attempt;
an unanchored research answer is refused. `FULL_CREDIT_32 / DEEP_RESEARCH`
stays disabled -- the same two nodes, but its own contract test is not
written. The host's route extension (`RouteExtensions.research_brief`, CP-DR
appended at stage 99) is refused at execution input: it carries none of the
predecessor and consumer edges the vendor's `Route` synthesises from the
brief's questions, so a run on it would take a path the bundle would not.

**5. The set.** `qualification/vmo2-fy2025-deep-research/` over the two VMO2
releases, with an implementer-authored brief -- the owner asked for
equivalent versions to test with; the coordinator recommended authoring,
because a brief is a run control, not evidence -- of three questions: two the
Q4 release answers and one (Moody's current rating) neither release carries,
keyed UNRESOLVED. A qualification case may now declare `research_brief`: the
loader carries it as the pin's canonical text, the set digest covers it, the
harness pins it and eligibility compares it. Digest `09807efb…`; no run is
performed, and the figures await the owner (`RESULT.md`).

**What it does not do.** No live run; step 7 needs its own authorization. The
workspace cannot create a deep-research run that executes: the input-pin
command carries no brief, so such a run is refused at its pin (ledger).
Nothing downstream adopts research on this pathway -- every question's
consumer is `NONE` -- so the vendor's adoption register and its host
enforcement on a consumer are untested here, and the extension that would
reach them is refused.

**Build, as shipped:** §96 was made from `62a94ccd` concurrently with §98; the
coordinator combined the two edits into build `78c24be4…` (`docs/VENDOR_CHANGES.md`),
so `6a5f1050` above names an intermediate build no run is pinned to.

## 2026-09-18 §97 — Fable 5.1 is withdrawn from every role

The owner, 18 September 2026: "After the current task switch fable 5.1 as
implementer use opus", then "Stop usage of fable". Every implementer and every
review runs on Opus 5: implementers at `medium`, or `high` for store, lock,
billing or large multi-file work; task acceptance, the phase confidence review,
the phase adversarial audit and the final all-phases review at `xhigh`. The
running Task 9.4 implementer, which was on Fable, was stopped and its
uncommitted work handed to an Opus implementer. This overrides §85 and §86's
Fable rows. §81's caps stand: no `ultrathink`, no `max`.

What it gives up: §85 routed the phase gates and the final review to two
different models so their blind spots would differ. Both gates now share one
architecture. The agent definitions say so and tell the adversarial and final
reviewers to read as outsiders on purpose; that is a discipline, not a
substitute for a second model.

## 2026-09-18 §98 — The Boeing and Ford 10-K texts run by page: T8 names pages, the gate reads a page map

The owner approved the coordinator's recommendation on 18 September 2026:
make Boeing's (`BA_FY2025_10K.txt`, 1,177,234 bytes, `0446b367…`) and Ford's
(`F_FY2025_10K.txt`, 1,922,743 bytes, `97a38bc1…`) FY2025 10-K text extracts
runnable by page-level evidence selection, altering vendor files with a record
(the §92 approval), using only what is in hand -- no EDGAR. §95 had selected at
the source grain and recorded that neither text could run: a named member was
delivered whole and larger than the whole request.

**Measured first.** Through the real extractor (plain text v3): Boeing is 6,421
lines, 108 declared fixed-pitch pages of sixty lines, 4,852 blocks and 905,758
bytes of block text; Ford is 8,728 lines, 146 pages, 6,526 blocks and
1,435,471 bytes. Both now admit (the token cut of Completion Phase 13 took the
71,243- and 105,966-character XBRL runs on line one). A `.txt` page is
therefore a real, declared, checkable grain -- the `page` every evidence header
already shows -- so page grain is not meaningless here, and it is the one used.
Neither text fits whole: Boeing's escaped evidence alone is 933,394 bytes,
which with CP-0's delivered authority passes `MAX_REQUEST_BYTES` (1,048,576);
Ford's is 1,475,743.

**Two obstacles, not one.** A consumer's delivery is narrowed by the gate's T8
row, but the gate (CP-0) is always handed the whole pin, so a 1.9 MB source
could not reach CP-0 either. Both are answered, and neither by trimming.

1. **The bundle states the grammar (build `62a94ccd` -> `91c219fb`).**
   `REF_CP-0_STEPS.md` Step I rule 5 gains the page form of a `Source files to
   attach` item -- `<filename> pages <first>-<last>` or `<filename> page <n>`,
   one range per item, pages being the `page` locators the evidence shows, a
   filename alone attaching the whole source -- and a new rule 8 says a source
   the host delivers as a page map is evidence only in the lines shown, is
   triaged `PARSE_TARGETED` (the vendor's own existing decision for "only
   identified sections are useful, and the exclusion boundary is auditable")
   or `BLOCKED`, is attached by page and never whole, and carries the page-map
   limitation into every row. Edited once, `verify_package.py --refresh`, the
   bundle's 52 tests and 10 self-checks green, recorded in
   `docs/VENDOR_CHANGES.md`; no runtime authority moved, so
   `authority_bundle_sha256` is unchanged. CP-0's delivered authority grows 740
   bytes to 147,345. So the question §88.2 asked -- may a model-authored
   register decide what a downstream node may cite -- is answered one grain
   down exactly as §95 answered it at the source grain: the cell is the
   bundle's own statement of what a consumer needs, now in a form the bundle
   defines.
2. **Consumers: pages of a named member (`selection.select_sources`).** An
   item in the page form names its member by the §95 rules and the node is
   handed that member's blocks on those pages only; a member named whole and by
   page is handed whole; ranges union. A range that is backwards, below page
   one, past the last page the pin captured of the member, or longer than six
   digits refuses `EVIDENCE_DEMAND_UNRESOLVED` before any attempt, as a
   half-readable cell does: narrowing to the pages that exist would decide what
   the gate did not. The host reads the page form as §95 reads the item split,
   in the form the bundle states and no looser than optional parentheses,
   `page`/`pages` and an en dash. A filename that itself ends in a page phrase
   is still matched whole first.
3. **The gate: a page map (`selection.gate_view`).** A source whose block text
   passes `GATE_SOURCE_BYTES` -- 3/8 of the request ceiling, 393,216 bytes, so
   two such sources beside CP-0's authority still leave the instructions room --
   is shown to CP-0 as the largest uniform number `k` of leading lines of every
   page whose total fits the bound: every page present, every line whole, in
   stored order. Its entry in the host preparation metadata carries
   `evidence_delivery: PAGE_MAP`, `leading_lines_per_page`, `pages`,
   `lines_shown` and `lines`, and one note says that no other line is evidence
   and names rules 5 and 8. A map that cannot hold one whole line a page
   refuses `CONTEXT_OVER_CEILING`; nothing is cut. A source within the bound is
   shown whole exactly as before, and every document in the tree before this
   entry is within it, so no existing set's prompt moved. Measured: Boeing
   `k` = 16 (1,713 of 4,852 lines), Ford `k` = 10 (1,460 of 6,526).

**Why this preserves the invariants.** *Invariant 4*: the grammar and what a
page map means for readiness are the bundle's; the host decides only which
lines a map shows, by position alone -- never a keyword or a heading guess,
which would be the host deciding what matters -- and says that it did. The
host invents no readiness: CP-0 still writes every verdict, from lines it was
shown and told were partial. *No silent truncation*: nothing is trimmed; a
withheld line is withheld whole and declared, the gate cannot cite it
(`CITATION_NOT_DELIVERED`), and every prompt still meets `CONTEXT_OVER_CEILING`
as before. *Invariants 1, 10 and 11*: both rules are pure over the pinned
delivery and run inside `canonical._context`, after `read_run_blocks` has
counted the pin, so withdrawal still refuses first and the pre-call check, the
attempt and a replay select alike; a quote is still anchored only inside what
the node was handed, and a split line still needs all its blocks.

**Measured on the LITE earnings route** (`tests/test_large_documents.py`,
fixture provider, real bundle, extractor and prompt builder): CP-0's whole
request is 555,007 bytes on Boeing's map and 545,382 on Ford's; CP-L10 handed
Boeing pages 13-40 is 440,709 and Ford pages 22-64 is 555,512; each screen's
answer, citing its set's key, is accepted; and the same screen handed the
document whole still refuses `CONTEXT_OVER_CEILING`.

**The sets.** `qualification/ba-fy2025/` and `qualification/f-fy2025/`, one
LITE earnings case each, carry the texts byte-for-byte from the owner's corpus
(digests verified on copy). Their keys come from the owner's answer key by its
own locators -- Boeing's cash (10,921), revenue (89,463) and long-term debt
(45,637); Ford's consolidated operating cash flow (21,282),
Company-excluding-Ford-Credit operating cash flow (8,351) and Ford Credit debt
(141,417) -- each unique on its page, each CP-0 key inside the gate's map.
`.pre-commit-config.yaml`'s `check-added-large-files` excludes exactly those two
paths. The register rows are `in_hand` and the table is re-emitted.

**Not done, stated.** No live run: neither set has met a model, so whether a
real CP-0 names useful pages from a map of each page's first lines is
unmeasured, and nothing is qualified. The page map is blind to where a
filing's headings fall (Boeing's `Item 7.` is the 34th non-blank line of page
13, outside its map). The vendor record gap this edit triggered is now closed:
`docs/VENDOR_CHANGES.md` records the pre-change Git base and its exact expanded
path inventory, held equal to Git by `tests/test_vendor_change_record.py`.
The page-map limitation remains in the ledger.

**Decided against.** A host table of contents or heading detector for the gate
(the host choosing content); a vendor-declared staged CP-0 read (two gate calls
per run, a route and billing change far larger than this need); raising
`MAX_REQUEST_BYTES` (a provider-side bound, and Ford would still not fit); and
host-authored pagination of `.txt` beyond the extractor's declared page (a
second grain the evidence headers would not show).

## 2026-09-18 §99 — A set may declare the readiness refusal it expects; the CCL portfolio set does

Owner decision A, 18 September 2026, on `qualification/ccl-fy2025-portfolio/`:
keep the set and change its key to expect CP-0 to refuse CP-L10, so the set
tests the refusal and the VMO2 portfolio set keeps testing the ready path. The
authorized run of that set ended BLOCKED at CP-0's gate, whose T8 row for
CP-L10 asked for portfolio holdings, mandate and limits, the eligible
universe, market evidence and governing security documents -- a defensible
reading of what `LITE_PORTFOLIO_DECISION` needs over a 10-K alone -- while the
set's `expects_ready: ["CP-L10"]` assumed otherwise.

No existing key said that honestly. `expected_refusal: HANDOFF_BLOCKED` is met
by any BLOCKED run, but its code means a validated Blocked *handoff*, not a gate
verdict. So a case gains `expects_blocked: [module_id, ...]`:

1. **The reading.** `MatrixRow.blocked_met` reads `readiness_from(route,
   accepted)` -- the projection `ready_met` and the engine read -- and is met
   when every named module's verdict is in `UNCLEARED_READINESS`
   (`CONDITIONAL`, `BLOCKED`), the gate's own words for "does not run". A
   module the gate did not rule on is not refused; an unreadable route or
   artifacts is `False`; an undeclared key is `None`.
2. **Answerability.** `blocked_met is False` makes a row unanswered.
   `PerformedEvidence.complete` waives the COMPLETE requirement for a row whose
   key was met **and** whose run ended BLOCKED -- the run the key declared --
   and for no other status, mirroring the met-`expected_refusal` waiver.
3. **Validation.** The loader bounds and de-duplicates the list like
   `expects_ready`, and refuses a module in both lists
   (`QUALIFICATION_SET_FILE_INVALID`; `assert_unambiguous` refuses the same
   for an in-memory set). `prepare` and `perform` refuse, before anything is
   written, a readiness key of either kind naming a module that is not a
   pinned consumer of CP-0 on the case's route
   (`QUALIFICATION_KEY_UNANSWERABLE`). That check was not previously made for
   `expects_ready`; every committed set passes it.
4. **Digest stability.** The digest appends the key tagged
   (`["expects_blocked", [...]]`) so the same ids under the two keys cannot
   digest alike, and only when declared; the matrix row serialises
   `blocked_met` only when not `None`. Every existing set digest and every
   stored performed digest is therefore unchanged, and
   `tests/test_qualification_on_disk.py::test_every_committed_set_binds_its_recorded_digest`
   pins every committed set's digest.

The CCL portfolio set drops `expects_ready`, its CP-L10 citation key and its
two CP-L10 projection keys -- unreachable when CP-L10 is refused -- and gains
`expects_blocked: ["CP-L10"]`. It carried no CP-0 key to keep. Its digest moves
`5d50d1e7…` -> `7dcfa846…`. The key was changed by the owner's decision about
what the set measures, not fitted to a run's output: what a set should
measure over a 10-K alone was decided first, and the run's verdict is the thing
it will be scored against.

What it does not do: re-score the retained run through `build_matrix`. Its
database, `caos_qualify_13ec1a9c…`, no longer exists on the test server; only
its blob root does. Scored from the retained record blob (T8 readiness
`CP-L10: BLOCKED`) and the capture's run status and proof, the row reads
`blocked_met: true` and the snapshot `complete: true` under the new key -- an
offline reading of stored facts, not a performed snapshot, and nothing
signable until the set is performed again.

## 2026-09-18 §100 — A paid run's database is kept on the persistent server

`scripts/qualify.py` created each run's database on `CAOS_TEST_POSTGRES_URL`,
the test server whose data directory is a `tmpfs`. Under concurrent suites that
server ran out of space, implementers restarted it, and every retained database
of 18 September 2026's runs was erased -- among them the two authorised
portfolio runs (`caos_qualify_9b87b710…`, `caos_qualify_13ec1a9c…`). Their blob
roots and captures survive, so the records in each set's `RESULT.md` still hold
and a fact can be re-read from a blob, but a matrix can no longer be re-derived
from the store for them.

The driver now reads `CAOS_QUALIFY_POSTGRES_URL` and refuses, before spending
anything, when it is unset (`tests/test_qualify_script.py::test_main_refuses_to_keep_a_paid_run_where_it_cannot_last`).
`.env.example` names the persistent dev server on 55436 with its local admin
role. Earlier runs whose databases lived on the test server are in the same
state, whatever their `RESULT.md` says about retention.

## 2026-09-18 §101 — CP-DR is delivered the research contract its own authority names

Amends §45.1, which delivers a module's own non-script files and the root files
its `SKILL.md` names, and treats every one-level-up link as a script whose step
the host performs. One such link is not a script. CP-DR's `SKILL.md` says
"Read `../cp-os-credit-os/references/CP_DR_RESEARCH_BRIEF_V1.md`", and its
own references say that file "governs field names, hashes and run placement":
it is the only authority that spells the `<!-- table-id: cpdr.questions -->`,
`cpdr.evidence` and `cpdr.findings` tags `cp_tables` reads the registers by,
and the closed `claim_type` and `source_type` sets. The vendor's
`research.validate_dossier` refuses a dossier on every one of them.

Found by the Task 9.4 live run `94590ea4…` (`qualification/vmo2-fy2025-deep-research/`):
CP-0 accepted, CP-DR refused `HANDOFF_INCOMPLETE` twice. The report that the
approved-plan hash differed from the brief was a replay against the wrong brief.
Rebuilt from the retained pins, the identity's bound brief is the one the prompt
showed, and both answers carry exactly the `approved_plan_hash` the host wrote
into their front matter (`sha256:8ce1977e…`). The vendor refused both for
`cpdr.questions: required nonempty register/columns missing` because the
registers were untagged. Add the three tags and the next refusal is `research
source_type is invalid`: the model wrote "Issuer earnings release". Map its
source types onto the contract's and the first stored answer passes
`validate_dossier` unchanged in every other cell. Both refusals were for rules
the prompt never stated, so this was a host defect and not a model outcome.

`bundle.CROSS_SKILL_AUTHORITY` declares the file for CP-DR alone. It is
delivered after CP-DR's own references, under the literal its `SKILL.md` uses,
and verified under CP-OS's manifest entry. `AUTHORITY_BYTES_MISMATCH` refuses
a build whose CP-DR `SKILL.md` stops naming it
(`tests/test_delivered_authority.py::test_cp_dr_is_delivered_the_research_contract_its_skill_names`,
`test_a_cp_dr_skill_that_stops_naming_its_research_contract_refuses`). It is
declared rather than derived because every other `SKILL.md` names the same file
for the consumer side of research. Delivering it to them would move every
module's prompt and `delivered_authority_digest`, and with it the authority
match of each record accepted before now, for a route none of them is on
(`test_only_cp_dr_is_delivered_another_skills_file`). The route guard is
`tests/test_lite_deep_research_route.py::test_the_cp_dr_prompt_states_every_rule_its_dossier_is_refused_for`.
It reads every register id and enumerated value out of the vendor's own
`validate_dossier` and requires each one in the prompt CP-DR is sent. Before
this change it failed on five of them. No CP-DR record was ever accepted, so
the change to CP-DR's delivered digest invalidates nothing. A re-run of the set
is expected to reach a dossier the validator can judge on its content. Whether
the model answers it conformingly is still the model's.

## 2026-09-18 §102 — Every source says how its evidence was delivered

§98 labelled a page-mapped source `evidence_delivery: PAGE_MAP` and left a
whole source unlabelled. On build `78c24be4` the VMO2 portfolio run's CP-0
(run `cf5464dd…`) read the new vendor rule 8 -- which is about page maps -- onto
two earnings releases the host had delivered whole, triaged both
`PARSE_TARGETED`, called them unvalidated, and blocked CP-L10; the same set's
CP-0 on the previous build had judged them `PASS_THROUGH` and CP-L10 ready. The
investigation found the host section otherwise unchanged, so this was the model
misapplying our own new rule, not a missing fact.

Every source in `HOST SOURCE PREPARATION` now carries `evidence_delivery`:
`PAGE_MAP` with its map fields, or `WHOLE`. It changes CP-0's prompt bytes for
every run from here on; no accepted record binds those bytes (a record binds its
delivered authority, which is unchanged), so nothing already accepted moves.
Whether it prevents the misreading is a live question the next run answers.
`tests/test_page_selection.py::test_a_source_within_the_gate_bound_reaches_cp0_whole_and_says_so`.

## 2026-09-18 §103 — A register key is read the way the vendor's `check()` reads it

The scorer located registers with the vendor's `find_registers` asked with no
id list, on the Completion Phase 8 claim that this is how the bundle asks. It
is not: `completeness_check.check()` -- which every handoff passes at
acceptance -- asks with the module's whole contract register list, and an empty
list falls back to a default pattern (`[PT][0-9]…|TL[0-9]+.[0-9]+`) that cannot
match `TDR.1`–`TDR.3` or CP-1A's named registers. Run `de27f93c…` of
`qualification/vmo2-fy2025-deep-research/` was scored `registers_met: false`
over a CP-DR dossier whose `#### TDR.3 — Findings` table carried exactly the
three statuses the keys named.

`matrix.module_registers` now asks exactly as `check()` does: the module's
declared register list from its verified `SKILL.md`. Neither narrower (the
Phase 8 sibling-table defect) nor wider (this one); CP-L10's list names every
TL family, so the Phase 8 case still reads the honest table.

Keys keep naming `TDR.3`, not `cpdr.findings`. CP-DR's `SKILL.md` declares
`required_register_ids: TDR.1; TDR.2; TDR.3` and the completeness contract's
`required_registers` keys `TDR.3` with the seven finding columns; the catalog's
CP-DR entry lists `TDR.3`; and `CP_DR_RESEARCH_BRIEF_V1.md` names the same table
"TDR.3, tag `<!-- table-id: cpdr.findings -->`". The register id is the
identity every module shares and the one acceptance's completeness check
enforces, so one reader serves every module and no committed set digest moves.
`matrix.unlocatable_register_keys` reports a key its module's contract or the
scorer's reader cannot locate; the suite runs it over every committed set
(`tests/test_qualification_matrix.py::test_every_committed_register_key_is_locatable_by_its_modules_reader`).

## 2026-09-19 §104 — Claude roles map to two GPT models; `xhigh` remains the ceiling

The owner supplied `claude_fable_and_opus_reasoning_matrix.md` as reference
data and asked that its model and effort settings be adapted to their GPT
equivalents for resumed development. For every new dispatch, Claude Opus 5's
daily-driver and verification role maps to `gpt-5.6-sol`; Claude Fable 5.1's
long-horizon and chief-architect role maps to `gpt-6-astra`. The complete
forward-looking matrix is `docs/GPT_MODEL_REASONING_MATRIX.md`.

§81's ceiling remains binding. Codex has no `ultrathink` prompt lever, and a
source request for `ultrathink`, `max` or `ultra` maps to the actual `xhigh`
reasoning setting. Default implementation and ordinary review use
`gpt-5.6-sol` at `medium`; critical store, billing and localized concurrency
work may use `high`; long-horizon execution uses `gpt-6-astra` at `medium`,
and architecture/governance at `high`.

At a phase freeze, the confidence review runs on `gpt-5.6-sol` at `xhigh`,
then, after remediation and retest, the separate adversarial audit runs on
`gpt-6-astra` at `xhigh`. Task acceptance stays with the workhorse model at
`xhigh`; the one final all-phases review runs on `gpt-6-astra` at `xhigh`.
This restores a distinct reader for the adversarial gate that §97 explicitly
gave up. It overrides §97 and every earlier forward-looking Claude routing
row, but does not rewrite the model or effort recorded for completed work.

## 2026-09-19 §105 — FULL deep research is enabled on its deterministic contract only

`FULL_CREDIT_32 / DEEP_RESEARCH` has the same CP-0 -> CP-DR shape as the LITE
pathway proved in §96. `tests/test_full_deep_research_route.py` now proves that
whole route under its own FULL identity: the accepted CP-DR record projects
`decision_scope: FULL`, carries the pinned brief bound to the accepted CP-0,
anchors its citations, stays below the request ceiling, proves and freezes,
and is never attempted when CP-0 blocks it. The pair therefore joins
`ADAPTER_ROUTES`; the exact-set and disabled-route guards move with it.

This is not Task 11.4 acceptance. The test uses the existing deterministic
supplied-only fixture and makes no provider call. No FULL qualification keys,
live run, performed snapshot, or signed verdict exist yet; those remain the
separate qualification slice.

## 2026-09-20 §122 — release truth is store-backed and the dated feature inventory is append-only

The owner authorized the resolution plan through completion. Phase 5 preserves
the 248 historical feature rows rather than rewriting their dated test results,
and appends `REL-01` and `REL-02` as the current deterministic-route and
qualification censuses. This supersedes §94's statement that the predecessor
would remain entirely unedited without changing what §94 protected: old rows
remain historical evidence, while the generated release pack remains the live
answer.

At `2026-09-20T00:00:00+00:00`, the retained verdict store reports all eighteen
catalog pathways enabled, `LITE_CREDIT_22 / LITE_DEEP_RESEARCH` `QUALIFIED` by
the current owner-signed verdict, and the other seventeen `NOT_QUALIFIED`.
Two independent store-backed emissions under different hash seeds were
byte-identical. The emitted JSON SHA-256 is
`29e6f2492605476c6e617f428bd18c85cf7576e354976b0a46066349c0d70af4`;
the Markdown SHA-256 is
`18c9b5d38728616c57b6f5cf2ef5868ed671aa32ff018f7ec10eaa3e2cbae064`.
As §94 requires, `release-pack/` remains ignored and uncommitted.

This census does not authorize another provider call or convert route
enablement into model qualification. Private portfolio facts, a genuine T0
decision record, FULL research-brief confirmation, the last-trade-only market
limit and the two latest model misses remain explicit limitations.

## 2026-09-20 §123 — Canonical prompt identity is content-bound

The canonical adapter now pins a full SHA-256 identity over a domain-separated
manifest containing its readable adapter label, exact host persona and module
precedence policy, explicitly named fixed host instruction inputs, and the
source bytes of the shared builder and policy module. The compiled expected pin
is generated by `scripts/canonical_adapter_manifest.py`; runtime source or
policy drift refuses before a prompt is built and again while identity/accepted
records are read. The existing CP-CF host manifest continues to bind only the
calculator extension and its vendor invocation digest remains unchanged.

Module contracts, schemas, registers, status/refusal and QA-release rules,
output bounds, analytical remit, host safety, and supplied-only evidence remain
authoritative over the shared analytical persona. “Fully reasoned” is evaluated
from observable rationale, calculations and evidence, not private deliberation.
