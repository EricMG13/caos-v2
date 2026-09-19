# CCL FY2025 portfolio-screen qualification — one authorized run, 18 September 2026 (below)

**Before 18 September 2026 no run had been performed against this set;** the authorized run is recorded at the end. It is authored, loadable and
digested; nothing here reports a result, a verdict or a provider. The live run
is Phase 9 Task 9.1 step 7 and needs the owner's explicit authorization — it
costs real money and calls a real model.

## The set

- Qualification-set digest:
  `7dcfa84602ff94a38fcc2627d15b7922acb08c23a871f7280e16bfe4a92d6a6c` since
  owner decision A (below); the set the authorized run was performed against
  was `5d50d1e7b9d39b0318d730ea98c795518c72e8f8644fe321b6f96acbc4bb2f29`. A
  digest covers the keys, so the two are different sets.
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

**Superseded by owner decision A (below).** The keys this section describes are
the ones the authorized run was performed against; the set now carries only
`expects_blocked: ["CP-L10"]`. They are kept here as the record of what that
run was measured by.

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

## Owner decision A, 18 September 2026 — the set measures the refusal

The owner chose to keep this set and change what it measures: over a 10-K
alone, the correct answer for `LITE_PORTFOLIO_DECISION` is that CP-0 refuses
CP-L10 for want of portfolio context, and a correct refusal is a pass. The VMO2
portfolio set keeps measuring the ready path. **The key was changed by the
owner's decision about what the set measures, not fitted to a run's output**:
nothing in it is taken from the run's text, and it names no reason the refusal
must give -- only that CP-0 withholds CP-L10.

- Removed: `expects_ready: ["CP-L10"]`, the CP-L10 citation key and the two
  CP-L10 projection keys (`decision_scope`, `qa_status`). Each asks something
  of a CP-L10 handoff, which a refused CP-L10 never produces. The set carried
  no CP-0 key, so none is kept.
- Added: `expects_blocked: ["CP-L10"]` (`docs/DECISIONS.md` §99), met when
  CP-0's T8 verdict for CP-L10 is `BLOCKED` or `CONDITIONAL`; a met key waives
  the run-COMPLETE requirement only for a run that ended BLOCKED.
- New set digest:
  `7dcfa84602ff94a38fcc2627d15b7922acb08c23a871f7280e16bfe4a92d6a6c`.

**The retained run was not re-scored through the matrix.** Its database,
`caos_qualify_13ec1a9ca0814387aca7e8977dd1f9f1`, no longer exists on the test
server (its blob root does), and nothing was re-run or re-called. Read offline
from the retained CP-0 record blob (`34b54985…`, T8 readiness `CP-L10:
BLOCKED`) and this directory's capture (status `BLOCKED`, proof sound), the row
would read `blocked_met: true` and the snapshot `complete: true`. That is a
reading of stored facts, not a performed snapshot: the stored evidence
(`9b9868e0…`) binds the earlier digest and stays unsignable, and a verdict over
this set needs it performed again.
