# CI-compliant delivery split

GitHub `main` is `01c3724` (PR #283, "feat: render Report v1 saved payload (4.1l)"), read on 17 September 2026. The entry this paragraph used to name, `c032df8` (PR #160), is 123 merges behind that; the count and the ceiling below were restated at the same reading. Repository ruleset 22701406 ("main gates", enforcement `active`) requires pull requests and the checks `lint`, `types`, `test`, `security`, `size`, `frontend`, `postgres`, `sonarqube`, and `SonarCloud Code Analysis`; the repository's size gate limits a PR to 800 counted lines.

`git rev-list --count gh-origin/main..codex/execute-repair-plan` is 353 commits (150 the other way, since every merge is squashed). What is still undelivered is smaller than that history: the two-dot difference between `main` and the branch, under the size gate's own exclusions, is **13,036 counted lines over 173 files** — the Phase 6 qualification stack (open PRs #284–#296) and the audit-remediation wave, not 123,065 lines. It remains an integration stack, not a merge candidate. Replay dependency-ordered task slices, run the full local gate on every candidate, and open each PR only after `make check-size` against its exact current base passes. Do not force-push or alter rulesets.

## Commits requiring source-level decomposition

These cannot be replayed as one PR because each alone is over the ceiling. **Landed as** names the merged PRs that carry the commit's content on `main`, read from GitHub on 17 September 2026; the hosted `size` figure, where it is worth stating, is the one the `size` job printed for that PR, never a local run.

| Commit | Lines | Required split boundary | Landed as |
|---|---:|---|---|
| `2f807b4` | 10,494 | Separate generated demo fixture/wire output from Model view behavior; then split behavior by route/page. | #278 (backend read) + **#282** (4.1k render). The split held: 10,464 of the 10,494 lines were the regenerated `frontend/fixtures/model.json`, which the gate excludes, and that blob on `main` is byte-identical to this commit's. `frontend/scripts/fixture-routes.mjs` still differs — the demo wiring is pending. |
| `ca996f6` | 8,497 | Split Run view by selector/graph/read model and generated artifacts. | #223 (node reasons) + **#224** (Run view on the v1 wire) |
| `f05d414` | 5,951 | Split Analysis transport removal from each rendered handoff/evidence view. | #226 (reads v1) + #228 (legacy dual path removed) + **#230** (ten dead views deleted) |
| `b90ae3d` | 2,145 | Split Directory from Upload view. | #221 (Directory) + **#222** (Upload) |
| `9bf20b2` | 1,953 | Split immutable revision persistence from filing behavior and regressions. | **#275** + #276 (event identity, gate readiness, receipt binding) + #279 (exact receipts). #275 merged over cap: its hosted `size` reported 1,965 and failed, under the standing proven-indivisible exception. |
| `c48219d` | 1,786 | Split parser/reconciliation behavior from fixtures/regressions. | **#272** (host skill and calculator authority, hosted `size` 234) + #273 (accept CP-CF only with reconciled anchored owner inputs, 678). The unsplit attempt, #271, was closed with hosted `size` 1,482. |
| `be6710a` | 1,621 | Split retired-executor deletion from adapter migration. | #173 + #176 + #177 (superseded tests dropped first) then **#182** (executor and envelope retired) |
| `5986b60` | 1,253 | Split plan/handoff documentation by topic. | Pending. `docs/**` is excluded from the counted size, so the documentation half needs no split and has been delivered piecemeal by the PRs that carried it; the counted half — `CLAUDE.md`, `README.md`, `.github/pull_request_template.md` — still differs from `main`. |
| `c88167d` | 809–903 | Decompose by schema/store/API/test slices before opening. | #132 (verify and preserve immutable route identity) |
| `6e8c6ea` | 809–903 | as above | #133 (pin complete immutable run inputs) |
| `59738f9` | 809–903 | as above | #245 (case event stream beside the run tail) + **#247** (run tail retired) |
| `e11392c` | 809–903 | as above | #130 (preserve immutable source-set versions) |
| `5e06b92` | 809–903 | as above | #249 (create-case half) + **#250** (admit-sources half) |
| `75f6810` | 809–903 | as above | #251 (create-run and pin-input) + **#252** (gate preview and approval) |

Twelve of the fourteen are fully landed. `2f807b4`'s demo wiring and `5986b60`'s counted half are the two that are not.

## What is still in flight

Read from GitHub on 17 September 2026, PRs since #258:

- Merged and on `main`: #259–#267, #269, #270, #272–#279, #282, #283. Every one of these carries nine-of-nine required checks as GitHub reported them, with one exception: #275 merged with `size` red at 1,965 counted lines.
- Merged into another PR's branch, not onto `main`: #281 and #285. Their head commits are gone from the remote, so `gh pr checks` answers "no commit found on the pull request" for both and their hosted results cannot be re-read.
- Closed unmerged: #271 (replaced by #272 + #273), #280 (801 counted, one line over), #289 (replaced by #291).
- Open, stacked: #284 → #286 → #287 → #288 → #290 → #291 → #292 → #293 → #294 → #295, plus #268 and #296 on `main`. #296's hosted `size` is red at 879.

Delivery therefore closes on `main` when the #284–#295 stack and the audit-remediation wave have merged; the remediation wave has no branch on the remote yet.

## Release sequence

1. Rebase a disposable delivery branch onto the then-current `gh-origin/main`; do not mutate `codex/execute-repair-plan` until each selected patch is proven non-duplicate.
2. Deliver Phase 3.1c–3.4 in dependency order, then Phase 4, then Phase 5, then Phase 6 offline. Each PR must include only its own migration, API/wire, UI and regression changes, remain ≤800 lines, and pass all required local checks.
3. Refresh GitNexus after each merged source slice; run the phase-end confidence and adversarial reviews only when that phase's final PR is complete.
4. For Phase 6 release acceptance, obtain explicit live-provider authority, persist the result for every advertised route, and verify the exact PR's hosted checks. The live call and GitHub changes are not implied by this plan.

## Measuring a candidate's counted size

`scripts/check_pr_size.py` diffs `<base>...HEAD`; the hosted job diffs `origin/<base_ref>...HEAD` **against the pull request's merge ref**. The two disagree whenever a predecessor was squash-merged, because the squash leaves the predecessor's content in `main` without its ancestry, so a local three-dot diff re-counts it. #263 (790 hosted, 1,555 locally), #266 (124 against 942), #272 (234 against 1,716) and #282 (700 against 1,523) are all that shape. The hosted number is the gate; a local measurement is a forecast of it, and only the hosted `size` job's `changed lines:` line may be recorded as a result.

This plan is a delivery map, not approval to push, open PRs, change branch protections, or make paid provider calls.
