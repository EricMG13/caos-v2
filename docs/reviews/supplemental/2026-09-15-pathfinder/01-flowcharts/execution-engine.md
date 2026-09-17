# Feature 4 Flowchart: Execution Engine & Worker Runtime

**Date:** 2026-09-15
**Feature:** Execution Engine & Worker Runtime
**Scope:** Background worker polling loop, pure frontier evaluation, lease fencing, pre-flight context checks, fail-closed budget reservation, OpenRouter HTTPS invocation, attempt outcome recording, and atomic run completion.

---

## 1. Sources Consulted

- `server/api/commands/execution.py:1-273` — API commands (`start_run`, `retry_run`, `cancel_run`), pin & fingerprint verification, command envelopes.
- `server/store/work.py:1-217` — Work queue state machine (`enqueue_run`, `claim_run`, `require_lease`, `release`, `stop`, `requeue_run`, `request_cancel`, `mark_work_done`).
- `server/engine/worker.py:1-304` — Background worker process (`run_worker`, `work_once`, `pause_seconds`, `_refused`, `_settle`, `price_from_environment`, SIGTERM handler).
- `server/engine/runtime.py:1-478` — Frontier execution loop (`run_route`, `_drive`, `accepted_artifacts`, `_run_node`, `_settle`, `_end_blocked`, `_explain_live`).
- `server/pricing.py:1-68` — Worst-case ceiling calculation (`worst_case`), `ModelPrice` dataclass.
- `server/store/budget.py:1-171` — Fail-closed budget reservation (`reserve`, `_reserve`, `_remaining`, `validate_spend`, `reserved_for`).
- `server/provider.py:1-465` — OpenRouter client, HTTPS urllib transport (`UrllibTransport`, `_opener`), request encoding, Decimal cost extraction (`_completion`, `_content`).
- `server/store/outcomes.py:1-360` — Attempt checking & outcomes (`require_idle`, `execution_reads`, `check_call`, `record_outcome`, `record_refusal`, `accepted_rows`, `_record`).
- `server/store/runs.py:1-451` — Run lifecycle & transitions (`start_attempt`, `accept_attempt`, `complete_run`, `block_run`, `cancel_run`, `_transition`, `_require_terminal_decision`).
- `server/methodology/runner.py:1-138` — `ModuleProvider` implementation bridging `runtime.Provider` to canonical execution.
- `server/methodology/canonical.py:160-260` — `execute_handoff` pipeline calling provider and recording initial outcome.

---

## 2. Primary Execution Flowchart

