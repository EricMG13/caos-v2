# Adversarial review: the codebase and the Gemini audit

- **Date:** 17 September 2026
- **Base:** `codex/execute-repair-plan` at `e59ad7b`
- **Scope:** `server/`, `scripts/`, `frontend/src/`, the migrations, and every
  claim in the untracked `gemini-audit.md` (dated 15–16 September 2026)
- **Method:** three hostile personas (Saboteur, New Hire, Security Auditor)
  over the current tree; every Gemini claim re-verified against `e59ad7b` by
  five parallel read-only agents on Opus 5, each returning file:line evidence;
  complexity measured with the project's own ruff configuration
  (`--ignore-noqa`); import cycles from GitNexus; SonarCloud `main` queried
  (quality gate OK, zero open HIGH/BLOCKER).
- **Verdict:** **BLOCK** — three findings at CRITICAL after cross-persona
  promotion. None is an exploit against a correctly configured deployment;
  all three are cheap to close.

Findings caught by two or more personas are promoted one level, as the skill
requires. Preconditions are stated plainly so the promotion does not read as
alarm.

## Critical

### C1. A report read takes the case-wide write lock and holds it across unbounded I/O

`server/api/reads/reports.py:83-118`: both `GET …/report` and `GET …/committee`
call `lock_case(conn, case_id)` — `SELECT … FOR UPDATE` on `cases` — inside the
read unit, then run two unbounded reads of the audit chain (`audit_trail`, then
`verify_chain` which reads it again), two blob reads per pinned node, a full
vendor validator pass per node and citation re-anchoring, with no
`lock_timeout` on request connections. `lock_case` is the entry point of every
governed write and every run transition (`audit.py:83`, `events.py:63`,
`runs.py:102`, `budget.py:92`, `outcomes.py:349`, `ingest.py:173`).

*Failure:* any member with READ standing who keeps the committee page open
stalls admission, gate approval, the worker's `start_attempt`,
`record_outcome` and `accept_attempt` for that case for as long as the read
takes; two such readers serialise each other. No decision or ledger entry
records the lock (`git log -S` finds only the one-line commit `1e6cecb`).
Every other section read takes no lock. The digest comparison at
`reports.py:117` already detects a concurrent freeze; the lock buys nothing.
Personas: Saboteur, Security Auditor → CRITICAL.

### C2. The citation-candidate mechanism contradicts itself, is enforced nowhere, and bills unsatisfiable attempts

`server/evidence/citations.py:125-158` keeps the **three longest** anchorable
lines per page (`ponytail: three/page bounds work`), then
`invocation.py:440-445` tells the model *"Use only evidence whose host header
says `citation_candidate: true`"* **and** *"Select only evidence lines that
directly support claims you wrote."* On a filings page the three longest lines
are boilerplate, so the two sentences are jointly unsatisfiable for numeric
evidence — the phase-6 confidence review measured 93 flagged of 1,751
anchorable blocks. Nothing in `parse_response` or `verify_citations` reads the
flag, so a model that ignores it is accepted and one that obeys it is refused.
The per-block header (`citation_candidate:`, `source_id:`, `page:`) costs
~85 bytes per line — about one third of the measured 452,905-byte request —
against the 1 MiB `CONTEXT_OVER_CEILING`. A page whose lines all repeat yields
zero candidates and the prompt still demands *"Include at least one
citation"*: every attempt is called, charged and refused to the ordinal cap.
The flag also sits *inside* the `EVIDENCE` block that `_TAGGED` tells the model
is untrusted text, so a document line reading `citation_candidate: true`
renders indistinguishably. Selection runs `verify_citations` once per
delivered line inside the pre-call read unit: O(lines × tokens × words).
Personas: all three → CRITICAL.

### C3. Without an edge token, a loopback peer chooses its own role with no opt-in

`server/api/edge.py:102-107`: no `CAOS_EDGE_TOKEN` means dev mode.
`identity.py:116-118`: the `CAOS_TRUST_ROLE_HEADER` switch gates only
`x-caos-role`; the fallback path reads `x-forwarded-groups` unconditionally, so
`x-forwarded-groups: caos-admins` from any peer passing the loopback and Host
checks (`edge.py:250-253`) is ADMIN, and `x-caos-user` is any UUID the caller
names. nginx's default `proxy_set_header Host $proxy_host` forwards
`Host: 127.0.0.1:8000` and forwards hyphenated client headers verbatim, so a
same-host proxy in front of a tokenless API exposes full impersonation.

