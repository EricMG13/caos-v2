# CLAUDE.md — engineering contract

CAOS turns governed source documents into committee-ready credit conclusions.
This file is the contract. `docs/DECISIONS.md` is the binding record (later
entries override earlier). `docs/SYSTEM_SPEC.md` is the structure,
`docs/IA_SPEC.md` the workspace, `docs/archive/MODEL_BUILDER_SPEC.md` the
archived workbook,
`DESIGN.md` the visual language, `CONTEXT.md` the vocabulary.

Most of this repository is written by an agent. `docs/AI_CODE_QUALITY.md` says
what that costs and which tool stops each failure mode. Read it before your
first commit.

## Active continuation — Phase 3 repair

The sole current task/checkpoint record is
[`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md).
Read its tracked scope and acceptance evidence before editing; ignored local
reports are supplemental. Work only in `/Users/ericguei/Documents/caos-workbench`;
the original `/Users/ericguei/Documents/caos-v2` stays read-only.

Decision §39 reconciles the repair plan with older specifications. Phase 2 is
accepted (the handoff's acceptance record); Phase 3 runs under
[`docs/PHASE_3_ONWARDS_GOAL_PROMPT.md`](docs/PHASE_3_ONWARDS_GOAL_PROMPT.md)
and its tracked task briefs in `docs/superpowers/plans/`.
The complementary plan's Reasoning Modes section records both Opus 5 guides.

Every shell command starts by unsetting `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, and `CAOS_REQUIRE_PROVIDER`.
Never invoke a live provider without explicit authorization. Index the current
checkout with GitNexus and verify affected callers in source.

The coordinator may use up to three concurrent implementers only in isolated
worktrees with disjoint owned files, migrations and test resources. Each agent
gets an exact base and task brief, commits its own tested concern, and receives
ordinary exact-range review. The coordinator alone integrates reviewed commits,
runs integration/phase gates and updates the handoff. Never share a branch,
database/blob root or provider authority; an independently green branch is not
task or phase acceptance.

Ordinary review closes each task. One `confidence-review` and then one separate
adversarial code audit close the whole phase, both at actual `xhigh` reasoning,
with remediation/reverification between them. No per-task specialist review or
rewrite tournament. Requested document reviews do not certify these code gates.

## The eleven invariants (never weaken)

Each gets a named failing test before the code that satisfies it. A change that
makes one pass vacuously is wrong even with a green suite.

1. **Pinned sources only.** Runs execute against the pinned, immutable source
   set. Supplied evidence only; web discovery is structurally absent, not
   disabled. Withdrawal is checked live at every use.
2. **Evidence reads fail closed.** Every `read_evidence` is validated at the
   host boundary and refuses with a typed code. **No text is returned on
   refusal** — not in the exception chain, the delivered set, or the ledger.
3. **The host owns identity.** Provider-claimed frontmatter never survives.
   Checkpointed digests are expectations re-verified against the store.
4. **The bundle is the methodology authority.** Integrity checked on the bytes
   at use. A run pinned to one build never executes under another. **Never edit
   a file that exists upstream** — additions go in new skill folders.
5. **Human gates are digest-bound.** Approval binds the exact reviewed content
   (preview digest + input fingerprint). Single-actor releases are store CAS
   transactions, not interrupts.
6. **Execution is durable and exactly-once.** Resume from accepted attempts,
   never restart. A crash in the commit gap yields one artifact, one charge, one
   terminal event.
7. **Calculation is pure and finite.** Non-finite values and zero denominators
   refused before use. Decimal, never float, on any money path.
8. **Budgets fail closed.** Every ceiling refuses the next operation before
   overspend. No provider call without a reservation.
9. **Module output is the strict canonical envelope.** Bounded schema,
   undeclared fields refused, citations only from delivered evidence.
10. **The route is resolved once and pinned.** The resolved route — closed node
    list, typed edge set, frozen predicates — is digested at the plan gate.
    Execution reads only the pin. Replay from the same pins takes the same path.
    Route *resolution* is a pure function; route *selection* is a pinned input.
11. **Citations are coordinate-anchored.** `{document_sha256, page, bbox,
    matched_text}`. The host re-locates the quote in its token index and derives
    the rectangle. A quote it cannot re-locate is refused before it reaches the
    artifact.

Standing rules that back them:

- **Wire strictness.** Every JSON success serves a named model, `extra="forbid"`
  both ways. A new field means a model change plus an updated pinned key set.
  One document per section, never per widget.
- **Transactional pairing.** Governed writes commit state + audit event in one
  transaction; run-state transitions commit state + run event in one
  transaction, and every event insert rides a conditional update — zero rows
  updated, no event. That is what makes terminal events exactly-once.
- **Boundary text.** Every string that can reach pinned state, a revision, a
  frozen payload or an audit event carries `BoundaryText`, never a bare `str`.
  NFC-normalised before the length bound; rejects lone surrogates, Cc controls
  except CR/LF/TAB, and bidirectional override/isolate controls.
- **Auth edge.** Development trusts a role header; production derives role from
  OIDC groups only. Unknown and unauthorized both return 404.
- **Persona is not authority.** The section on screen composes the view and
  grants nothing. Every governed action is checked server-side at commit time.

## Where things live

- `server/engine/route.py` — `resolve_route`, `dependency_order`, `node_states`,
  `frontier`. Typed edges from `profile["edges"]`, never from
  `navigation.dependencies`. Pure: no I/O, no clock. Corrected from `engine/`
  for the reason §20 corrected `storage/` — the security floor claims `scripts`
  and `server`, so a top-level `engine/` would be a tracked tree no list claims,
  which `scripts/scan_floors.py` now refuses.
- `server/engine/runtime.py` — the frontier loop. No checkpointer: recovery is
  recomputation from the accepted-attempt ledger.
- `server/store/routes.py` — the pin. Resolution stays pure by keeping the one
  place it meets the store outside `server/engine/`.
- `server/store/` — Postgres owns everything transactional; bytes are content-
  addressed in the blob store. `schema.sql` is migration `0001_legacy`;
  `apply_schema` verifies and atomically advances the ordered immutable
  migration prefix (`docs/DECISIONS.md` §20a and `docs/MIGRATIONS.md`).
- `server/methodology/` — bundle verification, the registry (the only seam for
  adding or upgrading a module), and the calculator execution boundary.
- `vendor/deploy-v/` — the methodology bundle, read-only, pinned
  (`docs/DECISIONS.md` §13). Gates do not scan it.
- `server/deliverable/` — the renderer that turns a frozen snapshot into the
  one HTML deliverable (`SYSTEM_SPEC.md` §7; `docs/DECISIONS.md` §14).
- `frontend/` — one workspace, nine sections, static export.

## Rules of work

- **Test first.** The failing test names the invariant or the behaviour. This is
  the single highest-value control against the +75 % logic-error rate.
- **One concern per PR.** If the diff grows a second concern, split it.
- **Never log document-derived text.** Log the typed code, never `str(exc)`.
- **No new dependency without a dated decision entry.** Locks are fully pinned
  and hashed; the image and CI install with `--require-hashes`.
- **A scanner that scanned nothing is a failure**, not a pass.
- **Regenerate, don't hand-maintain.** Inventories and ledgers are emitted from
  the suite. The previous tree carried ~500 KB of hand-written governance
  markdown; do not repeat that.

## Running

- First setup: copy `.env.example` to `.env`, then run `make bootstrap`,
  `make doctor`, and `make dev-up`. This creates the locked Python 3.14/3.12
  and Node 24 environments, starts the persistent dev database on 55436 and
  the ephemeral test-admin database on 55437, and preserves local blobs.
- `make dev-api` (`make dev` is an alias) — the API alone on port 8000. It
  needs `CAOS_DATABASE_URL` and `CAOS_BLOB_ROOT`, both read per request, and
  advances the verified migration prefix at startup. No worker, nothing seeded.
- `make dev-ui` — the real UI on port 5173, proxying `/api` to port 8000. It
  fails visibly for routes not built yet. `make dev-ui-demo` is the separately
  labelled, read-only fixture workbench; it is never integration evidence.
- `make test` — the offline suite with PostgreSQL required; paid provider tests
  remain deselected.
- `make test-provider` — the live suite against the real model. Needs
  `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` and `CAOS_TEST_POSTGRES_URL`, and
  fails rather than skips without them.
- `make check` — the complete offline engineering gate: required PostgreSQL,
  backend lint/types/tests/coverage/I/O/races/security, frontend lint/types/unit/
  production and demo builds/a11y/workbench, then the image gate, sequentially.
  `make check-fast` is explicitly partial; `make check-size PR_BASE=<commit>` is
  the separate PR-only size gate.
- There is no workbook build and no LibreOffice (`docs/DECISIONS.md` §14).

## Known gaps (honest ledger)

Every accepted limitation gets an entry here with its reason and its upgrade
path, in the same breath as the code that creates it. An empty ledger on a
system this size means nobody looked.

The phase labels below are historical **rebuild** labels, not current repair
phase numbers. Entries are not evidence of completion; the handoff and repair
plan govern present work. Correct a stale entry when its owning task proves
the replacement behavior. The legacy hook claims are currently unverified
controls; see the tracked Phase 2 hook prerequisite in the handoff.

**Repair Phase 3.**

- **A letter-spaced heading cannot be quoted as a word.** (a) ~~The PDF
  extractor's identity no longer predicts its output for positioned text.~~
  Closed by slice 3.2d: `caos.pdfminer` v2 declares every effective `LAParams`
  scalar, `coordinates: "crop-top-left-rotated-pt"` and `crop_policy:
  "drop-outside"`, so new admissions record an identity that predicts their
  tokens; v1 rows keep their stored identity and bottom-left rectangles, and
  verify and re-anchor as recorded
  (`test_v1_pdf_extractions_still_verify_and_reanchor_as_recorded`) --
  readmission is how a source gains v2 geometry (§44.4). (b) Slice 3.2c's
  `word_margin` rule (§44.5) means glyphs spread
  by `Tc` character tracking beyond `word_margin` -- a heading tracked for
  display rather than readability -- split into single-letter tokens, so the
  word cannot be quoted as itself; `test_tracked_glyphs_beyond_word_margin_split_into_letters`
  pins it. *Upgrade:* quote normalisation, Phase 5.
- **A word just inside a crop edge can be dropped.** `PdfExtractor`'s
  `drop-outside` crop policy (slice 3.2d) tests membership on pdfminer's full
  glyph box -- the font size, descent included -- not the baseline, so a word
  whose baseline sits just inside the visible crop but whose box crosses its
  edge is dropped and cannot be cited. That is the fail-closed direction: a
  clipped rectangle would anchor text a reader may not fully see. A crop that
  clips to nothing against the MediaBox drops every token on its page.
  *Upgrade:* a declared tolerance, recorded in the extractor identity, if real
  documents need it.
- **"Undelivered pages of a delivered source cannot be cited" is enforced by
  the rule, not yet by any narrower delivery.** `verify_citations` (slice
  3.2e) anchors a quote only wholly within the block ids a node was handed,
  counting ambiguity over the whole page, and its three awkward-evidence tests
  prove the REPAIR_PLAN exit there. But `captured_blocks` and the executor's
  deliveries are every block of every pinned source, and `source_blocks` rows
  are immutable, so in production a node is always handed whole sources and
  `CITATION_NOT_DELIVERED` for an undelivered page of a delivered source never
  fires on a real run. The executor test that shows it
  (`test_a_quote_outside_the_captured_blocks_refuses_the_handoff`) narrows
  delivery by deleting a block with the trigger disabled: wiring, not exit
  evidence. *Upgrade:* per-node evidence selection -- the Phase 5 entry "The
  gate's evidence demands are dropped" -- is what first delivers less than a
  whole source, and its callers already pass exactly what they delivered.
- ~~**The extraction deadline is cooperative, not preemptive (§44.2).**~~
  Superseded by §47 after the Phase 3 adversarial audit measured a 16,926-byte
  page of operators taking 23.2 s against a 2 s deadline and a 261,529-byte page
  holding 806 MiB. `PdfExtractor.extract` runs `walk_pages` in a child
  interpreter (`python -I`, empty environment, JSON over pipes) that the
  parent kills at the admission deadline (`SOURCE_EXTRACTION_TIMEOUT`), and
  inside that child pdfminer's `zlib` is a budgeted inflater, so a
  document's Flate streams refuse `SOURCE_TOO_LARGE` past `max_decoded_bytes`
  (256 MiB) before the bytes are held -- the corrupt-checksum fallback draws on
  the same budget. What remains: LZW and run-length streams, which pdfminer
  decodes in pure Python, are bounded by the kill rather than by bytes; no
  address-space limit is set, so a child's memory is bounded only through the
  inflater; each PDF pays an interpreter's start-up (0.124 s measured on the
  development machine); and plain text stays in-process and cooperative per
  line, which the 20 MiB document ceiling bounds (a line now stops building
  tokens one past `max_tokens`). Extraction also runs while the caller's
  transaction is open, before `lock_case`: a pack of fifty documents can hold
  it idle for their extraction time. *Upgrade:* an address-space limit in the
  child where the platform enforces one, a worker pool if start-up cost shows,
  and extraction outside the store transaction with Phase 4's upload worker.

