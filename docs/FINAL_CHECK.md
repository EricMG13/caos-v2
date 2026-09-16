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

## What is not true, and is accepted

1. **No verdict exists — but one can now be made.** Closed after this document
   was first written: `POST /api/v1/qualification/{evidence_sha256}/verdict`
   (§65) takes the reviewer's six-binding document and records it with
   `reviewer_id` derived from the authenticated actor, from OIDC groups in
   production. `ADMIN` signs; below that, and for evidence the store does not
   hold, the answer is one private 404. `qualification_verdicts` is still empty
   in every database, including the retained evidence behind this check —
   because signing it is the reviewer's act, and no one has signed.
2. **One pathway of eighteen has been qualified.** `LITE_CREDIT_22 /
   LITE_EARNINGS_UPDATE`. The plan wants every route intended to be advertised.
3. **The model surfaces the material figure inconsistently.** It took three runs
   on this build for CP-L10 to quote the £1,021.7m Q4 goodwill impairment. The
   key was not lowered to meet it; the finding stands in the record.
4. **The restricted case is not demonstrated through the built UI.** It is
   expressible and proven in the harness, but no journey test drives a blocked
   or declared-refusal run through the production stack.
5. **Every run before this build refuses `ORCHESTRATION_BUILD_MOVED`.** Two
   authorised bundle edits moved the build twice. Earlier runs' artifacts,
   charges and citations stand as recorded; their proofs no longer re-derive.
6. **`completeness_check.load_contract` reads only the cell disqualifiers**, not
   the frontmatter ones every SKILL.md declares. A separate authorisation.
7. **Two register columns may need the same exemption CP-5's got** — T5B.3
   `Traceability Status` and T5B.7 `Assessment`. Neither has been observed
   failing; left until one does.

`CLAUDE.md`'s known-gap ledger carries these and the smaller ones, each with
its reason and its upgrade path.

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
