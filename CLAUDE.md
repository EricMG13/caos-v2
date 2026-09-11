# CLAUDE.md — engineering contract

CAOS turns governed source documents into committee-ready credit conclusions.
This file is the contract. `docs/DECISIONS.md` is the binding record (later
entries override earlier). `docs/SYSTEM_SPEC.md` is the structure,
`docs/IA_SPEC.md` the workspace, `docs/MODEL_BUILDER_SPEC.md` the workbook,
`DESIGN.md` the visual language, `CONTEXT.md` the vocabulary.

Most of this repository is written by an agent. `docs/AI_CODE_QUALITY.md` says
what that costs and which tool stops each failure mode. Read it before your
first commit.

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
  addressed in the blob store. `schema.sql` is the declared schema, applied in
  full at startup and refused when the database was built from a different one
  (`docs/DECISIONS.md` §20, which corrected this line from `storage/`).
- `methodology/` — bundle verification, the registry (the only seam for adding
  or upgrading a module), and the calculator execution boundary.
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

- `make venv` — the two toolchains. `make lock` — recompile every lock.
- `make dev` — API + worker + Postgres, seeded.
- `make test` — the suite.
- `make check` — lint, types, tests, security, in that order.
- There is no workbook build and no LibreOffice (`docs/DECISIONS.md` §14).

## Known gaps (honest ledger)

Every accepted limitation gets an entry here with its reason and its upgrade
path, in the same breath as the code that creates it. An empty ledger on a
system this size means nobody looked.

**Phase 0.**

- **No `image` CI job.** There is no Dockerfile and no runtime lock with
  packages in it, so Trivy would report every target as *not scanned*
  (`docs/DECISIONS.md` §11). *Upgrade:* the phase that adds the Dockerfile adds
  `trivy image` with `--exit-code 1` on fixable HIGH/CRITICAL and a scan floor
  asserting a non-empty target list.
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
- **The untested-definition gate reads Python only.** The vocabulary gate has
  its TypeScript half (`frontend/scripts/check-vocabulary.mjs`, same
  `ENFORCED` set, asserted by `tests/test_vocabulary_rules.py`); a public
  TypeScript export no test names is not refused. *Upgrade:* when the frontend
  grows a module whose logic is not exercised by the workbench, port
  `check_tested.py` over the compiler API the vocabulary gate already uses.
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
- **`io_budget.py --assert` enforces only that some `server/api/` module
  declares an `IO_BUDGET`.** It keys on the route directory, not on `server/`:
  a store module has no request path and no round-trip budget to declare.
  *Upgrade:* Phase 2 raises the floor to one budget per request path, with
  `test_io_budget_read_evidence`.

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
- **A qualification set lives in memory and is digested, not stored.** There is
  no table and no file format: a caller constructs `QualificationSet` in Python
  and gets a digest a verdict can bind. That is enough for the binding to be
  checkable and not enough for two people to be sure they hold the same set
  without comparing digests by hand — and now that a case carries its documents
  as bytes, a set of any size is a Python literal nobody wants to write.
  *Upgrade:* a declared on-disk form with a loader, which is the next thing this
  phase needs and the thing a reviewer would actually be handed.
- **A qualification run costs real money and nothing bounds the set.** `perform`
  runs every case through the real provider seam under `Harness.estimate`, and a
  set of two hundred cases is two hundred routes' worth of calls. Each run has
  its own ceiling (invariant 8), but nothing refuses a *set* whose total would
  exceed what the caller meant to spend. *Upgrade:* a ceiling on the set,
  checked against the sum of the per-run ceilings before the first case is
  admitted — the same fail-closed shape one run already has, one level up.
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
- **A refusal raised before a run exists still ends the set.** `perform` records
  a `Refusal` from `run_route` in `Performed.stopped`, stops, and returns what
  it performed. The refusals it cannot record are the ones raised before there
  is a run to record them against — `resolve_route`, `create_case`,
  `admit_pack`, `pin_route` — which still propagate and discard every earlier
  case's record with them. Resolving the route first (it is pure) removes the
  one that used to leave an orphan RUNNING run behind; the rest are setup
  failures on a case the caller assembled, and they are loud where a misassembled
  set should be loud. *Upgrade:* the day a set is loaded from the declared
  on-disk form rather than built in Python, a case that will not admit is a
  file defect rather than a caller's bug, and belongs in a record like any
  other.
- **An unrun node's state is a weaker reading when the artifacts cannot be
  read.** `_unrun` asks `accepted_artifacts` for CP-0's body, which is where a
  soft edge's readiness comes from, and bytes that will not load would raise out
  of the one function added to stop a bad case ending the set. Guarded, it falls
  back to artifact presence: which nodes are COMPLETE stays exact, and what is
  given up is the readiness that separates a BLOCKED node from a RESTRICTED one.
  The run has already refused its proof by then, so the signal is not lost.
  *Upgrade:* none — a run whose artifacts are unreadable has a worse problem
  than the precision of this field.
- **`Unrun` does not say whether a node was attempted.** A node the provider was
  asked for and refused and a node execution never reached both come back
  RUNNABLE, although `run_attempts` holds the difference: the first has a
  started, unaccepted row and a reservation, the second has nothing. With the
  frontier running its ready nodes in order this is at most one node per run.
  *Upgrade:* read the attempt rows alongside the states, the day a wide frontier
  runs concurrently and more than one node can be mid-flight.
- **A proof is held and not stored.** `perform` now holds each case's
  `OrchestrationProof` beside the run id it covers — and only for as long as the
  caller does. There is no table and no route that serves one, so a proof still
  cannot be handed to anyone who was not there when the set was performed. That
  is the right shape while it is re-derived on every ask — a stored proof is a
  claim about a store that has since moved — and the wrong one as soon as a
  verdict has to cite the proofs behind it. *Upgrade:* the declared on-disk form
  the qualification set is waiting for; the two land together or neither means
  anything.
