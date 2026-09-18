# Agent prompts — adapted for CAOS

The uploaded prompt set is written for a repository with no governance. This one has
a great deal, so most of the adaptation is *subtraction*: where a generic prompt says
"maintain a ledger", this repository already names the ledger, and pointing a second
one at the same work is how two records start disagreeing.

Four prompts of the original ten survive adaptation. The rest are already implemented
as agents, gates or briefs, and the last section says which and why — a prompt that
duplicates an existing gate is worse than no prompt, because it produces a second
verdict nobody reconciles.

## What does not change per prompt

`CLAUDE.md` is the contract and is already the shared preamble the original asks for.
The three rules behind the original's rewrites hold here too, and each maps onto
something this repository already has.

**1. State lives in tracked files.** The sole task and checkpoint record is
`docs/CLAUDE_CODE_HANDOFF.md`. Task scope is `docs/superpowers/plans/*-brief.md`.
Accepted limitations are the **Known gaps** ledger in `CLAUDE.md`. Phase acceptance is
`docs/PHASE_N_EXIT_EVIDENCE.md`. Never open a new ledger; append to the one that owns
the fact. `docs/REPAIR_PLAN.md` is read-only — report findings against it, never edit it.

**2. Exit conditions resolve to a command.** This repository's are:

| Condition | Command |
|---|---|
| complete offline gate | `make check` |
| partial, explicitly not acceptance | `make check-fast` |
| PR size | `make check-size PR_BASE=<commit>` |
| ledger entries cite a defined test and state an upgrade | `pytest tests/test_ledger.py` |
| named phase-exit tests exist and pass | `pytest tests/test_phase_exits.py` |
| every definition is named by a test | `python scripts/check_tested.py` |
| a scanner that scanned nothing fails | `python scripts/scan_floors.py <report> --<format>` (as `make test`, `make security` and `make image` invoke it) |

An exit condition that is not one of these, or a count over a tracked file, is not
checkable by an evaluator. Do not write one.

**3. Named illegal solutions.** Every "until X passes" loop here has a cheap wrong
answer, and each is out of bounds without the owner:

- Weakening or deleting a test that names an invariant, or making one pass vacuously.
- Editing any file that exists upstream in `vendor/deploy-v/` (invariant 4). Additions
  go in new skill folders.
- Adding a name to `NOT_YET_REACHED` in `tests/test_phase_exits.py` to green a phase.
- Striking a Known gaps entry without naming the test that closed it, or adding one
  whose cited test the suite does not define.
- Adding a path to a coverage, lint or floor ignore list.
- Editing `docs/REPAIR_PLAN.md`, or a dated row of `docs/feature-status.csv`.
- Calling a live provider. Every shell command starts with the unset prefix below, and
  a live run needs its own authorization naming provider, model, endpoint tag,
  reasoning effort, ceiling and window, and runs only through `scripts/qualify.py`.

```
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL \
    -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER
```

## Models and effort

Three stages, two models. **Sonnet 5 detects. Opus 5 implements and reviews.**

| Stage | Model | Effort | What it covers |
|---|---|---|---|
| **Detect** | Sonnet 5 | high | Enumeration sweeps: §5 reachability, §6 first pass, §9 census, the candidate scan in §1. Produces candidates with file:line, never verdicts. |
| **Implement** | Opus 5 | low → high by task | All code. Falsification tests, fixes, briefs, wire, UI, vendor request documents. |
| **Review** | Opus 5 | xhigh + ultrathink | Ordinary per-task review, both phase gates, and every verdict over a Sonnet candidate. |

Opus effort within the implement stage, unchanged from the contract:

| Work | Effort |
|---|---|
| scaffolding, fixtures, admission manifests, regenerated ledgers | low |
| per-module fixtures, contract tests, route enablement, endpoints, wire, UI, tests, PR authoring | medium |
| long-horizon multi-file work; task and phase briefs; vendor request documents | high |

`xhigh` is the ceiling; `max` is not dispatched (`1b1ffcd`). Ultrathink is the Opus
lever and never appears in a Sonnet prompt.

Set `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` for the detect stage so parallel sweeps do not
inherit Opus, and unset it before the implement and review stages.

### The one carve-out, and why

Detection splits into two kinds of work, and only one of them is Sonnet's.

**Enumeration** — walk every symbol, every call site, every claim, and report what is
there. Throughput work. Sonnet, in parallel subagents, and the cheaper model is the
right call precisely because the expensive judgement happens afterwards.

