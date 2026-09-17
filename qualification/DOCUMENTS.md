# The document register

Emitted 17 September 2026 against `codex/execute-repair-plan`, re-emitted after Task 9.1 added the portfolio-screen set's document copies.

> **How this file is made.** The hand-authored half is
> [`documents.json`](documents.json) — the demand, the public location, the status,
> the note. The table below is emitted by `scripts/document_register.py --report`,
> which reads that file plus every `qualification/*/qualification.json` and
> computes each document's size and SHA-256 from the bytes on disk. Do not
> hand-edit the table: change `documents.json` and re-emit. The same script is a
> gate — it exits non-zero when a qualification set names a document the
> register does not list, and when a row claims `in_hand` for something that is
> not a file under `qualification/`.

Nothing here is fetched by the system. Invariant 1 makes web discovery
structurally absent, so every document arrives because the owner sourced it and
the coordinator admitted it. A `to_source` row is a request to a person.

## Why a register

Twelve of the catalog's twenty-three modules are proven and eleven are not
(`docs/COMPLETION_PLAN.md` §2), and what most of the eleven are missing is not
code but evidence: CP-4 needs executed instruments, CP-2H needs dated agency
actions, CP-3D needs timestamped prices, CP-8 needs a decision that was
actually taken. Those demands were read out of the vendored `SKILL.md` files
once, for this plan. Without somewhere to put that reading, it is re-derived
per task and drifts; with a register it is one artefact a gate can hold to the
tree.

Each row's `demand_verified` says whether the module's own `SKILL.md` states a
document gate, or whether the demand is inferred from its purpose and register
names. Two rows are inferred; the note says from what.

## The register

