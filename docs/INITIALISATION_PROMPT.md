# Initialisation prompt

Paste this as the first message of a fresh session in a clone of this
repository. It is deliberately short: the contract lives in the repo, not in the
prompt. A long prompt that restates the docs will drift from them.

---

```
You are continuing the governed CAOS v2 build. Do not restart it or infer the
current task from historical phase labels. The record is docs/DECISIONS.md;
CLAUDE.md names the active continuation and its exact handoff.

Read first, in this order, in full:
  CLAUDE.md, docs/CLAUDE_CODE_HANDOFF.md, CONTEXT.md,
  docs/REPAIR_PLAN.md, docs/SYSTEM_SPEC.md, docs/AI_CODE_QUALITY.md
Then, when the phase reaches them: docs/IA_SPEC.md,
docs/archive/MODEL_BUILDER_SPEC.md, DESIGN.md.

The methodology bundle is vendored, read-only, and authoritative. Never edit a
file that exists upstream; additions go in new skill folders.

Resume only the active task and phase named by CLAUDE.md and the handoff. For
each implementation slice:

  1. State the exact accepted base, task, allowed paths, hard size budget and
     exit assertion. Index that checkout with GitNexus and verify callers in
     source.
  2. Write the failing test first. Run it. Show me it failing for the right
     reason — a test that fails because of a typo proves nothing.
  3. Implement the smallest thing that makes it pass.
  4. Run focused checks, freeze hashes and size, then run the exact required
     PostgreSQL/static/security gates. Run the complete `make check` at the
     phase boundary.
  5. Commit locally and run an ordinary exact-range task review. Do not push,
     open a PR, merge or deploy without separate authorization.
  6. Only after every task in the phase passes, run one confidence-review at
     actual xhigh reasoning, remediate and retest, then one separate adversarial
     code audit at actual xhigh reasoning. Never run a rewrite tournament.
  7. Stop at the authorized phase boundary and report exact evidence.

Non-negotiable while you work:
  - Test first. The failing test names the invariant it protects.
  - Decimal on every money path. Never float.
  - Typed refusals only. No bare except, no str(exc) in a log or a response.
  - Never log document-derived text.
  - No new dependency without a dated docs/DECISIONS.md entry.
  - Any accepted limitation gets a CLAUDE.md known-gaps entry in the same PR
    that creates it.
  - A scanner that scanned nothing is a failure, not a pass.

If the spec is wrong, say so and stop. Do not build around it, and do not
weaken an invariant to make a test pass. The specs are the product of a long
review; they are also fallible, and a contradiction you found is more valuable
than code you wrote.

Begin at the exact checkpoint in docs/CLAUDE_CODE_HANDOFF.md.
```

---

## Why it is shaped this way

**"Show me it failing for the right reason."** The measured +75 % logic-error
rate in agent-written code is not fixed by having tests; it is fixed by tests
that were seen to fail. A test written after the implementation tends to assert
what the code does.

**"One concern in it."** AI PRs carry ~1.7× the issues of human PRs, and issue
density rises with diff size. The cap is the cheapest control available.

**"Stop and report."** Ten phases executed without a checkpoint is one long
uninterrupted opportunity to drift from the spec.

**"If the spec is wrong, say so and stop."** The predecessor's most expensive
defect — route resolution reading the untyped display list instead of the typed
edges — was in the code for months behind a green suite. An agent that builds
around a contradiction hides exactly that class of problem.

**No restatement of the invariants.** They are in `CLAUDE.md`, which the prompt
requires reading in full. Restating them here creates two versions that will
disagree.

## Session hygiene

- One phase per session where practical. Context that has watched three phases
  land is context that half-remembers the first.
- Re-read `CLAUDE.md` at the start of any session that resumes mid-phase.
- The plan's exit tests are the only definition of done. "It works when I try
  it" is not an exit test.
