# Completion Phase 7 exit evidence

Candidate: `codex/execute-repair-plan` at the commit that adds this record, whose
parent is `da475c7`. This record maps every `docs/COMPLETION_PLAN.md` Phase 7
exit check to the evidence that demonstrates it. It is evidence for acceptance,
not acceptance: the handoff's Phase 7 record holds the reviews and the gate, and
names the model and effort each ran at.

**What has and has not been run at the candidate.** `make check`, the complete
offline gate, **has not been run** on this candidate. What has:

| Gate | State at the candidate |
|---|---|
| `tests/test_ledger.py`, `tests/test_gate_scripts.py` | 59 passed |
| the offline backend suite (`make test`) | run; the result is in the handoff's Phase 7 record |
| `ruff check .`, `ruff format --check`, `mypy scripts tests server` | clean |
| `scripts/check_tested.py`, `check_vocabulary.py`, `io_budget.py --assert` | clean |
| `make smoke-production` | the production image built and the real-stack journey ran, 15 passed |
| `make image` | **not run.** The gate pins Trivy 0.70.0 and the machine has 0.72.0; substituting a version would be changing a gate to get a pass |
| the whole-phase confidence review and the adversarial audit | both run at `xhigh`, and their remediation is in the candidate |

The phase's commits, in order. Two of them are later phases' work that landed in
the same range and are named so the range is not read as Phase 7's alone:

| Commit | Phase | What |
|---|---|---|
| `c8b5e29` | 7 | the completion plan for Phases 7–13 and its task briefs |
| `8b1fac6` | 7 | Task 7.1: the ledger gate, two struck entries, two withdrawn upgrade paths, the relabelled headings, six regenerated status rows, the filed audits, the handoff table |
| `6fa946a` | 7 | a test helper corrected for the roles the merge changed |
| `2b5103e` | 8 | Task 8.4, the document register |
| `729e2cf` | 7 | Task 7.2's delivery record and Phase 8 Task 8.5's five vendor requests |
| `2f9d54a` | — | the remediation stream's first wave and what it gave up (`docs/DECISIONS.md` §70) |
| `814c387` | 7 | the concurrent stream's records tracked; the generated instruction file ignored |
| `d88061e` | 8 | Task 8.1: a key can name a register cell, and a miss stops a signature |
| `1921448` | 9 | Task 9.1: `LITE_PORTFOLIO_DECISION`, the third enabled pathway |
| `fa6bbfe` | 7 | the confidence review's two P2s |
| `da475c7` | 8, 9 | the portfolio set's register key and the journey's route count |
| this commit | 7 | the adversarial audit's P1, its P2s and its cheap P3s |

## 1. `tests/test_ledger.py` passes, and no entry names a state a later decision closed

`tests/test_ledger.py` holds seven tests over `scripts/ledger_state.py`:

| Test | What it refuses |
|---|---|
| `test_every_test_a_ledger_entry_cites_exists_in_the_suite` | an entry citing a test the suite does not define, so a gap recorded as guarded is guarded |
| `test_no_exempt_name_has_quietly_been_written` | an exemption that has come true, so the excuse list cannot outlive its reasons |
| `test_every_open_ledger_entry_states_its_upgrade_path` | an open entry with no `*Upgrade:*` clause, which is the shape of an entry closed without being struck |
| `test_the_reader_found_the_whole_ledger` | a reader that matched too little, which would make the two rules above vacuous, now asserting the whole declared phase set rather than a count |
| `test_a_contract_with_no_ledger_heading_refuses` | a silently empty ledger |
| `test_the_reader_separates_struck_entries_from_open_ones` | the one distinction every rule rests on |
| `test_a_heading_without_a_blank_line_before_it_is_refused` | the failure below, made into a rule |

Run at the candidate: `tests/test_ledger.py` and `tests/test_gate_scripts.py`
together, 59 passed. `scripts/ledger_state.py --report` reads 111 entries, 38
closed and 73 open, against 108/35/73 before the phase: three entries struck,
three added. The open count is unchanged by coincidence, not by cancellation.