<!-- emitted: register table. Everything between these markers is what
`scripts/document_register.py --report` prints; a test holds them equal, so
a row typed here is a row that fails. -->
| id | issuer | document | status | modules | pathways | bytes | fits ceiling | sha256 |
|---|---|---|---|---|---|---|---|---|
| `vmo2-q3-2025-earnings` | VMO2 | Virgin Media O2 Q3 2025 earnings release | in_hand | CP-0, CP-L10, CP-5, CP-1, CP-1B, CP-2, CP-8 | LITE_EARNINGS_UPDATE, LITE_PORTFOLIO_DECISION, EARNINGS_UPDATE | 144538 | yes | `505bf1a0f4181c9c…` |
| `vmo2-q4-2025-earnings` | VMO2 | Virgin Media O2 Q4 2025 earnings release | in_hand | CP-0, CP-L10, CP-5, CP-1, CP-1B, CP-2, CP-8 | LITE_EARNINGS_UPDATE, LITE_PORTFOLIO_DECISION, EARNINGS_UPDATE | 178368 | yes | `66055bbb8d27721d…` |
| `ccl-fy2025-10k` | CCL | Carnival Corporation & plc FY2025 Form 10-K (text extract) | in_hand | CP-0, CP-L10, CP-1, CP-1A, CP-1B, CP-1D, CP-2, CP-2A, CP-2D, CP-2E, CP-2G, CP-3C, CP-5 | LITE_EARNINGS_UPDATE, LITE_PORTFOLIO_DECISION, LIQUIDITY_REVIEW, EARNINGS_UPDATE, COVENANT_REFINANCING, PORTFOLIO_DECISION, FULL_CREDIT_ASSESSMENT | 311896 | yes | `8fa7fceda34be50b…` |
| `vmo2-q3-2025-earnings-portfolio` | VMO2 | Virgin Media O2 Q3 2025 earnings release (portfolio-screen set copy) | in_hand | CP-0, CP-L10 | LITE_PORTFOLIO_DECISION | 144538 | yes | `505bf1a0f4181c9c…` |
| `vmo2-q4-2025-earnings-portfolio` | VMO2 | Virgin Media O2 Q4 2025 earnings release (portfolio-screen set copy) | in_hand | CP-0, CP-L10 | LITE_PORTFOLIO_DECISION | 178368 | yes | `66055bbb8d27721d…` |
| `ccl-fy2025-10k-portfolio` | CCL | Carnival Corporation & plc FY2025 Form 10-K (text extract, portfolio-screen set copy) | in_hand | CP-0, CP-L10 | LITE_PORTFOLIO_DECISION | 311896 | yes | `8fa7fceda34be50b…` |
| `ba-fy2025-10k` | BA | The Boeing Company FY2025 Form 10-K (text extract) | to_source | CP-0, CP-1, CP-1A, CP-1B, CP-1D, CP-2, CP-2A, CP-2D, CP-2E, CP-2G, CP-3C, CP-5 | LIQUIDITY_REVIEW, EARNINGS_UPDATE, COVENANT_REFINANCING, FULL_CREDIT_ASSESSMENT | — | — | — |
| `f-fy2025-10k` | F | Ford Motor Company FY2025 Form 10-K (text extract) | to_source | CP-0, CP-1, CP-1B, CP-1D, CP-2, CP-2A, CP-2D, CP-2E, CP-2G, CP-3C, CP-5 | LIQUIDITY_REVIEW, EARNINGS_UPDATE, FULL_CREDIT_ASSESSMENT | — | — | — |
| `ccl-debt-documents` | CCL | Executed debt documents: indentures, credit agreements, maturity schedules | to_source | CP-4, CP-3C, CP-4C | COVENANT_REFINANCING, PORTFOLIO_DECISION, FULL_CREDIT_ASSESSMENT, LITE_COVENANT_REFINANCING, DISTRESSED_RESTRUCTURING, LITE_DISTRESSED_RESTRUCTURING | — | — | — |
| `ba-debt-documents` | BA | Executed debt documents: indentures, credit agreements, maturity schedules | to_source | CP-4, CP-3C, CP-4C | COVENANT_REFINANCING, PORTFOLIO_DECISION, FULL_CREDIT_ASSESSMENT | — | — | — |
| `ccl-rating-actions` | CCL | Dated agency rating actions, outlooks, watches and the applicable published criteria | to_source | CP-2H | LITE_DISTRESSED_RESTRUCTURING, LITE_FULL_CREDIT_SCREEN, FULL_CREDIT_ASSESSMENT, DISTRESSED_RESTRUCTURING | — | — | — |
| `ccl-market-data-extract` | CCL | Dated market-data extract: instrument prices, spreads, curve points with observation timestamps | to_source | CP-3D, CP-3 | MARKET_DISLOCATION, PORTFOLIO_DECISION, RELATIVE_VALUE | — | — | — |
| `cruise-peer-pack` | CCL | Peer pack: cruise-sector peers' FY2025 filings for the aligned metric set | to_source | CP-1C | LITE_RELATIVE_VALUE, LITE_FULL_CREDIT_SCREEN, RELATIVE_VALUE | — | — | — |
| `ccl-decision-record` | CCL | A completed decision record at T0: thesis, expectations, dissent, and the decision date | to_author | CP-8 | LITE_DECISION_LEDGER, DECISION_LEDGER | — | — | — |
| `cp-dr-research-brief` | — | A CP-DR research brief and the supplied evidence its questions need | to_author | CP-DR | LITE_DEEP_RESEARCH, DEEP_RESEARCH | — | — | — |
| `distressed-disclosure-statement` | — | A distressed issuer's disclosure statement, plan or restructuring support agreement | not_available | CP-4C | DISTRESSED_RESTRUCTURING, LITE_DISTRESSED_RESTRUCTURING | — | — | — |
| `answer-key-3issuer` | CCL, BA, F | ANSWER_KEY_3ISSUER.md — human-authored core facts, derived values and 24 traps per issuer | **key source, never admitted** | — | — | — | — | — |
<!-- /emitted -->

