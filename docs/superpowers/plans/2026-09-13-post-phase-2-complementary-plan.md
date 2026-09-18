# Post-Phase-2 Complementary Implementation Plan

> **For agentic workers:** A coordinator may use up to three implementers in
> parallel only after partitioning independent tasks. Prefer native isolated
> worktrees; fall back to Git worktrees only when native isolation is absent.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete repair Phases 3–6 without re-planning the product, widening
an unfinished phase, or carrying stale interfaces across phase boundaries.

**Architecture:** Each phase consumes one accepted predecessor commit and
produces one independently demonstrable capability: canonical module handoffs,
the first real workbench, trustworthy calculations/filing, then qualified
release evidence. These are complementary phase briefs. Each phase begins with
a fresh GitNexus/source preflight that converts its brief into exact
concern-sized implementation slices against the interfaces that actually exist
then.

**Tech Stack:** Python 3.14 application code, Python 3.12 security tools,
PostgreSQL 17, FastAPI/Pydantic, psycopg 3, React/TypeScript/Vite, Node 24,
Playwright, Docker, Trivy 0.70.0, and installed GitNexus 1.6.9.

## Global Constraints

- Phase 2 must be accepted before this plan starts. Never implement a later
  phase to make a Phase 2 test pass.
- Work in `/Users/ericguei/Documents/caos-workbench`; keep
  `/Users/ericguei/Documents/caos-v2` read-only.
- `docs/DECISIONS.md` is binding; §39 reconciles this repair plan with older
  rebuild phases and specifications. `docs/CLAUDE_CODE_HANDOFF.md` alone owns
  current task status. The short launch text is `docs/PHASE_3_ONWARDS_GOAL_PROMPT.md`.
- The vendored methodology bundle is immutable. New host behavior must not edit
  a file that exists upstream.
- Every shell command starts by unsetting `OPENROUTER_API_KEY`,
  `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_PROVIDER`,
  `OPENROUTER_REASONING_EFFORT`, and `CAOS_REQUIRE_PROVIDER`.
- No live/paid provider call, hosted write, push, PR, merge, deploy, CI-rule
  change, dependency change, or destructive data cleanup without separate
  authorization.
- Use only the local test-admin service at `127.0.0.1:55437/postgres`, with its
  URL supplied privately. Tests create UUID-owned databases and clean them in
  `finally`; preserve the development database on 55436, blobs, and volumes.
- Use TDD. A semantic failure must be observed before production code changes.
- One task is one reviewable concern. The hosted size limit is 800 additions
  plus removals cumulatively from the actual PR base, not per commit.
- Parallel work is opt-in and bounded: the coordinator assigns each agent an
  exact base, branch/worktree, owned files, migration ownership, isolated test
  database/blob root, tests and report path. Do not run concurrent implementers
  on overlapping files, migrations, fixtures, provider authority or an
  integration branch. Read-only exploration may run in parallel.
- An implementer commits only its isolated concern. It runs focused tests and
  reports its commit/risk evidence. A task reviewer checks that exact range;
  the coordinator resolves findings, serially integrates reviewed commits and
  runs integration gates. No independent green branch is phase acceptance.
- GitNexus is discovery evidence. Verify every affected definition and caller
  in current source, types, and tests.
- Run ordinary exact-range review for every accepted task. Do not run a rewrite
  tournament.
- Run `confidence-review` only once at the end of each whole phase, followed by
  one separate adversarial code audit at the same phase boundary. Configure
  both actual review sessions to `xhigh`.

## Reasoning Modes

Apply the user's two attached Opus 5 guides as preferences: the coding guide
and the newer `claude_opus_5_plans_and_briefs_reasoning_guide.md`. Their roles
are recorded here so a fresh clone does not depend on a Downloads file.

| Mode | Scope and timing |
|---|---|
| `low` | Faithful formatting/transcription, status briefs and mechanical edits after decisions are fixed; never make authority, money, schema or concurrency decisions here |
| `medium` | Default for task briefs, feature/API specifications, migration runbooks, technical research briefs, ordinary implementation/TDD, ordinary task review and reports |
| `ultrathink` | One focused prompt to stress-test a drafted plan, ADR trade-off, rollback, race, trust boundary or numerical assumption; return to the normal drafting session afterward |
| `max` | Initial blueprint for a genuinely new complex multi-phase architecture or cutover; then `medium` for execution drafting. Do not repeatedly re-plan this accepted roadmap or use it for routine code work |
| `xhigh` | Actual executor setting for one whole-phase confidence review and the separate whole-phase adversarial code audit; never a per-task review requirement |