**Construction** — invent the input on which the system is wrong. §7 and §8's lens 2
are this: not "scan for a pattern" but "build me a handoff that passes the vendor's own
completeness check while the shipped key is met from the wrong register". That is what
found the register locator, and no scan finds it, because the defect has no signature
until the counterexample exists.

So **§7 and §8 detect on Opus 5 at xhigh with ultrathink.** Everything else detects on
Sonnet.

The reason is an asymmetry in the pipeline: **Opus reviewing Sonnet's findings cannot
recover what Sonnet never surfaced.** Review is a filter over a candidate set — it
removes false positives, and it is structurally blind to false negatives. Where
detection is enumeration, a miss is a symbol the sweep did not list, and the sweep's own
floor catches that. Where detection is construction, a miss is a counterexample nobody
imagined, and nothing downstream will ever ask for it again.

Run §5, §6 and §9 on Sonnet and you save most of the cost of this file. Run §8's lens 2
on Sonnet and you get a report full of clean-refusal bugs and no silent-corruption ones
— which the prompt itself names as the failed run.

### The detect → verdict handoff

Append this to every Sonnet detect prompt (§5, §6, §9). It is what keeps the stages from
collapsing into one another, in both directions.

```markdown
You are the detect stage. You produce candidates, not verdicts.

Every candidate carries a file:line you have read, and the observation that made you
raise it, in one sentence. Nothing else — no severity, no root cause, no fix, no
judgement of whether it is really a defect. Those are the review stage's, and a
candidate arriving with a confident verdict attached is worse than one arriving bare,
because it anchors the reviewer.

Raise the uncertain one. A false positive costs the reviewer a minute; a candidate you
suppressed because it looked probably-fine is invisible from here on — the review stage
never sees what you did not list, and nothing downstream asks again. When you are
unsure, raise it and say you are unsure.

Report your floor: how many units you examined, of how many that exist. A sweep that
cannot state its denominator has not swept. If you could not reach part of the scope,
name the part rather than narrowing the scope to what you reached.
```

The review stage's counterpart: a verdict over a candidate names the file:line that
decides it, and `UNDECIDABLE-FROM-CODE` is an allowed verdict. Dismissing a candidate
is a finding about the candidate, not a silence.

---

## Two kinds of prompt, and which one you need

Prompts §1–§4 work **inward from the plan**: a brief, an answer key, a named scenario.
They find what the plan predicted and confirm it. They cannot find what nobody wrote
down, which is most of what has actually gone wrong here.

Prompts §5–§9 work **outward from the code**: every symbol, every claim, every pair of
authorities that must agree, every assumption nothing checks. They exist because of the
record below, and if you only run one section, run this one. If you only run one
prompt, run §8.

The inversion that makes them work: a reviewer asked *"is this correct?"* evaluates code
against its own apparent intent, and an LLM asked that question adopts the author's
mental model — which is the model that produced the defect. So it finds what that model
already worried about: syntax, formatting, declared edge cases. Known unknowns. Each
prompt below asks a question the author's model cannot answer from inside itself —
what nothing reaches, what the docs assert and the code denies, what the input would be
that splits two authorities, what is assumed and never checked, what a caller believes
that the callee never promised.

**Why enumerate-your-doubts is not enough.** The `confidence-review` method asks what
you are least confident about. That is a complete method for *known* unknowns and
structurally blind to the rest: you cannot list a doubt you do not have. The repository
has measured this exactly once, and the result is in `CLAUDE.md` under Completion
Phase 8 — the confidence review read the register-locator code and recorded it as safe;
the adversarial audit then *constructed* a handoff that passed the vendor's own
completeness check with zero violations while the shipped key was met from the wrong
register. Same code, same reviewer quality, opposite verdict. The difference was not
effort. It was direction: one asked "does this look right", the other asked "build me
the input where it is wrong".

The population these prompts hunt is not hypothetical. Everything below is recorded in
this tree, and none of it would be found by §1–§4:

| Fault | Class |
|---|---|
| `frontend/src/app/authority.ts:59` `bind`/`release` and `EvidenceContext.openPassport` reach no section — tested, shipped, unreachable | unwired |
| `canonical._within_reservation` shipped with no test; the gate passed because the name appears in a *comment* | invisible gate |
| `INTERNAL_FAULT` is 400 in `server/api/app.py:261` and 500 in `server/api/edge.py:227`; nothing asserts the disagreement | two authorities |
| Nine refusal codes answer 400 with retry-shaped clearance text, invisible to the partition test because it defined its universe as codes already at 5xx | scope-defined blindness |
| `_cell`'s documented rule — "a register whose header names the same column twice answers `None`" — could never fire, because the vendor collapses the row first | doc true, code false |
| Two Known gaps entries were "fluent, cited nothing, and kept their upgrade clause while becoming false" | doc true, code false |
| `frontend/fixtures/admin.json` says the health route is not served; it has been since §53.8 | fixture drift |
| Nine test names cited in `docs/feature-status.csv` are defined nowhere on disk | citation rot |

