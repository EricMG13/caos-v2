# VMO2 FY2025 portfolio-screen qualification — no run has been performed

**No run has been performed against this set.** It is authored, loadable and
digested; nothing here reports a result, a verdict or a provider. The live run
is Phase 9 Task 9.1 step 7 and needs the owner's explicit authorization — it
costs real money and calls a real model.

## The set

- Qualification-set digest:
  `8e53fe3d9c5e68011047cc1a71b9ff6d5eddbf89b4fe0c07479a62eec881a96a`
- Route: `LITE_CREDIT_22 / LITE_PORTFOLIO_DECISION` (`CP-0` → `CP-L10`, one
  REQUIRED edge, `decision_scope: SCREENING_ONLY`, terminal deliverable
  `CP-L10`)
- Documents: the Virgin Media O2 Q3 and Q4 2025 earnings releases, the same
  bytes as `qualification/vmo2-fy2025/`
  (`505bf1a0f4181c9c…` and `66055bbb8d27721d…`). They are copied rather than
  referenced because `server/qualification/on_disk._document` refuses a
  declared path that resolves outside the set's own directory; the register
  (`qualification/documents.json`) carries a row per copy.

## Keys, and where each came from

Authored from the documents, never from any run output, capture file or result
section. Nothing has been run on this route, so there was nothing to copy from.

- `expects_ready: ["CP-L10"]` — the route's one pinned consumer, which is
  exactly what CP-0's T8 is asked to report here (`_gate_expects`).
- `expects_projection` — CP-L10 `decision_scope` = `SCREENING_ONLY`, which the
  catalog declares for this pathway and the host projects beside the status;
  and CP-L10 `qa_status` = `Restricted`, the honest expectation over a
  two-release extract, as in the earnings sets.
- `expects` — one citation, CP-L10 against the Q4 release
  (`66055bbb8d27721d07a5e8cb834c9b96a256ada45a0812ea4fb2e7202ee4f64d`):

      we recorded a non-cash goodwill impairment of £1,021.7 million

  Q4 2025 release, page 7 of the extraction, the line reading
  `In Q4 2025, we recorded a non-cash goodwill impairment of £1,021.7 million
  primarily related to the impacts of the UK market and`. The quote was checked
  against the real extractor's token index for that page: it matches whole
  tokens exactly and matches **once**, so it anchors rather than refusing
  `CITATION_AMBIGUOUS`. It is the fact-carrying span of the line rather than the
  whole line, whose tail is a subordinate clause carrying no figure — the defect
  `CLAUDE.md`'s "borrowing-capacity key names a subordinate clause" entry
  records.

## What is owed

- **Register keys.** A richer `ExpectedRegister` key form is landing separately
  (`server/qualification/matrix.py`). This manifest deliberately carries no
  `expects_register`, so it loads against the schema as it is today. Once that
  form lands, this set owes register keys on CP-L10's `TL10.2` (the Q4 goodwill
  impairment topic row and its `scope_status`) and on `TL10.1` (the source row
  for each release).
- **The run itself**, and a signed verdict or a recorded reason why not.
