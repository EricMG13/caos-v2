# CAOS v2 — Codebase Duplication & Divergence Report

**Date:** 2026-09-15
**Codebase:** `/Users/ericguei/Documents/caos-workbench`
**Phase:** Phase 2 Duplication Hunt
**Scope:** Exhaustive audit of cross-feature and within-feature duplication across all 9 architectural features. Every claim cites $\ge$ 2 exact `file:line` locations.

---

## Executive Summary

Static analysis and call-graph tracing reveal significant structural and logic duplication across CAOS v2. While domain invariants (such as immutable bundle authority, pure route resolution, and fail-closed budgets) are strictly maintained, independent development across project phases has produced:

1. **Triple-Redundant State Commitments:** Every successful node execution invokes `record_outcome` **three consecutive times** across three different abstraction layers (`canonical.py`, `runtime.py`, `runs.py`), creating two redundant database transactions and row locks per node attempt.
2. **Triplicated Verification/Proof Engines:** A complex 6-step artifact proof pipeline is implemented in three separate files (`qualification/proof.py`, `deliverable/canonical.py`, `methodology/canonical.py`) with subtle, accidental divergences in gate exclusions and token caching.
3. **Decentralized Canonical JSON Hashing with Latent Hash Discrepancies:** 10+ locations independently serialize JSON for cryptographic SHA-256 hashing. Because some locations omit `ensure_ascii=False`, Unicode/accented characters are escaped as `\uXXXX` in audit logs and route stores, but preserved as raw UTF-8 in deliverable signatures.
4. **Ad-Hoc Authorization & Visibility Logic:** Four different read routers re-implement case visibility queries, with one read endpoint (`reports.py`) taking an exclusive database write lock on a GET request.
5. **Repeated Error, Transaction, and Command Boilerplate:** Identical transaction cleanup blocks, subprocess parsers, command execution envelopes, and frontend form lifecycle state machines are duplicated across multiple modules.

---

## Part 1: Cross-Feature Duplication Analysis

### Concern 1: Triplicated Artifact Verification & Proof Engines

#### Locations
1. `server/qualification/proof.py:207-332` (`_CanonicalReader.proven`):
   Called during qualification (`assert_orchestration_proof`). Reconstructs host identity, reads stored blobs, invokes `read_record`, checks `record_authority_matches(..., verify=True)`, verifies `accepted_lineage`, validates markdown projections (`validate_markdown`) excluding `{GATE_MODULE, "CP-CF"}` from route nodes, and re-anchors citations with a shared `TokenIndex` (`self.index`).
2. `server/deliverable/canonical.py:140-218` (`_Reader.proven`):
   Called during deliverable generation (`canonical_payload`). Reconstructs host identity, reads stored blobs, invokes `read_record`, checks `record_authority_matches(..., verify=True)`, verifies `accepted_lineage`, validates markdown projections (`validate_markdown`) excluding `{GATE_MODULE, MODEL_MODULE}`, and re-anchors citations WITHOUT a `TokenIndex`.
3. `server/methodology/canonical.py:760-884` (`_verified_accepted` & `_accepted_record`):
   Called during runtime prompt assembly for upstream nodes (`_upstream_records`). Reads stored record blob, invokes `read_record`, checks `record_authority_matches(..., verify=False)` (using cached manifest), verifies `accepted_lineage`, validates projections (`validate_markdown`) excluding `{GATE_MODULE, "CP-CF"}`, checks `_forecast_inputs` if module is `"CP-CF"`, but skips citation re-anchoring.
4. `server/deliverable/revisions.py:145-188` (`prove_revision`):
   Wraps `canonical_payload` under case lock and compares re-derived digest against stored `payload_sha256`.

#### Why They Diverged
Developed in separate project phases: `methodology/canonical.py` in Phase 3 for upstream node prompt context, `deliverable/canonical.py` in Phase 6 for committee publication, and `qualification/proof.py` in Phase 9 for benchmark scoring against answer keys. `qualification` added a `TokenIndex` cache to resolve an 8x N+1 SQL bottleneck, but the optimization was never backported to `deliverable`.

