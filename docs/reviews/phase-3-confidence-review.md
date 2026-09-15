# CAOS Repair Phase 3 — whole-phase confidence review

- **Model:** Claude Opus 5 (`claude-opus-5`).
- **Effort:** `xhigh`, set with the app's session-effort control and read back
  from the session record (`effort: "xhigh"`, 2026-09-14T05:50:11Z) before this
  review turn began.
- **Target:** `codex/execute-repair-plan`, range `e2f2f9a..8736158` (Phase 2
  acceptance to the Phase 3 exit candidate, 82 commits).
- **Method:** `~/.claude/skills/confidence-review/SKILL.md`. Code and callers
  were read in source; suspected defects were reproduced before any fix.

## Least confident about (ranked), and what was found

1. **Which routes execute.** `require_adapter_route` gated execution and
   acceptance by module set alone.
   *Investigated:* enumerated every catalog pathway. Two consist only of adapter
   modules: `LITE_EARNINGS_UPDATE`, which is proven, and
   `LITE_PORTFOLIO_DECISION` (CP-0 -> CP-L10), which no test touches.
   **CONFIRMED P2:** that route pins, passes `execution_input`, runs and
   accepts. This contradicts REPAIR_PLAN Phase 3 work item 6: "Keep other
   routes disabled until equivalent contract tests exist."
   *Fixed:* `ADAPTER_ROUTES` (`server/methodology/handoff.py`) names the proven
   pathway, and `require_adapter_route` refuses any other pathway with
   `HANDOFF_MODULE_UNSUPPORTED`.
   *Test:* `tests/test_disabled_routes.py` now parametrizes both disabled-route
   tests with `PORTFOLIO`. Both failed before the fix (no refusal raised) and
   pass after it.
2. **Named-object boundary after the 3.4b review.** Enforcement is limited to
   boundaries the route can meet.
   *Investigated:* ran `named_objects` over all 20 catalog pathways. None
   refuses. CP-5 is held on `LITE_EARNINGS_UPDATE`, where CP-L10 both owns and
   carries `lite_financial_change_screen`, so the one executable boundary is
   enforced (`test_cp5_is_not_invoked_without_an_accepted_named_lite_object`).
   *Fine.* **P3 (docs), fixed:** §46.1 did not record the owned-or-carried rule
   or the meetable-only scoping, and two `route.py` docstrings still said
   "owns". §46 now has a dated refinement and the docstrings say "offers".
3. **Billing and exactly-once around Blocked, truncated and refused answers.**
   *Investigated:* `execute_handoff` records the bill and the exact response
   body before any analysis. `blocked_verdict` re-derives Blocked only from
   billed, unaccepted attempts with a stored body, after full validation and
   anchoring. Truncated or refused calls store no body. *Fine.*
   **Open P3 (pre-existing, Phase 4):** a crash after a successful answer's bill
   commits and before `accept_attempt` leaves a billed, unaccepted attempt, and
   resume calls again. This is the same gap as in Phase 2's loop, and
   REPAIR_PLAN Phase 4 owns worker crash recovery. *Recorded* in the CLAUDE.md
   "Two workers can pay for one node" ledger entry.
4. **Host-owned identity through the vendor's front-matter parser.**
   `_yaml` JSON-quotes every scalar with ASCII escapes, so a subject name with
   accents, quotes or backslashes might never compare equal. *Investigated:*
   fed `Société Générale`, `Say "hi"`, `a\b` and `A: B # c` to the vendor's
   `parse_restricted_frontmatter`; each decodes back to the original value.
   *Fine.*
5. **Prompt-section forgery.** *Investigated:* the tag is the first 16 hex
   characters of SHA-256 over the host front matter plus every untagged
   section. Evidence or upstream text that reproduces a marker must contain its
   own digest prefix, a 64-bit fixed point. *Fine.*
6. **Delivered-block judgement.** *Investigated:* PDF line ids are numbered
   across the whole document, not per page, and plain-text line numbers are
   global too. Admission and anchoring share `block_ids_by_line`. *Fine.*
   `CITATION_NOT_DELIVERED` never fires on a real run while every block is
   delivered; the ledger already records this.
7. **Document text in logs.** *Investigated:* the `pdfminer` logger gets a
   `NullHandler` with `propagate = False`, so child loggers stop there and
   `lastResort` is never used. `_extract` re-raises every failure as a bare
   code. *Fine.*
8. **Authority digest cache.** *Investigated:* the runtime, API and pre-call
   upstream reads use the per-manifest cache. The proof and the deliverable
   pass `verify=True`, and the executor's prompt reads every byte it delivers.
   *By design,* as recorded in the ledger entry "A record's lineage is
   re-checked…".
9. **Context ceiling ordering.** *Investigated:* `check_context` runs before
   `start_attempt` and `reserve` under `prospective_identity`, at the maximum
   ordinal, which gives a fixed-width prompt. The executor re-bounds the prompt
   after reserving. *Fine for one loop.* The Phase 4 interleave is recorded.
10. **Size gate.** Per-commit line counts over the range, with the gate's
    exclusions, found one commit over 800 lines: `be6710a` (211 added, 1,343
    deleted), which removes the claims executor. It is deletion-dominated,
    which the user allowed; recorded here.

## By design / already recorded

- A `%PDF-` header within the first kilobyte routes a document to the PDF
  extractor. Plain text quoting that header is refused
  (`test_plain_text_beginning_with_a_pdf_header_is_read_as_pdf_and_refused`).
- The page ceiling lays out one page past `max_pages` before refusing.
- The proof does not re-check the named-object hold. Only the runtime accepts,
  and direct store acceptance is the Phase 2 ledger's "terminal decision"
  entry.
- No calculator is exposed (§45.2). Read-model labels appear only in the
  deliverable, with API models in Phase 4 (§46.3).

## Remediation

One commit with the `ADAPTER_ROUTES` gate, its parametrized RED test, the §46
refinement, the `route.py` docstrings and the CLAUDE.md ledger entries.
Re-verified with the affected suites and then the wave gate.
