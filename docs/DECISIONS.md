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
no charge, and the run completes with it reported unrun. The run surface carries
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