#### Divergence Classification: Accidental Duplication with Divergence Hazards
The core 6-step verification pipeline is identical across all three:
$$\text{blobs.get} \longrightarrow \text{host\_identity} \longrightarrow \text{read\_record} \longrightarrow \text{record\_authority\_matches} \longrightarrow \text{accepted\_lineage} \longrightarrow \text{validate\_markdown}$$
The differences are accidental maintenance hazards:
- `deliverable/canonical.py:192` uses the constant `MODEL_MODULE`, whereas `qualification/proof.py:300` and `methodology/canonical.py:942` hardcode `"CP-CF"`.
- `qualification/proof.py` uses `TokenIndex`, but `deliverable/canonical.py` does not (leaving deliverable assembly unoptimized).
- `methodology` skips citation re-anchoring while `deliverable` and `proof` enforce it.

#### Consolidation Recommendation
Extract a single canonical verification function `verify_canonical_artifact(...)` in `server/methodology/verification.py`. Accept flags for `reanchor_citations: bool` and an optional `token_index: TokenIndex`. Replace hardcoded `"CP-CF"` strings with `MODEL_MODULE`.

---

### Concern 2: Triple-Redundant Outcome Recording & Attempt Settling

#### Locations
1. `server/methodology/canonical.py:212-216`:
   `record_outcome(conn, attempt_id=attempt, outcome=CallOutcome(charge, model, generation, diagnostic))`
   Called immediately after `provider.complete(...)` in the canonical executor.
2. `server/engine/runtime.py:410-419`:
   `record_outcome(conn, attempt_id=attempt_id, outcome=CallOutcome(result.charge, result.model, result.generation_id, result.diagnostic_sha256))`
   Called in `_execute_attempt` right after `executor.execute_node(...)` returns.
3. `server/store/runs.py:215-224`:
   `record_outcome(conn, attempt_id=attempt, outcome=CallOutcome(accepted.charge, accepted.model, accepted.generation_id, accepted.diagnostic_sha256))`
   Called inside `_accept` during `accept_attempt(...)`.
4. `server/store/outcomes.py:176-235`:
   The underlying implementation of `record_outcome`. Commits its own transaction (`conn.commit()`), acquires a row lock on `run_attempts`, queries `call_outcomes` and `budget_ledger`, checks replay equality, and inserts spend.

#### Why They Diverged
- `canonical.py` added `record_outcome` to satisfy Invariant 8 (spend must be committed before parsing/validating responses so transport failure cannot discard spend).
- `runtime.py` added `record_outcome` assuming the runtime orchestrator owned outcome recording.
- `runs.py` added `record_outcome` inside `_accept` assuming an artifact must guarantee an outcome row.
- Because `record_outcome` was written defensively to treat identical replays as idempotent no-ops, the three calls coexisted without raising exceptions.

#### Divergence Classification: Pure Accidental Duplication
Every successful node attempt executes `record_outcome` **three consecutive times**:
1. `canonical.py` commits `call_outcomes` and `budget_ledger`.
2. `runtime.py` acquires attempt row lock, checks replay, commits.
3. `runs.py` acquires attempt row lock, checks replay, commits.

#### Consolidation Recommendation
Remove `record_outcome` from `runtime.py:410` and `runs.py:215`. The executor alone owns recording the outcome immediately upon transport return. In `runs.py:215`, verify existence via `SELECT 1 FROM call_outcomes WHERE attempt_id = %s` rather than re-invoking `record_outcome`. This saves 2 redundant database commits and row locks per node attempt.

---

### Concern 3: Parallel Route Loading, Deserialization, and Validation

#### Locations
1. `server/engine/route.py:401-419` (`route_digest`):
   Serializes `ResolvedRoute` using a **compact list-of-lists** representation:
   `"nodes": [[n.route_node_id, n.module_id, n.stage] ...], "edges": sorted([[e.source, e.target, e.type.value] ...])`.
