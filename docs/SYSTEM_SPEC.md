# CAOS v2 — system spec

Repair target structure. Scope and phase acceptance live in
`docs/REPAIR_PLAN.md`; decisions §39 reconciles the historical rebuild plan.
The workspace and its sections live in `docs/IA_SPEC.md`. The tracked handoff
records what is implemented; a target described here is not an acceptance claim.

Older inherited decision numbers (including §§18, 24, 25, 38, 45 and 48)
refer to CAOS-Final and resolve through the mapping in decisions §12, not the
same-numbered local entries. Repair decision §39 governs current phase order.

---

## 1. Shape

```
                          browser (static export, no Node in prod)
                                     │  HTTPS · SSE
                          ┌──────────┴───────────┐
                          │      API (FastAPI)   │  strict named wire models
                          └──────────┬───────────┘
        ┌──────────────────┬─────────┼──────────┬──────────────────┐
   ingestion          route          │       forecast        deliverable
   + citation       resolution    execution     (CP-CF)       rendering
   anchoring        + pinning       loop            │          + filing
        └──────────────────┴─────────┼──────────────┴──────────────┘
                          ┌──────────┴───────────┐        ┌─────────────┐
                          │    PostgreSQL 17     │        │  blob store │
                          │  domain · runs ·     │        │  CAS, sha256│
                          │  events · audit      │        │  bytes only │
                          └──────────────────────┘        └─────────────┘
                          ┌──────────────────────┐
                          │ methodology bundle   │  vendored, digest-verified
                          │ (Deploy V, read-only)│  on the bytes at use
                          └──────────────────────┘
```

The current host has one API process. Repair Phase 3 proves the shared runtime
and canonical validator without a worker. Repair Phase 4 adds one worker beside
the API, with PostgreSQL claims/leases, a shared blob root and the same runtime.
The API enqueues governed work; disconnecting a browser does not cancel a
provider operation. Decision §39 supersedes the historical no-worker limit.

No checkpointer, second database, message broker or restored publication/model
build service. Worker deployment is a Phase 4 target, not implemented status.

---

## 2. Storage

PostgreSQL owns everything transactional. Bytes live in a content-addressed
blob store keyed by `sha256`; the database holds the digest, never the bytes.

| Group | Tables |
|---|---|
| Tenancy | `cases`, `case_members`, `users` |
| Evidence | `sources` (read through the `live_sources` view, `docs/DECISIONS.md` §45), `source_sets`, `source_set_members`, `source_blocks`, `source_tokens` |
| Runs | `runs`, `run_routes`, `run_nodes`, `run_attempts`, `run_events`, `budget_ledger` |
| Artifacts | `artifacts`, `snapshots`, `snapshot_members` |
| Deliverable | `deliverable_drafts`, `deliverable_opinions`, `deliverable_publications` |
| Audit | `audit_events`, `audit_chain_heads` |

This is the target table set. `server/store/schema.sql` is the immutable legacy
migration; `server.store.MIGRATIONS` defines the current applied schema prefix.
Tables arrive through append-only migrations with the feature that first writes
them. Follow `docs/MIGRATIONS.md`; do not edit an applied SQL file.

Rules that do not bend:

- **Transactional pairing.** A governed write commits state and its audit event
  in one transaction. A run-state transition commits state and its run event in
  one transaction, and no event is inserted without the transition it records —
  proven either by the row lock the transition is taken under or by a
  conditional update whose zero rows mean no event. That is what makes terminal
  events exactly-once.
- **`run_events.seq`** is per-run monotonic, allocated under the run row lock.
- **Append-only** means append-only: `run_events`, `run_attempts`,
  `deliverable_opinions`, `audit_events` have no UPDATE path.
- **`BoundaryText`** on every string that can reach pinned state, a revision, a
  frozen payload or an audit event. NFC-normalised before the length bound;
  rejects lone surrogates, Unicode Cc controls except CR/LF/TAB, and
  bidirectional override/isolate controls. Never a bare `str`.
- **Audit chain.** `audit_events` is hash-chained per case with a
  `audit_chain_heads` lock row. The chain has no external anchor; detect a
  rewrite by comparing a retained package's head with the live head.

### `source_blocks` and `source_tokens`

Blocks are the unit `read_evidence` returns and are one row per block keyed by
`(source_id, block_id)` — not a JSON column on the source row. Tokens are the
coordinate index behind invariant 11 (§5): one row per extracted text run with
its page and rectangle. Tokens are never returned to a module; they exist so the
host can re-locate a quote and refuse one it cannot.

