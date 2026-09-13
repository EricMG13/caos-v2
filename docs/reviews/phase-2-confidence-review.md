# CAOS Repair Phase 2 — whole-phase confidence review

- **Model:** Claude Opus 5 (`claude-opus-5`)
- **Effort:** I can't see this session's reasoning-effort setting from inside the
  session. The Build session asked for `xhigh`, but I can't confirm it, so
  **this report is not proof of the "actual `xhigh`" gate** in
  `docs/PHASE_2_EXIT_EVIDENCE.md`. Whoever records acceptance has to confirm the
  effort level outside the session.
- **Target:** main checkout `/Users/ericguei/Documents/caos-workbench`,
  `codex/execute-repair-plan` at `a5ff1d0`. Range `59d3145..a5ff1d0`, excluding
  the docs-only commits `8015c43` and `3c4c698`.
- **Method:** `~/.claude/skills/confidence-review/SKILL.md` run read-only. I
  traced the code and its callers by hand.
  - I made no edits, commits, provider calls, database commands or test runs.
  - The only commands I ran were `git` reads, `grep`/`sed`/`cat`, three
    stdlib-only `shlex` tokenisation checks, and one `ls` of the system
    `python3` bin directory.
- **Authority:** `docs/REPAIR_PLAN.md` Phase 2, `docs/DECISIONS.md` §39 and §40,
  the `CLAUDE.md` invariants, and the "Repair Phase 2" known-gap entries. I
  treat those entries as accepted and don't re-report them unless they are
  wrong.

---

## CONFIRMED findings

### F-1 [P2] The qualification harness accepts a price its route can never afford, pays for one real call, then stops

- **Where:**
  - `server/qualification/harness.py:384-386` (`_affordable`)
  - `server/qualification/harness.py:296-312` (`perform` loop)
  - `CLAUDE.md:566-573` (Phase 5 ledger entry for the price source)
- **What:** `_affordable` refuses only when **one** call's worst case is above
  `CEILING`. Every harness case pins a route, and the suite's selection is
  `DEEP_RESEARCH` (CP-0 then CP-DR, `tests/test_qualification_harness.py:85`).
  A two-node route needs at least `2 × worst_case(price)` of the run's `$5.00`.
  - Reservations are never released.
  - `_remaining` subtracts `greatest(reserved, charged)` for each attempt.
- **Failure scenario:** a harness price of `$3/M` input and `$15/M` output. This
  is the ledger's own example.
  1. `worst_case = 1,048,576 × 3e-6 + 32,768 × 15e-6 ≈ $3.637`, which is not
     above `$5.00`, so `_affordable` passes.
  2. `perform` → `_perform_one` → `run_route`.
  3. CP-0 reserves `$3.637`, calls the live provider (a real charge) and is
     accepted.
  4. CP-DR's `reserve` sees `$5.00 − $3.637 < $3.637` and refuses
     `BUDGET_CEILING_REACHED`.
  5. The case records `stopped`, the set stops, and no matrix is built.

  Every set at any price with `CEILING/2 < worst_case ≤ CEILING` pays for a
  call it already knew could not lead to a finished run. The ledger text at
  `CLAUDE.md:572-573` says "a qualification harness refuses such a price up
  front". That is false for this exact example: the harness refuses only above
  `$5.00`.