- **Three vendor rules have no Python implementation and are not enforced.**
  `server/methodology/handoff.py` calls the vendor's own validators, and the
  vendor ships no code for `semantic_rules`, `document_substrings_casefold` or
  the LITE pathways' `required_payload_fields` (§46.5).
  Reimplementing them would make the host a second conformance authority
  beside the bundle (invariant 4). The catalog declares each LITE pathway
  `decision_scope: SCREENING_ONLY` but maps no `committee_status` to it, so a
  LITE handoff saying `Committee Ready` validates; the host projects the scope
  beside the status and invents no refusal. *Upgrade:* enforce each rule the
  day the vendor ships it, or by a dated decision that the host owns it. The
  deliverable (d-4) labels a screening-only record a screen whatever its
  committee status; the proof (d-2) and the matrix (d-3b) report no status a
  record projects, so neither has anything to label.
- **The canonical deliverable proves the store at freeze and verification, not
  continuously.** `server/deliverable/canonical.py` re-derives the payload --
  both blobs, identity, projections, rectangles -- when it is built, frozen and
  verified. It is derived in its own read unit before `freeze`'s governed write,
  and `artifacts` rows are mutable (the Phase 2 entry below), so a pair moved in
  that gap freezes and is caught by `verify_frozen`, not by the freeze. Proof is
  re-derived under the bundle and live sources present now: a bundle upgrade
  (as for the proof, Phase 10) or a withdrawn source makes a filed revision
  refuse verification. The payload needs every pinned node accepted, and the
  Markdown renders as escaped preformatted text, not formatted Markdown. A soft
  upstream ref may be absent from a record only if that input's artifact was
  accepted after the attempt started (`call_time_identity`); the comparison is
  `artifacts.created_at > run_attempts.started_at`, both transaction-start
  times, so an acceptance whose transaction began before the attempt's and
  committed after it is refused -- impossible in the one sequential loop,
  fail-closed under Phase 4's concurrent workers, which should order by event
  or lease instead. Sources are `pinned_live_sources`, which the proof reads
  too: a document captured under several live members resolves to the lowest
  source id when they share one extraction output and to none when they do
  not.
  *Upgrade:* derive inside the freeze's lock once artifact rows are immutable,
  and a Markdown renderer with a closed element set when committee layout needs
  one.
