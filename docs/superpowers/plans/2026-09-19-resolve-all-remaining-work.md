# CAOS v2 — resolve all remaining work

Date: 19 September 2026
Execution branch: `completion/owner-decisions`
Plan baseline: `ad19d1262f7fd2a7a8d612fd95c845017b011224`

This is the delta plan from the current checkpoint to programme closeout. It
does not reopen accepted work in `docs/REPAIR_PLAN.md`, renumber the completion
phases, or replace `docs/CLAUDE_CODE_HANDOFF.md` as the status record. It turns
the work that became available after the 19 September evidence tranche into an
executable order.

The target outcome is:

1. all eighteen catalog pathways have deterministic, source-grounded
   whole-route contracts and are in `ADAPTER_ROUTES`;
2. every pathway has either an immutable offline qualification set or an
   explicit, evidence-based reason why no honest set can yet exist;
3. every set selected for paid execution is exercised under one pinned
   provider identity and dated price, with its performed evidence retained;
   any eligible set left unrun carries the evidence-based stop reason and
   needs fresh authorization; only an authenticated human reviewer may sign a
   qualification verdict;
4. the release pack states `QUALIFIED`, `NOT_QUALIFIED`, or `UNVERIFIED`
   truthfully for every enabled pathway;
5. the separate delivery task lands the local commits through reviewed PRs,
   resolves CI and SonarCloud, and performs final fast-forward synchronization.

No public filing, model output, or coordinator-authored prose may substitute
for private portfolio facts or a genuine pre-outcome decision record.

## Non-negotiable execution rules

- The implementation task never pushes, opens, updates, merges, or closes a
  pull request. It commits local checkpoints and sends exact commit ranges to
  the separate delivery task.
- `/Users/ericguei/Documents/caos-v2` remains read-only until final closeout.
  No force push, reset, destructive checkout, or direct merge from a
  `completion/*` branch is a synchronization strategy.
- Before changing a function, class, method, or constant, run GitNexus
  upstream impact analysis. Warn before changing a HIGH or CRITICAL target.
  Run `detect_changes(scope="compare", base_ref="main")` before every local
  commit.
- Run `rewrite-tournament` only when GitNexus identifies a changed area as
  HIGH or CRITICAL. It is not a routine post-edit gate.
- Run `confidence-review` only at a phase end, in a separate agent. Every
  Astra review—targeted, phase-end, or final—also runs in a separate agent.
- Keep the smallest root-cause change. Reuse the route fixtures and production
  APIs already present; do not add a framework, dependency, or speculative
  abstraction.
- Route enablement is not qualification. Green deterministic tests never
  become a claim that a live model, issuer, or pathway is qualified.

## Model and reasoning plan

This plan applies `docs/GPT_MODEL_REASONING_MATRIX.md` to the full available
portfolio rather than treating two source roles as a two-model allow-list.

| Work | Model / effort | Session rule |
|---|---|---|
| Main orchestration, dependency decisions, plan updates | `gpt-6-astra` / `high` | main window |
| Literal route censuses, formatting, generated register updates | `gpt-5.6-luna` / `low` | bounded implementation agent |
| Ordinary route fixtures, qualification manifests and tests | `gpt-5.6-terra` / `medium` | default implementation agent |
| Money, provider identity, qualification evidence and verdict binding | `gpt-5.6-sol` / `high` | reliability-critical agent |
| Phase confidence review | `gpt-5.6-sol` / `xhigh` | separate review agent only |
| Independent phase adversarial audit and final all-phase review | `gpt-6-astra` / `xhigh` | separate review agent only |
| Auth, secrets, TLS, CI security or dependency findings | `gpt-daybreak-blue-latest` / `high` or `xhigh` | defensive-security work only |
| Compatibility or deliberate independent baseline | `gpt-5.5` / `high` | use once only when a previous-generation view adds evidence |
| PR construction and ordinary Sonar remediation | `gpt-5.6-terra` / `medium`; raise to `gpt-5.6-sol` / `high` for invariant-sensitive faults | separate delivery task only |

No dispatch uses `max`, `ultra`, or `ultrathink`; `xhigh` is the ceiling.
Record the actual model and effort in every formal checkpoint.

