# CCL FY2025 portfolio-screen qualification — no run has been performed

**No run has been performed against this set.** It is authored, loadable and
digested; nothing here reports a result, a verdict or a provider. The live run
is Phase 9 Task 9.1 step 7 and needs the owner's explicit authorization — it
costs real money and calls a real model.

## The set

- Qualification-set digest:
  `5d50d1e7b9d39b0318d730ea98c795518c72e8f8644fe321b6f96acbc4bb2f29`
- Route: `LITE_CREDIT_22 / LITE_PORTFOLIO_DECISION` (`CP-0` → `CP-L10`, one
  REQUIRED edge, `decision_scope: SCREENING_ONLY`, terminal deliverable
  `CP-L10`)
- Document: the Carnival Corporation & plc FY2025 Form 10-K text extract, the
  same bytes as `qualification/ccl-fy2025/`
  (`8fa7fceda34be50b3b9b5406e0c9269b5269870d1cd8c2bdafb682755a1c88e6`). It is
  copied rather than referenced because
  `server/qualification/on_disk._document` refuses a declared path that resolves
  outside the set's own directory; the register
  (`qualification/documents.json`) carries a row for the copy.

## Keys, and where each came from

Authored from the document, never from any run output, capture file or result
section. Nothing has been run on this route, so there was nothing to copy from.

- `expects_ready: ["CP-L10"]` — the route's one pinned consumer, which is
  exactly what CP-0's T8 is asked to report here (`_gate_expects`).
- `expects_projection` — CP-L10 `decision_scope` = `SCREENING_ONLY`, which the
  catalog declares for this pathway and the host projects beside the status;
  and CP-L10 `qa_status` = `Restricted`, the honest expectation over a single
  filing extract, as in the earnings sets.
- `expects` — one citation, CP-L10 against the 10-K extract:

      Debt extinguishment and modification costs | ( 409 ) | ( 79 ) | ( 111 ) |

  Page 12 of the extraction, the consolidated statements of income (loss), the
  line between `Interest expense, net of capitalized interest` and
  `Other income (expense), net`. A core income-statement figure, and the P&L
  side of the three-figure debt-extinguishment trap the owner's answer key
  records (409 through the P&L, 401 added back, 272 in cash) — so a screen that
  reads the cash-flow add-back as the charge cites something else. The quote was
  checked against the real extractor's token index for that page: it matches
  whole tokens exactly (the parentheses and pipes are their own tokens) and
  matches **once**, so it anchors rather than refusing `CITATION_AMBIGUOUS`.

## What is owed

- **Register keys.** A richer `ExpectedRegister` key form is landing separately
  (`server/qualification/matrix.py`). This manifest deliberately carries no
  `expects_register`, so it loads against the schema as it is today. Once that
  form lands, this set owes register keys on CP-L10's `TL10.2` (the
  debt-extinguishment topic row) and on `TL10.1` (the source row for the
  filing).
- **The run itself**, and a signed verdict or a recorded reason why not.
