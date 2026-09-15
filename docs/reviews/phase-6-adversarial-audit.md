## Adversarial review — Phase 6 (`ca7b13a..d4bdde5`)

**Scope:** qualification execution, persistence/read API, qualification chrome, migrations, recovery and the three-engine production journey.  **Verdict:** CONCERNS.

### Warnings

1. **Release evidence remains incomplete.** Saboteur and Security Auditor both found that deterministic qualification is not an authorization to advertise a live provider route. The code correctly returns unqualified/restricted states without a current authenticated verdict, but the required capped live evaluation has not been authorized or run. Do not release a route as qualified until explicit provider/model/route/call/token/cost/time-window authority is supplied and its result is persisted.

### Notes

1. **SSE disconnect noise.** Saboteur observed `httpx.RemoteProtocolError` in the intentionally dropped-stream journey while Playwright still passed. This is expected test-induced disconnect behavior, but makes smoke logs noisier; treat a change in status or an unhandled server failure as actionable, not this known cleanup noise.
2. **Global qualification visibility is a policy seam.** Security Auditor confirmed the endpoint deliberately is not case-scoped. It authenticates callers and hides metadata from readers, but any future role expansion must explicitly decide which non-reader global roles may read evidence by digest.
3. **Transient success text is not a reliable end-to-end assertion.** New Hire traced the timing to the immediate read-back. Unit coverage deliberately holds the refetch to test the text; the production journey now tests the durable contract.

No code blocker was found beyond the already-remediated browser assertion. Security scans, race checks, backend/frontend checks and production image checks passed locally; this audit does not substitute for the missing authorized live qualification or GitHub-hosted checks.
