# CAOS Repair Phase 4 — whole-phase adversarial audit

- **Model:** Claude Opus 5 (`claude-opus-5`).
- **Effort:** `xhigh`. The session record read `effort: "xhigh"` at
  2026-09-14T17:49:56Z, before this audit began; ultrathink applied.
- **Target:** `codex/execute-repair-plan`, range `8a64704..e2c4989`: Phase 4
  through the confidence-review remediation, run after the backend wave gate
  passed on `e2c4989` (2,570 backend tests passed; the race tests passed).
- **Method:** `~/.claude/skills/adversarial-reviewer/SKILL.md`, with three
  personas: Saboteur, New Hire and Security Auditor. Every finding was checked
  against source; the P1 was reproduced by a failing test before its fix.

## Verdict: CONCERNS

One P1 (promoted because two personas raised it), fixed; one P3 fixed; two P3
recorded. No P0.

## Findings

### P1: a pack's extraction had no deadline of its own (Saboteur and Security Auditor)

`server/evidence/ingest.py` `_extract` gave each document
`time.monotonic() + limits.max_seconds` (60 s) and nothing bounded the pack.
`admit_sources` (`server/api/commands/cases.py`) runs `prepare_pack` in the
request, so an authenticated writer's pack of 50 documents that each run close
to the deadline (pathological PDFs under the 20 MiB and 100 MiB byte caps)
held one request, its threadpool thread and one of the image's
`--limit-concurrency 32` slots for up to 50 minutes. About 32 such uploads, from
any writer on any case, refuse every other request with 503.

*Reproduced:* `test_one_deadline_bounds_the_whole_pack_not_each_document`
records the deadline handed to each extraction under a 0.12 s pack budget. It
failed first because no pack bound existed (`AdmissionLimits` had no such
field).

*Fixed* (`420f628`): `AdmissionLimits.max_pack_seconds` (300 s, the edge's idle
timeout) and one pack deadline that caps every document's deadline, so a pack
past it refuses `SOURCE_EXTRACTION_TIMEOUT` with nothing written. Recorded as a
dated §51 refinement.

### P3: the site's deep-link sections were an untested copy (New Hire)

`server/api/site.py` `SECTIONS` restates `frontend/src/wire/shared.ts`'s
`SECTIONS` by hand. A section added to the workspace and not to the dispatcher
would load in development and answer 404 as a deep link in the production image,
and nothing would fail. *Fixed* (`1ca4989`):
`test_the_deep_link_sections_are_the_workspace_sections` reads the TypeScript
list and requires equality.

### P3: `/api/health` answers everyone, token or not (Security Auditor)

`server/api/edge.py` exempts `GET|HEAD /api/health` from the token, loopback and
Host checks in both modes, so anything that reaches the listener learns whether
the store, bundle and blob root probe `OK` and which typed code each fails with
(for example `STORE_SCHEMA_DRIFT`). *By design:* a load balancer must reach
readiness without the edge's secret (§53.8), the body carries typed codes only
with no identity, path, version or timing, and the listener is private by the
edge contract. *Recorded here;* an operator publishing the listener exposes
readiness, not data.

### P3: the smoke stack's database password is in the tracked Compose file (Security Auditor)

`compose.smoke.yaml` spells out `local-smoke-only` for a PostgreSQL on tmpfs
with no host port, in its own Compose project. *By design* for a disposable
local proof. The risk is copying the file into a deployment, which the README
and §53.11 describe as smoke-only. *Recorded here.*

## Checked and sound

- **Worker (Saboteur).** Every run write is fenced by the lease token under
  `lock_run`; a lost lease never accepts; cancel of a claimed run is left to its
  holder; an unexpected fault now parks the run (`b8d905f`) instead of killing
  the worker with the claim held.
- **Commands (Saboteur).** Concurrent twins roll back and replay; a refused
  request burns no key; standing is rechecked under the case lock; the upload
  stream is held to its declared length before parsing.
- **Edge and identity (Security Auditor).** Constant-time token comparison;
  the token is stripped before any other code runs; the role header is never
  believed with a token set; repeated and lookalike identity headers are 401;
  cross-site unsafe requests are refused on Origin and `Sec-Fetch-Site`.
- **Evidence (Security Auditor).** No page text on any refusal path; pinned,
  live, identity-matched sources only.
- **Stream (Saboteur).** Standing rechecked per poll and per frame; a
  disconnected idle stream releases its thread within one poll (`0db50fa`).
- **Frontend (New Hire).** Wire documents validated whole and bound to their
  case and run; approval sends exactly the previewed digests; command keys are
  per intent.

## Remediation and re-verification

`420f628` (pack deadline, with its RED test and the §51 refinement) and
`1ca4989` (section list pinned). Re-verified with
`tests/test_admission_limits.py`, `tests/test_ingestion.py`,
`tests/test_pdf_extraction.py`, `tests/test_case_commands.py`,
`tests/test_site.py`, ruff, mypy and `check_tested`, then a complete
`make check` on the final candidate.
