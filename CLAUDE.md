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

- **The PDF extractor's identity no longer predicts its output for positioned
  text, and a letter-spaced heading cannot be quoted as a word.** (a) Slice
  3.2c changed `_runs` to follow pdfminer's own `word_margin` word-break rule
  (§44.5) instead of a custom heuristic, so `caos.pdfminer` v1 -- the identity
  `PdfExtractor.identity` still reports -- no longer predicts the tokens a
  positioned-text page produces from its `laparams`; stored rows are
  unaffected, since nothing re-extracts an already-admitted document.
  *Upgrade:* slice 3.2d bumps the identity to v2 the day a caller needs the
  old and new behavior distinguishable. (b) The same rule means glyphs spread
  by `Tc` character tracking beyond `word_margin` -- a heading tracked for
  display rather than readability -- split into single-letter tokens, so the
  word cannot be quoted as itself; `test_tracked_glyphs_beyond_word_margin_split_into_letters`
  pins it. *Upgrade:* quote normalisation, Phase 5.
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

- **Two vendor rules have no Python implementation and are not enforced.**
  `server/methodology/handoff.py` calls the vendor's own validators, and the
  vendor ships no code for `semantic_rules` or `document_substrings_casefold`.
  Reimplementing them would make the host a second conformance authority
  beside the bundle (invariant 4). The catalog declares each LITE pathway
  `decision_scope: SCREENING_ONLY` but maps no `committee_status` to it, so a
  LITE handoff saying `Committee Ready` validates; the host projects the scope
  beside the status and invents no refusal. *Upgrade:* enforce each rule the
  day the vendor ships it, or by a dated decision that the host owns it.
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
  read them as analysis. The orchestration proof still refuses canonical
  pins. The compiled vendor contract is cached per manifest digest, so a
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
  CP-5 -- FULL, DEEP and every other catalog pathway -- pins and passes its
  gates but is refused `HANDOFF_MODULE_UNSUPPORTED` at `execution_input` (so
  before any attempt, reservation or call) and at acceptance. A harness case
  on such a route still prepares and is refused only when performed. The
  claims executor, `envelope.py` and the claims deliverable render remain,
  unreachable from any pin. *Upgrade:* f-2a/f-2b delete that dead code, and
  the HTTP gap closes the day Phase 5 extends the canonical adapter (and its
  contract tests) to a route carrying that QA_GATE.
