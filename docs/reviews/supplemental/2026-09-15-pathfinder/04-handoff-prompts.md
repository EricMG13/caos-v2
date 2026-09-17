# CAOS v2 — Per-System Handoff Prompts for `/make-plan`

**Date:** 2026-09-15
**Author:** Pathfinder Orchestrator
**Phase:** Phase 4 Per-System Handoff Prompts
**Target:** Ready-to-run copy-pasteable `/make-plan` prompts for each unified refactoring slice.

---

## 1. Handoff: Single-Point Outcome Recording Unification

```markdown
/make-plan Unify outcome recording to eliminate 3x redundant database transactions and locks per node attempt

### Target Unified Component
- **Component:** `server/store/outcomes.py`
- **Single Entry Point:** `record_outcome(conn: StoreConnection, attempt_id: UUID, outcome: CallOutcome) -> bool`

### Exact Call Sites to Rewrite
1. `server/methodology/canonical.py:212-216`:
   - RETAIN as the single authoritative call site executing immediately after `provider.complete(...)`.
2. `server/engine/runtime.py:410-419`:
   - DELETE the redundant call to `record_outcome` inside `_execute_attempt`.
3. `server/store/runs.py:215-224`:
   - REPLACE the redundant call to `record_outcome` inside `_accept` with a lightweight verification query:
     ```python
     with conn.cursor() as cur:
         cur.execute("SELECT 1 FROM call_outcomes WHERE attempt_id = %s", (attempt,))
         if cur.fetchone() is None:
             raise Refusal(RefusalCode.STORE_CORRUPT)
     ```

### Relevant Flowcharts & Specifications
- `PATHFINDER-2026-09-15/01-flowcharts/execution-engine.md` (Node Execution Pipeline)
- `PATHFINDER-2026-09-15/01-flowcharts/methodology-calculators.md` (Module Execution Happy Path)
- `docs/SYSTEM_SPEC.md` §2 (Transactional pairing and attempt outcomes)

### Anti-Pattern Guards
- DO NOT add a middleware or event-emitter layer for outcome recording.
- DO NOT keep the old call sites behind a feature flag or configuration toggle.
- DO NOT alter `record_outcome` signature or its internal atomic commit semantics.
- Verify that `make test` and `pytest tests/test_execution_engine.py` pass without regression.
```

---

## 2. Handoff: Canonical JSON & SHA-256 Hashing Unification

```markdown
/make-plan Centralize canonical JSON serialization and SHA-256 hashing across all subsystems

### Target Unified Component
- **Component:** `server/canonical_json.py`
- **Single Entry Points:**
  - `canonical_dumps(obj: object) -> str`
  - `canonical_bytes(obj: object) -> bytes`
  - `canonical_digest(obj: object) -> str` (computes SHA-256 over `canonical_bytes`)

### Exact Call Sites to Rewrite
1. `server/deliverable/canonical.py:61`: Replace `payload_bytes` body with `canonical_bytes(payload)`.
2. `server/deliverable/filing.py:189`: Replace `receipt_bytes` body with `canonical_bytes(receipt)`.
3. `server/store/commands.py:85`: Replace `request_digest` body with `canonical_digest(request)`.
4. `server/store/audit.py:214`: Replace `_digest_of` body with `canonical_digest(payload)`.
5. `server/store/routes.py:207`: Replace `_canonical` body with `canonical_bytes(route)`.
6. `server/engine/route.py:401`: Replace `route_digest` body with `canonical_digest(route)`.
7. `server/qualification/store.py:28`: Replace `Evidence.sha256` calculation with `canonical_digest(evidence)`.
8. `server/qualification/matrix.py:185`: Replace `qualification_set_digest` body with `canonical_digest(canonical)`.
9. `server/calculators/cash_flow.py:118`: Replace `cash_flow_digest` body with `canonical_digest(payload)`.
10. `server/evidence/ingest.py:290`: Replace `_fingerprint` body with `canonical_digest(meta)`.

### Relevant Flowcharts & Specifications
- `PATHFINDER-2026-09-15/01-flowcharts/storage-governance.md`
- `PATHFINDER-2026-09-15/01-flowcharts/deliverable-filing.md`
- `CLAUDE.md` §3 (Deterministic hashing, Unicode NFC boundary)

### Anti-Pattern Guards
- MUST enforce `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, and `allow_nan=False` in `canonical_dumps`.
- DO NOT use third-party libraries (e.g. `canonicaljson` or `orjson`); use Python standard library `json` and `hashlib`.
- DO NOT preserve divergent Unicode-escaping behavior (`\uXXXX`) in any subsystem.
- Run `pytest tests/` to confirm that all existing test digests match.
```

---

## 3. Handoff: Shared Canonical Artifact Verification Engine

```markdown
/make-plan Unify the 6-step canonical artifact verification engine across execution, deliverables, and qualification

### Target Unified Component
- **Component:** `server/methodology/verification.py`
- **Single Entry Point:**
  ```python
  def verify_canonical_artifact(
      conn: StoreConnection,
      blobs: BlobStore,
      bundle: Bundle,
      *,
      run_id: UUID,
      node: RouteNode,
      delivered_blocks: Mapping[UUID, Sequence[str]],
      token_index: TokenIndex | None = None,
      reanchor_citations: bool = True,
      verify_manifest: bool = True,
  ) -> VerifiedArtifact:
  ```

### Exact Call Sites to Rewrite
1. `server/qualification/proof.py:207-332`:
   - Replace the internal logic of `_CanonicalReader.proven` with a single call to `verify_canonical_artifact(..., token_index=self.index, reanchor_citations=True, verify_manifest=True)`.
