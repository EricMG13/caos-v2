# AI code quality — controls

Most of this repository will be written by an AI agent. CodeRabbit's *State of
AI vs Human Code Generation* (470 PRs: 320 AI-co-authored, 150 human-only)
measured what that does to a codebase: **10.83 issues per AI PR against 6.45
for human-only**, ~1.7× overall.

This document maps each measured failure mode to a control that is enforced by
a tool, not by intention. A control nobody runs is not a control.

---

## 1. The measured failure modes, and what stops each

| Failure mode | Measured | Control | Enforced by |
|---|---|---|---|
| **Logic & correctness** | +75 % | Test-first for every calculator, state transition and money path. A failing test exists before the implementation. | `superpowers:test-driven-development`; CI refuses a PR whose new public function has no test |
| **Readability** | 3× | Function length and complexity ceilings; ordinary task review rejects needless complexity | `ruff` (C901, PLR0912/0913/0915); exact-range task review |
| **Error handling** | ~2× | Typed refusals only. No bare `except`, no `except Exception` without re-raise, no `str(exc)` reaching a log or a wire response | `ruff` (BLE, TRY); the observability test that drives a sentinel document through real ingestion |
| **Security** | 2.74× | Static analysis, dependency audit, image scan, and a route-level actor matrix that drives every endpoint as nine different actors | `bandit` (pinned 3.12 — see §4), `pip-audit`, Trivy, `gitleaks`; extend the HTTP actor matrix with repaired endpoints in repair Phase 4 |
| **Formatting** | 2.66× | Format authored files and verify before acceptance | `ruff format` in pre-commit/CI; `prettier --check` in frontend lint/CI; automatic Claude hook on edit (`scripts/claude_hook.py`) |
| **Naming inconsistency** | ~2× | One glossary. Every domain term in `CONTEXT.md`; a check that new identifiers do not introduce a synonym for an existing term | `CONTEXT.md` + `scripts/check_vocabulary.py` |
| **Concurrency & dependencies** | ~2× | No new dependency without a dated decision entry. Fully pinned, hashed locks. Every governed race proven on two independent Postgres connections | `test_dependency_pins.py`, `--require-hashes`, `test_postgres_races.py` |
| **Performance — excessive I/O** | **~8×** | A declared I/O budget per request path, asserted in tests. N+1 detection on every list endpoint | `scripts/io_budget.py` + `test_io_budget.py` |
| **Critical/major severity** | 1.4–1.7× | Ordinary review per task; at phase completion, self-doubt enumeration then hostile review | `confidence-review` and `adversarial-reviewer` at the phase boundary; SonarQube Cloud on the PR (`docs/DECISIONS.md` §15) |
| **Overall volume** | 1.7× | Small PRs. One concern per PR, hard cap on changed lines | CI size gate |

**Excessive I/O deserves its own note.** It is the largest single multiple in
the report (~8×) and the old CAOS tree had exactly this defect: evidence blocks
lived in one JSON column, so `read_evidence` parsed every block of a source on
every call — 17 ms per read at the ceiling, ~1.4 s per run. `SYSTEM_SPEC.md` §2
fixes the shape (`source_blocks` keyed by `(source_id, block_id)`); the I/O
budget test is what stops it coming back.

---

## 2. Repository controls

### `.claude/settings.json` — hooks read the event on stdin

Both hooks run `scripts/claude_hook.py`, which reads the JSON event Claude Code
passes on stdin (`tool_input.command` / `tool_input.file_path`). The earlier
inline commands read `CLAUDE_FILE_PATHS` and `CLAUDE_TOOL_INPUT_command`, which
are never set, so they enforced nothing
([PLAN_ADVERSARIAL_REVIEW.md](PLAN_ADVERSARIAL_REVIEW.md) R2).

- **Guard (PreToolUse, Bash).** Refuses force pushes (`-f` in any cluster,
  `--force`, `+ref`), hook-bypassing commits (the long flag, or `-n` in any
  cluster), unpinned `pip install`, `printenv`, `env` run with nothing to run,
  `$OPENROUTER…` and a `.env` path other than `.env.example`. A newline ends a
  command; a command `shlex` cannot split is checked on a plain split rather
  than skipped. A malformed event refuses, and the settings command falls back
  to `python3` when the repo venv is absent (a fresh worktree) and turns a crash
  or a missing interpreter into a refusal (`|| exit 2`). It is a pattern screen,
  not a sandbox: a command built to hide its intent at run time passes.
- **Formatter (PostToolUse, Write/Edit/MultiEdit).** `ruff format
  --force-exclude` (format only, no `check --fix`) for authored Python and the
  pinned `prettier`, run from `frontend/` so its ignore file applies, for
  frontend TS/CSS; vendor, `.claude`, out-of-repo and other files are untouched.