```mermaid
flowchart TD
    classDef happy fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef sideEffect fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef error fill:#ffebee,stroke:#d32f2f,stroke-width:1px;

    subgraph Enqueue["1. Enqueue Run (API)"]
        A["start_run<br/>server/api/commands/execution.py:79-91"]:::happy --> B["_queue<br/>server/api/commands/execution.py:135-170"]:::happy
        B --> C["_require_owned & _require_this_build<br/>server/api/commands/execution.py:213-241"]:::happy
        C --> D["execution_input check<br/>server/store/gates.py:48-75"]:::happy
        D --> E["enqueue_run<br/>server/store/work.py:41-51"]:::sideEffect
        E -. "DB Write: INSERT run_work (QUEUED)<br/>Audit Write: RUN_ENQUEUED" .-> F["run_command receipt<br/>server/api/commands/execution.py:208-211"]:::happy
    end

    subgraph WorkerPoll["2. Worker Claim"]
        G["run_worker loop<br/>server/engine/worker.py:200-235"]:::happy --> H["work_once<br/>server/engine/worker.py:115-160"]:::happy
        H --> I["claim_run (SKIP LOCKED)<br/>server/store/work.py:54-91"]:::sideEffect
        I -. "DB Write: UPDATE run_work<br/>state=CLAIMED, token++, lease_expires_at" .-> J["Acquired Lease(run_id, token)<br/>server/store/work.py:34-39"]:::happy
    end

    Enqueue --> WorkerPoll

    subgraph EngineLoop["3. Route Execution & Frontier Loop"]
        J --> K["run_route<br/>server/engine/runtime.py:128-163"]:::happy
        K --> L["_execution_route authority check<br/>server/engine/runtime.py:466-478"]:::happy
        L --> M["_drive loop entry<br/>server/engine/runtime.py:165-223"]:::happy
        M --> N["accepted_artifacts<br/>server/engine/runtime.py:271-328"]:::happy
        N --> O["frontier(route, accepted, named)<br/>server/engine/route.py:118-142"]:::happy
        O --> P{"replay_billed?<br/>server/engine/runtime.py:184-195"}:::happy
        P -- "Crash recovery detected" --> P1["_settle replayed verdict<br/>server/engine/runtime.py:225-269"]:::sideEffect
        P1 -. "Accept stored answer / Block without call" .-> M
        P -- "No uncommitted bills" --> Q{"ready frontier nodes?"}:::happy
    end

    subgraph NodeExec["4. Node Execution Pipeline"]
        Q -- "ready = [route_node_id, ...]" --> R["_run_node<br/>server/engine/runtime.py:355-434"]:::happy
        R --> S["check_context (pre-flight bounds)<br/>server/methodology/runner.py:66-78"]:::happy
        S --> T["start_attempt<br/>server/store/runs.py:89-140"]:::sideEffect
        T -. "DB Write: INSERT run_attempts<br/>Event: ATTEMPT_STARTED" .-> U["reserve worst_case budget<br/>server/store/budget.py:57-80"]:::sideEffect
        U -. "DB Write: INSERT budget_reservations<br/>Fail-closed ceiling check (Commits alone)" .-> V["provider.execute -> execute_handoff<br/>server/methodology/canonical.py:161-253"]:::happy
        V --> W["UrllibTransport.post (HTTPS)<br/>server/provider.py:133-154"]:::sideEffect
        W -. "HTTP Call: POST openrouter.ai/chat/completions<br/>Read usage.cost as Decimal" .-> X["BlobStore.put(diagnostic)<br/>server/blobs.py"]:::sideEffect
        X --> Y["record_outcome<br/>server/store/outcomes.py:176-194"]:::sideEffect
        Y -. "DB Write: INSERT budget_ledger (charge)<br/>INSERT call_outcomes, Event: CALL_OUTCOME_RECORDED" .-> Z["BlobStore.put(markdown, record)<br/>server/blobs.py"]:::sideEffect
        Z --> AA["accept_attempt<br/>server/store/runs.py:179-203"]:::sideEffect
        AA -. "DB Write: INSERT artifacts<br/>Event: ATTEMPT_ACCEPTED, renew lease" .-> AB["_run_node returns True<br/>server/engine/runtime.py:434"]:::happy
        AB --> M
    end

    subgraph SubordinateBranches["Subordinate Error / Alternative Branches"]
        S -- "Prompt over ceiling" --> ERR1["Refusal: CONTEXT_OVER_CEILING<br/>(No attempt, no reservation)"]:::error
        U -- "Exceeds remaining ceiling" --> ERR2["Refusal: BUDGET_CEILING_REACHED<br/>(No HTTP call)"]:::error
        W -- "Blocked handoff verdict" --> ERR3["_end_blocked -> block_run<br/>server/engine/runtime.py:437-464"]:::error
        W -- "Provider failure / Analytical refusal" --> ERR4["_explain_live -> record_refusal<br/>server/engine/runtime.py:331-342"]:::error
        ERR4 --> ERR5["_refused -> stop(STOPPED)<br/>server/engine/worker.py:162-178"]:::error
        ERR5 --> RETRY["retry_run -> requeue_run<br/>server/api/commands/execution.py:93-104"]:::happy
        RETRY -. "Requeues STOPPED run" .-> E
        H -- "SIGTERM caught between nodes" --> ST1["_Stopping -> release(QUEUED)<br/>server/engine/worker.py:146-147"]:::error
        CANCEL_CMD["cancel_run API<br/>server/api/commands/execution.py:107-133"] --> CANCEL_WORK["request_cancel<br/>server/store/work.py:170-202"]:::sideEffect
        CANCEL_WORK -. "Sets cancel_requested_at<br/>require_lease discovers -> cancel_run" .-> CANCEL_TERM["cancel_run terminal<br/>server/store/runs.py:388-394"]:::error
    end

    subgraph TerminalState["5. Terminal Evaluation"]
        Q -- "ready is empty" --> AC["node_states evaluation<br/>server/engine/route.py:95-115"]:::happy
        AC --> AD{"All nodes COMPLETE?<br/>server/engine/runtime.py:219-222"}:::happy
        AD -- "Yes: all nodes accepted" --> AE["complete_run<br/>server/store/runs.py:322-339"]:::sideEffect
        AD -- "No: unfinished required work" --> AF["block_run<br/>server/store/runs.py:362-378"]:::error
        AE --> AG["_transition -> RunStatus.COMPLETE<br/>server/store/runs.py:396-431"]:::sideEffect
        AG -. "DB Write: UPDATE runs status='COMPLETE'<br/>Event: RUN_COMPLETE<br/>mark_work_done: UPDATE run_work state='DONE'" .-> AH(["Terminal State Reached"]):::happy
        AF --> AI["_transition -> RunStatus.BLOCKED<br/>server/store/runs.py:396-431"]:::error
        AI -. "DB Write: UPDATE runs status='BLOCKED'<br/>Event: RUN_BLOCKED<br/>mark_work_done: UPDATE run_work state='DONE'" .-> AH
    end
```

---

## 3. External Dependencies

1. **Governance & Request Handling (Feature 1)**:
   - `server/api/commands/_request.py`: `require_case_writer`, `command_response`, `json_body`, `Key`.
   - `server/store/commands.py`: `run_command`, `request_digest`.
   - `server/store/audit.py`: `GovernedAction`.
   - `server/store/members.py`: `Standing`.
2. **Route Graph & Manifest Authority (Feature 2 & 3)**:
   - `server/engine/route.py`: `ResolvedRoute`, `RouteNode`, `frontier`, `node_states`, `NodeState`, `NamedObjects`, `EdgeType`.
   - `server/methodology/bundle.py`: `Bundle`, `verify_manifest`.
   - `server/methodology/invocation.py`: `named_objects`.
3. **Gate Approval & Input Pinning (Feature 3)**:
   - `server/store/gates.py`: `execution_input`, `approved_run_input`, `require_adapter_route`.
   - `server/store/run_inputs.py`: `load_run_input`.
4. **Methodology Execution & Canonical Adapter (Feature 5)**:
   - `server/methodology/runner.py`: `ModuleProvider`.
   - `server/methodology/canonical.py`: `check_context`, `execute_handoff`, `replay_billed`, `blocked_verdict`, `accepted_projections`.
5. **Storage & Blob Infrastructure (Feature 7)**:
   - `server/blobs.py`: `BlobStore` (content-addressed storage for artifacts, records, and raw diagnostics).
   - `server/store/__init__.py`: `StoreConnection`, `RunStatus`, `connect`, `apply_schema`, `rollback_or_close`.
   - `server/store/events.py`: `lock_run`, `append`, `RunEvent`.
   - `server/store/cases.py`: `lock_case`.
   - `server/refusals.py`: `Refusal`, `RefusalCode`.
