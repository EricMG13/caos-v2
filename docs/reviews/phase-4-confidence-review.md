# CAOS Repair Phase 4 — whole-phase confidence review

- **Model:** Claude Opus 5 (`claude-opus-5`).
- **Effort:** `xhigh`, set with the app's session-effort control and read back
  from the session record (`effort: "xhigh"`, 2026-09-14T17:38:40Z) before this
  review began; ultrathink applied, as the user asked for end-of-phase reviews.
- **Target:** `codex/execute-repair-plan`, range `8a64704..5657ade` (Phase 3
  acceptance to the Phase 4 exit candidate, 72 commits, 230 files). The
  candidate passed a complete `make check` (backend 2569, races 20, frontend
  unit 235, workbench 84, image 8, three-engine journey 39).
- **Method:** `~/.claude/skills/confidence-review/SKILL.md`. Code and callers
  were read in source; the one confirmed defect was reproduced by a failing
  test before it was fixed.

## Least confident about (ranked), and what was found

1. **A worker fault that is neither a refusal nor a store error.**
   `work_once` (`server/engine/worker.py`) caught `_Stopping`, `psycopg.Error`
   and `Refusal`; anything else escaped it and `run_worker`, killing the process
   with the claim still `CLAIMED`. `claim_run` picks an expired claim in
   `requested_at` order, so after every 300 s lease expiry the same run was
   claimed first and the same fault recurred: one deterministic fault (a vendor
   validator raising, a programming error on one run's data) blocked every run
   behind it. **CONFIRMED P2.** *Reproduced:*
   `test_an_unexpected_fault_parks_the_run_and_the_worker_goes_on`, with a
   deterministic provider whose call raises `RuntimeError`, failed with the
   exception escaping `work_once`. *Fixed* (`b8d905f`): the run is stopped
   `INTERNAL_FAULT` (the retry command requeues it, and replay recovers any
   billed answer), only the fault's class name is written (its message may
   quote a document), and `work_once` returns so the loop polls on. The test
   passes with `tests/test_worker.py` and `tests/test_postgres_races.py`.
2. **The edge guard and identity switch** (`server/api/edge.py`,
   `identity.py`). *Investigated:* the token is compared with
   `hmac.compare_digest`, exactly one must be present, and it is removed from
   the scope before a refusal or the app runs. The role header is believed only
   with the switch set and no edge token, and boot refuses the pair. Dev mode
   needs both socket ends loopback and one loopback `Host`, so a published port
   on a tokenless image answers only health and a DNS-rebinding page is refused
   by its `Host`. A repeated or `_`-lookalike identity header is 401. Unsafe
   `/api` methods need `Sec-Fetch-Site: same-origin` or an allowed `Origin`.
   Security headers are set on `http.response.start`, so streaming responses
   and the guard's own 500 carry them. *Fine.* The static shared token and the
   undetectable non-stripping edge are recorded in the ledger.
3. **Command idempotency under concurrency and revocation**
   (`server/store/commands.py`, `server/api/commands/*`). *Investigated:* a
   replay or reused key is answered before any write; a case-scope twin waits
   at the case lock and finds the first receipt; a nil-scope (create case) twin
   blocks on the receipt's primary key, inserts nothing, rolls back its own
   case row and replays. `governed_write` rechecks standing under the case lock,
   and a `NOT_AUTHORISED` there answers `CASE_NOT_FOUND`. Admission checks the
   receipt before extraction, extracts with no transaction or case lock, and
   bounds the stream to its declared length. *Fine.*
4. **Worker lease fencing and terminal transitions** (`server/store/work.py`,
   `runs.py`). *Investigated:* every terminal transition runs `require_lease`
   under `lock_run` and closes the work row in the same unit; `claim_run`
   re-checks expiry on the locked row; `request_cancel` ends only an unheld
   (QUEUED or STOPPED) run and leaves a claimed run to its holder;
   `requeue_run` refuses a cancel-requested run. *Fine.* The I6 double-pay and
   trickling-response residuals stay recorded.
5. **Evidence pages** (`server/api/reads/evidence.py`, `server/evidence/page.py`).
   *Investigated:* identity, then READER standing (`CASE_NOT_FOUND`), then the
   run's case (`RUN_NOT_FOUND`), then one query joining the run's pinned source
   set to live sources with matching document and extraction identity. Every
   source or page failure, including a store error and a child refusal, is one
   `PAGE_NOT_AVAILABLE` raised outside any `except`, so no text is chained
   (invariant 2). *Fine.* A store fault reads as 404 there rather than 503;
   that is the fail-closed direction and is recorded here, not changed.
6. **The case stream** (`server/api/stream.py`, `app.py`). *Investigated:*
   standing is checked before the first byte and rechecked before each frame
   and each poll; `?run=` must be the case's; a marker ahead of the heads
   resumes from the heads. The idle-stream thread hold the journey exposed was
   fixed before this review (`0db50fa`, keepalive per poll). *Fine.*
7. **The site dispatcher and image** (`server/api/site.py`, `Dockerfile`,
   `compose.smoke.yaml`). *Investigated:* `EdgeGuard` is outermost; `/api`
   routes to the app before any file; static serving is GET/HEAD with no
   directory listing, and a path or symlink resolving outside the root is 404.
   The image runs as uid 10001 with `--no-proxy-headers`. The smoke Compose
   file's database password is a tmpfs, no-host-port smoke credential, not a
   deployment secret. *Fine.*
8. **Unauthenticated health.** `/api/health` returns only typed probe codes
   and a timestamp, with no identity, token or request I/O. *Fine.*
9. **Worker price configuration.** `price_from_environment` refuses a
   malformed, NaN, infinite or negative price through `worst_case`, and `main`
   exits 2 with the code only. *Fine.*
10. **Frontend command keys and approval binding.** Covered by the per-task
    reviews of 4.2i and 4.2j and their remediation: one idempotency key per
    intent, reused only for a same-body offline retry; approval sends exactly
    the digests of the preview on screen, and a pinned-input change clears it.
    *Fine* (re-read in source for this review).
11. **Size gate.** Per commit over the range with `scripts/check_pr_size.py`'s
    exclusions, five commits exceed 800 changed lines. Three are
    deletion-dominated, which the user allowed: `b90ae3d` (1,288), `f05d414`
    (1,994) and `59738f9` (871). Two are not: `5e06b92` (4.2d, 810) and
    `75f6810` (4.2e, 809). **Open P3:** each is 9–10 lines over, and the branch
    is shared with Codex, so history is not rewritten; recorded here.

## By design / already recorded

- A deterministic fault now stops a run instead of killing the worker; a
  process-level failure (the database gone, `SystemExit`) still ends the loop
  or backs off as before.
- `--limit-concurrency 32` counts every open stream (ledger).
- An evidence page holds its read transaction while the frame is extracted
  (ledger).
- The edge token is static and shared (ledger).

## Remediation

`b8d905f`: the worker parks an unexpected fault `INTERNAL_FAULT`, with its RED
test. Re-verified with `tests/test_worker.py`, `tests/test_postgres_races.py`,
ruff, mypy and `check_tested`, then the backend wave gate.
