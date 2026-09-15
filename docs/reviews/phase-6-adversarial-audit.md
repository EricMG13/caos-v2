## Adversarial review — Phase 6 (`ca7b13a..d4bdde5`)

**Scope:** qualification execution, persistence/read API, qualification chrome, migrations, recovery and the three-engine production journey.  **Verdict:** CONCERNS.

### Warnings

1. **Release evidence remains incomplete.** The authorized capped DeepSeek
   smoke run and production UI checks are now complete, and the live test
   reserves from a dated configured price plus an explicit run ceiling rather
   than a flat estimate. That does not authorize the application to advertise
   a route as qualified: qualification still requires an externally
   authenticated verdict for the exact provider/model/route/call/token/cost/
   time window. Do not mint or substitute that evidence locally.

### Notes

1. **SSE disconnect noise.** Saboteur observed `httpx.RemoteProtocolError` in the intentionally dropped-stream journey while Playwright still passed. This is expected test-induced disconnect behavior, but makes smoke logs noisier; treat a change in status or an unhandled server failure as actionable, not this known cleanup noise.
2. **Global qualification visibility is a policy seam.** Security Auditor confirmed the endpoint deliberately is not case-scoped. It authenticates callers and hides metadata from readers, but any future role expansion must explicitly decide which non-reader global roles may read evidence by digest.
3. **Transient success text is not a reliable end-to-end assertion.** New Hire traced the timing to the immediate read-back. Unit coverage deliberately holds the refetch to test the text; the production journey now tests the durable contract.

No code blocker was found beyond the already-remediated browser assertion. Security scans, race checks, backend/frontend checks and production image checks passed locally; this audit does not substitute for the missing authorized live qualification or GitHub-hosted checks.

## Adversarial review addendum — provider-profile remediation

Effort: `xhigh`, run separately after confidence remediation and verification.

**Scope:** owned `dc25c65..working-tree` provider, qualification, adapter,
environment, tests and evidence documentation. **Verdict:** CLEAN after
remediation.

### Remediated findings

1. **Saboteur — dynamic provider could mint an overbroad verdict (critical).**
   `allow_fallbacks: false` did not choose the first endpoint, and an unset pin
   still left qualification on a dynamic pool. The request now orders one tag
   and the qualification harness refuses an unpinned OpenRouter provider.
2. **New Hire — display name and endpoint tag were indistinguishable
   (warning).** `DeepSeek` looked valid but OpenRouter requires catalog tag
   `deepseek`. Lowercase validation, a concrete example and a regression make
   the contract explicit.
3. **Security Auditor — a profile change silently changes the external data
   recipient (warning).** The README now states that changing the provider
   requires fresh authorization; offline gates scrub the new variables and no
   credential or response body enters tracked evidence.
4. **Saboteur — prompt guidance leaked into accepted-read I/O (warning).**
   Citation candidates were built by every `_context` caller, including replay
   and accepted CP-CF validation, exceeding the declared model I/O budget.
   Candidate generation is now explicit at prompt construction only; the
   existing budget regression passes without raising the budget.

### Notes

1. First-party DeepSeek remains inaccessible under the current OpenRouter
   account/workspace policy. The code fails closed; account-policy changes are
   external administration, not an application workaround.
2. The successful reasoning probe and failed full run establish only
   `openrouter/ionstream/xhigh` behavior. They do not justify a claim about
   every DeepSeek deployment or a positive qualification verdict.

The blocking invariants found by the personas were fixed at their shared
boundaries and covered by focused regressions. No unresolved code blocker
remains; release qualification remains correctly negative.

Post-remediation verification passed 2,844 PostgreSQL-backed tests, 21 race
tests, all I/O budgets, repository lint/types/security, frontend build, 230
units, 171 accessibility entries and 90 three-engine workbench tests.
