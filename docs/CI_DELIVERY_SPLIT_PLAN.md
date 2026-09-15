# CI-compliant delivery split

Current GitHub `main` is `c032df8` (PR #160). Repository ruleset 22701406 requires pull requests and the checks `lint`, `types`, `test`, `security`, `size`, `frontend`, `postgres`, `sonarqube`, and `SonarCloud Code Analysis`; the repository's local size gate limits a PR to 800 counted lines.

`git rev-list gh-origin/main..0c02eb4` contains 299 commits / 123,065 commit-counted changed lines. It is an integration stack, not a merge candidate. Replay dependency-ordered task slices from the Phase 3.1c boundary, run the full local gate on every candidate, and open each PR only after `make check-size` against its exact current base passes. Do not force-push or alter rulesets.

## Commits requiring source-level decomposition

These cannot be replayed as one PR because each alone is over the ceiling:

| Commit | Lines | Required split boundary |
|---|---:|---|
| `2f807b4` | 10,494 | Separate generated demo fixture/wire output from Model view behavior; then split behavior by route/page. |
| `ca996f6` | 8,497 | Split Run view by selector/graph/read model and generated artifacts. |
| `f05d414` | 5,951 | Split Analysis transport removal from each rendered handoff/evidence view. |
| `b90ae3d` | 2,145 | Split Directory from Upload view. |
| `9bf20b2` | 1,953 | Split immutable revision persistence from filing behavior and regressions. |
| `c48219d` | 1,786 | Split parser/reconciliation behavior from fixtures/regressions. |
| `be6710a` | 1,621 | Split retired-executor deletion from adapter migration. |
| `5986b60` | 1,253 | Split plan/handoff documentation by topic. |
| `c88167d`, `6e8c6ea`, `59738f9`, `e11392c`, `5e06b92`, `75f6810` | 809–903 | Decompose by schema/store/API/test slices before opening. |

## Release sequence

1. Rebase a disposable delivery branch onto the then-current `gh-origin/main`; do not mutate `codex/execute-repair-plan` until each selected patch is proven non-duplicate.
2. Deliver Phase 3.1c–3.4 in dependency order, then Phase 4, then Phase 5, then Phase 6 offline. Each PR must include only its own migration, API/wire, UI and regression changes, remain ≤800 lines, and pass all required local checks.
3. Refresh GitNexus after each merged source slice; run the phase-end confidence and adversarial reviews only when that phase's final PR is complete.
4. For Phase 6 release acceptance, obtain explicit live-provider authority, persist the result for every advertised route, and verify the exact PR's hosted checks. The live call and GitHub changes are not implied by this plan.

This plan is a delivery map, not approval to push, open PRs, change branch protections, or make paid provider calls.
