# CAOS plan review — findings and documentation disposition

The resumed review corrects the execution documents while Task17f progresses.
The maintained handoff records the observed checkpoint and distinguishes
reported task acceptance from pending implementation. This review does not
accept application code or close Phase 2.
The complete original findings below refer to their original reviewed revision;
line numbers there are historical evidence, not current navigation.

| Finding | Documentation disposition | Remaining implementation evidence |
|---|---|---|
| R1 divergent plan copies | Repository REPAIR_PLAN is maintained; saved original is a pointer with a dated historical snapshot | None for documentation |
| R2 ineffective hook input | AI quality claims corrected; tracked Phase 2 hook prerequisite added | **Open:** repair hooks and pass invocation tests before Phase 2 acceptance |
| R3 conflicting authority | Decision §39 and corrected system/IA/rebuild scope resolve terminal and worker semantics | Implement and prove the scheduled terminal/worker repairs |
| R4 phase dependency/acceptance cycle | Phase 3 engineering acceptance uses existing runtime; Phase 4 owns worker; Phase 6 owns live release qualification | Corresponding phase exit proofs |
| R5 restricted analysis rejected | Valid restricted handoffs carry limitations and may proceed only as permitted | Contract tests when the adapter is implemented |
| R6 missing forecast owners | Task 5.2a proves the catalog route and canonical owners before CP-CF | Canonical owner/extension integration proof |
| R7 stale/untracked handoff | One maintained checkpoint and Task17f scope; reported acceptance evidence imported; ignored logs optional; other entry docs link to it | Task and phase acceptance remain separate; consult the handoff for current status |
| R8 size check precedes commit | Final committed candidate and real PR base are checked after review remediation | Actual range check at each task/PR acceptance |

Additional documentation corrections from the resumed pass: the attached Opus
planning guide is preserved as an explicit mode policy; release evidence is
invalidated by review changes to candidate identity; the required standalone
verifier is not made optional by a test; the system spec identifies the migration
registry/current route API; and intake cannot authorize analysis before human
gates. None of those statements claims the corresponding future feature exists.

The final reference pass also removed an invented `registry.py`/`ModuleSpec`
seam in favor of the existing `Bundle.skill_of`, clarified inherited decision
number mappings, and marked a vanished temporary frontend probe as historical,
not portable evidence.

Fresh documentation checks passed: 15 files, 125 local Markdown links, no
whitespace errors, and the goal prompt is 2,931 Unicode characters (2,938
UTF-8 bytes), strictly below 3,000. The checks also cover all five reasoning
modes, phase review cadence, forecast-owner dependency order, offline Phase 3
acceptance, the hook warning and the original-plan pointer. The repository's
pre-commit checks passed for these files; Python formatting hooks correctly
skipped this docs-only change. The first run hit a sandbox permission limit in
the EOF hook; the approved retry passed. No application changes belong to
this documentation patch. Checkpoint `5986b60` was committed locally. Its
final committed concern range `2f12a2c...5986b60` passed `make check-size` at
68 counted lines; Git inspection confirmed only the 15 documentation paths.
The eventual actual PR range and hosted checks remain binding and unverified.
Formal phase code reviews remain pending and require actual `xhigh`.
The attached guides are user-selected preferences, not independent proof that
a prompt keyword selects a particular token budget.

---

## Original adversarial findings (before these documentation corrections)

Reviewed 13 September 2026 against workbench commit
`694660b02759ce98ad230c38197ce690e6d5af21` on `codex/execute-repair-plan`.
Concurrent, uncommitted qualification work was present; it was not changed or
treated as accepted implementation.

**Verdict: BLOCK for use as an unambiguous implementation runbook.** The
documents contain conflicting authority and acceptance rules, and two claimed
developer controls do not protect the workflow as described. This is not a
claim that the current deployed application suffered a security incident.

This review uses the adversarial-reviewer skill's Saboteur, New Hire, and
Security Auditor perspectives. Findings are deduplicated and ranked by their
effect on execution. No application fixes, commits, provider calls, database
writes, or hosted changes were performed. This requested documentation audit
does not satisfy the pending whole-Phase-2 code-audit gate. The current thread's
actual reasoning setting was not independently verifiable, so no `xhigh`
gate certification is asserted.

## Scope and method

