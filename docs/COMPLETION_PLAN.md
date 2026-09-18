# CAOS v2 — completion review and plan

Reviewed 17 September 2026. Target: `/Users/ericguei/Documents/caos-workbench`
on `codex/execute-repair-plan` at `e59ad7b`.

> **Standing.** This plan follows [`REPAIR_PLAN.md`](REPAIR_PLAN.md), whose
> Phases 0–6 are accepted (`docs/DECISIONS.md` §62, §69) and whose file is
> not edited by this review. It inventories what the repair left outstanding
> and sequences the remaining work as Phases 7–13, with the deployment of the
> remaining modules and pathways — their corpus and their answer keys — at the
> centre, because that is the handoff's stated next task. The numbers continue
> the repair plan's; they are **not** the historical rebuild labels
> (`CLAUDE.md`'s "Phase 7–10" ledger headings). A ledger entry written under
> this plan says "Completion Phase N". `docs/CLAUDE_CODE_HANDOFF.md` stays the
> sole task/checkpoint record; the complementary task breakdown and the
> Opus 5 / Fable 5.1 routing are in
> [`superpowers/plans/2026-09-17-completion-complementary-plan.md`](superpowers/plans/2026-09-17-completion-complementary-plan.md);
> the launch text is [`PHASE_7_ONWARDS_GOAL_PROMPT.md`](PHASE_7_ONWARDS_GOAL_PROMPT.md).
>
> **Concurrent stream.** The audit remediation
> ([`superpowers/plans/2026-09-17-audit-remediation.md`](superpowers/plans/2026-09-17-audit-remediation.md),
> Tasks T1–T20, decisions D1–D3) is already underway in its own SDD worktrees
> and is **not** a task of this plan. This plan records its state where
> observed, names the tasks here that depend on its outputs, and keeps its
> phase close separate.

## Recommendation

Deploy the remaining modules and pathways, and build only what that needs.

The repair delivered one governed credit journey end to end and a
qualification apparatus that produced one `complete` snapshot on the current
build. Of the catalog's eighteen pathways, two execute (`LITE_EARNINGS_UPDATE`
and `RELATIVE_VALUE`), one has a complete live snapshot, none has a signed
verdict, and sixteen refuse `HANDOFF_MODULE_UNSUPPORTED` before any attempt.
Twelve of the twenty-three catalog modules the pathways use are proven to the
Phase 3 standard; eleven are not. That is the work: for each pathway, prove
its unproven modules' canonical contracts deterministically, assemble the
documents its modules demand, author its answer keys from those documents
before any run, enable the route, and — when the owner authorizes the spend —
run it live and sign the verdict.

Around that programme, five smaller groups, in the order the programme needs
them:

1. **The record and the delivery** (Phase 7). The branch is 351 commits ahead
   of GitHub `main` and the ledger carries entries later decisions closed.
2. **The qualification instrument** (Phase 8). Keys that measure what a module
   concluded, not which quotes it drew; a price recorded with the reservation;
   a verdict that must name a model the runs used; the corpus register; and
   the four bundle-side change requests the programme cannot proceed without.
3. **The LITE pathways** (Phase 9): four can be deployed on the current bundle;
   three wait on LITE producer modules the vendor specifies but does not ship.
4. **Route semantics for large evidence** (Phase 10). Two of the three public
   10-K texts in hand exceed the request ceiling whole; the FULL pathways need
   per-node evidence selection before they can run on real filings.
5. **The FULL pathways** (Phase 11), then **the workbench's missing writes and
   Book** (Phase 12), then **concurrency, durability, the trusted edge and the
   release pack** (Phase 13).

Live spend, bundle edits, dependency additions, pushes and deploys remain
individually authorized. This document is a review and plan, not a claim that
any item is done. No source, dependency, branch, remote or database was
changed by it.

## 1. Baseline and verification

### Exact baseline