- **A LITE route runs through `run_route`, but only the runtime reads its
  records.** Slice c-5b: `_run_node` replays the executor's outcome with its
  diagnostic and accepts with `record_sha256`; a validated `qa_status: Blocked`
  (identity held, every citation anchored -- an unanchorable Blocked handoff is
  an ordinary refusal) keeps its bill and diagnostic, accepts nothing and ends
  the run `BLOCKED` with one `RUN_BLOCKED`, no retry. The diagnostic is the
  exact response body, and `blocked_verdict` re-derives that verdict from the
  billed, unaccepted attempts -- before every frontier's attempts (so a crash
  before `block_run` commits resumes BLOCKED without a second call) and before
  ending the run; a raised `HANDOFF_BLOCKED` alone decides nothing. The
  re-derivation reads the provider body back, but only through the full
  validation and anchoring; it rebuilds identity from the upstream accepted
  now, which holds only while no direct input is accepted after its target.
  A billed attempt refused for another reason is re-validated on every pass
  until the node is accepted. A stored body that will not read is a store
  fault, never "not blocked", and a body that cannot be stored refuses the
  attempt after its bill. The re-derivation checks current state: once a
  captured source is withdrawn no verdict can be re-derived, so a Blocked node
  is neither blocked nor re-paid (the pre-call read refuses) and each resume
  adds an attempt row until the 256 ordinal cap. `accepted_artifacts`
  reduces each row to a typed `route.NodeResult` (readiness rows, `qa_status`):
  a canonical row's from its record, verified against its Markdown and the
  identity rebuilt from the store (§42.4, no re-anchoring), refused without a
  bundle. The API's `read_run` (the process's cached vendored bundle,
  `methodology_bundle`) and the harness's `_unrun` (the harness bundle) pass
  one (slice d-1). Every frontier pass and every run-document read re-runs the
  vendor validators on each readiness node's Markdown, costing the host
  identity's ten queries (with the call-time narrowing every reader shares) and
  three blob reads per such node; `read_run`'s
  `IO_BUDGET` is the bound for two such rows (the gate and the catalog's one
  QA_GATE source), measured on LITE's one. The harness still falls back to
  presence when a record will not verify. The call-time narrowing infers from
  `now()` (transaction start) which soft inputs an attempt could name, sound
  for one sequential loop but able to refuse a valid record once concurrent
  workers interleave accepts (Phase 4 records visibility instead); and a
  document pinned twice under different extractions resolves to no source, so
  its citations can never be proven. Diagnostic blobs are
  untrusted provider text, never `BoundaryText`: nothing may render them or
  read them as analysis. The compiled vendor contract is cached per manifest digest, so a
  vendor script changed on disk under an unchanged manifest is not re-verified
  by the cached validator (every other read still is). The executor's pre-call
  unit binds every upstream record it will put in the prompt to that
  upstream's call-time identity and this build (`record_authority_matches`,
  shared with the proof and the deliverable), costing the host identity's
  queries per upstream under the case lock; the record is not re-checked after
  the call (only the digests are). Since f-1a the shared loop fixtures run
  LITE, so the claims executor has no freshness tests left while it still
  ships. No HTTP test covers a canonical `read_run` over a QA_GATE verdict
  other than `Passed`, because the catalog's only QA_GATE (CP-5 -> CP-6) sits
  on a route the canonical adapter does not execute (§42.2); the view function
  that projects a stored `qa_status` is tested directly instead. Since f-1c
  the adapter is one constant: every reader refuses a row without its record
  `ARTIFACT_RECORD_MISMATCH` (API 503), a stored `claims-json-v1` pin refuses
  `RUN_INPUT_INVALID`, and every route with a module outside CP-0, CP-L10 and
  CP-5 -- FULL, DEEP and every other catalog pathway -- and every pathway of
  those modules but LITE earnings (`ADAPTER_ROUTES`: LITE portfolio decision,
  CP-0 -> CP-L10, has no contract test) pins and passes its
  gates but is refused `HANDOFF_MODULE_UNSUPPORTED` at `execution_input` (so
  before any attempt, reservation or call) and at acceptance. A harness case
  on such a route still prepares and is refused only when performed. Closed in
  f-2a/f-2b: the claims executor (`execute_module` and its helpers in
  `server/methodology/executor.py`), `envelope.py` and the claims deliverable
  render (`server/deliverable/render.py`'s `_artifact`) are deleted rather than
  left unreachable; `render()` now renders every artifact from its canonical
  record. The live Phase 5 exit
  `test_cp1_produces_canonical_envelope_with_anchored_citations` ran the
  deleted executor's citation pipeline against CP-1 of the FULL route, a
  live-model contract the canonical adapter does not cover; it is deleted
  rather than ported, and `tests/test_phase_exits.py`'s `NOT_YET_REACHED`
  names it so the phase-exit gate stays honest instead of failing red for a
  test that structurally cannot pass. *Upgrade:* the HTTP gap above closes,
  and that Phase 5 exit test is owed again, the day Phase 5 extends the
  canonical adapter (and its contract tests) to CP-1 and a route carrying
  that QA_GATE.
- **The orchestration proof over a canonical run proves it now, not
  continuously.** `server/qualification/proof.py` (slice d-2) reads both blobs,
  binds the record to the identity rebuilt from the store, requires the pin's
  adapter and the bundle's build, manifest and authority, re-validates the
  Markdown against the record's projections and re-anchors every recorded
  citation in the run's pinned live sources on identical rectangles -- the
  deliverable's verdicts, under the proof's codes, through the same two readers
  (`pinned_live_sources`, `call_time_identity`): a withdrawn or re-extracted
  source, or a doubly captured document, gets one verdict from both. A
  `host_identity` refusal keeps its own code. It proves a BLOCKED run's
  accepted artifacts and says nothing of the node that never ran. Beside its
  counts it returns `anchored`, the `(module_id, document_sha256,
  matched_text)` it re-anchored under the pinned modules, and the matrix (d-3b) scores exactly that set with no second artifact or
  record read: an artifact accepted after the proof is not scored, an unproven
  canonical run cites nothing, and a proven document no longer among
  `pinned_live_sources` at scoring refuses the row
  `ORCHESTRATION_SOURCE_NOT_PINNED`. Under READ COMMITTED the proof's own
  statements can still see different snapshots, and a withdrawal committed
  after the matrix's live check is not seen by that row. Like every proof it
  holds only for the bundle and sources present now. *Upgrade:* the proof and
  scoring in one REPEATABLE READ unit, the day a reviewer relies on the matrix
  as one consistent snapshot.
- **Canonical upstream refs ignore readiness and predicates.**
  `server/methodology/invocation.py` names every accepted direct input and
  refuses a blocking one that is missing, as the vendor's
  `expected_upstream_digests` does, but omits two of its inputs: a CONDITIONAL
  edge always blocks (no predicate is evaluated, the Phase 3 gap below), and a
  soft edge whose unaccepted source CP-0 reported READY is omitted where the
  vendor refuses. The route engine already BLOCKS such a node, so the runtime
  never asks for its identity. `module_name` is read from the verified catalog
  at call time rather than pinned. Since slice 3.3c a non-gate node whose
  upstream carries no direct CP-0 ref refuses `ROUTE_IDENTITY_INVALID` in
  `host_identity` (§45.5), so before any attempt via `check_context`; the
  anchor is still derived from that ref, not stored. *Upgrade:* readiness joins
  the refs from the canonical CP-0 T8 reader c-5b added to the runtime (d-2),
  and a stored anchor field with Phase 5.
- **A record's lineage is re-checked against the accepted rows, not re-proven
  ancestor by ancestor.** Record format v2 (slice 3.3c, §45.4) adds
  `delivered_authority_digest` -- over exactly the `DeliveredAuthority` the
  prompt carried, compared with the pinned bundle's by every reader through
  `record_authority_matches` (`ORCHESTRATION_BUILD_MOVED` in the runtime and
  proof, `ARTIFACT_RECORD_MISMATCH` in the deliverable) -- and `lineage`, the
  transitive accepted chain behind the direct upstream, each (artifact, record)
  pair read by `stored_lineage` from the direct upstream records and required
  to be each node's accepted pair now. v1 records refuse; there is no backfill.
  A reader compares a record's lineage with `accepted_lineage` over the
  accepted pairs its read unit already holds (one `accepted_rows` query per
  unit, not per record; one record blob read per direct upstream, none in the
  executor's pre-call unit, which reads the lineage from the records it has
  just verified), so an
  ancestor record rewritten after its consumer was accepted refuses at the
  runtime's pre-call unit, at the proof and at the deliverable -- but whether
  that ancestor's own record is sound is the ancestor's own verification, which
  the proof and deliverable run for every row and the pre-call unit runs for
  direct inputs only. The pairs are read once per unit, so under READ COMMITTED
  a row moved between that read and a later record's comparison is seen by the
  next unit, not this one. The executor's post-call unit compares only the
  lineage's pairs with the accepted rows (one query), not the records again.
  The executor writes the lineage from the pre-call host identity's upstream
  -- every direct input accepted when the prompt was built -- and the post-call
  identity comparison refuses an attempt during whose call another input was
  accepted, so no lineage names one; `call_time_identity`'s narrowing applies
  only when a record is read back. `blocked_verdict` builds no record and
  checks no lineage. `record_authority_matches` hashes a module's authority
  files once per process for each (bundle root, manifest digest, build,
  module): the manifest pins every hash, so the digests cannot differ for one
  manifest, but a file changed on disk under an unchanged manifest is refused
  by the executor's prompt (which reads every delivered byte) and no longer by
  a reader's comparison. *Upgrade:* Phase 4's lease fencing ancestors for the
  node's whole attempt, and immutable `artifacts` rows.
- **The upstream citation register states acceptance-time anchoring, not a
  fresh one.** Since slice 3.3d a consumer's prompt carries, after the
  upstream handoffs, an `UPSTREAM CITATION REGISTER` section: for each direct
  upstream, one line per citation of its verified record (`document_sha256`,
  `page`, `matched_text`) labelled `quote_existence:
  HOST_VERIFIED_IN_DELIVERED_EVIDENCE` and `support: NOT_ASSESSED_BY_HOST
  (CP-5 audit)`, under a header saying it is context, not evidence. The lines
  come from the record the pre-call unit just verified against its Markdown
  and identity, but the rectangles are not re-derived there: the quote was
  located when that upstream was accepted, and the proof and deliverable are
  what re-anchor it. Citations still anchor only in the consumer's own
  delivered blocks, so a quote found only in upstream text or the register
  refuses `CITATION_NOT_LOCATED`; the register rides inside the request
  ceiling like every other section and has no bound of its own. *Upgrade:*
  re-anchoring in the pre-call unit if a consumer ever relies on the register
  for more than orientation, and a per-section bound with the one "An upstream
  section is unbounded" owes.
- **The named-LITE-object boundary is read from `SKILL.md` prose headings, and
  only where a block is keyed to its module.** Slice 3.4b (§46.1): each
  upstream section names its source's catalog
  `artifact_contract.owned_object` (`NOT_DECLARED` when absent) beside
  `allowed_use`, and `invocation.named_objects` reads every pinned node's
  verified `SKILL.md` block headed `## LITE profile compatibility — <module_id>`
  -- vendor fields only, no module or object named in host code. A block that
  names the route's profile and retains `NAMED_LITE_OBJECT_ACCEPTED` holds its
  node BLOCKED in `route.node_states` (no attempt, reservation or call) until
  an accepted direct input offers one of its `accepted_lite_object_ids` --
  owned through its catalog `owned_object` or carried by the edge's declared
  `accepted_object_id`; a present but malformed block refuses
  `AUTHORITY_BYTES_MISMATCH`. The runtime, `read_run` and the harness's
  `_unrun` pass it, and the run document names the edges that could meet it in
  `waiting_on`. A boundary no input on the pinned route offers is not enforced
  (holding the node forever would be a host-invented graph): on
  `LITE_FULL_CREDIT_SCREEN` CP-2A accepts `lite_fundamental_credit_screen`,
  which no catalog module owns or carries, so the host does not hold it there;
  those routes are refused `HANDOFF_MODULE_UNSUPPORTED` before any attempt
  today. CP-3C's unkeyed prose heading is not read, although the vendor's
  execution-profiles JSON declares its boundary.
  `named_objects` re-reads the bundle bytes per run and per `read_run`.
  *Upgrade:* read the structured `CP_DEPLOY_V_EXECUTION_PROFILES_v1.json`
  declaration beside the block (refusing disagreement), and a vendor owner for
  every accepted object before those routes are enabled (Phase 5).

**Repair Phase 2.**

- **Only a QA `Passed` releases CP-6; `Restricted` blocks it.** F03 asks which
  QA results permit the downstream action, and §39 says restricted output is
  usable but not QA-cleared, so `route._unmet` meets the CP-5 -> CP-6 QA_GATE
  only on a stored `qa_status` of `Passed`; `Not Reviewed` is refused as a
  verdict so the attempt can retry. A reading that let `Restricted` release
  CP-6 as RESTRICTED is also defensible from the bundle. The value is the
  module's own verdict, so text in the evidence that steers the model can steer
  it too; human QA approval is not consulted in Phase 2.
  *Upgrade:* the Phase 3 canonical QA record, and a dated decision if committee
  practice wants restricted clearance to proceed.
- **BLOCKED ends the run; recovery is a new run.** §39 calls an empty frontier
  with unfinished required work recoverably blocked, and `run_route` now ends
  such a run `BLOCKED` with one `RUN_BLOCKED` (migration 0010). Nothing moves a
  BLOCKED run back to RUNNING: every spend guard refuses it and its stream
  closes. "Recoverable" means nothing failed and the reason is re-derived from
  the pins and accepted artifacts, not stored. *Upgrade:* a governed resume --
  a CAS back to RUNNING with its own event, taken by an authorized actor when
  an input that could release the node has changed -- arrives with Phase 4's
  commands and worker.
- ~~**The terminal decision reads outside the run lock, and the store does not
  check it.**~~ Closed by Phase 4 Task 4.3c (§49.4): `complete_run` refuses
  `RUN_NODES_UNACCEPTED` while a pinned node is unaccepted and `complete_run`/
  `block_run` refuse `RUN_TERMINAL_STALE` when the accepted set moved since the
  caller's snapshot; `run_route` retries one pass. A Blocked verdict still ends
  the run on one node's stored verdict without a snapshot.
- **A stale lease holder can still pay once.** Phase 4 Task 4.3 (§49) fences
  every run write with the work lease and replays a billed, unaccepted answer
  from its stored body after a crash (accepted, Blocked, or written once to
  `attempt_refusals`), so a crash no longer pays twice and a lost lease never
  accepts. Two residuals remain. A holder whose bill commits after the new
  holder's replay read but before its reservation is paid for twice with one
  acceptance (interleaving I6: no lock is held across transport). A response
  that trickles past the 300 s lease (the provider timeout bounds each socket
  operation, not the call) costs at most one extra paid call. `run_work` is
  enqueued only by the store function today; the governed start command is
  Task 4.2. `stop` refuses a non-`RefusalCode` with `CALL_OUTCOME_INVALID`,
  a borrowed code. `artifacts` rows are also not UPDATE/DELETE-immutable, so a
  privileged edit could move ownership; a refusal trigger like 0007's is the
  upgrade. *Upgrade:* none planned for I6 while one worker runs; per-node
  fencing of the transport if a second worker is ever added.
- **Acceptance does not recompare upstream, and context reads hold the case
  lock.** `_accept_artifact` checks authority and ownership under the lock but
  not the predecessor digests the post-call unit compared; with Phase 2's one
  sequential loop no writer can accept a predecessor in between. The pre-call
  unit also reads every captured block one query at a time under the case lock,
  so a large pack holds governed writes on that case for the whole read.
  *Upgrade:* Phase 4 rechecks upstream digests inside the accept unit (or fences
  predecessors with the node's lease), and a batched block query when the first
  large PDF pack measures the hold.

**Phase 0.**

- ~~**No `image` CI job.**~~ Closed in Phase 7, and recorded here late. The
  entry said there was no Dockerfile and no runtime lock with packages in it,
  so Trivy would report every target as *not scanned*; the Dockerfile arrived
  with the PDF extractor and the `image` job builds it, scans it, and runs the
  upgrade this entry asked for — `scripts/scan_floors.py trivy.json --trivy`
  asserting a non-empty target list, then `trivy image` failing on fixable
  HIGH/CRITICAL. A ledger entry that describes a gap the tree has since closed
  is the same defect as a missing one, read the other way round.
- **`check_tested.py` matches a name as a whole word anywhere in the suite's
  bytes,** docstrings and comments included. It catches the definition no test
  mentions, not the definition whose test asserts nothing. *Upgrade:* resolve
  references through the AST once the suite is large enough for the false
  negatives to matter.
- **`check_tested.py` sees module-level definitions only.** A method is covered
  through the class that holds it. *Upgrade:* descend into classes when a
  governed path first puts logic on a method.
- **`check_vocabulary.py` enforces 9 of the 33 synonyms `CONTEXT.md` lists.**
  The other 24 carry an ordinary technical meaning here — `file`, `state`,
  `version`, `response` — and each is exempt with a stated reason in
  `NOT_ENFORCED`. The check refuses to run if `CONTEXT.md` and that list drift
  apart. *Upgrade:* enforce an exempt synonym the day it is actually misused.
- ~~**The untested-definition gate reads Python only.**~~ Closed by
  `frontend/scripts/check-tested.mjs`, which rides `npm run lint` beside the
  vocabulary gate's TypeScript half and is driven from `tests/test_gate_scripts.py`
  the way CI drives it. It keeps the Python half's two scope rules so the two
  enforce one thing, and states two of its own: an `interface` or a `type` is
  erased before anything runs, so `tsc --noEmit` at every use site is what
  checks it; and a React component is covered through the section that composes
  it, because a component is reached by rendering rather than by name and
  demanding a mention per component buys shallow render tests. It found 32
  exports carrying real logic that no test named -- `confidenceTier`,
  `severityOf`, `isUncited`, `withdrawRefusal`, `useModalA11y` among them --
  and `frontend/tests/unit/helpers.test.ts` and `hooks.test.tsx` are what
  closed them.
- **The literal-bidi gate scans a named list of roots, not what git tracks.**
  `test_no_file_this_repository_writes_carries_a_literal_bidi_control` walks the
  directories in `WRITTEN`, which mirrors `sonar-project.properties`'s source
  list. A new top-level tree this repository writes goes unscanned until it is
  added there, and the gate catches the nine bidi controls `BoundaryText`
  refuses — not zero-width characters or homoglyphs, which deceive a reader
  differently and are not the trojan-source class. The file floor (`scanned >
  100`) is what stops a moved root reading as a clean pass. *Upgrade:* drive it
  from `scripts/tracked.py` the day that module lists more than `*.py`, which is
  also what would let `check_tested.py` see the frontend.
- ~~**`io_budget.py --assert` enforces only that some `server/api/` module
  declares an `IO_BUDGET`.**~~ Closed. The floor is now every module under
  `server/api/`, and a module that makes no round trip declares `0` --
  `server/api/identity.py` is the one that does. Every module rather than every
  module a heuristic recognises as serving a path: "it declares no route" and
  "it never names the store" are both things a module can stop being true of
  without anyone noticing, so a gate resting on either is one the next request
  path can be written around, which is what the old floor allowed. It still
  keys on the route directory rather than on `server/`, because a store module
  has no request path. `test_io_budget_read_evidence` is the per-path
  assertion the entry asked for and predates this.

**Phase 10.**

- **An answer key names citations, not figures.** `ExpectedCitation` is
  `(module_id, document_sha256, matched_text)`, because that is the strongest
  key the canonical envelope can be checked against: an envelope carries
  statements and citations, not typed numbers. A key saying "net leverage is
  4.2x" has nothing to compare against, so the matrix measures whether a run
  found the right *evidence* rather than whether it reached the right
  *conclusion* — which is a real part of qualification and not the whole of it.
  *Upgrade:* the day the envelope carries a figure as a `Decimal` (the payload
  schema of the Phase 5 gap above), a key gains an expected value and the matrix
  compares it.
- ~~**The matrix is handed its runs; nothing drives the set.**~~ Closed by
  `server/qualification/harness.py`. `perform` admits each case, runs the route
  the case declares through the same `run_route` every other caller uses, and
  hands `build_matrix` the runs it made. Folding the cases into the set also
  closed a hole in the digest: it now covers the documents and the route
  selection, so two sets with identical answer keys over different evidence no
  longer digest the same.
- ~~**A qualification set lives in memory and is digested, not stored.**~~
  Closed by `server/qualification/on_disk.py` (`docs/DECISIONS.md` §24): a
  manifest naming its cases with the documents beside it, and a loader that
  produces the same dataclasses a Python caller would. The digest does not move,
  which is what lets a verdict's `qualification_set_sha256` name a directory
  somebody is holding. There is still no *table* — a set is a directory, not a
  row — and nothing here needs one while a set is authored rather than
  generated.
- ~~**A qualification run costs real money and nothing bounds the set.**~~
  Closed: `Harness.ceiling` is what the whole set may cost, and `_affordable`
  refuses `QUALIFICATION_SET_OVER_CEILING` before the first case is admitted.
  What is left is the shape of the comparison rather than its absence: the
  ceiling is checked against the sum of the per-run ceilings, which is the worst
  case, so a caller must budget for what the set *could* spend and not for what
  it probably will. That is deliberate — a set admitted because it would likely
  come in under would be a forecast, and invariant 8 does not rest on one — and
  it means a set ceiling under `budget.CEILING` times the number of cases is
  refused however cheap the runs turn out to be. *Upgrade:* per-run ceilings
  derived from the set's, the day a caller wants a set of two hundred cases
  without budgeting five dollars for each.
- ~~**The proof says every accepted artifact holds up, not that the run
  finished.**~~ Closed beside the proof rather than inside it.
  `assert_orchestration_proof` still makes only the narrower claim, which is the
  true one it can make from a run id alone. The harness resolved and pinned the
  route, so it holds what the proof is silent about: a `Performed` carries the
  run's own status and the pinned nodes that produced no artifact, each with the
  state the route left it in — BLOCKED is the route's rules applied, RUNNABLE is
  a run that stopped with work in front of it. The facts sit beside the proof
  and are not summed, because a run that stopped with a sound proof and a run
  that finished with an unprovable one are different things to a reviewer.
- **The harness performs its cases one after another.** `perform` runs each case
  to the end of its route before opening the next, so a ten-case set takes the
  sum of ten runs rather than the longest. It is the Phase 4 gap below one level
  up, with the same answer: nothing about correctness turns on it, because each
  case is its own run against its own case row. This entry was written once and
  lost in a rebase onto the harness's other half — recorded again here, which is
  the only way a ledger survives its own history being rewritten. *Upgrade:* the
  async store connection Phase 5's gap already owes; over a synchronous one a
  concurrent harness would serialise on the connection, for the same wall clock
  and harder reasoning.
- ~~**A document that will not admit still ends the set, after the cases before
  it were paid for.**~~ Closed by `prepare`, which resolves every route, creates
  every case, admits every document and pins every input before `perform` may
  spend anything: `SOURCE_HAS_NO_TEXT` on the last case of ten now refuses the
  set before any provider call, with the earlier cases' prepared rows committed
  and unspent.
- **An unrun node's state is a weaker reading when the artifacts cannot be
  read.** `_unrun` asks `accepted_artifacts` for CP-0's body, which is where a
  soft edge's readiness comes from, and bytes that will not load would raise out
  of the one function added to stop a bad case ending the set. Guarded, it falls
  back to artifact presence: which nodes are COMPLETE stays exact, and what is
  given up is the readiness that separates a BLOCKED node from a RESTRICTED one.
  The run has already refused its proof by then, so the signal is not lost.
  *Upgrade:* none — a run whose artifacts are unreadable has a worse problem
  than the precision of this field.
- ~~**`Unrun` does not say whether a node was attempted.**~~ Closed in Task17f-b:
  each `Unrun` carries its stored `Attempted` rows -- whether the attempt was
  reserved, whether its call was recorded (reserved and unrecorded is possible
  spend), whether a known charge was billed (a recorded call without one is
  unknown exposure), and the recorded model and generation, read from the store
  and `None` when the call recorded none.
- **A proof is held and not stored.** `perform` now holds each case's
  `OrchestrationProof` beside the run id it covers — and only for as long as the
  caller does. There is no table and no route that serves one, so a proof still
  cannot be handed to anyone who was not there when the set was performed. That
  is the right shape while it is re-derived on every ask — a stored proof is a
  claim about a store that has since moved — and the wrong one as soon as a
  verdict has to cite the proofs behind it. *Upgrade:* a declared form for the
  proof beside the set's own (§24), which has landed — so what blocked this is
  gone and what remains is the work itself: somewhere to put a proof, and a
  reader that can be handed one.
- **Each case's artifacts are read four times.** `run_route`'s last frontier
  pass, the proof `perform` records, `_unrun`'s own pass, and `build_matrix`
  re-deriving the proof (a run is scored from its proof, not by re-reading
  artifacts). Two of
  those are deliberate: the matrix stands alone, and reading a proof back from
  the harness would make it trust a caller's copy of what the store said
  (invariant 3). Against a provider call per node none of it shows. *Upgrade:*
  hand the accepted mapping from `_perform_one` to the matrix the day a set is
  large enough for the reads to be measurable — which is the same day the
  per-set budget above starts to bite.
- ~~**`perform` returns with a read transaction open.**~~ Closed when
  `_perform_one` and the matrix began reading inside `execution_reads`, which
  rolls its unit back on the way out, so `perform` returns with the connection
  idle.
- **A bundle upgrade invalidates every earlier run's proof.** The authority is
  re-derived from the bundle that is here now, so after an upgrade a run that
  was correct under the old build refuses `ORCHESTRATION_BUILD_MOVED`. That is
  the fail-closed direction and invariant 4 read strictly — the host cannot
  assert bytes it no longer holds — but it means the proof is a statement about
  *now*, not a certificate with a shelf life. *Upgrade:* none while one build is
  vendored at a time; the day two are, the proof takes the build the run was
  pinned to and verifies against that tree.
- **A verdict is read and not stored.** `read_verdict` refuses a document
  missing any of the six bindings or past its expiry, and returns a `Verdict`
  the caller holds; there is no `qualification_verdicts` table and no query that
  answers "is this build qualified". Nothing consumes a verdict yet, so nothing
  can read a stale one. The harness is now the caller with a reason to look one
  up — it holds the matrix and the proofs a verdict would be measured over — and
  deliberately does not: a signature bound to a `PerformedSet` that lives no
  longer than the process that built it is a binding nobody can re-check.
  *Upgrade:* the set's on-disk form has landed (§24), so the verdict stored
  beside the performed set it names is now the whole of what is left here.
- **The provider identity in a verdict is the reviewer's word, not the host's.**
  Invariant 3 says the host owns identity, and here it does not: `provider` is a
  string in a document this repository did not write, and nothing compares it
  against the provider the runs behind the verdict actually called. It is a
  binding rather than a fact, which is the honest reading of a reviewer's
  signature — but it is not the same guarantee the rest of the system gives.
  The harness now holds **both** halves: every accepted artifact records the
  model the host configured and the provider's generation id beside the charge
  (`docs/DECISIONS.md` §25), so what the runs behind a verdict called is a fact
  the store holds rather than something nobody could ask. What is left is the
  comparison itself — nothing yet refuses a verdict whose `provider` names a
  model no run used, so the binding is still the reviewer's word in practice
  even though it is now checkable in principle. *Upgrade:* the harness reads the
  models its runs recorded and refuses a verdict that does not name one of them,
  which is a change to `read_verdict`'s callers rather than to `read_verdict`,
  since the document is still the reviewer's to write.

**Phase 9.**

- **The phase-exit gate reads a workspace test by its literal title.**
  `tests/test_phase_exits.py` now reads `frontend/tests/` as well as `tests/`,
  which is what lets Phase 9 be exited by the TypeScript tests the plan names.
  It matches `test("test_x", ...)` and `it("test_x", ...)` textually, so a title
  assembled at run time — the chrome suite builds one per section from a
  template — is invisible to it. No test the plan names is written that way, and
  `test_the_gate_reads_the_workspace_suite_as_well_as_this_one` fails the day
  the reader stops finding the two it must. *Upgrade:* resolve titles through
  the compiler API the vocabulary gate already uses, the day the plan first
  names a test whose title is computed — the same upgrade `check_tested.py`'s
  TypeScript half is waiting on, and worth doing once, for both.
- **The workbench proves the offline state against an aborted route, not
  against the fixture middleware.** `serveSection` simulates a request that
  never reached the server by destroying the socket, and that reset carries no
  response — so a client may retry it (RFC 9110 §9.2.2), and WebKit does. The
  retry's backoff outran the five-second assertion and turned `main` red on a
  tree that had passed the same step minutes earlier. The test now aborts
  `/api/sections/**` itself, which says the same thing in one
  engine-independent step; what it gives up is coverage of the middleware's
  offline arm. That arm is still driven on all three engines by the a11y
  matrix, over the same `/analysis/?fixture=offline` in `STATE_ROUTES`, which
  tolerates the retry because it waits fifteen seconds for the loading marker
  to detach rather than five. *Upgrade:* make the arm fast and unambiguous the
  day a WebKit build can be run against it — the sandbox this was diagnosed in
  cannot fetch one, and a change to that arm checked only by CI would be a
  guess.
- **The real workspace reads the v1 section routes, but events, evidence pages
  and commands are not wired yet.** Phase 4 Task 4.1 (§50) closed the reads:
  Directory, Upload, Run and Analysis are served at `/api/v1/…`, validated whole
  in the browser and bound to their case and run, with one `{code, clears}`
  refusal body; the other five sections are unavailable. What follows is the
  entry as it stood, kept for the parts still open — the event vocabulary
  (Task 4.4), evidence pages (4.4) and governed writes (4.2):
  **The real workspace is not yet wired to backend section routes.**
  `frontend/src/app/transport.ts` asks `/api/sections/<section>` for every
  section document and `sse.ts` tails `/api/events` for six lower-case event
  names, while `server/api/app.py` serves `/api/runs/{id}` and its
  `/events`, whose stream carries `RunEvent` names (`ROUTE_PINNED` …
  `RUN_FAILED`). The refusal bodies differ as well: the client reads
  `{code, clears}` and the server sends `{refusal}`, so a real server refusal
  is classed `RESPONSE_INVALID`. Ordinary development and production preview
  now use the real API path and fail visibly; only the explicitly labelled
  read-only demo serves fixtures. No governed write — commit,
  withdraw, pin, approve, accept, sign, freeze, file — has a route. A control
  refused for want of one now says so (`READ_ONLY_API`) instead of naming a
  build phase that had already exited; a control refused for a domain reason —
  `APPROVER_NOT_INDEPENDENT`, `RUN_NOT_TERMINAL` — still gives that reason,
  which is the one its route will owe, although meeting it opens no route
  today. The fixtures are the contract those routes owe, including two fields
  the workspace now reads: `withdrawn_at` on a citation of a withdrawn source,
  and `tab` on a ribbon action that opens one of the section's own tabs. This
  entry was missing — the gap was found by driving every user story
  (`docs/feature-status.csv`), not by the ledger.
  *Upgrade:* a named model per section document behind `/api/sections/<s>`,
  one event vocabulary chosen for both halves, and a refusal body that carries
  what clears it; then a write route per governed action over the store call
  that already exists.

**Phase 8.**

- **The analyst narrative reaches the page as one escaped paragraph.**
  `_narrative` takes a `str` and emits a single `<p>`, so a narrative with two
  paragraphs, a list or an emphasised clause arrives as one run of text. That is
  the safe direction while the render must stay pure and the narrative is
  analyst-authored text reaching a governed page — escaping everything is the
  only reading that cannot surprise — but a committee paper whose narrative
  cannot have two paragraphs is a real limit on the deliverable. *Upgrade:* a
  bounded structured narrative, the day an analyst's revision needs shape rather
  than prose.
- **A citation renders without its page when the payload omits one.**
  `_citation` reads `str(citation.get("page", ""))`, while `matched_text` and
  `document_sha256` beside it are refused when absent — so a payload with no
  `page` prints "page " rather than refusing. Unreachable from any real run:
  `AnchoredCitation` (`server/evidence/citations.py`) declares `page` a
  required `int` with no default, and `record_bytes`
  (`server/methodology/handoff.py`) serialises it into every stored record, so
  only a payload hand-built for `freeze` can carry a citation without one. The
  cost is a cosmetic line on the page rather than a false assurance, which is
  why it is recorded and not fixed. *Upgrade:* refuse it here too, for
  consistency with the two fields beside it, the day a payload
  has any author but this repository.

**Phase 7.**

- **`_ratio` divides at the process-global `Decimal` context.** Nothing under
  `server/` sets a context, so the precision and rounding of every ratio come
  from `decimal.getcontext()` — 28 significant digits by default, and mutable by
  anything else in the process. The module's own promise is "same inputs,
  byte-identical output", and it holds only while nothing else touches that
  context; a library that set it on import would change these numbers without
  changing this file. *Upgrade:* a `localcontext()` around the division with a
  stated precision and rounding, which turns the output's shape into a decision
  rather than an inheritance.
- **The residual tolerance is absolute, not relative.** `residual >
  inputs.tolerance` compares against a default of `0.001` while the host never
  learns what units the model's balances are in. On figures stated in millions
  that is effectively exact; on figures stated in units it is a cent, and the
  same set of drivers reconciles or does not depending on a scale nobody
  declared. The caller can pass a tolerance, which is what makes this a limit
  rather than a defect. *Upgrade:* a tolerance stated relative to the balance it
  is judging, the day a forecast request carries its own scale.

**Phase 6.**

- **Identity before the store rests on parameter order.** Every section read
  (`server/api/reads/*.py`, since §50 the retired `read_run`'s successors) and
  `read_run_events` declare `actor: Caller` ahead of `conn: Store`, and that is
  the whole of what refuses an anonymous request before a connection is opened:
  FastAPI builds a route's dependency list in signature order (`get_dependant`)
  and solves it sequentially (`solve_dependencies`), so the ordering is a
  property of a pinned dependency rather than something the code says out loud.
  `test_an_anonymous_request_opens_no_store_connection` counts the dependency's
  calls, so a reorder and a FastAPI that stopped doing this both fail there --
  which is what makes this a limit rather than a defect. *Upgrade:*
  `dependencies=[Depends(actor_from_request)]` on each decorator, which FastAPI
  inserts at the front of the list whatever the parameters say; worth taking the
  day a third route arrives and the order has to be remembered three times.
- **A run tail polls.** `server/api/app.py` re-reads `run_events` every
  `POLL_INTERVAL` until the run is terminal, standing is lost, or
  `TAIL_DEADLINE` passes. Every §9 rule holds and events are timely, but an idle
  watcher still costs `EVENTS_IO_BUDGET` queries every half second — six a
  second, per open connection. *Upgrade:* `LISTEN`/`NOTIFY` on the event append,
  making the poll a fallback rather than the mechanism; worth doing when there
  are enough concurrent watchers to measure it, not before.
- **The role an actor carries is global, and nothing reads it.**
  `server/api/identity.py` derives a `GlobalRole` from the groups the proxy
  asserts, which is what the actor matrix is about; but every authority decision
  that matters is per case and is taken at commit time against `case_members`
  (`SYSTEM_SPEC.md` §8), so no code path consults the global role today. It is
  derived rather than deferred because deriving it later, once routes exist that
  assume a role is present, is how a role header gets trusted "just for now".
  *Upgrade:* the first authority that is genuinely account-wide rather than
  case-scoped. This entry used to name administration in Phase 10; Phase 10 came
  and went without it, and `docs/REBUILD_PLAN.md` lists an admin UI under what is
  deliberately not in the plan — so there is no scheduled upgrade, and saying so
  is better than pointing at a phase that has closed.
- **`GET /api/health` is specified and not served.** `SYSTEM_SPEC.md` §11 wants
  liveness and readiness on one strict model — store, bundle, blob store, 200
  when all hold and 503 otherwise, probed on a shared background task — and the
  route answers FastAPI's own 404. The Admin section's document said
  `HEALTH · 200` and listed a worker the one-process deployment does not have;
  it now names the route as not served. Until the route exists a drifted schema
  stops the process at boot, and every other store fault surfaces only on the
  request that meets it. *Upgrade:* the route and its three probes, the day a
  proxy or an operator has to ask whether the process can serve.

**Phase 5.**

- ~~**The envelope is the host's minimal shape, not CP-1's payload schema.**~~
  Closed by retirement: `server/methodology/envelope.py` enforced the host's
  own closed claims/statements/citations shape, and was deleted with the
  claims executor (Task 3.1 slice f-2a; `docs/DECISIONS.md` §42.1). What
  invariant 9's "bounded schema, undeclared fields refused" means on the
  canonical path is the vendor's own conforming-Markdown validators
  (`server/methodology/handoff.py`), not a host-invented shape — the gap this
  entry named does not carry over.
- ~~**A refused claim is counted, not shown.**~~ Closed by retirement:
  `claims_refused` lived on the now-deleted claims `Envelope`
  (`docs/DECISIONS.md` §26). The canonical adapter's citations bind to the
  whole handoff rather than per claim (§41.3), so there is no partial-refusal
  count to show; a record's `citations` and its projections are what the
  deliverable renders in full.
- ~~**Only `SKILL.md` reaches the prompt.**~~ Closed by repair Task 3.3b
  (`docs/DECISIONS.md` §45.1): `build_handoff_prompt` takes the module's
  `DeliveredAuthority` -- `SKILL.md`, every non-script manifest file and each
  root file `SKILL.md` names -- and hands each file whole, UTF-8, in its own
  tagged section named with its digest, beside a host note that the host runs
  invocation preparation, handoff validation and the completeness check
  itself, while the module authors scoring by the rules stated for
  `confidence_score.py`; no script is delivered. Upstream sections carry their edge's
  catalog `allowed_use` (`NOT_DECLARED` when the catalog gives none), read from
  the verified catalog at prompt time because `Edge` and the route pin do not
  carry it, so no route digest moved. Retrieval (Phase 5) remains the way to
  send less than the whole set.
- **A run's price is supplied by its caller, not read from a table.**
  `docs/DECISIONS.md` §40: every call reserves `pricing.worst_case(price)` --
  every byte of the largest request (§38) as an input token plus the output cap
  -- and `run_route` refuses a price for any model but the provider's configured
  one before an attempt exists. Nothing in the tree says what the live model
  costs, so `tests/test_live_run.py` still prices it from its flat estimate. The
  byte bound is severe for a real model: at about $3/M input and $15/M output one
  call reserves about $3.64, so under the $5 default ceiling a two-node route
  cannot finish; the qualification harness refuses a set whose route length
  times that worst case exceeds a run's ceiling before any case is prepared.
  `ModelPrice.as_of` is carried but not stored beside the reservation, so a
  reservation row does not say which price produced it. *Upgrade:* a
  user-confirmed dated price for the configured live model, recorded with the
  reservation, and pricing the actual encoded request once the prompt is built
  before the reservation.
- ~~**The `provider` CI job is red until its credential exists.**~~ Closed on
  2026-09-11, when `OPENROUTER_API_KEY` (secret) and `OPENROUTER_MODEL`
  (variable) were set on the repository — outside the tree, which is why the
  entry could not close itself. The job still runs on a schedule and on
  dispatch only, never on a pull request, and it now carries Postgres beside
  the credential: `CAOS_REQUIRE_PROVIDER=1` and `CAOS_REQUIRE_POSTGRES=1` turn
  either one missing into a failure rather than a skip.
- **The nightly live run proves one three-module canonical pathway.**
  `test_a_live_run_admits_documents_and_completes_its_route` runs
  `LITE_CREDIT_22`/`LITE_EARNINGS_UPDATE` — CP-0, CP-L10, CP-5 — the canonical
  route (slice e-2): documents admitted, a subject and route pinned and run,
  every node accepted with its host record, every citation re-located. The
  retarget was made statically and has not yet answered a live model: whether
  a real model returns vendor-valid handoffs with whole-token quotes is
  unmeasured, and a validated `Blocked` ends the run BLOCKED and fails the
  test. Most of `FULL_CREDIT_ASSESSMENT`'s modules have never answered a live
  model in CI; `CAOS_LIVE_PROFILE`/`CAOS_LIVE_PATHWAY` name another route on
  demand. *Upgrade:* a first authorized nightly run to measure the canonical
  pathway, then the larger pathways once on-demand runs have said what they
  cost and how often a quote fails to locate.
- **`UrllibTransport`'s error path is tested at the director, not over a
  socket.** `test_an_error_status_arrives_as_an_http_error_the_transport_can_type`
  asks the real `_opener()` to convert a non-2xx, which is where the handler set
  actually decides the answer; what it does not do is send that status over a
  real connection. A local TLS endpoint would, and needs a certificate — which
  needs a signing dependency and a decision entry, for a defect that lives
  entirely in which handlers the director holds. *Upgrade:* fold it into the
  `provider` job, which already has a real endpoint on the other end, by asking
  the live provider for a status it will refuse.
- **The gate's evidence demands are dropped.** A readiness row keeps
  `module_id`, `readiness_status` and `readiness_effect`; CP-0's schema also
  declares `evidence_demand` and `active_representation_ids`, which say *which*
  sources a module needs (`docs/DECISIONS.md` §27). Nothing reads them yet, and
  every module is still handed every block. *Upgrade:* per-module evidence
  selection, which is the same change that would let a set with a 541-page
  credit agreement run at all.
- ~~**The workspace cannot show the cause yet.**~~ Closed by Phase 4 Task
  4.1i: the v1 `NodeView` carries `gate_verdict` and the Run section's node
  detail and reason (`frontend/src/sections/run/reason.ts`) draw it as the
  cause.
- ~~**The host asks the gate for claims and a map in one answer, and refuses an
  answer carrying only the map.**~~ Closed by retirement: `execute_module` and
  `parse_claims` were the claims adapter's mechanism, deleted with it (Task 3.1
  slice f-2b). CP-0 runs on the canonical adapter now, answering in its own
  register (T8), not a JSON claims map, so the shape mismatch this entry named
  does not arise. `server/qualification/proof.py` no longer refuses on an empty
  claim list either; it reads the canonical record. *Upgrade:* a declared
  gate-artifact shape the proof and the matrix both
  understand.
- **A node RESTRICTED by the verdict alone has its cause everywhere but in the
  engine's answer.** `_state_for` returns RESTRICTED for a
  READY_WITH_LIMITATIONS module with no unmet edge, and `limitations_of` reports
  soft edges — so it answers `()`, the one condition its own docstring says must
  not happen. The cause is not lost: the verdict's `readiness_effect` is stored
  on the gate artifact and is where the state came from, and the run surface
  carries the status as `NodeView.gate_verdict`. Widening `limitations_of` is
  the wrong way to add it — the return is `tuple[Edge, ...]`, a verdict is not
  an `Edge`, and every caller would ripple for a field none of them asked for.
  *Upgrade:* the effect travelling with the state, the day a reader works from
  the engine rather than from the run document.
- **An upstream section is unbounded, but the whole context is refused.** A
  node's prompt carries every direct predecessor's accepted Markdown whole
  (`docs/DECISIONS.md` §28), with no per-section cap. Since Task 3.3b the whole
  prompt -- authority, upstream, evidence -- is built by
  `canonical.check_context` under `prospective_identity` before
  `start_attempt`, and one whose whole encoded request
  (`CompletionProvider.request_bytes`: model, parameters and prompt, as the
  provider sends it) exceeds `MAX_REQUEST_BYTES` refuses
  `CONTEXT_OVER_CEILING` with no attempt, reservation or call and nothing
  truncated (§45.3). The executor rebuilds and re-bounds it under the
  attempt's own identity, so each call reads its context twice (the pre-call
  reads, the case lock hold included). That second check runs after the
  attempt and its reservation exist: in the one sequential loop only a bundle
  file changed on disk between the two can make it refuse, but with Phase 4's
  concurrent workers an upstream accepted in between can make the pre-check
  pass and the re-check refuse with a reservation held (no call is made).
  *Upgrade:* a declared per-section bound the day a wide route or a large pack
  comes near the ceiling, and Phase 4's lease fencing the node's inputs
  between the two checks.

**Phase 4.**

- **The frontier's ready nodes run in order, not concurrently.**
  `docs/REBUILD_PLAN.md` Phase 4 and `SYSTEM_SPEC.md` §4 both write the loop as
  `await gather(*(run_node(n) for n in ready))`. This build runs them one after
  another. Nothing about correctness depends on the difference — the frontier is
  recomputed from the store on every pass either way, and Phase 4's exit tests
  are about recovery and reservations rather than parallelism — but a wide
  frontier takes as long as the sum of its nodes instead of the longest one.
  *Upgrade:* the phase that makes the provider call real (Phase 5) is where the
  latency starts to matter and where an async store connection has to arrive
  anyway; the loop's shape does not change, only the `for` becomes a `gather`.
- ~~**The reservation estimate is the caller's number.**~~ Closed by §40:
  `Execution` carries a dated `ModelPrice` bound to the provider's model, and
  each call reserves its worst case. The price's source is the remaining gap,
  recorded in the Phase 5 entry above.

**Phase 3.**

- **A route's predicates are frozen and never evaluated.** `ResolvedRoute`
  carries them, `route_digest` covers them, and `server/store/routes.py` writes
  and reads them back — and no code consults them. `CONDITIONAL` sits in
  `BLOCKING` beside `REQUIRED`, so a conditional edge blocks unconditionally and
  its condition decides nothing. That is the fail-closed direction, and the only
  one available: a condition the host cannot evaluate must not be assumed met,
  and the predecessor's failure was the opposite — edges that did not enforce
  what they claimed. But invariant 10's "frozen predicates" are, for now, frozen
  without yet being predicates, and a reader of the pin could take the presence
  of a predicate for its enforcement. *Upgrade:* the phase that gives a predicate
  a grammar and an evaluator, which is the same thing that would make
  `CONDITIONAL` behave differently from `REQUIRED`.

**Phase 2.**

- **A quote matches whole tokens exactly.** `matched_text` is split on
  whitespace and each word must equal a token, punctuation included. A module
  quoting `USD 1,240.0m.` where the token is `1,240.0m` is refused
  `CITATION_NOT_LOCATED`. That is the fail-closed direction — a refused citation
  costs its claim under the retired claims adapter's per-claim refusal (§26,
  closed with the claims executor in f-2b); on the canonical adapter one
  unanchored quote refuses the whole handoff (§41.3) — an over-eager match
  costs a rectangle over text the quote does not contain either way — but it
  will refuse quotes a reader would call correct.
  *Upgrade:* Phase 5, when a real module's real quotes say which normalisations
  are needed; anything decided before then is guesswork about a caller that does
  not exist.
