# Feature 8 Flowchart: Frontend Workspace UI

**Date:** 2026-09-15
**Feature:** Frontend Workspace UI
**Scope:** Browser single-page application, 4 invariant chrome bands (Ribbon, Decision Brief, Section Tabs, Verdict Strip), 9 workspace sections, SSE reactive stream tail, monotonic authority state machine, stale-while-revalidate (SWR) analytical identity reconciliation, Evidence/Source drawers with QuadPoint coordinate normalization, and idempotent command dispatch.

---

## 1. Sources Consulted

- `frontend/src/main.tsx:1-14`: React root initialization and CSS token mount.
- `frontend/src/app/App.tsx:1-57`: BrowserRouter shell, absent route handling, resolve dispatch.
- `frontend/src/app/sections.ts:1-102`: Section registry, enabled sections list, path forwarding, slug renames.
- `frontend/src/app/Workspace.tsx:1-253`: Main workspace layout, route parameter tracking, authority lifecycle, adopt/visible reconciliation, SSE tail integration.
- `frontend/src/app/transport.ts:1-301`: HTTP transport, wire validation, V1 document parsing, qualification fetch, page fetch.
- `frontend/src/app/commands.ts:1-239`: Governed mutation commands, idempotency key generation/reuse, receipt parsing.
- `frontend/src/app/sse.ts:1-48`: Server-Sent Events connection lifecycle, reconnection handlers, event dispatch.
- `frontend/src/app/authority.ts:1-166`: Monotonic seq authority machine, ticket acceptance, snapshot ledger bindings, refetch mapping, analytical identity hashing.
- `frontend/src/app/snapshot.ts:1-25`: Visible snapshot context and hook for pinning viewed version.
- `frontend/src/app/ledger.tsx:1-41`: Comparison ledger provider and snapshot binding interface.
- `frontend/src/app/views.tsx:1-39`: Section to View component mapping registry.
- `frontend/src/chrome/Ribbon.tsx:1-87`: Band 1: brand, case chip, status chips, state, actions.
- `frontend/src/chrome/DecisionBrief.tsx:1-27`: Band 2: CHANGE, IMPACT, ACTION, EVIDENCE, and headline.
- `frontend/src/chrome/SectionTabs.tsx:1-63`: Band 3: Section sub-views with roving tabindex keyboard navigation.
- `frontend/src/chrome/VerdictStrip.tsx:1-20`: Band 4: Conclusion severity, text, and blocking reason.
- `frontend/src/chrome/ServedRole.tsx:1-15`: Served role display and case standing label.
- `frontend/src/chrome/QualificationStrip.tsx:1-91`: Global performed-evidence verification strip and live fetch.
- `frontend/src/chrome/Rail.tsx:1-114`: Workspace navigation rail, section status/counts, served role, refused actions.
- `frontend/src/chrome/compose.ts:1-60`: Client-side synthesis of Chrome bands for V1 documents.
- `frontend/src/chrome/fallback.ts:1-88`: Fallback Chrome composition for loading/unavailable/offline/error states.
- `frontend/src/evidence/EvidenceContext.tsx:1-130`: Evidence coordinator, modal state, active citation/passport/fact tracking.
- `frontend/src/evidence/EvidenceDrawer.tsx:1-122`: Evidence modal for render URLs, silhouettes, bounding boxes, matched text.
- `frontend/src/evidence/SourceDrawer.tsx:1-193`: V1 source fact drawer, token-index text layer, live geometry overlays, withdrawal notice.
- `frontend/src/evidence/CitationChip.tsx:1-36`: Clickable evidence chip button binding to EvidenceContext.
- `frontend/src/evidence/MetricPassport.tsx:1-115`: 10-field passport modal, driver citations, deviation records.
- `frontend/src/evidence/geometry.ts:1-45`: Frame coordinate normalization to fraction box for y-up and y-down axes.
- `frontend/src/sections/directory/DirectorySection.tsx:1-56`: Case register table container and inline NewCase form.
- `frontend/src/sections/upload/UploadSection.tsx:1-61`: Source pack view container and set versions sidebar.
- `frontend/src/sections/analysis/AnalysisSection.tsx:1-220`: Accepted handoff cards, host facts, model analysis, pending node list.
- `frontend/src/sections/book/BookSection.tsx:1-132`: Portfolio cases table / comparison matrix, facet filtering, ledger binding.
- `frontend/src/sections/run/RunSection.tsx:1-269`: Route graph DAG, node detail, gate list, run switcher, work controls.
- `frontend/src/sections/run/controls.tsx:1-542`: Pin input, route choices, gate preview, gate approval, start/retry/cancel commands.
- `frontend/src/sections/model/ModelSection.tsx:1-95`: Accepted CP-CF projection period table, units, and limitation flags.
- `frontend/src/sections/report/ReportSection.tsx:1-118`: Saved report revisions, markdown/record artifacts, narrative paragraphs.
- `frontend/src/sections/committee/CommitteeSection.tsx:1-173`: Saved committee deliverables, signers, frozen/filed state, filing receipts.
- `frontend/src/sections/admin/AdminSection.tsx:1-24`: Admin unavailable capability surface.
- `frontend/src/states/RegionState.tsx:1-93`: Region status discriminator: loading, ready, observed-empty, error, unavailable, stale, offline, partial.
- `frontend/src/states/SectionBoundary.tsx:1-26`: React error boundary catching section render failures to render RENDER_FAILED refusal.