## Phase 0 — documentation discovery and allowed interfaces

### Sources read

- Current authority and checkpoint: `docs/CLAUDE_CODE_HANDOFF.md:1-198` and
  its Task 11 records at `docs/CLAUDE_CODE_HANDOFF.md:1582-1770`.
- Completion outcomes and gates: `docs/COMPLETION_PLAN.md:478-1009`.
- Copy-ready task templates: `docs/superpowers/plans/2026-09-17-completion-complementary-plan.md:301-906`.
- Model routing: `docs/GPT_MODEL_REASONING_MATRIX.md:26-65`.
- Evidence status: `qualification/DOCUMENTS.md:37-168`.
- Route declaration and allowlist: `server/engine/route.py:174-220` and
  `server/methodology/handoff.py:67-90`.
- Existing fixture seams: `tests/canonical_route_fixtures.py:69-103,
  396-515`, `tests/cp3c_route_fixtures.py:518-776`, and
  `tests/full_assessment_route_fixtures.py:108-313`.
- Live qualification and release interfaces: `scripts/qualify.py:233-315` and
  `scripts/release_pack.py:370-410`.

Historical rebuild status, old unchecked task boxes, and stale
`docs/feature-status.csv` rows are evidence of prior intent, not current state.

The discovery pass also corrects two stale checkpoint claims. The Spirit
distressed pack is now in the dirty worktree, so Task 11.9 is no longer
corpus-blocked. And `qualification/vmo2-fy2025-deep-research/RESULT.md` records
one owner-signed verdict over build `78c24be4`. It is historical signed
evidence; because the bundle still names that build, its currency for this
later tree can be established only by reading the retained qualification store
through `current_verdict` at an explicit as-of time, not from the repository
tree alone. All other enabled pathways remain unsigned or otherwise not
qualified.

### Allowed APIs and patterns

| Need | Existing interface to copy |
|---|---|
| Resolve exact nodes and typed edges | `resolve_route(catalog, profile_id, selection_id, *, extensions=None, predicates=None)` in `server/engine/route.py:174` |
| Admit a route to production execution | the closed `ADAPTER_ROUTES` set in `server/methodology/handoff.py:69` |
| Generic selection-aware deterministic handoffs | `route_identity(..., selection=...)`, `canonical_markdown(...)`, and `RouteCompletions(..., selection=...)` in `tests/canonical_route_fixtures.py` |
| CP-3C plus LITE route handoffs | `route_markdown(..., selection=...)` and `RefinancingCompletions(..., selection=...)` in `tests/cp3c_route_fixtures.py` |
| Wide FULL-module dispatch | `route_markdown` and `FullAssessmentCompletions` in `tests/full_assessment_route_fixtures.py`; parameterize this seam rather than duplicating thirteen modules |
| Whole-route acceptance | copy the complete/proof/freeze/block pattern from `tests/test_market_dislocation_route.py:34-159` and the wide route harness from `tests/test_full_credit_assessment_route.py:38-125` |
| Load immutable on-disk sets | `load_qualification_set(root)` in `server/qualification/on_disk.py:130` |
| Paid execution | `scripts/qualify.py <set> --expect-identity <identity> --ceiling <decimal> [--attempts N] [--capture path]` |
| Release truth | `make release-pack`, or `STORE=1 AS_OF=<offset timestamp> make release-pack`, backed by `scripts/release_pack.py` |
| Complete local gate | `make check`, whose ordered targets are declared in `Makefile:125-136` |

### Anti-pattern guards

- Do not add a second route resolver, fixture hierarchy, evidence parser, or
  qualification driver.
- Do not copy a full fixture per route when a selection parameter closes the
  difference.
- Do not enable a route before its own exact whole-route test passes.
- Do not derive answer keys from a run, relax a key after seeing output, or
  admit `ANSWER_KEY_3ISSUER.md` as evidence.
- Do not reconstruct `ccl-decision-record` after the fact or invent
  `ccl-portfolio-mandate-exposures`.
- Do not claim FINRA's last trade is a bid, mid, evaluated price, spread, or
  curve. A market result using it must retain that limitation.