- **A refused pack can leave blobs behind.** `admit_pack` writes bytes to the
  blob store inside the caller's transaction, and the blob store is a filesystem
  that transaction cannot roll back. The orphans are harmless — content-
  addressed, immutable, and reused verbatim if the same document is admitted
  again — but nothing collects them. *Upgrade:* a sweep that deletes blobs no
  `sources` row names, the day the store is large enough for the space to matter.
- **One block per line; the bounded line group is not built.**
  `SYSTEM_SPEC.md` §5 wants one block per line "while small" and bounded line
  groups once not. This build always packs a line per block, so a large document
  produces more blocks than it should. *Upgrade:* the group arrives with the
  first document big enough to need it, splitting a line at the group width
  rather than giving it a block of its own. Block ids are zero-padded to six
  digits, so reading order and `block_id` order agree up to 999,999 lines.
- **The plain-text extractor's rectangles are a fixed-pitch rendering.** A `.txt`
  document has no typography, so `PlainTextExtractor` states its cell size and
  derives rectangles from character positions. It is a real, reproducible
  mapping, not a measurement of a page. Since slice 3.2d its identity (v2)
  declares that convention, `coordinates: "cell-top-left-pt"` -- top-left,
  y down, the same orientation as a v2 PDF's crop-relative rectangles -- so
  the two extractors no longer disagree silently about which way y grows.
  *Upgrade:* Phase 6 owes
  `test_citations_anchor_in_an_extracted_pdf` with a real extractor, which
  implements the same protocol and changes nothing above it.