---

## 3. Methodology boundary

The vendored Deploy V bundle is the authority. It is read-only at runtime and
verified on the bytes at use, not at startup only.

- **Module lookup** is `Bundle.skill_of` in `server/methodology/bundle.py`.
  Reuse that manifest-backed seam; there is no separate `registry.py` or
  `ModuleSpec` to implement against. The live set and each module's files come
  from the catalog and the
  manifest, never written out (`docs/DECISIONS.md` §24); which calculator a
  module may select is a rule, not a field (§25). The host's one declaration
  is `_CARVE_OUTS`: CP-PARSE (§5).
- **Calculators** are host-owned. Only a `(module_id, calculator_id)` pair the
  host declares can select code; the calculator and its helper module are read
  through no-follow file handles and digest-checked; work factors are bounded
  per calculator. A module asks for a calculation; it never supplies the code.
- **Pin.** A run records the bundle build id and digest. A run pinned to one
  build never executes under another. Never edit a file that exists upstream
  (`DECISIONS.md` §6). Host additions go in new skill folders and require a
  dated decision entry and regenerated manifests; they are part of the pinned
  build and are verified at use too.
- **Provider frontmatter never survives.** Whatever a module claims about its
  own identity, period, module id or digests is an expectation the host
  re-verifies against the store.

---

## 4. Route resolution and execution

The full argument is `docs/DECISIONS.md` §2. The contract:

```python
# resolution — pure, no I/O
resolve_route(catalog, profile_id, selection_id, *,
              extensions=None,          # RouteExtensions: research_brief/model_extension
              predicates=None,          # freezes CONDITIONAL edges
             ) -> ResolvedRoute         # nodes (dependency order), typed edges, predicates

# pinning — at the plan gate, once
pin_route(run_id, resolved) -> route_digest      # row in run_routes, digest in run_events

# state — recomputed from accepted attempts, never stored; readiness is read
# from the accepted CP-0 artifact, never passed in (docs/DECISIONS.md §18)
node_states(route, accepted) -> {route_node_id: COMPLETE|BLOCKED|RESTRICTED|RUNNABLE}
frontier(route, accepted)    -> [route_node_id]   # RUNNABLE + RESTRICTED
```

An `expected_upstream_digests` in the first draft of this block had no consumer
and was never built; it is dropped rather than left as a promise
(`docs/DECISIONS.md` §38).

Edge types and their meaning are the bundle's, read from `profile["edges"]`:
`REQUIRED`, `CONDITIONAL`, `QA_GATE` block; `OPTIONAL`, `ADVISORY` degrade to
`RESTRICTED` — unless the source's readiness is `READY` or
`READY_WITH_LIMITATIONS`, in which case they block.

The current runtime processes the ready frontier sequentially and recomputes it
from stored accepted artifacts. Concurrency is not an acceptance prerequisite.
Repair Phase 2 must additionally derive terminal success from fulfilled
required obligations: an empty frontier alone cannot mean COMPLETE (§39).
A blocked route retains its reason and can resume when its permitted inputs or
approvals change through the governed version/generation mechanism.

- `run_node` reserves budget, resolves the provider, executes, validates the
  envelope, verifies citations, and commits the accepted attempt with its
  `artifact_sha256` — state and event in one transaction.
- Recovery is recomputation: on start, `node_states` over the surviving attempt
  rows tells the engine exactly what remains. There is nothing to restore.
- A node parked on a digest-bound interrupt (source-set pinning, research-plan
  approval) is `BLOCKED` on a host predicate, not a special engine state.

**Route coverage.** 18 pathways across two profiles: `FULL_CREDIT_32` (10,
2–19 nodes) and `LITE_CREDIT_22` (8). The catalog is the route set; adding one
is a catalog read.

---

## 5. Evidence and citation

Ingestion is the only way bytes enter a case. Web discovery is structurally
absent — there is no code path to it.

1. Admit or refuse the whole pack in one transaction. Store bytes at
   `sha256`; extract text with page and rectangle per token; pack blocks
   (one per line while small, bounded line groups once not, splitting a line at
   the group width rather than giving it a block of its own).
2. Classify, propose dispositions, select a route. Every one of these is a
   **labelled machine suggestion**. Issuer, document types, periods,
   dispositions and route are never taken from the browser and never from an
   instruction found inside a document.
3. Pin a source-set version. Version allocation locks the case row before
   reading the current version.

`read_evidence` is validated at the host boundary and fails closed with a typed
refusal. **No text is ever returned on refusal** — not in the exception chain,
not in the delivered set, not in the ledger.