Sixteen documents: six `in_hand`, seven `to_source`, two `to_author`, one
`not_available`; plus one key source. Three of the six in hand are the
portfolio-screen set's own copies of the other three, which the on-disk loader
requires because it refuses a declared path resolving outside its set root. The `bytes` and `sha256` columns are
blank for a document that does not yet exist on the machine the table was
emitted from — for `ba-fy2025-10k` and `f-fy2025-10k` they are filled from the
owner's out-of-tree document register, which is why those two rows carry measurements
while the other `to_source` rows do not.

## Sourcing list for the owner

Each row below is a document the programme needs and does not have in the tree.
No URL or accession number is asserted anywhere here: where one was not
verified, the venue and the identifier that *is* known are given instead, and
the register's `source` stays `null`. Inventing an accession would be worse
than leaving it blank, because a wrong one reads as provenance.

1. **`ba-fy2025-10k`, `f-fy2025-10k` — copy in from the owner's document register.**
   Both are already held, read-only, at
   `/Users/ericguei/Documents/Co-Pilot Agents/assessment_3issuer_20260719/document register/`,
   with their raw HTML and SEC XBRL company facts in `raw/` beside them. This
   repository has not copied them. The coordinator admits each under its own
   digest (`0446b367…` and `97a38bc1…` as measured on 17 September 2026) and
   records the provenance in the receiving set's `RESULT.md` header. Neither
   fits the request ceiling; see **Size** below.
2. **`ccl-debt-documents`, `ba-debt-documents` — executed debt documents.**
   Indentures, credit agreements and their maturity schedules, filed as
   exhibits on EDGAR. `docs/COMPLETION_PLAN.md` records the issuers' CIKs as
   **815097** (Carnival) and **12927** (Boeing); the exhibit and accession
   numbers were not established here, so the owner locates the exhibits by CIK
   and states the accession when admitting. CP-4's runbook step 1 is a Document
   Gate producing `T4F.1 Controlling Documents`, so a 10-K debt footnote does
   not substitute: CP-4 construes clause meaning and needs the instrument.
3. **`ccl-rating-actions` — dated agency rating actions and criteria.**
   CP-2H's Phase 1 wants dated issuer and instrument ratings, outlook and
   watch, recovery ratings where applicable, agency reports, issuer disclosures
   and the current criteria, with agency-issued evidence separated from
   management characterisation. Agency releases and criteria are
   entitlement-gated; an issuer's own disclosure of its ratings is the freely
   available substitute, and CP-2H is told to label it as the weaker evidence.
   This is a soft gate — without it CP-2H may do methodology-only work with
   limitations, so the module can be proven `Restricted` now and `Passed` only
   once this arrives.
4. **`ccl-market-data-extract` — a dated market-data extract.** Instrument
   identifiers, currency, coupon, maturity, seniority and pricing convention,
   and per observation the source, entitlement, bid/mid/ask or evaluated
   status, observation time and staleness. CP-3D states that required market
   observations cannot be replaced with model memory. This is the one demand no
   filing can satisfy: it is priced and timestamped rather than disclosed. The
   owner supplies it as a document; it is admitted under its own digest like any
   other.
5. **`cruise-peer-pack` — the peers' own FY2025 filings.** CP-1C's steps 0 and
   1 are a Peer Discovery Gate and a Peer Data Gate; each peer figure it
   benchmarks has to be citable, so the pack is the peers' filings rather than
   a summary table. Which peers is the owner's call — naming them here would be
   the host choosing a peer set, which is the judgement CP-1C exists to make
   defensible.
6. **`ccl-decision-record` — an owner-authored decision record (to author).**
   CP-8 is explicit: *"Blocked: No decision record available to attribute.
   STOP — do not reconstruct a thesis after the fact."* So it must be a real,
   dated record from before the outcome window. The outcome side of the pair is
   already in hand for VMO2 (Q3 then Q4 2025).
