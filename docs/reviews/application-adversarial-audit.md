## Application-wide adversarial audit — `5054d7c`

**Scope:** the complete deployable application boundary: API edge/identity and exception surface; all v1 reads and governed writes; PostgreSQL transactions, membership, source/route/gate/attempt/budget state; worker/runtime/provider boundary; evidence ingestion, PDF child process and citation reads; deliverables/revisions/filing; browser transport, section controls and qualification chrome; migrations, image/smoke, static scans and the three-engine journey. GitNexus was refreshed at this commit (8,768 nodes, 22,363 edges, 378 clusters, 300 flows).

**Method:** Saboteur traced hostile inputs and state transitions across API-to-store-to-worker boundaries; New Hire traced the primary case path from browser command through read-back and recovery; Security Auditor reviewed the edge, identity, input, SQL, subprocess and provider seams. Existing evidence was rechecked: parameterized SQL, Bandit/pip-audit/gitleaks/Trivy, race tests, backend/frontend suites, accessibility, image tests and browser journeys.

**Verdict: BLOCK — release-control blockers, not a newly confirmed in-repository exploit.**

### Critical findings

1. **Required release qualification is absent.** The deterministic harness and authenticated evidence model correctly fail closed, but no explicitly authorized capped live-provider evaluation exists for advertised routes. A route cannot be represented as credit-qualified until the exact provider, model, route, maximum calls/tokens/cost and time window are authorized, executed, persisted and verified.
2. **The branch cannot pass the repository’s size gate.** `PR_BASE=eebb1327a5b77ea75775e793b420251595336f29 make check-size` reports 75,566 changed lines against an 800-line ceiling. It must be split into reviewable PRs; green local suites do not waive that CI requirement.

### Warnings

1. **Trusted edge remains an external security assumption.** The API correctly rejects duplicate/lookalike identity headers, requires an edge token in edge mode, strips it before application code and rejects tokenless non-loopback traffic. It cannot detect a reverse proxy that forwards browser-supplied identity headers. Deployment must enforce the documented strip-and-replace contract and private API listener.
2. **Hosted required checks are unverified.** No PR exists for `codex/execute-repair-plan`; therefore GitHub’s branch protection, required workflow results and image provenance have not been checked for the exact candidate.
3. **Qualification evidence is intentionally global.** Readers receive metadata-free `RESTRICTED`; non-reader global roles may read an immutable digest. If new global roles are introduced, their qualification-read authority must be explicitly specified and tested rather than inheriting this behavior accidentally.

### Notes

1. The intentionally disconnected SSE journey logs a child-side `RemoteProtocolError` while its browser assertions pass. This is expected test noise, but an operational log policy should distinguish it from a failed stream implementation.
2. The 322 authored server/frontend/test files were audited by boundary and call graph, not by treating generated wire artifacts or snapshot bytes as independent application logic.

### Verified controls

- API inputs are typed and command writes require idempotency keys plus case/global authority; store calls recheck authority under transaction.
- SQL calls in the reviewed surface use bound parameters; the PDF parser executes a fixed isolated interpreter and parses JSON only.
- Provider reservations are made before calls and retained on indeterminate outcomes; worker leases, cancellation and outcome fencing have race coverage.
- Reader qualification responses avoid evidence-existence and metadata disclosure; browser transport rejects substituted qualification identities.

This audit provides no authority to make paid calls, change GitHub settings, or waive CI policy.