Every one is *invisible*: nothing failed, nothing went red, and each surfaced when
something else broke. So the count is a lower bound — which is the whole argument for
running §5–§9 on a green tree rather than waiting for a symptom.

Note what the right-hand column is not: severity. It is the *mechanism of silence*, and
the taxonomy before §8 turns that into something each finding must name.

---

# Prompts over known work

## 1. Wave execution and remediation

> **Opus 5** · **Effort** medium · **Mode** `goal` · replaces the original §1b/§1c/§3

The original splits discovery from execution because its ledger does not exist yet.
Here the brief *is* the discovery artefact and is written before the wave, so this
prompt starts at execution.

```bash
claude -p "/goal Every task in this wave's briefs under docs/superpowers/plans/ has a
reviewed commit on its own worktree branch; the coordinator has integrated each and
make check exits 0 on the integrated tree; make check-size PR_BASE=<base> passes or the
over-cap exception is recorded with the attempted split; docs/CLAUDE_CODE_HANDOFF.md
records each task's acceptance evidence with the command output that proves it."
```

Session prompt:

```markdown
Work from the task briefs in docs/superpowers/plans/ for this wave, and from
docs/CLAUDE_CODE_HANDOFF.md. Re-read both at the start of every turn — they are the
source of truth, not your memory of them, and this session will compact.

Test first. The failing test names the invariant or the behaviour, and you watch it
fail before the code that satisfies it exists. A change that makes an invariant pass
vacuously is wrong even with a green suite.

One concern per commit. If a diff grows a second concern, split it.

Up to five implementers concurrently, only in isolated worktrees with disjoint owned
files, migrations and test resources. Each gets an exact base and brief, commits its
own tested concern, and receives ordinary exact-range review. You alone integrate
reviewed commits, run the gates and update the handoff. Never share a branch, database
or blob root; an independently green branch is not task acceptance.

When an implementer fails a task or a test, fix it yourself. Do not re-run it and do not
re-dispatch it.

Before editing a symbol run impact on it and report the blast radius; before committing
run detect_changes. Refresh GitNexus at phase entry.

Escalate rather than deciding: spend, a bundle edit, a new dependency, a push, a hosted
write, a deployment, or anything that changes intended behaviour. Write the blocker to
the handoff and move to the next task rather than inventing a workaround.

A limitation you accept gets a Known gaps entry in CLAUDE.md in the same commit as the
code that creates it, with its reason and its upgrade path. An entry you close is struck
in the commit that closes it, naming the test.
```

*Note on the original's "run 1a → 1b → 1c then decide".* The equivalent boundary here
is the phase, and it is already human-gated: acceptance is recorded in the handoff by
the owner, and an implementation commit is not acceptance. Do not let a `/goal` loop
cross a phase boundary.

---

## 2. Gate-axis audit

> **Opus 5** (construction) · **Effort** xhigh + ultrathink · **Mode** `plan`, read-only · replaces the original §9

The original §9 raises coverage. This repository's coverage is already enforced by
`make check`, so the version that earns its place here is the one aimed at the failure
mode `CLAUDE.md` names under **Phase 0**: *a gate measuring an axis correlated with the
hazard rather than the hazard itself.* Four instances turned up in one day and none was
found by looking for them; the count is a lower bound.

```markdown
Audit this repository's gates for the axis they actually measure.

For every gate — the scripts in scripts/, the gate tests in tests/ (test_ledger,
test_phase_exits, test_gate_scripts, test_vocabulary_rules), the Makefile targets, the
CI floors — state four things:

1. The hazard it exists to stop, in one sentence, as a thing that can happen to this
   codebase.
2. The axis it actually measures.
3. Whether 2 is the hazard or merely correlated with it. Name the gap precisely if it
   is correlated.
4. The cheapest way to satisfy the gate without reducing the hazard — and then the
   decisive question: does that cheapest evasion make the code better or worse? Keep
   the gate only if the answer is better.

Read CLAUDE.md's Phase 0 entries first. check_tested.py matching a name anywhere in the
suite's bytes is the worked example: the cheapest evasion is naming the symbol in a
comment, which leaves prose where a test should be, and that is exactly what happened
on a money path.

A gate that fails 4 does not automatically get deleted — say what would have to replace
it. A gate whose replacement is "discipline" is one this file should say so about
rather than one that should keep passing quietly.

Make no edits. Report findings ranked by how invisible the failure would be, not by how
likely — an invisible gate failure is the one nobody is looking at, which is the whole
class.
```