---

## 2. Primary Execution Flowchart

```mermaid
flowchart TD
    %% Entry Point & Router Resolution
    A["createRoot.render<br/>frontend/src/main.tsx:9-13"] --> B["App<br/>frontend/src/app/App.tsx:45-56"]
    B --> C["Shell<br/>frontend/src/app/App.tsx:37-43"]
    C --> D["Resolve<br/>frontend/src/app/App.tsx:25-32"]

    D -->|"forward(pathname, search)"| E{"Check Forwarding<br/>frontend/src/app/sections.ts:92-101"}
    E -->|"Slug / Root Match"| F["Navigate (replace)<br/>frontend/src/app/App.tsx:28"]
    E -->|"No Forward"| G{"sectionFromPath()<br/>frontend/src/app/sections.ts:53-57"}

    G -->|"Invalid Section"| H["Absent Route (404)<br/>frontend/src/app/App.tsx:8-23"]
    H -->|"Render Unavailable"| H1["RegionState (unavailable)<br/>frontend/src/states/RegionState.tsx:39-40"]

    G -->|"Valid Section"| I["Workspace<br/>frontend/src/app/Workspace.tsx:84-252"]

    %% Route Parsing & Parameter Setup
    I --> J["Read URL Search Params<br/>frontend/src/app/Workspace.tsx:85-96"]
    J --> K{"sectionUrl != null?<br/>frontend/src/app/transport.ts:70-96"}

    K -->|"No (Disabled/Missing Case)"| L["status = UNAVAILABLE<br/>frontend/src/app/Workspace.tsx:38,176"]
    K -->|"Yes (Enabled & Valid)"| M["authority.navigate(caseId)<br/>frontend/src/app/authority.ts:25-27"]

    %% SSE Tail Subscription
    M --> N["openTail(eventsUrl)<br/>frontend/src/app/sse.ts:28-47"]
    N -.->|"EventSource listener [Side Effect: SSE Connect]"| N1["SSE Stream (/api/v1/cases/:id/events)<br/>frontend/src/app/sse.ts:25"]
    N1 -.->|"onEvent(name) / onReconnect"| N2{"refetches(name, section)?<br/>frontend/src/app/authority.ts:85-87"}
    N2 -.->|"Yes"| O["Trigger load()<br/>frontend/src/app/Workspace.tsx:117-137"]

    %% Document Fetch Execution
    M --> O
    O --> P["authority.issue()<br/>frontend/src/app/authority.ts:30-32"]
    P --> Q["fetchSection()<br/>frontend/src/app/transport.ts:168-186"]
    Q -->|"HTTP GET [Side Effect: Fetch]"| R["/api/v1/... Endpoint<br/>frontend/src/app/transport.ts:70-96"]

    %% Wire Validation & Classification
    R --> S{"Response Classification<br/>frontend/src/app/transport.ts:178-185"}
    S -->|"Network Threw"| S1["kind: offline<br/>frontend/src/app/transport.ts:180"]
    S -->|"HTTP 404"| S2["kind: unavailable<br/>frontend/src/app/transport.ts:182"]
    S -->|"HTTP !200"| S3["kind: error (refusal)<br/>frontend/src/app/transport.ts:183"]
    S -->|"HTTP 200"| T["classifyV1()<br/>frontend/src/app/transport.ts:122-166"]

    T -->|"V1_PARSER validation"| U{"requireIdentity()<br/>frontend/src/app/transport.ts:134-140"}
    U -->|"Shape/Identity Error"| U1["kind: error (refusal)<br/>frontend/src/app/transport.ts:143-156"]
    U -->|"observed_empty: true"| U2["kind: observed-empty<br/>frontend/src/app/transport.ts:160"]
    U -->|"status: partial"| U3["kind: partial<br/>frontend/src/app/transport.ts:163"]
    U -->|"Valid Document"| U4["kind: ready<br/>frontend/src/app/transport.ts:165"]

    %% Authority Acceptance & Reconciliation
    S1 & S2 & S3 & U1 & U2 & U3 & U4 --> V{"accepts(authority, ticket)?<br/>frontend/src/app/authority.ts:39-41"}
    V -->|"No (Outdated Response)"| V1["Discard Stale Response<br/>frontend/src/app/Workspace.tsx:132"]
    V -->|"Yes (Active Authority)"| W["adopt()<br/>frontend/src/app/Workspace.tsx:62-71"]

    W --> X{"analyticalIdentity() match?<br/>frontend/src/app/authority.ts:103-121"}
    X -->|"Match or Initial"| Y["Adopt: displayed = next<br/>frontend/src/app/Workspace.tsx:68"]
    X -->|"Identity Changed"| Z["Hold SWR: pending = next, stale displayed<br/>frontend/src/app/Workspace.tsx:70"]
    Z -->|"User Clicks RELOAD"| Z1["reload()<br/>frontend/src/app/Workspace.tsx:166-172"]
    Z1 --> Y

    %% State Assignment & Chrome Composition
    Y --> AA["setHeld() [Side Effect: State / DOM Update]<br/>frontend/src/app/Workspace.tsx:115"]
    L --> AA
    AA --> AB["composeChrome() / fallbackChrome()<br/>frontend/src/app/Workspace.tsx:201-206"]

    %% Chrome Bands Mounting
    AB --> AC["Mount Chrome Bands<br/>frontend/src/app/Workspace.tsx:209-232"]
    AC --> AC1["Ribbon<br/>frontend/src/chrome/Ribbon.tsx:15-86"]
    AC --> AC2["DecisionBrief<br/>frontend/src/chrome/DecisionBrief.tsx:12-26"]
    AC --> AC3["SectionTabs<br/>frontend/src/chrome/SectionTabs.tsx:19-62"]
    AC --> AC4["VerdictStrip<br/>frontend/src/chrome/VerdictStrip.tsx:6-19"]
    AC --> AC5["QualificationStrip (Optional Fetch)<br/>frontend/src/chrome/QualificationStrip.tsx:63-90"]
    AC --> AC6["Rail<br/>frontend/src/chrome/Rail.tsx:28-113"]

    %% Workspace Body Providers & State Host
    AC --> AD["Mount Providers & Boundary<br/>frontend/src/app/Workspace.tsx:235-246"]
    AD --> AD1["VisibleSnapshotContext.Provider<br/>frontend/src/app/snapshot.ts:20"]
    AD --> AD2["EvidenceProvider<br/>frontend/src/evidence/EvidenceContext.tsx:60-129"]
    AD --> AD3["LedgerProvider<br/>frontend/src/app/ledger.tsx:18-34"]
    AD --> AD4["RegionState<br/>frontend/src/states/RegionState.tsx:7-92"]
    AD4 --> AD5["SectionBoundary<br/>frontend/src/states/SectionBoundary.tsx:12-25"]

    %% Section View Dispatch
    AD5 --> AE{"Dispatch SECTION_VIEWS[section]<br/>frontend/src/app/views.tsx:28-38"}
    AE -->|"directory"| AF1["DirectorySection<br/>frontend/src/sections/directory/DirectorySection.tsx:11-55"]
    AE -->|"upload"| AF2["UploadSection<br/>frontend/src/sections/upload/UploadSection.tsx:12-60"]
    AE -->|"run"| AF3["RunSection<br/>frontend/src/sections/run/RunSection.tsx:38-268"]
    AE -->|"analysis"| AF4["AnalysisSection<br/>frontend/src/sections/analysis/AnalysisSection.tsx:183-219"]
    AE -->|"model"| AF5["ModelSection<br/>frontend/src/sections/model/ModelSection.tsx:13-94"]
    AE -->|"report"| AF6["ReportSection<br/>frontend/src/sections/report/ReportSection.tsx:65-117"]
    AE -->|"committee"| AF7["CommitteeSection<br/>frontend/src/sections/committee/CommitteeSection.tsx:112-172"]
    AE -->|"book"| AF8["BookSection (Disabled by Default)<br/>frontend/src/sections/book/BookSection.tsx:26-131"]
    AE -->|"admin"| AF9["AdminSection (Disabled by Default)<br/>frontend/src/sections/admin/AdminSection.tsx:7-23"]

    %% Governed Mutation Commands (Example: Run Controls)
    AF3 --> AG["Run Controls & Mutations<br/>frontend/src/sections/run/controls.tsx:124-144"]
    AG -->|"createRun / pinRunInput / approveGate / startRun"| AH["sendCommand(intent, request)<br/>frontend/src/app/commands.ts:80-120"]
    AH -->|"HTTP POST (Idempotency-Key) [Side Effect]"| AI["Backend Command API<br/>frontend/src/app/commands.ts:140-238"]
    AI -->|"Receipt OK"| AJ["onRefetch() [Side Effect: GET /run]<br/>frontend/src/sections/run/controls.tsx:75-86"]
    AJ --> O

    %% Evidence Modal Flow
    AF4 --> AK["Click Citation / Fact Chip<br/>frontend/src/sections/analysis/AnalysisSection.tsx:43-49"]
    AK --> AL["EvidenceContext.openFact()<br/>frontend/src/evidence/EvidenceContext.tsx:74-79"]
    AL --> AM["SourceDrawer Modal Mount<br/>frontend/src/evidence/SourceDrawer.tsx:89-192"]
    AM -->|"fetchPage() [Side Effect: HTTP GET]"| AN["/api/v1/.../sources/:id/pages/:p<br/>frontend/src/app/transport.ts:253-258"]
    AN --> AO["toFraction() Placement<br/>frontend/src/evidence/geometry.ts:27-44"]
    AO --> AP["Render TextLayer Overlays<br/>frontend/src/evidence/SourceDrawer.tsx:19-72"]
```