| Identity | Value |
|---|---|
| Branch / commit | `codex/execute-repair-plan` @ `e59ad7b` (docs: Phase 6 signed off, §69) |
| Working tree | clean except untracked `AGENTS.md`, `gemini-audit.md`, `PATHFINDER-2026-09-15/`, `.claude/skills/`, and the two remediation documents below |
| Bundle build | `30222a494a5a1035c7955cb1ccfbe0b3b0fbbfa7d6426930f5dcf4d35aa1fc18` (§63) |
| Verified manifest (`DEPLOY_V_INTEGRITY_v1.json`) | `8ccc8ed035745b5fb3a18d1176f0bfbbbc2c7e337357bbf25828c3611f3d110e` |
| Bundle overrides | §61 (two edits), §63 (one edit); upstream `EricMG13/Deploy-V@c4d2e356` carries none |
| Qualification sets | `qualification/vmo2-fy2025` (`0863964b…`, two earnings releases, one complete snapshot); `qualification/ccl-fy2025` (`f5555753…`, one 10-K extract, one refused run under an unapproved model) |
| Complete snapshot | run `62308d4e-70b5-4793-abb0-7be62d2ceba6`, evidence `bb09d8d0…`, performed `d758a253…`, database `caos_qualify_5a47243d96774e088f1bfebb6271f2d1` |
| Verdicts | `qualification_verdicts` empty in every database |
| Live spend recorded | `$7.75` across eleven VMO2 runs; one CCL run (`$0.18`-class, refused at CP-0) |
| GitHub `main` | `01c3724` (PR #283), 17 September 2026. Ruleset 22701406 "main gates" is **active**. The local branch is 353 commits ahead, but the undelivered work under the size gate's own exclusions is **13,036 counted lines over 173 files**, not the 75,566 the Phase 6 checkpoint recorded or the 123,065 the split plan names: most of the branch has landed. Nine PRs are open |
| Migrations | `0001_legacy` … `0021_blocking_verdicts` |
| Enabled routes | `ADAPTER_ROUTES` = {`LITE_CREDIT_22/LITE_EARNINGS_UPDATE`, `FULL_CREDIT_32/RELATIVE_VALUE`}; `ADAPTER_MODULES` = 12 (`server/methodology/handoff.py:36-55`) |
| GitNexus | indexed as `caos-v2` (8,993 symbols, 22,700 relationships, 300 flows) at an earlier commit; refresh at Phase 7 entry |
| Remediation stream (observed 17 September) | `docs/reviews/2026-09-17-gemini-audit-adversarial-review.md` and `docs/superpowers/plans/2026-09-17-audit-remediation.md` untracked; SDD worktrees `sdd/t1`–`sdd/t6` at `/private/tmp/caos-sdd-t{1..6}`; `sdd/t1` carries `4103121` (T1, the report read holds no case lock) and `sdd/t6` carries `65f9d10` (T6, the workspace remount); `sdd/t2`–`t5` at base; plan checkboxes unticked; execution ledger `.superpowers/sdd/2026-09-17-audit-remediation/` |

### What actually ran

This review read; it did not execute a gate. The gate evidence it relies on is
the acceptance record's: a complete green `make check` at `dbb2e44` per
[`FINAL_CHECK.md`](FINAL_CHECK.md). Claims that the plan acts on were verified
in source; where the concurrent adversarial review reached the same claim, its
verdict is cited rather than repeated.

| Claim | Where | Verdict |
|---|---|---|
| A GET read takes the case write lock | `server/api/reads/reports.py:88` | **Confirmed**; the review's C1; fixed on `sdd/t1` |
| Outcome recording has three call sites | `canonical.py:212`, `runtime.py:438`, `runs.py:215` | **Confirmed as sites.** Idempotent by design; the review's W1 promotes the two extra transactions under the case lock; its T3 |
| Canonical JSON diverges on Unicode | 21 `sort_keys=True` sites, 6 with `ensure_ascii=False` | **Divergence confirmed, hazard absent** (the review's W12: every digest is produced and verified by one function); only `allow_nan` is a defect; its T14 |
| Migration 17 keys on `applied_count == 16` | `server/store/__init__.py:258` | **Refuted as a defect** by both; pinned by `tests/test_filed_receipts.py` |
| `/api/health` is "not built" | `docs/feature-status.csv` | **Stale**; served since §53.8 |
| The catalog carries CONDITIONAL edges | `CREDIT_OS_V_MODULE_CATALOG_v2.json` profile edges | **No.** 60 REQUIRED, 26 OPTIONAL, 29 ADVISORY, 1 QA_GATE, 0 CONDITIONAL |
| The pinned research brief reaches CP-DR | `server/` | **No.** `RunInput.research_json` is pinned and validated (`run_inputs.py:195`); nothing under `server/methodology/` reads it; `RouteExtensions(research_brief=…)` is built only by tests |
| The 10-K texts in hand fit the request ceiling | `MAX_REQUEST_BYTES = 1_048_576` | CCL 304,600 bytes fits; BA 1,105,000 and F 1,830,000 do not, whole |

Not performed: live qualification, a fresh vulnerability scan, hosted check
inspection, production boot.

## 2. Where the system stands

### Served and enabled

`server/api/`: one health document; section reads for Directory, Upload, Run,
Analysis, Model, Report and Committee; the case event stream; an authorized
evidence page; nine governed commands (`CREATE_CASE`, `ADMIT_SOURCES`,
`CREATE_RUN`, `PIN_RUN_INPUT`, `APPROVE_SOURCE_SET`, `APPROVE_RESEARCH_PLAN`,
`START_RUN`, `RETRY_RUN`, `CANCEL_RUN`); and one account-wide command, the
qualification verdict (§65). Seven of nine sections enabled; Book and Admin
unavailable. Every arrow below is real; the gaps are in "every block" (nothing
selects less) and "(verdict)" (a route nobody has called).

```text
Browser ↔ edge (token) ↔ API ↔ PostgreSQL + blobs ↔ one leased worker
                                     ↓
                verified bundle bytes + exact upstream records + every block
                                     ↓
                    canonical Markdown → vendor validators → host record
                                     ↓
        accepted artifact → proof → matrix → performed snapshot → (verdict)
```

### The module and pathway inventory

The catalog's two profiles define eighteen pathways over twenty-three modules
plus the host's CP-CF extension; 101 module calls in total. Proven means: a
deterministic fixture handoff validates through the vendor validators, carries
host identity with every direct upstream ref, projects, anchors every
citation, keeps limitations when Restricted, and refuses a missing register, a
wrong upstream digest and an unanchored quote (`tests/test_owner_contracts.py`,
the Task 5.2a standard).

| Module | Name | Proven | Where |
|---|---|---|---|
| CP-0 | SourceReadiness | yes | LITE earnings, RELATIVE_VALUE |
| CP-L10 | LiteFinancialChangeScreen | yes | LITE earnings |
| CP-5 | EvidenceTraceValidator | yes | LITE earnings |
| CP-1, CP-1C, CP-2, CP-2A, CP-2G, CP-3, CP-3D, CP-4 | the RELATIVE_VALUE owners | yes | `tests/test_owner_contracts.py`, `test_relative_value_route.py` |
| CP-CF | host forecast extension | yes | `tests/test_forecast_*.py` |
| CP-1A | BusinessTransactionFactPack (22 registers) | **no** | — |
| CP-1B | EarningsDelta (15) | **no** | — |
| CP-1D | EarningsQuality (13) | **no** | — |
| CP-2D | LiquidityCashFlowBridge (8) | **no** | — |
| CP-2E | MacroFXHedgingSensitivity (17) | **no** | — |
| CP-2H | RatingTransitionCase (10) | **no** | — |
| CP-3C | RefinancingLMERisk (11) | **no** | — |
| CP-4C | RestructuringScenario (10) | **no** | — |
| CP-6 | ICDebateChallenge (8); the only QA_GATE consumer | **no** | — |
| CP-8 | DecisionLedgerPostMortem (8) | **no** | — |
| CP-DR | DeepResearch (3); needs a run-linked brief | **no** | — |

| Pathway | Nodes | Unproven modules | Bundle dependency | Corpus in hand | Cost at `$0.27`/call |
|---|---|---|---|---|---|
| LITE_EARNINGS_UPDATE | CP-0, CP-L10, CP-5 | none | — | VMO2 (complete snapshot), CCL (refused under DeepSeek) | `$0.81` |
| LITE_PORTFOLIO_DECISION | CP-0, CP-L10 | none | — | VMO2, CCL | `$0.54` |
| LITE_RELATIVE_VALUE | CP-0, CP-L10, CP-1C | none (CP-1C's LITE block accepts `lite_financial_change_screen`, which CP-L10 owns) | — | needs a peer table | `$0.81` |
| LITE_DECISION_LEDGER | CP-0, CP-8 | CP-8 | — | needs a decision record and a later outcome period | `$0.54` |
| LITE_DEEP_RESEARCH | CP-0, CP-DR | CP-DR + host brief delivery | — | needs a brief; supplied evidence only | `$0.54` |
| LITE_COVENANT_REFINANCING | CP-0, CP-L10, CP-3C, CP-5 | CP-3C | **CP-3C under LITE accepts only `lite_liquidity_sensitivity_screen`, `lite_market_recovery_opportunity_screen`, `lite_legal_structure_capacity_screen`; no vendored module produces them** | — | `$1.08` |
| LITE_DISTRESSED_RESTRUCTURING | CP-0, CP-L10, CP-2A, CP-2H, CP-4C | CP-2H, CP-4C | **CP-2A/CP-2H accept `lite_fundamental_credit_screen`/`lite_liquidity_sensitivity_screen`; CP-4C `lite_legal_structure_capacity_screen`; none produced** | — | `$1.35` |
| LITE_FULL_CREDIT_SCREEN | CP-0, CP-L10, CP-1A, CP-1C, CP-2A, CP-2H, CP-3C, CP-4C, CP-5 | CP-1A, CP-2H, CP-3C, CP-4C | **as above, four consumers** | — | `$2.43` |
| RELATIVE_VALUE | 9 | none | — | fixture only; needs a real issuer with facility terms and a peer/market table | `$2.43` |
| MARKET_DISLOCATION | CP-0, CP-3D | none | — | needs a dated market-data extract | `$0.54` |
| LIQUIDITY_REVIEW | CP-0, CP-1, CP-2, CP-2D | CP-2D | — | CCL 10-K | `$1.08` |
| EARNINGS_UPDATE | CP-0, CP-1, CP-1B, CP-2, CP-5 | CP-1B | — | two periods: VMO2 Q3/Q4 or CCL FY2024/FY2025 | `$1.35` |
| DECISION_LEDGER | CP-0, CP-8 | CP-8 | — | as LITE_DECISION_LEDGER | `$0.54` |
| DEEP_RESEARCH | CP-0, CP-DR | CP-DR | — | as LITE_DEEP_RESEARCH | `$0.54` |
| COVENANT_REFINANCING | CP-0, CP-1, CP-4, CP-2, CP-2D, CP-3C, CP-5 | CP-2D, CP-3C | — | CCL 10-K + its indentures (public EDGAR exhibits, not in hand) | `$1.89` |
| PORTFOLIO_DECISION | CP-0, CP-1, CP-2, CP-4, CP-3D, CP-3, CP-5, CP-6 | CP-6 (QA_GATE CP-5 → CP-6) | — | CCL 10-K + indentures + market extract | `$2.16` |
| FULL_CREDIT_ASSESSMENT | 19 | CP-1A, CP-1B, CP-1D, CP-2D, CP-2E, CP-2H, CP-3C, CP-4C, CP-6 | — | CCL pack + rating reports + hedging note; needs per-node selection | `$5.13` |
| DISTRESSED_RESTRUCTURING | 13 | CP-2D, CP-2H, CP-3C, CP-4C, CP-6 | — | **a distressed issuer, not in hand** | `$3.51` |

Corpus in hand: `qualification/vmo2-fy2025/documents/` (two Virgin Media O2
earnings releases, PDF); `qualification/ccl-fy2025/documents/CCL_FY2025_10K.txt`;
and, outside the tree, the owner's three-issuer assessment corpus at
`/Users/ericguei/Documents/Co-Pilot Agents/assessment_3issuer_20260719/corpus/`
— CCL, Boeing (`BA`) and Ford (`F`) FY2025 10-K texts with raw HTML and XBRL
company facts, and a human-authored answer key (`ANSWER_KEY_3ISSUER.md`: core
facts, derived values and 24 traps per issuer). That key is a source for
host keys; it is never an admitted document.

## 3. Outstanding items

P1 means it blocks a pathway from being deployed or a release label. P2 means
a limit accepted under a stated condition that the plan removes. P3 means
hygiene the ledger records. Each item names its phase.

### Modules and pathways

**O01 — Eleven modules have no canonical contract [P1, Phases 9 and 11].**
CP-1A, CP-1B, CP-1D, CP-2D, CP-2E, CP-2H, CP-3C, CP-4C, CP-6, CP-8 and CP-DR
are outside `ADAPTER_MODULES`; every pathway carrying one refuses before any
attempt. Each needs the Task 5.2a treatment: a realistic fixture handoff built
from the vendor's `load_contract` registers (`tests/canonical_route_fixtures.py`),
the five contract tests, and the module added to the constant in the slice
that proves it.

**O02 — Sixteen pathways are not enabled [P1, Phases 9 and 11].** Enabling a
route means every module on it proven, a deterministic whole-route run that
completes, proves and freezes (`test_relative_value_route_completes_proves_and_freezes`'s
shape), every request under the ceiling, the pair added to `ADAPTER_ROUTES`,
and the `DISABLED` guard in `tests/test_relative_value_route.py` updated so it
still asserts the exact enabled set. `tests/test_phase_exits.py` excuses one
test (`NOT_YET_REACHED`, CP-1 canonical) that comes due with
`FULL_CREDIT_ASSESSMENT`.

**O03 — Two LITE objects reach their consumer on no edge [P1 for one pathway,
bundle-side, Phase 8 request].** This item was overstated when first written and
Task 8.5 corrected it against the bundle. What is true:
`CP_DEPLOY_V_EXECUTION_PROFILES_v1.json` `retained_lite_capabilities` declares
the LITE objects CP-2A, CP-2H, CP-3C and CP-4C accept, and the catalog **does**
carry two of them on edges -- `lite_liquidity_sensitivity_screen` to CP-2H and
`lite_legal_structure_capacity_screen` to CP-4C. Only
`lite_fundamental_credit_screen` (CP-2A) and
`lite_market_recovery_opportunity_screen` reach no consumer on any edge. The
producers are not missing either: `superseded_module_ids` absorbs CP-L20,
CP-L23, CP-L30 and CP-L40 into CP-L10, whose `SKILL.md` carries each as an
absorbed phase with its own owned object, while the catalog names CP-L10 just
one `owned_object`. And `invocation.named_objects` does not hold a consumer
forever: it drops a boundary no route input can meet. So what actually holds
the three pathways is `ADAPTER_ROUTES` plus the ledger's policy that a vendor
owner must exist before a route is enabled. Repair: the request asks the vendor
to declare `accepted_object_id` on the two uncarried edges and to key CP-3C's
prose block so the host reads it; the three pathway tasks stay held in Phase 9
with their template ready.

**O04 — CP-DR cannot be invoked [P1, Phase 9].** `RunInput.research_json` is
pinned and validated to 64 KiB and read by nothing in `server/methodology/`;
`CP_DR_RESEARCH_BRIEF_V1.md` requires the run-linked brief (`mode`, `run_id`,
`cp0_sha256`, `authority_sha256`, scope, questions with
`consumer_module_id`/`after_module_id`) as a sidecar and `prepare_invocation`
to emit `research_mode`. Repair: the host renders the pinned brief as a
host-owned tagged section for CP-DR only, with `source_mode` fixed to supplied
evidence (invariant 1: web discovery is structurally absent), `cp0_sha256`
bound to the accepted CP-0 record, and the CP-DR contract proven.

**O05 — CP-8 needs a decision record the system has never produced [P1,
Phase 9].** `DecisionLedgerPostMortem` records a completed decision's
rationale, assumptions, dissent and realised outcomes (T7.1–T7.8: expected
versus realised by metric, attribution, lessons). Its only required upstream
is CP-0, so the decision record and the later outcome period are *documents*.
Repair: a corpus pair — a decision memo at T0 (a filed CAOS deliverable is the
natural one, or an owner-supplied memo) and the issuer's later filing at T1 —
with keys authored from both.

**O06 — The corpus in hand covers screening, not the FULL demands [P1,
Phase 8].** Two earnings releases and three 10-K texts cover CP-0, CP-L10,
CP-1, CP-1B, CP-1D, CP-2, CP-2D, CP-2E, CP-3C and CP-5. Not in hand, as Task
8.4's reading of each `SKILL.md` established: executed debt documents for
**CP-4**, whose step 1 is a Document Gate producing `T4F.1 Controlling
Documents` (public EDGAR exhibits for CCL, BA and F) and which CP-4C inherits;
a dated market-data extract (CP-3D, CP-3 — must be supplied as a document); a
peer pack (CP-1C, inferred from its Peer Discovery and Peer Data gates, which
name no document form); a named acquisition or sponsor transaction for
**CP-1A**, whose ownership and governance registers the CCL 10-K serves but
whose transaction registers it does not; a distressed issuer with a documented
distress gate (CP-4C, `DISTRESSED_RESTRUCTURING`); a decision record (CP-8).

Two demands this review had overstated, corrected by that reading. **CP-3C is
not blocked on EDGAR exhibits**: its runbook names the maturity and debt
schedule as the source gate, and the CCL 10-K carries the scheduled-maturities
table, so the exhibits deepen it rather than gate it. **CP-2H degrades rather
than blocking**: its Phase 1 permits methodology-only work with limitations
when current rating evidence is absent, so it can be proven `Restricted` on the
corpus in hand and only a `Passed` needs the agency documents. CP-1B, CP-1D and
CP-6 state upstream-only source gates and demand no document of their own.

Repair: the corpus register (Phase 8), sourced pathway by pathway, each
document admitted under its own digest and named in the set manifest.

**O07 — Two of the three 10-K texts cannot run whole [P1 for BA and F, Phase
10].** Boeing (1.1 MB) and Ford (1.8 MB) do not **admit**: each holds a single
token — 71,243 and 105,966 characters — and `ingest._prepare` calls
`BoundaryText.of` on every token before any line is packed, so both refuse
`BOUNDARY_TEXT_TOO_LONG` at the door. That is the first obstacle, and this
entry named the second: they would *also* exceed `MAX_REQUEST_BYTES`, because
every module is handed every block (`captured_blocks`) and
`CONTEXT_OVER_CEILING` refuses with no narrowing. Corrected after the
line-group review measured both texts on base and on the line-group branch and
found neither admits — so neither reaches a prompt for the request ceiling to
refuse. CCL (304 KB) fits. Repair, in the order the obstacles arrive: a
declared maximum token length in the extractor that produced them, since a
token that long is an extraction finding no whitespace where a reader sees
words; then per-node evidence selection from CP-0's `evidence_demand` and
`active_representation_ids`, recorded on the attempt and enforced by every
reader; a per-section bound and one recorded narrowing step. The line group's
splitting half is built and moves neither document (CLAUDE.md, Phase 2). Until
then the FULL pathways run on CCL and on curated extracts.

**O08 — Keys measure citations, readiness and seven projected scalars, not
registers [P1, Phase 8].** `ExpectedCitation`, `expects_ready`,
`ExpectedProjection` over `PROJECTION_FIELDS` (`qa_status`,
`committee_status`, `confidence_band`, `decision_scope`, `limitation_flags`,
`validation_warnings`, `downstream_consumers`) and `ExpectedForecast` (CP-CF
only). A CP-2D liquidity bridge or a CP-4 covenant term cannot be keyed. The
vendor ships the reader: `completeness_check.find_registers(handoff_text,
register_ids) -> {register_id: (header, rows)}`, loaded through
`VendorContract`. Repair: `ExpectedRegister(module_id, register_id, row_key,
column, expected)` where `row_key` is `{column: value}` selecting exactly one
row (ambiguity refuses the key), compared on the NFC, whitespace-collapsed
cell; authored from documents, never from a run.

**O09 — The price is the caller's number [P2, Phase 8].** `ModelPrice` comes
from `CAOS_MODEL_PRICE` (`worker.py:249`) and is not stored with the
reservation; the worst-case byte bound reserves about `$3.64` per call at
Terra's rates, so a nineteen-node route needs a `$70` ceiling before it can
start. Repair: the dated price recorded on the reservation row and the
encoded request priced before reserving.

**O10 — A verdict's provider is the reviewer's word [P2, Phase 8].** Nothing
refuses a verdict naming a model no run used; a second signature is
`VERDICT_BINDING_INVALID` rather than `VERDICT_ALREADY_RECORDED`; the write
has no receipt. Repair: the comparison in `read_verdict`'s callers, the code,
and a global-scope receipt.

**O11 — Four bundle-side decisions are owed [P2, Phase 8 request].** The
disqualifier list conflates fixture markers with thin-evidence markers (§66);
CP-0 gates per consumer while the owner's stated intent is classification
only; `semantic_rules`, `document_substrings_casefold` and the LITE
`required_payload_fields` ship without code; the LITE `decision_scope` maps to
no `committee_status` — and run `ff71c457…` on `LITE_EARNINGS_UPDATE` accepted
a CP-0 declaring `Committee Ready` at 93 on a `SCREENING_ONLY` pathway, which is
that gap observed rather than predicted (`decision_scope` appears 19 times in
the catalog; `committee_status` never, and in no vendor script). With O03 that
is five requests, each a §61-style authorization or an upstream pull; the host
closes none alone.

### Record and delivery

**O12 — The branch has not landed [P1, Phase 7].** Measured by Task 7.2:
`main` is `01c3724` and the undelivered remainder is 13,036 counted lines over
173 files. Phase 7's last merged PR on `main` is #283; Phase 6 delivery is
incomplete, with nine PRs open and #296 failing `size` at 879. The last merged
PR is #283, a Phase 4 slice: PR numbering does not track phase order. Two PRs recorded
as merged, #281 and #285, merged into sibling PR branches rather than `main`,
one of them with `test` and `security` red; their content reaches `main` only if
#284's stack merges. The one over-cap merge since #258, #275 at 1,965 lines,
carries no split proof in its body, which the standing authorization requires.
`scripts/check_pr_size.py` hardcodes `HEAD`, so it cannot measure an arbitrary
PR without a checkout; the hosted `size` job's own log is the authority, and a
local three-dot diff systematically overcounts once a predecessor was
squash-merged. Owned by the delivery session; Phase 7 verifies read-only.

**O13 — The record disagrees with itself [P2, Phase 7].** The handoff's
"Next task" still says CP-5 is deferred (§62) after §63 and §69; three ledger
entries describe states `0018`–`0020` and §65 closed; the ledger's "predicates
frozen and never evaluated" and "BLOCKED ends the run; recovery is a new run"
carry upgrade paths this review withdraws (O16, O17); "Phase 7–10" headings
are rebuild labels; `feature-status.csv` records the health route as unbuilt;
`gemini-audit.md` and `PATHFINDER-2026-09-15/` are untracked.

**O14 — The remediation stream's outputs are inputs here [dependency].** T7
retires citation candidates and moves the prompt identity: every snapshot
before it is not comparable, so the programme's live runs start after T7
lands. T8 (`read_run_blocks`) and T11 (one verification reader) are what the
evidence-selection task builds on. T2 closes the tokenless dev-mode role hole.
D2 decides where Book starts. T3 removes one of the three outcome-record
transactions per node while keeping the replay binding; whether that meets T3 is
that stream's own definition.

### Route semantics

**O15 — Every module is handed every block** — see O07 [P1, Phase 10].

**O16 — A conditional edge would block unconditionally, and nothing says so
at the pin [P3, Phase 10].** `EdgeType.CONDITIONAL` is in `BLOCKING`
(`route.py:59`); the catalog declares none. Repair: a guard test on the
catalog's typed-edge counts and `ROUTE_EDGE_UNSUPPORTED` at resolution; no
evaluator until an upstream build introduces such an edge and the guard fails.
**Closed** by Task 10.2 (`8b806d0`, ledger entry `42e44aa`), with the scope the
code actually has: the guard fires for a conditional edge *on a resolved route*,
not for one declared anywhere in the catalog.

**O17 — A discharged CONDITIONAL verdict has no path back [P2, Phase 10].**
§61: the verdict names a source the effective set lacks, discharged by
supplying it and re-running CP-0 — under the pins, a new run. The host keeps
`(module_id, readiness)` per T8 row and drops `why_now_or_blocker`, the cell
that names the source. Repair: project that cell (bounded), a
`supersedes_run_id` on `runs` set by `CREATE_RUN`, both documents naming the
link. The ledger's "governed resume" is withdrawn: a CAS back to RUNNING would
reopen a run whose pins cannot change. **Closed** by Task 10.3 in two commits,
`cabb3d4` (the bounded projection and `NodeView.gate_reason`) and `167d800` (the
column, migration `0025`, the command, the read and the page), with `7e6c330`
recording §72. The withdrawal is scoped to a readiness verdict: a run whose
frontier empties against an unmet QA_GATE is the Repair Phase 2 entry's case and
keeps its own discharge. What the closure cost is a new ledger entry -- a gate
record stored before `blockers` existed refuses at every reader if its T8 named a
condition, discharged by a new run.

**O18 — Upstream identity ignores readiness; the anchor is derived; the
boundary is read from prose [P2, Phase 10].** Repair: a stored anchor; the
structured LITE boundary read beside the prose block with disagreement refused.
**The first repair clause is withdrawn.** It said readiness joins the refs from
the T8 reader, and Task 10.4 found that neither side can do that: where a soft
input is unaccepted and its source READY, the vendor *raises* rather than naming
the input, so there is no accepted artifact and no digest for a ref to carry.
The rule itself is enforced once, in the engine's `_state_for`, and the two
agree in every state a run can reach -- measured over 9,888 frontier memberships
of a three-module route with no disagreement. What was actually owed is a
comment at each rule naming the other, and a property test the day per-node
evidence selection changes `node_states`. No code was written, which is the
right outcome for a clause that described an unreachable state.

**O19 — Quotes match whole tokens exactly [P2, Phase 10].** Letter-spaced
headings, trailing punctuation and crop-edge glyph boxes refuse. Repair:
declared normalisations, tried only where the exact search finds nothing.
**Closed for the first two by Task 10.5 (§78); the crop-edge box is not this
item's and keeps its own ledger entry.** The repair clause first read
"versioned in the extractor identity" and is corrected: the identity records how
*tokens* were produced and these rules change no token, so a bump would force
every source in every database to be re-admitted for a change that altered no
extraction. The version is declared as `NORMALISATION_VERSION` beside the rules
it names.

### Workbench

**O20 — Five governed writes have store functions and no route [P1, Phase
12].** `members.grant`/`revoke`, source withdrawal, `save_revision`,
`sign_opinion`/`freeze`/`file_deliverable`. `ACTION_UNPLACED`'s clearance is
stale. Repair: five commands, controls, availability, the journey.

**O21 — Book and Admin are unavailable [P2, Phase 12].** Book from the shell
D2 leaves, over accepted CP-CF projections; Admin stays unavailable
(`IA_SPEC.md` §4.9); membership surfaces in Directory.

**O22 — The analysis page cannot name what blocked the run; Markdown renders
as text; a citation without a page prints "page " [P2, Phase 12].**

### Concurrency, durability, trust

**O23 — One node at a time, one connection; a second worker is not safe
[P2, Phase 13].** Sequential frontier and harness; `call_time_identity` by
clock; lineage read once per unit; acceptance does not recompare upstream; I6
can pay twice; `artifacts` mutable; proof and matrix not one snapshot.

**O24 — Streams poll; the evidence page holds a transaction; no worker
readiness; orphan blobs; unbounded blob reads; no schema-drift check; no
`request_sha256` on audit events; receipts forever; non-atomic package
publish [P3, Phase 13].**

**O25 — The edge is one static shared secret; test-edge cookie without
`Secure`; smoke not in CI; package verification has no signature anchor;
gate scripts recognise names [P2/P3, Phase 13].**

**O26 — Release evidence is a signed check, not a pack; the nightly live job
has never been authorized [P2, Phase 13].**

## 4. Completion gaps, not defects

1. **Three LITE pathways and one FULL pathway need what the tree cannot
   supply.** CP-L20/L23/L30/L40 are upstream's to ship (O03);
   `DISTRESSED_RESTRUCTURING` needs a distressed issuer's documents and a
   documented distress gate (O06). Each is recorded as *blocked on corpus or
   bundle*, not as unqualified by the host's fault.
2. **CP-DR researches supplied evidence only.** Invariant 1 makes web
   discovery structurally absent; a CP-DR question whose evidence is not in
   the pack is answered UNRESOLVED, and the key expects that.
3. **A key is authored, not measured.** A key taken from what a run cited
   measures the model against itself (§69's warning). Keys come from the
   documents and the owner's answer key; where a figure is derived, the key
   carries the derivation the vendor labels `[Calculated]`.
4. **The trusted edge and authenticity end outside the tree** (O25).
5. **Excluded on purpose, still:** no Excel/Word, no LibreOffice, no automatic
   web research, no graph framework, no broker, no UI redesign, no dashboard,
   no role switcher.

## 5. Phased implementation plan

Each phase is completed and demonstrated before its dependent phase starts;
Phase 9's tasks are independent of each other and of Phase 10's, so the
coordinator may run Phase 9 pathway tasks in parallel with Phase 10 engine
tasks in disjoint worktrees, but accepts them as separate phases. Small
single-concern PRs; the hosted 800-counted-line ceiling per actual PR base,
with the standing over-cap exception for proven-indivisible commits.

### Indexing, review and model policy

Ordinary exact-range review per task; one `confidence-review` and one
separate adversarial code audit per whole phase, with remediation and
reverification between them; no rewrite tournaments; no per-task specialist
review. The model axis follows the owner's Opus 5 / Fable 5.1 matrix (16
September 2026); Sonnet is not used.

| Activity | Model and effort | Notes |
|---|---|---|
| GitNexus refresh and caller verification | any, `low` | `analyze --force --index-only`, `status`; verify callers in source |
| Phase brief, spec, ADR, request document to the vendor | **Fable 5.1 `high`** | one brief per phase; one code-ready brief per task at phase entry |
| Plan or trade-off stress test | **Opus 5 `xhigh` with `ultrathink`** | one targeted prompt per brief; never `ultrathink` on Fable |
| Long-horizon multi-file implementation | **Fable 5.1 `medium`** | evidence selection (10.1), CP-DR brief delivery (9.4), the command chain (12.1), async store and second worker (13.1, 13.2), signed assertion (13.4) |
| Per-module fixture and contract tests; route enablement slices | **Opus 5 `medium`** | the Task 5.2a precedent; one implementer per module, one per route |
| Answer-key authoring from documents | **Opus 5 `medium`**, documents only | the key file and its derivations; the owner confirms every material figure; nothing read from a run |
| Ordinary implementation: endpoints, wire, UI, unit and integration tests | **Opus 5 `medium`** | 8.1–8.3, 10.2–10.5, 12.2–12.4, 13.3, 13.5, 13.6 |
| Scaffolding, fixtures, regenerated ledgers, docstrings, status | **Opus 5 `low`** | 7.1, corpus admission manifests, schema regeneration |
| Targeted invariant audit | **Opus 5 `xhigh` with `ultrathink`** | each module's register semantics before its fixture is trusted (the 5.2a precedent); money path (8.2); three-actor independence (12.1); interleavings (13.2); trust trace (13.4) |
| Ordinary per-task review | **Opus 5 `medium`** | the exact base…candidate range |
| Whole-phase `confidence-review` and adversarial audit | **Fable 5.1 `xhigh`** | actual `xhigh`, read back from the session record before the review turn |

A mixed slice takes the stricter row. Record the actual model, version and
effort at every formal checkpoint. Up to five implementers in isolated
worktrees with disjoint owned files, migrations and UUID-owned test databases
and blob roots; the coordinator alone integrates, gates and accepts, and fixes
an implementer's failure directly rather than re-dispatching.

**Coordination with the remediation stream.** Programme slices that edit
`server/methodology/handoff.py` (`ADAPTER_MODULES`, `ADAPTER_ROUTES`) or
`server/methodology/invocation.py` rebase onto the remediation's wave-3
integration (T10–T15 touch both); until it lands they own only test files,
fixtures and the two constants' lines. The programme's live runs begin only
after T7 (D1) has moved the prompt identity.

**High-risk sections** are the repair plan's list plus: per-node delivery;
the successor link; the five new writes; the second worker; the signed
assertion; the price recorded with the reservation; **and every register key
and its derivation** — a wrong key qualifies a wrong conclusion.

Phase-close order: implementation → normal tests → `confidence-review`
(Fable 5.1 `xhigh`) → remediate and rerun → refresh GitNexus → adversarial code
audit (Fable 5.1 `xhigh`) → remediate and reverify → phase accepted, recorded in
the handoff with both review records and the actual settings.

### The pathway task template

Every pathway task in Phases 9 and 11 has the same shape; each brief
instantiates it against the current interfaces. Numbers in brackets are the
step's model row.

1. **Contract stress test** [Opus 5 `xhigh`, `ultrathink`]: for each unproven
   module, read its `SKILL.md`, `load_contract` registers and payload schema;
   name the register rows whose semantics a fixture could fake and the cells
   a key must pin.
2. **Fixture pack and handoffs** [Opus 5 `medium`]: extend
   `tests/canonical_route_fixtures.py` with one realistic issuer pack for the
   pathway (quotes whole tokens; independently authored figures) and one
   fixture handoff per module from `load_contract`'s registers and minimum
   rows; module-specific cells in one small function each.
3. **Contract tests** [Opus 5 `medium`]: the five per module
   (`test_<module>_contract_validates_identifies_projects_and_anchors`,
   `…_refuses_a_missing_register`, `…_refuses_a_wrong_upstream`,
   `…_refuses_an_unanchored_quote`, `test_each_restricted_owner_retains_its_limitations`),
   parametrised in `tests/test_owner_contracts.py`; the module joins
   `ADAPTER_MODULES` in the same slice.
4. **Whole-route deterministic run** [Opus 5 `medium`]: completes, proves,
   freezes; every request under `MAX_REQUEST_BYTES`; a blocked required
   owner holds every dependent and calls nothing after; a restricted owner
   keeps its limitations downstream; where the route has a QA_GATE, `Blocked`
   holds CP-6 and `Passed` releases it; the pair joins `ADAPTER_ROUTES`; the
   `DISABLED` guard updated.
5. **Corpus** [Opus 5 `low` for admission manifests; the owner for sourcing]:
   the documents each module demands, admitted under their digests into a
   named set under `qualification/<set>/documents/`, each with provenance
   (URL, accession, date) in the set's `RESULT.md` header; documents not in
   hand recorded as *blocked on corpus*.
6. **Keys** [Opus 5 `medium`, documents only]: per module at least one
   `ExpectedRegister`, one `ExpectedProjection` and, where the module cites,
   one `ExpectedCitation` naming the fact-carrying line; `expects_ready` for
   every module the route runs; a refusal expectation where the corpus
   cannot support a module. Authored before any run; the owner confirms
   material figures; the set digest recorded.
7. **Live run** [authorization required]: provider, model, endpoint tag,
   reasoning effort, ceiling and window authorized per set;
   `scripts/qualify.py <set> --expect-identity <profile> --ceiling <n>`;
   database and blob root retained; the capture committed under
   `qualification/<set>/`; the verdict signed by an `ADMIN` through
   `POST /api/v1/qualification/{evidence_sha256}/verdict` — or the set
   recorded as not qualified with the reason.

### Phase 7 — Reconcile the record and land the branch

**Fixes:** O12, O13; records O14.

**Work**

1. Make the record true (Task 7.1): strike the closed ledger entries with
   their commits; rewrite the two withdrawn upgrade paths (O16, O17); relabel
   the rebuild headings; add a "Completion Phase 7" heading; rewrite the
   handoff's checkpoint table to §69's state and this plan; regenerate the
   stale `feature-status.csv` rows; a `tests/test_ledger.py` gate. Its rules are
   the ones that proved mechanical: a cited test the suite does not define, an
   open entry stating no `*Upgrade:*`, a heading with no blank line before it,
   a foreign list marker, and a floor naming the whole phase set. A sixth was
   specified here first -- an open entry citing the test that proves its
   closure -- and was measured against the real ledger and dropped, because the
   best phrase rule flagged three entries of which two were correct entries
   using the same words. The gate does not read prose, and the ledger says so. Move `gemini-audit.md` and
   `PATHFINDER-2026-09-15/` under `docs/reviews/supplemental/` with a header
   naming the concurrent review, or delete them.
2. Land and verify (Task 7.2): for each PR the delivery session merges, the
   head, base, counted size and the nine hosted check results read from
   GitHub; over-cap merges with their split proof; the `main` commit at which
   the branch is fully landed; GitNexus refreshed there.
3. Record the remediation stream's landed commits per wave in the handoff
   as they integrate; do not run its tasks, reviews or phase close from here.

**Exit checks**

- `tests/test_ledger.py` passes; no entry names a state a later decision
  closed; the handoff names this plan and the remediation stream's state.
- Every merged PR since #258 has a row with hosted results read from GitHub;
  no hosted status is described from a local run.
- Nothing under the repository root is untracked except `.claude/`.

**Guardrails:** no edit to `docs/REPAIR_PLAN.md`; no remediation task run
from this plan; no push, PR or ruleset change without authorization.

### Phase 8 — The qualification instrument

**Fixes:** O03 (request), O06 (register), O08, O09, O10, O11 (requests).

**Work**

1. Register keys (Task 8.1): `ExpectedRegister` in
   `server/qualification/matrix.py`, read through
   `VendorContract.completeness_check.find_registers` on the accepted
   Markdown; `expects_register` in the on-disk manifest; the borrowing-capacity
   key re-cast to the fact-carrying line; a key the loader can judge without a
   run refuses `QUALIFICATION_KEY_AMBIGUOUS` at set load -- an empty `row_key`,
   or two column names that normalise to one. **Corrected after building it:**
   this item first said a `row_key` matching no row or more than one refuses at
   load, which set load cannot know, because how many rows a register will carry
   is a fact about a run that has not happened. Zero rows and two rows are
   scored as a miss when the matrix reads the artifact, which is the only place
   the answer exists.
2. The price with the reservation (Task 8.2): `budget_reservations` gains the
   dated price (name, input, output, `as_of`) in a migration; the encoded
   request is priced after the prompt is built and before the reservation;
   the worst-case byte bound remains the ceiling check, not the reservation.
3. Verdict hygiene (Task 8.3): the provider comparison against the models the
   runs recorded; `VERDICT_ALREADY_RECORDED`; a global-scope receipt.
4. The corpus register (Task 8.4): `qualification/DOCUMENTS.md` — one row per
   document in hand or needed: pathway, module demand, source (URL,
   accession), digest once admitted, status (in hand / to source / not
   available); the sourcing list for the owner (EDGAR exhibits for CCL, BA and
   F debt documents; rating press releases; a dated market extract; peer
   filings; a decision record; a distressed issuer). Nothing is fetched
   automatically.
5. Bundle change requests (Task 8.5): five request documents under
   `docs/requests/`, each stating the change, the evidence, and what it
   unblocks: the LITE producers (O03); the marker split (§66); CP-0's gating
   versus classification; the three unshipped rules; the LITE scope-to-status
   mapping. Each awaits its own §61-style authorization or an upstream pull.

**Exit checks**

- A key naming a wrong cell fails a run whose citations are all located; a key
  the loader can judge ambiguous without a run refuses at load, and a `row_key`
  matching zero or two rows is a miss at scoring; the VMO2 set gains a register
  key for the module whose register has closed row-key cells -- CP-L10's TL10.2 --
  and still loads with an unchanged citation key. **Corrected after building
  it:** "one register key per module" was not reached and should not have been
  asked for, because CP-0's T8 has one closed cell and CP-5's T5B.5 keys on free
  prose, so a key there would measure wording.
- A reservation row says which dated price produced it; a small prompt
  reserves its priced cost, not the byte ceiling.
- A verdict naming an unused model is refused; a second signature is
  `VERDICT_ALREADY_RECORDED`.
- `qualification/DOCUMENTS.md` names every document Phase 9 and Phase 11 tasks
  will admit, with status, and a test holds it equal to what
  `scripts/document_register.py --report` emits; the five requests exist and the
  handoff records them as pending. (The file was named `CORPUS.md` here until the
  vocabulary gate refused "corpus"; work item 4 was corrected and this check was
  not.)

**Guardrails:** no key authored from a run's output; no document fetched by
the system; no vendor file edited by a request.

### Phase 9 — The LITE pathways

**Fixes:** O01 (CP-8, CP-DR), O02 (four pathways), O04, O05; holds three
pathways on O03.

**Work** — one task per pathway on the template, in this order:

1. `LITE_PORTFOLIO_DECISION` (Task 9.1): CP-0 → CP-L10, both proven; the
   route's contract test, the ledger entry that says it has none retired; keys
   on VMO2 and CCL; live run and verdict when authorized.
2. `LITE_RELATIVE_VALUE` (Task 9.2): CP-1C under its LITE compatibility block
   (accepts `lite_financial_change_screen`); a peer table document sourced for
   the corpus; keys; run.
3. `LITE_DECISION_LEDGER` (Task 9.3): CP-8's contract; the decision-record
   corpus pair (O05); keys; run.
4. `LITE_DEEP_RESEARCH` (Task 9.4): the host delivers the pinned brief to
   CP-DR as a tagged host-owned section, `source_mode` supplied-only,
   `cp0_sha256` bound to the accepted CP-0 record, refused for any other
   module; CP-DR's contract; a brief and its evidence in the corpus; keys
   that expect UNRESOLVED where the pack cannot answer; run.
5. `LITE_COVENANT_REFINANCING`, `LITE_DISTRESSED_RESTRUCTURING`,
   `LITE_FULL_CREDIT_SCREEN` (Tasks 9.5–9.7): **blocked on O03.** The briefs
   are written to the template and held; the day the producers arrive each
   runs as written.

**Exit checks**

- Four LITE pathways in `ADAPTER_ROUTES`, each with a deterministic
  whole-route test, a set with keys, and either a live snapshot with a signed
  verdict or a recorded reason.
- CP-DR receives exactly the pinned brief and nothing else new; a run whose
  pin carries no brief cannot reach CP-DR; a brief naming a consumer the route
  does not carry refuses at pin.
- CP-8's expected-versus-realised registers key against the outcome document.
- The three held pathways refuse `HANDOFF_MODULE_UNSUPPORTED` before any
  attempt and the handoff names the request they wait on.

**Guardrails:** no host-invented LITE producer; no CP-DR web access; no
route enabled before its whole-route test; no key from a run.

### Phase 10 — Route semantics for large evidence

**Fixes:** O07/O15, O16–O19.

**Work**

1. Per-node evidence selection (Task 10.1), on the prompt T7 leaves, the
   batched `read_run_blocks` T8 adds and the one verification reader T11
   leaves: delivery derived from the accepted CP-0 verdict's
   `evidence_demand`/`active_representation_ids` against the pinned set;
   written as an immutable `attempt_deliveries` row in the attempt's
   transaction; `verify_citations`, the proof and the deliverable anchor
   against the row; the bounded line group; a per-section bound and one
   recorded narrowing step; never truncation.
2. The conditional-edge guard (Task 10.2).
3. Successor runs (Task 10.3): the projected blocker cell; `supersedes_run_id`;
   both documents; the Restricted-clearance decision recorded.
4. Readiness-joined refs, a stored anchor, the structured boundary (Task 10.4).
5. Declared quote normalisations (Task 10.5) — **landed 18 September 2026**
   (§78): the quote's first and last word may differ from their token by
   `EDGE_PUNCTUATION`, and a maximal run of single-character tokens on one line
   of one region joins into the word a reader sees. Both only where the exact
   search found nothing, so the widening is monotone and every stored record
   re-verifies. Phase 10 is **not** exited by it: Task 10.1 is still held.

**Exit checks**

- A node is handed only what its verdict demanded; a quote on an undelivered
  page of a delivered source is refused on a real run.
- Boeing's and Ford's 10-K texts admit, group into bounded blocks, and a node
  demanding their statements runs under the ceiling. **The first obstacle is
  closed (18 September 2026)**: `PlainTextExtractor` declares `max_token_chars`
  and cuts a longer run, so the 71,243- and 105,966-character single tokens no
  longer refuse the pack. The texts themselves are still outside the tree and
  `MAX_REQUEST_BYTES` is still the second obstacle, which per-node evidence
  selection (10.1) owns.
- The catalog guard passes; a profile with a CONDITIONAL edge refuses at
  resolution.
- A BLOCKED run's document names the source its CONDITIONAL row asked for; a
  successor names its predecessor and is refused for a run that is not
  BLOCKED or not of its case.
- A letter-spaced heading and a quote ending in a full stop anchor to the
  rectangle a reader sees.

**Guardrails:** no evaluator for an edge type the catalog does not carry; no
delivery chosen by the model; no truncation; no run reopened after it ended.

### Phase 11 — The FULL pathways

**Fixes:** O01 (nine modules), O02 (nine pathways + RELATIVE_VALUE live).

**Work** — one task per pathway on the template, ordered by new modules and
corpus:

1. `MARKET_DISLOCATION` (11.1): CP-0, CP-3D, both proven; a dated market
   extract; keys; run.
2. `LIQUIDITY_REVIEW` (11.2): CP-2D; CCL 10-K; keys from the cash-flow
   statement and liquidity note (the answer key's CFO 6,218, capex 3,611,
   cash 1,928 are the anchors); run.
3. `EARNINGS_UPDATE` (11.3): CP-1B; two periods (VMO2 Q3/Q4 or CCL
   FY2024/FY2025); keys on the delta; run.
4. `DECISION_LEDGER` and `DEEP_RESEARCH` (11.4): CP-8 and CP-DR contracts
   shared with Phase 9; FULL-profile identity; keys; runs.
5. `RELATIVE_VALUE` live (11.5): the enabled route has only a fixture; a
   real issuer pack (annual report, facility terms from an EDGAR exhibit, a
   peer/market table); keys; run.
6. `COVENANT_REFINANCING` (11.6): CP-2D and CP-3C. CP-3C runs on the CCL
   10-K's maturity schedule; CP-4 on the same route is what needs the
   indentures sourced, so this pathway waits on CP-4's documents rather than on
   CP-3C's. Keys on maturities and covenant terms; run.
7. `PORTFOLIO_DECISION` (11.7): CP-6 and the QA_GATE; the HTTP test over a
   canonical `read_run` with a QA verdict other than `Passed` (the ledger's
   owed test); keys; run.
8. `FULL_CREDIT_ASSESSMENT` (11.8): CP-1A, CP-1D, CP-2E, CP-2H, CP-4C. CP-2E's
   Item 7A substrate is present in the CCL extract and CP-2H can be proven
   `Restricted` without the agency documents, so the binding constraints are
   CP-1A's missing transaction and CP-4C's inherited debt documents. Needs
   Phase 10 for the pack size; retires `NOT_YET_REACHED`; keys; run.
9. `DISTRESSED_RESTRUCTURING` (11.9): CP-4C's distress gate; **blocked on
   corpus** until a distressed issuer's documents are sourced; brief held.

**Before the first wide pathway runs, the per-section bound is owed.** Measured
on 17 September 2026: `FULL_CREDIT_ASSESSMENT`'s CP-5 carries 16 direct
upstreams and 165,548 bytes of its own delivered authority, so authority plus
upstream sections alone reach 47 % of `MAX_REQUEST_BYTES` at 20 KB per handoff,
before any evidence. The only route ever measured is LITE's at about 210 KB.
`CONTEXT_OVER_CEILING` refuses the whole request rather than truncating it, so a
pathway over the ceiling cannot be run and therefore cannot be qualified. The
Phase 5 ledger entry "An upstream section is unbounded" carries the numbers.
Treat this as a precondition of 11.9, not a risk.

**Task 10.1 is blocked on the vendor or on the owner, not on effort.** It was
dispatched and stopped rather than built. Per-node selection needs a per-module
statement of which sources a module needs; CP-0's schema declares one, in
`runtime_output`, and `invocation.py`'s `_FINAL_CHECK` explicitly tells the model
not to author that. Parsing the Markdown registers means a host table contract
the bundle does not state -- all sixteen declare `columns: none` -- and T8's
`Source files to attach` column is validated by the vendor and then dropped by
its own parser, so keeping it would make the host a second reader of one table.
Both breach invariant 4. `docs/requests/2026-09-17-t8-source-files-column.md` is
the smallest unblock; the alternative is a dated decision taking host ownership
of a register's shape, which must first answer whether a model-authored register
may decide what evidence a *downstream* node can cite. It may not be assumed:
narrowing is monotone downward on anchoring, so that register could turn a later
module's truthful quote of a pinned source into a refusal.

**Exit checks**

- Every FULL pathway except the one blocked on corpus is in `ADAPTER_ROUTES`
  with a whole-route test, a set with keys, and a signed verdict or a
  recorded reason; `tests/test_phase_exits.py` lists nothing under
  `NOT_YET_REACHED`.
- A `Blocked` CP-5 holds CP-6 on the production API and the run document
  says so.
- No pathway is advertised whose corpus could not support a module; the
  refusal expectation in its set says which.

**Guardrails:** no route enabled before its whole-route test; no key from a
run; no fabricated owner rows; no spend without its authorization line.

### Phase 12 — Complete the governed workbench

**Fixes:** O20–O22.

**Work:** five commands over the governed-write pattern (12.1), which is also
where the API surface's positional-argument width should be taken: the
remediation stream's redefined suppression gate counts functions callable with
more than five positional arguments, and **eighteen of its twenty-two charges
are under `server/api/`** -- the command handlers and the section reads, at six
to nine positional parameters, twenty-one of the twenty-two declaring no
keyword-only parameter at all. The hazard is a caller transposing two
same-typed neighbours silently, and the fix is making the surplus keyword-only,
so clearing the charge repairs the hazard rather than hiding it. Not a
refactor for its own sake: 12.1 rewrites these handlers anyway, and a layer that
never reached for keyword-only is one to correct while it is open rather than
in a pass of its own; controls and
availability, the clearance corrected, one available demo action (12.2);
Book over accepted snapshots from the shell D2 leaves (12.3); `blocked_by` on
`AnalysisBody`, a Markdown renderer with a closed element set, a citation
without a page refused (12.4); the journey extended through withdraw, save,
sign, freeze, file, grant, revoke and Book compare on three engines (12.5).

**Exit checks:** every new command passes the seven-identity matrix; a signer
cannot freeze and a freezer cannot file; withdrawal mid-run prevents fresh
acceptance and updates an open drawer; Book compares on one stated basis with
a ten-field passport per cell; the analysis page names the blocking node; nine
sections honest.

**How each was met, recorded on 17 September 2026 at the phase's exit rather
than left to be read off the plan.** Five of the six are met. The fourth is
met in one half and **unmeetable in the other**, and is written out here so
nobody reads the clause as satisfied:

1. *Seven-identity matrix* — **met.** `tests/test_actor_matrix.py` carries two
   tables over the same nine actors: `MATRIX` for the nine earlier commands and
   the three Task 12.1 added (`members`, `revocation`, `withdrawal`), and
   `DELIVERABLE` for the four filing commands, which needs a different fixture
   because a revision can only be derived from a run whose artifacts are
   accepted. Both include `anonymous → 401`, `nonmember → 404`,
   `revoked → 404` and a global READER with case standing → 403.
2. *A signer cannot freeze and a freezer cannot file* — **met**, twice over: at
   the surface by `report_actions`, at commit by `server/deliverable/filing.py`,
   and now in the browser on three engines, with a control that distinguishes
   `APPROVER_NOT_INDEPENDENT` from `DELIVERABLE_NOT_SIGNED` so the assertion
   names which rule refused.
3. *Withdrawal mid-run prevents fresh acceptance and updates an open drawer* —
   **met**, in one journey test with a real control on each half: the drawer is
   unchanged when a *different* source is withdrawn, and marked when its own is.
4. *Book on one stated basis with a ten-field passport per cell* — **the basis
   is met; the per-cell passport cannot be met end to end and is met by unit
   test only.** No run made through the API can carry CP-CF, so no cell exists
   to open a passport from: `create_run` resolves the route with no
   `RouteExtensions` and `CreateRun` carries no field to ask for one, while the
   only caller that requests the model extension is the qualification harness.
   The ten fields are held by three assertions, and **not** by
   `test_passport_contract`, which this entry first cited: that test lives in
   `frontend/tests/unit/evidence.test.tsx`, renders `MetricPassport` over a
   hand-built passport, says nothing about a Book cell, and is pinned by name
   in `tests/test_phase_exits.py` as *not* defined in the Python suite -- so
   the citation sent a reader to a file that does not hold it and would have
   broken the gate if anyone had "corrected" it by moving the test. What holds
   the claim is `PINNED[wire.BookPassport]` in `tests/test_wire_contract.py`
   (checked by `test_the_v1_wire_key_sets_are_pinned`),
   `frontend/tests/unit/book.test.tsx`'s "selecting a cell opens the passport
   with its ten fields", and `tests/test_book_section.py`. The journey asserts the
   *absence* of a table and a cell, so the day the extension becomes
   requestable that test fails and is rewritten to open the passport. See
   `CLAUDE.md`'s Completion Phase 12 entry, whose upgrade is a
   `model_extension` field on `CreateRun`, pinned in the route digest.
5. *The analysis page names the blocking node* — **met**, through the
   production stack on three engines (Task 12.4's field, Task 12.5's proof).
6. *Nine sections honest* — **met with two recorded dishonesties, both
   entered in the ledger rather than fixed**: Report is served but unreachable
   from the workspace, because nothing there can make a case's first revision;
   and `work.stop_code` is on the wire and on no surface, so an operator
   meeting a parked run is told only that Start and Retry are refused.

### Phase 13 — Concurrency, durability, the trusted edge, the release pack

**Fixes:** O23–O26.

**Work:** ~~async store and~~ the frontier's concurrent pass (13.1 -- **landed
18 September 2026**, §80: threads rather than `gather`, and the async store
**declined** rather than deferred, because the wait is a provider call and both
that socket and psycopg's release the interpreter lock; what the exit check
needed instead was `independent_batch`, a rule the spec does not state);
second-worker
safety in the race suite (13.2 -- **landed 18 September 2026**: two workers on a
queue of two runs take one each, and the concurrent pass 13.1 introduced accepts
each node exactly once. The I6 residual is **not** closed and is what a
*deployed* second worker still has to answer); `LISTEN`/`NOTIFY`, a stream cap, worker
readiness, the frame outside the transaction (13.3); the signed identity
assertion or mTLS, TLS in the smoke stack, the smoke stack in CI (13.4); store
hygiene and gate scripts (13.5); the release pack generated from the suite and
the store, the first authorized nightly, hosted checks verified against the
candidate on `main` (13.6).

**Exit checks:** two workers on one queue yield one accepted result per node
generation; a wide frontier finishes in the longest node's time; a forged
group header is refused whatever the proxy forwarded; the smoke stack runs in
CI; the release pack reproduces without editing a checksum; every advertised
pathway has a current verdict or is disabled and says so.

## 6. Development environment

Unchanged from the README and [`CI_GATE_CONTRACT.md`](CI_GATE_CONTRACT.md).
Additions arrive only with their tasks and decisions: a confirmed price
recorded with reservations (8.2); an identity-provider setting for the signed
assertion (13.4). Every shell command still starts by unsetting
`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`,
`OPENROUTER_PROVIDER`, `OPENROUTER_REASONING_EFFORT` and
`CAOS_REQUIRE_PROVIDER`.

## 7. Gate rules

The repair plan's §7 tables apply unchanged. Four rows are sharpened:

| Gate | Addition |
|---|---|
| Review/diff | Ordinary review on Opus 5 `medium`; model, version and effort recorded in the task's acceptance note |
| Phase-completion reviews | Both whole-phase reviews on **Opus 5 at `xhigh` with `ultrathink`**, pinned in `.claude/agents/phase-confidence-reviewer.md` and `phase-adversarial-auditor.md` where a setting lives. This row has been wrong twice: it was written for Fable 5.1, the owner rerouted to Opus `max` on 17 September 2026, and the same day set these two gates to `xhigh` -- which is what `CLAUDE.md` has said since the repair phases began, so the `max` pin contradicted the contract it was meant to satisfy |
| **Final review of all phases** | **One** review across the whole programme, on **Fable 5.1 at `xhigh`**, no `ultrathink` (an Opus lever). Run once, after the last phase's own two gates have passed and been remediated -- never for a single phase. Fable returns for this gate alone, and the reason is disconfirming evidence rather than preference: every other review here runs on Opus, gates that share an architecture share blind spots, and a different model reading the same tree is the only independent check available at the end. Pinned in `.claude/agents/final-phases-reviewer.md`. What it is for is the seams between phases, drift in the record read end to end, claims true per phase and false together, and whether the eleven invariants still hold as a set |
| Release qualification | A verdict must name a model the runs recorded; a pathway is advertised only with a current verdict over a complete snapshot on the current build and the current prompt identity |
| Answer keys | A key is authored from documents before the run and its material figures are confirmed by the owner; a key changed after a run invalidates that run's comparability, and the set digest says so |

### Definition of done for each completion item

The repair plan's §7C, plus: the ledger entry that recorded the limit is
struck in the commit that closes it, naming the test; a pathway is done when
its route is enabled, its set has keys, and its live result — qualified or
not — is recorded with its authorization.

## 8. Smallest useful delivery order

Revised 17 September 2026, against the tree at `b8e06ac`. The phases keep
their numbers, their tasks and their exit checks; what this section orders is
*delivery*, and delivery no longer follows the phase numbers. Read with the
handoff's "Completion plan state and what blocks each task", which is the
per-task record this section summarises and does not replace.

**Done.** Phases 7 and 8 are accepted (`38f4639`, one complete `make check`
gated both). Of Phase 9, Task 9.1 is in the branch. Of Phase 10, 10.2 and 10.3
are in the branch and 10.4 was answered as a finding rather than code.

**Buildable now, in this order.**

1. **Phase 12, the governed workbench, whole** (12.1–12.5). It is the one
   remaining phase that waits on no owner input, no vendor answer and no
   authorized run: the five store functions exist, D2 is decided (§74.4 leaves
   Book at its shell), the remediation stream it was told to coordinate with is
   complete and merged (§75), and every exit check is provable offline against
   the production stack the journey already drives on three engines. It also
   pays forward: the filing command is the natural T0 decision record Task 9.3
   needs (§9 item 4 of this plan), so landing 12.1 turns one owner-authored
   document into one the system can produce.
2. **Two pieces of Task 10.1's work item that need no vendor answer**, taken
   under Phase 10 without moving them:
   - **The bounded line group** (`SYSTEM_SPEC.md` §5; the Phase 2 ledger entry
     "One block per line; the bounded line group is not built"). Boeing's and
     Ford's 10-K texts are what it is for, both are held read-only outside the
     tree, and their admission is the first half of Phase 10's second exit
     check. It changes the extractor's block packing and nothing about
     delivery, so it does not depend on the T8 column.
   - **The per-section prompt bound** (the Phase 5 ledger entry "An upstream
     section is unbounded"). Measured today: `FULL_CREDIT_ASSESSMENT`'s CP-5
     carries 16 direct upstreams and 165,548 bytes of its own authority, so
     authority and upstream sections reach 47 % of `MAX_REQUEST_BYTES` at
     20 KB per handoff before any evidence. A declared bound refuses, before
     any attempt or reservation, with the section named -- never truncation
     (Phase 10's guardrail). What it does not do is make a wide route fit:
     that is per-node selection, which stays blocked. What it buys is that the
     first wide pathway's refusal names the oversize section rather than the
     whole request, and that Phase 11's precondition is met before its
     documents arrive rather than after. The 20 KB figure is an assumption;
     the real number arrives only when a FULL module produces a handoff.
3. **Phase 13's host-only tasks** (13.1 async store and `gather`, 13.2 the
   second worker in the race suite, 13.3 `LISTEN`/`NOTIFY` and worker
   readiness, 13.5 store hygiene and gate scripts), after Phase 12. Only 13.4
   (an identity-provider setting, TLS material) and 13.6 (an authorized nightly)
   end outside the tree. This is buildable, not yet chosen: starting 13.2 before
   10.1 lands means per-node delivery is later written onto a concurrent runtime,
   a cost this plan has not priced, and the ledger's I6 residual ("a stale lease
   holder can still pay once") is what the second worker has to answer first.

**Deferred, and what each waits on.** None of these is paused for effort.

| Delivery | Waits on | Freed by |
|---|---|---|
| Phase 9, Tasks 9.2–9.4 | a peer pack (9.2), a dated decision record (9.3), a research brief and its evidence (9.4): items 5–7 of `qualification/DOCUMENTS.md`'s sourcing list; then live-run authorization for each verdict | owner action 1, then 2 |
| Phase 9, Tasks 9.5–9.7 | the LITE producers request (O03) | the vendor, or a §61-style authorization |
| Phase 10, Task 10.1 | a per-module evidence demand the host may read without becoming a second reader of a vendor register: `docs/requests/2026-09-17-t8-source-files-column.md`, or a dated decision taking host ownership of a register's shape, which must first answer whether a model-authored register may decide what a downstream node can cite | the vendor, or owner action 3 |
| Phase 10, Task 10.5 | nothing external; sequenced after the line group because both touch the extractor identity, and a declared normalisation belongs in the identity that the group's blocks are recorded under | -- |
| Phase 11, all | the documents (items 1–5 of the sourcing list; the BA and F texts exist and are not yet copied in), the per-section bound above, and Task 10.1 for any pack over the ceiling; then live-run authorization per set. 11.9 also waits on a distressed issuer nobody has chosen (item 8) | owner action 1, then 2; 10.1 for 11.8 |
| Phase 13, Tasks 13.4 and 13.6 | an identity-provider setting and TLS material (13.4); an authorized nightly (13.6) | owner action 2 for 13.6 |
| Every live verdict | `qualification_verdicts` is empty in every database; nothing is qualified and nothing describes itself that way | owner action 2 |

The six vendor requests under `docs/requests/` -- the LITE producers, the
marker split, CP-0 gating versus classification, the unshipped rules, the LITE
scope-to-status mapping, and the T8 source-files column -- are each a §61-style
authorization or an upstream pull. The host closes none alone, and a route is
not enabled on a workaround for any of them (Phase 9's first guardrail).

### Why the order changed

The plan's phases were sequenced by dependency: instrument before pathways,
route semantics before the wide pathways, workbench and infrastructure last.
That order was right when everything in it was buildable, and it stopped being
buildable in one afternoon. Task 8.4's reading of the module skills turned
"corpus" into eight named document sets the tree does not hold; Task 8.5 turned
four bundle-side doubts into five written requests; Task 10.1 was dispatched
and stopped because both ways of reading a per-module evidence demand breach
invariant 4, which made it a sixth. After that, Phases 9, 10 and 11 were held
by three owner inputs and six vendor requests, and the dependency order sent a
reader into work that could not start while the one phase that could sat last
but one. The handoff caught it first (`b8e06ac`); this section is the plan
saying the same thing, so the two records agree.

What did not change: the phase numbers, the tasks under each, their exit checks
and guardrails, the definition of done. A pathway is still done only when its
route is enabled, its set has keys, and its live result is recorded with its
authorization -- so the buildable order above delivers no verdict by itself.

**The three owner actions, in the order they free the most work.**

1. **Source the documents.** `qualification/DOCUMENTS.md`'s sourcing list, in
   its own order: copy in the BA and F texts already held read-only outside the
   tree, then the executed debt documents by CIK, the rating actions, the
   market-data extract, the peer pack, and author the decision record and the
   research brief. They hold Tasks 9.2–9.4 and the whole of Phase 11. Nothing
   here fetches one: invariant 1 makes web discovery structurally absent, so a
   `to_source` row is a request to a person.
2. **Authorize live runs**, naming provider, model, endpoint tag, reasoning
   effort, ceiling and window per set. Every pathway's exit check ends in a
   verdict, and no verdict exists over any snapshot. The runs begin only after
   the documents for a set are admitted and its keys authored, so this action
   frees work only behind the first.
3. **Take, or decline, the dated decisions the plan leaves to the owner.** Two
   are named: whether the host may own the shape of one register for evidence
   selection, which is Task 10.1's alternative to waiting on the vendor; and
   Task 10.3 part (b), whether a QA `Restricted` releases CP-6 as RESTRICTED.
   Each is a §61-style entry. A decline is also an answer: it leaves 10.1 with
   the vendor and 11.8 behind it, and the plan should then say so rather than
   carry the task as pending.

Skipped deliberately: another architecture pass, a generic agent platform, a
second orchestration layer, workbook or Word output, automatic research, a
redesign.

## 9. Confidence review — this plan

Least confident about, ranked by consequence:

1. **Whether every module's evidence demand is what its skill says.** Read
   each unproven module's `Dependencies` line, entry stages, purpose and
   register list from the catalog and `SKILL.md`; did not read every register
   definition. Verdict: the corpus register (8.4) is where each demand is
   pinned document by document, and step 1 of the template re-reads the skill
   before any fixture is trusted.
2. **Ordering the LITE pathways before evidence selection.** VMO2 and CCL fit
   the ceiling (452,993 bytes measured with the candidate headers T7 removes);
   BA and F do not. Verdict: Phase 9 runs on what fits; Phase 11's larger
   packs wait for Phase 10.
3. **The three held LITE pathways.** Verified the schemas exist and the skills
   do not, and that no profile edge carries an object. Verdict: bundle-side;
   the request is the deliverable, not a host workaround.
4. **CP-8's corpus.** Its only required upstream is CP-0; the decision record
   is a document. Verdict: a filed CAOS deliverable is the natural T0 record
   once Phase 12 lands the filing commands; until then an owner-supplied memo.
5. **Cost figures.** `$0.27` per call is `$0.80` over three calls on the
   current build (`RESULT.md`); totals are that rate times node counts.
6. **The remediation stream's state.** Observed from worktrees and branches
   at review time; it moves. Recorded as observed on 17 September.
7. **Treating audit claims as findings.** Five verified in source; the
   concurrent review re-verified all and more. Verdict: adopted as the source
   of truth for those findings; this plan does not own their fixes.

Fixed in this deliverable: nothing in source. Verified fine: the served route
list, the enabled sections and routes, the migration list, the catalog's
pathway node lists and typed edges, the execution profiles' LITE object rows,
the key dataclasses, the qualification driver's interface. By design: §4.
Still open: everything in §3.