**Phase 1.**

- ~~**A schema change is refused, not migrated.**~~ Closed by the ordered,
  checksum-verified `MIGRATIONS` prefix and `store_migrations` history in
  `server/store/__init__.py`; append-only migration files now advance populated
  databases under one transaction and advisory lock. Backup/restore and the
  no-downgrade rule are recorded in `docs/MIGRATIONS.md` and
  `docs/DECISIONS.md` §20a.
- **The recorded digest proves the declared schema did not change, not that the
  database still matches it.** `apply_schema` compares the SHA-256 of
  `schema.sql` against what was applied; a table altered or dropped outside this
  code afterwards passes unnoticed. It catches the failure that startup exists to
  catch — a process meeting a database an older build created — and not
  tampering. *Upgrade:* apply the declared schema into a scratch namespace and
  diff `information_schema` against the live one, the day a database is edited by
  anything but this function.
- **`budget_ledger` records a charge and enforces no ceiling.** One charge per
  attempt is a database fact, but nothing refuses the charge that takes a run
  past a budget, because invariant 8's reservation belongs to the provider call
  and there is no provider call yet. *Upgrade:* Phase 4 reserves before the call
  and reconciles after, and its three named tests
  (`docs/REBUILD_PLAN.md` Phase 4) are what make the ceiling bite.