A citation is `{document_sha256, page, bboxes, matched_text}`. The host
re-locates `matched_text` in `source_tokens` at the stated page and derives one
rectangle per line the quote covers -- the same shape as a PDF highlight's
QuadPoints, and for the same reason: selected text wraps. A single enclosing
rectangle would cover text the quote does not contain, which is the predecessor's
line-range defect wearing coordinates.

Every token carries the layout region and the line it belongs to, assigned by
the extractor. A region is a column or a paragraph; it is not a `block`, which
is the unit `read_evidence` returns. Matching joins tokens within a line and
continues only onto the next line of the same region, so a quote cannot be
assembled across a column gutter: the two columns are different regions and the
phrase never forms. A quote it cannot re-locate, or cannot locate exactly
once, is refused before it reaches the artifact, and the claim resting on it
with it; the envelope counts the claims refused, and an answer left with none is
refused (`docs/DECISIONS.md` §26). Citations may only name evidence actually
delivered to that node.

---

## 6. Forecast

The forward model is CP-CF's accepted artifact: a projection the host computes
from module-authored drivers, read in the Model section (`IA_SPEC.md` §4.6).
The workbook build that stood here — one model effect per pathway, overlays,
`source_lineage`, the expression-language calculator — went with CP-MODEL
(`docs/DECISIONS.md` §48; archived in `docs/archive/MODEL_BUILDER_SPEC.md`).
Calculation is pure and finite: non-finite values
and zero denominators are refused before use.

### 6.1 `cash_flow_forecast` — the deterministic forecast calculator

The calculator in `server/calculators/cash_flow.py` computes the forecast from
module-authored drivers. Decision §54 freezes the implemented contract.
It currently has no production caller: the verified CP-CF extension and
allowlisted invocation remain Task 5.2 (§6.2); no upstream file gains code.

**Closed input.** Required top-level fields are `opening`, `periods`,
`drivers`, `contractual`, `units`, `perimeter`; only `tolerance` is optional.

| Field | Supported meaning |
|---|---|
| `opening` | Required `cash`, `as_of_period_id`, `debt_by_facility[]` of `{facility_id, amount}`; unique facilities |
| `periods[]` | Required `period_id`, `fiscal_year`, `case`, `days`; unique case-period, caller order per case, integer-string days 1..366 |
| `drivers[]` | Unique requested case-period, status and both stated closing balances, and §54's 13 movements |
| `contractual` | Required `amortisation[]` with requested case-period, opened facility, amount; unique four-field entries |
| `units` | Required `{currency, scale}`: three uppercase currency letters, units/thousands/millions/billions |
| `perimeter` | Nonblank BoundaryText/NFC label, at most 64 characters |
| `tolerance` | Nonnegative reconciliation tolerance, default `"0.001"`, in the supplied units |

All nested objects are closed. Policy (sweep, minimum cash, revolver, FX),
maturities, coupons and the old driver `financing_investing` field refuse
`METHODOLOGY_INPUT_INVALID`. A missing movement on READY gives
`DRIVER_FIELD_MISSING`; a missing driver gives `DRIVER_MISSING`; status other
than READY gives `DRIVER_NOT_READY`. Present malformed numbers refuse the
whole request even if their row would be unavailable.

**The identities.** Contractual repayment sums that case-period's amortisation
rows, zero only when there are none. Acquisitions/disposals and FX/perimeter
are signed; all other movements are nonnegative.

```
closing_debt = opening_debt + issuance + pik + capitalised_interest
               - contractual_repayment - optional_repayment + fx_perimeter
financing_investing = issuance - contractual_repayment - optional_repayment
                      - acquisitions_disposals
fcf = cfo - capex - cash_interest - cash_taxes
closing_cash = opening_cash + fcf - distributions + financing_investing
residual_debt = stated_closing_debt - closing_debt
residual_cash = stated_closing_cash - closing_cash
```

Each case starts from supplied opening balances and chains computed closes.
A disagreement is `FORECAST_CHAIN_BROKEN`. Either residual magnitude above
tolerance makes the row `RESIDUAL_UNRECONCILED`; equality passes. Every later
row in that case is `PRIOR_PERIOD_UNAVAILABLE`, without affecting another case.

**Numeric boundary.** Every input number is a JSON string matching the entire
`-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?` grammar, never a JSON number, bool,
exponent or non-finite value. One local precision-38, half-even Decimal context
with InvalidOperation/DivisionByZero/Overflow traps covers all arithmetic.
Amounts serialize to six places, ratios to four; no ambient context is read.