2. `server/store/routes.py:207-230` (`_canonical`):
   Serializes `ResolvedRoute` for storage in `run_routes.resolved` using a **dict-of-dicts** representation:
   `"nodes": [{"route_node_id": ..., "module_id": ..., "stage": ...}], "edges": [{"source": ..., "target": ..., "type": ...}]`.
3. `server/store/routes.py:137-175` (`_decode` and `_rebuild` in `resolved_route`):
   Rebuilds `ResolvedRoute` from stored text. Validates limits, regexes, node uniqueness, and re-runs `dependency_order` topological sort, checking `route_digest(route) == row[2]`.
4. `server/qualification/harness.py:423-468` (`_eligible`):
   Re-loads `pin, route = execution_input(...)` and re-validates route profile and model extension flags.
5. `server/api/reads/run.py:268-281`:
   Loads `resolved_route(conn, run_id)` and re-computes `route_digest(route)` on the fly instead of reading the stored `route_digest` column.

#### Why They Diverged
`route_digest` aimed for minimal byte size for cryptographic signing, while `_canonical` favored human-readable dictionary JSON for database inspection. Subsequent consumers defensively re-parsed and re-hashed routes independently.

#### Divergence Classification: Accidental Duplication
Maintaining two distinct JSON schemas for the exact same `ResolvedRoute` entity introduces redundant encoders, decoders, and validators.

#### Consolidation Recommendation
Standardize on a single canonical dictionary JSON serialization in `server/engine/route.py` that serves both hashing (`route_digest`) and persistence (`pin_route`). Store the computed digest in `run_routes.route_digest` and read it directly in read endpoints rather than re-computing.

---

### Concern 4: Disparate Authority & Permission Checking Mechanisms

#### Locations
1. `server/api/deps.py:82-100`:
   `actor_from_request` parses `x-caos-user` and `x-forwarded-groups`/`x-caos-role` into `Actor(user_id, role)`.
2. `server/store/members.py:69-85`:
   `standing_of(conn, case_id, user_id)` queries `case_members`. `satisfies(held, required)` compares rank: `READER (0) < WRITER (1) < APPROVER (2) < ADMIN (3)`.
3. `server/api/commands/_request.py:93-135`:
   `case_standing` checks: (1) live standing in DB (raises `CASE_NOT_FOUND` if None), (2) global role (`if write and actor.role is GlobalRole.READER: raise NOT_AUTHORISED`), (3) standing floor (`not satisfies(standing, floor)`).
4. `server/store/audit.py:125-132`:
   `_require_standing` inside `governed_write`: under case lock, checks `not satisfies(standing_of(...), action.requires) -> raise NOT_AUTHORISED`. (Omits checking `GlobalRole`).
5. `server/api/reads/`:
   - `server/api/reads/upload.py:65-73`: Uses `case_path` dependency, calls `standing_of`, queries `cases`.
   - `server/api/reads/run.py:188-210`: Uses `_visible_case` helper executing an inline lateral join.
   - `server/api/reads/analysis.py:87-99`: Inlines `standing_of` and queries `cases`.
   - `server/api/reads/reports.py:84-91`: Takes an exclusive `lock_case` write lock on a GET read endpoint and checks `standing_of` twice.
6. `frontend/src/app/authority.ts:1-74`:
   Defines an unrelated `Authority` interface (`{ case, seq, bound }`) used for UI concurrency ticketing.

#### Why They Diverged
Separating request-time auth from commit-time auth was intentional (`SYSTEM_SPEC.md` §8) to guard against mid-request revocation. However, read endpoints were written by different authors who created 4 different ad-hoc visibility checks. In `reports.py:88`, a developer mistakenly used `lock_case` (which acquires a PostgreSQL `FOR UPDATE` lock) on a read endpoint.

#### Divergence Classification: Legitimate Defense-in-Depth, Accidental Implementation Drift
- Request-time vs commit-time checks are legitimate.
- Read endpoints implementing 4 different queries (and write-locking reads) is accidental duplication and a performance defect.
- `authority.ts` on frontend is a semantic naming collision with backend governance.