For an ADR, draft at `medium`, then stress-test the specific trade-off using
`ultrathink`. For an implementation roadmap or migration strategy, settle the
initial complex blueprint at `max` only when needed, then draft its bounded
tasks/runbook at `medium`. Audit each drafted plan with one targeted
`ultrathink` request; that document check is distinct from the phase code gate.

### Model routing (dual-model matrix, adopted 13 September 2026)

The user's `claude_dual_model_reasoning_matrix.md` adds a model axis to the
modes above. Recorded here so a fresh clone does not depend on a Downloads file.

| Work | Model | Mode |
|---|---|---|
| Phase briefs, specs, ADRs, runbooks, slice plans | Opus | `medium` |
| Plan/trade-off/rollback/race/trust stress test | Opus | `ultrathink` |
| Mechanical edits: fixture moves, renames, formatting, status | Sonnet | `low` |
| Ordinary implementation, test retargeting, UI/API wiring, unit tests | Sonnet | `medium` |
| Implementation touching locks, transactions, money, identity, migrations, canonical verification or authority | Opus | `medium` |
| Tricky local logic in an otherwise ordinary slice | Sonnet | `ultrathink` |
| Ordinary per-slice review (scope, tests, readability, style) | Sonnet | `medium` |
| Ordinary review of a slice in the Opus implementation row above | Opus | `medium` |
| Whole-phase confidence review and adversarial audit | Opus | `xhigh` |

