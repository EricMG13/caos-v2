## Confidence review — Phase 6 (`ca7b13a..d4bdde5`)

Least confident about (ranked):

1. Prepared work could be re-bound to a changed catalog or source set.
   Investigated → `PreparedCase` retains the set digest, provider, model and resolved route; `_eligible` checks that retained route. The regression mutates catalog/source state after preparation.
   Verdict → fixed in `a28423f`; verified by the focused suite and the full backend gate.
2. A reader could learn whether an evidence digest exists.
   Investigated → `read_qualification` returns `RESTRICTED` before its database read, and `_read` omits all metadata.
   Verdict → fine; exercised by the reader/PDF journey and API tests.
3. A stale or malformed verdict could be shown as current.
   Investigated → evidence and verdict identities are recomputed and compared; database time is used; future, expired and binding-invalid states fail closed.
   Verdict → fine; regression tests cover the clock and identity cases.
4. The qualification strip could display a response for a different digest.
   Investigated → transport rejects a substituted identity and the strip holds status only when its digest matches the current prop.
   Verdict → fine; covered by transport and strip tests.
5. The production journey could hide a real creation failure behind a timing-dependent success note.
   Investigated → Firefox reproduced a `201` followed by an immediate refetch that removed the intentionally transient note before paint.
   Verdict → confirmed test defect, fixed in `d4bdde5`: the journey now requires the durable `201` receipt and refreshed run. Firefox and WebKit passed all 14 tests after the repair.
6. Restore evidence could omit qualification rows.
   Investigated → the restore probe writes and reads the exact evidence/verdict pair; migrations 0018/0019 preserve both tables.
   Verdict → fine; recovery probe and production image tests passed.

Fixed: durable browser assertion in `d4bdde5`.

Verified fine: exact identity binding, reader non-disclosure, verdict time validation, UI response binding, restore persistence.

By design: no live provider call was made; the UI therefore cannot claim a release-qualified live route.

7. The live-provider smoke test could reserve a placeholder rather than the
   configured model's maximum possible call cost.
   Investigated → the production worker already parses one dated model price
   and reserves `worst_case(price)`, but the direct live test constructed its
   execution with a flat `0.10` estimate.
   Verdict → fixed locally: the test now requires the same dated price input
   as the worker plus a positive, explicit run ceiling, and CI supplies both
   only as repository variables. The authorized three-call DeepSeek run used
   the configured ceiling; the focused price/configuration suite passed.
8. Production evidence could be confused with a fixture-only browser result.
   Investigated → rebuilt the production image without its stale local Docker
   cache; the production-image suite passed and the disposable Chromium
   journey completed its real text/PDF, restricted-reader, crash/restart and
   cleanup flow. The reader assertion is deliberately `RESTRICTED`, never a
   fabricated qualification.
   Verdict → automated evidence is current.

Still open: an external, authenticated qualification verdict for the exact
provider/model/route/time window and hosted required-check confirmation. The
application correctly refuses to mint that release evidence itself.

## Confidence review addendum — provider-profile remediation

Effort: `xhigh`, over the whole Phase 6 completion candidate after the live
qualification outcome.

Scope: owned `dc25c65..f95e8ba`; user-owned `CLAUDE.md`, `.claude/skills/`,
`AGENTS.md` and `gemini-audit.md` were excluded.

Least confident about (ranked):

1. OpenRouter's fallback switch might not bind the first selected endpoint.
   Investigated → official routing documentation and generation reconciliation
   confirmed that `allow_fallbacks: false` alone still let OpenRouter select
   Ionstream first.
   Verdict → confirmed bug.
   Patch → send one lowercase endpoint tag in `provider.order`, retain disabled
   fallbacks, and bind endpoint/reasoning into qualification identity.
2. A future qualification could still use the legacy automatic provider pool.
   Investigated → reasoning-only or unset configuration produced an identity
   that did not name the endpoint OpenRouter would choose.
   Verdict → confirmed bug.
   Patch → the qualification boundary now refuses OpenRouter without an
   explicit upstream pin; ordinary non-qualification calls retain legacy auto
   routing. Regression covers refusal and pinned identity.
3. Endpoint display names might be accepted as routing tags.
   Investigated → OpenRouter's endpoint catalog separates display name
   `DeepSeek` from tag `deepseek`; the display name produced repeatable 404s.
   Verdict → confirmed configuration defect.
   Patch → provider tags must be lowercase and the example names the tag.
