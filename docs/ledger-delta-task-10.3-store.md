# Ledger delta — Completion Phase 10 Task 10.3, the successor link

Ready to paste into `CLAUDE.md`'s "Known gaps" ledger by the coordinator. This
file is not read by `tests/test_ledger.py`; every test it names is defined in
the suite (`tests/test_run_commands.py`, `tests/test_postgres_races.py`,
`tests/test_store_schema.py`, `frontend/tests/unit/run.test.tsx`).

## Replace, under **Repair Phase 2.**

The entry "BLOCKED ends the run; recovery is a new run." is replaced whole by
the entry below. The scoping the coordinator already gave it -- a readiness
verdict and nothing else, the QA_GATE case owned by "Only a QA `Passed`
releases CP-6" -- is preserved; what is added is what the link now does.

```markdown
- **BLOCKED ends the run; recovery is a new run that names it.** §39 calls an
  empty frontier with unfinished required work recoverably blocked, and
  `run_route` ends such a run `BLOCKED` with one `RUN_BLOCKED` (migration 0010).
  Nothing moves a BLOCKED run back to RUNNING: every spend guard refuses it and
  its stream closes. "Recoverable" means nothing failed and the reason is
  re-derived from the pins and accepted artifacts, not stored. §72 withdrew the
  resume for good: §61 defines the CONDITIONAL verdict as naming a source the
  effective-source set does not carry, discharged only when that source is
  supplied and CP-0 is re-run, and under invariants 1 and 10 a run's source set
  and route are pinned, so that discharge is a new run. What records it is the
  successor link, `runs.supersedes_run_id` (migration 0025): written once by
  the insert that makes the successor and refused by trigger on any later
  change, never a run's own id, at most one successor per predecessor by the
  partial unique index `runs_one_successor`, and served at both ends as
  `RunView.supersedes` and `RunView.superseded_by`. `start_run` refuses a run
  of another case with the same private `RUN_NOT_FOUND` an unknown run gets,
  any status but BLOCKED `RUN_NOT_BLOCKED`, and a second successor
  `RUN_ALREADY_SUPERSEDED` inside its own unit
  (`test_a_successor_run_links_a_blocked_run_of_its_case`,
  `test_a_successor_for_a_running_run_or_another_case_is_refused`,
  `test_two_successors_for_one_blocked_run_commit_one`,
  `test_a_runs_predecessor_is_written_once_and_is_never_itself`). The T8
  blocker cell is projected as `NodeView.gate_reason`, so a reader sees which
  source the verdict asked for. What the link does not do: a successor is an
  ordinary new run that pins its own route and input and pays for every node
  again; nothing carries an artifact across the link, and nothing checks that
  the successor's source set carries the source the verdict named -- the host
  cannot read a model's prose as a source identifier, and inventing a match
  would be a readiness ground of its own (invariant 4). The Run section offers
  `supersedes` pre-filled on a BLOCKED run nobody has answered
  (`test_a_blocked_run_not_yet_answered_offers_supersedes_prefilled`) and on
  its status alone: the brief's "source set newer than the pinned version" has
  nothing to read, because a version is minted only when a run pins its input.
  That withdrawal covers a readiness verdict and nothing else. A run also ends
  BLOCKED when the frontier empties with required work unfinished -- for a
  QA_GATE whose source is not `Passed` -- and there the discharge is a human
  decision under unchanged pins, not a supplied source. The Repair Phase 2
  entry "Only a QA `Passed` releases CP-6" owns that case and names its own
  discharge; this entry does not speak for it. *Upgrade:* a stored anchor for
  which source a successor supplied, the day a reader wants the host to say
  whether a successor answered its predecessor rather than only that it
  claimed to.
```