Overrides kept from the governing goal: no rewrite tournaments, and the phase
gates stay at actual `xhigh` (the matrix's `max` is not substituted). When a
slice is mixed, the stricter row decides.

Configure and verify supported effort controls on the installed Claude session
or reviewer. Record actual model/version/effort at formal checkpoints; a word
in a prompt is not proof of a setting or a fixed token budget. Do not copy an
unverified environment-variable example or silently substitute `max` for the
user's `xhigh` code reviews. If a required mode is unsupported, report the
limitation and leave the affected gate unsatisfied.

Stay strictly within the requested scope: no optional extensions, speculative
infrastructure or unrequested architectural layers.

## Shared Phase Entry and Exit

Every phase starts with this sequence:

- [ ] Confirm the preceding phase's accepted commit, clean worktree, active
      branch, and explicit authorization for only the next phase.
- [ ] Read `CLAUDE.md`, `docs/REPAIR_PLAN.md`, the relevant specification and
      decision sections named below, and every current implementation/caller in
      the phase file map.
- [ ] Rebuild and verify the local index only:

  ```sh
  env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u CAOS_REQUIRE_PROVIDER /Users/ericguei/.nvm/versions/node/v24.16.0/bin/gitnexus analyze --force --index-only
  env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u CAOS_REQUIRE_PROVIDER /Users/ericguei/.nvm/versions/node/v24.16.0/bin/gitnexus status
  ```

- [ ] Write a tracked phase/task brief under `docs/superpowers/plans/` with
      the accepted base, exact files, current interface signatures, failing
      assertions, task splits, risk classification, commands and cumulative PR
      size estimate. These phase cards are not code-ready task briefs: elaborate
      only the next task against actual interfaces, including exact tests and
      implementation steps. Ignored notes cannot be the only binding record.
- [ ] Use the Reasoning Modes table for drafting; keep implementation at
      `medium`. Stress-test the completed brief with the named `ultrathink`
      prompt before beginning its code, without reopening settled scope.
- [ ] Map task dependencies and launch at most three implementers only for
      disjoint ownership. Give every worktree its own UUID-owned test database
      and blob root; the coordinator alone updates the handoff and integration
      branch.

Every implementation task exits through focused tests, then the serial backend
gate using the private test URL supplied to both the process and Make:

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u CAOS_REQUIRE_PROVIDER make -j1 check-postgres lint types test test-postgres-races security CAOS_REQUIRE_POSTGRES=1 CAOS_TEST_POSTGRES_URL="${CAOS_TEST_POSTGRES_URL:?set privately}"
```

Each implementer commits its tested concern, then a task reviewer completes
ordinary review/remediation for that exact range. The coordinator integrates
only reviewed commits, runs affected integration checks, then runs the final
size gate before acceptance. The script reads only committed
`base...HEAD`; a pre-commit run misses pending edits. Set `PR_BASE` to the
actual target base and record the candidate HEAD. A task's accepted base may
be used only if it is also the intended PR base; otherwise prove both ranges.
Plan stacked PRs or independent slices explicitly; small local commits do not
make an oversized eventual PR valid:

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u CAOS_REQUIRE_PROVIDER make check-size PR_BASE="${PR_BASE:?set exact proposed PR base}"
```

At whole-phase freeze, run the complete repository gate—not `check-fast`—with
the pinned local Trivy executable/path:

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u CAOS_REQUIRE_PROVIDER TRIVY="$TRIVY" IMAGE=caos-workbench:check make check
```

Then run one `xhigh` confidence review over the full phase and affected callers,
remediate and rerun gates, refresh GitNexus, run the separate `xhigh`
adversarial audit, remediate/reverify within that checkpoint, and freeze final
evidence. Commit a tracked acceptance record with exact implementation and
review-remediation commits, source/index identities, actual modes, commands,
results and remaining limits. Recheck the final committed size, then continue
to the next authorized phase until Phases 3–6 are complete.
Local checks cannot manufacture hosted GitHub/Sonar statuses. Any review
change invalidates evidence tied to the previous candidate; refresh affected
tests, build/qualification identities and verdicts before accepting it.

---

## Phase 3 — Canonical Module Handoffs on One Bounded Route

**Why now:** Phase 2 establishes durable identity and acceptance. Phase 3 can
therefore replace the lossy claims-only carrier without letting a model choose
run, route, evidence, or upstream identity.

**Consumes:** Accepted Phase 2 run-input, source, route, gate, billing,
generation-fencing, and blocked/QA guarantees.

**Produces:** One deterministic-provider execution of
`CP-0 → CP-L10 → CP-5` whose accepted artifact preserves validated canonical
Markdown, exact lineage, typed projections, and anchored citations.

**Primary references:** `docs/REPAIR_PLAN.md`,
`docs/SYSTEM_SPEC.md`, `docs/DECISIONS.md` §§26, 28, and 29,
`vendor/deploy-v/CANON_SHARED.md`, and the complete CP-0/CP-L10/CP-5 bundle
files selected by the pinned catalog.

### Task 3.1: Freeze the Canonical Record and Adapter Boundary

**Files:** Read and plan changes around `server/methodology/envelope.py`,
`server/methodology/executor.py`, `server/methodology/runner.py`,
`server/methodology/bundle.py`, `server/methodology/__init__.py`,
`tests/test_module_execution.py`, and `tests/test_manifest_authority.py`.

- [ ] Specify one authoritative record containing exact Markdown bytes/hash,
      host-owned run/entity/period/source-set/route/bundle/adapter identities,
      module-required sections/registers, QA/readiness, limitations, and closed
      typed UI projections.
- [ ] Identify which current `Envelope`, `ModuleOutcome`, artifact, and runner
      fields can be reused. Add no second model-authored summary and no generic
      per-module claims template.
- [ ] Record the exact parser/validator signatures and persistence boundary in
      the Phase 3 binding brief before tests are written.
- [ ] Write semantic REDs showing that claims-only JSON, changed Markdown,
      missing registers, mismatched identity, undeclared fields, and a wrong
      adapter cannot become accepted authority.

**Targeted prompt:** `ultrathink: Trace the proposed canonical Markdown bytes,
hash, host identities, typed projections, and accepted artifact through every
write/read boundary. Find any path that can create two competing authorities or
accept a provider-claimed identity.`

**Task acceptance:** The contract is lossless for the selected route, closed on
the wire, and stored once. Existing direct callers are migrated without an
optional compatibility bypass.

### Task 3.2: Complete Evidence Admission and PDF Geometry

**Files:** `server/evidence/ingest.py`, `server/evidence/extract.py`,
`server/evidence/pdf.py`, `server/evidence/citations.py`,
`tests/test_ingestion.py`, `tests/test_pdf_extraction.py`, and
`tests/test_awkward_evidence.py`.

- [ ] Write REDs for atomic mixed text/PDF admission and typed refusal of
      scanned, encrypted, corrupt, oversized, over-page, over-token, and
      over-time inputs.
- [ ] Add edge proofs for spaced glyphs, wrapped lines, columns, repeated
      quotes, page rotation, and crop coordinates. A quote must resolve exactly
      once inside a delivered page/token range.
- [ ] Reuse the existing `Extractor` protocol and admission transaction. Add
      only the minimal type dispatch and bounds needed by those failures.
- [ ] Prove a refused pack leaves no admitted database rows and that error
      messages/logs contain no document-derived text.

**Targeted prompt:** `ultrathink: Attempt to make the citation locator join
tokens across a column, choose the wrong repeated quote, or derive a rectangle
outside rotated/cropped page coordinates. Name the smallest failing fixtures
that distinguish those cases.`

**Task acceptance:** Mixed packs are atomic; host-derived geometry and extractor
identity survive admission; undelivered page content cannot be cited.

### Task 3.3: Deliver Complete Instructions and Upstream Lineage

**Files:** `server/methodology/bundle.py`,
`server/methodology/executor.py`, `server/methodology/runner.py`,
`tests/test_methodology_bundle.py`, `tests/test_module_execution.py`, and
`tests/test_orchestration_proof.py`.

- [ ] Write REDs proving required shared/reference bytes are missing from the
      current prompt and that a missing/changed accepted predecessor prevents
      downstream acceptance.
- [ ] Build context only from verified bundle bytes and the pinned route's
      direct predecessor artifacts, in route order. Carry full lineage even
      when immediate context is direct-only.
- [ ] Keep upstream analytical content distinct from evidence: predecessor text
      cannot satisfy a citation.
- [ ] Add the smallest host-owned calculator allowlist and work-factor bounds
      required by the selected route. Source/model text never chooses code,
      paths, or shell commands.
- [ ] Refuse over-ceiling context explicitly; never silently truncate or ask a
      second model to summarize mandatory registers.

**Task acceptance:** Every delivered instruction/reference/upstream byte is
verified and identity-bound; missing or changed lineage fails before artifact
acceptance.

### Task 3.4: Prove the Single LITE Route End to End

**Files:** `server/engine/route.py`, `server/engine/runtime.py`,
`server/methodology/runner.py`, `tests/test_live_run.py`,
`tests/test_module_execution.py`, `tests/test_runtime.py`, and
`tests/test_orchestration_proof.py`.

- [ ] Use the catalog-selected `CP-0 → CP-L10 → CP-5` route; do not hardcode a
      replacement graph or enable another route.
- [ ] Drive realistic valid canonical handoffs with the deterministic fake
      provider through the existing runtime and validator that the Phase 4
      worker will invoke. A worker is not a Phase 3 prerequisite.
- [ ] Prove malformed, blocked, wrong-upstream and undelivered-citation results
      cannot become usable downstream analysis; source/model instructions
      cannot change host authority or tool selection.
- [ ] Prove valid restricted output stays usable only where its contract
      permits and carries its limitations throughout. Preserve disclosed
      conflicts; neither a restriction nor a conflict is automatic QA clearance.
- [ ] Prove CP-5 remains the full named LITE QA workflow and that blocked or
      invalid output is retained only as diagnostic attempt evidence.

**Phase 3 exit:** Run the parent plan's Phase 3 engineering exit checks, the
complete repository gate, one whole-phase `xhigh` confidence review, and one
separate whole-phase `xhigh` adversarial audit. This recorded engineering
acceptance permits an authorized Phase 4. It requires neither paid calls nor
the future worker, and does not confer live qualification. Phase 6 owns the
release candidate's separately authorized live evaluation.

---

## Phase 4 — First Real and Secured Credit Workbench

**Why now:** The browser must consume the exact accepted authority produced by
Phase 3. Connecting it earlier would stabilize fixture shapes instead of the
real contract.

**Consumes:** Accepted Phase 3 canonical artifacts and Phase 2 durable worker
ownership/authority rules.

**Produces:** A real Directory → Upload → Run → Analysis browser journey over
PostgreSQL, blobs, API, worker, events, and pinned evidence pages, with no
fixture fallback.

**Primary references:** `docs/REPAIR_PLAN.md`,
`docs/SYSTEM_SPEC.md`, `docs/IA_SPEC.md` §§2–5,
`docs/DECISIONS.md` §§22 and 30.

### Task 4.1: Freeze One Section Wire and Refusal Contract

**Files:** `server/api/app.py`, `server/api/identity.py`,
`frontend/src/wire/shared.ts`, `frontend/src/wire/directory.ts`,
`frontend/src/wire/upload.ts`, `frontend/src/wire/run.ts`,
`frontend/src/wire/analysis.ts`, `frontend/src/app/transport.ts`,
`tests/test_api_routes.py`, and `frontend/tests/unit/transport.test.ts`.

- [ ] Define versioned Pydantic and TypeScript contracts for the four enabled
      sections, one document per section, with matching pinned key sets and
      closed shapes both ways.
- [ ] Choose one refusal body carrying typed code and what clears it; preserve
      private 404 equivalence for unknown/unauthorized resources.
- [ ] Write cross-language contract tests before adding endpoints. Reject stale,
      partial, malformed, or undeclared browser responses instead of casting.
- [ ] Keep Book, Model, Report, Committee, and Admin unavailable until their
      real contracts are enabled by later phases.

**Task acceptance:** The backend and browser agree on exact section/refusal
documents; no fixture is reachable from ordinary development or production.

### Task 4.2: Add Minimal Governed Commands

**Files:** `server/api/app.py`, `server/api/identity.py`, the existing owning
modules under `server/store/` and `server/evidence/`,
`tests/test_api_routes.py`, `tests/test_actor_matrix.py`, and
`tests/test_governed_writes.py`.

- [ ] Freeze endpoint names and request/response models in the Phase 4 brief,
      then write REDs for case creation, document admission, exact preview and
      approval, run start, retry, and cancel.
- [ ] Derive actor, case, run, route, digest, and permission on the server.
      Browser-supplied identities are expectations only.
- [ ] Bind commands to idempotency keys and current digests; stale preview or
      changed authority returns a typed conflict without a provider call.
- [ ] Run every endpoint through applicable anonymous, nonmember, reader,
      writer, approver, revoked, and administrator cases.

**Task acceptance:** The smallest command set can drive the four-section
journey; no client-computed authorization or ambiguous mutation succeeds.

### Task 4.3: Add One PostgreSQL-Backed Worker

**Files:** Create `server/engine/worker.py`; modify
`server/engine/runtime.py`, `server/store/runs.py`, `Makefile`, and the smallest
required migration/store module; test in `tests/test_runtime.py`,
`tests/test_execution_attempts.py`, and `tests/test_postgres_races.py`.

- [ ] Write crash/interleaving REDs around queue claim, reservation, provider
      return, acceptance, lease expiry, cancellation, and terminal state.
- [ ] Claim work with PostgreSQL and the accepted-attempt ledger. Recompute from
      durable state after restart; add no broker, checkpointer, Redis, or second
      database.
- [ ] Ensure browser disconnect does not cancel a paid call and a lost lease
      cannot accept a stale result.
- [ ] Add `make dev-worker` only with the worker entry point and health behavior
      proven by tests.

**Targeted prompt:** `ultrathink: Enumerate every two-worker interleaving from
claim through reservation, provider return, cancellation, lease loss, artifact
acceptance, and terminal event. Identify the database predicate that prevents
each stale acceptance without holding a lock across transport.`

**Task acceptance:** Kill/restart at each boundary yields one authoritative
accepted result, durable known/possible spend, and explainable retry state.

### Task 4.4: Connect Real Reads, Events, and Evidence Pages

**Files:** `server/api/app.py`, `server/api/stream.py`,
`server/evidence/read.py`, `frontend/src/app/App.tsx`,
`frontend/src/app/Workspace.tsx`, `frontend/src/app/authority.ts`,
`frontend/src/app/sse.ts`, `frontend/src/evidence/EvidenceDrawer.tsx`,
`tests/test_api_routes.py`, `tests/test_run_stream.py`, and relevant frontend
unit/workbench tests.

- [ ] Port the isolated frontend regressions into tracked tests before fixes.
- [ ] Fetch/refetch real section documents; discard late responses after case
      switches and require explicit reload for stale visible snapshots.
- [ ] Send name-only SSE invalidations with `Last-Event-ID`; recheck membership
      during streaming and stop after terminal delivery/deadline.
- [ ] Serve only authorized pinned source pages. Derive highlights from retained
      source geometry and bind the drawer to the visible snapshot.

**Task acceptance:** Case switching, withdrawal, reconnect, terminal stop, and
evidence focus restoration behave correctly against the real API.

### Task 4.5: Package and Prove the Same-Origin Deployment

**Files:** `Dockerfile`, deployment configuration chosen in the Phase 4 brief,
`server/api/app.py`, `frontend/vite.config.ts`, `tests/test_dev_environment.py`,
`tests/test_frontend_modes.py`, and `frontend/tests/workbench/`.

- [ ] Add liveness/readiness over store, bundle, and blob dependencies with
      bounded cached probes and no auth requirement.
- [ ] Derive production identity only from the trusted OIDC/reverse-proxy edge;
      block direct access to the development role-header listener.
- [ ] Add origin/CSRF controls for cookie-authenticated writes and CSP/safe
      rendering for untrusted analytical text.
- [ ] Boot the production image with disposable data and drive the complete
      four-section journey. Prove production contains no demo middleware or
      fixture artifact.

**Targeted prompt:** `ultrathink: Trace every header, cookie, proxy hop, origin
check, and backend listener that can influence Actor. Find a deployment path
where a user-supplied role/group value or cross-origin write can reach a
governed command.`

**Phase 4 exit:** All Phase 4 checks at `docs/REPAIR_PLAN.md`, full browser
matrix and production smoke pass, followed by the complete repository gate,
one whole-phase `xhigh` confidence review, and one separate whole-phase `xhigh`
adversarial audit.

---

## Phase 5 — Trustworthy Forecast, Revision, and Filing

**Why now:** Model, Report, and Committee must stay unavailable until financial
arithmetic and the immutable revision/sign/freeze/file chain are independently
provable.

**Consumes:** Accepted canonical artifacts and the secured real workbench.

**Produces:** Deterministic CP-CF projections, validated revision payloads, one
HTML deliverable, and a bounded independently verifiable audit package.

**Primary references:** `docs/REPAIR_PLAN.md`,
`docs/SYSTEM_SPEC.md`,
`docs/IA_SPEC.md` §§4.6–4.8, and `docs/DECISIONS.md` §§8, 14, and 29.

### Task 5.1: Freeze and Correct the Forecast Contract

**Files:** `server/calculators/cash_flow.py`,
`tests/test_cash_flow_forecast.py`, and the CP-CF host-extension files permitted
by the verified bundle/host-skill mechanism.

- [ ] Decide which documented opening, periods, drivers, contractual, policy,
      tolerance, case, scenario, perimeter, and unit fields are supported.
      Explicitly refuse unsupported fields; never coerce missing values to zero.
- [ ] Write independent hand-calculated annual and quarterly base/downside REDs,
      including duplicate/extraneous identities, magnitude/work-factor bounds,
      zero denominators, unavailable propagation, and ambient Decimal context.
- [ ] Use one local Decimal context and fixed rounding. Keep numeric input/output
      as finite strings; reject float, boolean, NaN, infinity, and huge finite
      exponents before arithmetic.
- [ ] Implement only the declared cash/debt movements and preserve explicit
      residual/unavailability reasons.

**Targeted prompt:** `ultrathink: Recalculate every debt and cash identity by
hand under the chosen Decimal precision. Search for ambient-context leakage,
rounding-order dependence, missing-versus-zero collapse, non-finite values, and
an exponent or collection that can evade the work-factor ceiling.`

**Task acceptance:** Independent expected values reconcile; repeated execution
under changed ambient contexts produces byte-identical output.

### Task 5.2a: Establish the Forecast Route's Canonical Owners

**Files:** `server/engine/route.py`, `server/methodology/envelope.py`,
`server/methodology/bundle.py`, `server/methodology/runner.py`,
`tests/test_route_resolution.py`, `tests/test_module_execution.py`, and
`tests/test_orchestration_proof.py`.

- [ ] Select `FULL_CREDIT_32 / FULL_CREDIT_ASSESSMENT` from the pinned
      catalog, verify it still contains CP-1, CP-2G and CP-4, and enumerate
      its required predecessor contracts before enabling the model extension.
      Do not add owners to the LITE earnings route.
- [ ] Split the canonical adapters/proofs into bounded owner concerns using
      the Phase 3 accepted Markdown/host-identity mechanism. Preserve mandatory
      registers and references for every required predecessor; claims-only
      fixtures cannot satisfy these inputs.
- [ ] Write the missing-owner refusal first, then prove a deterministic run
      produces exact accepted owner handoffs with anchored drivers and covenant
      terms. Record restricted/blocked behavior and context/budget bounds.
- [ ] Enable this route only after those contract proofs pass; keep all other
      unproven routes disabled. Live qualification still belongs to Phase 6.

**Task acceptance:** Exact accepted CP-1/CP-2G/CP-4 and required predecessor
handoffs exist on the proven route and can be consumed by CP-CF without
inventing inputs. The extension still refuses an absent owner.

### Task 5.2b: Wire CP-CF Through the Host Allowlist

**Files:** `server/engine/route.py`, `server/methodology/bundle.py`,
`server/methodology/executor.py`, `server/methodology/runner.py`, and focused
route/module/calculator tests.

- [ ] Add CP-CF only through the declared host extension and pinned route; do
      not edit CP-2G, CP-4, or the upstream catalog.
- [ ] Require the exact accepted CP-1, CP-2G, and CP-4 inputs and evidence-backed
      drivers before selecting `cash_flow_forecast`.
- [ ] Keep code selection host-owned and digest-verified. The model supplies
      data, never Python, a path, or a calculator identifier outside the
      allowlist.
- [ ] Prove missing/wrong upstream identity, incomplete output, and a stale
      extension pin cannot release the Model projection.

**Task acceptance:** CP-CF is a real accepted module artifact on its pinned
extension route, not an orphan library or an editable workbook.

### Task 5.3: Construct and Render the Saved Revision

**Files:** `server/deliverable/render.py`, `server/deliverable/filing.py`,
the smallest owning store module, `tests/test_deliverable_render.py`, and
`tests/test_deliverable.py`.

- [ ] Define the revision solely from validated accepted artifacts in route
      order, exact narrative bytes, typed figure references, limitations, and
      partial/refused claims.
- [ ] Write REDs proving arbitrary caller bytes, detached hashes, uncited
      figures, wrong case/snapshot/upstream identities, and altered narrative
      cannot be signed or frozen.
- [ ] Render deterministic one-file HTML without originating facts. Preserve
      both sides of conflicts, restrictions, screening labels, and provenance.
- [ ] Bind opinion, freeze, and filing to exact saved/frozen bytes and three
      independent actors using existing transactional CAS/event patterns.

**Targeted prompt:** `ultrathink: Enumerate concurrent save, sign, freeze, and
file interleavings across two cases and three actors. Find any path where a
detached digest, stale revision, or actor checked before commit can authorize
different bytes.`

**Task acceptance:** Only the exact current signed revision freezes; immutable
file/receipt identity and actor independence hold under races.

### Task 5.4: Bound and Verify the Audit Package

**Files:** `server/deliverable/package.py`, `server/deliverable/filing.py`,
`tests/test_deliverable.py`, and Model/Report/Committee wire/view tests.

- [ ] Refuse malformed, oversized, duplicate-member, traversal, decompression,
      and ambiguous archive inputs with total bounded verification.
- [ ] Keep package creation exclusive and non-overwriting; receipt, payload,
      export, signatures, and provenance must agree exactly.
- [ ] Supply the stdlib-only verifier required by decision §14 and prove it
      works in a clean environment without the repository. Removing portability
      requires an explicit scope decision; a test does not decide the product
      requirement.
- [ ] Enable Model, Report, and Committee reads only for these accepted real
      objects; keep editing/filing controls server-authorized.

**Phase 5 exit:** Run the financial, filing, package, UI, concurrency, and
malformed-input checks at `docs/REPAIR_PLAN.md`, then the complete repository
gate, one whole-phase `xhigh` confidence review, and one separate whole-phase
`xhigh` adversarial audit.

---

## Phase 6 — Qualification and Release Evidence

**Why now:** A build can be engineering-green while producing poor or wrongly
bound credit conclusions. Qualification measures the exact shipped route,
provider/model, adapter, bundle, evidence, and answer keys before advertising
it.

**Consumes:** Accepted Phase 5 application and immutable deliverable chain.

**Produces:** One current authenticated qualification verdict and complete
release evidence for each route actually enabled; all other routes remain
unqualified or disabled.

**Primary references:** `docs/REPAIR_PLAN.md`,
`docs/DECISIONS.md` §§23–25, `server/qualification/`,
`tests/test_qualification_matrix.py`, `tests/test_qualification_on_disk.py`,
and `tests/test_orchestration_proof.py`.

### Task 6.1: Validate the Entire Qualification Set Before Spend

**Files:** `server/qualification/matrix.py`,
`server/qualification/on_disk.py`, `server/qualification/harness.py`,
`tests/test_qualification_matrix.py`, `tests/test_qualification_on_disk.py`,
and `tests/test_qualification_harness.py`.

- [ ] Write REDs for duplicate cases/keys, path escape, malformed/extra fields,
      missing documents, wrong route/selection/source-set/extractor/bundle/
      adapter/provider/model, and manifest changes after preparation.
- [ ] Validate and digest the complete set and every answer key before any
      reservation or provider call. Do not validate cases lazily after spend.
- [ ] Bind performed evidence to exact accepted runs/artifacts and preserve
      unrun/refused/indeterminate outcomes without converting them to success.
- [ ] Prove different in-memory/on-disk representations of the same declared
      set digest identically and different bytes never do.

**Task acceptance:** Any invalid or mismatched set fails before spend; every
performed row remains explainable and immutable.

### Task 6.2: Add Independent Credit-Conclusion Answer Keys

**Files:** `server/qualification/matrix.py`, qualification-set manifests and
documents, `tests/test_qualification_matrix.py`, and
`tests/test_orchestration_proof.py`.

- [ ] Extend the closed answer-key contract with independently checked values,
      period, unit, perimeter, scenario, required gaps/limitations, refusal
      expectations, and readiness/QA outcomes.
- [ ] Write cases proving a located quote with the wrong amount/unit/perimeter
      fails, while an expected restriction/insufficient-evidence refusal passes
      only its declared expectation.
- [ ] Keep deterministic calculations separate from source facts and analyst
      judgments. Never use model-authored balancing figures as answer keys.
- [ ] Add one real PDF case and one deliberately restricted case through the
      production-built UI path.

**Task acceptance:** Citation presence alone cannot qualify an incorrect credit
conclusion; declared limitations and refusal semantics are measured.

### Task 6.3: Bind and Persist the Current Review Verdict

**Files:** `server/qualification/verdict.py`, the smallest owning store/API
module, qualification UI wire/view files, `tests/test_qualification.py`, and
`tests/test_api_routes.py`.

- [ ] Write REDs for future, expired, naive-time, wrong-reviewer, wrong-set,
      wrong-build/adapter/model/provider, and changed performed-evidence
      verdicts.
- [ ] Persist an authenticated review decision over the exact frozen performed
      evidence and its digest. Recheck `decided_at <= now < expires_at` and all
      identities at read/use time.
- [ ] Display `UNQUALIFIED`, `RESTRICTED`, and `UNAVAILABLE` honestly; never
      reuse a broader or older verdict for a narrower/different build.

**Targeted prompt:** `ultrathink: Trace qualification identity from on-disk
manifest through prepared/performed rows, reviewer decision, persisted verdict,
UI label, and release evidence. Find any time-of-check, timezone, or substituted
run/model/adapter path that can display QUALIFIED for different evidence.`

**Task acceptance:** Only a current authenticated verdict over the exact
performed build can produce `QUALIFIED`.

### Task 6.4: Prove Recovery and Assemble Release Evidence

**Files:** `.github/workflows/ci.yml`, `docs/CI_GATE_CONTRACT.md`,
`docs/MIGRATIONS.md`, release documentation, migration/restore probes, and
production smoke/qualification tests. Change CI only when a new check arrives
with the code it scans; never loosen an existing gate.

- [ ] Run complete engineering, authorization, concurrency, recovery,
      accessibility, image, and production journey gates with no unexplained
      skip.
- [ ] Restore database and matching blobs into new empty locations; verify
      migrations, digests, accepted artifacts, receipts, worker recovery, and
      qualification under the same application revision.
- [ ] Record exact commit/image/bundle/adapter/provider/model/qualification-set
      identities, test outputs, verdict dates, migration history, backup/restore
      evidence, rollback procedure, and disabled routes.
- [ ] Inspect hosted required checks/settings read-only against the exact future
      PR head when authorized. Local output never substitutes for GitHub or
      Sonar status.

**Task acceptance:** Release evidence is complete and reproducible without
rewriting checksums, weakening gates, or interpreting newer data with older
code.

### Task 6.5: Run Capped Live Qualification Only When Authorized

**Files:** Existing live-provider harness/tests and the frozen qualification
set. No production code change belongs in this task unless a separately
reproduced defect requires its own TDD slice.

- [ ] Obtain explicit authorization for provider, model, route set, maximum
      calls/tokens/cost, and execution window. Without it, leave this task
      blocked and all affected routes unqualified.
- [ ] Run every advertised route through the same production worker,
      validation, billing, acceptance, and UI path used by deterministic tests.
- [ ] Record known and indeterminate spend, performed evidence, failures, and
      the authenticated reviewer verdict without exposing credentials or source
      text in logs.

**Phase 6 exit:** Every F01–F18 item links to verified remediation or an
explicitly disabled affected feature; real PDF/restricted journeys and restore
proof pass. Complete the repository gate and the two `xhigh` whole-phase
reviews. After remediation, verify hosted checks on the final authorized
candidate and an unexpired live-qualification verdict for that same identity.
If review changes invalidate the qualified candidate, repeat affected
qualification within the authorized spend scope or leave release acceptance
blocked. Never attach an older verdict to a repaired build.

## Final Verification Checklist

- [ ] No task started before its predecessor phase was accepted.
- [ ] Every phase brief records exact bases, paths, APIs, REDs, sizes, commands,
      and ordinary review evidence from the current checkout.
- [ ] Concurrent implementers had isolated worktrees/resources and disjoint
      ownership; the coordinator reviewed and integrated their exact commits
      before any task or phase acceptance.
- [ ] No `claims-json-v1` artifact is described as canonical Markdown.
- [ ] No fixture/demo, provider claim, browser digest, detached hash, latest-row
      query, or stale worker becomes authority.
- [ ] `low`, `medium`, targeted `ultrathink`, initial-blueprint-only `max`,
      and phase-code-review-only `xhigh` followed the reasoning table;
      actual checkpoint settings were recorded.
- [ ] No rewrite tournament ran.
- [ ] Full local gates and both phase reviews are attached to each accepted
      phase; hosted checks are attached only to their exact authorized head.
- [ ] Unqualified, restricted, unavailable, and disabled capabilities are
      presented honestly.
