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
receipt, the package verifiable with the standard library. One process.
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
