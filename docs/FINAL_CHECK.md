# Final check — CAOS workbench, 16 September 2026

For the owner to read and sign. It states what is true, what is not, and what
signing it does and does not assert. Nothing here describes any build, model or
pathway as QUALIFIED, because nothing has been.

## What is being signed

That the engineering work of the repair plan is complete to the standard the
plan sets, that the live qualification apparatus produces a snapshot a reviewer
*could* sign, and that the gaps listed below are known and accepted rather than
undiscovered.

It is **not** a qualification verdict. That is a separate assertion, made by a
named reviewer over exact evidence, and no route exists by which to make it.

## Identity of the thing checked

| | |
|---|---|
| Branch / commit | `codex/execute-repair-plan` @ `dbb2e44` |
| Bundle build | `30222a494a5a1035c7955cb1ccfbe0b3b0fbbfa7d6426930f5dcf4d35aa1fc18` |
| Bundle overrides | `docs/DECISIONS.md` §61 (two edits), §63 (one edit) |
| Qualification set | `0863964bb4dbad8dc8772654311d7b59dfc2810cd08cf6cfdeda6a940ed0db74` |

## Gates, all green on this commit

lint; mypy over 227 files; 2902 backend tests; 21 PostgreSQL race tests;
bandit, pip-audit and gitleaks; frontend 230 unit tests, the a11y matrix and 90
workbench tests, both builds; the image under pinned Trivy 0.70.0 with no
fixable HIGH or CRITICAL; and the production smoke stack — the image's own
tests plus the browser journey on three engines.

## The live evidence

Eleven authorised runs against a real provider, `$7.75` in total, every one
recorded in `qualification/vmo2-fy2025/RESULT.md` with its charges, generation
ids and outcome, including the ones that failed and the ones that failed for
reasons that turned out to be ours.

The current snapshot, run `62308d4e-70b5-4793-abb0-7be62d2ceba6`:

- route COMPLETE, three artifacts, eleven citations, every one re-located
- citation key met, readiness key met, all four conclusion keys met
- `qualification_performed.complete` is **true**, bound to build `30222a49`
- evidence digest `bb09d8d0bcec1524eabdc426142ef9eae60890be52a58bbf973f321644cd4621`
- performed digest `d758a253dba3aed1f88cd325a46c8984d2e0da9189a3027e8f8b4734eb78a7bd`
- database `caos_qualify_5a47243d96774e088f1bfebb6271f2d1`, retained

Re-derived from the store against the set on disk, not read back from the run's
own capture.

## What was owed when this was first written, and what became of it

Seven items were listed. Four are closed, two were miscategorised, one is open.

**Closed.**

1. **A reviewer can now sign.** `POST /api/v1/qualification/{evidence_sha256}/verdict`
   (§65) records the reviewer's document with `reviewer_id` derived from the
   authenticated actor — OIDC groups in production — and from nowhere else.
   `ADMIN` signs; below that, and for evidence the store does not hold, one
   private 404. `qualification_verdicts` is still empty everywhere **because
   nobody has signed**, which is now a fact about people rather than about the
   software.
2. **The insufficient-evidence case is demonstrated through the built UI** (§67).
   A journey test admits a thin pack, runs it, and asserts the run page reads
   BLOCKED and not COMPLETE while the modules that did answer read COMPLETE —
   on the production image, through the real edge, on all three engines.
   *With a caveat a signer should know:* driving it showed the workspace draws
   the blocking node as **running** beside a BLOCKED status, and the analysis
   page carries no run status, so it looks like a run still in flight. The
   status cell, the register tag and the handoff count are honest and are what
   the test asserts; the misleading parts are recorded in the ledger and
   deliberately left unasserted, because a test asserting them would pin them in
   place. The exit check is met; the workspace is not yet fully honest about a
   blocked run.
3. **The frontmatter disqualifiers are deliberately not enforced** (§66). The
   change was written, measured and rejected: it refuses seven of the 25
   retained real handoffs, two of them the accepted artifacts of the only
   complete snapshot, each for declaring `SOURCE_LIMITED_NOT_COMMITTEE_READY` —
   which is true of this corpus. The bundle's list conflates a fixture marker
   with a thin-evidence one; the flag is already projected and already keyable.
   The split is owed upstream, and the ledger says so.
4. **The two further CP-5 columns do not need an exemption.** Every CP-5 body
   this repository retains — nine, across every run — was parsed: no cell in
   `T5B.3 Traceability Status` or `T5B.7 Assessment` holds any disqualifying
   phrase. Measured, not assumed.

**Miscategorised — real, but not work anyone can close.**

5. **The model surfaces the material figure about one run in three.** It took
   three runs on this build for CP-L10 to quote the £1,021.7m impairment. That
   is the qualification *result* — a measured finding about `openai/gpt-5.6-terra`
   on this corpus — not a defect in the system. The bar was not moved to meet it.
6. **Runs pinned to earlier builds no longer re-prove.** Three authorised bundle
   edits moved the build. Their artifacts, charges and citations stand as
   recorded; their proofs refuse `ORCHESTRATION_BUILD_MOVED`. That is invariant 4
   working, the fail-closed direction, and nothing to repair.

**Open, and quantified.**

7. **One pathway of eighteen is qualified.** The catalog carries ten FULL and
   eight LITE pathways, 101 module calls in total; at the observed per-call cost
   that is upwards of $26 of provider spend. Cost is not the obstacle. Each
   pathway needs its own answer key authored from its documents *before* its
   run, and several need evidence this corpus does not contain — `CP-4` wants
   executed debt documents, `CP-2D` a cash-flow pack. Two earnings releases
   cannot qualify `LITE_COVENANT_REFINANCING` or `DISTRESSED_RESTRUCTURING` at
   any price. This is a corpus-and-answer-key programme, not a run.

`CLAUDE.md`'s known-gap ledger carries item 7, the two miscategorised ones and
the smaller gaps besides, each with its reason and its upgrade path.

## What the day changed

Six defects were found and fixed, and four of them were ours rather than any
model's: a reader that refused typographic quotation marks and blamed models
for it across four paid attempts; a billed call whose body could not be stored
being billed again; a readiness gate refusing a module on grounds its own
contract forbids; an answer key naming a subordinate clause instead of the fact;
a vendor validator that never enforced the rule it existed to protect, so a
module could declare itself committee-ready at 93 over its own MATERIAL gap; and
a completeness rule that refused CP-5 for writing the honest answer.

The instrument was the thing hiding them. A key that asks only which quotes a
module happened to draw reports every one of those as a model failing to find
evidence.

## Signature

    Reviewer:
    Date:
    Signed:

Signing asserts that the above is an accurate account and that items 1-7 are
accepted as stated. It asserts nothing about the fitness of any model or
pathway for use.