- **Each case's artifacts are read four times.** `run_route`'s last frontier
  pass, the proof `perform` records, `_unrun`'s own pass, and `build_matrix`
  re-deriving the proof and re-reading every artifact for its citations. Two of
  those are deliberate: the matrix stands alone, and reading a proof back from
  the harness would make it trust a caller's copy of what the store said
  (invariant 3). Against a provider call per node none of it shows. *Upgrade:*
  hand the accepted mapping from `_perform_one` to the matrix the day a set is
  large enough for the reads to be measurable — which is the same day the
  per-set budget above starts to bite.
- **`perform` returns with a read transaction open.** Its last writes commit
  inside the store calls, and the proof, the status read, `_unrun` and the
  matrix all read after them without committing or rolling back. Under the
  `with connect(...)` every caller uses today the connection closes immediately
  after; a caller that held one would leave a session idle-in-transaction,
  pinning a snapshot. *Upgrade:* end the transaction on the way out, in the
  phase that first gives this a caller which outlives one set.
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
  *Upgrade:* the declared on-disk form above, then the verdict stored beside the
  performed set it names.
- **The provider identity in a verdict is the reviewer's word, not the host's.**
  Invariant 3 says the host owns identity, and here it does not: `provider` is a
  string in a document this repository did not write, and nothing compares it
  against the provider the runs behind the verdict actually called. It is a
  binding rather than a fact, which is the honest reading of a reviewer's
  signature — but it is not the same guarantee the rest of the system gives.
  The harness has one half of the comparison and not the other: it holds the
  runs, and nothing a run leaves behind names the model it called —
  `ProviderResult` carries an artifact digest and a charge, and `run_attempts`
  neither a model nor a generation id. *Upgrade:* record the provider identity
  on the attempt it was charged against, a store change with its own decision
  entry, and the precondition for the harness refusing a verdict whose
  `provider` names a model the runs behind it never called.

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
- **Only `SKILL.md` reaches the prompt.** A module's `reference_files` are
  verified and assembled but not sent: one module's reference set runs to tens
  of thousands of tokens, and the budget is invariant 8's. *Upgrade:* the
  retrieval index the bundle ships (`CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json`) is
  what selects the references a question actually needs.
- **No per-model price table, so the reservation is still a flat estimate.**
  `docs/DECISIONS.md` §16 wants each configured model to carry a dated
  `(input, output)` price as `Decimal` driving the reservation ceiling. The
  provider reports `usage.cost`, which is the *actual* charge and is what the
  ledger records; the number reserved *before* the call is still the caller's
  single estimate. *Upgrade:* the price table lands with the module executor
  that knows the prompt's size, and retires the Phase 4 gap below with it.
- **The `provider` CI job is red until its credential exists.** It runs on a
  schedule and on dispatch only — never on a pull request — and sets
  `CAOS_REQUIRE_PROVIDER=1`, so a missing secret fails loudly rather than
  skipping. Until `OPENROUTER_API_KEY` (secret) and `OPENROUTER_MODEL`
  (variable) are set on the repository, every scheduled run fails. That is the
  intended signal, not a gap to widen.
- **`UrllibTransport`'s error path is tested at the director, not over a
  socket.** `test_an_error_status_arrives_as_an_http_error_the_transport_can_type`
  asks the real `_opener()` to convert a non-2xx, which is where the handler set
  actually decides the answer; what it does not do is send that status over a
  real connection. A local TLS endpoint would, and needs a certificate — which
  needs a signing dependency and a decision entry, for a defect that lives
  entirely in which handlers the director holds. *Upgrade:* fold it into the
  `provider` job, which already has a real endpoint on the other end, by asking
  the live provider for a status it will refuse.

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
- **The reservation estimate is the caller's number.** `run_route` takes one
  `estimate` and reserves it for every node. A real estimate is per module and
  comes from the model's price and the prompt's size (`docs/DECISIONS.md` §16).
  *Upgrade:* Phase 5, with the provider that knows both.

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
  costs a retry, an over-eager match costs a rectangle over text the quote does
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

- **A schema change is refused, not migrated.** `apply_schema` refuses
  `STORE_SCHEMA_DRIFT` against a database built from a different declared
  schema, which is the right answer only while no deployment holds data — it
  offers a running system no way forward. *Upgrade:* the first deployment brings
  an ordered migration table and a decision entry overriding §20; the drift
  refusal stays as the check that the migrations were actually run.
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
- **The store suite skips without `CAOS_TEST_POSTGRES_URL`.** A local `make
  test` with the variable unset reports success having exercised none of the
  store. CI sets `CAOS_REQUIRE_POSTGRES=1`, which turns that skip into a
  failure, so the gap is local only. *Upgrade:* none needed while CI is the
  gate; the day a developer's green run is trusted on its own, the variable
  becomes required everywhere.
- ~~**`scan_floors.py --min-files 1` is a weak floor.**~~ Closed in Phase 1.
  The floor is now `--cover scripts server --unscanned tests`: a tracked `.py`
  under `--cover` that the report did not measure is a failure, and so is one
  neither list claims. `methodology` joins `--cover` in Phase 5, which is when
  the directory exists — naming it now would claim a tree that is not there.
- **The record cites decisions this repository did not take.** The specs
  lifted from CAOS-Final at `cf8c3a9` cite its §18–§48; `docs/DECISIONS.md`
  §12 maps each to the entry here or to the phase that adopts it. *Upgrade:*
  each phase re-numbers the citations in the pages it corrects.
