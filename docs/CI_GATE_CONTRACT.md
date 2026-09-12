# CI gate contract

Observed read-only on 12 September 2026 against
https://github.com/EricMG13/caos-v2 at
`26d7ee99f6c90396ddb5f7c3614cdd733af4ed76`.

## Hosted merge rules

Active repository ruleset [main gates](https://github.com/EricMG13/caos-v2/rules/22701406)
targets the default branch. It requires a pull request, prohibits deletion and
non-fast-forward changes, has no bypass actors, and reports that the current
user can never bypass it. Required checks are strict (branch up to date):

- `lint`
- `types`
- `test`
- `security`
- `size`
- `frontend`
- `postgres`
- `sonarqube`
- `SonarCloud Code Analysis`

Required approving review count is zero; code-owner review, last-push approval,
stale-review dismissal and thread resolution are not currently mandated by
this ruleset. This does not waive the implementation plan's review gates.
Merge, squash and rebase are allowed. The legacy branch-protection endpoint
returns 404; protection is supplied by the active ruleset, not absent.

Do not change rules, required checks, thresholds, scanner exclusions or action
pins to make a failing change pass. Hosted statuses must be verified against
the exact eventual PR head; local checks do not post those statuses.

## Workflow obligations

`.github/workflows/ci.yml` is binding. In particular:

- Wheels-only, fully hashed Python installs; Python 3.14 application/dev and
  Python 3.12 security toolchain.
- Ruff lint/format, vocabulary/tested checks, strict mypy.
- Full PostgreSQL-backed tests, coverage report and scanner floor, I/O budget
  checks; a separate real two-connection PostgreSQL race job.
- Bandit with zero parse errors and claimed-file coverage; dependency audit
  across every lock; gitleaks. Zero scanned files is failure.
- Sonar analysis imports coverage and needs the hosted quality-gate result.
  The live `qualitygates/project_status` endpoint confirms these new-code
  conditions: reliability, security and maintainability ratings must each be
  1 (A); coverage at least 80%; duplicated-line density at most 3%; security
  hotspots reviewed 100%. Preserve existing measurement scope: frontend and
  workflow files are analyzed but currently excluded from coverage measurement.
  Baseline main reported OK, 97.0% new coverage, 0.0% new duplication, all three
  ratings 1, and 100% hotspots reviewed. Its new-code period was
  `previous_version` starting 2026-09-10T05:38:51+0000. Those baseline values
  are observations, not evidence that a later PR meets the same conditions.
  The selected-gate administration endpoint returned 403 without credentials;
  the thresholds above are the conditions in the publicly readable latest
  analysis, not a claim of administrative configuration access.
- Size: at most 800 added plus removed lines per PR, with exactly the existing
  workflow exclusions for locks, requirements text, vendor, docs and fixtures.
  A sequence of small commits in one oversized PR does not satisfy this rule.
- Node 24, `npm ci --ignore-scripts`, frontend lint/types/unit/build, nine
  exported deep links, pinned Playwright browser install, accessibility and
  workbench checks. Fixture checks are additional to, not replacements for,
  the plan's real-API journey.
- Image build, Trivy scan coverage and no fixable HIGH/CRITICAL findings.
  `image` is not in the hosted required-check list but remains a workflow and
  plan obligation.
- Live provider job is scheduled/dispatched, never on push/PR. Do not invoke
  paid tests or workflow dispatch without explicit spend authorization.
- Preserve action SHA pins, job timeouts and superseded-run cancellation.

Existing CI run 34695306468 succeeded for baseline engineering/image jobs;
the later run 34695743108 was cancelled. Neither is evidence for new changes.
The `size` check was skipped on the main push because it runs only on PRs.

## Local execution and review

The repair plan strengthens local gate parity; it does not loosen hosted CI.
Use `confidence-review` after code changes, prioritizing high-risk sections,
with actual extra-high (`xhigh`) executor reasoning. Confidence review replaces
rewrite tournaments; no further tournaments are required. Run the adversarial
audit only at phase completion, over the full phase diff and affected callers,
also with actual `xhigh` reasoning. The user's current policy in
`docs/REPAIR_PLAN.md` supersedes older blanket skill cadence and historical
max-reasoning requirements. Record risk scope, executor settings and evidence
in the execution ledger. Keep external writes and live spend separately
authorized.

## Complete offline gate

`make check-fast` is partial and intentionally excludes PostgreSQL, browser,
security and image proof. It must not be described as complete.

```sh
./frontend/node_modules/.bin/playwright install
TRIVY=/path/to/trivy IMAGE=caos-workbench:check make check
PR_BASE=<exact-pr-base> make check-size
```

The complete command requires the configured test PostgreSQL to be reachable
and forces skipped database suites to fail. It runs backend lint, types,
coverage, I/O and security; the separate two-connection race suite; frontend
lint, types, fixture unit tests, production build/deep links, explicit demo
build, the full accessibility matrix and workbench; and the repaired image
gate. These ecosystems run sequentially even under
`make -j`. Provider credentials are removed and the paid suite is not selected.

The separate PR-only `check-size` gate has no guessed default: `PR_BASE` must be
the exact caller-supplied PR base. It uses the hosted exclusions and 800-line limit and fails closed for
an absent or invalid base or failed diff. Splitting an oversized cumulative
branch into commits does not make it eligible. Local completion cannot post or
imitate required GitHub or SonarCloud statuses; those remain mandatory on the
exact future PR head.

Ordinary `npm run dev` proxies `/api` to the real loopback API at port 8000;
ordinary production preview has no fixture middleware. `dev:demo`, `build:demo`
and `preview:demo` opt into read-only fixtures and a visible demonstration
label. Their `dist-demo` artifact is separate from production `dist`. Real
API/browser/PostgreSQL acceptance remains later-phase work; fixture coverage
proves presentation only.