Compared the original saved `CAOS_V2_REVIEW_AND_REPAIR_PLAN.md` with the tracked
`docs/REPAIR_PLAN.md`; read the Phase 3–6 complementary plan, Claude handoff,
initialisation prompt, README, CLAUDE.md, CI gate contract, AI quality controls,
migration procedure, rebuild plan, system specification, and IA specification.
Checked relevant decision entries, Make targets, workflow, hook configuration,
PR template, size script, ignore rules, and route-extension boundary. The
attached reasoning guide was read as reference material.

Verification included harmless hook-input probes, Git tracking/ignore checks,
a read-only size-gate probe, and a pure route-resolution probe. Hosted ruleset
and Sonar observations dated 12 September were not refreshed; this report does
not certify current hosted status. Historical test counts were not rerun or
presented as current results.

## Findings

### R1 — P1: The original named plan still mandates obsolete reviews

The saved artifact at
`/Users/ericguei/.codex/visualizations/2026/09/12/01a095a3-976e-7ab3-b5b5-1bf38300215f/CAOS_V2_REVIEW_AND_REPAIR_PLAN.md`
still requires per-change confidence review, high-risk rewrite tournaments, and
`max` reasoning (lines 257–273, 524–525, 556–558). Line 269 explicitly forbids
substituting `xhigh`. Its selected route also still spells `CP-L10` as `CPL-10`
at line 369. The repository copy has the corrected policy and module spelling.

This is the exact document the user quoted. The earlier correction updated
the repository and PR template but missed this saved artifact. A reader can
therefore follow the supplied plan and violate the latest review policy.

**Correction:** designate the repository plan as the sole maintained plan;
replace the saved artifact with a clearly marked pointer or a dated snapshot
that explicitly says it is superseded. Check all four policy locations, not
just the review table. Preserve the original only as historical evidence.

### R2 — P1: The documented Claude guard hook does not inspect real hook input

`docs/AI_CODE_QUALITY.md:43` promises rejection of force pushes, commits that
bypass hooks, and unpinned installs. `.claude/settings.json:20` instead reads
`CLAUDE_TOOL_INPUT_command`; the formatter at line 9 reads `CLAUDE_FILE_PATHS`.
Neither command reads the event's JSON input.

Claude Code's [official hook contract](https://code.claude.com/docs/en/hooks#hook-input-and-output)
delivers command-hook event data on stdin. With representative JSON input and
no invented command environment variable, the actual guard returned exit 0 for
all three synthetic inputs: force push, commit with `--no-verify`, and unpinned
installation. Supplying the legacy variable as a positive control made each
return exit 2. Only the hook was run; none of the named operations executed.

**Correction:** add an explicit hook repair task using the documented input
contract, with invocation-level tests, malformed-input handling, and vendor
exclusions for formatting. Until verified, describe these as intended controls
rather than enforced protections. Hosted gates remain independent controls.

### R3 — P1: The declared authority hierarchy contradicts required repairs

The handoff and complementary plan subordinate themselves to `DECISIONS.md`.
Decision §27 (`docs/DECISIONS.md:727`) explicitly permits a run to complete
with a blocked node, while repair F02 and Phase 2 require that situation to
remain blocked. Decision §14 retains one process, and
`docs/SYSTEM_SPEC.md:32` explicitly forbids a worker; repair Phase 4 requires
one. No later inspected decision reconciles those changes. README still lists
`REBUILD_PLAN.md` as the build order; its Phase 11 repeats blocked-but-complete
behavior. The initialisation prompt instructs the builder to stop on spec
contradictions.

**Correction:** add specific reconciliation tasks before the affected repairs:
record the changed terminal semantics and worker lifecycle in new decision
entries, correct the operational specifications in place, and mark the old
rebuild phases as historical. State which document owns current phase status.

### R4 — P1: Phase 3 depends on Phase 4 and has two acceptance definitions

`docs/REPAIR_PLAN.md:399` requires a paid run through the same worker path to
exit Phase 3; that worker is introduced at line 412 in Phase 4. The
complementary plan also requires the worker path at lines 227–229 but creates
`server/engine/worker.py` only in Task 4.3. Dependent phases may not start until
their predecessor is accepted. Its lines 236–240 additionally allow an
engineering-complete Phase 3 without a paid run, while still requiring every
parent-plan exit check, including that paid run.

**Correction:** define Phase 3 acceptance over the existing runtime and
validator with a deterministic provider; place worker recovery and identical
worker-path evidence in Phase 4. Explicitly distinguish engineering acceptance
from separately authorized live qualification, and make both plans agree on
which acceptance permits the next phase.

