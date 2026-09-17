Goal: Complete CAOS repair Phases 3–6 as a governed credit workbench.

Work in /Users/ericguei/Documents/caos-workbench on codex/execute-repair-plan. Keep /Users/ericguei/Documents/caos-v2 read-only. Before Phase 3, remediate and accept every open Phase 2 adversarial finding: hook enforcement, fenced accepted ownership, blocked/QA terminal semantics, and priced reservation/exposure exits. Confirm Phase 2 acceptance in docs/CLAUDE_CODE_HANDOFF.md; an implementation commit is not acceptance.

Review these documents before planning or editing, and again when their phase becomes active:
CLAUDE.md; README.md; docs/CLAUDE_CODE_HANDOFF.md; docs/REPAIR_PLAN.md;
docs/DECISIONS.md (especially §12 and §39); docs/SYSTEM_SPEC.md;
docs/IA_SPEC.md; docs/CI_GATE_CONTRACT.md; docs/AI_CODE_QUALITY.md;
docs/INITIALISATION_PROMPT.md; docs/MIGRATIONS.md;
docs/HOST_ADAPTER_CONTRACT.md; docs/PLAN_ADVERSARIAL_REVIEW.md;
docs/ADVERSARIAL_REVIEW.md; DESIGN.md; CONTEXT.md; and
docs/superpowers/plans/2026-09-13-post-phase-2-complementary-plan.md.
Read docs/REBUILD_PLAN.md only as historical context; current repair documents
and decisions govern. Treat ignored logs/reports as supplemental evidence, not
binding instructions. For Phase 4 UI work also review docs/design/BRIEF.md,
docs/design/DESIGN_HANDOFF.md and docs/design/INVENTORY.md. Read the archived
model/report builder specifications only to preserve their explicit exclusions.

Opus 5: medium for briefs, specs, ADRs, runbooks, implementation/review; low for formatting/status. Use targeted ultrathink for plan, trade-off, rollback, race or trust checks. Use max only for a new complex blueprint, then medium; do not re-plan settled architecture. Phase code reviews require actual xhigh. Verify and record model/effort. Add no speculative scope.

At each phase entry, refresh GitNexus with analyze --force --index-only, confirm status, then verify affected definitions/callers in source. Write a tracked task brief with exact base, files, interfaces, failing tests and exit checks. A coordinator may use three implementers concurrently only in isolated worktrees with disjoint files, migrations and test resources. Each reports a reviewed commit; the coordinator alone serially integrates, runs gates and accepts. Never share a branch, database/blob root or provider authority.

Phase 3: prove CP-0 → CP-L10 → CP-5 using exact canonical Markdown, host-owned identity, validated projections, pinned evidence and complete upstream lineage. Valid restricted output retains limitations. Use the real runtime/validator with a deterministic provider; no worker or paid call is required for engineering acceptance.

Phase 4: connect Directory/Upload/Run/Analysis, governed commands, one PostgreSQL worker, events and authorized evidence pages. Prove recovery, authentication, real browser behavior and production packaging.

Phase 5: prove canonical CP-1/CP-2G/CP-4 and required predecessors on a compatible catalog route before CP-CF. Complete deterministic forecasts, saved revisions, independent sign/freeze/file and portable package verification.

Phase 6: prove exact-identity qualification, restore/rollback and final release evidence. Live calls, hosted writes and deployment require explicit authorization and spend bounds.

Prefix shell commands: env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER.

Use TDD and ordinary review per task. After committing and remediation, pass the 800-line gate against the actual PR base. At each phase end run full local/required CI gates, one confidence-review at xhigh, remediate/retest, then one adversarial audit at xhigh. Revalidate changed candidate evidence, including qualification. No rewrite tournaments. Record acceptance in the tracked handoff, then continue directly through the next phase until Phases 3–6 are complete. Pause only for a failed gate, missing explicit authorization (including spend, hosted writes or deployment), or a genuine blocker.