- Do not treat a green gate, a complete snapshot, or an unsigned matrix as a
  signed qualification verdict.

Phase 0 is complete when this plan is committed and the handoff links to it.

## Phase 1 — finish deterministic coverage for all eighteen routes

The committed baseline has thirteen enabled pathways. The dirty worktree
already contains the evidence-register tranche, a CCL covenant/refinancing
set, selection-aware fixture work, and the first pass of
`MARKET_DISLOCATION` and `LITE_COVENANT_REFINANCING`. Preserve and verify that
work; do not restart or reset it.

### 1.1 Stabilize the in-progress market route

Files: `tests/canonical_route_fixtures.py`,
`tests/test_market_dislocation_route.py`, `server/methodology/handoff.py`, and
the exact route-census tests.

- Finish the selection-aware generic fixture already present.
- Prove the exact `CP-0 -> CP-3D` REQUIRED edge, request ceiling,
  source-grounded citation, FULL projection, block behavior, orchestration
  proof, and save/sign/freeze/verify.
- Keep the test corpus deterministic. The real FINRA observation belongs to
  Phase 2, not this fixture.
- On green tests, the census is 14 enabled / 4 disabled.

### 1.2 Finish `LITE_COVENANT_REFINANCING`

Files: `tests/cp3c_route_fixtures.py`,
`tests/test_lite_covenant_refinancing_route.py`,
`server/methodology/handoff.py`, and the route censuses.

- Complete the existing selection parameter instead of creating a second
  CP-3C fixture.
- Reuse `realistic_handoff_markdown` for CP-L10 and retain the CP-3C/CP-5
  limitation through the LITE projection.
- Prove the exact four nodes and six typed edges, no-work-on-CP-0-block,
  request ceiling, proof, and freeze.
- On green tests, add the route to `ADAPTER_ROUTES`; census 15 / 3.

### 1.3 Make the wide fixture selection-aware once

Files: `tests/full_assessment_route_fixtures.py` and its existing consumers.

- Add a keyword-only `selection` to `route_identity`, `route_markdown`, and
  `FullAssessmentCompletions`.
- Derive the route, direct upstreams, CP-0 T8 owners, expected filenames, and
  decision scope from that selection.
- Reuse the existing CP-L10 renderer for LITE identities. Do not create a new
  production helper or duplicate module Markdown.
- Keep current FULL assessment defaults byte-for-byte behaviorally compatible;
  its existing suite must stay green before adding new routes.

### 1.4 Enable `LITE_DISTRESSED_RESTRUCTURING`

- Add one route test over exactly `CP-0, CP-L10, CP-2A, CP-2H, CP-4C` and its
  eight catalog edges.
- Prove LITE scope, direct lineage, restricted limitations, source anchoring,
  request bounds, complete/proof/freeze, and no downstream work after a CP-0
  block.
- Add the route only after the test passes; census 16 / 2.

### 1.5 Enable `LITE_FULL_CREDIT_SCREEN`

- Add one route test over exactly `CP-0, CP-L10, CP-1A, CP-1C, CP-2A,
  CP-2H, CP-3C, CP-4C, CP-5` and its catalog edges.
- Prove CP-5 receives every direct advisory upstream, preserves restrictions,
  and cannot turn limited evidence into Passed output.
- Prove complete/proof/freeze, request bounds and CP-0 block behavior.
- Add the route only after the test passes; census 17 / 1.

### 1.6 Enable `FULL_CREDIT_32 / DISTRESSED_RESTRUCTURING`

- Add one route test over the exact thirteen nodes and fifty-six catalog edges.
- Reuse the wide fixture. Prove CP-5's QA_GATE behavior for CP-6: Passed
  releases it; Restricted or Blocked creates no CP-6 attempt or reservation.
- Prove every direct upstream identity, request ceiling, orchestration proof,
  canonical freeze, and block behavior.
- Add the route last. Replace the obsolete adapter-owned-disabled test with a
  catalog census proving `ADAPTER_ROUTES` equals all 18 declared pathways;
  census 18 / 0.

### Phase 1 verification and freeze

1. Run focused fixture/route tests, first without and then with the configured
   PostgreSQL test service so no integration test is merely skipped.
