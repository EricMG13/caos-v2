# VMO2 FY2025 portfolio-screen qualification — no run has been performed

**No run has been performed against this set.** It is authored, loadable and
digested; nothing here reports a result, a verdict or a provider. The live run
is Phase 9 Task 9.1 step 7 and needs the owner's explicit authorization — it
costs real money and calls a real model.

## The set

- Qualification-set digest:
  `a46a1b4f597885e8…` (moved from `8e53fe3d…` when the register key below was
  added; a digest covers the keys, so the two are different sets)
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

- ~~**Register keys.**~~ The `ExpectedRegister` form landed with Task 8.1 and
  this set now carries one key: CP-L10's `TL10.2`, row
  `topic_id=LIQUIDITY_MATURITIES`, `evidence_status` must be `PARTIAL`. It is
  the key Task 8.1 justified from these same two releases -- they give undrawn
  commitments and covenant leverage, so the topic is not `MISSING`, and neither
  carries a maturity profile of the third-party debt, so it is not
  `SUFFICIENT`. Same module, same register, same documents, so the conclusion
  carries to this pathway unchanged. A `TL10.1` source-row key is still owed and
  is not guessed here.
- **The run itself**, and a signed verdict or a recorded reason why not.

## First authorized run — 18 September 2026

Authorized by the owner the same day ("authorize the two portfolio runs with the
Terra settings above, a $5 ceiling per run, today"). **Not signable:**
`complete` is false because the one citation key was missed.

- Provider/model: `openrouter/openai/flex/high/65536` / `openai/gpt-5.6-terra`
- Price: `$0.000002` input, `$0.000012` output per token, dated 2026-09-18,
  read from OpenRouter's published model list that day
- Run ceiling `$5.00`; `--attempts 2`; build
  `62a94ccd0ef6439f797d60ebb72e6a44e1d42db16cd8af217fc41b7f1d6ea72c` (§92)
- Run `2ab8b2e2-b577-45ca-87bd-8c45e3f7b9f2`; set `a46a1b4f597885e8…`
  (unchanged); evidence `1b9df866631eb3d8…`; performed `65701fdf5f8863c9…`
- Retained database `caos_qualify_9b87b7104a8d49f1badeffc12d47b3c4`, blob root
  `/var/folders/81/bwblpst93lb6wb3lwrk8k6800000gn/T/caos-qualify-fi8rdqvn`;
  capture `run-2026-09-18-capture.json`
- Charges: CP-0 `$0.13946575`; CP-L10 attempt 1 `$0.1660905` (refused
  `CITATION_NOT_LOCATED`), attempt 2 `$0.16364625` (accepted). Total
  **`$0.46920250`**.

| | |
|---|---|
| Route | COMPLETE, 2 artifacts |
| Proof | 5 citations, every one re-located |
| `ready_met` / `projections_met` | true / true |
| Citation key | `met=0, missed=1` — CP-L10 did not quote the £1,021.7m goodwill impairment line |

CP-L10 cited the adjusted EBITDA guidance, adjusted FCF and undrawn commitments
lines instead. The key is unchanged: it was authored from the documents before
any run, and moving it to what the model quoted would measure the model against
itself.

**Retention, corrected 18 September 2026 (§100):** the retained database named above was on the in-memory test server and was erased when that server restarted. The capture and blob root survive; a matrix can no longer be re-derived from the store for this run.