---

## 3. Qualification run under production-like conditions

> **Opus 5** · **Effort** high · **Mode** `goal` · replaces the original §4

The original builds a synthetic production dataset. Here the equivalents already exist
and are stricter: the qualification harness, the on-disk qualification set, and
`make smoke-production`. Adaptation is to drive those rather than to invent a dataset.

```bash
claude -p "/goal make smoke-production exits 0; the qualification set prepares without
spend and every case's route resolves and pins; each answer key is authored from the
documents and the owner's key rather than from any run's output; the authorization for
any live run is recorded with provider, model, endpoint tag, reasoning effort, ceiling
and window; nothing is described as QUALIFIED without a signed verdict over a complete
snapshot on the current build and prompt identity."
```

```markdown
Run the system as a real operator would, offline first.

make dev-up, then make dev-api and make dev-worker, then make dev-ui. Nothing is
seeded. make dev-ui-demo is the separately labelled read-only fixture workbench and is
never integration evidence — do not cite it.

Prepare the qualification set through scripts/qualify.py. prepare resolves every route,
creates every case, admits every document and pins every input before perform may spend
anything, so a document that will not admit refuses the set before any provider call.
Confirm that boundary holds before asking for spend authorization.

Author each answer key from the source documents and the owner's answer key, before the
run. Never from what a run produced — a key chosen from a run's output measures the
model against itself. The owner confirms every material figure.

A live run needs its own authorization and runs only through scripts/qualify.py. Keep
its database and blob root until its verdict is signed or its refusal recorded.

Log each failure where it belongs: a defect in the code is a failing test and a fix; an
accepted limitation is a Known gaps entry with its upgrade path; a vendor rule this host
may not implement is a vendor change request document, never host code that becomes a
second conformance authority beside the bundle.

Ask before anything that spends, touches the bundle, adds a dependency, or pushes.
```

---

## 4. Journey and flake discipline

> **Opus 5** · **Effort** medium · **Mode** `goal` · replaces the original §8

The original's scenario streak is a reasonable fit for the journey suite, with one
correction this repository has already paid for: *confirm pass and fail at the same
commit before calling anything a scheduling flake.* A "flaky" query-count assertion here
turned out to be a deterministic regression.

```bash
claude -p "/goal The journey suite has run N consecutive times with zero failures across
chromium, firefox and webkit, each run recorded with its commit; every failure seen
during the streak has either a regression test that failed before the fix and passes
after, or a Known gaps entry naming why it is accepted; make check exits 0."
```

Twenty is a reasonable first N. Above fifty you are measuring the machine, not the code.

```markdown
Run the journey suite repeatedly and treat every failure as a defect until proven
otherwise.

When a run fails:
1. Re-run the same test at the same commit. A test that passes and fails at one commit
   is a flake; a test that fails at that commit is a regression. Do not skip this step —
   the classification is the whole finding, and calling a regression a flake is how one
   ships.
2. If it is a regression, find the root cause in source, write the failing test, fix it,
   and reset the streak to zero.
3. If it is genuinely a flake, identify the shared resource. Concurrent load on this
   checkout is a known cause: pytest -n auto flakes when many CI runs race, and two
   vendor tests fail on __pycache__ any concurrent process can write. Record which, and
   whether the isolation rule is being bent by working in one tree.
4. A flaky pass is a failure. Never narrow, simplify or retire a journey to keep a
   streak; only the owner retires one.

Note which engine found each failure. The smoke journey's worker exit-once marker lives
in a shared blob volume, so only the first engine meets the real exit-after-first-accept
path — a failure the later engines cannot see is still a real failure.
```

---

# Prompts over unknown unknowns

## 5. Reachability census

> **Detect: Sonnet 5** high, parallel subagents · **Verdict: Opus 5** xhigh · **Mode** `plan`, read-only · no equivalent in the original set

The original set has no prompt for this, and it is the direct answer to "unwired
sections". Two are already documented; the question is how many are not.