7. **`cp-dr-research-brief` — an owner-authored research brief (to author).**
   Materialized from
   `vendor/deploy-v/skills/cp-os-credit-os/references/CP_DR_RESEARCH_BRIEF_V1.md`,
   carrying subject, question, decision context, as-of, horizon, boundaries,
   source mode and budget. It must declare `supplied_only`: CP-DR's capability
   gate blocks `web_only` and `hybrid` when web research is unavailable, and
   here that is structural, not a configuration.
8. **`distressed-disclosure-statement` — not available.** CP-4C's Phase 1
   distress gate needs evidence of payment or default risk, a failed
   refinancing, a distressed exchange or LME escalation, a covenant or
   enforcement event, adviser engagement, a filing, or another named distress
   trigger, and returns `Not Applicable` rather than a speculative
   restructuring when none is met. No issuer in the document register is distressed, so
   over this document register only CP-4C's `Not Applicable` path can be proven. Proving
   the substantive path means choosing a different issuer — a document register decision
   for the owner, not a fetch.

## Size

`MAX_REQUEST_BYTES` is **1,048,576** (`server/provider.py`), and it bounds the
*whole encoded request* — model, parameters, the module's delivered authority
files, every upstream record, and the evidence — not the document alone. So a
document comfortably under the ceiling can still put a wide route's prompt over
it, and `CONTEXT_OVER_CEILING` refuses before any attempt, reservation or call.

The `bytes` column is the document's own bytes on disk. For the two PDFs that
is the file, which overstates what reaches a prompt: the pinned extractor
yields 38,360 bytes of text from the Q3 release and 51,942 from Q4 (measured
with the vendored pdfminer). For the `.txt` extracts the file *is* the text.

| Document | Bytes reaching a prompt | Fits alone |
|---|---|---|
| `vmo2-q3-2025-earnings` | 38,360 (extracted text) | yes, with ample room |
| `vmo2-q4-2025-earnings` | 51,942 (extracted text) | yes, with ample room |
| `ccl-fy2025-10k` | 311,896 | yes — 30% of the ceiling |
| `ba-fy2025-10k` | 1,177,234 | **no** — 112% of the ceiling |
| `f-fy2025-10k` | 1,922,743 | **no** — 183% of the ceiling |

Which pathway tasks may run before per-node evidence selection exists:

- **VMO2 (two releases, ~90 KB of text together)** — any pathway whose nodes
  are served by earnings releases. The LITE earnings route already has a
  complete live snapshot here.
- **CCL (312 KB)** — runnable whole today, with roughly 700 KB left for
  authority files and upstream records. That headroom shrinks with every node
  on the route, so the long routes (`FULL_CREDIT_ASSESSMENT`'s 19 nodes) are
  the ones to measure rather than assume.
- **BA and F** — not runnable whole at all. They need the per-node evidence
  selection the ledger owes ("The gate's evidence demands are dropped"), which
  is the same change CP-0's `evidence_demand` and `active_representation_ids`
  are waiting on. Until then they are held in the register as sourced-but-
  unrunnable, which is the honest state and not a reason to drop the rows.

## The key source

`ANSWER_KEY_3ISSUER.md` (8,268 bytes, as of 19 July 2026) holds the owner's
independent reading of the three 10-Ks: core facts, derived values and 24 traps
per issuer. It is a **key source** — a qualification set's `expects` rows may
be authored from it — and it is **never an admitted document**. Admitting it
would put the answers inside the evidence the modules read, and a key measured
against a document register that contains the key measures nothing. It has no row in the
documents table for exactly that reason; the script emits it in its own line,
labelled.

One thing it cannot do: `ExpectedCitation` is
`(module_id, document_sha256, matched_text)`, so a key's derived values and
traps become citation expectations, not value comparisons. The known-gaps
ledger entry "An answer key names citations, not figures" is the standing
statement of that limit, and it applies to every key authored from this
document.