**Output.** `cash_flow_forecast` returns
`{status, units, perimeter, rows[], checks[]}`; `forecast_bytes` produces
sorted-key, compact UTF-8 canonical JSON. Rows appear in requested order and
carry case, period, fiscal year and days, with computed fields or an unavailable
reason. Computed fields are operating (including EBITDA/revenue margin),
investing, financing (including derived financing/investing), FCF, debt, cash,
both signed residuals and metrics. Failed residual rows retain diagnostics.
Accessible cash equals closing cash; restricted cash and liquidity runway are
not implemented. Units and perimeter carry to output.

Metrics are closing debt/EBITDA, (closing debt-closing cash)/EBITDA,
EBITDA/cash interest and FCF/closing debt. Each returns
`{value: "<four-place string>", reason: null}` or, for a nonpositive
denominator, `{value: null, reason: "ZERO_OR_NEGATIVE_DENOMINATOR"}`.
A null ratio does not itself make a period unavailable.
Each requested row has a residual check with `check_id`, PASS/FAIL `outcome`
and `reason`; these are host records, not an archived workbook schema.

**Completeness and ceilings.** Complete means every requested pair appears
exactly once and is available. Missing values never become zero.
Before parsing any numeric, the host bounds 40 periods per case, 6 cases,
40 facilities, 2,000 amortisation entries, one driver per requested pair and
`max_periods_per_case × cases × (1 + facilities) <= 100000`.
The calculation is pure; the same request yields identical canonical bytes
under any ambient Decimal context. Invalid input refuses
`METHODOLOGY_INPUT_INVALID`; driver/residual issues use row reasons, retiring
the old whole-request driver/residual refusals on this path.

### 6.2 CP-CF — CashFlowEngine, and the no-edit rule

**The rule.** We never edit a file that exists upstream. One Deploy V release
changed 175 files including 21 of 22 `SKILL.md`; every upstream file we touch
becomes a permanent merge and moves the whole-tree pin. Additions live in new
folders under `skills/`, which upstream will never write to. Invariant 4's
preference — "behaviour changes ride wrappers or registry entries where they
can" — is satisfied as closely as a new calculator permits, because calculator
code must be bundle-resident and verified at use.

The id follows the host/utility convention — `CP-DR`, `CP-MODEL`, `CP-MEMO` —
not the numbered families. `CP-2CF` would read as a sub-module of CP-2 absorbed
by it, which is the opposite of what this is.

**Why a new module and not a wider CP-2G.** CP-2G's contract is fixed upstream
at seven drivers × three fiscal years × BASE and DOWNSIDE — 42 rows, three
divisions, annual only. A complete cash flow model needs quarterly periods,
more than two cases, per-facility contractual detail and covenant-period
testing. Widening CP-2G means editing upstream. CP-CF carries the wider
contract; CP-2G is left untouched as the annual base case and remains the
driver author.

**What CP-CF does.** It is an agent module whose job is explicitly *not*
arithmetic: it authors the driver set, the contractual schedule and the policy
(sweep, minimum cash, revolver behaviour, FX) from CP-1 actuals, CP-2G's
drivers and CP-4's covenant terms, each with evidence — then declares
`cash_flow_forecast` and reports what the calculator returned. Its handoff
carries the projection, the residual per period, and the first covenant breach
period per case.

**Route placement without editing the catalog.** Reuse the mechanism legacy
already has for CP-DR: a host-declared model extension, mirroring
`profile["research_extension"]`, appends CP-CF at stage 100 with synthesised
`REQUIRED` edges `CP-1 → CP-CF`, `CP-2G → CP-CF` and `CP-4 → CP-CF`. These
name every artifact owner CP-CF reads, including the covenant terms; CP-2G
completing alone does not release CP-CF. An extended route missing a required
owner is refused during resolution, before pinning, rather than dropping the
edge or running with missing inputs. No upstream pathway node list is edited,
and the extension is part of the resolved route that gets pinned at the gate
(§4), so replay is unaffected. `docs/DECISIONS.md` §23 had the extension place
CP-MODEL at 101 as well; §48 does not place it.

---

## 7. Deliverable

The host renders the deliverable from the frozen snapshot (`IA_SPEC.md` §4.8
for the surface; `docs/DECISIONS.md` §48 for why it is not CP-MEMO's `.docx`,
whose contract is archived in `docs/archive/REPORT_BUILDER_SPEC.md`):

- Exactly one HTML file, never overwriting. It prints to paper (`DESIGN.md`);
  no PDF, deck, dashboard or workbook deliverable.