---

## 3. External Dependencies

### Query & Section Fetch Endpoints (`transport.ts`)
1. `GET /api/v1/directory` — Directory case register query.
2. `GET /api/v1/cases/:caseId/upload` — Admitted source pack and set versions.
3. `GET /api/v1/cases/:caseId/run?run=:runId` — Pinned route, DAG nodes, attempts, and gate status.
4. `GET /api/v1/cases/:caseId/analysis?run=:runId` — Accepted handoffs, citations, model prose, and pending route nodes.
5. `GET /api/v1/cases/:caseId/model?run=:runId` — CP-CF forecast projections and period valuation table.
6. `GET /api/v1/cases/:caseId/report?run=:runId&revision=:revisionId` — Saved narrative report and markdown/record artifacts.
7. `GET /api/v1/cases/:caseId/committee?run=:runId&revision=:revisionId` — Committee deliverable, signers, and filing receipts.
8. `GET /api/v1/cases/:caseId/events?run=:runId` — Real-time Server-Sent Events stream for case activity.
9. `GET /api/v1/cases/:caseId/runs/:runId/sources/:sourceId/pages/:page` — Token-index text layer and layout frames for source documents.
10. `GET /api/v1/qualification/:evidenceSha256` — Global evidence verification status and expiration time.

### Governed Command Endpoints (`commands.ts`)
1. `POST /api/v1/cases` — Create new case (`title`) with `Idempotency-Key`.
2. `POST /api/v1/cases/:caseId/sources` — Multipart form-data admission of files (`document` parts) with `Idempotency-Key`.
3. `POST /api/v1/cases/:caseId/runs` — Create and pin route for a new run (`profile_id`, `selection_id`) with `Idempotency-Key`.
4. `POST /api/v1/cases/:caseId/runs/:runId/input` — Pin subject input parameters (`issuer_id`, `issuer_name`, `reporting_period`, `analysis_date`) with `Idempotency-Key`.
5. `GET /api/v1/cases/:caseId/runs/:runId/gates/:gateSlug/preview` — Read exact gate preview markdown (no idempotency key).
6. `POST /api/v1/cases/:caseId/runs/:runId/gates/:gateSlug/approval` — Approve gate with `preview_sha256` and `input_fingerprint` with `Idempotency-Key`.
7. `POST /api/v1/cases/:caseId/runs/:runId/start` — Start pinned run with `input_fingerprint` and `Idempotency-Key`.
8. `POST /api/v1/cases/:caseId/runs/:runId/retry` — Retry failed run attempt with `input_fingerprint` and `Idempotency-Key`.
9. `POST /api/v1/cases/:caseId/runs/:runId/cancel` — Cancel active run with `Idempotency-Key`.
