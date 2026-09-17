# Completion Phase 7 exit evidence

Candidate: `codex/execute-repair-plan` at `814c387`, with the remediation
stream's wave 1 merged on top at `6eb7fef`. This record maps every
`docs/COMPLETION_PLAN.md` Phase 7 exit check to the evidence that demonstrates
it. It is evidence for acceptance, not acceptance: the handoff's Phase 7 record
holds the complete gate, the whole-phase confidence review and the separate
adversarial audit, and names the model and effort each ran at.

The phase is three commits plus two housekeeping ones:

| Commit | What |
|---|---|
| `c8b5e29` | the completion plan for Phases 7–13 and its task briefs |
| `8b1fac6` | Task 7.1: the ledger gate, two struck entries, two withdrawn upgrade paths, the relabelled headings, six regenerated status rows, the filed audits, the handoff table |
| `729e2cf` | Task 7.2's delivery record and Phase 8 Task 8.5's five vendor requests |
| `2b5103e` | Phase 8 Task 8.4, the document register (in the range, not in this phase's scope) |
| `814c387` | the concurrent stream's records tracked; the generated instruction file ignored |

## 1. `tests/test_ledger.py` passes, and no entry names a state a later decision closed

`tests/test_ledger.py` holds six tests over `scripts/ledger_state.py`:

| Test | What it refuses |
|---|---|
| `test_every_test_a_ledger_entry_cites_exists_in_the_suite` | an entry citing a test the suite does not define, so a gap recorded as guarded is guarded |
| `test_no_exempt_name_has_quietly_been_written` | an exemption that has come true, so the excuse list cannot outlive its reasons |
| `test_every_open_ledger_entry_states_its_upgrade_path` | an open entry with no `*Upgrade:*` clause, which is the shape of an entry closed without being struck |
| `test_the_reader_found_the_whole_ledger` | a reader that matched too little, which would make the two rules above vacuous |
| `test_a_contract_with_no_ledger_heading_refuses` | a silently empty ledger |
| `test_the_reader_separates_struck_entries_from_open_ones` | the one distinction every rule rests on |

Run at the candidate: `tests/test_ledger.py` and `tests/test_gate_scripts.py`
together, 58 passed. `scripts/ledger_state.py --report` reads 110 entries, 37
closed and 73 open, against 108/35/73 before the phase: two entries struck, two
added.

The two entries struck were each verified in source first, and the verification
is the evidence, not the commit message:

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

**What this check does not cover, stated because the gate cannot cover it.**
Neither struck entry would have been caught by any rule in this file: both were
fluent, cited no test, and kept their upgrade clause while becoming false.
Phrase-based rules were measured against the real ledger and rejected — the best
flagged three entries, one the real defect and two correct entries using the
same words. The limit is recorded in the ledger itself under "Completion
Phase 7", and what closes the class is the plan's definition of done, that the
entry a task closes is struck in the commit that closes it.

Two upgrade paths were withdrawn rather than carried forward, each on a fact:

- The predicates entry asked for an evaluator. The vendored catalog declares 60
  REQUIRED, 26 OPTIONAL, 29 ADVISORY and one QA_GATE typed edge and **no**
  CONDITIONAL edge, so the blocking branch is unreachable and a grammar would be
  code for a route that does not exist. Phase 10 Task 10.2 pins the counts and
  refuses `ROUTE_EDGE_UNSUPPORTED` instead.
- The BLOCKED entry asked for a governed resume. §61 discharges a CONDITIONAL
  verdict only by supplying the named source and re-running CP-0, and under
  invariants 1 and 10 a run's source set and route are pinned, so the discharge
  is a new run and a CAS back to RUNNING would reopen a run whose pins cannot
  change. Phase 10 Task 10.3 records a successor link instead.

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
tip. Both records were corrected rather than left standing, which is
the rule this phase's own ledger gate exists to enforce. T1 to T6 are therefore
in the branch and T2, T3 and T5 are met; waves 2 to 4 have no branch, so T7, T8,
T11, T13 and D2 are not.

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

Three facts the record states plainly: #281 and #285 are recorded MERGED but
merged into sibling PR branches rather than `main`; #275 is the only over-cap
merge since #258 and its body carries no split proof, which the standing
authorization requires; #296 is open and failing `size` at 879.

## 4. Nothing under the repository root is untracked except `.claude/`

`git status --short` at the candidate lists `.claude/skills/` alone. `AGENTS.md`
is in `.gitignore` with its reason, being written by GitNexus from the same index
as the block appended to `CLAUDE.md`. The concurrent stream's review and plan are
tracked unmodified at `814c387`, because three of this phase's commits cite them.

## What this phase did not do

- It did not edit `docs/REPAIR_PLAN.md`, which is accepted and is the owner's.
- It did not run any remediation task, review or phase close. That stream is
  consumed, not owned.
- It did not push, open, merge or close a pull request, change a ruleset, or make
  a provider call.
- It did not correct the stale claim-ledger row in the concurrent stream's own
  review, which that stream owns.