*Preconditions, stated honestly:* the operator must omit the token (README
and §53 say not to), run the API on the host rather than in the image with a
published port (`test_the_image_without_a_token_answers_only_health` proves
that case refuses), and front it with a proxy that rewrites Host to the
upstream. Gemini's "insecure default" is overstated: the default for a remote
peer is fail-closed. What is real and unledgered is that the only opt-in
switch protects nothing. The ledger entry "The API cannot tell whether the
edge stripped a client's identity" covers edge mode, not this. Fix is one
branch: in dev mode without the switch, the role is READER. Personas:
Security Auditor, Saboteur → CRITICAL.

## Warnings

### W1. Every accepted node records its outcome three times

`canonical.py:212` (authoritative, after the call), `runtime.py:438` (comment:
"this is then an exact replay"), `runs.py:215` inside `_accept`. Calls two and
three each cost six round trips, a `COMMIT`, and `cases FOR UPDATE` plus `runs
FOR UPDATE`; `_accept_artifact` then re-locks a fourth time. Idempotent, so
never wrong — but it serialises against every governed write on the case,
three times per node, and no decision sanctions it.

### W2. The pre-call read unit reads every delivered block one query at a time and re-verifies every line

`executor.py:88-97` `_delivered` runs the six-table `_RUN_BLOCK_QUERY` once per
captured block on every prompt build (and again on replay and for CP-CF);
`canonical.py:429-440` then offers every line to `citation_candidates` (see
C2). A 20,000-line pack costs 20,001 queries per node under the case lock.
Ledgered ("a batched block query when the first large PDF pack measures the
hold"); the measurement is not needed to see the shape.

### W3. Admission runs two re-planned dynamic `EXECUTE`s per token row under the case lock

`0008_frozen_evidence.sql:2-31`: `BEFORE INSERT FOR EACH ROW` on
`source_tokens` and `source_blocks`, two `format()`-built `EXECUTE`s each, no
plan cache; `ingest.py:337-358` inserts with `executemany` up to 500,000
tokens; `blobs.put` runs inside the same lock (`ingest.py:316`). Worst case one
million trigger statements while every run transition on the case waits.
Unledgered. (Gemini DE-01, confirmed.)

### W4. Five paths let a raw store error or an untyped exception escape the typed boundary

- `commands/qualification.py:100-104`: `SELECT now()`, `evidence_at` and
  `record_evidence` run outside the `try`; a `psycopg.Error` becomes FastAPI's
  default 500 with the driver message (host, role) in the log.
- `qualification/store.py:423`: `psycopg.Error` → `VERDICT_BINDING_INVALID`,
  which `_STATUS` does not map, so a failover is answered **400** — the
  reviewer is told their bindings are wrong.
- `store/runs.py:89-139` `start_attempt` has no `except psycopg.Error`, unlike
  every sibling; the caller must remember to roll back.
- `engine/worker.py:168-174`: `cancel_run` can raise `RUN_TERMINAL_STALE` or
  `RUN_NODES_UNACCEPTED`; both re-raise out of `work_once` past `main()`'s
  handler and print a traceback — the one thing `worker.py:158` exists to
  prevent.
- `store/__init__.py:184`: `apply_schema` catches `Refusal` too, so an inner
  `STORE_UNAVAILABLE` or `STORE_NOT_TRANSACTIONAL` is re-labelled
  `STORE_SCHEMA_DRIFT`; the 21 import-time `read_text` calls (`:17-119`) turn a
  missing file into a traceback rather than a typed code. The `from None`
  itself is policy (§20a) and stays; the flattening is not.

### W5. Twenty-two of the twenty-three codes served 503 are permanent, and a new code is 400 by default

`app.py:106-170`: only `STORE_UNAVAILABLE` is transient; the rest
(`BLOB_DIGEST_MISMATCH`, `HANDOFF_MALFORMED`, `ARTIFACT_RECORD_MISMATCH`, …)
invite a retrying proxy to loop; no `Retry-After` anywhere. `_STATUS.get(code,
400)` has no exhaustiveness test, so the next store-fault code silently
answers "your request was the problem" — the exact inversion the map's own
comment forbids. Three of the 503s are recorded decisions; the split between
"come back later" and "this row is corrupt" is not.

### W6. A crashed PDF child is reported as a bad document

`evidence/pdf.py:166-182`: `stderr=DEVNULL`, `env={}`, and `_answer` never
reads `returncode`; an `ImportError` in the child is `SOURCE_NOT_READABLE`,
identical to a corrupt file. §47.1 records "stderr discarded"; it does not
record that a broken interpreter is blamed on the document. Also
`pdf.py:173`: the wait is computed after `Popen`, so an expired deadline still
pays an interpreter start before the kill.

### W7. Frontend runtime races and latches

- `sections/run/controls.tsx:74-86` `useRunRefetch`: an unguarded promise; a
  slower command refetch resolving after an SSE-driven load resurrects the
  older run document.
- `controls.tsx:229-234` `CreateRunControl` refetches the new run while the URL
  still names the old one; the next event reverts the panel with no notice.
- `states/SectionBoundary.tsx:12-24` latches `RENDER_FAILED` until navigation;
  a good document 200 ms later is never shown.
- `app/Workspace.tsx:103`: `qualificationEvidence` in the region key remounts
  the body, aborts the section fetch and reopens the SSE tail for a strip that
  fetches independently.
- `evidence/EvidenceContext.tsx:84`: a render-phase `setFact(null)` keyed on a
  derived value, not a prop transition — the one of four such sites that is
  not React's documented pattern.

### W8. Dead and unserved frontend code is kept "covered" by gate-satisfying tests

Eight components (992 lines: `committee/Paper`, `ProvenanceIndex`,
`FilingLadder`, `model/ModelDetail`, `Projection`, `report/OpinionColumn`,
`ReportViews`, `RevisionEditor`) are unreachable from `main.tsx`; three are
named only by `tests/unit/helpers.test.ts`, which exists to satisfy
`check-tested.mjs`. They are the sole consumers of `wire/report.ts`,
`wire/model.ts` and `wire/committee.ts`. Book and Admin (≈895 lines with
`ledger.tsx` and `authority.ts`'s bind/release machinery) are excluded from
`ENABLED_SECTIONS`, never mount, yet `LedgerProvider` wraps every section for
Book alone. `IA_SPEC.md:13-16` still requires nine sections, so the *shells*
are spec; the implementations are not. Stale counts in `sections.ts:7-8`
("the other four"), `scripts/fixture-routes.mjs:16-17` ("six … three") and
`wire/index.ts:7-11` (names Report and Committee as unavailable).

### W9. Three artifact-verification readers, four divergences

`qualification/proof.py:255-330`, `deliverable/canonical.py:167-216`,
`methodology/canonical.py:816-921` implement the same ten-step pipeline
(~160 lines) and differ in: `MODEL_MODULE` vs thirteen `"CP-CF"` literals plus a
second constant `HOST_MODULE`; `TokenIndex` shared in proof but re-read per
node in the deliverable reader (under C1's lock); no re-anchoring in the
methodology reader (§42.4, deliberate); and `record_authority_matches(...,
verify=True)` in two readers but the cached default in the third.

### W10. Copy-pasted transaction and request boilerplate

Seventeen byte-identical eight-line commit/rollback blocks across
`server/store/` (`execution_reads` already shows the shape for reads);
`_require_uncancelled` re-spelled in `budget.py:92-95`; the attempt
revalidation query written twice (`budget.py:98-106`, `outcomes.py:350-358`);
the governed-command envelope three times in `commands/runs.py` while
`commands/execution.py:171-210` holds the helper privately; UUID path parsing
nine times, with `CasePath` homed in `reads/upload.py` and imported by six
unrelated modules; six visibility query shapes, five of them accidental.

### W11. The argument-count control is suppressed at scale

Fifty-two `# noqa: PLR0913`; at ruff's default every one is load-bearing, so
the gate `docs/AI_CODE_QUALITY.md` names is green by suppression. The real
targets are one signature repeated four times with ten parameters
(`accepted_projections`, `accepted_handoff`, `_verified_accepted`,
`_accepted_record`) and `build_handoff_prompt` (10). Nothing pins the count.

### W12. Private cross-package imports and cycles

`from server.evidence.ingest import _digest` in three `server/store` modules;
`from server.methodology.handoff import _strict_json` in `forecast.py`. Six
backend import cycles held apart by function-local imports
(deliverable/canonical↔revisions, evidence/extract↔pdf,
ingest→store→extraction_integrity→ingest, forecast↔handoff, harness↔store,
budget→work→outcomes→budget) and one frontend cycle
(CitationChip→EvidenceContext→MetricPassport). Five canonical-JSON flag sets
exist, but every digest is produced and verified by the same function, so
no hash can drift; `allow_nan` defaults to `True` on the signed payload,
receipt, audit and matrix digests (a NaN would emit non-JSON).

## Notes

- N1. `_TAGGED` (`invocation.py:423`) says markers "end in the tag"; every real
  marker embeds it mid-line. `_CP0_FINAL_CHECK` is appended with no marker;
  HOST-PERFORMED STEPS, UPSTREAM, CITATION REGISTER, FORECAST EXTENSION and
  FINAL CHECK have no END marker. Gemini's "put the final check in the
  preimage" is circular (the check contains the tag) and unnecessary: the
  guarantee is about markers, and a document cannot contain its own digest.
- N2. `case_members` has no `(user_id)` index; the directory listing
  (`members.py:119-131`) scans it. The other five indexes Gemini proposed serve
  no query or are already served.
- N3. `scripts/dev_doctor.py` and `.env.example` omit `CAOS_MODEL_PRICE`,
  `CAOS_LIVE_BUDGET_CEILING`, `CAOS_SITE_ROOT`, `CAOS_EDGE_TOKEN`,
  `CAOS_PUBLIC_ORIGIN`; the worker exits 2 with the bare token
  `PROVIDER_NOT_CONFIGURED` for unset, wrong-model and malformed alike.
- N4. `verify_package.py:168-176`: `sys.argv[1]` with no usage; a missing
  argument is `UNREADABLE`.
- N5. `invocation.py:653` `named_objects` and `:851` `extractor_identity` call
  `json.loads` unguarded on the scheduling path (`_catalog` guards the same
  read); `handoff.py:484` `_quoted` is a second unindexed linear scan inside
  the post-call read unit, acknowledged in a comment but not ledgered.
- N6. `_catalog` is byte-identical in `methodology/canonical.py:127` and
  `api/commands/runs.py:118`; `deliverable/host.py` has zero production
  callers and both tests alias it to `render`; `reads/run.py:293` recomputes
  `route_digest` that `resolved_route` verified one call earlier; two
  hand-written `ResolvedRoute` serialisers.
- N7. Frontend duplicates: `stamp`, `scrollArtifact`, `Values`/`List`,
  `bodyOf`, `offlineMessage` (verbatim); `shortDigest`/`abbreviate` disagree on
  the threshold (16 vs 12); `NewCase`/`AdmitSources` carry ~58 lines the
  `useCommand` hook mostly covers; `scripts/check-tested.mjs` `resolveGit` is
  the weaker of two copies (no executable check, no `.exe`).
- N8. `chrome/compose.ts:55` passes `markDisabled(null)`, so the seven served
  sections render `sect off` (light weight, blank state) and the two
  unavailable ones at full weight; `requirePageIdentity` is exported and
  tested but `transport.ts:283-296` reimplements it; nine `as unknown as
  AnyView` casts erase the per-section body type; `later()` exists only for
  declaration order; `forwardRef` on React 19 with no ref consumer; `<th>`
  without `scope` in `ModelSection`; `NewCase` submits from a `div`;
  `@tailwindcss/vite` under `dependencies`.
- N9. Edge: a 404 under `/assets/` is cached `immutable` for a year
  (`edge.py:290-297`); `StaticFiles` is constructed per request
  (`site.py:91`); the verdict route is absent from the actor matrix table;
  `reads/reports.py:51,66` pass seven positionals of which two are adjacent
  UUIDs; `reads/run.py:127` declares the path before the actor; `GET
  /api/v1/qualification/{sha}` lets any ANALYST learn which digests exist (by
  design). No `Strict-Transport-Security` (the terminator's job; §53.6 does not
  say so).
- N10. `Execution.lease` defaults to `None` on the shared dataclass;
  `events.py:52-69` `lock_run`'s `RUN_NOT_FOUND` leaves `cases FOR UPDATE`
  held until the caller rolls back; `extraction_integrity.py:63,87` re-derives
  block ids a second way (frozen v1 verifier, by design).

## Gemini claim ledger

| Gemini ref | Claim | Verdict | Basis |
|---|---|---|---|
| 1.1 / 5.1 / 14 P2 | `apply_schema` masks cause with `from None` | DELIBERATE (§20a) + W4 for the `Refusal` flattening | Cause suppression is policy; `from exc` would leak the driver message. Flattening inner codes is the real loss. |
| 1.2 / 5.2 / 14 P6 / ADR-03 | Migration 17 guard skipped on fresh install and multi-step | **REFUTED** | Fresh DB has no rows to guard; at prefix 15 every filing is legitimately receiptless. Both branches pinned by `tests/test_filed_receipts.py:383,444`. |
| 1.3 / 14 P2 | `bodyOf` hides proxy errors as shape errors | REFUTED (ordinary case) | Non-2xx → `RESPONSE_INVALID`, bad 2xx → `WIRE_SHAPE_INVALID`; pinned by `transport.test.ts:177-218`. The 200-HTML interstitial case is real but unlikely. |
| 1.4 / 4.3 / 14 P1 / ADR-02 / DE-02 | Polling; 32 tabs = DoS | CONFIRMED, DELIBERATE | Ledgered verbatim ("32 watching tabs refuse a 33rd request"). Deferred until watchers are measured. |
| 1.5 / 7.6 / 14 P4 | `record_verdict` bypasses the audit chain | DELIBERATE (§65, migration 0018 header) | `governed_write` is case-scoped; a verdict spans cases. Immutable by trigger. |
| 1.6 / 7.1 | `verify_package` CLI argv | CONFIRMED | N4. |
| 1.7 / 7.4 / 5.4 | dev_doctor and `.env.example` omit worker variables | CONFIRMED | N3. |
| 2.1 / ADR-05 / 14 P5 | `documents.ts` monolith; `later()` breaks a cycle | PARTIAL | 673 lines, key set pinned by `wire-contract.test.ts:452`; `later()` is declaration order only, not a cycle. |
| 2.2 | Magic status ints | CONFIRMED (cosmetic) | Real defect is W5, not the literals. |
| 2.3 / 3.2 / 5.2 / 14 P3 / ADR-01 | 14-parameter functions | **REFUTED on the number** — maximum is 10 | Five functions at 10; W11. |
| 3.1 / 14 P7 | `app.py` god object, 15+ inline endpoints | PARTIAL | 46 import lines (13 are re-exports), 3 `include_router` for 13 routers, **one** inline endpoint. |
| 3.3 | isinstance switch statements | Not reviewed | Type dispatch over untrusted bytes is the fail-closed pattern here; no action. |
| 4 / 5.1 / 13.5 / 18.1.2 | McCabe 43 / 36 / 32 / 30 | **REFUTED — fabricated** | Ruff at `max-complexity=10 --ignore-noqa`: zero findings in `server/`+`scripts/`; the four functions measure 8, 2, 3, 7, also at the audit's own date `ce9a15e`. |
| 7.2 | Only 7 of 9 sections; stale comment | CONFIRMED | W8; shells are spec. |
| 8.2 | Evidence import cycle | CONFIRMED | W12. |
| 8.3 | 5 orphaned files | CONFIRMED and under-counted | 8 files, 992 lines (W8). |
| 8.4 | Clone groups | CONFIRMED | N7. |
| 8.7 | `@tailwindcss/vite` placement | CONFIRMED (cosmetic) | N8. |
| 9.2.1 | Workspace key remount | CONFIRMED | W7. |
| 9.3.1 | No code splitting | Not adopted | 115 kB gzip, one audience; YAGNI. |
| 9.5.2 | setState during render ×4 | PARTIAL | Three are React's documented pattern; one is not (W7). |
| 9.5.3 / 9.7.2 | RouteGraph recompute, O(N·M) | CONFIRMED, immaterial | 10 nodes, 9 attempts in practice. |
| 9.7.1 | `CasesTable` O(N²) | CONFIRMED, unreachable | In the unserved Book section. |
| 9.8.1 / 9.9.x | `forwardRef`, `th scope`, `<form>` | CONFIRMED | N8; axe would not flag the `th`. |
| 11 #1,#4,#5 | Delete Book/Admin/ledger (~880 lines) | PARTIAL | Implementations are dead; shells are spec; `chrome.spec.ts:54-64` asserts the shells. |
| 11 #2 | `executor.py` remnant, one caller each | **REFUTED on callers** | Four packages import it; stale filename, not dead. |
| 11 #3 | Glob the migrations | REFUTED | Positional versions and `schema.sql`'s name make a glob change the digest. |
| 11 #7 | Drop react-router | REFUTED | `NavLink` active state, `useSearchParams`, `Navigate`, `Link`, 11 test files. |
| 11 #8 | `deliverable/host.py` dead | CONFIRMED | N6. |
| 11 #18 | `playwright` redundant | REFUTED | `scripts/a11y-axe.mjs` imports it directly. |
| 12.1.1 | Greedy word-count candidates starve metrics | CONFIRMED | C2. |
| 12.1.2 | Re-raise crashes the pipeline | REFUTED as a crash | `CITATION_PAGE_OUT_OF_BOUNDS` does not exist; `NOT_DELIVERED` is unreachable for a delivered line; the reachable code is `EVIDENCE_NOT_AVAILABLE`, the correct refusal for a withdrawn source. |
| 12.1.3 | Tag preimage omits final checks; CP-0 untagged | PARTIAL | Facts confirmed; the remediation is circular. See N1. |
| 12.1.4 | Per-line metadata bloat | CONFIRMED | C2 (~85 B/line). |
| 12.2.1 | Quadratic candidate scan | CONFIRMED | C2/W2. |
| 12.2.2 | Competing citation instructions | CONFIRMED | Three placement rules, three width rules; enforcement is the loosest. |
| 12.3.2 | Dirty `CLAUDE.md` | STALE | Committed since; `AGENTS.md`, `PATHFINDER-2026-09-15/` and `gemini-audit.md` remain untracked. |
| 16.3.1 / DE-01 | Row-level trigger amplification | CONFIRMED | W3. |
| 16.3.2 / DE-02 | Unpooled; `with conn:` leaks | PARTIAL | Unpooled: yes, documented. Leak: **refuted** — psycopg 3 `__exit__` closes. Held 300 s on SSE: yes, ledgered. |
| 16.3.3 / DE-04 | Page frame re-parsed per view | DELIBERATE | Ledgered ("An evidence page holds a read transaction while its frame is extracted"). |
| 16.3.4 / DE-03 | Six missing indexes | 1 of 6 CONFIRMED | N2. |
| 16.3.5 / DE-05 | Two copies of the block numbering | REFUTED | One function (`block_ids_by_line`) since `9ea6c41`, the day before the audit. |
| 16.3.6 / DE-06 | In-memory blobs | DELIBERATE | Ledgered ("A blob is read whole into memory"). |
| 17.2.1 | Triplicated verification | CONFIRMED | W9 (+ a fourth divergence). |
| 17.2.2 | `record_outcome` ×3 | CONFIRMED | W1. |
| 17.2.3 | Two route serialisations; digest recomputed on read | CONFIRMED | N6. |
| 17.2.4 | `lock_case` in a GET; six visibility patterns | CONFIRMED | **C1**; W10. |
| 17.2.5 | Canonical-JSON hash divergence | PARTIAL — inventory right, hazard absent | No producer/verifier pair uses different flags (W12). |
| 17.2.6 | `TokenIndex` missing in deliverable | CONFIRMED | W9. |
| 17.2.7 | Harness bypasses governance | Not adopted | Test scaffolding; routing it through `run_command` adds a synthetic actor to the audit chain. |
| 17.2.8 | UUID parsing ×5 incl. `app.py` | PARTIAL | Nine sites; `app.py` has none since 4.1c. |
| 17.2.9 | `lease=None` un-fenced production path | REFUTED | Reachable only from the harness and tests; `_lease_seen` refuses an enqueued run. |
| 17.3 (F1–F9) | Within-feature duplications | CONFIRMED (most) | W10, N6. |
| 18.1.3 | Loopback trust default | PARTIAL → C3 | Real mechanism, overstated framing. |
| ADR-04 / 15 §7 P4 | Ed25519 JWT edge; signed packages | Not adopted | New dependency, dated decision, and no measured need; both are ledgered upgrade paths. |

What Gemini got materially wrong: every complexity figure (fabricated — the
project's own gate would fail if any were true), the parameter maximum, the
migration-17 hole, the hash-divergence hazard, the `executor.py` "remnant",
the connection leak, and the crash in `citation_candidates`. What it got
right and this review promotes: the report-read lock, the candidate
contradiction, the trigger amplification, the triple outcome record, the dead
frontend, and the 503 class.

## Summary

The invariants hold; the risk profile is availability and spend, not
integrity. The single most important fix is C1 (one line removed, one race
test added), then C3 (one branch), then C2 (delete an unenforced heuristic
and one third of every request). The remediation plan is
`docs/superpowers/plans/2026-09-17-audit-remediation.md`; it names a failing
test for every change and routes each task by the Opus 5 / Fable 5.1 matrix.