2. Run every route-census and disabled-route test; grep for stale `(14, 4)`,
   `(15, 3)`, `(16, 2)`, and `(17, 1)` literals.
3. Run `make check` once over the integrated tree.
4. Run a separate `gpt-5.6-sol` `xhigh` confidence review; remediate and rerun
   the affected checks.
5. Refresh GitNexus, then run a separate `gpt-6-astra` `xhigh` adversarial
   audit; remediate and reverify.
6. Run GitNexus `detect_changes` against `main`, commit the phase locally, and
   send only the exact range and instructions to the delivery task.

## Phase 2 — complete the offline qualification inventory

Phase 2 never calls a provider. It turns the 29 in-hand documents into
immutable cases and records the two facts that remain outside the repository.

### 2.1 Audit the existing twelve sets

- Load every committed `qualification/*/qualification.json` with
  `load_qualification_set` and verify its digest, copied documents, subject,
  route identity, projections, readiness keys and unique citation anchors.
- Keep keys authored from the source documents. A correction to a key changes
  the set digest and invalidates comparison with earlier runs.
- Reconcile each `RESULT.md` with the manifest: `OFFLINE`, `UNVERIFIED`, live
  capture, and signed verdict are distinct states.

### 2.2 Add the public-evidence sets now possible

Create the smallest independent set directory for each route; copy admitted
documents byte-for-byte because the loader refuses paths outside the set root.

| Route | Evidence and intended boundary |
|---|---|
| `MARKET_DISLOCATION` | CCL 10-K plus the governed FINRA observation; expect a restricted market conclusion because the observation is last-trade-only |
| `LITE_COVENANT_REFINANCING` | CCL 10-K, 2025 revolver and 5.75% notes indenture; key CP-L10/CP-3C/CP-5 without erasing legal or market gaps |
| `LITE_FULL_CREDIT_SCREEN` | CCL 10-K, CCL debt documents, Fitch action, RCL and NCLH releases; key only cells those documents establish |
| `LITE_DISTRESSED_RESTRUCTURING` | Spirit 8-K and RSA/Plan; if CP-0 cannot clear a demanded owner, key the exact blocked readiness rather than inventing it |
| `DISTRESSED_RESTRUCTURING` | the same Spirit pack; record the honest missing financial/rating/covenant inputs through `expects_blocked` or restricted projections |
| `RELATIVE_VALUE` under FULL | CCL 10-K, debt terms, FINRA observation and peer releases; market limitations remain explicit |
| `PORTFOLIO_DECISION` and `FULL_CREDIT_ASSESSMENT` | prepare public-evidence cases only if CP-0 can deterministically express the missing private portfolio input; otherwise leave the route `NOT_QUALIFIED` with the register reason |

For each new set:

- verify every `matched_text` is exact and uniquely anchorable in an admitted
  document;
- prefer projection/register/readiness keys over citation-only keys when they
  measure the analytical conclusion;
- state any expected refusal or block before a run;
- add the set digest to `tests/test_qualification_on_disk.py`;
- update `qualification/documents.json` and regenerate the committed table via
  `scripts/document_register.py --report`;
- never claim that the set has run.

### 2.3 Resolve the three owner-only inputs without fabrication

1. `ccl-portfolio-mandate-exposures`: the owner supplies current holdings,
   limits, mandate and proposed-position inputs, or explicitly records that
   they are unavailable. Until supplied, portfolio/full-assessment live
   qualification remains `NOT_QUALIFIED`.
2. `ccl-decision-record`: accept only a genuine, dated T0 record written before
   the measured outcome period. If none exists, both decision-ledger routes
   remain enabled but `NOT_QUALIFIED`; do not create a retrospective memo.
3. `cp-dr-research-brief`: obtain owner confirmation of the existing
   supplied-only questions and keys. If not confirmed, retain the sets as
   unconfirmed offline fixtures and do not sign a verdict over them.

An explicit “not available” closes planning ambiguity but does not turn the
affected route into a qualified one.

### Phase 2 verification and freeze

- `python3 scripts/document_register.py --report` matches the committed table.
- All on-disk set, digest, vocabulary and qualification tests pass.
- Run `make check` if Phase 2 changes anything outside documents and test data;
  otherwise run the complete relevant offline gate plus `git diff --check`.
