# Completion Complementary Implementation Plan (Phases 7–13)

> **For agentic workers:** A coordinator may use up to five implementers in
> parallel only after partitioning independent tasks (owner's authorization
> of 14 September 2026). Prefer native isolated worktrees; fall back to Git
> worktrees only when native isolation is absent. Steps use checkbox
> (`- [ ]`) syntax for tracking. When an implementer fails a task or a test,
> the coordinator fixes it directly; it is never re-run or re-dispatched for
> the same failure.

**Goal:** Deploy the sixteen remaining catalog pathways — prove their eleven
unproven modules, assemble the documents they demand, author their answer
keys before any run, enable each route, run it live when authorized and sign
its verdict — and build only what that programme needs: the record made
true, the qualification instrument, per-node evidence selection, the
workbench's missing writes, and a system safe for two workers behind a real
edge.

**Architecture:** Each phase consumes one accepted predecessor commit and
produces one independently demonstrable capability. Phases 9 and 11 are the
programme: one task per pathway on one template. Phase 8 is the instrument
those tasks measure with; Phase 10 is what the large-evidence pathways need
to run at all. The audit remediation stream runs concurrently in its own
worktrees and is consumed, not owned.

**Tech Stack:** Python 3.14 application code, Python 3.12 security tools,
PostgreSQL 17, FastAPI/Pydantic, psycopg 3, React/TypeScript/Vite, Node 24,
Playwright, Docker, Trivy 0.70.0, installed GitNexus 1.6.9.

**Spec:** [`docs/COMPLETION_PLAN.md`](../../COMPLETION_PLAN.md) — its §2
inventory and §3 items O01–O26 are the requirements this plan implements;
its §5 "pathway task template" is the unit every programme task instantiates.

## Global Constraints

- Phase 6 is accepted (`docs/DECISIONS.md` §62, §69). Never implement a later
  completion phase to make an earlier phase's test pass.
- Work in `/Users/ericguei/Documents/caos-workbench`; keep
  `/Users/ericguei/Documents/caos-v2` read-only. `docs/REPAIR_PLAN.md` is not
  edited by these phases.
- `docs/DECISIONS.md` is binding; §39 still reconciles repair semantics.
  `docs/CLAUDE_CODE_HANDOFF.md` alone owns current task status. The launch text
  is `docs/PHASE_7_ONWARDS_GOAL_PROMPT.md`.
- The vendored bundle is immutable except by a dated decision under §61's
  precedent, one edit per authorization. The host never invents a vendor
  module, object owner or register.
- Every shell command starts by unsetting `OPENROUTER_API_KEY`,
  `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_PROVIDER`,
  `OPENROUTER_REASONING_EFFORT` and `CAOS_REQUIRE_PROVIDER`.
- No live/paid provider call, hosted write, push, PR, merge, deploy, CI-rule
  change, dependency change or destructive data cleanup without separate
  authorization. Every live run is authorized per set with provider, model,
  endpoint tag, reasoning effort, ceiling and window. Standing
  authorizations: pushing stacked PRs to `EricMG13/caos-v2`; merging a
  proven-indivisible over-cap PR with the proof in its body.
- Use only the local test-admin service at `127.0.0.1:55437/postgres`, URL
  supplied privately; UUID-owned databases cleaned in `finally`; preserve the
  development database on 55436, blobs and volumes. Retain every
  qualification run's database and blob root until its verdict is signed or
  its refusal recorded.
- TDD: a semantic failure is observed before production code changes.
- A key is authored from documents and the owner's answer key before the run;
  never from anything a run produced. The owner confirms material figures.
- One task is one reviewable concern. The hosted size limit is 800 additions
  plus removals from the actual PR base; deletion-dominated commits may
  exceed it with the size stated.
- Full engineering gate once per integration wave; commits run lint, types,
  `check_tested` and affected tests. Ordinary review for server changes;
  test-only, fixture-only and deletion slices skip it.
- GitNexus is discovery evidence. Verify every affected definition and
  caller in current source, types and tests; `impact` before editing a
  symbol, `detect_changes` before committing.
- No rewrite tournament. One `confidence-review` on `gpt-5.6-sol` `xhigh` and
  one separate adversarial code audit on `gpt-6-astra` `xhigh` per whole
  phase.
- **Remediation coordination.** See "Running Beside the Remediation Stream"
  below: it classifies every task by what it owns, names the four shared
  resources and their rules, and states the two hard orderings.

## Running Beside the Remediation Stream

The audit remediation (`2026-09-17-audit-remediation.md`, T1–T20 in four
waves) is executing now in `sdd/t1`–`sdd/t6`. It is not a task of this plan.
Both streams commit to one integration branch, so the question is file
ownership, not sequencing goodwill. Every completion task falls into one of
three classes, measured against the remediation tasks' own declared file
lists.

### Class A — owns no source file, runs today, and is the critical path

Tasks 7.1, 7.2, 8.4, 8.5, and **steps 1, 5 and 6 of every pathway task** (the
contract stress test, corpus sourcing, key authoring). These touch documents,
`qualification/`, `docs/requests/`, two new gate scripts and their tests.
Nothing in the remediation stream owns any of them.

This is also where the programme's real lead time sits. A pathway cannot run
before its documents exist and its keys are authored, and that work is EDGAR
exhibits, rating releases, a decision memo, peer filings and the owner
confirming material figures — weeks of sourcing with no code in it. Start
here on day one and the remediation stream is never in the way.

### Class B — owns new test files and two frozenset lines, runs today

Steps 2–4 of every pathway task (fixtures, contract tests, whole-route run,
route enablement) and Task 8.1's key form. What they touch:

