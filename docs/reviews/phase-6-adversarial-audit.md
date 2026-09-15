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

**Scope:** owned `dc25c65..f95e8ba` provider, qualification, adapter,
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

## Adversarial review addendum — 65,536-token Gemini retry

Effort: `xhigh`, after the confidence remediation and before the authorized
live call. **Verdict:** CLEAN after remediation.

### Remediated findings

1. **Saboteur — 32k and 65k calls could obtain interchangeable qualification
   evidence (critical).** The vendor `build_id` does not fingerprint the host
   completion policy. The provider identity now appends the exact ceiling;
   changing it forces a fresh prepared identity and rejects stale preparation.
2. **New Hire — the new profile contract was implicit (warning).** A bare
   numeric suffix would otherwise be easy to mistake for a model revision.
   The decision record names it as the completion ceiling and provider/harness
   regressions assert the complete profile string.
3. **Security Auditor — an allowlist change could turn a false-positive fix
   into a secret-scanning blind spot (warning).** The exception is anchored to
   the two public enum values exactly; it neither ignores a file nor broadens
   to arbitrary `key=value` content. A full-history gitleaks scan remains
   clean.

### Notes

1. Raising a shared ceiling may make an unrelated future configured endpoint
   unavailable if it does not accept 65,536 output tokens. Required parameters
   and disabled fallbacks make that a safe refusal rather than a silent provider
   change. Make a per-model policy only if a supported configured model needs a
   different bound.
2. The 4 MiB response-byte limit can still fail closed on an exceptionally
   large encoded response. It is a separate transport guard, intentionally not
   relaxed by this narrowly scoped output-token change.

No unresolved repository code or security blocker remained for the single
authorized Gemini call. Its temporary reporter then failed after `perform()`
returned and erased the disposable record; therefore it created no usable
execution evidence, and no retry is authorized. Even a successfully captured
future result cannot create a qualification verdict without external
authenticated review.

## Adversarial review addendum — durable qualification handoff

Effort: `xhigh`; scope is the uncommitted Phase 6 recovery candidate, excluding
user-owned working-tree files. **Verdict:** CLEAN after remediation; this is
not a release qualification verdict.

### Remediated findings

1. **Saboteur — kill the reporter after `perform()` returns (critical).** The
   old path held the only result in process memory. The shared execution
   boundary now commits the immutable snapshot and exact evidence identity
   before control returns; complete and stopped-path regressions assert both.
2. **New Hire — a new execution caller must remember two obscure store calls
   (warning).** Snapshot/evidence creation now belongs to `perform()`, the one
   common execution path, not to a disposable script. The reporter only
   validates and serializes that state.
3. **Security Auditor — an attacker could attach an old evidence row to a
   snapshot with a matching digest but different declared identity (warning).**
   Snapshot/evidence joins now compare all five identity fields and incomplete
   snapshots cannot be promoted to current verdicts. Regression covers the
   substituted legacy record.
4. **Saboteur — stop the first case of a multi-case set (warning).** Initial
   prefix validation contradicted its own shorter-record allowance. It now
   compares the shorter prefix after its explicit upper-bound check; the
   affected multi-case and injected-read-failure regressions pass.

### Notes

1. The retained local database and blob root are reviewer evidence, not a
   substitute for the required external six-field authenticated verdict.
2. The snapshot document deliberately excludes prompts, source text and model
   response bodies; it contains only the pins, outcomes, hashes and anchors
   needed to evaluate the execution.

The candidate has no remaining local code finding from these personas. Its
three-scenario migration restore proof and full CI-equivalent gate passed:
2,849 backend tests, 21 race tests, security, frontend, accessibility,
workbench, image, and all three 14-step production journeys. Authorized live
execution and external review remain release prerequisites.