```markdown
Census every definition in this repository against the paths that actually reach it.

Entry points are exactly these, and nothing else counts as one: the routes registered
in server/api/, server/engine/worker.py, the scripts under scripts/ that an operator
runs, the nine sections composed in frontend/src/sections/, and the migrations applied
by apply_schema.

For every exported symbol, route, React component, refusal code, migration, Makefile
target, config flag and environment variable, assign exactly one category:

  A. reachable from a production entry point
  B. reachable only from tests
  C. reachable only from demo fixtures or the read-only workbench
  D. reachable from nothing

B, C and D are the findings. Do not report A.

Use GitNexus for the call graph — impact with direction upstream on each candidate, and
the process listings for flows — but confirm every B/C/D in source before reporting it.
A symbol reached through a registry, a decorator, a string key, a dynamic import or a
FastAPI dependency is reachable and the graph may not show it; that false positive is
the main cost of this census and you own excluding it.

Three traps, each of which has already caught someone here:

1. A tested island is not dead code you may delete. `frontend/src/app/authority.ts`'s
   bind/release and EvidenceContext.openPassport are category B and are the subject of
   tests pinned by name in tests/test_phase_exits.py, so deleting either is a gate edit.
   Report; never delete.
2. Category C is where a fixture claims something the API contradicts — the demo Admin
   panel says the health route is not served and it has been since §53.8. For each C,
   state what the real path does instead.
3. A definition in category D that a document claims is live is a §6 finding too. Cross
   them over.

Make no edits. Output the census as a table, then rank the findings by what a reader
would wrongly believe because of each one.
```

## 6. Claim falsification

> **Detect: Sonnet 5** high · **Verdict: Opus 5** xhigh + ultrathink · **Mode** `plan`, read-only · replaces the original §6

The original audits code against framework conventions. Here the richer seam is the
opposite direction: this repository writes down a great deal, some of it has quietly
stopped being true, and `tests/test_ledger.py` says outright that no mechanical gate
catches that class — phrase-based rules were measured against `CLAUDE.md` and rejected,
the best of them flagging three entries of which one was the real defect.

```markdown
Take this repository's own claims about its behaviour and try to falsify each one
against source. You are not summarising the documents. You are attacking them.

Scope, in priority order — each has produced a false claim already:

1. Every open Known gaps entry in CLAUDE.md. Two were fluent, cited nothing, and had
   become false while keeping their upgrade clause. Check the code each describes still
   behaves that way, and that a struck entry's named test exists and asserts what the
   strike claims.
2. Every refusal code's clearance text in server/ and frontend/src/controls/. A
   clearance tells an operator what to do next; CONTEXT_OVER_CEILING says "deliver less
   context" where the reservation, not the context, is what moved, and ACTION_UNPLACED's
   READ_ONLY_API text describes an API that stopped existing at §50.
3. Every docstring and comment that states a *rule* rather than describing code. `_cell`
   documented a duplicate-column rule that could never fire. A comment asserting a
   guarantee is a claim; a comment restating the line below it is not — skip those.
4. The §-numbered behavioural claims in docs/DECISIONS.md that current code is supposed
   to implement. Not the historical record of what was decided — the claims a reader
   would act on today.

For each claim record exactly three things: the claim, the file:line that decides it,
and the verdict — TRUE, FALSE, or UNDECIDABLE-FROM-CODE. A verdict with no file:line is
an opinion and does not go in the report.

Two failure modes to avoid, both of which have happened. Do not accept a claim because
it is well written; the false ones here were the most fluent. And do not report a claim
as false because it is imprecise — say specifically what a reader would do wrongly
because of it, and if the answer is nothing, it is not a finding.

Make no edits. A FALSE verdict on a Known gaps entry is corrected in the commit that
proves it, naming the test; that is a separate task, not this one.
```

## 7. Peer-authority differential

> **Opus 5** (construction — not Sonnet) · **Effort** xhigh + ultrathink · **Mode** `plan`, read-only · sharpens the original §2

Two *peers* that read the same rule and must reach the same answer. §9 below covers the
*vertical* case — a caller and the thing it calls — and the two should not both be run
on one seam. The distinction: here neither side is the other's provider, so there is no
contract to compare, only two derivations of one rule that may have drifted apart.

This is the method that found the register locator, and the one §1–§4 structurally
cannot reproduce. It does not review code. It builds the input on which two things that
must agree do not.