- Separate Sol/xhigh confidence review, remediation, then separate
  Astra/xhigh adversarial review and re-verification.
- Run GitNexus `detect_changes`, commit locally, and hand the exact range to
  the delivery task.

## Phase 3 — pin the provider, price and spend envelope

This phase is owned by `gpt-5.6-sol` at `high` because a wrong identity or
price can spend money on evidence that cannot support a verdict.

1. Read the currently configured provider, exact model identifier, endpoint
   tag and reasoning effort without printing secrets.
2. Verify the model identifier and dated input/output price against the
   provider's current official documentation. Record the URL, access date and
   conservative `CAOS_MODEL_PRICE`; never infer a price from a prior run.
3. Run `make doctor` and `make check-postgres`. Use a persistent database via
   `CAOS_QUALIFY_POSTGRES_URL`, never the ephemeral test database.
4. Compute each set's ceiling from the recorded worst-case per-call price,
   route node count and bounded retry allowance. The ceiling is derived, not a
   round-number guess.
5. Pin the exact identity in `--expect-identity`. If environment resolution
   differs, stop before spend as `scripts/qualify.py` already does.
6. Store each JSON capture beside its `RESULT.md` or at the governed location
   that file names; record database and blob-root identifiers without secrets.

The GPT development matrix does not invent an OpenRouter model slug. Use the
provider's actual supported identifier discovered at execution time and record
why it is the qualification model.

## Phase 4 — run, classify and review every eligible set

Run the smallest routes first, then the widest, so host/provider defects are
found before an expensive nineteen-node run.

1. LITE portfolio and earnings baselines.
2. LITE relative value and both deep-research profiles after brief
   confirmation.
3. FULL liquidity, earnings, market and covenant/refinancing.
4. LITE covenant, LITE distressed and LITE full-credit screen.
5. FULL relative value and distressed restructuring.
6. Portfolio decision and full credit assessment only after the private
   portfolio input exists.
7. Decision-ledger routes only after a genuine T0 record exists.

For every run:

- invoke `scripts/qualify.py` with the exact identity, derived ceiling,
  bounded `--attempts`, and `--capture`;
- retain complete and blocked results alike; a supported expected block is a
  measurement, not a failed excuse;
- compare citations, projections, registers, readiness and refusal against
  the pre-run keys;
- if a key is wrong, fix it from the source, mint a new set digest and rerun;
  never tune it to the model's answer;
- if a host defect is found, return to implementation, test the root cause,
  invalidate the candidate, and repeat the phase gate;
- if only the model missed a valid key, record the miss without weakening the
  contract.

An authenticated human reviewer decides and signs a verdict through the
existing qualification API. The implementation agent may prepare the evidence
and recommendation but never impersonates that reviewer. A route without a
current signed verdict remains `NOT_QUALIFIED`.

### Phase 4 verification and freeze

- Re-read every retained run from its persistent database and blob root.
- Confirm the recorded provider/model identity equals the runs' call outcomes.
- Emit a store-backed release pack at a fixed offset-aware `AS_OF` and verify
  that only signed, current verdicts say `QUALIFIED`.
- Run the full local gate, then the separate Sol/xhigh confidence review and
  separate Astra/xhigh adversarial audit with remediation between them.
- Commit only source, tests, immutable set/capture records and status docs;
  never credentials or mutable database files.

### Phase 4 outcome — stopped by evidence, 20 September 2026

The two smallest smoke sets ran under the pinned Sol/high identity, then each
received the owner's one-attempt Sol/xhigh retry. CCL again stopped at CP-0 on
a model-contract contradiction. VMO2 completed both nodes but missed its
unchanged citation key, so its performed snapshot remained incomplete. The
combined retry reserved `$8.365320` and charged `$1.3507305`.

The separate Sol/xhigh confidence review and separate Astra/xhigh adversarial
audit reproduced the classifications and found no host, parser, provider,
source-delivery, or answer-key defect. Phase 4 therefore stops without wider
spend. The remaining eligible sets were not run in this Sol campaign and
require a new owner decision before any later provider call. Their release
status remains store-derived: the earlier owner-signed LITE deep-research
verdict is still current at the Phase 5 census time; the other seventeen
pathways are `NOT_QUALIFIED`. This is the approved early-stop outcome, not a
claim that every set ran.

