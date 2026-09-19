# VMO2 FY2025 deep-research qualification — no run has been performed

**No run has been performed against this set.** It is authored, loadable and
digested; nothing here reports a result, a verdict or a provider. The live run
is Phase 9 Task 9.4 step 7 and needs the owner's explicit authorization — it
costs real money and calls a real model. **The material figures in the keys
below await the owner's confirmation** before that run.

## The set

- Qualification-set digest:
  `09807efb1a3d5d40680d1a9d0e054333537781d7bb4013ecd7670323f817fd9b`
- Route: `LITE_CREDIT_22 / LITE_DEEP_RESEARCH` (`CP-0` → `CP-DR`, one
  REQUIRED edge, `decision_scope: SCREENING_ONLY`, terminal deliverable
  `CP-DR`), enabled by `docs/DECISIONS.md` §96 at build `6a5f1050`.
- `tests/test_deep_research_set.py` holds the digest, the document digests,
  that the brief is one the pin accepts, that every citation key anchors
  exactly once, and that the UNRESOLVED question names a fact neither
  document carries.

## The documents

The two Virgin Media O2 earnings releases of `qualification/vmo2-fy2025/`,
the same bytes, copied because `server/qualification/on_disk._document`
refuses a declared path outside the set root:

- `documents/Virgin-Media-O2-Q3-2025-Earnings-Release.pdf`, SHA-256
  `505bf1a0f4181c9cdffeeac7e6af3253d1883788e9cd1a81e65952e008aa17a1`
- `documents/Virgin-Media-O2-Q4-2025-Earnings-Release.pdf`, SHA-256
  `66055bbb8d27721d07a5e8cb834c9b96a256ada45a0812ea4fb2e7202ee4f64d`

## The brief

**Implementer-authored**, not sourced: the owner's instruction was to search
for equivalent versions to test with; the coordinator recommended authoring
one, because a brief is a run control the host pins rather than evidence, and
a sourced brief would still have needed rewriting to this issuer and pack. It
is `CP_DR_RESEARCH_BRIEF_V1`, `mode: linked`, scoped to `VMO2` / `Virgin Media
O2`, `source_mode: supplied_only` (invariant 1: the host has no web access, and
the pin refuses any other mode), `budget: standard`. The host writes `run_id`,
`cp0_sha256` and `authority_sha256` when CP-DR is invoked; the manifest carries
none of them, and the pin refuses a brief that does. Every question is placed
`consumer_module_id: NONE` after `CP-0`: on this pathway CP-DR is the
terminal deliverable, so no downstream module adopts the research.

Three locked questions, two the pack answers and one it cannot:

1. `RQ-impairment` — the stated cause of the Q4 2025 non-cash goodwill
   impairment. Answered by the Q4 release, page 7: "In Q4 2025, we recorded a
   non-cash goodwill impairment of £1,021.7 million primarily related to the
   impacts of the UK market and" / "macroeconomic conditions in the UK on
   estimated future cash flows."
2. `RQ-undrawn` — maximum undrawn commitments at 31 December 2025. Answered by
   the Q4 release, page 3: "At 31 December 2025, the company had maximum
   undrawn commitments of £1,378.0 million" / "equivalent." The Q3 release
   states the same amount at 30 September 2025, which is the contrary evidence
   a sound dossier searches and does not contradict.
3. `RQ-rating` — Moody's current corporate family rating and outlook. **Neither
   release names a rating agency or a rating**, so a supplied-only dossier must
   record it `UNRESOLVED` rather than answer from model memory.

## Keys, and where each came from

Authored from the two documents and the brief only, never from any run output,
capture file or result section; nothing has been run on this route.

- `expects_ready: ["CP-DR"]` — the route's one pinned consumer, which CP-0's
  T8 must report as ready.
- `expects_projection` — CP-DR `decision_scope` = `SCREENING_ONLY`, which the
  catalog declares for this pathway.
- `expects` — two CP-DR citation keys on the Q4 release, the first line of
  each answer above (each anchors exactly once in the extracted tokens).
- `expects_register` — TDR.3 `resolution_status` per question:
  `RQ-impairment` ANSWERED, `RQ-undrawn` ANSWERED, `RQ-rating` UNRESOLVED.
  Coverage is therefore expected at 67 (two of three), which the vendor's
  `validate_dossier` requires to be reported `Complete with Gaps`; that is not
  keyed, because it follows from the three rows.

## What awaits the owner

The two figures above (£1,021.7 million and £1,378.0 million) and the choice of
questions, before the step 7 run is authorized.