`tests/test_claude_hooks.py` drives both, including through the real settings
command. Pre-commit and CI checks remain separate obligations.

- **No `Stop` hook.** An earlier draft of this page promised one that ran the
  changed-file tests; it was never built, and a hook that runs the suite would
  need Postgres from Phase 1 on. The gates run in pre-commit and CI instead.

### Pre-commit

`ruff`, `ruff-format`, `gitleaks`, `check-added-large-files`,
`check-merge-conflict`, `end-of-file-fixer`, `trailing-whitespace`, the
vocabulary check, the untested-definition check and the I/O-budget floor.
`scan_floors.py` needs a scanner report, so it runs in `make security` and CI.

### CI jobs

Phase numbers in this historical inventory are rebuild phases, not repair
phases. Current workflow obligations are in `CI_GATE_CONTRACT.md`.

Phase 0 ships `lint` · `types` · `test` · `security` (bandit + pip-audit +
gitleaks) · `size`. A job arrives with the code it scans (`docs/DECISIONS.md`
§11): `postgres` (two-connection races, Phase 1) · `sonarqube` (CI analysis
with coverage, Phase 1) · `provider` (one live OpenRouter call, nightly,
Phase 5) · `image` (Trivy, fixable HIGH/CRITICAL, the Dockerfile phase) ·
`frontend` (lint, tsc, unit, build, a11y, workbench smoke, Phase 9). Every job
declares `timeout-minutes`, and a superseded run is cancelled
(`tests/test_ci_hygiene.py`).

### Review

SonarQube Cloud analyzes PRs through the CI-side analysis and coverage import
(`docs/DECISIONS.md` §15); the hosted quality gate is required. Ordinary review
closes tasks. The two specialist reviews run only at the phase boundary as
specified below; historical rebuild timing is not the current cadence.

---

## 3. Skills enabled for this repository

Names are the installed invocation names; a name that does not resolve is a
control nobody runs.

| Skill | When |
|---|---|
| `superpowers:test-driven-development` | before implementing any feature or fix |
| `superpowers:systematic-debugging` | before proposing a fix for any failure |
| coordinator + isolated implementers | up to three only for disjoint task scopes; coordinator integrates and owns acceptance |
| ordinary task review | after each local implementation commit, before task acceptance |
| `confidence-review` | once at whole-phase completion, actual `xhigh` reasoning |
| `adversarial-reviewer` | once at whole-phase completion after confidence remediation, actual `xhigh` reasoning |
| `rewrite-tournament` | disabled; historical records only |
| `senior-architect` | on a specification or phase-boundary change |
| `ponytail:ponytail-review` | when a diff grows past its concern |
| `superpowers:verification-before-completion` | before reporting completion |
| `impeccable` | Audit/polish changed UI in repair Phases 4–5 when needed; reuse the accepted design, with no new redesign requirement |

For current planning, briefing and execution settings, use
[`GPT_MODEL_REASONING_MATRIX.md`](GPT_MODEL_REASONING_MATRIX.md). The
complementary plan's Claude routing is retained as dated history. Plan stress
tests and blueprint drafting do not trigger the whole-phase code-review gates.

Parallelism reduces elapsed time, not accountability: each implementer uses an
isolated worktree and test resources, receives exact ownership, and submits a
commit for ordinary range review. The coordinator serially integrates reviewed
commits and reruns affected integration gates; independent green branches are
not CI or phase evidence.

The historical workspace was designed in Claude Design (project `69d37748-8595-4309-9b06-bc5f9529a29c`,
`DESIGN.md`) with its `hifi-design` workflow. Repair work reuses that design;
a redesign is not a prerequisite.

---

## 4. Two gates that must not be "tidied"

**bandit is pinned to Python 3.12.** bandit 1.7.10 reaches for the
`ast.Constant.s` alias newer interpreters no longer provide; under 3.14 it skips
every server file and exits 0 — a green SAST gate that scanned nothing. The step
asserts the JSON report carries no parse errors and covers the whole server, so
a naive version bump fails loudly.

**A scanner that scanned nothing is a failure.** `scan_floors.py` refuses a
scanner reporting zero files. This applies to every scanning gate, not just
bandit.

**Every gate judges what this branch tracks, and nothing else.** The identifier
gates take their file set from `git ls-files` (`scripts/tracked.py`); `ruff` and
`mypy` walk the filesystem instead, so they exclude `.claude`, where the harness
keeps worktrees of *other* branches. A finding in one of those is a finding
against a different branch's code: nothing this PR can fix, and a red gate no
author can clear.

---

## 5. What these controls do not fix

The report's root causes include "AI lacking local business logic" and "poor
adherence to repository idioms". No linter detects a plausible-looking credit
calculation that is wrong. That is what the methodology bundle, the calculator
boundary and the qualification set are for — and why the invariants in
`CLAUDE.md` are non-negotiable rather than advisory.