#### Consolidation Recommendation
1. Provide a single FastAPI dependency `require_visible_case(case_id, caller, store)` in `server/api/deps.py` for all read endpoints. Remove `lock_case` from `reports.py:88`.
2. Pass `GlobalRole` into `GovernedAction` so `governed_write` enforces global role checks at commit time alongside case standing.
3. Rename frontend `authority.ts` to `ticket_machine.ts` or `session_binding.ts`.

---

### Concern 5: Duplicated Canonical JSON Serialization & Hashing Logic

#### Locations
1. `server/deliverable/canonical.py:61-66`:
   `payload_bytes`: `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`
2. `server/deliverable/filing.py:189-196`:
   `receipt_bytes`: `json.dumps({...}, sort_keys=True, separators=(",", ":")).encode("utf-8")`
3. `server/store/commands.py:85-98`:
   `request_digest`: `json.dumps({...}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`
4. `server/store/audit.py:214-219`:
   `_digest_of`: `json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")`
5. `server/store/routes.py:207-229`:
   `_canonical`: `dumps({...}, sort_keys=True, separators=(",", ":"))`
6. `server/engine/route.py:401-419`:
   `route_digest`: `dumps({...}, sort_keys=True, separators=(",", ":")).encode("utf-8")`
7. `server/qualification/store.py:28-32, 101, 327-330`:
   `Evidence.sha256`, `_digest`: `json.dumps(document, sort_keys=True, separators=(",", ":")).encode()`
8. `server/qualification/matrix.py:185`:
   `qualification_set_digest`: `json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()`
9. `server/calculators/cash_flow.py:118`:
   `cash_flow_digest`: `json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")`
10. `server/evidence/ingest.py:290`:
    `_fingerprint`: `json.dumps(meta, sort_keys=True, separators=(",", ":")).encode("utf-8")`

#### Why They Diverged
Every subsystem needed cryptographic SHA-256 hashes of dictionaries. Without a centralized utility, each developer wrote `json.dumps(..., sort_keys=True, separators=(',', ':'))`.

#### Divergence Classification: Accidental Duplication with Semantic Inconsistencies
- `canonical.py` and `commands.py` pass `ensure_ascii=False`.
- `commands.py` passes `allow_nan=False`.
- `audit.py`, `route.py`, and `qualification/store.py` default to `ensure_ascii=True`, escaping non-ASCII text as `\uXXXX`.
- **Result:** If a payload containing accented characters passes through `audit.py` vs `canonical.py`, their generated SHA-256 digests will diverge!