- **Why it matters:** this is the class of waste `_affordable`'s docstring
  exists to prevent ("refuses the operation that would breach it *before* it
  happens"). It is also an incorrect ledger entry, which `CLAUDE.md` itself
  calls "the same defect as a missing one".
- **Smallest root-cause fix:**
  - In `perform`, the `_eligible` pass at `harness.py:296-298` already returns
    each case's pinned route before any case runs. Keep those routes and refuse
    `QUALIFICATION_SET_OVER_CEILING` when
    `worst_case(harness.price) * len(route.nodes) > CEILING` for any case. That
    replaces the single-call check at line 385.
  - Correct the `CLAUDE.md:572-573` sentence.
  - Regression test: a two-node `DEEP_RESEARCH` case priced so that
    `CEILING/2 < worst_case ≤ CEILING` is refused, with zero `run_attempts`
    rows and `provider.calls == []`.
  - `len(route.nodes) × W` is a floor, not a bound: an analytical refusal
    re-reserves. The floor is still enough to refuse every provably doomed set.
  - *Optional, same idea one level down:* `run_route` could refuse before its
    first attempt when `remaining < unaccepted_nodes × W`. That isn't needed for
    F06's exit, which refuses per call.

### F-2 [P2] Ordinary git syntax bypasses the force-push and no-verify guard

- **Where:** `scripts/claude_hook.py:86-99` (`_token_reason`) and
  `scripts/claude_hook.py:102-107` (`_forced`).
- **What:**
  - The subcommand only matches when the word right before it is exactly
    `git`: `before == "git" and word == "push"` / `"commit"`.
  - `_forced` only recognises the exact tokens `--force` and
    `--force-with-lease`.
- **Failure scenarios.** I checked the tokens with stdlib `shlex` using the
  hook's own settings (`posix=True, punctuation_chars=True,
  whitespace_split=True`). Each of these is allowed with exit 0:
  - `git -C /Users/ericguei/Documents/caos-workbench push --force origin x`:
    the tokens are `['git','-C','<path>','push',...]`, so `before` is the path.
    This is the form the coordinating session tells reviewers to use for
    history.
  - `git -c core.hooksPath=/dev/null commit -n -m x` and `git -C . commit -n`:
    the same `before` problem, for no-verify.
  - `git push --force-with-lease=main:abc origin main`: the token stays whole,
    because `=` is a word character under `punctuation_chars`, so it is not in
    `{"--force","--force-with-lease"}`. It is not a short flag, and it has no
    `+` prefix.
  - `/usr/bin/git push -f`: `before == "/usr/bin/git"`.

  The inline guard this replaced matched the substring `push --force`, which
  caught the `-C`, `-c` and `--force-with-lease=` forms. That guard read
  unset variables, so it never actually ran, but the ruleset is narrower than
  the one it replaced.

  The module docstring's "a command built to hide its intent at run time
  passes" reasonably covers `bash -c '…'` and `eval`. `git -C` is not hiding
  anything.
- **Smallest root-cause fix:**
  - In `_token_reason`, find the git subcommand by skipping git's global
    options:
    - options that take a value: `-C`, `-c`, `--git-dir`, `--work-tree`,
      `--namespace`, `--exec-path`
    - boolean options: `--no-pager`, `-p`, `--bare`, `--no-replace-objects`
    - any `--opt=value` token
  - Match the command word by basename (`Path(word).name == "git"`).
  - In `_forced`, treat any argument starting with `--force` (and `--mirror`)
    as forced.
  - Add the three examples above to
    `test_the_guard_refuses_forbidden_commands`.

### F-3 [P3] `env` with options and no command still prints the environment

- **Where:** `scripts/claude_hook.py:96-98`.
- **What:** the rule refuses `env` only when `until` is empty.
- **Failure scenario:** `env -u CAOS_REQUIRE_PROVIDER` on its own has `until` of
  `['-u','CAOS_REQUIRE_PROVIDER']`, which is not empty, so the guard allows
  it. The command prints every other variable, including
  `OPENROUTER_API_KEY`, into the transcript. `env -0` behaves the same way.
- **Smallest fix:** drop `env`'s option words (`-u NAME`, `-i`, `-0`, `-v`,
  `-S`, `--unset=…`) and `NAME=value` assignments from `until`, then refuse
  when no command word is left. Add `env -u X` and `env -0` to the refused
  cases.

### F-4 [P3] In a worktree with no venv, the format hook formats nothing and reports a failure on every edit

- **Where:** `scripts/claude_hook.py:150-159` and the fallback in
  `.claude/settings.json:9`.
- **What:**
  - When `$CLAUDE_PROJECT_DIR/.venv/bin/python` is missing, the settings
    command falls back to `python3`.
  - `format_file` then looks for `ruff` next to that interpreter.
  - It looks for `prettier` at `<worktree>/frontend/node_modules/.bin/prettier`.
- **Failure scenario:**
  - Checked on this host: `python3` resolves to
    `/opt/homebrew/opt/python@3.14/bin`, and there is no `ruff` there.
  - The implementers §39 authorises run in isolated worktrees (the
    `.claude/worktrees/*` checkouts listed by `git worktree list` have no
    `.venv`). In those, every Python Write or Edit hits `OSError` → `2` →
    `HOOK_FORMAT_FAILED`, and nothing is formatted.
  - `.ts`, `.tsx` and `.css` edits fail the same way without `node_modules`.
  - A PostToolUse exit 2 doesn't block anything, so this is noise plus a
    formatter that silently does nothing. Lint still catches the formatting
    later.
- **Relation to tests:** `test_the_wired_guard_blocks_through_the_shell`
  covers only the guard on a bare project.
- **Smallest fix:**
  - When the pinned tool is absent, exit 0 with one `HOOK_FORMAT_SKIPPED` line
    rather than reporting a failure.
  - Or resolve `ruff` from `$CLAUDE_PROJECT_DIR/.venv/bin` the same way the
    interpreter is resolved.
  - Add a bare-project test for `format`.

---

## Least confident about (ranked), with verdicts

1. **Harness affordability versus route length.** *CONFIRMED*, F-1.
2. **The hook guard's token model.** *CONFIRMED*, F-2 and F-3. The formatter
   fallback is *CONFIRMED* as F-4.
3. **Fresh authority at acceptance** (`runs._accept_artifact:190-209`).
   *Fine.*
   - `_locked_attempt` takes the case lock, then the run lock.
   - `approved_run_input` re-takes the same locks in the same order, then
     checks RUNNING, the pinned input, **every** captured member live with
     unchanged document and extraction identity (`_sources_live`), and both
     gate approvals with the approver's current standing.
   - It then checks that the attempt's node is in the pinned route and has no
     other accepted owner, and inserts.
   - All of this is one transaction under the case lock that `governed_write`
     also takes first, so no revocation or withdrawal can commit between the
     check and the insert.
   - `record_outcome` commits before this unit, so a refusal can't erase the
     bill.
   - The exact-replay path (`row == values → False`) deliberately skips the
     authority check, and that is proven by
     `test_exact_replay_never_rechecks_authority_or_duplicates`.
4. **Lock order and deadlock risk** across `lock_run`, `approved_run_input`,
   `_locked_attempt`, `reserve`, `append` and `governed_write`. *Fine.* Every
   path takes the case row `FOR UPDATE` before the run row `FOR UPDATE`, and
   `run_attempts` rows are only `FOR KEY SHARE` after both. I found no reversed
   order.
5. **Host-derived context and the recheck after the call**
   (`executor.execute_module:382-434`). *Fine for one sequential worker.*
   - The pre-call unit, in order:
     - `check_call`: the attempt identity, RUNNING, no foreign owner, a
       reservation, and no outcome, ledger or artifact.
     - `_stored_identity`: the full `execution_input` with the actual `Bundle`,
       and equality of stored route, node and module.
     - `_context`: evidence from `_CAPTURED` (the pinned source-set version)
       through `read_run_block`, `gate_expects` from the pinned nodes,
       upstream from accepted artifacts with a build and authority check, and
       the QA flag from pinned edges.
   - After the call, the order is: the outcome is committed first, then
     `check_attempt`, then `_stored_identity` again, then upstream digests are
     compared, and only then `_envelope`.
   - Nothing the caller supplies (the `Assignment` is identity only) reaches
     the prompt.
   - Refusals raise `from None`, so no document text leaks.
6. **One accepted owner per node**, covering migration 0009,
   `outcomes.accepted_owner`, `start_attempt` and `_accept_artifact`. *Fine.*
   - The ownership check runs under the run lock and is backed by
     `UNIQUE (run_id, route_node_id)`.
   - The composite foreign key `(run_id, attempt_id, route_node_id) →
     run_attempts` refuses a node that names the wrong attempt.
   - The BEFORE INSERT trigger fills the node from the attempt, and a missing
     attempt gives NULL, which `NOT NULL` refuses.
   - Existing rows are backfilled by joining on `attempt_id`.
   - On a populated database, a duplicate owner or a mismatched run makes the
     constraint fail, and the whole migration rolls back.
   - `artifact_digests` no longer needs an ordering to choose a winner. That
     removes "latest wins", which the plan forbids.
7. **BLOCKED as a terminal state** (`runtime.run_route:137-144`, 0010,
   `RunStatus`, `RunEvent`, `stream.TERMINAL`). *Fine for Phase 2.*
   - Every spend or progress guard refuses anything that isn't RUNNING:
     `start_attempt`, `reserve`, `check_attempt`, `approved_run_input`,
     `routes.py:66` and `run_inputs.py:224`.
   - `_transition` is conditional, so exactly one event is written.
   - `_accept_artifact` returns False for a run that isn't RUNNING, and late
     outcomes are still recorded.
   - The 0010 event list equals 0007's plus `RUN_BLOCKED`.
   - The API's `RunDocument.status` is a `str`, so `BLOCKED` validates.
   - The frontend is not wired to run status: the Phase 9 known gap. The
     guardrail "frontend contracts" therefore has nothing to update yet.
   - Terminal events can't race in a sequential loop: an accepted set only
     grows, and an in-flight node that hasn't been accepted stays in the
     frontier.
8. **QA releases only on `Passed`** (`envelope.parse_qa`, `route._unmet` and
   `_qa_passed`, `runtime.accepted_artifacts`, `app._node_view`). *Fine.*
   - The QA source's body is loaded wherever `node_states` runs: the runtime,
     the API, and the harness through `accepted_artifacts`.
   - The harness fallback `{}` makes CP-6 BLOCKED, which fails closed.
   - `Not Reviewed` is refused as a verdict.
   - A module that isn't a QA source and emits `qa_status` is refused
     `ENVELOPE_UNDECLARED_FIELD`.
   - The canonical bytes of artifacts that aren't QA sources are unchanged.
   - A CP-5 artifact accepted before this change has no `qa_status`, so it
     leaves CP-6 BLOCKED, which fails closed. No deployment holds data.
9. **Priced reservations** (`pricing.worst_case`, `runtime`). *Fine.*
   - An exact context with `Inexact`, `Overflow` and `InvalidOperation`
     trapped refuses anything that isn't exact.
   - `validate_spend` runs on the inputs and on the result.
   - Zero is refused.
   - The model identity is checked per run and per call before
     `start_attempt`.
   - The byte bound is enforced on the encoded payload
     (`provider.py:278`), so input tokens are at most the payload bytes. The
     only exceptions are a few chat-template tokens, which the JSON framing
     bytes outnumber.
   - An overrun makes `_remaining` negative, so the next reservation is
     refused (`test_an_overrun_charge_stops_the_next_node_before_its_call`).
10. **Proof and provenance** (`proof.py`). *Fine.*
    - The pinned nodes are checked before anything else.
    - `load_run_input` is checked against the bundle build, manifest and
      adapter version.
    - Each artifact needs its stored call outcome with a matching
      `(model, generation_id)`.
    - Citations resolve only through the run's captured members that are still
      live with unchanged identity. A copy admitted after the pin, or
      re-admitted, has a different `source_id` and can't support the proof.
    - Duplicate digests resolve deterministically (the smallest `source_id`).
11. **`Unrun.attempts`** (`harness._unrun:501-512`). *Fine.* Reservations,
    outcomes and the ledger each have at most one row per attempt, so the LEFT
    JOINs can't multiply rows. "Reserved, no outcome" is correctly described as
    *possible* spend: it also covers a refusal before the call, which is the
    conservative reading.

---

## Verified fine (and how)

- **Authority at acceptance and lock ordering:** points 3 and 4. I traced every
  `lock_run`, `lock_case` and `FOR UPDATE`/`FOR KEY SHARE` in `runs.py`,
  `outcomes.py`, `budget.py`, `events.py`, `gates.py` and `cases.py`.
- **No transaction is held across the provider call:**
  - `execution_reads` rolls back before `provider.complete`, and
    `require_idle` runs before and after it.
  - `runtime._run_node` calls `require_idle` before `record_outcome`.
  - This follows the plan's Phase 2 work item 6.
- **Billing is independent of analysis:**
  - The executor's `record_outcome` commits before the refusal and analysis
    checks.
  - The runtime's second `record_outcome` with the same
    `(charge, model, generation)` is an exact no-op replay: `_record` compares
    the stored row, with Decimal equality by value.
  - `_accept` calls it again before `_accept_artifact`.
- **Withdrawal during an in-flight call:** `_sources_live` covers **all**
  captured members, both in the post-call `_stored_identity` and again inside
  `_accept_artifact`. A withdrawn source that no claim cites still refuses
  acceptance.
- **Refusals don't leak text:** every new refusal in `executor._stored_claims`,
  `_context` (through `read_run_block`), `parse_qa` and `worst_case` is raised
  `from None` with a typed code. The hook's stderr carries fixed constants
  only.
- **Migrations:** 0009 and 0010 are appended to `MIGRATIONS` in order.
  `schema.sql` stays the untouched `0001_legacy` baseline, which is the
  documented rule. The 0010 constraint names match those created in
  `schema.sql`, 0005 and 0007.
- **Stream:** `TERMINAL` includes `RUN_BLOCKED`, and the tail and `_frames` both
  return on it. Membership is still rechecked before each event.
- **Runtime model check against the executor's recorded model:**
  `ModuleProvider.model` is `completions.model`, the same value
  `execute_module` records through `producer_identifier(provider.model)`.
- **`Assignment` positional construction** (`runner.py:84-86`): it matches the
  field order `module_id, run_id, node, route, attempt_id`.
- **Dotenv regex:** checked by reading against `.env`, `./.env.local`,
  `.env-prod`, `.envrc`, `.env.example` and `os.environ`. It refuses a path and
  allows words.
- **Symlink targets in `format_target`:** paths are resolved before the vendor
  and in-repo checks, so a symlink into `vendor/` is skipped.

## By design / accepted (not re-reported)

- The known-gap entries cover the following. Each reads as accurate against the
  code, except the one F-1 corrects:
  - QA `Restricted` blocks CP-6, and the verdict is the module's own
    self-report.
  - A BLOCKED run can't be resumed, so recovery is a new run.
  - The terminal decision is read outside the run lock.
  - Two workers can pay for one node, and `artifacts` rows are not immutable.
  - The price comes from the caller, and the byte bound is severe.
- **Gap between the final pre-call check and the call:** `execution_reads`
  rolls back before transport, so a revocation that commits in that window
  still reaches the provider. The `approved_run_input` docstring says it is not
  an atomic claim. The acceptance recheck is what keeps the result out of
  accepted analysis.
- **`start_attempt` and `reserve` run before the authority recheck in
  `_run_node`.** A revocation between `run_route`'s entry check and a node
  leaves an attempt with a worst-case reservation and no call. That is
  capacity lost, not money spent, and it follows the documented order: start,
  reserve, check, call.
- **`bash -c '…'`, `eval` and similar pass the hook.** The docstring says the
  hook is a pattern screen, not a sandbox.

## Still open (not proven defects in Phase 2 scope; next step named)

1. **Upstream can change between the post-call check and acceptance under
   concurrent workers.**
   - `_accept_artifact` doesn't recompare predecessor digests.
   - The post-call comparison is in a separate unit that has already rolled
     back.
   - With Phase 2's one sequential loop, no other writer exists.
   - With Phase 4 workers, a soft predecessor accepted in that window lets a
     RESTRICTED node be accepted with stale upstream.
   - The ledger records neither the two-workers entry nor the terminal-decision
     entry for this.
   - *Next step:* add it to the Phase 4 claims/leases work, by rechecking
     `_upstream_digests` inside `_accept_artifact`'s locked unit, or by having
     the lease fence the predecessors.
2. **`awaiting_gate` ignores run status** (`app.py:402-405`).
   - On a terminal BLOCKED run where CP-5 never answered (its own upstream is
     blocked), CP-6 reports `awaiting_gate: true`, even though nothing will
     ever answer.
   - `status: "BLOCKED"` sits beside it, so this is misleading rather than
     wrong.
   - *Next step:* `and status == RUNNING` when the section document is wired
     (the Phase 9 gap).
3. **The case lock is held for the whole evidence and citation read.**
   - `_context` reads every captured block one query at a time inside the unit
     holding the case row `FOR UPDATE`.
   - `_envelope`'s `verify_citations` runs under the same lock after the call.
   - For a large pack, governed writes on that case wait for the whole read.
   - This is a correctness-preserving choice (§39: "derived from the pins in
     the same unit"), but the lock hold time grows with document size.
   - *Next step:* measure it with the first large PDF pack, and consider one
     batched block query.
4. **`ModelPrice.as_of` is carried and never used.** It isn't validated,
   stored beside the reservation, or compared with anything. "Dated price" is
   therefore not auditable after the fact: a reservation row doesn't say which
   price produced it.
   - §40 leaves where the price comes from undecided, so this isn't a defect
     yet.
   - *Next step:* record `(model, input, output, as_of)` with the first
     user-confirmed live price.
5. **A QA source's unreadable blob makes `GET /api/runs/{id}` return 500.**
   - `accepted_artifacts` runs `json.loads(blobs.get(...))`, and a
     `ValueError` there is not a `Refusal`.
   - This was already true for CP-0; Phase 2 extends it to CP-5.
   - *Next step:* map it to the typed `ORCHESTRATION_ARTIFACT_UNREADABLE` in
     `accepted_artifacts`, as the harness's `_accepted` does.
6. **Reasoning-token and vendor billing semantics** for
   `max_completion_tokens` weren't checked against the live provider. There
   were no provider calls, by instruction, and the application price "cannot
   guarantee a vendor bill" (§40).

---

## Summary

| ID | P | Area | File:line |
|---|---|---|---|
| F-1 | P2 | Harness accepts a price its route can't afford, pays one call, stops; ledger claim false | `server/qualification/harness.py:384-386`, `CLAUDE.md:572-573` |
| F-2 | P2 | Guard bypass: `git -C/-c … push --force` / `commit -n`, `--force-with-lease=…`, path-qualified `git` | `scripts/claude_hook.py:86-107` |
| F-3 | P3 | `env -u X` / `env -0` print the environment | `scripts/claude_hook.py:96-98` |
| F-4 | P3 | Formatter fails on every edit in a worktree with no venv | `scripts/claude_hook.py:150-159`, `.claude/settings.json:9` |

I found no P0 or P1 issue. The authority, ownership, BLOCKED, QA and
priced-reservation mechanics hold for Phase 2's single sequential loop, as far
as a hand trace can show; no tests were run here.
