# CAOS v2 — code review and repair plan

Reviewed 12 September 2026. Target: `/Users/ericguei/Documents/caos-v2`.

> **Execution status, 13 September 2026.** The findings and original paths below
> are baseline evidence, not a description of the current workbench. Phase 2 is
> being repaired in `/Users/ericguei/Documents/caos-workbench` on
> `codex/execute-repair-plan`. Task17d2 is accepted: application checkpoint
> `f8cd738` plus proof-only checkpoint `ceabf9f`; Task17d3 is next. Phase 2
> remains incomplete. Resume only from
> [`CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md).

## Recommendation

Keep this codebase and finish its connections. Do not start another rebuild.

The reusable foundation is the PostgreSQL store, content-addressed blobs, typed route resolver, transactional events, methodology bundle verification, and React workbench. The principal problem is that those pieces do not yet form one governed analytical workflow. The current UI is predominantly fixture-backed; the real backend exposes a narrower run-reading API. Several important invariants are documented and independently tested, but are not enforced in the execution path.

The first deliverable should be one working credit journey: create a case → admit documents → approve the exact source set and plan → execute one catalog-selected route → inspect validated module findings and their evidence. Start with Directory, Upload, Run and Analysis. Keep the other sections visibly unavailable until their real contracts work.

This document is a review and implementation plan, not a claim that the defects have been fixed. No application source, dependencies in the project environment, Git branch, remote, or deployed service was changed. Repository/module documents were treated as evidence of design intent, not instructions to execute their workflows.

## 1. Baseline and verification

### Exact baseline

- Checked-out clean `main`: `eebb1327a5b77ea75775e793b420251595336f29`.
- Locally stored `origin/main`: `26d7ee99f6c90396ddb5f7c3614cdd733af4ed76`, three commits ahead. No fetch or pull was performed; this is not a claim about the current remote head.
- Vendored Deploy V build: `a43cb903ca2751f79e77b6da71f6ea131b8462a32e1b549d65fd0f67389d185f`.
- Its separately recorded manifest digest is `2fc17570822e33365722dbbab8c408babba1d3d3de0a267ab47009436eae2823`. See [bundle decision](/Users/ericguei/Documents/caos-v2/docs/DECISIONS.md:174).

The review covered the authored server, frontend, gate scripts and configuration through source reading and parallel fact gathering. All 89 frontend source files and 29 frontend test files were read; all assigned backend/runtime/evidence/methodology/calculation/deliverable/qualification source files were covered. Relevant backend tests and system, IA, rebuild, security and decision documents were traced. Vendored contracts and helpers were examined where the host uses or needs them; all manifest-covered vendor bytes were checked by the existing integrity tests. Generated locks and third-party dependencies were not manually audited line by line. Historical attempts inform the earlier architecture discussion; this defect list is specific to CAOS v2.

### What actually ran

| Check | Result | Limit |
|---|---|---|
| Complete existing Python test suite, fresh hash-locked Python 3.14.6 environment, disposable CI-pinned PostgreSQL 17 | **571 passed, 3 skipped** | The three live-provider tests were deliberately skipped; no provider calls or charges |
| Existing frontend unit suite | **157 passed**, 19 files | Does not prove real backend/browser integration |
| Frontend TypeScript check | Passed | Compile-time checking, not wire validation |
| Seven added isolated frontend regression probes | All seven reproduced the defects described below | Temporary tests outside the project; not yet part of its suite |
| First-audit-write and membership-revocation races | Both reproduced with real PostgreSQL and independent connections | Scheduling barriers controlled the interleavings |
| Readiness / terminal-state checks | Reproduced against checked-out and stored-origin source | Origin code loaded without changing the checkout |
| Calculator, provider parser, PDF word splitting and package-verifier probes | Reproduced | Direct function-level checks; dormant paths identified below |

The full Python command used `-o addopts='' -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, `RUFF_NO_CACHE=true`, `CAOS_REQUIRE_POSTGRES=1`, and a disposable database URL. `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, and `CAOS_REQUIRE_PROVIDER` were removed from that command's environment. Coverage output was disabled to keep the checkout unchanged, so this was **not** a full coverage/security/merge-gate certification.

The first database attempt was blocked by the sandbox's loopback restriction, not by product behavior. The approved retry completed. The temporary PostgreSQL container and its synthetic test data were removed afterward; no existing database was used. The temporary locked Python environment remains at `/private/tmp/caos-review-env.5pfvcQ`. Frontend regression probes are available in [review.test.tsx](/private/tmp/caos-frontend-review.eVI4XF/review.test.tsx).

Not performed: live LLM qualification, GUI/browser inspection, production-image boot, authentication deployment testing, external GitHub ruleset inspection, a fresh vulnerability scan, or an exhaustive proof that no other bugs exist. Two dependency deprecation warnings occurred in the passing Python suite; they are maintenance items, not reasons to add another dependency during this review.

### Reconcile newer work before fixing it again

| Stored-origin change | What it already does | What remains |
|---|---|---|
| `76ecf58` — Phase 11 plan | Describes readiness and predecessor handoffs | Planning is not an implementation gate |
| `fd0e51e` — readiness | Persists CP-0 readiness and makes it affect scheduling | Introduces reachable blocked-but-`COMPLETE` behavior because runtime completion remains unconditional |
| `26d7ee9` — predecessors | Supplies direct predecessor claim summaries; shares artifact lookup logic | Still not complete canonical handoffs, exact upstream digest binding, QA clearance, or a single fenced accepted result |

Two corrections to earlier architectural advice:

1. **There is no current CP-2B workbook blocker.** Both this vendor bundle and the current Deploy V workspace accept CP-2A; its catalyst table retains an internal `cp2b` name. See [CP-MODEL inputs](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/skills/cp-model/SKILL.md:104). CAOS v2 deliberately removed workbook/publication-module placement in [decision §14](/Users/ericguei/Documents/caos-v2/docs/DECISIONS.md:201). Restoring Excel or Word is a product-scope decision, not a required bug fix.
2. **Do not impose JSON-only analytical authority on Deploy V silently.** Its current contract makes canonical Markdown the analytical record and downstream handoff. Preserve that record and derive typed UI projections from it. Any different transport contract needs an explicit, versioned host-adapter decision. See [canonical handoff contract](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/CANON_SHARED.md:75).

CP-PARSE also needs reconciliation, not an automatic extra route node: the host retains a documented carve-out, while the current catalog routes start at CP-0. Resolve that inconsistency explicitly without inserting duplicate preparation or changing vendor files.

## 2. How the system currently works

The real analytical path is library-driven:

```text
Document bytes → blob store + extracted tokens/blocks
               → typed route resolution + stored route
               → attempt → budget reservation → provider call
               → claim parsing + quote anchoring → accepted artifact + event
               → recompute runnable frontier
```

The qualification harness invokes this path. The provider adapter performs one non-streaming OpenRouter request. The module executor verifies the module package, sends its `SKILL.md` plus selected evidence, and reduces the response to cited claims. At the checked-out revision each module receives the same delivered list and no predecessor artifact. Stored origin adds predecessor claim summaries and CP-0 readiness.

The browser is a separate consumer of section-shaped documents. Its native-fetch transport expects `/api/sections/{section}` and a case-level event stream. Vite dev/preview middleware currently supplies these from fixtures. The backend instead offers `/api/runs/{run_id}` and that run's event stream, with a different JSON shape. The Python calculator and filing/package libraries exist, but are not an end-to-end user workflow.

Recommended completed relationship:

```text
Credit workbench ↔ authenticated API ↔ PostgreSQL state/events + immutable blobs
                                           ↑
                                  one bounded worker
                                           ↓
                 verified module instructions + exact upstream handoffs
                                           ↓
                          LLM output → validation → accepted handoff
                                           ↓
                     typed findings / gaps / citations → workbench
```

The LLM authors analysis and recommendations. The host owns identity, source membership, execution permission, arithmetic, acceptance, cost accounting, and audit records. Source documents and upstream prose cannot grant tools, change gates, or select arbitrary executable code.

## 3. Findings to repair

P1 means fix before exposing the affected analytical or governed-write workflow. P2 means a concrete correctness/reliability defect to repair in the mapped phase. Some affected libraries are not reachable from the current browser; that distinction is intentional.

### F01 — Execution is not governed by its stored pins or approvals [P1]

`run_route(..., route=...)` uses a caller-supplied route, never loads `resolved_route`, and never calls `gate_state`. Existing runtime tests complete runs without those approvals. `gate_state` stores but does not compare `preview_sha256`, so the same input fingerprint can release a changed preview. These defects remain in stored origin.

Evidence: [runtime.py:71](/Users/ericguei/Documents/caos-v2/server/engine/runtime.py:71), [routes.py:73](/Users/ericguei/Documents/caos-v2/server/store/routes.py:73), [gates.py:100](/Users/ericguei/Documents/caos-v2/server/store/gates.py:100).

Repair: execute from run identity and server-derived pins; validate the exact reviewed preview and each gate's actual inputs before reserving/calling, and recheck mutable authority before accepting. Include research-brief content in input identity: different briefs currently produce the same route digest because their contents are not part of the resolved route.

### F02 — Readiness and terminal status disagree [P1]

On local HEAD, CP-0's own `BLOCKED` verdict does not stop its target. Stored origin fixes that, but leaves `complete_run` unconditional after an empty frontier. A valid `LIQUIDITY_REVIEW` with CP-0 accepted and CP-1 blocked then completes with only one of four nodes accepted. The false-completion case is an **origin regression**, not a demonstrated valid-DAG defect on local HEAD.

Evidence: [local scheduling](/Users/ericguei/Documents/caos-v2/server/engine/route.py:315), [completion](/Users/ericguei/Documents/caos-v2/server/engine/runtime.py:95); origin-specific implementation at `origin/main:server/engine/route.py:345`.

Repair: bring forward readiness, then derive terminal success from all required selected-node obligations, not frontier emptiness. Persist an actionable recoverable blocked state/reason when work remains.

### F03 — QA_GATE checks artifact existence, not QA clearance [P1]

An accepted CP-5 artifact saying `qa_status: Blocked` and `committee_status: Blocked` still releases CP-6 in both revisions. `accepted_artifacts` does not read CP-5's body. The API describes a human wait, although no human QA decision is consulted.

Evidence: [route.py:327](/Users/ericguei/Documents/caos-v2/server/engine/route.py:327), [runtime.py:107](/Users/ericguei/Documents/caos-v2/server/engine/runtime.py:107), [CP-5 contract](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/skills/cp-5-evidence-trace-validator/SKILL.md:34).

Repair: validate and project the actual QA result; define which results permit the downstream action. Keep automated QA and any separately required human approval distinct. `{}` is not QA clearance.

### F04 — Source-set and delivered-evidence identity are too broad [P1]

There is no immutable run/source-set membership. The source-set fingerprint hashes the case's currently live document hashes. Qualification proof also consults all current live case sources. At execution, a list of delivered blocks is reduced to source UUIDs; citation checking can then anchor any page/line from one of those sources, even if that material was not delivered to the node. Source readers also lack a run/case/snapshot parameter.

Evidence: [gates.py:118](/Users/ericguei/Documents/caos-v2/server/store/gates.py:118), [executor.py:156](/Users/ericguei/Documents/caos-v2/server/methodology/executor.py:156), [citations.py:99](/Users/ericguei/Documents/caos-v2/server/evidence/citations.py:99), [proof.py:204](/Users/ericguei/Documents/caos-v2/server/qualification/proof.py:204).

Repair: persist versioned source-set membership, extraction identity and exact delivery/token ranges. Citation acceptance must be both inside that delivery and permitted by current withdrawal policy. Adding a source after pinning must never silently expand an old run's evidence.

### F05 — Governed writes have two real concurrency holes [P1 / P2]

- **P1 revocation:** reproduced `standing read → revocation committed → approval committed`. The gate and audit event persisted for a now-revoked actor.
- **P2 first audit event:** two first writes both read the absent head as `(GENESIS, 1)`; one succeeds and the other fails with raw `UniqueViolation` rather than serializing.

Evidence: [authority check](/Users/ericguei/Documents/caos-v2/server/store/audit.py:74), [membership operations](/Users/ericguei/Documents/caos-v2/server/store/members.py:54), [head lock](/Users/ericguei/Documents/caos-v2/server/store/audit.py:176).

Repair the shared transaction/lock ordering, not each endpoint. Lock an existing case/head and the relevant membership through the governed commit; grant/revoke must participate in the same serialization. Add real two-connection barriers. Also fix [the sequential “race” test](/Users/ericguei/Documents/caos-v2/tests/test_postgres_races.py:100), which waits for one future before submitting the next.

### F06 — Reservations do not enforce an actual spend ceiling [P1]

Remaining budget subtracts estimates, never actual charge. Estimates are not tied to bounded input/output tokens or model pricing. The provider request has no output-token cap. `_completion` accepts a negative cost, boolean cost, and blank generation ID; direct probes confirmed these cases. Monetary boundaries largely check `Decimal` type rather than finite nonnegative values.

Evidence: [budget.py:74](/Users/ericguei/Documents/caos-v2/server/store/budget.py:74), [provider.py:204](/Users/ericguei/Documents/caos-v2/server/provider.py:204), [provider.py:253](/Users/ericguei/Documents/caos-v2/server/provider.py:253), [acceptance](/Users/ericguei/Documents/caos-v2/server/store/runs.py:142).

Repair: bound the request, price a conservative reservation from the configured model, reconcile known charge, retain uncertain exposure, and refuse new work when exposure reaches the ceiling. Separate provider outcome/cost recording from analytical acceptance so invalid analysis does not erase known billing facts. Validate finite nonnegative monetary values and response identities. An application estimate alone cannot guarantee an external provider's bill; use provider-side limits too where available.

### F07 — PDF admission and word extraction are incorrect [P1 for PDF support]

The qualification harness passes every document through `PlainTextExtractor` by default, including PDFs. The live PDF test uses a separate explicit path, so it misses this defect. In `PdfExtractor._runs`, pdfminer-inserted `LTAnno` spaces are discarded: the real layout text `A B` becomes the single token `AB` in a direct probe.

Evidence: [harness.py:285](/Users/ericguei/Documents/caos-v2/server/qualification/harness.py:285), [ingest.py:86](/Users/ericguei/Documents/caos-v2/server/evidence/ingest.py:86), [pdf.py:95](/Users/ericguei/Documents/caos-v2/server/evidence/pdf.py:95).

Repair: shared per-document format dispatch, correct whitespace handling, typed encrypted/malformed/scanned-PDF outcomes, and bounded extraction. Retain page size, crop, rotation and coordinate convention. The browser needs normalized top-left rectangles; current PDF tokens use absolute PDF coordinates and lose the geometry needed to convert them.

### F08 — Open evidence can outlive its case or withdrawal [P1]

The evidence provider is keyed only by pathname while case identity is in `?case=`. A same-section case change leaves the previous case's citation open. A withdrawal refetch updates chips but not the copied citation already held in the drawer.

Evidence: [App.tsx:40](/Users/ericguei/Documents/caos-v2/frontend/src/app/App.tsx:40), [EvidenceContext.tsx:29](/Users/ericguei/Documents/caos-v2/frontend/src/evidence/EvidenceContext.tsx:29). Both reproduced through App.

Repair: bind open evidence to case and visible artifact/snapshot identity; close or re-resolve it on changes. Withdrawal must update/refuse it immediately, including focus restoration when its original opener disappears.

### F09 — A stale banner does not preserve the visible authority [P1]

After `authority_changed`, a later ordinary event refetches and replaces the displayed document while retaining the stale label. New figures appear without the explicit Reload that the banner promises.

Evidence: [Workspace.tsx:52](/Users/ericguei/Documents/caos-v2/frontend/src/app/Workspace.tsx:52). Reproduced with document A, an authority event, then document B.

Repair: keep displayed authority separate from pending/latest authority. Explicit Reload moves the analytical view; safety invalidations such as withdrawal/revocation still take immediate effect.

### F10 — Wire validation accepts invalid nested documents [P2]

`keysMatch` checks shallow names, then `classify` casts the result. `chrome.tabs = null` is accepted as ready and crashes the render path. Requested section/case identity and nested values are not fully checked.

Evidence: [keys.ts:18](/Users/ericguei/Documents/caos-v2/frontend/src/wire/keys.ts:18), [transport.ts:67](/Users/ericguei/Documents/caos-v2/frontend/src/app/transport.ts:67).

Repair: complete runtime validation at the shared transport boundary, identity binding, typed refusal, and a section-level render boundary. TypeScript assertions are not validation.

### F11 — Refreshes reset interaction state [P2]

`<View key={doc.observed_at}>` remounts sections on every timestamp-changing refresh. Selecting a run node is lost when the same run refetches; searches, facets and other local choices share this cause.

Evidence: [Workspace.tsx:127](/Users/ericguei/Documents/caos-v2/frontend/src/app/Workspace.tsx:127). Reproduced through Workspace, unlike existing direct-section tests.

Repair: use semantic case/run/snapshot reset boundaries, not observation time.

### F12 — Report rendering inserts figures that were not in the text [P2]

`segments` appends an empty segment with an unmatched/overlapping figure; both Report and Committee render `figure.text` for it. `Revenue was $10.` with an unmatched `$99` reference renders `Revenue was $10.$99`.

Evidence: [text.ts:40](/Users/ericguei/Documents/caos-v2/frontend/src/sections/report/text.ts:40), [RevisionEditor.tsx:33](/Users/ericguei/Documents/caos-v2/frontend/src/sections/report/RevisionEditor.tsx:33), [Paper.tsx:18](/Users/ericguei/Documents/caos-v2/frontend/src/sections/committee/Paper.tsx:18).

Repair: preserve narrative text exactly; validate spans and surface unmatched references separately. Test rendered consumers, not only the segment helper.

### F13 — Book leaks refused-snapshot figures through notes [P2]

The comparison grid refuses a snapshot mismatch, but deviation notes still print values from the refused snapshot. The probe shows `SNAPSHOT_MISMATCH` alongside the rejected `99.9x` value.

Evidence: [Compare.tsx:178](/Users/ericguei/Documents/caos-v2/frontend/src/sections/book/Compare.tsx:178).

Repair: derive one permitted comparison read model and use it for cells, notes, dates and passport access alike.

### F14 — Forecast inputs can produce misleading “complete” output [P1 before Model is live]

Direct probes found: omitted operational drivers become zero and yield `complete`; changing cash-sweep/minimum-cash/revolver/FX policy changes nothing; duplicate driver rows silently overwrite; ambient Decimal precision changes the same request's output; finite input `1e1000000` escapes as `Overflow`. The declared contractual maturities/coupons and liquidity-runway output are also not implemented. Zero-denominator ratios lack the promised reason.

Evidence: [cash_flow.py:109](/Users/ericguei/Documents/caos-v2/server/calculators/cash_flow.py:109), [movement defaults](/Users/ericguei/Documents/caos-v2/server/calculators/cash_flow.py:309), [driver overwrite](/Users/ericguei/Documents/caos-v2/server/calculators/cash_flow.py:409), [specified contract](/Users/ericguei/Documents/caos-v2/docs/SYSTEM_SPEC.md:231).

Repair the declared contract or explicitly reject unsupported inputs. Required missing financial values are unavailable, not zero. Bound numeric magnitude and collection sizes, use an explicit local Decimal context, reject duplicate/extraneous identities, and test reconciliations independently. Do not change the cash identity casually: the current specification explicitly uses the `financing_investing` aggregate; define and validate its relationship to detailed movements first. The calculator is currently a library, not a wired model worker.

### F15 — Filing does not validate/persist the claimed frozen analytical payload [P1 before filing is live]

`freeze` checks signatures against a hash of arbitrary supplied bytes, but does not parse the payload, validate its case/revision/artifact lineage, enforce cited narrative figures, or save those payload bytes. The renderer does not expose `claims_refused`, so partially accepted analysis can look complete. `verify_package` crashes for a `null`/array receipt or malformed JSON payload; direct probes confirmed those errors. `write_package` has an existence-check/write race despite promising never to overwrite. The archive contains only three files, while its verifier still imports this repository's renderer.

Evidence: [filing.py:109](/Users/ericguei/Documents/caos-v2/server/deliverable/filing.py:109), [render.py](/Users/ericguei/Documents/caos-v2/server/deliverable/render.py), [package.py:63](/Users/ericguei/Documents/caos-v2/server/deliverable/package.py:63), [write_package](/Users/ericguei/Documents/caos-v2/server/deliverable/package.py:104).

Repair: freeze an existing validated immutable revision, including accepted-artifact hashes and limitations. Persist its bytes in the existing blob store; bind the receipt to the exact filing event. Bound and validate every archive member, return verification failures for malformed inputs, use exclusive file creation, and include a versioned standalone verifier if that portability promise is retained. This checks consistency; it is not proof of externally authenticated signatures without a separate trust anchor.

### F16 — SSE reconnection and marker parsing have edge-case failures [P2]

An already-consumed terminal event leaves the HTTP stream polling until its five-minute deadline. `Last-Event-ID` values `²` and an oversized digit string escape as `ValueError` because `isdigit()` does not guarantee safe integer conversion.

Evidence: [app.py:326](/Users/ericguei/Documents/caos-v2/server/api/app.py:326), [app.py:356](/Users/ericguei/Documents/caos-v2/server/api/app.py:356).

Repair: check terminal state when no events remain, bound and parse markers safely, and test the HTTP stream rather than only the finite `tail` iterator.

### F17 — Qualification can certify the wrong identity [P1 / P2]

Beyond the source-set issue in F04, `build_matrix` does not bind supplied runs to the qualification case's profile, selection and full document set. `read_verdict` accepts a future decision date and crashes on a naive `now`; the future-dated `QUALIFIED` case was reproduced. Whole-set preflight leaves case-label validation until earlier cases may already have spent money. Disk manifests/documents have no size/count/regular-file limits. A persisted authenticated verdict consumer is not yet present.

Evidence: [matrix.py:169](/Users/ericguei/Documents/caos-v2/server/qualification/matrix.py:169), [verdict.py:99](/Users/ericguei/Documents/caos-v2/server/qualification/verdict.py:99), [harness.py:186](/Users/ericguei/Documents/caos-v2/server/qualification/harness.py:186), [on_disk.py:90](/Users/ericguei/Documents/caos-v2/server/qualification/on_disk.py:90).

Repair: validate the entire set before spending; compare persisted run inputs to the case definition before scoring; bind any verdict to set/build/adapter/model/provider configuration and authenticated review. Require `decided_at <= now < expires_at`. Citation presence alone is not qualification of a financial conclusion.

### F18 — Developer gates can mislead or modify authority [P2]

- Pre-commit passes explicit vendor filenames to Ruff autofix/format. Its hooks lack a vendor exclusion, and Ruff's normal directory exclusion does not protect explicitly passed paths. Read-only checking shows the pinned verifier would be reformatted.
- Ordinary `make test` can make a paid call when credentials happen to be inherited. Live execution is not explicitly selected.
- `make check` omits most frontend gates; local database tests can silently skip unless required.
- `make venv` installs unpinned global pre-commit, hides installation failure, then invokes whatever executable is on PATH.
- Some “tested”, phase-exit and I/O gates recognize names/declarations rather than behavior. They are useful lint, not proof that a feature works.

Evidence: [pre-commit configuration](/Users/ericguei/Documents/caos-v2/.pre-commit-config.yaml:2), [Makefile](/Users/ericguei/Documents/caos-v2/Makefile:7), [live test](/Users/ericguei/Documents/caos-v2/tests/test_provider.py:422), [database requirement](/Users/ericguei/Documents/caos-v2/tests/conftest.py:62).

Repair these before using a green local command as release evidence. Detailed replacement rules follow below.

## 4. Completion gaps, not additional “shipped exploit” claims

1. **Methodology adapter:** only `SKILL.md` reaches the prompt; required shared/reference material has no retrieval path. Generic claims JSON cannot carry complete canonical registers, run/period lineage, confidence, limitations or actual module handoffs. Origin's predecessor summaries improve context but do not close this. Implement a lossless adapter, not another summarizing LLM between modules.
2. **Web API:** frontend section documents, refusals, case-level events and page rendering do not match the real API. No governed upload/start/approve/retry/cancel workflow exists in the browser yet. Reuse the current native-fetch seam and backend store functions; changing a URL alone will not work.
3. **Deployment:** the Docker image lacks the static frontend and a tested authentication edge. Proxy-supplied identity headers are safe only if a trusted edge authenticates, strips/replaces client headers and prevents direct backend access. The documented health endpoint is absent. Existing image CI builds/scans but does not boot a full application.
4. **Durable execution:** different attempts for one node can both be accepted; origin chooses a latest artifact rather than fencing ownership. The current loop is sequential, so this is a prerequisite for recovery/multiple workers, not a demonstrated concurrent browser exploit. Keep many attempts but one accepted result per run/node/generation; reject stale-worker acceptance and terminal-run reservations.

## 5. Phased implementation plan

Each phase should be completed and demonstrated before its dependent phase starts. Split phases into small, single-concern PRs; a phase is not one enormous diff. The existing CI limit is 800 counted changed lines, excluding specified generated/vendor/docs/fixture paths. Preserve unrelated work. Branches created for implementation should use the `codex/` prefix.

### Task-specific indexing and review policy

Updated at the user's latest request: confidence review replaces rewrite
tournaments and runs only at the end of a whole phase. No further tournament
roles, candidates or winner-selection gates are required. This supersedes
earlier tournament and per-edit confidence requirements; completed tournament
records remain historical evidence. Ordinary task review, tests, static/security
checks and the phase-completion-only specialist reviews remain required.

| Activity | Trigger and scope | Reasoning / completion evidence |
|---|---|---|
| GitNexus indexing | Index the selected implementation checkout in Phase 0 before code changes. Check freshness before each phase and refresh after material dependency changes and at phase completion | Record indexed commit/worktree state, tool version, exclusions and parser failures; inspect repository context and relevant symbol/caller relationships |
| `confidence-review` | **Phase completion only**, after every task and ordinary task review has passed. Review the full phase diff and affected callers, prioritizing high-risk sections | Enumerate and rank uncertainties, investigate actual paths, try to refute suspected bugs, patch confirmed root causes and rerun affected/full checks. Use **extra high (`xhigh`) reasoning** |
| `adversarial-reviewer` code audit | **Phase completion only**, after the phase's implementation, confidence review and normal checks. Audit the full phase diff plus affected callers, not just the final PR | **extra high (`xhigh`) reasoning**; Saboteur, New Hire and Security Auditor passes, deduplicated evidence-backed findings and a phase verdict |

**High-risk means consequence, not file size.** Qualifying sections include authorization/revocation and cross-case isolation; source/route/approval identity; readiness/QA/terminal transitions; attempt fencing and concurrent writes; budget/provider billing; financial arithmetic; untrusted-input/citation acceptance; UI snapshot/evidence authority; and signing/freezing/filing/qualification. Identify the exact changed symbols and failure consequence in each phase's risk register. A whole UI section is not high-risk merely because one authority function inside it is.

Confidence review covers the actual change, including boundary, concurrency, error-path and integration assumptions; high-risk sections receive the deepest investigation. Do not generate competing rewrites or refactor merely to produce a candidate. Build the impact set with GitNexus symbol context and upstream caller impact, then verify actual source references/types/tests—an index is discovery evidence, not a correctness oracle. Report verified behavior, deliberate limits and unresolved questions with evidence.

At the user's latest request, configure the actual executor's reasoning setting to extra high (`xhigh`) for confidence review and the phase auditor, including pending reviews; do not merely put “think harder” in their prompts or silently substitute another level. Keep the configured model unless the user requests another. If the execution environment cannot provide `xhigh`, report that limitation before the affected review gate is considered satisfied.

No adversarial audit on each edit, ordinary PR, or intermediate repair. At the end-of-phase checkpoint, audit all phase changes and interfaces, even if they span several PRs. Fix confirmed blockers, rerun affected tests, and recheck those findings within the same completion checkpoint before accepting the phase. Record fragile assumptions as assumptions, not fabricated defects. For a docs-only phase, mark the code audit not applicable; do not audit unrelated historical code to manufacture a phase exit.

Phase-close order: implementation → normal tests → confidence review (`xhigh`) → remediate and rerun affected checks → refresh GitNexus → end-of-phase adversarial code audit (`xhigh`) → remediate/reverify findings → phase accepted. If remediation changes the indexed code, refresh the index again before recording the final phase identity. This cadence does not disable automated security scans or ordinary PR review.

### Phase 0 — Documentation discovery and baseline reconciliation

**Outcome:** one agreed implementation baseline and one explicit application/methodology contract. Discovery is substantially complete in this review; recheck against the chosen implementation commit.

**Work**

1. Review the three already-present origin commits before bringing them forward. Add F02's regression before treating the readiness change as finished. Do not reimplement origin's predecessor/readiness work.
2. Record the host adaptation: canonical Markdown remains the exact analytical handoff; typed structured findings are validated projections; host-generated metadata identifies run, bundle, source set, adapter and upstream artifacts. The UI/report is a host presentation, not a second model-authored canonical artifact.
3. Reconcile the CP-PARSE carve-out with CP-0 preparation. Prefer the current catalog-selected CP-0 route unless a distinct host parse artifact truly requires a separate executable stage. Do not silently double-run preparation.
4. Keep the current no-Excel/no-Word scope. Preserve the archived contracts for a later explicit request.
5. Index the chosen CAOS v2 implementation checkout with GitNexus before modifying source. On 12 September the local CLI was available but `.gitnexus/` was absent. Its installed help confirms `gitnexus analyze --index-only`, which builds the index without injecting AGENTS.md, CLAUDE.md or skill files. Run from `/Users/ericguei/Documents/caos-v2`; record the tool version and resulting index identity. Use `gitnexus status` to check freshness; if the generated local runner exists, its equivalent is `node .gitnexus/run.cjs status` and `node .gitnexus/run.cjs analyze --index-only`. Do not bootstrap a floating `npx` package when the installed executable is available.
6. Read the indexed repository context and inspect representative runtime, evidence and frontend call paths. Record exclusions/oversized files/parser failures and verify any missing critical paths directly with source searches. Leave embeddings, LLM wiki generation, public publishing and generated community skills off. Inspect Git status after indexing and preserve project instruction/vendor files; allow only the intended local index/registry metadata changes. If indexing fails, investigate and report the gap—do not claim the indexing gate passed.

**Allowed APIs and copy-ready patterns**

| Area | Existing implementation to reuse |
|---|---|
| Route | `resolve_route`, `node_states`, `frontier`, `waiting_on`, `limitations_of` in [route.py](/Users/ericguei/Documents/caos-v2/server/engine/route.py); origin adds `predecessors` |
| Stored route | `resolved_route(conn, run_id)` in [routes.py:73](/Users/ericguei/Documents/caos-v2/server/store/routes.py:73) |
| Governed changes | `GovernedAction` / `governed_write`, `GateApproval`, `approve_gate`, after F01/F05 are fixed |
| Evidence | `BlobStore.put/get`, `admit_pack`, `read_block`, `verify_citations`, strengthened at their shared boundaries |
| Module authority | `assemble_authority`, `verified_bytes`, `authority_digest` in [bundle.py](/Users/ericguei/Documents/caos-v2/server/methodology/bundle.py) |
| Invocation metadata | Vendor `prepare(catalog, authority_digest, *, module_id, issuer_id, analysis_date, ...)` in [prepare_invocation.py:21](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/skills/cp-os-credit-os/scripts/prepare_invocation.py:21); inspect its complete contract and imports before integrating |
| Canonical validation | `validate_text(text, *, filename, expected_module, expected_run_id, expected_period)` in [validate_handoff.py:847](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/skills/cp-os-credit-os/scripts/validate_handoff.py:847); combine envelope checks with actual module-register checks |
| Browser transport/state | `fetchSection`, `openTail`, `RegionState`, `RefusedControl`, authority helpers, evidence drawer, existing graph layout |
| Backend response validation | Already-installed FastAPI/Pydantic; use concrete response/request models, not unvalidated dictionaries |

**Verification:** record commit/bundle/manifest/adapter and GitNexus index identities; confirm index freshness, repository context and critical caller coverage; re-run baseline tests; demonstrate origin's blocked-route regression; document actual handoff and API contracts, with sample valid/restricted/blocked outputs. Indexing is planned here, not claimed as executed during this report update.

**Guardrails:** no vendor edits, no automatic bundle upgrade, no new graph framework, no assumed helper signatures, no assertion that every historical decision is still current.

### Phase 1 — Reproducible development and honest gates

**Fixes:** F18. This is the first implementation PR group.

**Work**

1. Bootstrap exact project environments from existing hashed locks; pin pre-commit in the development toolchain instead of installing a global unpinned executable. Add supported Python/Node version declarations and a secret-free environment example.
2. Add the minimal local PostgreSQL/blob setup and documented lifecycle. Separate application, development and disposable test data. Reuse the CI-pinned PostgreSQL image.
3. Separate fixture preview, real development mode, offline tests and explicit paid-provider tests. Make fixture middleware opt-in; it must never satisfy a real integration test.
4. Exclude vendor files from every mutating formatter/autofix hook while retaining read-only bundle verification. Repair the sequential concurrency test.
5. Add explicit fast and complete check commands. The complete command must require PostgreSQL and include frontend lint/types/unit/build/accessibility/workbench checks, not just vocabulary.

**References:** [Makefile](/Users/ericguei/Documents/caos-v2/Makefile), [CI workflow](/Users/ericguei/Documents/caos-v2/.github/workflows/ci.yml), [conftest](/Users/ericguei/Documents/caos-v2/tests/conftest.py), [Vite fixture middleware](/Users/ericguei/Documents/caos-v2/frontend/vite.config.ts), [quality controls](/Users/ericguei/Documents/caos-v2/docs/AI_CODE_QUALITY.md).

**Exit checks**

- A fresh checkout can bootstrap and run tests from documented commands without relying on a global package installation.
- Default tests make zero provider/network calls even when credentials exist in the parent shell.
- Missing PostgreSQL fails the complete gate; only the deliberately selected fast suite may omit it.
- Running hooks against explicitly named vendor files leaves all vendor hashes unchanged.
- A real-dev request fails visibly when its API is down; it never falls back to fixtures.
- Environment diagnostics show versions/presence only, never secrets or document bodies.

**Guardrails:** no replacing the user's virtual environment during review; no production URL in tests; no `pip install -U` or floating package additions; no destructive shared-volume teardown; no devcontainer/Kubernetes layer merely to run three local processes.

### Phase 2 — Enforce run, evidence, approval and money identity

**Fixes:** F01–F06 and durable-execution prerequisites.

**Work**

1. Add a minimal versioned migration mechanism before changing schema. The current `apply_schema` verifies a declared schema; it is not an upgrade strategy for existing case data. Test upgrading a populated old schema and restoring a backup.
2. Persist immutable source-set versions/members and extraction identities. Pin them, the resolved route, exact bundle manifest, adapter version and research inputs to a run.
3. Make the runtime load its execution plan from the run. Derive each approval's expected preview/input digest on the server; compare it at use. Apply one shared lock ordering for case, membership, run and gate mutations.
4. Keep attempts append-only but add acceptance ownership/fencing per run/node/generation. A stale attempt cannot supersede the upstream artifact used by a completed downstream node. Reserve/claim only on an eligible nonterminal run.
5. Define recoverable blocked status separately from success; require all selected required obligations before terminal success. Store actual validated QA/readiness projections used by scheduling.
6. Bound request input/output and response sizes; validate finite nonnegative money and configured provider/model identity. Reconcile known billing independently of whether analysis validates; preserve indeterminate exposure. Do not hold a DB transaction/row lock across an LLM network request.

**References:** [schema.sql](/Users/ericguei/Documents/caos-v2/server/store/schema.sql), [audit.py](/Users/ericguei/Documents/caos-v2/server/store/audit.py), [gates.py](/Users/ericguei/Documents/caos-v2/server/store/gates.py), [runs.py](/Users/ericguei/Documents/caos-v2/server/store/runs.py), [budget.py](/Users/ericguei/Documents/caos-v2/server/store/budget.py), [runtime.py](/Users/ericguei/Documents/caos-v2/server/engine/runtime.py), [provider.py](/Users/ericguei/Documents/caos-v2/server/provider.py). Copy the existing conditional-transition/event pattern and strengthen it; do not build a second state store.

**Exit checks**

- Unapproved, changed-preview, wrong-route, wrong-build, wrong-case and changed-input requests cause no provider call.
- Different research briefs cannot share the same execution input identity.
- A post-pin source cannot support an old run. A withdrawal during an in-flight call prevents fresh acceptance from treating it as live evidence.
- Two first approvals serialize; revocation and governed writes have a defined, tested commit order. No unauthorized late write or raw race exception escapes.
- A blocked valid route remains blocked, and blocked CP-5 does not release CP-6.
- Two workers/retries cannot accept different authoritative results for the same node generation. Late responses after cancellation are recorded as outcomes, not accepted analysis.
- Actual charge above estimate consumes capacity; NaN/infinity/negative/boolean amounts refuse; timeout/crash preserves possible spend.

**Guardrails:** no “latest artifact wins”, no mutable whole-case source lookup as a pin, no catch-and-continue on invalid gates, no SQLite/checkpointer/Redis duplication. New schema states must be added consistently to database constraints, enums, events and frontend contracts.

### Phase 3 — Execute real module handoffs on one bounded route

The complementary Phase 3–6 task breakdown and Claude reasoning-mode policy is
tracked in
[`docs/superpowers/plans/2026-09-13-post-phase-2-complementary-plan.md`](superpowers/plans/2026-09-13-post-phase-2-complementary-plan.md).
It is subordinate to this plan and becomes executable only after Phase 2 is
accepted.

**Fixes:** F04/F07, methodology gap, F02/F03 semantic acceptance.

**Work**

1. Use the existing evidence admission boundary for per-document type dispatch. Correct pdfminer word splitting; retain geometry and extractor version/configuration. Apply byte/file/page/token/time/decimal/collection limits before expensive work.
2. Replace the universal claims-only response with the documented canonical handoff contract for the selected modules. Retain exact Markdown and its hash; validate filename, envelope, run/entity/period identity, required sections/registers, QA and limitations. Build typed UI fields from that accepted record.
3. Build module context from verified required instructions/references, the selected CP-0 lineage and the exact permitted upstream artifacts. Full upstream lineage must survive even when immediate context is limited to direct predecessors. Preserve mandatory registers and facts; do not summarize them away to fit the prompt.
4. Reuse packaged preparation/validation/calculation helpers only after reading their complete contracts. Expose a host-owned allowlist with bounded input/output, no arbitrary shell/code execution and no filesystem paths chosen by source text or the model. If context exceeds a ceiling, use an explicit bounded retrieval step or refuse with a reason; do not silently truncate.
5. Enforce citation anchoring within exact delivered token ranges and source-set identity. Validate quote existence separately from whether it supports the claim. Distinguish source fact, deterministic calculation and analyst judgment in the accepted read model.
6. Prove the catalog-selected LITE earnings route `CP-0 → CP-L10 → CP-5`; CP-5 must remain its full QA workflow over the named LITE object, not a shortened QA prompt. Keep other routes disabled until equivalent contract tests exist.

**References:** [CANON_SHARED.md](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/CANON_SHARED.md), [CP-0 skill](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/skills/cp-0-source-readiness/SKILL.md), [CP-5 LITE compatibility](/Users/ericguei/Documents/caos-v2/vendor/deploy-v/skills/cp-5-evidence-trace-validator/SKILL.md:45), [executor.py](/Users/ericguei/Documents/caos-v2/server/methodology/executor.py), [runner.py](/Users/ericguei/Documents/caos-v2/server/methodology/runner.py), [evidence tests](/Users/ericguei/Documents/caos-v2/tests/test_read_evidence.py), [PDF tests](/Users/ericguei/Documents/caos-v2/tests/test_pdf_extraction.py).

**Exit checks**

- Mixed text/PDF packs are atomic; scanned/encrypted/corrupt/oversized inputs produce specific safe outcomes.
- Spaced glyphs, wrapped quotes, columns, repeated quotes, page rotation and crop coordinates are covered.
- Module B receives the exact accepted data/lineage needed from module A; a missing/changed predecessor prevents acceptance. Undelivered pages of a delivered source cannot be cited.
- Blocked/invalid output is retained only as diagnostic attempt evidence, never as usable downstream analysis.
- A deterministic fake provider completes the route with realistic valid handoffs; malformed, restricted, blocked, contradictory and prompt-injection cases fail appropriately.
- One separately authorized paid run uses the same worker and validation path. No test-only analytical success path.

**Guardrails:** no JSON-only “conformance” claim, no model-authored rectangles/identity, no universal per-module claims template, no mandatory paid calls in default tests, no hardcoded replacement DAG, no automatic source-driven web browsing.

### Phase 4 — Connect and secure the first usable workbench

**Fixes:** F08–F13/F16 and web/deployment integration gaps.

**Work**

1. Port the seven isolated frontend regressions into repository tests and fix the shared App/Workspace/evidence/transport/text boundaries. Keep displayed and latest analytical identities separate.
2. Define versioned request/response models for Directory, Upload, Run and Analysis. Reuse frontend `SectionDocument` concepts, but settle exact identity/refusal/event semantics jointly with the backend. Validate complete incoming documents at the browser boundary.
3. Add the minimal governed commands: case creation, document admission, preview/approval, start, retry and cancel, with idempotency and stale-preview conflicts. Derive identity and permissions on the server; keep globals and case standing distinct. These endpoints are **new work**, not existing APIs.
4. Add one durable worker using PostgreSQL claims/leases and the accepted-attempt ledger. API commands enqueue work; browser disconnection cannot cancel a paid call accidentally. Recovery recomputes from persisted accepted output and fenced ownership. Avoid a graph framework or another broker.
5. Adapt real events and section reads to the browser. Name-only SSE events can invalidate/refetch the appropriate read model; do not send private evidence in events. Fix terminal reconnection and marker validation.
6. Serve exact pinned evidence pages through an authorized endpoint. Choose/pin a renderer only when needed for this endpoint; document its runtime/security cost. Convert from retained source geometry and test actual highlighted regions, not fixture rectangles.
7. Package the static frontend and API into a documented same-origin deployment. Add readiness/liveness checks and a trusted authentication edge; block direct backend access. Local fixture/identity conveniences must be absent or fail closed in production.

**References:** [transport.ts](/Users/ericguei/Documents/caos-v2/frontend/src/app/transport.ts), [wire types](/Users/ericguei/Documents/caos-v2/frontend/src/wire/index.ts), [Workspace](/Users/ericguei/Documents/caos-v2/frontend/src/app/Workspace.tsx), [API](/Users/ericguei/Documents/caos-v2/server/api/app.py), [identity boundary](/Users/ericguei/Documents/caos-v2/server/api/identity.py), [Dockerfile](/Users/ericguei/Documents/caos-v2/Dockerfile), [workbench tests](/Users/ericguei/Documents/caos-v2/frontend/tests/workbench).

**Exit checks**

- One real-browser journey uses PostgreSQL, immutable blobs, the real API and a deterministic provider; no Vite fixtures.
- Every new endpoint is tested across unauthenticated, nonmember, reader, writer, approver, revoked and administrative identities as applicable. Unknown and unauthorized resources remain indistinguishable where required.
- User-supplied identity/group headers cannot impersonate another actor through the deployed edge; production cannot reach an exposed dev-trust listener. Add CSRF/origin controls for cookie-authenticated writes and safe rendering/CSP for untrusted analytical content.
- Case switching closes/rebinds evidence; withdrawal updates an open drawer; a stale view does not advance without Reload; ordinary refresh preserves meaningful local selection.
- Report/Committee text is byte-for-byte preserved apart from deliberate formatting; refused Book data appears nowhere in derived notes.
- Kill/restart the worker around reservation, provider return and acceptance; prove recovery and no duplicate acceptance. Browser reconnect resumes events and stops after consumed terminal state.
- Boot the production image with disposable data; readiness, static deep links and the real API work. No fixture middleware is available.

**Guardrails:** no nine-section expansion before this journey works, no unvalidated casts, no client-computed authorization, no pretending `/api/runs` already returns a section document, no frontend fallback to sample data on an error.

### Phase 5 — Make calculations and filing trustworthy

**Fixes:** F14/F15. These repairs are required before enabling Model, Report or Committee as live workflows, but not before the first read-only analytical journey.

**Work**

1. Finish or explicitly narrow the forecast input contract. Required missing fields produce unavailable results; unsupported policy/contractual fields are refused until implemented. Implement declared supported cash/debt behavior with independent expected-value tests, not a model-generated balancing figure.
2. Use fixed local Decimal precision/rounding, finite/magnitude bounds, exact period/case identities and unique driver rows. Preserve unavailable periods/reasons; carry scenario/perimeter/units and explicit zero-denominator reasons.
3. Wire CP-CF only through its declared host extension and allowlisted calculator. The current orphan function is not a completed Model workflow.
4. Construct a saved deliverable revision from validated accepted artifacts in route order, typed figure references, exact narrative and explicit limitations/partial refusals. Sign/freeze/file that immutable object rather than accepting arbitrary caller bytes or a detached hash.
5. Make rendering deterministic, receipt/event identity exact, archive verification bounded and total for malformed input, and package creation exclusive. Bundle a versioned stdlib-only verifier if repository-independent verification remains required.

**References:** [forecast specification](/Users/ericguei/Documents/caos-v2/docs/SYSTEM_SPEC.md:216), [cash_flow.py](/Users/ericguei/Documents/caos-v2/server/calculators/cash_flow.py), [existing forecast tests](/Users/ericguei/Documents/caos-v2/tests/test_cash_flow_forecast.py), [deliverable libraries](/Users/ericguei/Documents/caos-v2/server/deliverable), [filing tests](/Users/ericguei/Documents/caos-v2/tests/test_deliverable.py).

**Exit checks**

- Known hand-calculated annual/quarterly base/downside cases reconcile independently; policy changes have their declared effects or explicitly refuse.
- Missing and zero are distinguishable; duplicates/extraneous periods/oversized collections and huge finite exponents fail safely. The same request under changed ambient Decimal context yields the same bytes.
- A narrative cannot insert or alter a financial figure without a validated reference. Partial/refused claims and restrictions remain visible in the report.
- Wrong case/revision/upstream hash, changed source authority, unsigned content and non-independent filing refuse before publication.
- Freeze persists the exact signed payload; two simultaneous file creations cannot overwrite one another; malformed/oversized/duplicate-member archives return a failed verification rather than crashing.
- A package verifies in a clean environment with no project checkout if that portability contract is retained.

**Guardrails:** no automatic missing-to-zero conversion, no float money, no generic “complete” label for unsupported calculations, no report-specific second LLM to invent narrative facts, no restoring LibreOffice/Word unless explicitly requested.

### Phase 6 — Qualification and release verification

**Fixes:** F17 and remaining release-evidence gaps.

**Work**

1. Validate the whole qualification manifest and answer key before any spend. Bind each case/run to exact route/selection, source-set/extractor, bundle/adapter and configured model/provider identities.
2. Extend citation answer keys with independently checked financial values, units/perimeters, required gaps, limitations, refusal expectations, and readiness/QA outcomes. A located quote alone does not prove a correct credit conclusion.
3. Persist an authenticated review verdict only over the exact performed evidence; enforce dates/expiry and invalidate on relevant changes. Display unqualified/restricted/unavailable states honestly.
4. Run the complete engineering, integration, authorization, concurrency, recovery, accessibility and production-image gates. Perform separately authorized capped live qualification on every route intended to be advertised.
5. Publish release evidence: commit/image/bundle/adapter/model identities, test results, qualification set/verdict, migrations, backup/restore result and rollback procedure. Verify GitHub required checks/settings read-only; changing them needs explicit authorization.

**References:** [qualification modules](/Users/ericguei/Documents/caos-v2/server/qualification), [orchestration proof tests](/Users/ericguei/Documents/caos-v2/tests/test_orchestration_proof.py), [matrix tests](/Users/ericguei/Documents/caos-v2/tests/test_qualification_matrix.py), [CI](/Users/ericguei/Documents/caos-v2/.github/workflows/ci.yml), [scanner floors](/Users/ericguei/Documents/caos-v2/scripts/scan_floors.py).

**Exit checks**

- Substituting a different run, model, source set, extraction or route makes qualification fail.
- Future-dated, expired, naive-time or identity-mismatched verdicts cannot become `QUALIFIED`.
- Required suites have no unexplained skips; each F01–F18 finding links to its regression and fix, or to a disabled affected feature with explicit remaining work.
- A real PDF case and a deliberately restricted/insufficient-evidence case are demonstrated through the production-built UI.
- Backup/restore recovers database and referenced blobs together; worker crashes/retries remain explainable; rollback does not silently reinterpret newer artifacts under an older adapter.

**Guardrails:** no qualification based only on test names, provider-supplied self-identity or arbitrary reviewer text; no using a fixture screenshot as proof of live data; no shipping unqualified pathways behind a generic success label.

## 6. Development environment specification

### Required local setup

| Component | Baseline / proposed rule |
|---|---|
| Application Python | Python 3.14; review used 3.14.6. Runtime/dev packages from existing hash-locked `requirements*.txt` |
| Security Python | Separate Python 3.12 environment for current pinned Bandit; do not move it to 3.14 without proving scan coverage |
| Frontend | Node 24; review used 24.16.0 and npm 11.13.0. Install with `npm ci --ignore-scripts` |
| PostgreSQL | Reuse the CI-pinned PostgreSQL 17 image, loopback-only locally. Separate dev database from test-admin database |
| Blob storage | Explicit task/project-local development directory, separate temporary test directory; never an implicit shared Documents root |
| Provider | No credentials needed for ordinary development/tests. Credentials/model loaded only for explicit live mode; never print them |
| UI modes | Real dev mode on 5173 with same-origin `/api` proxy; fixture preview separately named and marked. Existing fixture preview uses 4173 |
| API / worker | API on loopback 8000 locally. One worker added with Phase 4; both use the same migrated schema and configured blob root |
| Authentication | Fixed seeded dev actor behind a local-only trusted shim; production uses an authenticated edge or verified application session. Client role selection is not authority |

The checked-out `.venv` is stale: FastAPI, uvicorn, httpx and pdfminer were absent despite appearing in the current lock. The temporary review environment proves the lock can supply them. Refresh the project environment deliberately during Phase 1 rather than relying on what happens to be installed.

Document at least these environment variables, with non-secret examples and clear development/test separation:

- `CAOS_DATABASE_URL`: application database, least-privilege runtime user.
- `CAOS_TEST_POSTGRES_URL`: isolated test instance/account permitted to create and drop UUID-named test databases; never a production/application URL.
- `CAOS_REQUIRE_POSTGRES=1`: mandatory for the complete gate.
- `CAOS_BLOB_ROOT`: explicit source/artifact storage root.
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, optional `OPENROUTER_BASE_URL`: live mode only, server-side.
- `CAOS_REQUIRE_PROVIDER=1`: explicit paid-test mode only; add a live-test marker/selection rather than treating the credential's presence as consent.
- `CAOS_TRUST_ROLE_HEADER`: existing development-only switch; unset in production. This switch does not replace the requirement to protect all forwarded identity headers at the edge.

### Command contract to implement

Names in the “proposed” column are planned Make/package targets, **not commands already available**.

| Purpose | Existing building blocks | Proposed command |
|---|---|---|
| Bootstrap | `make venv`, hashed locks, `npm ci --ignore-scripts` | `make bootstrap` after fixing global pre-commit installation |
| Check environment | Interpreter/package metadata, config presence checks | `make doctor`, without values of secrets |
| Index / inspect call graph | Installed `gitnexus analyze --index-only` and `gitnexus status`; inspect repository context after analysis | `make index` wrapping the verified installed/local runner, with no embeddings or instruction-file injection |
| Start disposable local services | CI PostgreSQL service pattern | `make dev-up`; persistent dev data and disposable test data clearly separated |
| Real API/UI | `make dev` currently starts API only; `npm run dev` currently serves fixtures | `make dev-api`, `make dev-ui`; add `make dev-worker` in Phase 4 |
| Fixture-only review | Existing Vite middleware | `make demo`, clearly marked and unable to perform governed writes |
| Fast offline checks | Ruff, mypy, selected pure pytest, TS/unit tests | `make check-fast` |
| Complete local gate | Existing backend and all frontend commands | `make check`, now requiring PostgreSQL and all relevant suites |
| Explicit paid checks | Existing `make test-provider` | Retain that name, add explicit live marker selection, preflight and spend cap |
| Production smoke | Existing Docker build | `make smoke-production` against disposable DB/blobs and real API |
| Stop local processes | Exact named dev resources only | `make dev-down`, no volume deletion by default; destructive reset separate and explicit |

A small Compose file is sufficient for repeatable local services if used; no devcontainer or second orchestration system is required. Record installed runtime/renderer/image versions and their supported ceilings. Do not add libraries or infrastructure without a concrete task and a decision entry.

## 7. Gate rules

### A. Engineering and merge gates

These are proposed completion rules, retaining the useful existing controls. Current external branch-protection/Sonar settings were not inspected and must not be assumed from workflow comments.

| Gate | Must pass | Failure rule |
|---|---|---|
| Baseline/integrity | Cleanly identified commit; expected bundle and separate manifest pin; hashed lock installs; vendor verifier | Refuse unknown/mutated authority; never autofix vendor bytes |
| Codebase index | GitNexus index for the implementation checkout, freshness check, recorded exclusions/parser failures and critical-path context | A stale/incomplete index cannot stand in for current caller analysis; investigate gaps and verify source directly |
| Static correctness | Backend Ruff lint/format, strict mypy, vocabulary/tests/I/O declarations; frontend ESLint/Prettier/vocabulary/tested checks and TypeScript | No unexplained suppressions or invented vocabulary to bypass a check |
| Behavioral regression | Default offline tests; complete suite with mandatory PostgreSQL; real two-connection races; every confirmed defect has a failing-before/passing-after assertion | Missing/skipped required tests fail. Merely finding a test name does not pass |
| UI behavior | All frontend units, build/deep-link exports, existing accessibility/workbench matrix, plus real API integration journey | Fixture-only tests cannot satisfy integration; no severe accessibility or authority-isolation regression |
| Scan coverage/security | Bandit on 3.12 with no parse errors and claimed-file coverage, locked dependency audit, gitleaks, Trivy/scanner floor | A scan of zero files is a failure. Existing Trivy policy rejects fixable HIGH/CRITICAL findings; unfixed risks still need triage |
| Measured performance | Actual query/call counts on affected endpoints and collection-size cases, bounded inputs, cancellation/timeouts | A declaration such as `IO_BUDGET = None` is not measured evidence |
| Review/diff | Ordinary exact-range task review at each accepted slice; no rewrite tournaments; existing 800-counted-line PR ceiling | Record evidence-backed findings, fix confirmed root causes, rerun affected checks, and split oversized concerns. Defer `confidence-review` to the whole-phase gate below |
| Phase-completion audit | **`adversarial-reviewer` only at phase completion, at extra high (`xhigh`) reasoning**, over the full phase diff and affected callers | No intermediate/per-PR adversarial audit requirement; confirmed blockers must be fixed and reverified before accepting the phase |
| Production smoke | Boot built artifact; health/readiness, auth edge, static routes, real section reads/commands, fixtures absent | A Docker build or image scan alone is insufficient |
| Release qualification | Exact build/adapter/model/set identity, current authenticated verdict, explicit capped paid evaluation when authorized | A unit-green build is not automatically credit-qualified |

Do not invent a pre-existing coverage percentage: `scan_floors.py` principally proves measurement/coverage of files, not an 80%/90% business-correctness threshold. Retain coverage reports, baseline affected packages and prevent unexplained regression; critical cases above must be asserted regardless of aggregate percentage. Confirm actual hosted quality-gate thresholds when accessing that service is in scope.

### B. Credit-workflow gates

An approval is a decision over exact content, not “approved sometime during this run.” Hash the gate's actual inputs using a versioned canonical representation. Record the preview digest, relevant source-set/extraction identity, route/brief/bundle/adapter identity and upstream hashes appropriate to that gate. Derive expected values on the server; a browser-supplied digest is an expectation to compare, never authority.

| Gate/boundary | Release conditions | What blocks or invalidates it |
|---|---|---|
| Document admission | Supported readable format; size/count/page/token limits; immutable bytes/geometry; case write authority; whole pack succeeds | Corrupt/encrypted/unsupported/scanned-without-text inputs, unsafe resource use, or partial pack failure |
| `SOURCE_SET` human approval | Current APPROVER standing reviews exact source-set version and preview; atomic audit entry | Changed membership/extraction/source preview, withdrawal, or invalid actor. Historical approvals remain records, not current permission |
| `RESEARCH_PLAN` human approval | Exact resolved typed route, source-set identity and applicable research-brief content are reviewed and pinned | Route/brief/input/preview change, wrong build/adapter, or revoked standing |
| CP-0 readiness | Valid canonical CP-0 handoff with complete, unique verdicts for intended modules and selected-run lineage | Missing/invalid/blocked verdicts; no inference that artifact presence means ready |
| Dependency edges | `REQUIRED` and applicable frozen `CONDITIONAL` obligations satisfied; soft `OPTIONAL`/`ADVISORY` availability handled with declared restrictions | Never convert all edges into mandatory dependencies. Missing soft input must not become invented analysis or unqualified success |
| Module invocation | Gate-valid run, correct node generation, verified authority and exact upstream/source context, reserved bounded cost | Unapproved/changed pins, wrong-case input, insufficient budget, missing mandatory reference/handoff, unsupported helper |
| Artifact acceptance | Valid full contract/identity/registers; citations inside exact delivery; deterministic calculations where required; current ownership/withdrawal/gate checks | Model-asserted identity, malformed/blocked output, invalid citations, lost worker lease, cancelled run, or changed safety inputs |
| `QA_GATE` | Validated CP-5 clearance meeting the downstream contract; restrictions remain explicit | `{}`, merely accepted CP-5 bytes, `Blocked`, insufficient evidence, or mismatched lineage. A separate human decision is required only if explicitly defined; do not mislabel automated QA |
| Route completion | Every required selected obligation has accepted usable output and all required gates are satisfied | Empty frontier with unresolved nodes is blocked, not `COMPLETE`; optional restrictions remain visible |
| Opinion → freeze → file | Persisted validated revision; exact signed digest; current permissions; signer/freezer/filer independence as required by existing contract | Changed payload/upstream authority, uncited inserted figure, incomplete sign-off, reused/late revision, or non-independent filer |
| Qualification label | Performed evidence matches exact candidate/set/provider-model/adapter/bundle; authenticated review; `decided_at <= now < expires_at` | Future/expired/mismatched verdict or unqualified pathway. Label must not imply a broader scope than the evaluated routes |

Source withdrawal is an immediate safety event. Keep historical artifacts/audit records explainable without continuing to present withdrawn evidence as current or silently replacing a pinned analytical view. Approval/acceptance/withdrawal must share a transaction ordering that prevents a stale read from authorizing a later conflicting commit.

### C. Definition of done for each repair

1. The reproduction fails against the pre-fix implementation for the stated cause.
2. The shared root cause is fixed, and sibling callers are checked.
3. The regression and relevant integration/race/error-path tests pass.
4. An ordinary task review has checked the exact repair range. Neither
   specialist review runs for an individual repair: one full-phase
   `confidence-review`, then one full-phase adversarial code audit, run only at
   phase completion with actual `xhigh` reasoning. Rewrite tournaments are no
   longer required.
5. No unrelated source, vendor or user changes are lost. Gate/contract changes have an explicit decision and migration where needed.
6. Handoff names the exact commit, GitNexus index identity/freshness,
   commands/results, risk classifications, ordinary review result, remaining
   limitations and enabled/disabled feature scope. At phase completion, also
   attach both specialist-review scopes/results, actual reasoning settings,
   verdicts and remediation evidence. “All tests pass” never substitutes for
   “the requested user journey works.”

## 8. Smallest useful delivery order

1. **Environment/gate repair:** make development reproducible and ordinary tests safe.
2. **Execution safety:** pins, authority, concurrency, budgets and honest blocked/QA state.
3. **One faithful module chain:** exact validated handoffs and real text/PDF evidence.
4. **One real credit workbench:** Directory/Upload/Run/Analysis, secured API, durable worker, correct evidence/view behavior.
5. **Trusted Model/Report/Committee:** repair the existing dormant numerical/filing defects before enabling these workflows.
6. **Qualified release:** prove the exact shipped configuration and only then broaden route/section coverage.

Skipped deliberately: another repository rebuild, a generic agent platform, a new graph/checkpoint system, extra message broker, automatic broad web research, Excel/Word restoration, and a UI redesign. Add any of these only when an enabled user workflow demonstrably requires it.

## 9. Confidence review — this review and plan

Least confident about, ranked by consequence:

1. **Attributing newer-code defects to the checkout.** Investigated both exact Git references and executed the readiness cases against each. Verdict: the origin blocked-completion regression is confirmed; the same accusation against a valid local-HEAD DAG is not supported. Report corrected; no source patch in this planning task.
2. **Mistaking architectural choices for bugs.** Read the current vendor handoff contract and decision §14. Verdict: no Excel/Word is by design; CP-2A is already the supported workbook input; canonical Markdown is authoritative upstream. The plan explicitly preserves those distinctions and requires a documented host adaptation.
3. **Reporting hypothetical concurrency failures.** Reproduced both first-head collision and post-revocation approval with actual independent PostgreSQL connections. Verdict: confirmed bugs. F05 names the shared root cause and regression requirements; source repairs remain planned.
4. **Trusting green component tests over real UI behavior.** Ran all existing frontend units and seven App/Workspace/rendered-component counterexamples. Verdict: the six frontend finding groups are confirmed despite the passing baseline. Module-ID graph keys were investigated and not reported as a bug because routes reject duplicate modules.
5. **Overstating financial/qualification correctness.** Reproduced calculator missing-value/policy/duplicate/context/overflow behavior and future-dated qualification. Traced source and run binding statically. Verdict: confirmed local issues; economic correctness of all model outputs and real live-provider quality remain open until the planned independent answer keys and paid qualification.
6. **Accidentally spending money or altering development data during verification.** Removed live-provider configuration from test commands, used a fresh locked environment and isolated temporary PostgreSQL, and checked Git status again. Verdict: no paid calls; checkout still clean; only synthetic test databases/container were removed.
7. **Claiming a complete release gate or working deployment.** Reviewed actual Make/CI/Docker/API paths. Verdict: existing unit/database tests pass, but coverage/security scans, browser production integration, auth edge and current external rulesets were not certified. Those limits are explicit in sections 1 and 7.
8. **Broken references or invented commands.** Checked all 97 Markdown file links for existence and referenced line bounds; compared reusable signatures to source. Verdict: references valid. New command names/endpoints are explicitly proposed, not described as already implemented.

Fixed in this deliverable: baseline attribution and stale architectural recommendations; implementation phases and gates reflect verified code. Verified fine: baseline tests, existing bundle-byte checks, referenced paths and clean checkout. By design: deferred workbook/Word scope and no automatic paid calls. Still open: the source repairs in F01–F18, live qualification and production integration. This report does not mark any of those source defects resolved.