## Phase 5 — reconcile documentation and release truth

- Update the top checkpoint in `docs/CLAUDE_CODE_HANDOFF.md` from measured
  facts, not earlier plan prose.
- Reconcile stale phase statements in `docs/COMPLETION_PLAN.md`, the
  complementary plan and `docs/feature-status.csv`. Preserve historical
  claims as historical; do not rewrite accepted evidence.
- Record an 18/18 deterministic route census and, separately, the current
  `QUALIFIED`/`NOT_QUALIFIED` route census.
- Regenerate the release pack twice into two temporary directories and verify
  byte equality before replacing the ignored emitted pack. The pack remains
  uncommitted under `docs/DECISIONS.md` §94.
- Record every intentional limitation: private data unavailable, no genuine
  T0 record, unconfirmed research brief, restricted market observation, or
  live model miss.

Phase 5 ends with one complete `make check`, separate Sol/xhigh confidence and
separate Astra/xhigh adversarial reviews, remediation, `detect_changes`, and a
local commit handed to the delivery task.

## Phase 6 — delivery, final review and synchronization

The separate delivery task owns this phase's GitHub actions.

### Delivery task

- Receive exact local commit ranges and dependency order from this task.
- Create isolated delivery branches/worktrees from the current GitHub base;
  split each PR at a coherent test-backed boundary and keep the hosted size
  gate at or below 800 counted lines unless the repository's documented
  indivisible exception is actually met.
- Push, open and update PRs; resolve conflicts, required CI and SonarCloud
  findings; merge only when the required checks are green.
- Never weaken a ruleset, suppress a real Sonar finding, or treat a local test
  as hosted evidence.
- Report merged commit identities and remaining failures to the implementation
  task. The main implementation window performs none of these operations.

### Final programme gate

1. Verify every planned local commit is represented in the accepted GitHub
   tree and every delivery PR is merged or deliberately closed with a reason.
2. Run the complete local gate against the accepted tree and regenerate the
   release pack from the retained qualification store.
3. Run one separate Sol/xhigh final confidence review; remediate and retest.
4. Run one separate Astra/xhigh review across all completion phases; remediate
   and repeat every affected gate. This is the single final cross-phase Astra
   review, not a main-window self-review.
5. Have the delivery task fast-forward the workbench `main` from the verified
   GitHub remote. Only after tree equality is proven may it fast-forward the
   read-only original checkout's `main` from its GitHub `origin/main`.
6. Stop on a dirty checkout, non-fast-forward result, open delivery PR,
   required red check, release-pack mismatch, or unresolved qualification
   status. Do not repair closeout with force or reset.

## Completion checklist

- [ ] 18/18 catalog pathways are in `ADAPTER_ROUTES` and each has its own
      exact deterministic whole-route test.
- [ ] No PostgreSQL-dependent route proof passed only by being skipped.
- [ ] Every document row and digest agrees with the generated register.
- [ ] Every route has an offline set or an explicit owner-input reason.
- [ ] Every paid set has a retained performed capture under one exact, dated
      provider identity and price; every unrun eligible set has the explicit
      early-stop reason and fresh-authorization requirement recorded.
- [ ] No owner fact, mandate exposure, decision record, market datapoint or
      qualification verdict was fabricated.
- [ ] Every `QUALIFIED` label is backed by a current signed verdict; all other
      enabled routes say `NOT_QUALIFIED` or `UNVERIFIED`.
- [ ] Phase confidence and Astra adversarial reviews ran only in separate
      agents at phase ends.
- [ ] Rewrite tournament ran only for a GitNexus HIGH/CRITICAL changed area,
      or the checkpoint records that no such area was changed.
- [ ] All local commits were handed to the separate delivery task; this task
      performed no PR operation.
- [ ] Required hosted checks and SonarCloud are green on the merged tree.
- [ ] Workbench and original `main` end at the verified GitHub commit by
      fast-forward only, and the final handoff records both commit IDs.