The three entries struck were each verified in source first, and the
verification is the evidence, not the commit message:

- "A verdict is read and not stored" claimed there is no `qualification_verdicts`
  table. `server/store/0018_qualification_verdicts.sql` creates it,
  `server/qualification/store.py::record_verdict` writes it under its bindings,
  and §65's `POST /api/v1/qualification/{evidence_sha256}/verdict` is the route.
- "A proof is held and not stored" claimed no table holds a proof.
  `server/qualification/store.py::_performed_document` serialises each case's
  proof — `run_id`, `route_digest`, `build_id`, `artifacts`, `citations` and the
  `anchored` set — into `qualification_performed.performed_json`
  (`server/store/0020_qualification_performed.sql`), and `record_performed`
  reads the row back for equality before `performed_sha256` binds it.
- "`budget_ledger` records a charge and enforces no ceiling" claimed there is no
  provider call to reserve against. §40 reserves `pricing.worst_case` before
  every call and `run_route` refuses a price for any model but the configured
  one, so the entry described a tree two phases old.

**The failure this phase's own gate was written after.** `8b1fac6` deleted the
blank line before `**Phase 2.**` while rewriting the entry above it, and
`fa6bbfe` then made a heading require a blank line before it. Together they
stopped that heading being read, silently moved its four entries under the phase
above, and left the entry count identical — so the one signal the remediation
relied on, that the counts had not moved, was exactly the signal that could not
see it. Found by the adversarial audit, not by the gate. The blank line is
restored, `entries` now **raises** on an unseparated heading rather than
absorbing it, `_readable` refuses any list marker but this ledger's, and
`test_the_reader_found_the_whole_ledger` asserts the whole `EXPECTED_PHASES` set.

**What this check does not cover, stated because the gate cannot cover it.**
None of the three struck entries would have been caught by any rule in this
file: each was fluent, cited no test, and kept its upgrade clause while becoming
false. Phrase-based rules were measured against the real ledger and rejected —
the best flagged three entries, one the real defect and two correct entries
using the same words. The plan and Task 7.1's brief each specified such a rule
before it was measured, and both now say it was not built and why. The limit is
recorded in the ledger under "Completion Phase 7", and what closes the class is
the plan's definition of done, that the entry a task closes is struck in the
commit that closes it.

Two upgrade paths were withdrawn rather than carried forward, each on a fact:

- The predicates entry asked for an evaluator. The vendored catalog declares 60
  REQUIRED, 26 OPTIONAL, 29 ADVISORY and one QA_GATE typed edge and **no**
  CONDITIONAL edge, so the blocking branch is unreachable and a grammar would be
  code for a route that does not exist. The counts were already pinned by
  `tests/test_bundle_pin.py::test_the_catalog_declares_no_conditional_edge`,
  which the rewrite did not know and the audit found; what Phase 10 Task 10.2
  still owes is `ROUTE_EDGE_UNSUPPORTED` at resolution.
- The BLOCKED entry asked for a governed resume. §61 discharges a CONDITIONAL
  verdict only by supplying the named source and re-running CP-0, and under
  invariants 1 and 10 a run's source set and route are pinned, so the discharge
  is a new run and a CAS back to RUNNING would reopen a run whose pins cannot
  change. Phase 10 Task 10.3 records a successor link instead. The withdrawal is
  scoped to a readiness verdict: a run whose frontier empties against an unmet
  QA_GATE is the Repair Phase 2 entry's case, with its own discharge, and this
  one does not speak for it.

## 2. The handoff names this plan and the remediation stream's state

`docs/CLAUDE_CODE_HANDOFF.md`'s checkpoint table carries a "Completion plan" row
and a "Remediation stream" row, and its Phase 7 Task 7.2 record carries the
stream's per-wave state determined from commits rather than from plan checkboxes.

