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
- **The two identifier gates read Python only.** TypeScript identifiers are
  unchecked. *Upgrade:* Phase 9, with the frontend.
- **`io_budget.py --assert` enforces only that some `server/api/` module
  declares an `IO_BUDGET`.** It keys on the route directory, not on `server/`:
  a store module has no request path and no round-trip budget to declare.
  *Upgrade:* Phase 2 raises the floor to one budget per request path, with
  `test_io_budget_read_evidence`.
- **`make dev` fails.** The schema arrived with Phase 1
  (`docs/DECISIONS.md` §20); there is no process to serve until the first HTTP
  route, which `docs/REBUILD_PLAN.md` places in Phase 6.

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