- **A blob is read whole into memory and has no size ceiling of its own.**
  `BlobStore.get` still returns `bytes`, with nothing bounding a read but the
  process. What has changed since this entry was written: `admit_pack` now
  refuses a document over `AdmissionLimits.max_document_bytes` (20 MiB) or a
  pack over `max_pack_bytes` (100 MiB) or `max_documents` (50) before dispatch,
  extraction, or any write to the blob store (§44.1, Phase 3 Task 3.2c) — so no
  document admission puts bytes past those ceilings into the store to begin
  with. What stays open is `BlobStore.get` itself: a caller reading a blob back
  (or any bytes that reached the store some other way) is still bounded by
  nothing this class declares. *Upgrade:* the ceiling and a streaming read on
  `BlobStore.get` itself, the day a caller other than admission needs one.
- **`BlobStore.path_of` hands out a filesystem path.** It validates the address
  first, so no caller can name a path outside the root, but it does let one
  write to the store without going through `put` and its digest. It is public
  because proving the mismatch refusal means damaging a blob through the real
  filesystem. *Upgrade:* make it private the day a caller needs a streaming read
  instead, which is the only other reason to want it.
- ~~**The store suite skips without `CAOS_TEST_POSTGRES_URL`.**~~ Closed in
  Phase 1. `make test` and `make check` set `CAOS_REQUIRE_POSTGRES=1`, and the
  complete gate first refuses an absent or unreachable configured test
  database. Only the explicitly partial `make check-fast` permits database
  suites to skip.
- ~~**`scan_floors.py --min-files 1` is a weak floor.**~~ Closed in Phase 1.
  The floor is now `--cover scripts server --unscanned tests`: a tracked `.py`
  under `--cover` that the report did not measure is a failure, and so is one
  neither list claims. `server/methodology` is already included by the `server`
  coverage root; there is no separate top-level methodology tree to add.
- **The record cites decisions this repository did not take.** The specs
  lifted from CAOS-Final at `cf8c3a9` cite its §18–§48; `docs/DECISIONS.md`
  §12 maps each to the entry here or to the phase that adopts it. *Upgrade:*
  each phase re-numbers the citations in the pages it corrects.