```markdown
This system holds many pairs of authorities that are required to agree. Find the input
on which a pair disagrees.

First enumerate the pairs. These are known and are your starting set, not your limit:

- the host's readiness reasoning (server/engine/route.py `_state_for`) and the vendor's
  `expected_upstream_digests` clause — CLAUDE.md records that their agreement "rests on
  nothing written down"
- server/api/app.py's status map and server/api/edge.py's, per refusal code
- the demo fixtures under frontend/fixtures/ and the real API's responses
- the ordered MIGRATIONS prefix and schema.sql
- each wire Pydantic model and the TypeScript type the frontend reads it as
- record_bytes and _decoded_record, over every projection
- the proof (server/qualification/proof.py), the deliverable (server/deliverable/
  canonical.py) and the runtime, which re-derive the same verdicts under different codes
- the host's register reading and the bundle's own check(), which already diverged once

Then, for each pair, do the thing that distinguishes this pass from a review: construct
a concrete input — a handoff, a register, a request, a stored record — on which they
answer differently. Write the input out. Run it where you can.

If you cannot construct one, say what makes it impossible, and name the code that
enforces the impossibility. "I read both and they look consistent" is not that answer,
and is exactly the answer that passed the register locator.

Rank findings by whether the disagreement is observable. A pair that disagrees where no
caller can reach the divergence is a latent finding; a pair that disagrees on a path
that ships is a defect. The register locator was the second kind and read like the
first.

Make no edits. For each confirmed divergence, name which side is right and why — the
fail-closed side is not automatically correct, and where the host and the bundle
disagree, invariant 4 decides, not preference.
```

## Why a finding stays invisible here — the concealment taxonomy

§8 and §9 both ask, per finding, *why has this not surfaced yet*. That question is what
breaks confirmation bias: a reviewer asked "is this correct" checks the code against its
own apparent intent, while a reviewer asked "why is this still hidden" has to name a
mechanism, and an unnameable mechanism means the finding is imaginary.

In this repository the mechanisms are enumerable, which turns a free-text field into a
checkable one. Every finding names at least one:

| # | Concealment | Why it hides things |
|---|---|---|
| C1 | **One sequential loop.** `run_route` drives one node at a time. | Every ordering, interleaving and lost-update assumption is unfalsifiable today. Phase 13's concurrent frontier is the day they all become real at once. |
| C2 | **Three routes of nineteen execute.** Everything outside `ADAPTER_ROUTES` (`server/methodology/handoff.py:57`) is refused `HANDOFF_MODULE_UNSUPPORTED` before any attempt. | Sixteen pathways' code paths have never run. CP-5 on the widest route carries 16 direct upstreams and has never built a prompt. |
| C3 | **Unreachable-by-route code.** No route serves a package; `write_package` has no caller outside the suite; Book, Model, Report, Committee and Admin are shells. | A defect there is real and arrives silently on the day a route is served. |
| C4 | **A frozen ASCII corpus.** | Every `BoundaryText` path, invisible-character refusal and normalisation branch is untriggered by real data. |
| C5 | **Fixture-scale data.** | Memory ceilings, `work_mem` spills, the shared `TokenIndex`, unbounded table growth and the 20 MiB/100 MiB admission limits are never approached. |
| C6 | **The gate runs sequentially.** `make check` serialises; races live only in `test-postgres-races`. | A race outside that suite's imagination is not covered by a green gate. |
| C7 | **Nobody has signed.** `qualification_verdicts` is empty in every database; no authorized live run has been made on most pathways. | Whole verdict, pricing and provider-identity paths are exercised only by tests that supply their own inputs. |
| C8 | **A gate measuring a correlated axis.** The `check_tested.py` comment case. | The gate is green *because* of the defect's shape, not despite it. |

A finding whose concealment is C1, C2 or C3 is **latent**: correct today, wrong on a
named future day, and it belongs in the Known gaps ledger with that day as its upgrade
trigger. A finding whose concealment is C4–C8 is **live**: reachable now, and it is a
defect. Say which, because the two get different treatment and conflating them is how a
real defect gets filed as an accepted limitation.

## 8. Shadow invariants and silent degeneracy

> **Opus 5** (construction — not Sonnet) · **Effort** xhigh + ultrathink · **Mode** `plan`, read-only

The single highest-value prompt in this file. It inverts the reviewer's question from
"does this code do what it means to" to "what does this code assume that nothing
checks, and what happens when that assumption is false without anything crashing".

Note the effort: the source method asks for `max`, and `max` is not dispatched in this
repository (`1b1ffcd`). `xhigh` with ultrathink is the ceiling and is what this runs at.