4. The DeepSeek failure might still be fallback routing, disabled reasoning or
   truncation.
   Investigated → the frozen-v2 Ionstream/xhigh generation reconciled to 6,286
   native reasoning tokens and `finish_reason=stop`; the host refused exact
   citation delivery.
   Verdict → fine: the failure classification is evidence-backed and remains
   non-qualification.
5. Ambient live-profile variables might leak into offline gates.
   Investigated → all Make test/smoke entry points and the restore probe scrub
   both new names; focused tests, Ruff and mypy passed.
   Verdict → fine.
6. Citation-candidate guidance might add undeclared work to accepted reads.
   Investigated → `_context` served prompt construction, replay and accepted
   read validation, so the later candidate-guidance change added three database
   operations to the model read path and broke its declared I/O budget.
   Verdict → confirmed bug.
   Patch → candidate generation is now requested only by the two prompt-building
   callers; replay and accepted reads retain their original bounded work. The
   exact model budget plus prompt/citation regression set passed (40 tests).

Fixed: endpoint pinning, qualification refusal for automatic routing, tag
validation/documentation, adapter revision identity, prompt-only candidate work.

Verified fine: one-call/no-retry behavior, fail-closed first-party 404, exact
profile binding across prepare/perform, offline environment scrubbing, no
qualification verdict on failure.

By design: model pricing remains explicit dated operator input; external
generation reconciliation is reviewer evidence, not provider self-identity.

Still open: first-party DeepSeek is excluded by current OpenRouter account or
workspace policy; DeepSeek remains unqualified for the canonical route.

Final verification: 2,844 PostgreSQL-backed tests, 21 race tests, all 22 I/O
budgets, repository lint/types/security, frontend build, 230 units, 171
accessibility entries and 90 three-engine workbench tests passed.

## Confidence review addendum — 65,536-token Gemini retry

Effort: `xhigh`, at the Phase 6 checkpoint before the authorized paid retry.

Scope: the completion ceiling, OpenRouter profile binding, conservative pricing,
fixture assertions, the narrowly scoped gitleaks exception, and their decision
record. User-owned `CLAUDE.md`, `.claude/skills/`, `AGENTS.md` and
`gemini-audit.md` remain excluded.

Least confident about (ranked):

1. **A 65,536-token retry could share the earlier 32,768-token evidence
   identity.** Investigated → `Bundle.build_id` comes from the immutable
   vendored manifest, not host source, and the existing OpenRouter identity
   named only endpoint and reasoning. Verdict → confirmed binding gap. Patch →
   bind `MAX_COMPLETION_TOKENS` into every pinned OpenRouter qualification
   profile, so this attempt is exactly
   `openrouter/google-ai-studio/high/65536`. Targeted red/green regressions
   prove the new suffix is persisted through provider configuration and harness
   identity validation.
2. **The shared ceiling could silently route ordinary models to a different
   provider or weaker parameter set.** Investigated → every request retains
   `require_parameters: true`, one explicit endpoint when configured, and no
   fallbacks. Verdict → it can cause a non-supporting configured provider to
   refuse, but cannot silently downgrade or re-route a qualification. The user
   authorized the shared CAOS bound; no model selection changed.
3. **The larger output reservation could exceed the authorized ceiling.**
   Investigated → at the configured Gemini rates (`$0.75` input and `$3.75`
   output per million), `worst_case` is exactly `$1.03219200` per node and
   `$3.09657600` for the three-node route. Verdict → within the explicit
   `$22.00` run/set ceiling; pricing regressions passed.
4. **The gitleaks relief could hide a credential.** Investigated → the added
   regex matches only the two closed literal finish-reason strings, not a path,
   key name or arbitrary assignment. Verdict → safe scope; the current full
   repository scan found no leaks.
5. **A maximum-length answer could exceed the unchanged 4 MiB response-byte
   ceiling.** Investigated → the byte limit remains an independent host safety
   boundary and rejects a whole oversized response before parsing. Verdict →
   deliberate fail-closed behavior, not a reason to raise an unrelated
   transport limit; the live result will establish practical compatibility.

Fixed: qualification identity now binds the changed completion ceiling.

Verified: provider/pricing regression suite (219 tests), targeted identity
red/green regression (3 tests), lint, format, vocabulary, mypy, Bandit,
pip-audit and gitleaks.

Still open: the one authorized live Gemini attempt and an external,
authenticated qualification verdict. No local check can substitute for either.