- The accepted artifacts in route order, every figure carrying its citation
  (§5), then the analyst's narrative and the module provenance index.
- The render originates nothing, structurally: it is a function of frozen
  bytes, so there is no editorial boundary to police. Both sides of an
  unresolved conflict, `Restricted` and `SCREENING_ONLY` qualifications reach
  the page as the artifacts carry them.

Around it, the host's own chain: the analyst signs an opinion on the exact saved
revision (expected-head CAS), and a frozen revision takes no further signature;
freeze refuses without a current sign-off, refuses anyone who signed the
revision, and refuses a narrative asserting an uncited figure; filing refuses
the opinion signer and the freeze actor (`APPROVER_NOT_INDEPENDENT`) and writes
an immutable detached receipt naming three people. The approved bytes always read `PENDING APPROVAL`.

The audit package is verifiable with the standard library alone and re-renders
the export from the frozen payload.

---

## 8. Identity and authority

- Development trusts a role header, and only a loopback peer on a loopback
  `Host` is served without an edge token. Production is edge mode: a request
  without the operator edge's token is refused before routing, role comes from
  OIDC groups only, and a client role header never escalates
  (`docs/DECISIONS.md` §53).
- A repeated or lookalike identity header is not authenticated; an unsafe API
  request needs a same-origin fetch or the allowed `Origin`.
- Unknown and unauthorized cases and runs return the same 404.
- Case standing (`READER`/`WRITER`/`APPROVER`/`ADMIN`) and global role are
  separate and both are rechecked at commit time, not only at request time.
- **Persona is not authority.** The workspace section a user is looking at
  composes the view and grants nothing (`IA_SPEC.md` §2).

---

## 9. Wire

Every JSON success serves a *named* model. `extra="forbid"` both directions.
New field means a model change plus an updated pinned key set in the contract
test. One carve-out only: SSE and binary downloads are not JSON. A first draft
also carved out service-owned envelopes for the model and publication services;
they went with those services (`docs/DECISIONS.md` §48).

One document per section, not per widget — the per-widget query pattern is what
produced the open-envelope carve-outs in the current tree.

Case and run progress reach the browser as one SSE stream per case
(`/api/v1/cases/{case}/events`, `?run=` for a run's events) over `audit_events`
and `run_events`, with a composite `Last-Event-ID` resume (`docs/DECISIONS.md`
§52). Membership is rechecked before each event; the run half ends once its
terminal is delivered, each idle poll writes an SSE comment so a disconnect is
noticed, and streams close after five minutes for edge reauthentication. The client never reads event payloads — an event name triggers
a refetch.

---

## 10. Observability

Structured JSON on stdout, standard library only. Run and node transitions
(all of them through one emitter), typed refusals, provider call start and
finish, budget reserve and reconcile, gate interrupts, startup recovery,
intake dispositions.

**Never log source text, evidence block text, module output, prompts, or
anything a document produced.** Log the typed code, never the exception string.
Every string, including nested mapping keys, is redacted and truncated. The ban
is to be enforced by a test that drives a sentinel document through real
ingestion and a real agent node; nothing in the tree logs yet, and the test
arrives with the first logger (`docs/DECISIONS.md` §45).

---

## 11. Deployment and failure

One image, run as two containers -- the API (`server.api.site:application`,
one uvicorn worker, `--limit-concurrency 32`, `--no-proxy-headers`) and the
polling worker -- beside one PostgreSQL, one blob store and the operator's
authenticating edge, which is not in the image. The API serves the static
export and `/api` from one origin behind the edge guard. API and worker use the
same verified schema, bundle and blob configuration (`docs/DECISIONS.md` §53).

`GET /api/health` serves readiness on one closed model -- store, bundle, blob
store -- 200 when all three hold and the last round is fresh, 503 otherwise.
The probes run every 10 s on one background task, each under a 2 s deadline;
the route reads the cached round, needs no identity or edge token, and does no
I/O. The worker serves no health route.

Failure posture, in order of preference: refuse before acting; if acting,
commit exactly once; if uncertain, recompute rather than restore.

- A crash mid-node loses the attempt, not the run. The next pass recomputes
  `frontier` and retries the node.
- A crash in the commit gap yields one artifact, one charge, one terminal event.
- Every ceiling refuses the next operation before overspend. No provider call
  without a reservation.
- Dependencies are fully pinned and hashed; the image and CI install with
  `--require-hashes`. A red vulnerability gate is answered by recompiling, not
  by waiving.