```markdown
You are conducting an adversarial blind-spot audit of CAOS. You are looking for
failures, assumptions and edge conditions that appear in no test, no comment, no
decision entry and no ledger entry. Treat the code as an adversarial system, not as an
artefact whose author was probably right.

Read CLAUDE.md's eleven invariants and its Known gaps ledger first — not to confirm
them, but so that you do not spend the run rediscovering what is already written down.
A finding already in the ledger is not a finding.

### Lens 1 — shadow invariants

Identify every assumption the code makes about its environment that nothing checks.
The classes that apply to this system:

- **Ordering and arrival.** What assumes one node at a time, one worker, one writer?
- **Re-entrancy and idempotency.** What breaks if it runs twice — a replay, a resumed
  attempt, a retried command, a redelivered event?
- **Time.** Transaction-start clocks compared across transactions, deadlines measured
  against wall clock, lease expiry, `Retry-After`, timezone and monotonicity.
- **Transaction isolation.** What assumes one consistent snapshot while running under
  READ COMMITTED across several statements?
- **Boundary survival.** A connection, a transaction, a lock or a lease held across
  something that can outlive it — a subprocess, a provider call, an SSE stream, a blob
  read.
- **Upstream shape.** Nullability, field length, duplicate keys, unexpected keys,
  ordering of rows a vendor reader returns.
- **Boundedness.** What grows without a ceiling — a table, an index, a buffer, a
  retry count, a tuplestore.

### Lens 2 — silent degeneracy and blast radius

Find where a failure does **not** produce a clean refusal, and instead causes:

- partial commit drift, or state that is internally inconsistent but passes every check
- a charge with no decision behind it, or work paid for twice
- an artifact, citation, projection or verdict that is wrong rather than absent
- a silent fallback to a weaker answer — presence instead of verification, a default
  instead of a derived value, an empty set instead of a refusal
- resource starvation: an unclosed handle, an unbounded read, a held connection

This lens outranks lens 1. A broken assumption that raises a typed refusal is a bug
with a clean signal. A broken assumption that returns a plausible wrong answer is the
class this repository cannot detect by any other means.

### Lens 3 — boundary transitions

Examine every seam where data changes format, process, or scope, and ask what each side
believes about the other: store transaction to blob filesystem; host to vendor
validator; API request to worker; sync code to subprocess; Postgres to Python Decimal;
Pydantic model to TypeScript type; governed write to audit event.

### Output

Write findings to `docs/reviews/shadow-invariants-<date>.md`, one section each:

- **Assumption** — what the code takes as always true.
- **Violation scenario** — a concrete sequence where it is false. Name the actors and
  the order of events. "Under concurrency" is not a scenario; "worker A commits its
  bill after worker B's replay read and before B's reservation" is.
- **Concealment** — which of C1–C8 above, and whether the finding is latent or live.
- **Evidence** — file:line where the assumption lives unchecked.
- **Verification test** — the minimal test that proves the failure exists. Name the
  file it would go in and what it would assert. Do not write it in this run.
- **Invariant** — which of the eleven it threatens, or none.

Rank by silence, not by severity: a wrong answer that looks right outranks an outage.

### Out of scope

Style, docstrings, naming, missing null checks, and anything already in the Known gaps
ledger. Also out of scope: proposing fixes. This run produces findings.

### The failure mode of this run

Returning only assumptions that are already documented, or only ones whose violation
raises a clean error. If your report contains no finding where the system keeps running
and produces something wrong, you have audited for correctness rather than for blind
spots, and the run has failed. Say so rather than padding it.
```

## 9. Contract asymmetry census

> **Detect: Sonnet 5** high, by package · **Verdict: Opus 5** xhigh · **Mode** `plan` → `interactive`

The vertical counterpart to §7. Unknown unknowns collect in the gap between what a
provider actually enforces and what its callers believe it enforces — and neither side
is wrong in isolation, which is why reading either alone finds nothing.

