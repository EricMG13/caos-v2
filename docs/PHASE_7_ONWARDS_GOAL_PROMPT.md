Goal: Complete CAOS Phases 7–13 under docs/COMPLETION_PLAN.md — deploy the sixteen remaining catalog pathways with their modules, corpus and answer keys, and build only what that programme needs.

Work in /Users/ericguei/Documents/caos-workbench on codex/execute-repair-plan. Keep /Users/ericguei/Documents/caos-v2 read-only. Phase 6 is accepted (docs/DECISIONS.md §62, §69); do not reopen it. The audit remediation plan (docs/superpowers/plans/2026-09-17-audit-remediation.md) is already underway in its own worktrees: consume its landed outputs, record its state in the handoff, never run its tasks or its phase close from this plan. Confirm each phase's acceptance in docs/CLAUDE_CODE_HANDOFF.md before starting the next; an implementation commit is not acceptance.

Review these documents before planning or editing, and again when their phase becomes active:
CLAUDE.md; README.md; docs/CLAUDE_CODE_HANDOFF.md; docs/COMPLETION_PLAN.md;
docs/REPAIR_PLAN.md (accepted, not edited); docs/DECISIONS.md (especially §39,
§40, §49–§53, §56, §61–§69); docs/SYSTEM_SPEC.md; docs/IA_SPEC.md;
docs/CI_GATE_CONTRACT.md; docs/AI_CODE_QUALITY.md; docs/MIGRATIONS.md;
docs/HOST_ADAPTER_CONTRACT.md; docs/CI_DELIVERY_SPLIT_PLAN.md; docs/FINAL_CHECK.md;
qualification/*/RESULT.md; DESIGN.md; CONTEXT.md; and
docs/superpowers/plans/2026-09-17-completion-complementary-plan.md with its task
briefs. For a pathway task also read every module's SKILL.md on that route, the
catalog's typed edges and the execution profiles' LITE object rows. Treat
ignored logs and reports as supplemental.

Models: Opus 5 low for scaffolding, fixtures, admission manifests and regenerated ledgers; Opus 5 medium for per-module fixtures and contract tests, route enablement, key authoring from documents, endpoints, wire, UI, tests, PR authoring and ordinary per-task review; Opus 5 max with ultrathink for one targeted invariant prompt per named risk (each unproven module's register semantics, the money path, three-actor independence, two-worker interleavings, the trust trace). Fable 5.1 medium for long-horizon multi-file work (evidence selection, CP-DR brief delivery, the command chain, async store, second-worker fencing, signed assertion); Fable 5.1 high for every phase and task brief and every vendor request document; Fable 5.1 xhigh for the whole-phase confidence review and the separate adversarial audit. Never put ultrathink in a Fable prompt. Sonnet is not used. Record actual model, version and effort at every checkpoint.

At each phase entry, refresh GitNexus with analyze --force --index-only, confirm status, then verify affected definitions and callers in source; run impact before editing a symbol and detect_changes before committing. Write one tracked brief per task with exact base, files, interfaces, failing tests, executor row and exit checks; a pathway brief instantiates the seven-step template (contract stress test, fixtures, contract tests, whole-route run, corpus, keys, live run). A coordinator may use up to five implementers concurrently only in isolated worktrees with disjoint files, migrations and test resources. Each reports a reviewed commit; the coordinator alone integrates, runs gates and accepts, and fixes an implementer's failure directly rather than re-dispatching it.

Phase 7: reconcile the ledger, handoff and feature status; dispose of the untracked audit files; verify each landed PR's hosted checks read-only; record the remediation stream's landed waves.

Phase 8: register keys over the vendor's own register reader; the dated price recorded with the reservation and the encoded request priced before reserving; a verdict that must name a recorded model, VERDICT_ALREADY_RECORDED and a receipt; the corpus register naming every document in hand or to source; five vendor change requests (the LITE producers, the marker split, CP-0 gating, the unshipped rules, the LITE scope mapping).

Phase 9: the four LITE pathways the current bundle can run — LITE_PORTFOLIO_DECISION, LITE_RELATIVE_VALUE, LITE_DECISION_LEDGER (CP-8), LITE_DEEP_RESEARCH (CP-DR, with the pinned brief delivered as a host-owned section, supplied evidence only) — each enabled, keyed and run when authorized; the three that need vendor LITE producers held with their briefs.

Phase 10: per-node evidence selection recorded on the attempt and enforced by every reader; the bounded line group and a per-section bound; the conditional-edge guard; successor runs naming the source a CONDITIONAL verdict asked for; readiness-joined refs and a stored anchor; declared quote normalisations.

Phase 11: the FULL pathways in order — MARKET_DISLOCATION, LIQUIDITY_REVIEW (CP-2D), EARNINGS_UPDATE (CP-1B), DECISION_LEDGER and DEEP_RESEARCH, RELATIVE_VALUE live, COVENANT_REFINANCING (CP-3C), PORTFOLIO_DECISION (CP-6 and the QA gate), FULL_CREDIT_ASSESSMENT (CP-1A, CP-1D, CP-2E, CP-2H, CP-4C; retires NOT_YET_REACHED) — each proven, enabled, keyed and run when authorized; DISTRESSED_RESTRUCTURING held on corpus.

Phase 12: withdraw, membership, save, sign, freeze and file as governed commands with controls; Book over accepted snapshots; the analysis page naming the blocking node; a Markdown renderer with a closed element set; the journey through all of it.

Phase 13: async store and a concurrent frontier; a safe second worker in the race suite; LISTEN/NOTIFY streams and worker readiness; a signed identity assertion or mTLS with TLS in the smoke stack and the smoke stack in CI; store hygiene; gate scripts that resolve behaviour; the generated release pack, the first authorized nightly, hosted checks verified on main.

A key is authored from the documents and the owner's answer key before the run, never from what a run produced; the owner confirms every material figure. A live run needs its own authorization naming provider, model, endpoint tag, reasoning effort, ceiling and window, runs only through scripts/qualify.py, and keeps its database and blob root until its verdict is signed or its refusal recorded. Nothing is described as QUALIFIED without a signed verdict over a complete snapshot on the current build and prompt identity.

Prefix shell commands: env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL -u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT -u CAOS_REQUIRE_PROVIDER.

Use TDD and ordinary review per task. Full gate once per integration wave. After committing and remediation, pass the 800-line gate against the actual PR base, with the standing over-cap exception only for a commit whose split was attempted and proven impossible. At each phase end run the complete gate, one confidence review on Fable 5.1 xhigh, remediate and retest, then one adversarial audit on Fable 5.1 xhigh. No rewrite tournaments. Record acceptance in the tracked handoff with every pathway's state, then continue through the next phase until Phases 7–13 are complete. Pause only for a failed gate, missing explicit authorization (spend, bundle edit, dependency, push, hosted write, deployment) or a genuine blocker.