That state moved while this phase was being written, which is itself part of the
evidence. When the record was first written, wave 1 was integrated only on a
local-only `sdd/integration-wave1`, observed at `86b0cd0`; that branch was then
rebased onto this phase's commits, abandoning `86b0cd0`, and merged into this
branch at `6eb7fef` whose second parent is the new tip `266ee28`
(`docs/DECISIONS.md` §70). Both hashes were real when read and only one is
citable now, which is why the record names the merge rather than an integration
tip. Both records were corrected rather than left standing, which is the rule
this phase's own ledger gate exists to enforce. T1 to T6 are therefore in the
branch and T2, T3 and T5 are met; waves 2 to 4 have no branch, so T7, T8, T11,
T13 and D2 are not.

Two consequences of that merge bind later tasks. `server/api/app.py`'s `_STATUS`
map is now exhaustive over `RefusalCode` with a `_STATUS[code]` lookup, so any
task adding a refusal code must add its status in the same commit or a `KeyError`
replaces a typed refusal; and §53.3 is superseded by §70.2, under which a groups
header with neither an edge token nor the trust switch no longer chooses a global
role.

## 3. Every merged PR since #258 has a row with hosted results, and no hosted status is described from a local run

`docs/CI_DELIVERY_SPLIT_PLAN.md` carries the per-PR table with a "landed as"
column; the handoff's Task 7.2 record carries the summary and the three
discrepancies. Sizes are the hosted `size` job's own log, because
`scripts/check_pr_size.py:39` diffs `{base}...HEAD` with `HEAD` hardcoded and so
cannot measure an arbitrary PR without a checkout — and its three-dot diff
overcounts once a predecessor was squash-merged, measured at 790 hosted against
1,555 local on #263 and 234 against 1,716 on #272.

Two rows carry no size and say why rather than reading `0`: #281's and #285's
head commits are gone from the remote, so `gh pr checks` answers "no commit
found" and their checks are last-observed from the commit's check-runs rather
than re-read. Three bases are explained by no head or landed commit in the
table and are recorded as unexplained rather than corrected, because correcting
them needs a hosted read this session did not make.

Three facts the record states plainly: #281 and #285 are recorded MERGED but
merged into sibling PR branches rather than `main`; #275 is the only over-cap
merge since #258 and its body carries no split proof, which the standing
authorization requires; #296 is open and failing `size` at 879.

## 4. Nothing under the repository root is untracked except `.claude/`

`git status --short` at the candidate lists `.claude/skills/` alone. `AGENTS.md`
is in `.gitignore` with its reason, being written by GitNexus from the same index
as the block appended to `CLAUDE.md`. The concurrent stream's review and plan are
tracked unmodified at `814c387`, because three of this phase's commits cite them.

## The status inventory is a dated record, and was not made to resolve

The adversarial audit asked that `docs/feature-status.csv`'s citations be made to
resolve. They were not, deliberately, and the disagreement is recorded rather
than settled quietly. 206 of its 248 rows are dated, 198 of them 2026-09-11, and
nine test names across 14 rows name tests `9bf20b2` wrote and the repair deleted
with the code they covered. A dated row whose evidence is edited later stops
being a record of that date, so rewriting those rows would buy agreement with
the tree by giving up the property that makes the file worth keeping. The limit
is now a ledger entry with its own upgrade path, and the ledger gate reads this
file not at all. What the audit's finding did produce: `fa6bbfe` had rewritten
all 249 line endings from CRLF to LF while changing six rows, making its own
diff unreadable and its message untrue. The bytes are restored and pinned in
`.gitattributes`.

## What this phase did not do

- It did not edit `docs/REPAIR_PLAN.md`, which is accepted and is the owner's.
- It did not run any remediation task, review or phase close. That stream is
  consumed, not owned.
- It did not run `make check` or `make image`, for the reasons in the table above.
- It did not push, open, merge or close a pull request, change a ruleset, or make
  a provider call.
- It did not correct the stale claim-ledger row in the concurrent stream's own
  review, which that stream owns.