### R5 — P1: The new task plan rejects valid restricted analysis

The complementary plan's Task 3.4, lines 230–232, requires restricted results
to be unusable downstream, grouping them with malformed and blocked results.
Decision §27 says `READY_WITH_LIMITATIONS` runs as `RESTRICTED` and carries its
limitation. `docs/IA_SPEC.md:133` requires displaying that output with its
limitation instead of promoting it to an error. The route implementation also
explicitly preserves this behavior.

**Correction:** specify separate assertions: valid restricted output remains
usable only within the permitted workflow and carries its limitations; blocked
or invalid output cannot release downstream work. Keep QA clearance as its own
contract. Do not erase restrictions to obtain an unrestricted success.

### R6 — P2: The forecast phase has unscheduled prerequisite modules

Phase 3 enables only `CP-0 → CP-L10 → CP-5`. Task 5.2 then requires accepted
CP-1, CP-2G, and CP-4 inputs, but no intervening task establishes their canonical
contracts and enables a compatible route. Existing claims-only support is not
the canonical handoff promised by Phase 3.

A pure call to the current resolver confirmed the LITE earnings route's three
modules; enabling its model extension refused with
`ROUTE_EXTENSION_OWNER_MISSING`, as `server/engine/route.py:427` requires.

**Correction:** insert a bounded prerequisite before Task 5.2 that selects a
catalog route containing all three owners, implements and proves their required
canonical handoffs, and then enables CP-CF. Alternatively leave Model explicitly
disabled and amend the promised Phase 5 output. Do not fabricate missing inputs
or add arbitrary nodes to the LITE route.

### R7 — P2: The tracked handoff is stale and its binding evidence is untracked

`docs/CLAUDE_CODE_HANDOFF.md:14` still identifies the unfinished Task17d2
checkpoint and later says to finish that task first. `docs/REPAIR_PLAN.md:8`
says Task17d3 is next; README still calls Task17d2 incomplete. At the reviewed
commit, `CLAUDE.md:18` records Task17d3 and Task17e accepted, with Task17f next.

The handoff calls `.superpowers/sdd/task-17d2-brief.md` binding and refers to a
"tracked brief", but `git check-ignore -v` proves the brief, later task brief,
and progress ledger are ignored. `git ls-files .superpowers` includes only the
Task 0 report. The advertised fresh-clone initialisation therefore cannot
recover the current binding scope or the acceptance evidence from Git.

**Correction:** keep one tracked current checkpoint/brief with exact final
acceptance commits and compact evidence; have other documents link to it.
Ignored logs may remain supplementary. Distinguish same-machine scratch
recovery from a reproducible handoff, and supply a fallback for absent logs.

### R8 — P2: The size gate runs before it can see the proposed change

Handoff acceptance step 5 (`docs/CLAUDE_CODE_HANDOFF.md:194`) runs
`make check-size`; step 7 makes the commit. The called script measures only
`base...HEAD` (`scripts/check_pr_size.py:34`), excluding staged and unstaged
work. Thus the documented order cannot verify a newly implemented slice.

Read-only reproduction: with 161 additions/removals in three uncommitted
qualification files, `scripts/check_pr_size.py HEAD` reported
`changed lines: 0`. This demonstrates the measurement scope, not an accusation
that those in-progress changes were accepted or exceeded 800 lines.

**Correction:** after committing and any review remediation, run the final
gate over the recorded base and actual candidate commit before task acceptance.
Keep an earlier working-tree estimate if useful. Separately validate every
eventual PR against its real target base; a task base is not automatically a
valid hosted PR base.

## Repair order and completion evidence

1. Resolve R1/R3/R7 so there is one policy, one active checkpoint, and one
   current specification hierarchy. Preserve historical evidence explicitly.
2. Correct R4/R5/R6 so phase inputs, permitted restricted states, and exit
   assertions describe a build that can actually be completed in order.
3. Schedule the R2 hook repair as its own ordinary implementation slice and
   correct R8's gate timing without weakening the hosted 800-line ceiling.
4. Walk the revised instructions from a fresh checkout and record where each
   prerequisite, command, acceptance record, and phase transition comes from.

The repository policy and PR template already agree that confidence review
and a separate adversarial code audit run only at phase completion, both at
actual `xhigh`, with no rewrite tournament. Retain that policy. The missing
correction is its propagation to the original supplied artifact and the other
execution inconsistencies described above.