```markdown
Perform a contract differential across this system's internal boundaries.

Build `docs/reviews/contract-gaps-<date>.csv`:

  boundary_id,provider_ref,consumer_ref,provider_guarantee,consumer_assumption,
  delta,invariant_at_risk,concealment,failure_mechanism

For every call site crossing a module boundary in server/ — into the store, the blob
store, the methodology registry, the vendor contract, the engine, the evidence readers,
the deliverable — record three things:

1. **What the provider actually enforces**, from its lines, not its name or docstring.
   Its return type, what it raises, what it mutates, what it locks, what it commits,
   what it leaves to the caller.
2. **What the consumer assumes**, from how it uses the result. Does it assume the call
   is non-blocking, that an id is unique, that a refusal rolls back, that a returned
   collection is ordered, that a digest was verified, that a lock is still held, that
   the value is fresh rather than snapshot-old?
3. **The delta** — anywhere the consumer expects more than the provider gives.

Prioritise the boundaries where a delta is already plausible: anything whose provider
docstring states a rule (a rule stated in prose is a rule nothing enforces until proven
otherwise); anything where the provider takes a lock the consumer then relies on past
the call; anything returning a collection the consumer treats as complete; anything
whose refusal path leaves a side effect behind.

For each delta name the concealment from the C1–C8 table and whether it is latent or
live, and name the invariant at risk or `none`.

Stop when every cross-module call site in server/ has a row. If that is too large for
one run, do it by package and say which packages remain — a partial census that says
what it did not cover is useful; one that silently stops is not.
```

## Turning findings into work

Findings from §5–§9 do not go straight to fixes. The path:

0. **Verdict the candidates.** Sonnet's §5/§6/§9 output is candidates. Opus at xhigh
   turns each into TRUE / FALSE / UNDECIDABLE-FROM-CODE with the file:line that decides
   it. §7 and §8 skip this step — they already ran on Opus and their output is findings.
1. **Falsify first.** For each surviving finding, write only the failing test from its
   Verification test line — Opus 5 medium, one test per finding, no fix. Watch it fail.
   A finding whose test passes was a misreading, and a fair fraction will be; delete
   those from the report rather than arguing them. This is the step that makes the
   cheap detect stage safe: a false positive dies here for the cost of one test.
2. **Rank by silence, not by severity.** Money-path and identity findings (invariants
   3, 6, 8) first, then evidence integrity (2, 11), then availability. A double charge
   and a false citation are invisible until a reconciliation or a committee disagrees;
   a 503 pages somebody. The instinct to fix the crash first is exactly backwards here.
3. **Route each by concealment.** Live findings (C4–C8) become tasks with briefs.
   Latent findings (C1–C3) become Known gaps entries naming the day they activate —
   "the day a second worker runs", "the day a package route is served" — which is the
   upgrade-path discipline the ledger already requires.
4. **Never waive on your own judgement.** A finding is closed by a test or by an owner.

---

## What the original set already has here, and is not duplicated

| Original | Why it is not adapted |
|---|---|
| §1a feature discovery | `docs/feature-status.csv` is the dated inventory, and is deliberately not re-cited to the current tree — a dated row edited later stops being a record of that date. The live equivalent is the per-task brief, written before the wave. Regenerate it from the suite (Task 13.6) rather than re-inventorying by hand. What the original wanted an inventory *for* — finding the feature nobody wrote down — is §5, which enumerates from the code rather than from the plan. |
| §2 confidence audit | Already an agent: `phase-confidence-reviewer`, at xhigh with ultrathink, run at a phase freeze. Do not run a second one per task — but do not mistake it for coverage of unknown unknowns either. It enumerates doubts, and the register locator proves a doubt you do not have cannot be enumerated. §7 is the complement, not a duplicate. |
| §3 lightweight loop | Redundant with §1 above on a system this size. |
| §5 maintenance heartbeat | The coordinator's own loop is this, and its state file is the handoff. A scheduled second agent opening competing work on the same branch is exactly the interference rule §5 warns about. |
| §6 evidence-based audit | Split. Its *method* — a verdict per area, every verdict carrying a file:line or command output — is kept and sharpened as §6 above, aimed at this repository's own claims rather than at framework conventions. Its *cadence* is already the `phase-adversarial-auditor` agent, run after the confidence review and its remediation, with `final-phases-reviewer` across all phases. |
| §7 logging coverage | Inverted here: the standing rule is **never log document-derived text** — the typed code, never `str(exc)`. Adding log statements is the hazard, not the remedy. If a logging pass is wanted, it is an audit that every governed path logs its typed code and nothing else. |
| §10 architecture refactor | The task brief template is this prompt, with the acceptance criteria already numeric and the plan already ordered. Write a brief. |

## Review cadence

Unchanged from the contract, restated because every prompt above ends in it: ordinary
review closes each task. One `confidence-review` and then one separate adversarial code
audit close the whole phase, both at xhigh with ultrathink, with remediation and
reverification between them. No per-task specialist review and no rewrite tournaments.
Requested document reviews do not certify these code gates.