#### Consolidation Recommendation
Create `server/canonical_json.py` providing `canonical_bytes(obj) -> bytes` and `canonical_digest(obj) -> str` enforcing `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, and `allow_nan=False`. Replace all 10 occurrences.

---

### Concern 6: Multiple Citation Re-Anchoring Calls & N+1 Token Lookup Bottlenecks

#### Locations
1. `server/methodology/canonical.py:299`:
   `anchored = verify_citations(conn, delivered=blocks, citations=citations)` (called without `index` during attempt acceptance).
2. `server/deliverable/canonical.py:207-216`:
   `anchored = verify_citations(self.conn, delivered=self.delivered, citations=...)` (called without `index` during deliverable generation).
3. `server/qualification/proof.py:320-330`:
   `anchored = _unless_refused(lambda: verify_citations(self.conn, delivered=self.delivered, citations=requests, index=self.index))` (called with `index=self.index` during proof assertion).
4. `server/evidence/citations.py:143-152`:
   `verify_citations(conn, delivered=delivered, citations=[citation], index=index)` inside `citation_candidates`.
5. `server/evidence/citations.py:77-88`:
   `anchor_citation(...)` (un-scoped test suite helper).

#### Why They Diverged
When Phase 9 qualification tests ran against hundreds of citations, developers noticed that querying `source_tokens` per citation produced an 8x N+1 SQL penalty. They added a `TokenIndex` in `citations.py` and used it in `qualification/proof.py`, but never updated `deliverable/canonical.py`.

#### Divergence Classification: Accidental Omission
`deliverable/canonical.py` performs identical citation anchoring across all route nodes from scratch without `TokenIndex`, leaving report and committee generation exposed to the N+1 database performance penalty.

#### Consolidation Recommendation
Initialize `self.index = TokenIndex()` in `_Reader.__init__` in `server/deliverable/canonical.py:155` and pass it to `verify_citations`.

---

### Concern 7: Parallel Document Ingestion & Staging Pipelines

#### Locations
1. `server/api/commands/cases.py:206-258` (`admit_sources`) + `server/evidence/ingest.py:98-250` (`prepare_pack`, `admit_prepared`):
   Production path. Multipart HTTP upload $\rightarrow$ in-memory `prepare_pack` $\rightarrow$ `run_command` idempotency check $\rightarrow$ `governed_write` (case lock, standing check, `audit_events` row) $\rightarrow$ `admit_prepared` persists blobs, tokens, and blocks.
2. `server/qualification/on_disk.py:112-202` (`load_qualification_set`, `_document`) + `server/qualification/harness.py:265-270`:
   Qualification harness path. Reads local directory $\rightarrow$ creates `Document(filename, data)` $\rightarrow$ calls `create_case` $\rightarrow$ calls `admit_pack` directly.
   **Bypasses:** `run_command`, `GovernedAction`, `governed_write`, `audit_events`, and case membership grants.
3. `server/qualification/harness.py:444-465` (`_eligible`):
   Parallel validation: re-queries `source_set_members` and re-hashes disk document bytes to verify stored evidence.

#### Why They Diverged
Production required HTTP multipart streaming, client authentication, and audit chaining. The qualification harness was created for local CLI benchmarks and bypassed governance wrappers for convenience.

#### Divergence Classification: Legitimate Source Specialization; Accidental Storage Divergence
Reading from disk vs reading from multipart HTTP forms is legitimate specialization. However, completely bypassing `governed_write` in the qualification harness means test suites fail to exercise the audit log and membership models used in production.

#### Consolidation Recommendation
Keep disk reading and HTTP multipart parsing separate, but have `harness.py` invoke `admit_prepared` through `run_command(ADMIT_SOURCES)` using a synthetic test actor (`Actor(HARNESS_UUID, GlobalRole.ADMIN)`).

---

### Concern 8: Parallel Error & Refusal Conversion Across API Routers

#### Locations
1. `server/api/app.py:226-274`:
   Global exception handlers for `Refusal`, `StarletteHTTPException`, and `RequestValidationError` (maps FastAPI 422 to `REQUEST_INVALID` or `RUN_NOT_FOUND`).
2. `server/api/commands/_request.py:61-90, 137-142`:
   `json_body` (custom body reader catching `ValidationError`) and `command_response`.
3. Ad-hoc UUID path parameter parsing across Read routers:
   - `server/api/reads/upload.py:45-56`: `case_path` dependency catching `ValueError`.
   - `server/api/reads/run.py:176-186`: `_uuid(value, code)` helper catching `ValueError`.
   - `server/api/reads/analysis.py:53-70`: `case_path` and `run_query` catching `ValueError`.
   - `server/api/reads/reports.py:50-65`: Manual parameter validation.

#### Why They Diverged
FastAPI's default 422 response returns internal schema validation details and quotes user input, violating security requirements. Because FastAPI evaluates path parameter types before dependency injection, authors wrote custom string-typed path arguments with manual `try...except ValueError` blocks in each file.

#### Divergence Classification: Pure Accidental Duplication
Four different patterns for parsing UUIDs and preventing 422 errors across read routers.

#### Consolidation Recommendation
Centralize `CasePath` and `RunQuery` in `server/api/deps.py` as standard FastAPI dependencies that validate UUIDs and raise `Refusal(RefusalCode.CASE_NOT_FOUND)` / `Refusal(RefusalCode.RUN_NOT_FOUND)`.

---

### Concern 9: Parallel Queue, Storage, and Execution State Machines

#### Locations
1. `server/store/work.py:55-85, 130-150` & `server/engine/worker.py:100-220`:
   PostgreSQL worker queue (`run_work`). Polls with `FOR UPDATE SKIP LOCKED`, manages lease tokens, timeouts, and worker heartbeats.
2. `server/qualification/harness.py:530-556`:
   Synchronous execution engine. Bypasses `run_work`, executing `run_route(..., execution=Execution(..., lease=None))` directly in-process.
3. `server/engine/route.py:50-57, 267-362` (`NodeState`):
   Pure DAG state machine (`RUNNABLE`, `BLOCKED`, `RESTRICTED`, `COMPLETE`) recomputed dynamically.
4. `server/store/__init__.py:126-148` (`RunStatus`):
   Durable run state machine (`QUEUED`, `RUNNING`, `CANCELLED`, `REFUSED`, `COMPLETE`) stored in `runs.status` and emitted to `run_events`.

#### Why They Diverged
`run_work` was built for background polling workers; `harness.py` was built for synchronous test benchmarks. `NodeState` manages micro-step DAG readiness, while `RunStatus` manages macro run lifecycle.

#### Divergence Classification: Legitimate Specialization with a Coupling Hazard
Macro `RunStatus` and micro `NodeState` serve distinct and necessary roles. However, `server/engine/runtime.py:123` accepting `lease=None` allows any caller to advance a run without lease fencing.

#### Consolidation Recommendation
Retain both state machines. Create an explicit `DirectExecution` context vs `LeasedExecution` in `runtime.py` to prevent accidental un-fenced execution in production.

---

## Part 2: Within-Feature Duplication Analysis

### Feature 1: Edge Authentication & API Gateway
1. **Lifespan Startup Failure Protocol:** `server/api/site.py:103-111` and `server/api/edge.py:211-219` duplicate the low-level ASGI `lifespan.startup.failed` message transmission and refusal raising.
   - *Fix:* Consolidate into `fail_lifespan_startup` in `server/api/edge.py`.
2. **Refusal Response Serialization:** `server/api/app.py:219-224` (`_body`) and `server/api/edge.py:322-335` (`_refuse`) duplicate building and serializing `RefusalBody(code, clears=CLEARS[code])`.
   - *Fix:* Expose `refusal_response_payload` in `server/api/wire.py`.
3. **API Path Prefix Predicate:** `path == "/api" or path.startswith("/api/")` is repeated at `site.py:115`, `edge.py:237`, `edge.py:292`, and `app.py:241`.
   - *Fix:* Define `is_api_path(path)` in `edge.py`.

### Feature 2: Evidence Ingestion & Citation Anchoring
1. **Pinned Source Membership 6-Table SQL Join:** `server/evidence/read.py:37-55` (`_RUN_BLOCK_QUERY`) and `server/evidence/page.py:52-70` (`_PAGE_QUERY`) duplicate an 18-line SQL join across `run_inputs`, `source_set_versions`, `source_set_members`, `live_sources`, and `source_extractions`.
   - *Fix:* Define a shared CTE/view `PINNED_SOURCE_JOIN` in `server/store/`.
2. **Token Grouping by Line:** `server/evidence/citations.py:265-277` (`_rectangles`) and `server/evidence/ingest.py:372-384` (`_blocks`) duplicate grouping tokens into line dictionaries and computing bounding box extents.
   - *Fix:* Consolidate into `group_tokens_by_line` in `server/evidence/extract.py`.
3. **Subprocess Output Parsing:** `server/evidence/pdf.py:201-216` (`_answer`) and `server/evidence/pdf.py:218-238` (`_frame_answer`) duplicate JSON stdout decoding and refusal mapping.
   - *Fix:* Consolidate into `_parse_child_response` in `server/evidence/pdf.py`.

### Feature 3: Case & Run Management, Route Resolution & Gate Planning
1. **Governed Command Boilerplate:** `server/api/commands/runs.py:155-172`, `runs.py:208-229`, and `runs.py:296-322` duplicate `request_digest`, `run_command`, and `command_response` envelope wrapping.
   - *Fix:* Implement `execute_governed_command` in `server/api/commands/_request.py`.
2. **Case-Run Ownership Query:** `server/api/commands/runs.py:108-115` (`_owned_run`), `server/store/gates.py:351-365` (`_case_of`), and `server/api/commands/execution.py:215-220` (`_require_owned`) duplicate querying run ownership on cases.
   - *Fix:* Unify as `require_case_run` in `server/store/runs.py`.

### Feature 4: Execution Engine & Worker Runtime
1. **Transaction Rollback-or-Close Boilerplate:** The identical 6-line `psycopg.Error` / `BaseException` rollback block is repeated at `server/store/budget.py:74-79`, `server/store/runs.py:196-201`, `server/store/runs.py:424-429`, `server/store/work.py:84-89`, and `server/store/outcomes.py:37-42`.
   - *Fix:* Provide `isolated_transaction` context manager in `server/store/__init__.py`.
2. **Fenced Run State Checks:** `server/store/budget.py:91-95`, `server/store/runs.py:102-108`, and `server/store/runs.py:413-415` duplicate checks for `lock_run is RUNNING` and `require_lease`.
   - *Fix:* Extract `fence_running_run` in `server/store/runs.py`.
3. **Worker Lease Settlement:** `server/engine/worker.py:146-159`, `worker.py:162-178`, and `worker.py:180-189` duplicate exception cleanup and lease release/stop calls.
   - *Fix:* Consolidate into `settle_worker_lease`.

### Feature 5: Methodology Bundle, Canonical Validation & Financial Calculators
1. **Dual Authority Digest Implementations:** `server/methodology/bundle.py:334-347` (`delivered_authority_digest`) and `server/methodology/bundle.py:367-380` (`authority_digest`) implement two divergent hashing schemes for the same file set.
   - *Fix:* Standardize on one canonical authority digest format in `bundle.py`.
2. **Catalog Path & JSON Parsing:** `server/methodology/canonical.py:100`, `server/methodology/runner.py:35`, and `server/api/commands/runs.py:75` duplicate loading and parsing `CREDIT_OS_V_MODULE_CATALOG_v2.json`.
   - *Fix:* Consolidate into `load_catalog(bundle)` in `server/methodology/vendor.py`.

### Feature 6: Deliverable Assembly, Governance & Audit Filing
1. **Revision Retrieval Query:** `server/deliverable/filing.py:35-45` (`_revision`), `server/deliverable/revisions.py:135-140` (`read_revision`), and `server/api/reads/reports.py:92-98` (`_read`) duplicate querying `deliverable_revisions`.
   - *Fix:* Export `load_revision_identity` from `server/deliverable/revisions.py`.
2. **Signer Independence Assertion:** `server/deliverable/filing.py:90-96` (`freeze`) and `server/deliverable/filing.py:137-144` (`file_deliverable`) duplicate checking signature digests and distinct actors.
   - *Fix:* Extract `assert_independent_signers` in `server/deliverable/filing.py`.
3. **Renderer SHA-256 Digest Pinning:** `server/deliverable/filing.py:127` dynamically hashes `render.py` while `server/deliverable/verify_package.py:21` hardcodes the SHA-256 string.
   - *Fix:* Define `RENDERER_SHA256` once in `server/deliverable/render.py`.

### Feature 7: Storage, Content-Addressed Blobs & Transactional Governance Core
1. **Case Row Lock Queries:** `server/store/events.py:58-63` (`lock_run`), `server/store/cases.py:20-31` (`lock_case`), and `server/store/audit.py:83` (`governed_write`) execute independent queries to acquire row locks on `cases`.
   - *Fix:* Route all case row locking strictly through `server.store.cases:lock_case`.

### Feature 8: Frontend Workspace UI
1. **Document State Sync Hook Pattern:** `frontend/src/sections/directory/DirectorySection.tsx:22-27`, `frontend/src/sections/upload/UploadSection.tsx:18-23`, and `frontend/src/sections/run/controls.tsx:69-72` duplicate the `useState(doc)` / `if (doc !== seen)` render-sync idiom.
   - *Fix:* Create a shared hook `useSyncedPropState` in `frontend/src/app/`.
2. **Governed Command Form Lifecycle & Intent Retry State Machine:** `frontend/src/sections/directory/NewCase.tsx:64-108` and `frontend/src/sections/upload/AdmitSources.tsx:71-109` duplicate a 45-line state machine managing intent keys, offline retries, pending spinners, error formatting, and document refetches.
   - *Fix:* Extract a reusable custom hook `useGovernedAction`.
3. **Ad-Hoc Section Refetching:** `frontend/src/sections/directory/NewCase.tsx:30-45` (`refetchDirectory`) and `frontend/src/sections/upload/AdmitSources.tsx:27-42` (`refetchUpload`) bypass application transport and duplicate fetch calls.
   - *Fix:* Replace with a typed helper `refetchSection` in `frontend/src/app/transport.ts`.
4. **HTTP Response JSON Parsing:** `frontend/src/app/transport.ts:113-119` and `frontend/src/app/commands.ts:69-75` duplicate `bodyOf(response)` with try/catch.
   - *Fix:* Move `bodyOf` to a common transport utility in `frontend/src/app/`.

### Feature 9: Benchmark Qualification & Model Performance Verification
1. **SHA-256 Hex Digest Regex Validation:** `server/api/reads/qualification.py:55-57`, `server/qualification/verdict.py:49, 147-151`, and `server/qualification/matrix.py:33` compile duplicate regexes matching 64 hex characters.
   - *Fix:* Standardize on `validate_sha256_digest` in `server/qualification/__init__.py`.
2. **5-Tuple Evidence Identity Matching:** `server/qualification/store.py:62-72` and `store.py:176-224` duplicate unpacking and verifying the 5-tuple identity `(qset_sha, build_id, adapter_version, provider, model)`.
   - *Fix:* Add an equality method `matches_identity` on `PerformedEvidence`.

---

## Part 3: Unification Priority & Impact Matrix

| Rank | Duplication Issue | Scope | Category | Impact / Risk | Consolidation Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Triple-Redundant `record_outcome` Calls** | Cross-Feature (F4, F5, F7) | Accidental | **HIGH**: 2 redundant DB transactions and locks per node attempt | Low (remove 2 call sites) |
| **2** | **Divergent Canonical JSON Serializers** | Cross-Feature (F1, F3, F5, F6, F7, F9) | Accidental | **HIGH**: Unicode character escaping differences cause latent hash mismatch | Low (centralize `canonical_json.py`) |
| **3** | **Triplicated Artifact Proof Engines** | Cross-Feature (F5, F6, F9) | Accidental | **HIGH**: Verification drift between execution, deliverable, and qualification | Medium (unify verification pipeline) |
| **4** | **Ad-Hoc Read Authorization & Write Locking** | Cross-Feature (F1, F6, F7) | Accidental | **MEDIUM**: Write lock on `reports.py` read endpoint; 4 disparate queries | Low (unify `require_visible_case`) |
| **5** | **Missing `TokenIndex` in Deliverables** | Cross-Feature (F2, F6) | Accidental | **MEDIUM**: 8x N+1 SQL overhead during report rendering | Low (pass `TokenIndex` in `deliverable`) |
| **6** | **Frontend Command & Form State Machine** | Within-Feature (F8) | Accidental | **MEDIUM**: 45+ lines duplicated between `NewCase` and `AdmitSources` | Low (extract `useGovernedAction`) |
| **7** | **Pinned Source SQL Join** | Within-Feature (F2) | Accidental | **MEDIUM**: 18-line SQL join duplicated in block & page readers | Low (extract SQL constant/view) |
| **8** | **Transaction Rollback Boilerplate** | Within-Feature (F4) | Accidental | **LOW**: Repeated 6-line error handler across 5 store functions | Low (context manager) |
| **9** | **UUID Parameter Handling in API Routers** | Cross-Feature (F1, F3, F5, F6) | Accidental | **LOW**: Boilerplate try/except blocks to bypass FastAPI 422 | Low (add `CasePath`/`RunQuery` deps) |