- **A frozen canonical deliverable binds its source record and Markdown.**
  Slice d-4 re-derives the package payload, records, identity, projections,
  and rectangles from the store before freezing and verifies those hashes and
  derivations again when the revision is checked. It renders model text as
  escaped preformatted text. Artifact rows can still change after derivation
  and before the governed freeze write, so verification catches that movement
  rather than the freeze itself. *Upgrade:* derive under the freeze lock once
  artifact rows are immutable; d-2 and d-3b provide proof and matrix readers.
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
  matched_text)` it re-anchored under the pinned modules, and the matrix (d-3b)
  scores exactly that set with no second artifact or record read: an artifact
  accepted after the proof is not scored, an unproven canonical run cites
  nothing, and a proven document no longer among `pinned_live_sources` at
  scoring refuses the row `ORCHESTRATION_SOURCE_NOT_PINNED`. Under READ
  COMMITTED the proof's own statements can still see different snapshots, and
  a withdrawal committed after the matrix's live check is not seen by that
  row. Like every proof it holds only for the bundle and sources present now.
  *Upgrade:* the proof and scoring in one REPEATABLE READ unit, the day a
  reviewer relies on the matrix as one consistent snapshot.
- **Every upstream carried into a canonical prompt is bound to this build.**
  Before the call, each accepted upstream record is validated against its
  call-time identity and current authority; a mismatch refuses the call.
- **Canonical upstream refs ignore readiness and predicates.**
  `server/methodology/invocation.py` names every accepted direct input and
  refuses a blocking one that is missing, as the vendor's
  `expected_upstream_digests` does, but omits two of its inputs: a CONDITIONAL
  edge always blocks (no predicate is evaluated, the Phase 3 gap below), and a
  soft edge whose unaccepted source CP-0 reported READY is omitted where the
  vendor refuses. The route engine already BLOCKS such a node, so the runtime
  never asks for its identity. `module_name` is read from the verified catalog
  at call time rather than pinned, and the prompt is bounded on its JSON
  encoding; the provider still re-checks the whole encoded request. *Upgrade:* readiness joins
  the refs from the canonical CP-0 T8 reader c-5b added to the runtime (d-2).

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
- **The terminal decision reads outside the run lock, and the store does not
  check it.** `run_route` decides COMPLETE or BLOCKED from a snapshot taken after
  its last pass, and `complete_run`/`complete_attempt` still let a direct store
  caller complete a run with unrun nodes (only tests do). Sound for the one
  sequential loop Phase 2 has. *Upgrade:* with Phase 4's concurrent workers,
  decide under `lock_run` in `_transition`, requiring an accepted artifact for
  every pinned node before COMPLETE.
- **Two workers can pay for one node.** Migration 0009 lets exactly one attempt
  own a node's accepted result, but two attempts can each reserve and call
  before either accepts; both bills are kept. The same window lets a second
  worker that checked `blocked_verdict` before the first worker's Blocked bill
  committed call again. *Upgrade:* Phase 4's PostgreSQL
  claims/leases (§39) take the node before the call. `artifacts` rows are also
  not UPDATE/DELETE-immutable, so a privileged edit could move ownership;
  a refusal trigger like 0007's is the upgrade.
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
- **The real workspace is not yet wired to backend section routes.**
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
  `server/methodology/envelope.py` lists `page` in `CITATION_KEYS` and parses it
  with `int(citation["page"])`, and `server/methodology/runner.py` writes it into
  every stored artifact, so only a payload hand-built for `freeze` can carry a
  citation without one. The cost is a cosmetic line on the page rather than a
  false assurance, which is why it is recorded and not fixed. *Upgrade:* refuse
  it here too, for consistency with the two fields beside it, the day a payload
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

- **Identity before the store rests on parameter order.** `read_run` and
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

- **The envelope is the host's minimal shape, not CP-1's payload schema.** The
  bundle ships `CP-1__CanonicalDataFoundation__payload.schema.txt`, and nothing
  validates a module's output against it yet: `server/methodology/envelope.py`
  enforces the host's own closed shape — claims, statements, citations — which
  is what invariant 9's "bounded schema, undeclared fields refused" needs to
  mean before a schema validator exists. *Upgrade:* the registry that derives
  each module's payload schema from the manifest (`docs/DECISIONS.md` §24) is
  where the bundle's own schema starts being enforced; it needs a JSON-schema
  dependency and therefore a decision entry.
- **A refused claim is counted, not shown.** `claims_refused` travels in the
  stored envelope (`docs/DECISIONS.md` §26) and nothing renders it: the
  deliverable prints the claims that survived and says nothing of the ones that
  did not, so a page can read as complete over a module that asserted twice
  what it kept. *Upgrade:* the deliverable's provenance line carries the count,
  the day a reader relies on the page without the store beside it.
- **Only `SKILL.md` reaches the prompt.** A module's `reference_files` are
  verified and assembled but not sent: one module's reference set runs to tens
  of thousands of tokens, and the budget is invariant 8's. *Upgrade:* the
  retrieval index the bundle ships (`CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json`) is
  what selects the references a question actually needs.
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
- **The workspace cannot show the cause yet.** `NodeView.gate_verdict` names
  why the gate blocked a module (`docs/DECISIONS.md` §27), but
  `frontend/src/wire/run.ts`'s `RouteNode` does not carry the field, so the API
  sends the reason and the UI has nowhere to put it. *Upgrade:* the
  workspace's wire type and the section that draws a node —
  `frontend/src/sections/run/RouteGraph.tsx` and `NodeDetail.tsx`.
- **The host asks the gate for claims and a map in one answer, and refuses an
  answer carrying only the map.** `execute_module` calls `parse_claims`, which
  refuses `ENVELOPE_INVALID` when `claims` is absent or empty — while CP-0's own
  payload schema declares no claims at all, its output being a register. So a
  gate answering in its own register terms loses the verdict, and costs the
  attempt and the reservation that paid for the call. Accepting it is not a
  guard away: `server/qualification/proof.py` refuses an artifact whose claim
  list is empty, so what a *gate* artifact is would have to change in the proof
  and the matrix as well as here — a phase-sized decision about that shape, not
  a fix. *Upgrade:* a declared gate-artifact shape the proof and the matrix both
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
- **An upstream section is unbounded.** A node's prompt carries every claim of
  every direct predecessor (`docs/DECISIONS.md` §28), and nothing caps the
  total: a node with five predecessors of fifty claims each carries two hundred
  and fifty statements and their quotes on top of the authority and every block
  of evidence. On the routes run so far it is a few thousand tokens. *Upgrade:*
  a declared bound with a typed refusal, the day a wide route meets a model's
  context rather than a budget.

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
  costs its claim (§26), an over-eager match costs a rectangle over text the quote does
  not contain — but it will refuse quotes a reader would call correct.
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
  mapping, not a measurement of a page. *Upgrade:* Phase 6 owes
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
- **A blob is read whole into memory and has no size ceiling.** `BlobStore.get`
  returns `bytes`, so a source document's size is bounded by nothing but the
  process. Nothing admits documents yet, so nothing can reach it. *Upgrade:*
  Phase 2 is where bytes first enter a case, and where the ceiling and a
  streaming read belong — a ceiling here would be a number invented ahead of the
  ingestion contract that has to state it.
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
