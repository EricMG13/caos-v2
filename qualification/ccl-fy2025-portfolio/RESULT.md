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

- **Register keys.** The `ExpectedRegister` form landed with Task 8.1, and this
  set still carries none, deliberately. The VMO2 set's key asserts CP-L10's
  `TL10.2` liquidity-maturities evidence status, which was justified by reading
  both Virgin Media O2 releases; the equivalent conclusion for Carnival has to be
  read out of its 10-K's liquidity and maturity disclosures, and a key asserted
  without that reading would measure a guess rather than the module. Owed, with
  the reading, before this set is run.
- **The run itself**, and a signed verdict or a recorded reason why not.

## First authorized run — 18 September 2026

Authorized by the owner the same day ("authorize the two portfolio runs with the
Terra settings above, a $5 ceiling per run, today"). **Not signable:** the run
ended BLOCKED at CP-0's readiness gate, so CP-L10 never ran.

- Provider/model: `openrouter/openai/flex/high/65536` / `openai/gpt-5.6-terra`
- Price: `$0.000002` input, `$0.000012` output per token, dated 2026-09-18
- Run ceiling `$5.00`; `--attempts 2`; build `62a94ccd…` (§92)
- Run `ef040775-7c99-4645-b681-a11405308854`; evidence `9b9868e0e3bae784…`;
  performed `a3da30d4b8cc3ec4…`
- Retained database `caos_qualify_13ec1a9ca0814387aca7e8977dd1f9f1`, blob root
  `/var/folders/81/bwblpst93lb6wb3lwrk8k6800000gn/T/caos-qualify-pemds0zr`;
  capture `run-2026-09-18-capture.json`
- Charge: CP-0 **`$0.17845375`**, one call, accepted. Nothing else was called.

| | |
|---|---|
| Route | BLOCKED after CP-0 (1 artifact, 2 citations, proof sound) |
| `ready_met` / `projections_met` | false / false |
| Citation key | missed — CP-L10 did not run |

CP-0's T8 row for CP-L10 reads `DO NOT RUN` / `BLOCKED`: "Supply current
portfolio holdings/exposure, portfolio mandate and limits, eligible-security
universe, current security-market evidence, and applicable executed governing
security documents; rerun CP-0 after receipt." That is the methodology refusing
a portfolio decision over a 10-K alone, which is a defensible reading of what
`LITE_PORTFOLIO_DECISION` needs; the set's `expects_ready: ["CP-L10"]` assumed
otherwise. Whether the key or the corpus should change is the owner's call; the
key is not edited to match the run. The VMO2 set, over two earnings releases,
was judged ready on the same build.