| What | Remediation owner | Verdict |
|---|---|---|
| new `tests/test_<pathway>_route.py`, `tests/test_owner_contracts.py` cases | none | clean |
| `tests/canonical_route_fixtures.py`, `tests/lite_route_fixtures.py` | none | clean |
| `ADAPTER_MODULES`, `ADAPTER_ROUTES` in `server/methodology/handoff.py` | T14 edits the same file's `_strict_json`, not these lines | clean, but serial among pathway tasks |
| `server/qualification/matrix.py` (8.1's new dataclasses and scoring) | T14 adds `allow_nan=False` at `:239` | one-line rebase |
| `server/qualification/on_disk.py`, `server/refusals.py` | none | clean |

The fixture builders are safe across T7, which is worth stating because it
looks like they would not be: `fields_from_prompt`
(`tests/canonical_fixtures.py:196`) parses the `HOST-OWNED FRONT MATTER`
block, and T7 rewrites the evidence section and the citation instruction, not
that block. What T7 does delete is
`tests/test_awkward_evidence.py::test_citation_candidates_keep_only_unique_delivered_lines`
and the candidate assertions in `tests/test_handoff_invocation.py` — its own
tests, not the fixtures. A pathway task's
`test_<pathway>_requests_fit_the_request_ceiling` only gains slack when T7
removes roughly a third of every request.

### Class C — must wait for a named remediation task

| Completion task | Waits on | Why |
|---|---|---|
| 8.2 the priced reservation | T10 (`server/store/budget.py`, `__init__.py`), T17 and T18 (migration ordinals) | same functions and the same append point |
| 8.3 verdict hygiene | T5 | `server/qualification/store.py:405-424` and `server/api/commands/qualification.py:95-115` are literally T5's lines |
| 9.4 the CP-DR brief section | T7 | it edits the prompt builder at the point T7 rewrites, and its whole purpose is a new prompt section |
| 10.1 evidence selection | T7, T8, T11 | T8 gives it `read_run_blocks`, T11 gives it the one verification reader whose `delivered` argument it changes |
| 10.3 successor runs | T13 | T13 rewrites the nine UUID parse sites including `reads/run.py` |
| Every live qualification run | T7 | T7 moves the prompt identity, so any snapshot taken before it is not comparable |

Class C is the code nothing else depends on until Phase 11's live runs, which
is why waiting costs the programme nothing.

### The four shared resources

1. **Migration ordinals.** The tree is at `0021`; the remediation stream holds
   `0022` (T17, `case_members` index) and `0023` (T18, evidence statement
   trigger). A brief therefore names its migration **by name only**
   (`<ordinal>_attempt_deliveries.sql`); the coordinator allocates the ordinal
   at integration and records it in the handoff's remediation table. No brief
   fixes a number.
2. **`docs/CLAUDE_CODE_HANDOFF.md`.** The coordinator owns the file. Each
   stream appends under its own heading and edits no other stream's section;
   T7's "the prompt bytes moved" note and this plan's pathway table are both
   appends.
3. **`docs/DECISIONS.md` section numbers.** Assigned by the coordinator at
   integration, as the remediation plan already requires. A brief describes
   its entry and does not number it.
4. **`ADAPTER_MODULES` / `ADAPTER_ROUTES`.** The programme's only unavoidable
   shared source lines. No remediation task touches them. One frozenset edit
   per pathway task, integrated serially, each with its own enabled-set guard
   assertion so two tasks cannot both claim to be the last.

### Gates and integration

One integration branch and one full `make check` per wave, not per stream: a
completion Class A or B slice rides the remediation wave's gate rather than
adding a third. The coordinator integrates reviewed commits from both streams
serially and records, in the handoff's remediation table, which wave landed
and which Class C dependency it thereby met. An independently green worktree
in either stream is still not acceptance.

## Reasoning Modes

**Current routing:** [`docs/GPT_MODEL_REASONING_MATRIX.md`](../../GPT_MODEL_REASONING_MATRIX.md)
and `docs/DECISIONS.md` §104 govern all work dispatched from 19 September
2026. They map the workhorse role to `gpt-5.6-sol`, the long-horizon and
architect role to `gpt-6-astra`, and every former `ultrathink`/`max` request
to the actual Codex `xhigh` setting. They override every forward-looking
Claude model or effort row below. Completed work keeps its recorded setting.

### Historical Claude routing

The owner's `claude_fable_and_opus_reasoning_matrix.md` (16 September 2026)
replaces the Sonnet/Opus routing of the post-Phase-2 plan. Sonnet is out.
Recorded here so a fresh clone does not depend on a Downloads file.

### Model roles

| Model | Role | Use for |
|---|---|---|
| **Claude Opus 5** | daily-driver workhorse and verification specialist | routine implementation, unit and integration tests, discrete bug fixes, localized concurrency verification, adversarial shootouts |
| **Claude Fable 5.1** | long-horizon autonomous engine and chief architect | multi-stage roadmaps, cross-file refactoring, autonomous end-to-end task runs, root-cause system repairs, governance |

### Settings matrix

| Model | Effort | Workflow role | Used here for |
|---|---|---|---|
| Opus 5 | `low` | scaffolding and mechanical edits | fixture moves, schema regeneration, ledger relabelling, corpus admission manifests, docstrings, status edits |
| Opus 5 | `medium` (default dev) | daily-driver implementation | per-module fixtures and contract tests, route enablement slices, key authoring from documents, endpoints, wire, controls, per-task review |
| Opus 5 | `xhigh` with `ultrathink` | targeted invariant audits | each module's register semantics before its fixture is trusted; the money path; three-actor independence; two-worker interleavings; the trust trace |
| Opus 5 | `xhigh` with `ultrathink` | long-horizon autonomous execution | what Fable 5.1 `low`/`medium` held: evidence selection, CP-DR brief delivery, the command chain, async store and second-worker fencing, the signed assertion |
| Opus 5 | `xhigh` with `ultrathink` | architecture and governance | what Fable 5.1 `high`/`xhigh` held: phase and task briefs, vendor request documents, decision entries, and task-level review |
| Opus 5 | **`xhigh`** with `ultrathink` | the two per-phase gates | the confidence review and the separate adversarial audit that close each phase. `xhigh`, not `max`: `CLAUDE.md` has said "both at actual `xhigh` reasoning" since the repair phases began, so the `max` pin contradicted the contract it was meant to satisfy |
| **Fable 5.1** | **`xhigh`**, no `ultrathink` | the **one** final review across all phases | run once, after the last phase's own two gates have passed and been remediated; never for a single phase. Fable returns for this gate alone |
| **Fable 5.1** | `high`, no `ultrathink` | plan updates | revising a plan document when the build turns up an issue that needs one |

### Rules

- **`xhigh` is the ceiling, for every model. `max` is not dispatched.** The owner
  capped effort on 17 September 2026, after `max` had been the top row for a day.
  It binds regardless of model, so there is no slice anywhere in this plan that
  asks for more: the four agent definitions carry `effort: xhigh`, and every
  forward-looking row and targeted prompt below says `xhigh`.
- **Records of work already done keep the effort they ran at, and are not
  rewritten.** `docs/CLAUDE_CODE_HANDOFF.md`, the audit remediation plan and the
  Phase 8 and Phase 10 task briefs still say `max` in places, and correctly: a
  review is evidence about a tree at a time, and restating the setting it ran
  under would make the record say something that did not happen. Only live
  settings and unstarted work were capped.
- A mixed slice takes the stricter row.
- `ultrathink` is an Opus 5 lever only. It now governs two live cases again: the
  final all-phases review and plan updates both run on Fable 5.1, and neither
  prompt may carry it. The rule was kept rather than deleted when it briefly
  governed nothing, which is why it was available within hours when Fable
  returned.
- **Every slice Fable 5.1 held runs on Opus 5 `xhigh` with `ultrathink`, except the
  two the owner named back on 17 September 2026**: the final review across all
  phases (Fable 5.1 `xhigh`) and plan updates (Fable 5.1 `high`). The reason for
  the first is disconfirming evidence rather than preference — every other review
  in this repository runs on Opus, gates that share an architecture share blind
  spots, and a different model reading the same tree is the only independent
  check available at the end of a programme. Otherwise the replacement stands,
  not only for the reviews. The owner's instruction of 17 September 2026 named no scope, so
  it is read as it was written: Opus 5 at top effort with `ultrathink` **instead of**
  Fable 5.1, wherever Fable appeared. The reviews were the live case when it
  arrived and were rerouted first; the long-horizon implementation rows followed
  once a peer session read the same instruction the broader way, which is the
  more literal reading and the one that keeps two sessions on one branch from
  routing differently.
- Work already done under the older routing keeps its recorded model and effort and
  is not re-run: a review, like a run, is evidence about a tree at a time, and
  re-running one under a new setting would not make the earlier one untrue. Task
  10.3's second concern ran on Fable 5.1 `high` hours before this change and stays
  recorded that way.
- Effort is a setting and not a word in a prompt, so all three are pinned where a
  setting lives: `phase-confidence-reviewer.md` and `phase-adversarial-auditor.md`
  carry `model: opus` and `effort: xhigh`; `task-acceptance-reviewer.md` carries
  `model: opus` and `effort: max`; `final-phases-reviewer.md` carries
  `model: fable` and `effort: xhigh` and says in its body **not** to use
  `ultrathink`. Each Opus definition says in its body that the review turn opens
  with `ultrathink`. A run missing either the setting or the lever is a
  review that ran and not this gate, and says so in its own report.
- A subagent cannot read its own effort back, so what a report can attest is the
  launch path and not the setting. The dispatch names the pinned definition; the
  definition carries the setting. Where that is the whole of the evidence, say so
  rather than asserting a number.
- Record actual model, version and effort at every formal checkpoint. A word
  in a prompt is not a setting.
- Stay strictly within the requested scope.

### Per-task routing

| Task | Implementation | Ordinary review | Targeted prompt |
|---|---|---|---|
| 7.1 record reconciliation | Opus 5 `low`; the ledger gate test Opus 5 `medium` | none | — |
| 7.2 land and verify | Opus 5 `medium` (PR bodies, split proofs) | — | — |
| 8.1 register keys | Opus 5 `medium` | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink`: can a key be met by a wrong row |
| 8.2 price with reservation | Opus 5 `medium` | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink`: the money path |
| 8.3 verdict hygiene | Opus 5 `medium` | Opus 5 `medium` | — |
| 8.4 corpus register | Opus 5 `low` (the register); owner sources | — | — |
| 8.5 vendor requests | Fable 5.1 `high` | — | — |
| 9.1–9.4 LITE pathways | template rows below | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink` per unproven module |
| 9.4 CP-DR brief delivery (host prompt change) | Fable 5.1 `medium` | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink`: the brief as a trust boundary |
| 9.5–9.7 held LITE pathways | brief only, Fable 5.1 `high` | — | — |
| 10.1 evidence selection | Fable 5.1 `medium` | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink`: delivery/anchoring |
| 10.2 conditional-edge guard | Opus 5 `low` | none | — |
| 10.3 successor runs | Opus 5 `medium` | Opus 5 `medium` | — |
| 10.4 readiness refs, anchor, boundary | Opus 5 `medium` | Opus 5 `medium` | — |
| 10.5 quote normalisation | Opus 5 `medium` | Opus 5 `medium` | — |
| 11.1–11.9 FULL pathways | template rows below | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink` per unproven module |
| 12.1 five commands | Fable 5.1 `medium` | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink`: three-actor independence |
| 12.2 controls; 12.3 Book; 12.4 analysis/renderer | Opus 5 `medium` | Opus 5 `medium` | — |
| 12.5 journey | Opus 5 `medium` | none (test-only) | — |
| 13.1 async and `gather`; 13.2 second worker; 13.4 signed assertion | Fable 5.1 `medium` | Opus 5 `medium` | Opus 5 `xhigh` `ultrathink` (13.2 interleavings; 13.4 trust trace) |
| 13.3 notify/cap/readiness/frame; 13.5 hygiene and gate scripts | Opus 5 `medium` | Opus 5 `medium` | — |
| 13.6 release pack, nightly | Opus 5 `low` (generated) | — | — |
| Every phase brief and vendor request | Fable 5.1 `high` | — | Opus 5 `xhigh` `ultrathink` stress test |
| Every phase exit | — | Fable 5.1 `xhigh` ×2 | — |

**Template rows (each pathway task):** step 1 contract stress test — Opus 5
`xhigh` `ultrathink`; steps 2–4 fixtures, contract tests, whole-route run —
Opus 5 `medium`, one implementer per module and one per route; step 5 corpus
admission manifests — Opus 5 `low`, sourcing by the owner; step 6 keys —
Opus 5 `medium` reading documents only, material figures confirmed by the
owner; step 7 live run — the authorized driver run by the coordinator, the
capture at Opus 5 `low`.

## Shared Phase Entry and Exit

Every phase starts with this sequence:

- [ ] Confirm the preceding phase's accepted commit, a clean worktree, the
      active branch and explicit authorization for only the next phase.
- [ ] Read `CLAUDE.md`, `docs/COMPLETION_PLAN.md`, the decision sections named
      on the phase card, and every current implementation and caller in the
      phase file map. Record the remediation stream's landed waves.
- [ ] Rebuild and verify the local index only:

  ```sh
  env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER /Users/ericguei/.nvm/versions/node/v24.16.0/bin/gitnexus analyze --force --index-only
  env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER /Users/ericguei/.nvm/versions/node/v24.16.0/bin/gitnexus status
  ```

- [ ] Write one tracked brief per task under `docs/superpowers/plans/` on
      `gpt-6-astra` `high`: accepted base, exact files, current interface
      signatures, failing assertions, executor row, risk classification,
      commands and cumulative PR size estimate; for a pathway task, the
      template's seven steps instantiated with the pathway's modules, edges,
      documents and keys. Stress-test it with one `gpt-5.6-sol` `xhigh`
      prompt before code.
- [ ] Map task dependencies and launch at most five implementers only for
      disjoint ownership, each with its own UUID-owned test database and blob
      root; the coordinator alone updates the handoff and integration branch.

Every implementation task exits through focused tests, then the serial
backend gate:

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER make -j1 check-postgres lint types test test-postgres-races security CAOS_REQUIRE_POSTGRES=1 CAOS_TEST_POSTGRES_URL="${CAOS_TEST_POSTGRES_URL:?set privately}"
```

Then ordinary review on `gpt-5.6-sol` `medium` of the exact range, remediation, and
the size gate against the actual PR base:

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER make check-size PR_BASE="${PR_BASE:?set exact proposed PR base}"
```

A live qualification run, once authorized, is driven only through the tree's
driver, with the profile the authorization names:

```sh
env -u CAOS_REQUIRE_PROVIDER scripts/qualify.py qualification/<set> --expect-identity <provider/endpoint/effort[/tokens]> --ceiling <usd>
```

with `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `CAOS_MODEL_PRICE` and
`CAOS_TEST_POSTGRES_URL` supplied privately to that process alone; the
capture, database name and blob root recorded under `qualification/<set>/`.

At whole-phase freeze, the complete repository gate with the pinned Trivy:

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER TRIVY="$TRIVY" IMAGE=caos-workbench:check make check
```

Then the `confidence-review` on `gpt-5.6-sol` `xhigh`, remediation and rerun, a
GitNexus refresh, the separate adversarial audit on `gpt-6-astra` `xhigh`,
remediation and reverification, and a tracked acceptance record in the
handoff with exact commits, index identity, actual model/effort read back
from the session, commands, results, every pathway's state (enabled / set
digest / live result / verdict) and remaining limits.

---

## Phase 7 — Reconcile the Record and Land the Branch

**Why now:** every later phase is measured against the ledger, the handoff
and GitHub `main`; all three currently disagree with the tree.

**Consumes:** Phase 6 accepted at `e59ad7b` (§69).

**Produces:** a ledger with no closed entry left open and no withdrawn
upgrade path, a handoff pointing at this plan and recording the remediation
stream, the untracked audits disposed of, and the branch landing with hosted
checks verified per PR.

**Primary references:** `CLAUDE.md` known-gaps ledger,
`docs/CLAUDE_CODE_HANDOFF.md`, `docs/CI_DELIVERY_SPLIT_PLAN.md`,
`docs/feature-status.csv`, `docs/DECISIONS.md` §62–§69. Briefs:
`2026-09-17-phase-7-task-7.{1,2}-brief.md`.

### Task 7.1: Make the Record True

**Files:** `CLAUDE.md`, `docs/CLAUDE_CODE_HANDOFF.md`,
`docs/feature-status.csv`, `tests/test_ledger.py` (create),
`scripts/ledger_state.py` (create), `docs/reviews/supplemental/` (create).

- [ ] RED: a test that reads every ledger bullet, extracts the test names it
      cites, and fails when a struck entry cites a test the suite lacks or an
      open entry cites the test that proves its closure (the three
      §65/`0018`–`0020` entries).
- [ ] Strike the closed entries with their closing commit; rewrite the
      "predicates frozen" and "BLOCKED ends the run" entries' upgrade paths
      to O16 and O17; relabel the four rebuild headings "Rebuild Phase N
      (historical)"; add "**Completion Phase 7.**".
- [ ] Rewrite the handoff's checkpoint table (Phase 6 at `e59ad7b`, §69; next
      task Completion Phase 7; launch text `PHASE_7_ONWARDS_GOAL_PROMPT.md`;
      a "Completion plan" row; a "Remediation stream" row with its observed
      state).
- [ ] Regenerate the six "Gap documented" `feature-status.csv` rows from
      their named tests.
- [ ] Move `gemini-audit.md` and `PATHFINDER-2026-09-15/` under
      `docs/reviews/supplemental/` with a header naming the concurrent review,
      or delete them.

**Task acceptance:** `tests/test_ledger.py` passes; nothing outside `.claude/`
is untracked; the handoff names this plan.

### Task 7.2: Land and Verify

**Files:** `docs/CLAUDE_CODE_HANDOFF.md` (per-PR record),
`docs/CI_DELIVERY_SPLIT_PLAN.md` (a "landed as" column).

- [ ] For each PR the delivery session opens or merges: head, base, counted
      size, the nine required check results read from GitHub, merged commit
      or open.
- [ ] Over-cap merges: the split attempt and its failure proof beside the PR.
- [ ] The `main` commit at which the branch is fully landed; GitNexus
      refreshed there.
- [ ] The remediation stream's landed commits per wave, as they integrate.

**Task acceptance:** every merged PR since #258 has a row with hosted results;
no hosted status is described from local output.

**Phase 7 exit:** the complete repository gate; the `gpt-5.6-sol` `xhigh`
confidence review and `gpt-6-astra` `xhigh` adversarial audit
(the adversarial audit marked not applicable for the docs-only half; it
covers the ledger gate script).

---

## Phase 8 — The Qualification Instrument

**Why now:** every pathway task authors keys and reserves spend; the keys
must be able to name a register cell, the reservation must know its price,
and the vendor requests must be in flight before the pathways that wait on
them are reached.

**Consumes:** Phase 7's reconciled tree; remediation T14's digest helper if
landed.

**Produces:** `ExpectedRegister` keys, a priced reservation, verdict hygiene,
the corpus register and five vendor request documents.

**Primary references:** `docs/COMPLETION_PLAN.md` O03, O06, O08–O11;
`server/qualification/{matrix,on_disk,store,verdict,harness}.py`,
`server/store/budget.py`, `server/pricing.py`, `server/engine/worker.py`,
`server/api/commands/qualification.py`, `docs/DECISIONS.md` §23–§25, §40,
§61, §63–§66. Briefs: `2026-09-17-phase-8-task-8.{1..5}-brief.md`.

### Task 8.1: Register Keys

**Files:** `server/qualification/matrix.py` (`ExpectedRegister`,
`QualificationCase.expects_register`, `MatrixRow.registers_met`,
`_registers_met`, `assert_measurable`), `server/qualification/on_disk.py`
(`_registers`, the manifest key `expects_register`), `server/refusals.py`
(`QUALIFICATION_KEY_AMBIGUOUS`), `qualification/vmo2-fy2025/qualification.json`,
`tests/test_qualification_matrix.py`, `tests/test_qualification_on_disk.py`.

- [ ] REDs: a run whose CP-L10 TL10.2 topic row says the wrong thing scores
      `projections_met=True`; a manifest with `expects_register` refuses as an
      undeclared key; a `row_key` matching two rows is accepted at load.
- [ ] `ExpectedRegister(module_id, register_id, row_key: tuple[tuple[str,str],...],
      column, expected)`; read through
      `VendorContract.completeness_check.find_registers(markdown, [register_id])`
      on the accepted Markdown that `accepted_projections` already verifies;
      the cell compared NFC and whitespace-collapsed; ambiguity refused at
      set load; the set digest covers it.
- [ ] The VMO2 set gains one register key per module; the borrowing-capacity
      key re-cast to the fact-carrying line.

**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `Construct a handoff that
meets an ExpectedRegister key while concluding the opposite of what the key
was authored to check — through row order, a duplicated register heading, a
fenced table, or a cell that matches after normalisation. Name the parser
rule that closes each.`

**Task acceptance:** a key naming a wrong cell fails a run whose citations
are all located; an ambiguous key never loads.

### Task 8.2: The Price with the Reservation

**Files:** `server/store/<ordinal>_reservation_price.sql` (create; ordinal
allocated at integration), `server/store/__init__.py` (`MIGRATIONS`),
`server/store/budget.py` (`reserve`, `_reserve`), `server/pricing.py`
(`priced_request`), `server/engine/runtime.py:408`,
`server/methodology/invocation.py` (the encoded request is available in the
pre-call unit), `tests/test_budget.py`, `tests/test_loop_charges.py`.

- [ ] REDs: a reservation row cannot say which price produced it; a 40 KB
      prompt reserves the 1 MiB worst case.
- [ ] `budget_reservations` gains `price_model`, `price_input`, `price_output`,
      `price_as_of`; `reserve` takes the `ModelPrice` and the priced amount;
      the amount is `priced_request(price, request_bytes, MAX_COMPLETION_TOKENS)`
      computed after `check_context` built the prompt and before
      `start_attempt`; the worst case remains the ceiling admission check.

**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `Under a changed price
between pre-check and reservation, a retried attempt, a replayed billed
answer and a crash between pricing and reservation, find any path that
reserves less than the call can cost or charges without a reservation.`

**Task acceptance:** every reservation names its dated price; a small prompt
reserves its priced cost; invariant 8 still refuses before overspend.

### Task 8.3: Verdict Hygiene

**Files:** `server/qualification/store.py` (`record_verdict`),
`server/qualification/verdict.py`, `server/api/commands/qualification.py`,
`server/refusals.py` (`VERDICT_ALREADY_RECORDED`), `server/store/commands.py`
(a global scope receipt keyed by the nil UUID scope `0014` already reserves
for create-case), `tests/test_qualification_sign.py`, `tests/test_qualification.py`.

- [ ] REDs: a verdict naming `openrouter:some-other-model` over evidence whose
      runs recorded Terra records; a second signature is
      `VERDICT_BINDING_INVALID`; a replayed request has no receipt.
- [ ] `record_verdict` reads the models the evidence's runs recorded
      (`call_outcomes`) and refuses a mismatch; the one-verdict constraint
      maps to `VERDICT_ALREADY_RECORDED`; the command runs through
      `run_command` with the nil-UUID scope.

**Task acceptance:** only a verdict naming a recorded model records; a retry
is answered by its receipt.

### Task 8.4: The Corpus Register

**Files:** `qualification/DOCUMENTS.md` (create), `qualification/<set>/RESULT.md`
headers as documents are admitted.

- [ ] One row per document in hand or needed: pathway(s), module demand,
      source (URL, accession, date), digest once admitted, status (in hand /
      to source / not available), and for each "to source" the exact public
      location where known — EDGAR exhibits for CCL, BA and F indentures and
      credit agreements; rating-agency press releases; a dated market-data
      extract the owner supplies; sector peers' filings; a decision record; a
      distressed issuer's disclosure statement.
- [ ] Nothing is fetched by the system; the owner sources and the coordinator
      admits.

**Task acceptance:** every document Phases 9 and 11 will admit is named with
its status before either phase starts.

### Task 8.5: Vendor Change Requests

**Files:** `docs/requests/2026-09-17-lite-producers.md`,
`…-disqualifier-marker-split.md`, `…-cp0-gating-vs-classification.md`,
`…-unshipped-rules.md`, `…-lite-scope-status.md` (create).

- [ ] Each request: the change, the evidence in this tree (run ids, ledger
      entries, decision sections), what it unblocks (O03: three LITE pathways;
      §66; the owner's stated intent; the three rules; the LITE scope
      mapping), and the two ways it can land (an upstream build pulled in with
      §61's procedure, or an authorized in-tree edit with its own decision).
- [ ] The handoff records each as pending with the pathways it holds.

**Task acceptance:** five requests exist; nothing in `vendor/` changed.

**Phase 8 exit:** the complete repository gate; the `gpt-5.6-sol` `xhigh`
confidence review and `gpt-6-astra` `xhigh` adversarial audit.

---

## Phase 9 — The LITE Pathways

**Why now:** four LITE pathways can run on the corpus in hand and the current
bundle; they exercise the instrument before the larger FULL packs need the
engine work of Phase 10.

**Consumes:** Phase 8's instrument; remediation T7 landed (the prompt
identity) before any live run.

**Produces:** four LITE pathways enabled, keyed and run; three held with
their briefs on the vendor request; CP-8 and CP-DR proven.

**Primary references:** `docs/COMPLETION_PLAN.md` §2 inventory, §5 template,
O01–O05; `tests/test_owner_contracts.py`, `tests/canonical_route_fixtures.py`,
`tests/lite_route_fixtures.py`, `tests/test_relative_value_route.py`
(`DISABLED`), `server/methodology/handoff.py` (`ADAPTER_MODULES`,
`ADAPTER_ROUTES`), `server/methodology/invocation.py`,
`vendor/deploy-v/skills/cp-8-decision-ledger-post-mortem/SKILL.md`,
`vendor/deploy-v/skills/cp-dr-deep-research/SKILL.md`,
`vendor/deploy-v/skills/cp-os-credit-os/references/CP_DR_RESEARCH_BRIEF_V1.md`.
Briefs: `2026-09-17-phase-9-task-9.{1..4}-brief.md`, `…-9.5-9.7-held-brief.md`.

### Task 9.1: `LITE_PORTFOLIO_DECISION` (CP-0 → CP-L10)

- [ ] Steps 1–4: no unproven module; a whole-route test in
      `tests/test_lite_portfolio_route.py` (completes, proves, freezes; CP-L10
      Blocked ends the run; ceiling); the pair joins `ADAPTER_ROUTES`;
      `DISABLED` updated; the ledger's "has no contract test" retired.
- [ ] Steps 5–6: sets `qualification/vmo2-fy2025-portfolio/` and
      `qualification/ccl-fy2025-portfolio/` reusing the admitted documents;
      keys: `expects_ready` CP-L10; register keys on TL10.1/TL10.2 (the
      goodwill impairment topic for VMO2; the debt-extinguishment three-figure
      trap for CCL); projection keys on `decision_scope` and `qa_status`.
- [ ] Step 7: authorized run and verdict, or the recorded reason.

### Task 9.2: `LITE_RELATIVE_VALUE` (CP-0 → CP-L10 → CP-1C)

- [ ] Step 1: CP-1C's LITE block (`SKILL.md:44-50`: accepts
      `lite_financial_change_screen`, `SCREENING_ONLY`, `UPGRADE`) — its
      registers under a LITE upstream; `named_objects` must release CP-1C on
      CP-L10's accepted object.
- [ ] Steps 2–4: a LITE fixture handoff for CP-1C consuming CP-L10's object;
      `test_cp1c_under_lite_accepts_the_named_object_and_keeps_screening_scope`;
      whole-route test; route enabled.
- [ ] Steps 5–6: a peer table document sourced (sector peers' FY2025
      figures with provenance); keys on CP-1C's benchmark registers and
      `decision_scope: SCREENING_ONLY`.
- [ ] Step 7.

### Task 9.3: `LITE_DECISION_LEDGER` (CP-0 → CP-8)

- [ ] Step 1: CP-8's T7.1–T7.8 (decision, thesis, realised values,
      expected-versus-realised, attribution, priors, aggregate, gaps) — which
      cells a fixture could fake and which a key must pin.
- [ ] Steps 2–4: CP-8 fixture and the five contract tests; CP-8 joins
      `ADAPTER_MODULES`; whole-route test; route enabled.
- [ ] Steps 5–6: the corpus pair — a decision record at T0 (an owner-supplied
      memo until Phase 12 can file one) and the later filing at T1 (VMO2 Q3 as
      T0 context and Q4 as T1 is the pair in hand); keys on T7.3 realised
      values and T7.4 variances from the T1 document.
- [ ] Step 7.

### Task 9.4: `LITE_DEEP_RESEARCH` (CP-0 → CP-DR) and the Brief Delivery

**Files (host):** `server/methodology/invocation.py` (a `RESEARCH BRIEF`
tagged host-owned section rendered only for CP-DR from
`RunInput.research_json`, with `cp0_sha256` bound to the accepted CP-0 record
and `source_mode` forced to supplied evidence), `server/store/run_inputs.py`
(`_research` validates the brief against `CP_DR_RESEARCH_BRIEF_V1`'s required
keys and refuses a consumer the route does not carry),
`server/api/commands/runs.py` (`PIN_RUN_INPUT` already carries
`research_json`), `tests/test_handoff_invocation.py`, `tests/test_run_inputs.py`.

- [ ] REDs: a run pinned with a brief reaches CP-DR with no brief in its
      prompt; a brief naming `consumer_module_id: CP-2A` on a route without
      CP-2A pins; a brief with `source_mode: hybrid` reaches the prompt
      unchanged; any module but CP-DR receives the section.
- [ ] The section; the pin validation; CP-DR's TDR.1–TDR.3 fixture and
      contract tests; CP-DR joins `ADAPTER_MODULES`; whole-route test; route
      enabled.
- [ ] Steps 5–6: a brief with two questions over the VMO2 pack — one the pack
      answers, one it cannot — and keys expecting ANSWERED and UNRESOLVED
      respectively in TDR.3.
- [ ] Step 7.

**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `The brief is caller text
that reaches the prompt. Trace it from PIN_RUN_INPUT through the pin, the
section and CP-DR's answer; find any path where it selects a module, a
source, a tool or a web access the invariants forbid, or where a consumer
adopts research the brief did not name.`

### Tasks 9.5–9.7: `LITE_COVENANT_REFINANCING`, `LITE_DISTRESSED_RESTRUCTURING`, `LITE_FULL_CREDIT_SCREEN` — held

- [ ] Briefs written to the template (CP-3C; CP-2H and CP-4C; CP-1A, CP-2H,
      CP-3C and CP-4C under LITE) and held on the LITE-producers request
      (Task 8.5). Their contract tests can be written and skipped with the
      request as the reason; no route is enabled.

**Phase 9 exit:** `docs/COMPLETION_PLAN.md` Phase 9 exit checks; the complete
gate; the `gpt-5.6-sol` `xhigh` confidence review and `gpt-6-astra` `xhigh`
adversarial audit; the handoff's pathway table.

---

## Phase 10 — Route Semantics for Large Evidence

**Why now:** two of the three 10-K texts exceed the request ceiling whole,
and the FULL pathways of Phase 11 demand them.

**Consumes:** remediation T7, T8 and T11 landed.

**Produces:** per-node delivery recorded on the attempt and enforced by every
reader; the conditional-edge guard; successor runs; readiness-joined refs;
declared quote normalisations.

**Primary references:** `docs/COMPLETION_PLAN.md` O07, O15–O19;
`docs/SYSTEM_SPEC.md` §4–§5; `docs/DECISIONS.md` §27, §39, §44–§47, §61.
Briefs: `2026-09-17-phase-10-task-10.{1,2,3}-brief.md`; 10.4 and 10.5 at
phase entry.

### Task 10.1: Per-Node Evidence Selection

**Files:** `server/methodology/selection.py` (create),
`server/methodology/executor.py` (`captured_blocks`, `delivered_blocks`),
`server/methodology/canonical.py` (`check_context`, the attempt unit),
`server/methodology/invocation.py` (`SECTION_BYTES`), `server/evidence/citations.py`,
`server/evidence/ingest.py` (`_blocks`, `BLOCK_CHARS`),
`server/store/<ordinal>_attempt_deliveries.sql` (create), `server/store/runs.py`,
`server/qualification/proof.py`, `server/deliverable/canonical.py`,
`tests/test_evidence_selection.py` (create), `tests/test_awkward_evidence.py`.

- [ ] REDs: a node demanding one document is handed another's; a quote on an
      undelivered page of a delivered source is accepted on a real run; a
      541-page text yields a block per line; the proof anchors against blocks
      the attempt was not handed.
- [ ] Delivery from CP-0's `content_to_module_map` row per consumer; an
      immutable `attempt_deliveries` row; every reader anchors against it;
      the bounded line group; a per-section bound; one recorded narrowing;
      never truncation.

**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `Trace one citation from the
model's quote through the delivery row, the token index, the proof's and the
deliverable's re-anchoring. Find any path where the delivery recorded, the
blocks prompted and the blocks anchored against differ — including a v2
record, a withdrawn member, a narrowed delivery and a replayed billed attempt.`

### Task 10.2: The Conditional-Edge Guard

- [ ] `test_the_vendored_catalog_carries_no_edge_this_engine_cannot_evaluate`
      pins `(60, 26, 29, 1, 0)`; `_edges_among` refuses
      `ROUTE_EDGE_UNSUPPORTED`; the ledger entry rewritten.

### Task 10.3: Successor Runs for a Discharged Verdict

- [ ] `Projections.blockers` from T8's `why_now_or_blocker` (bounded);
      `NodeView.gate_reason`; `runs.supersedes_run_id` (migration, ordinal allocated at integration,
      immutable once set, same case, target BLOCKED at commit); `CreateRun.supersedes`;
      both documents; the Run section offers the successor when a newer
      source-set version exists; the Restricted-clearance decision recorded.

### Task 10.4: Readiness-Joined Refs, Stored Anchor, Structured Boundary

- [ ] Readiness joins the refs from the T8 reader; a stored anchor
      (migration); the readiness effect carried with the state; the JSON LITE
      declaration read beside the prose block, disagreement refused.

### Task 10.5: Declared Quote Normalisations

- [ ] Tracking-collapse for headings, trailing-punctuation tolerance at a
      quote's last token, a crop tolerance — each in extractor identity v3 and
      the index; v2 rows keep their identity.

**Phase 10 exit:** `docs/COMPLETION_PLAN.md` Phase 10 exit checks; the
complete gate; the `gpt-5.6-sol` `xhigh` confidence review and
`gpt-6-astra` `xhigh` adversarial audit.

---

## Phase 11 — The FULL Pathways

**Why now:** the modules are proven one route at a time; the order below
adds the fewest new contracts first and holds the two that need what the
tree cannot supply.

**Consumes:** Phase 10 (for the packs that exceed the ceiling) and the corpus
register's sourced documents.

**Produces:** eight FULL pathways enabled, keyed and run; `RELATIVE_VALUE`
qualified live; `DISTRESSED_RESTRUCTURING` held on corpus; nine modules
proven; `NOT_YET_REACHED` empty.

**Primary references:** the Phase 9 references plus the nine modules'
`SKILL.md` and the catalog's typed edges (`docs/COMPLETION_PLAN.md` §2).
Briefs at phase entry, one per task, on the template.

### Task 11.1: `MARKET_DISLOCATION` (CP-0 → CP-3D)
- [ ] No unproven module; whole-route test; enable; a dated market extract
      admitted with provenance; keys on CP-3D's implied-risk registers; run.

### Task 11.2: `LIQUIDITY_REVIEW` (CP-0, CP-1, CP-2, CP-2D)
- [ ] CP-2D (T2E.1–T2E.9 less T2E.8) proven; CCL 10-K; keys anchored on CFO
      6,218, capex 3,611, cash 1,928, customer deposits 6,831 from the owner's
      key; run.

### Task 11.3: `EARNINGS_UPDATE` (CP-0, CP-1, CP-1B, CP-2, CP-5)
- [ ] CP-1B (T4.1–T4.15) proven; two periods; keys on the delta registers; run.

### Task 11.4: `DECISION_LEDGER` and `DEEP_RESEARCH` under FULL
- [ ] CP-8 and CP-DR contracts from Phase 9 under FULL identity; whole-route
      tests; enable; keys; runs.

### Task 11.5: `RELATIVE_VALUE` live
- [ ] A real issuer pack (annual report, facility terms from an EDGAR exhibit,
      a peer/market table); keys on CP-4's covenant terms, CP-2G's drivers and
      CP-3's selection; run and verdict.

### Task 11.6: `COVENANT_REFINANCING` (adds CP-3C)
- [ ] CP-3C (T3D.1–T3D.11) proven; CCL indentures sourced; keys on maturity
      walls and the funding gap; run.

### Task 11.7: `PORTFOLIO_DECISION` (adds CP-6 and the QA_GATE)
- [ ] CP-6 (T6E/T6A) proven; the whole-route test proves `Blocked` holds CP-6
      and `Passed` releases it; the HTTP test over a canonical `read_run` with
      a QA verdict other than `Passed` (the ledger's owed test); enable; keys;
      run.

### Task 11.8: `FULL_CREDIT_ASSESSMENT` (adds CP-1A, CP-1D, CP-2E, CP-2H, CP-4C)
- [ ] Five modules proven; the CCL pack plus rating press releases and the
      hedging note; needs Phase 10 for the pack size; `NOT_YET_REACHED`
      emptied; keys; run.

### Task 11.9: `DISTRESSED_RESTRUCTURING` — held on corpus
- [ ] CP-4C's distress gate needs a distressed issuer's documents (disclosure
      statement or restructuring support agreement); the brief is written and
      held; contract tests may be written and skipped with the corpus row as
      the reason.

**Phase 11 exit:** `docs/COMPLETION_PLAN.md` Phase 11 exit checks; the
complete gate; the `gpt-5.6-sol` `xhigh` confidence review and
`gpt-6-astra` `xhigh` adversarial audit; the handoff's pathway table
complete for all eighteen.

---

## Phase 12 — Complete the Governed Workbench

**Consumes:** the whole programme's read models; remediation D2.

**Produces:** five governed writes with controls, Book over accepted
snapshots, the analysis page naming the blocking node, a safe Markdown
renderer, the journey through all of it.

### Task 12.1: Five Commands
- [ ] `WITHDRAW_SOURCE`, `GRANT_MEMBER`, `REVOKE_MEMBER`, `SAVE_REVISION`,
      `SIGN_OPINION`/`FREEZE_REVISION`/`FILE_DELIVERABLE` over `governed_write`
      with receipts, digest-bound conflicts, three independent actors checked
      at commit, the seven-identity matrix per command.

**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `Enumerate save, sign,
freeze, file and revoke interleavings across two cases and three actors. Find
any path where an actor checked before commit, a detached digest or a stale
revision authorizes different bytes than the ones reviewed.`

### Task 12.2: Controls and Availability
- [ ] Controls in Upload, Directory, Report and Committee; `ACTION_UNPLACED`'s
      clearance corrected; one available demo action.

### Task 12.3: Book over Accepted Snapshots
- [ ] A v1 `BookDocument` from named models over accepted CP-CF projections,
      from the shell D2 leaves; the passport's ten fields; the section
      enabled after real-object tests.

### Task 12.4: Analysis `blocked_by`, Renderer, Citation Page
- [ ] `blocked_by` on `AnalysisBody`; a Markdown renderer with a closed
      element set; a citation without a page refused.

### Task 12.5: The Journey
- [ ] Withdraw mid-run; save, sign, freeze, file by three actors; grant and
      revoke; Book compare — production image, three engines.

**Phase 12 exit:** O20–O22 exit checks; the complete gate; both reviews.

---

## Phase 13 — Concurrency, Durability, the Trusted Edge, the Release Pack

### Task 13.1: Async Store and `gather`
### Task 13.2: Second-Worker Safety
**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `Enumerate every two-worker
interleaving from claim through reservation, provider return, ancestor
acceptance, cancellation, lease loss, artifact acceptance and terminal event.
Identify the database predicate that prevents each stale acceptance without a
lock across transport.`
### Task 13.3: Notify, Cap, Readiness, Frame
### Task 13.4: Signed Assertion, TLS, CI Smoke
**Targeted prompt (`gpt-5.6-sol` `xhigh`):** `Trace every header, cookie,
token, assertion, proxy hop and listener that can influence Actor. Find a
deployment where a client-supplied group or a replayed assertion reaches a
governed command.`
### Task 13.5: Store Hygiene and Gate Scripts
### Task 13.6: Release Pack, Nightly, Hosted Verification
- [ ] The pack generated from the suite and the store; the first authorized
      nightly on a LITE route; hosted checks verified against the candidate on
      `main`; every advertised pathway with a current verdict or disabled.

**Phase 13 exit:** O23–O26 exit checks; the complete gate including the CI
smoke job; the `gpt-5.6-sol` `xhigh` confidence review and `gpt-6-astra`
`xhigh` adversarial audit.

## Final Verification Checklist

- [ ] No task started before its predecessor phase was accepted; Phase 9
      pathway tasks ran in parallel with Phase 10 only in disjoint worktrees.
- [ ] Every brief records exact bases, paths, APIs, REDs, sizes, commands,
      executor row and ordinary review evidence; every pathway brief
      instantiates the seven-step template.
- [ ] No key was authored from a run; every material figure was confirmed by
      the owner; every set digest is recorded with its runs.
- [ ] Every live run had its authorization line; every run's database and
      blob root are retained until its verdict or refusal is recorded.
- [ ] `gpt-5.6-sol` and `gpt-6-astra` followed
      `docs/GPT_MODEL_REASONING_MATRIX.md`; no effort exceeded `xhigh`; actual
      checkpoint settings recorded.
- [ ] No rewrite tournament ran; the remediation stream was consumed, not run.
- [ ] Unqualified, restricted, unavailable, held and disabled pathways are
      presented honestly; nothing says QUALIFIED without a signed verdict.