2. `server/deliverable/canonical.py:140-218`:
   - Initialize `self.index = TokenIndex()` on `_Reader.__init__`.
   - Replace the internal logic of `_Reader.proven` with `verify_canonical_artifact(..., token_index=self.index, reanchor_citations=True, verify_manifest=True)`.
3. `server/methodology/canonical.py:760-884`:
   - Replace `_verified_accepted` with `verify_canonical_artifact(..., token_index=None, reanchor_citations=False, verify_manifest=False)`.
4. Standardize module constants:
   - Replace string literal `"CP-CF"` in `proof.py:300` and `methodology/canonical.py:942` with `MODEL_MODULE` imported from `server.engine.route`.

### Relevant Flowcharts & Specifications
- `PATHFINDER-2026-09-15/01-flowcharts/methodology-calculators.md`
- `PATHFINDER-2026-09-15/01-flowcharts/deliverable-filing.md`
- `PATHFINDER-2026-09-15/01-flowcharts/benchmark-qualification.md`

### Anti-Pattern Guards
- DO NOT create an abstract base class or strategy pattern; use a single pure procedural function.
- DO NOT omit the `TokenIndex` optimization in `deliverable/canonical.py`.
- DO NOT skip citation verification in `deliverable/canonical.py`.
- Run `pytest tests/test_filing_chain.py` and `pytest tests/test_qualification_harness.py` to verify byte-identical proofs.
```

---

## 4. Handoff: Unified Read Authorization & Case Visibility Dependency

```markdown
/make-plan Unify case visibility and standing checks across API read routes, eliminating database write locks on reads

### Target Unified Component
- **Component:** `server/api/deps.py`
- **Single Entry Point:**
  ```python
  VisibleCase = Annotated[CaseMetadata, Depends(require_visible_case)]
  ```

### Exact Call Sites to Rewrite
1. `server/api/reads/reports.py:84-91`:
   - DELETE `lock_case(conn, case_id)` write lock completely from `_read`!
   - Replace manual standing check and case query with `case: VisibleCase = Depends(require_visible_case)`.
2. `server/api/reads/upload.py:35`:
   - Replace `case_path` dependency and manual `standing_of` query with `case: VisibleCase = Depends(require_visible_case)`.
3. `server/api/reads/run.py:73`:
   - Replace `_visible_case` lateral join query with `case: VisibleCase = Depends(require_visible_case)`.
4. `server/api/reads/analysis.py:46`:
   - Replace inlined `standing_of` and `cases` query with `case: VisibleCase = Depends(require_visible_case)`.
5. Parameter validation in `server/api/deps.py`:
   - Add standard `CaseId` and `RunId` dependencies that catch unparseable UUIDs and raise `Refusal(RefusalCode.CASE_NOT_FOUND)` / `Refusal(RefusalCode.RUN_NOT_FOUND)` without triggering FastAPI 422 errors.

### Relevant Flowcharts & Specifications
- `PATHFINDER-2026-09-15/01-flowcharts/edge-api-gateway.md`
- `PATHFINDER-2026-09-15/01-flowcharts/case-run-management.md`
- `PATHFINDER-2026-09-15/01-flowcharts/deliverable-filing.md`

### Anti-Pattern Guards
- NEVER acquire a `FOR UPDATE` lock (`lock_case`) during a read endpoint.
- Unauthorized callers MUST receive 404 `CASE_NOT_FOUND` (never 403 or 401) to prevent enumeration of case IDs.
- Run `pytest tests/test_api_reads.py` and `pytest tests/test_edge.py` to confirm standing behavior.
```

---

## 5. Handoff: Frontend Governed Action Hook

```markdown
/make-plan Extract a unified React hook for governed command forms and offline intent retries

### Target Unified Component
- **Component:** `frontend/src/app/useGovernedAction.ts`
- **Single Entry Point:**
  ```ts
  export function useGovernedAction<TArgs, TReceipt>(
    action: (intent: Intent, args: TArgs) => Promise<CommandResult<TReceipt>>,
    onSuccess: () => Promise<void> | void
  ): {
    submit: (args: TArgs) => Promise<void>;
    pending: boolean;
    error: string | null;
    refused: RefusalCode | null;
    reset: () => void;
  };
  ```

### Exact Call Sites to Rewrite
1. `frontend/src/sections/directory/NewCase.tsx:64-108`:
   - Replace duplicate 45-line `lastSubmitted` intent state machine with `useGovernedAction(createCase, refetchDirectory)`.
2. `frontend/src/sections/upload/AdmitSources.tsx:71-109`:
   - Replace duplicate 45-line `lastSubmitted` intent state machine with `useGovernedAction(admitSources, refetchUpload)`.
3. `frontend/src/app/transport.ts`:
   - Add `refetchSection<D>(section: EnabledSection, query: SectionQuery): Promise<D | null>` to eliminate ad-hoc `fetch(sectionUrl)` in `NewCase.tsx:30` and `AdmitSources.tsx:27`.

### Relevant Flowcharts & Specifications
- `PATHFINDER-2026-09-15/01-flowcharts/frontend-workspace.md` (Governed Mutation Commands)
- `docs/IA_SPEC.md` §4 (Directory and Upload section contracts)

### Anti-Pattern Guards
- DO NOT introduce external state libraries (Zustand, Redux); use standard React hooks (`useState`, `useCallback`).
- The `Idempotency-Key` MUST be preserved on network offline failures (`kind: "offline"`) if the payload is unchanged, but rotated via `newIntent()` whenever input parameters change or after any server response.
- Run `npm --prefix frontend test` and `npm --prefix frontend run build` to verify type checking and tests.
```
