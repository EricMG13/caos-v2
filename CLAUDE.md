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
- `make dev-api` (`make dev` is an alias) — the guarded site application on
  127.0.0.1:8000, loopback only (§53). It needs `CAOS_DATABASE_URL` and
  `CAOS_BLOB_ROOT`, both read per request, and advances the verified migration
  prefix at startup. `make dev-worker` is the worker; nothing is seeded.
- `make dev-ui` — the real UI on port 5173, proxying `/api` to port 8000 as
  the local actor `CAOS_DEV_USER` (role `CAOS_DEV_ROLE`, default ANALYST);
  without it the API answers 401. `make dev-ui-demo` is the separately
  labelled, read-only fixture workbench; it is never integration evidence.
- `make test` — the offline suite with PostgreSQL required; paid provider tests
  remain deselected.
- `make test-provider` — the live suite against the real model. Needs
  `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` and `CAOS_TEST_POSTGRES_URL`, and
  fails rather than skips without them.
- `make check` — the complete offline engineering gate: required PostgreSQL,
  backend lint/types/tests/coverage/I/O/races/security, frontend lint/types/unit/
  production and demo builds/a11y/workbench, the image gate, then
  `make smoke-production` (the production image and real-stack journey),
  sequentially.
  `make check-fast` is explicitly partial; `make check-size PR_BASE=<commit>` is
  the separate PR-only size gate.
- There is no workbook build and no LibreOffice (`docs/DECISIONS.md` §14).

## Known gaps (honest ledger)

Every accepted limitation gets an entry here with its reason and its upgrade
path, in the same breath as the code that creates it. An empty ledger on a
system this size means nobody looked.

The phase labels below are historical **rebuild** labels, not current repair
or completion phase numbers; the four that collide with the phases of
`docs/COMPLETION_PLAN.md` say "Rebuild Phase N (historical)" outright. Entries
are not evidence of completion; the handoff and the repair and completion plans
govern present work. Correct a stale entry when its owning task proves the
replacement behavior, and strike it in the commit that closes it, naming the
test: `tests/test_ledger.py` refuses an entry citing a test the suite does not
define, and an open entry that states no upgrade path. The legacy hook claims are currently unverified
controls; see the tracked Phase 2 hook prerequisite in the handoff.

**Completion Phase 8.**

- ~~**A register is located by vendor prose, and a key trusts that location.**~~
  Struck in the commit that closed it, and worth reading as an example of an
  entry being wrong in the direction that matters. It said the narrowing was
  "not a divergence from the authority: the vendor's own `check()` reads the
  same table, so the host and the bundle agree". Both halves were false. The
  host asked the vendor's locator with a **narrowed** register-id list where
  the bundle's own `check()` asks with none, and the locator walks the lines
  above each table nearest-first, breaking on the first line naming any id it
  was given and keeping the first table it binds -- so the id list decides which
  table answers. CP-L10 is required to write five registers with identical
  columns and the same six-row minimum, and its own `SKILL.md` asks it for
  appendix prose naming the TL10 family, so a handoff could be scored `met` from
  a sibling register while the honest one said `MISSING`, and an honest handoff's
  key could miss because the prose named a different sibling first. The entry's
  reachability claim was wrong for the same reason, and its upgrade deferred the
  fix to a module "whose registers are optional" when CP-L10's are all required
  and the divergence was live on the only register key that ships. Closed by
  asking the locator exactly as the bundle asks it -- no id list --
  which `tests/test_qualification_matrix.py::test_the_register_locator_is_asked_exactly_as_the_bundle_asks_it`
  holds by building both readings of one handoff. Found by the Completion Phase 8
  adversarial audit, which constructed a handoff passing the vendor's own
  completeness check with zero violations in which the shipped key was met from
  the wrong register. The confidence review had looked at the same code and
  recorded it as safe; this is what a second, adversarial gate is for.
- **Two vendor tests fail on bytecode any concurrent process can write.**
  `tests/test_vendor_contract.py::test_vendor_loader_leaves_sys_path_untouched`
  asserts no `__pycache__` under `vendor/deploy-v`, and
  `tests/test_bundle_pin.py::test_the_bundle_verifies_with_its_own_tool` runs the
  bundle's own `verify_package.py`, which refuses a tree carrying any. Both are
  right to: the vendored tree is read-only and `docs/DECISIONS.md` §13 pins its
  bytes. Neither is isolated from the rest of the machine. This checkout is
  shared -- a peer session, review agents and the coordinator all run in it -- and
  any Python process that imports a vendor script through the ordinary machinery
  leaves bytecode beside the source, after which both tests fail for a cause
  neither names. It happened twice while retesting Completion Phase 8, and cost
  an hour: the first diagnosis blamed an agent that had used `-B` throughout and
  proved it by timestamp, and the second blamed `load_vendor_contract`, which was
  then shown to write nothing when nothing else is running. The real cause is
  concurrency, and the evidence for it is that the failure does not reproduce in
  an otherwise idle checkout. What is *not* in question: nothing in `server/` or
  `scripts/` reaches a vendor module except through `load_vendor_contract`, which
  uses `compile`/`exec` and writes no bytecode, and the one place that runs a
  vendor script as a subprocess already passes `-B`. The seam holds; its test is
  what is fragile. *Upgrade:* have the two tests clear `__pycache__` under
  `vendor/` before asserting, so they measure this repository's own behaviour
  rather than the machine's -- or give each agent its own checkout, which is the
  standing worktree rule these sessions have been bending by working in one tree.
- **A key over a duplicated column answers nothing, and that is now true rather
  than only written down.** The vendor's reader builds a register row as
  `dict(zip(header, cells))`, so a header naming one column twice collapses to
  the trailing cell before the host sees anything. `_cell`'s documented rule --
  "a register whose header names the same column twice answers `None`" -- could
  therefore never fire, and a shipped key was met by `PARTIAL` in a second
  `evidence_status` column while the first honestly said `MISSING`. `_cell` now
  takes the header, where the duplicate is still visible, and
  `tests/test_qualification_matrix.py::test_a_key_does_not_answer_from_a_duplicated_column`
  holds it. What remains is that the bundle still collapses the row, so the host
  refuses to answer where the vendor's own `check()` would read the trailing
  cell: the two disagree, and the host takes the fail-closed side.
  *Upgrade:* the bundle's, and it belongs with the other vendor requests -- a
  duplicate header is a malformed register and the validator should refuse it.

**Audit remediation (2026-09-17).**

- **A revision filed before a renderer change cannot be packaged verifiably
  again.** `server/deliverable/filing.py` records `renderer_sha256` from the
  `render.py` of the day the revision was filed; `build_package` embeds the
  renderer of the day the package is built; and `verify_package._contents`
  refuses when the receipt's hash and the embedded renderer disagree. So the
  moment the renderer changes -- as Completion Phase 12 Task 12.4 changed it --
  every revision filed before it can no longer be turned into a package that
  verifies. Unreachable today, which is why it is recorded rather than fixed:
  no route serves a package and `write_package` has no caller outside the
  suite. It becomes real the day a deliverable export route exists, and it will
  arrive silently, because the filing that breaks is one nobody is looking at.
  Found by the Task 12.4 review, which noticed that the task reasoned carefully
  about not breaking filed deliverables retroactively and stopped one step
  short of this one. *Upgrade:* verify a package against the renderer its
  receipt names rather than the one this build holds -- the archived verifier
  already works that way, which is the whole of §55's design -- or re-render
  and re-file on a renderer change, which is a governed write and a decision.

- **The wire says "come back later" honestly at 5xx and not at 400.** §75 split
  the twenty-four permanently-failing codes off 503: 500 for a fault no retry
  clears, 503 with `Retry-After` for the one that a retry does. What it did not
  touch is the other direction -- nine codes answer **400** carrying
  retry-shaped clearances (`PROVIDER_UNAVAILABLE`: "Retry when the provider
  answers"; `READINESS_INCOMPLETE`: "Retry the attempt";
  `INTERNAL_FAULT`: "Retry; an operator must investigate if it persists"), and
  `tests/test_api_routes.py`'s partition test cannot see them because it defines
  its universe as the codes already at 500 or 503. `INTERNAL_FAULT` is the
  sharpest: `server/api/app.py` maps it to 400 while `server/api/edge.py`
  answers 500 for it, so its only real wire status sits outside the guard and
  nothing asserts the disagreement. The contract that holds is therefore the
  narrow one -- of the codes served at 5xx, 503 means come back later and 500
  does not -- and a client reading 400 learns nothing about retrying.
  *Upgrade:* reconcile `INTERNAL_FAULT`'s two statuses, then put the
  retry-shaped 400s to the owner as D3's second half; the partition test widens
  to the whole enum on the same day.

- **A tokenless host believes the subject header, so a loopback peer who knows a
  member's id reads that member's cases.** §70.2 closed C3's *role* hole: with
  no `CAOS_EDGE_TOKEN` and no trust switch the global role is READER and no
  header can raise it. The *subject* is unchanged -- `x-caos-user` is parsed as
  a UUID and believed -- and `server/api/deps.py`'s visibility resolves per-case
  standing from it, admitting any live standing at or above READER. So a peer
  that passes the loopback bind and the Host check and knows a member's UUID
  reads that member's cases in full: the section documents, the event stream,
  evidence pages including document text, and the report and committee
  deliverables. Writes are closed -- every governed command refuses a global
  READER before it reaches the store -- so this is disclosure, not tampering.
  It needs the host process, which binds loopback only; the documented
  deployment is an authenticating edge that sets both headers, where the token
  branch takes over and the groups are the identity provider's. The plan's
  deferred table rejected a signed-assertion edge partly on the claim that
  C3's fix "removes the only unrecorded hole", which was true of the role and
  not of the subject. Found by the phase adversarial audit. *Upgrade:* the
  signed assertion the two edge entries above already owe, which makes the
  subject the identity provider's rather than a header's; nothing short of it
  makes a tokenless host safe to expose, and nothing should expose one.

- **A provider that returns without billing and then crashes is paid twice,
  with nobody deciding to.** §70.3 deleted the frontier loop's duplicate
  outcome record, and with it the loop's own enforcement that a returned call
  was billed. Each `Provider` owes that now, and for every implementation that
  ships it holds structurally, because `check_call` refuses a second recorder.
  The cost of a future one forgetting is not a refusal: a provider that returns
  unbilled and then crashes before acceptance leaves no `call_outcomes` row, so
  neither `replay_billed` nor `unexplained_charge` matches, the node is
  re-attempted and the money is spent again without an operator choosing it.
  What holds the obligation for every implementation that ships is
  `execute_handoff` recording the outcome unconditionally before any post-call
  refusal -- not `check_call`, which refuses a *second* recorder and so cannot
  make a provider bill at all. This entry said `check_call` when it was first
  written, copied from §70.3, and both were corrected at the phase adversarial
  audit that read the function.
  This is the same shape as "A billed call whose diagnostic body cannot be
  stored is billed again", which was closed by giving the operator the choice;
  this one has no such arm. The run ceiling bounds it, so it is two charges for
  one node rather than unbounded. *Upgrade:* a record adjacent to the call --
  nothing inside the acceptance unit can reach the window, which is why §70.3
  records it rather than closing it.
- **The deliverable's shared token index holds every cited page for the whole
  payload, on a request path.** §71.3 gave the report and committee reads a
  `TokenIndex` shared across the pinned nodes, which is what took six round
  trips per served path out of `IO_BUDGET`. Nothing clears it: it holds tokens
  for every cited page of every node until the reader is collected, where each
  node's index was previously released when its proof returned. A wide route
  citing many pages of a large credit agreement now holds them all at once, on
  an API request rather than in a worker. The proof reader has carried the same
  trade since it gained its own index. *Upgrade:* a bounded or per-node index
  the day a real payload's peak memory is measured; nothing today measures it.

- **The evidence seal is checked once per statement, and two costs come with
  that.** §74.2: migration `0027` makes `0008`'s immutability check an
  `AFTER INSERT ... FOR EACH STATEMENT` trigger with a transition table, and
  both evidence writers use `COPY`, so admitting a 100,000-token document runs
  the check twice instead of 30,001 times and its store write fell from 12.1 s
  to 4.4 s (`scripts/measure_admission.py`, warm, one machine). First: the
  statement's rows are materialised into a transition tuplestore that can spill
  past `work_mem`, a memory and temp-file cost the row trigger did not have --
  inside the noise on this workload and bounded per document by
  `AdmissionLimits.max_tokens`. Second: a refusal now arrives *after* the
  statement's rows are written rather than before the first, so a sealed
  source's bulk insert writes its rows and discards them where it used to
  refuse at row one. Nothing on the admission path meets that, because
  `_admit_one` seals in the transaction that writes. The trigger takes
  `FOR NO KEY UPDATE` where `0008` took `FOR UPDATE`, because an `AFTER` trigger
  runs after its own statement's foreign-key check has taken `FOR KEY SHARE` on
  the same row and two writers upgrading that would deadlock; every writer
  `0008` excluded, the seal included, is still excluded, and
  `tests/test_frozen_evidence.py::test_an_uncommitted_evidence_write_blocks_a_withdrawal_of_its_source`
  holds the exclusion direction that the permissive tests cannot.
  *Upgrade:* a declared `work_mem` floor for the admission path, the day a
  document large enough to spill is admitted; none for the refusal ordering,
  which is the price of checking once.
- **Two tested islands have no production caller, and deleting them is a gate
  edit.** §74.4: reducing Book and Admin to their unavailable shells left
  `bind`/`release` in `frontend/src/app/authority.ts` and
  `EvidenceContext.openPassport` with the metric-passport overlay behind it
  reachable from no section. Both are the subject of a test pinned by name in
  `tests/test_phase_exits.py`
  (`test_book_binds_one_snapshot_per_compared_case`, `test_passport_contract`),
  whose own assertion exists to stop the names being re-excused to green it. So
  neither may be deleted as cleanup, and both sites now carry a comment saying
  so. *Upgrade:* delete each with the gate entry that pins it, in one commit, on
  the day its section is served or its exit is formally withdrawn.

**Completion Phase 10.**

- **A run that cannot afford its next node writes an attempt row before it is
  refused.** `_affordable` reads the run's own ceiling rather than what is left
  of it, which is what lets a resume finish (the reason is in `runtime.py`). The
  cost is that a run whose ceiling covers one worst case but whose remainder no
  longer covers its next priced request is admitted, and the refusal then comes
  from `reserve` -- after `start_attempt` has committed a row and an
  `ATTEMPT_STARTED` event. Measured at three `run_route` entries: three attempt
  rows, three events, no reservation and no provider call. Before the fix that
  run was refused with no row written. No money guard was lost: `reserve` refuses
  under the run row lock, invariant 8 holds in the direction that matters, and
  nothing spends. What is lost is tidiness -- an operator retrying such a run sees
  its attempt count climb while nothing happens -- bounded by
  `ATTEMPT_LIMIT_REACHED` at 256 per node and by there being a human between
  retries. Recorded rather than fixed because the alternative is a second
  affordability read that decides nothing, and a check whose answer no caller
  acts on is how a gate starts looking stronger than it is. Found by the Task
  10.3 acceptance review, which probed it rather than reading it. *Upgrade:* a
  `remaining` read between `check_context` and `start_attempt` that refuses
  before the row, the day an operator meets a climbing attempt count on a real
  run and asks what it means.
- **A gate record stored before `blockers` existed refuses at every reader if its
  T8 named a condition.** Task 10.3 added `Projections.blockers` and kept the
  record format still: `record_bytes` omits the field when it has no rows,
  `_decoded_record` reads absence back as the empty tuple, an explicit
  `blockers: []` is refused as a second spelling, and
  `record_bytes(decoded) == data` holds for every record written before it
  (`tests/test_handoff_record.py::test_an_empty_blocker_list_is_absent_from_the_record_and_read_back_as_empty`).
  What that does not save is the record whose T8 *does* carry a CONDITIONAL or
  BLOCKED row. Every reader re-validates the Markdown and compares whole
  projections -- `canonical.py`, `qualification/proof.py`,
  `deliverable/canonical.py` -- so the rows now derived are rows the stored
  record lacks, and the comparison refuses `ARTIFACT_RECORD_MISMATCH`. The class
  is exactly the runs this feature exists for: a readiness-BLOCKED run's
  accepted CP-0, stored before this change. Its frontier pass, its run document,
  its proof and its deliverable all refuse. §72 and the commit that landed it
  both said the stored records were untouched, which is true of their bytes and
  false of their readers; the Task 10.3 acceptance review measured the
  difference. Nothing is repaired in place, because a projection is re-derived
  and never stored, and rewriting an accepted artifact to match a new derivation
  is what invariant 3 forbids. *Discharge:* a new run. The pins a successor
  takes are its own, so a re-run CP-0 writes a record carrying the rows, and
  `runs.supersedes_run_id` is what says which run it answers. *Upgrade:* a
  record-format version, the day a stored record must survive a projection the
  host learned to read after it was written -- the same shape as §45.4's v1 to
  v2, which had no backfill either.

**Completion Phase 7.**

- **The ledger's own gate reads citations and conventions, not claims.**
  `tests/test_ledger.py` refuses an entry that cites a test the suite does not
  define, and an open entry that states no `*Upgrade:*` clause: the two failures
  here that are mechanical. It cannot read an entry's prose and decide whether
  the tree still behaves that way, which is the failure that actually happened.
  Two entries below claimed there was no `qualification_verdicts` table and that
  a proof was never stored, and both were fluent, cited nothing, and kept their
  upgrade clause while becoming false. Phrase-based rules were measured against
  this file and rejected: the best of them flagged three entries, of which one
  was the real defect and two were correct entries using the same words.
  *Upgrade:* none that is mechanical. What closes this class is the discipline
  `docs/COMPLETION_PLAN.md` states in its definition of done, that the entry a
  task closes is struck in the commit that closes it, naming the test.
- **The feature-status record is dated evidence, so some of its citations name
  tests the tree deleted.** `docs/feature-status.csv` carries 248 rows of which
  206 are dated, 198 of them 2026-09-11, and each row says what was true when it
  was written. Nine test names it cites are defined nowhere in the suite and
  nowhere on disk -- `test_a_revision_is_frozen_once`,
  `test_the_receipt_names_the_signer_of_the_frozen_bytes` and seven more of the
  filing and revision-signing set, across 14 rows -- because `9bf20b2` wrote them
  and the repair deleted the code they covered. The Completion Phase 7
  adversarial audit asked for the citations to be made to resolve. They are
  deliberately not: a dated row whose evidence is edited later is no longer a
  record of that date, and rewriting 14 of them would make the file agree with
  the tree by giving up the one property that makes it worth keeping. So the
  ledger gate reads this file not at all, and a reader must take a row's date as
  part of its claim. *Upgrade:* a regenerated inventory emitted from the suite,
  which this file's own "Regenerate, don't hand-maintain" rule already asks for
  and which belongs with Completion Phase 13 Task 13.6, the task that generates
  the release pack from the suite and the store; the dated file is then the
  archived predecessor rather than the live answer.
- **The demonstration Admin panel says the health route is not served.**
  `frontend/fixtures/admin.json` carries `HEALTH` and `GET /api/health` marked
  not served;
  `server/api/health.py` has served that route since §53.8. The fixture
  under-claims, so its assertion still holds and no gate is weakened, but an
  operator reading the demonstration panel is told a control does not exist when
  it does. *Upgrade:* correct the fixture and the comment with Completion
  Phase 12's Admin work, which is the task that owns that panel.

**Repair Phase 5.**

- **Package verification proves consistency, not authenticity.** Task 5.4a
  (§55) ships a bounded stdlib verifier and exact renderer bytes; its trusted
  renderer hash prevents arbitrary archived code from executing. Replacing the
  verifier and the whole package can still produce a lying verdict: there is
  no external signature trust anchor. The current host verifier accepts its
  renderer build only; older packages use their own archived verifier. ZIP64,
  multi-disk containers and trailing bytes refuse within the ZIP32 size bounds.
  *Upgrade:* an authenticated external digest/signature and renderer-version
  registry if archival verification becomes an authenticity service.
- **Exclusive package creation is not crash durability.** `write_package`
  uses `xb`, so simultaneous writers cannot overwrite one another, but an I/O
  failure or crash may leave a partial new file that later writes refuse.
  It has no fsync or atomic publication protocol. *Upgrade:* staged durable
  writes and exclusive publication when this library becomes a filing exporter.

**Repair Phase 4.**

- **An audit event cannot be read back to the ids its command made.**
  `governed_write` stores only `payload_sha256`, never the payload, so a
  `RUN_CREATED` or `SOURCES_ADMITTED` row says a command happened without
  naming the run or sources. The payload binds the command's
  `request_sha256`, and the ids are in the `command_requests` receipt under
  that digest, but no column joins the two rows: an auditor needs the
  request itself to recompute the payload digest. *Upgrade:* a
  `request_sha256` column on `audit_events` (a migration), the day an audit
  reader needs the join.
- **Receipts are kept forever, including a revoked member's.**
  `command_requests` is UPDATE/DELETE/TRUNCATE-immutable and nothing collects
  it, so it grows by one row per committed command. A revoked member's
  receipts stay; their replay is answered 404 by the visibility check before
  the lookup. *Upgrade:* a dated retention decision and a governed sweep, the
  day the table's size is measured.
- **The demonstration workbench shows no available command.** The v1
  fixtures carry `"actions": []`, so every command control in `make
  dev-ui-demo` renders refused `ACTION_UNPLACED`, and the fixture middleware
  answers any non-GET under `/api/` 405 `READ_ONLY_DEMO`. `ACTION_UNPLACED`'s
  clearance (`frontend/src/controls/RefusedControl.tsx` `READ_ONLY_API`) still
  says the API serves only the run document and its event stream, which has
  not been true since §50. Availability is proven against the real API
  (`test_every_available_action_succeeds_and_every_refused_action_refuses_with_its_code`)
  and in unit tests, not in the workbench. *Upgrade:* correct the clearance
  text, and fixture actions when a workbench spec needs an available control.

- **An evidence page holds a read transaction while its frame is extracted.**
  `read_evidence_page` reads standing and the page's lines, then
  `server/evidence/page.py` reads the whole document blob and, for a PDF, runs
  the §47 child for its frame, under the admission deadline (60 s) and decoded
  budget -- all with the request's read transaction open and its unpooled
  connection held. Each request pays an interpreter start and a full blob read,
  and nothing caches a frame, so a reader paging a large PDF repeats both.
  *Upgrade:* a frame stored at admission beside the extraction, or a cache
  keyed by `(document_sha256, extractor identity, page)`, and the transaction
  closed before the child, the day page latency is measured.
- **The demonstration event stream keeps one process-wide frame counter.**
  `frontend/vite.config.ts`'s fixture stream advances a single `runFrame`
  (and `staleAdvanced`) for the whole dev server, reset when a fresh stream
  opens, so two tabs or two concurrent workbench specs tailing it move each
  other's Run document. The evidence workbench specs refuse the demo stream
  for that reason. Demo mode only; the real stream has no shared state.
  *Upgrade:* per-stream frames the day a spec needs two tails at once.

- **The edge proves itself with one static shared secret.** Edge mode trusts
  any request carrying `CAOS_EDGE_TOKEN` (§53.2): anything on the private
  network that learns it can assert any subject and groups, the process holds
  one token at a time so rotating it means restarting the API, and nothing
  binds a request to the edge's authentication of it. *Upgrade:* verifying the
  identity provider's signed assertion (a dependency and a dated decision), or
  mutual TLS between edge and API.
- **The API cannot tell whether the edge stripped a client's identity.** The
  guard refuses a repeated or lookalike identity header, which catches an edge
  that appends; an edge that forwards a client's `x-forwarded-groups` and sets
  none of its own is indistinguishable from a correct one, and that client
  chooses its global role. The contract lives in `server/api/edge.py`, §53.1
  and the test edge (`tests/journey/edge.py`), not in anything the API can
  check. *Upgrade:* the signed assertion above, which makes the groups the
  identity provider's rather than a header's.
- **The worker has no readiness.** The API's `/api/health` probes the store,
  bundle and blob root it uses; `server/engine/worker.py` serves no listener,
  and `compose.smoke.yaml` gives the worker no healthcheck. A worker that
  exited 2 (`PROVIDER_NOT_CONFIGURED`) or is backing off on store faults is
  visible only in its exit code and logs, and a queued run simply waits.
  *Upgrade:* a heartbeat the worker writes and health reads, the day an
  operator has to alert on a stalled queue.
- **An idle case stream held its thread until the deadline.** Fixed in
  `0db50fa`: each poll now ends in an SSE comment, so a disconnected browser
  releases its worker thread and uvicorn concurrency slot within one
  `POLL_INTERVAL`. What remains is the poll itself (the Phase 6 entry "A run
  tail polls") and `--limit-concurrency 32` counting every open stream: 32
  watching tabs refuse a 33rd request with 503. *Upgrade:* `LISTEN`/`NOTIFY`
  and a stream cap below the concurrency limit, the day real watchers measure it.
- **The test edge's session cookie is weaker than the contract's.** Over
  `http://127.0.0.1:18080` a cookie cannot be `Secure`, so `tests/journey/edge.py`
  drops `Secure` and the `__Host-` prefix the contract names and keeps
  `HttpOnly` and `SameSite=Lax`. The journey therefore proves SameSite and the
  Origin check, not the prefix. *Upgrade:* none while the smoke stack has no
  TLS material, which this task was not authorized to create.
- **The production image and journey are proven locally, not in CI.**
  `make smoke-production` is the last step of `make check`, and no CI
  job runs it. The journey (slice 4.5e2) runs 13 tests on each of chromium,
  firefox and webkit, but only the first engine meets the worker's real
  exit-after-first-accept and the 300 s lease wait: the exit-once marker lives
  in the shared blob volume, so the later engines restart the worker against
  a run that has already finished. *Upgrade:* a CI job over the smoke stack
  (Phase 6), and a per-engine marker if the recovery must be proven per engine.

**Repair Phase 3.**

- **RELATIVE_VALUE is proven offline, not economically qualified.** Task
  5.2a (§56) adds only `FULL_CREDIT_32` / `RELATIVE_VALUE` beside LITE earnings:
  all nine modules execute, validate, anchor, prove and freeze deterministically.
  Other pathways remain disabled, including FULL_CREDIT_ASSESSMENT; CP-CF
  remains disabled. The fixture pack is a compact annual/legal/peer extract,
  with independently authored owner rows and explicit extract-only limits;
  this proves contracts and lineage, not full underwriting or live-model
  quality. CP-3's two binary XLSX references reach the prompt whole as labelled
  base64 under their original digests; the host does not interpret workbook
  cells. CP-2G's 42-row vendor driver vocabulary differs from CP-CF's movement
  vocabulary. *Upgrade:* explicit accepted-owner mapping in 5.2b, and separately
  authorized exact-route economic/live qualification in Phase 6.

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
  tokens one past `max_tokens`). The admission command (§51) extracts through
  `prepare_pack` with no transaction open and no case lock held, but
  `admit_pack`, which the qualification harness still calls, extracts while
  the caller's transaction is open, before `lock_case`: a pack of fifty
  documents can hold it idle for their extraction time. *Upgrade:* an
  address-space limit in the child where the platform enforces one, a worker
  pool if start-up cost shows, and the harness admitting through
  `prepare_pack`.

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
  verified. Task 5.3 now stores an immutable host revision and re-derives it inside
  the freeze governed write under its case lock, closing the old read/write
  gap. Proof is
  re-derived under the bundle and live sources present now: a bundle upgrade
  (as for the proof, Phase 10) or a withdrawn source makes a filed revision
  refuse verification. The payload needs every pinned node accepted.
  ~~The Markdown renders as escaped preformatted text, not formatted
  Markdown.~~ Closed by Completion Phase 12 Task 12.4: `render.py`'s
  `_markdown` renders the closed element set `ELEMENTS` names -- front matter,
  headings, paragraphs, tables, lists, blockquotes, code blocks, thematic
  breaks, strong, emphasis and code spans -- escaping every authored character
  inside them, so a register reads as a table and a raw tag still reaches the
  page as the characters the model wrote
  (`tests/test_deliverable_render.py::test_a_handoffs_markdown_reaches_the_page_as_headings_tables_and_lists`,
  `test_markdown_outside_the_element_set_reaches_the_page_as_itself`,
  `test_an_identifier_and_an_unpaired_asterisk_are_not_emphasis`). A soft
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
  What the renderer added is a refusal of its own: a block with no faithful
  rendering -- an unterminated fence, a table row that does not fit its header,
  a list nested past four -- refuses `DELIVERABLE_MARKDOWN_UNSUPPORTED` rather
  than guessing
  (`tests/test_deliverable_render.py::test_a_block_with_no_faithful_rendering_is_refused_not_guessed_at`),
  and a filed revision whose handoff carries one cannot be re-rendered or
  verified. No stored handoff in this tree carries one, and the direction is
  the fail-closed one, but the class is new.
  *Upgrade:* widen `ELEMENTS` for the construct, the day a real handoff meets
  that refusal; and, for the entry's own title claim, nothing is planned while
  re-derivation needs the store, the bundle and the live sources the render
  deliberately does not hold.
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
  `RUN_INPUT_INVALID`. Task 5.2a now adds RELATIVE_VALUE and its eight new
  modules; Phase 9 Task 9.1 adds LITE portfolio decision (CP-0 -> CP-L10,
  `tests/test_lite_portfolio_route.py`); every route outside those three
  `ADAPTER_ROUTES` pathways remains disabled -- it pins and passes its
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
- **Canonical upstream refs do not read readiness, because the engine already
  did.** `server/methodology/invocation.py`'s `_upstream` names every accepted
  direct input and refuses a missing blocking one; the vendor's
  `expected_upstream_digests` does the same and adds one clause the host does
  not repeat — it also refuses when a **soft** input is unaccepted and CP-0
  reported its source READY or READY_WITH_LIMITATIONS. Note what the vendor does
  there: it raises, and it does not name the input. There is no accepted
  artifact, so there is no digest for a ref to carry, and "readiness joins the
  refs" — the upgrade this entry used to state, and O18's first repair clause in
  `docs/COMPLETION_PLAN.md` — describes something neither side can do. The rule
  itself is enforced, once, in `server/engine/route.py`'s `_state_for`, which
  BLOCKS a node with an unmet soft edge whose source is READY on the same
  predicate the vendor's own `node_states` uses. So the two agree in every state
  a run can reach: a node reaches `host_identity` only through `frontier`, and
  `frontier` excludes every node the vendor's clause would refuse. Measured
  rather than read — over every edge-type assignment, accepted subset, QA status
  and readiness assignment of a three-module route, 9,888 frontier memberships
  produced no disagreement; and on the real LITE route with CP-0 accepted
  declaring CP-L10 READY, the engine puts CP-L10 in the frontier and holds CP-5
  BLOCKED. `test_the_lite_upstream_follows_the_pinned_edges` builds CP-5's
  identity in that exact state, and can do so only because it calls
  `host_identity` directly, past the frontier. What is left is that the
  agreement rests on nothing written down: `_upstream` does not say it relies on
  `_state_for`, and `_state_for` does not say anything depends on it. Nor can
  `_upstream` cheaply re-check: readiness reaches the host through
  `accepted_artifacts`, which builds each `NodeResult` by calling
  `accepted_projections` and so `host_identity`, so an identity builder that
  asked for readiness would be asking the reader that calls it; `host_identity`
  also takes no `BlobStore`, and each gate row's readiness costs a record blob
  read and a vendor validator run. *Upgrade:* not a second reading of readiness
  — that would be a second authority over the rule, which invariant 3 refuses.
  What closes this is a comment at each of the two rules naming the other, and,
  the day per-node evidence selection changes `node_states`, a test that the
  frontier admits no node the vendor's clause refuses — written as the property
  it is rather than as a case the engine can reach. `module_name` is still read
  from the verified catalog at call time rather than pinned, and the CP-0 anchor
  is still derived from the direct CP-0 ref `host_identity` requires (§45.5)
  rather than stored; both keep their own upgrade with Phase 5.
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
- **BLOCKED ends the run; recovery is a new run, and the store records which
  run answers which.** §39 calls an empty frontier with unfinished required work
  recoverably blocked, and `run_route` ends such a run `BLOCKED` with one
  `RUN_BLOCKED` (migration 0010). Nothing moves a BLOCKED run back to RUNNING:
  every spend guard refuses it and its stream closes. "Recoverable" means
  nothing failed and the reason is re-derived from the pins and accepted
  artifacts, not stored. §72 withdrew the resume for good, on §61: the
  CONDITIONAL verdict names a source the effective-source set does not carry,
  discharged only when that source is supplied and CP-0 is re-run, and under
  invariants 1 and 10 a run's source set and route are pinned, so the discharge
  is a new run and a CAS back to RUNNING would reopen a run whose pins cannot
  change. What records it is `runs.supersedes_run_id` (migration `0025`):
  written by the insert that makes the successor and refused by trigger on any
  later change, never a run's own id, at most one successor per predecessor by
  the partial unique index `runs_one_successor`, served at both ends as
  `RunView.supersedes` and `RunView.superseded_by`. `start_run` refuses a run of
  another case with the same private `RUN_NOT_FOUND` an unknown run gets, any
  status but BLOCKED `RUN_NOT_BLOCKED`, and a second successor
  `RUN_ALREADY_SUPERSEDED` inside its own unit
  (`tests/test_run_commands.py::test_a_successor_run_links_a_blocked_run_of_its_case`,
  `test_a_successor_for_a_running_run_or_another_case_is_refused`,
  `test_a_runs_predecessor_is_written_once_and_is_never_itself`, and
  `tests/test_postgres_races.py::test_two_successors_for_one_blocked_run_commit_one`).
  The T8 blocker cell is projected as `NodeView.gate_reason`, so a reader sees
  which source the verdict asked for.
  **Two scopes that are easy to conflate.** The withdrawal of resume covers a
  readiness verdict and nothing else: a run also ends BLOCKED when the frontier
  empties against a QA_GATE whose source is not `Passed`, and there the
  discharge is a human decision under unchanged pins, which the Repair Phase 2
  entry "Only a QA `Passed` releases CP-6" owns and this entry does not speak
  for. The **link**, by contrast, is offered on a run's status alone, for both
  causes: `blocked_by` is `null` in each, so telling them apart would mean
  reading the gate verdicts, and a successor for a QA-blocked run is an ordinary
  run an analyst chose. §72 said the link was for the readiness case alone until
  the Task 10.3 acceptance review read that sentence against the code.
  What the link does not do: a successor pins its own route and input and pays
  for every node again, nothing carries an artifact across it, and nothing checks
  that the successor's source set carries the source the verdict named -- the
  host cannot read a model's prose as a source identifier, and inventing a match
  would be a readiness ground of its own (invariant 4). *Upgrade:* a stored
  anchor for which source a successor supplied, the day a reader wants the host
  to say whether a successor answered its predecessor rather than only that it
  claims to.
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
  written only by the start, retry and cancel commands (§51), each in its own
  audited unit that rechecks authority but never calls a provider. `stop` refuses a non-`RefusalCode` with `CALL_OUTCOME_INVALID`,
  a borrowed code. `artifacts` rows are also not UPDATE/DELETE-immutable, so a
  privileged edit could move ownership; a refusal trigger like 0007's is the
  upgrade. *Upgrade:* none planned for I6 while one worker runs; per-node
  fencing of the transport if a second worker is ever added.
- **Acceptance does not recompare upstream, and context reads hold the case
  lock.** `_accept_artifact` checks authority and ownership under the lock but
  not the predecessor digests the post-call unit compared; with Phase 2's one
  sequential loop no writer can accept a predecessor in between. The pre-call
  unit ~~also reads every captured block one query at a time under the case
  lock, so a large pack holds governed writes on that case for the whole
  read~~ -- closed by §71.2: one statement reads them all, and refuses
  unless it returns exactly the blocks the pin captured.
  *Upgrade:* Phase 4 rechecks upstream digests inside the accept unit (or fences
  predecessors with the node's lease). The batched block query this entry asked
  for arrived without waiting for a large pack to measure the hold.

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
  mentions, not the definition whose test asserts nothing.
  **It failed exactly that way on 17 September 2026, and the manner is the
  point.** Task 8.2 shipped `canonical._within_reservation` -- the guard that
  stops a rebuilt prompt going out under a reservation too small for it, which is
  invariant 8's whole claim on that path -- with **no test driving it**. The gate
  passed because the name appears in a *comment* in `server/engine/runtime.py`
  explaining what the guard does. So a sentence about the code satisfied the
  check for the code. The Phase 8 confidence review found it; the test now
  exists and was watched failing with the guard removed.
  This is one instance of a class worth naming, because three unrelated ones
  turned up in one day: **a gate measuring an axis correlated with the hazard
  rather than the hazard itself.** The suppression budget counted annotations
  where the hazard is positional width. A block of refusal statuses encoded
  *blame* where the status means *time*. Two ignore rules described the shape
  they expected -- a directory, an exact filename -- where they meant a path. And
  this gate counts mentions where the hazard is untested behaviour. The failure
  mode is **invisibility**: such a gate does not fail loudly, it passes quietly,
  and what it should have caught is exactly what nobody is looking at -- so the
  count of known instances is a lower bound, and none of the four was found by
  looking for it. Each surfaced when something else broke.
  The test that separates the class: **ask what the cheapest evasion of a gate
  does to the code, and keep the gate only if the answer is "it improves it".**
  This one fails immediately -- the cheapest way to satisfy it is to name the
  symbol in a comment, which makes the tree worse by leaving prose where a test
  should be, exactly as happened above.
  *Upgrade:* resolve references through the AST, which moves the axis from
  "mentioned" to "referenced"; the honest fix is an assertion reaching the
  definition, which no static check can see, so the AST version is a better
  proxy rather than the right one. Worth taking now rather than "once the suite
  is large enough", since the false negative has been paid for once on a money
  path.
- **`check_tested.py` sees module-level definitions only.** A method is covered
  through the class that holds it. *Upgrade:* descend into classes when a
  governed path first puts logic on a method.
- **`check_vocabulary.py` enforces 11 of the 34 synonyms `CONTEXT.md` lists.**
  The other 23 carry an ordinary technical meaning here — `file`, `state`,
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

**Rebuild Phase 10 (historical).**

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
- ~~**A proof is held and not stored.**~~ Closed by migration `0020`: each
  case's proof is serialised into `qualification_performed.performed_json` by
  `server/qualification/store.py::_performed_document` (`run_id`,
  `route_digest`, `build_id`, `artifacts`, `citations` and the `anchored` set),
  and `record_performed` reads the row back for equality before
  `performed_sha256` binds it, on a table immutable by trigger. A reviewer signs
  that snapshot, so a proof can now be handed to somebody who was not there when
  the set was performed. What it is not is a replayable proof: verification is
  still re-derived against the store and the bundle present now, which the entry
  "A bundle upgrade invalidates every earlier run's proof" below owns.
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
- ~~**A verdict is read and not stored.**~~ Closed by migration `0018`, which
  creates `qualification_verdicts` immutable by trigger, and
  `server/qualification/store.py::record_verdict`, which binds one reviewer
  decision to the exact evidence row and refuses a mismatched set digest,
  provider, build or an incomplete snapshot. §65 added the route the assertion is
  made through, `POST /api/v1/qualification/{evidence_sha256}/verdict`, with
  `reviewer_id` derived from the authenticated actor;
  `server/api/reads/qualification.py` serves the consumer. The table is empty in
  every database because nobody has signed, which is a fact about people rather
  than about the software; `docs/FINAL_CHECK.md` records it as such.
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

**Rebuild Phase 9 (historical).**

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
- ~~**The real workspace reads the v1 section routes, but events, evidence
  pages and commands are not wired yet.**~~ Closed by Phase 4: Task 4.1 (§50)
  served Directory, Upload, Run and Analysis at `/api/v1/…` with one `{code,
  clears}` refusal body; Task 4.2 (§51) the governed writes the journey needs;
  Task 4.4 (§52) one name-only case stream whose names the browser refetches
  by, and an authorized evidence page. Withdraw, sign, freeze, file and
  membership grants still have no route, and Book, Model, Report, Committee
  and Admin stay unavailable.
- ~~**A BLOCKED run draws the node that blocked it as running, and the analysis
  page cannot tell it from a run in flight.**~~ Closed. The run page no longer
  does: `reasonOf` and `runningOf` read the
  run's own status, which the run document already carried, so on an ended
  run nothing is drawn running and a ready-but-unrun node reads "did not
  run" instead of "in the frontier". No wire change was needed for that
  half — the status was there, and reading the node state without it was
  the defect. The journey now asserts it through the production stack.
  The analysis page needed the wire change, and has it: `AnalysisBody` carries
  `displayed_run_status`, so "Pending nodes / not yet accepted" — a claim about
  what happens next — becomes "Nodes that did not run / the run ended BLOCKED"
  once there is no next. Both are asserted through the production stack by the
  insufficient-evidence journey. *Why* the run ended is carried too:
  `RunView.blocked_by` names the node whose validated Blocked verdict ended it,
  with its attempt, and is `null` on a run the frontier emptied (§39) — the
  wire never claims a blocking node that does not exist. It is recorded by
  `block_run` in the transaction that ends the run, not re-derived by the
  reader, because the store refuses to judge an ended run's answer again
  (`docs/DECISIONS.md` §68). The run page says it on the node, in its detail
  and in the run panel, and the journey asserts all three. The analysis page
  was the half that remained, and Completion Phase 12 Task 12.4 closed it:
  `AnalysisBody.blocked_by` is the same `BlockedByView`, read in the same left
  join as the run's status so the declared budget did not move, and the pending
  list names that node as what ended the run instead of listing it among the
  nodes that never started
  (`tests/test_analysis_section.py::test_the_analysis_document_names_the_node_whose_verdict_ended_the_run`,
  `test_a_run_that_is_not_blocked_names_no_blocking_node`, and the workspace's
  `test_the_pending_list_names_the_node_whose_verdict_ended_the_run`). The
  Model section derives its body from Analysis' and now carries both fields
  rather than excluding them, so "no accepted forecast" says whether one is
  still coming
  (`frontend/tests/unit/model.test.tsx`'s
  `test_an_absent_forecast_says_whether_the_run_can_still_produce_one`). The
  original entry, which the same task's change makes historical:
- ~~**A BLOCKED run draws the node that blocked it as running.**~~ Both wire
  changes this entry owed have landed -- the analysis document's run status, and
  the run document's blocking node, which Task 12.4 then gave the analysis
  document too. Struck with the entry above it and kept verbatim, because it is
  the record of what the defect looked like before either field existed.
  `node_states`
  is recomputed from accepted artifacts alone (invariant 10), and a validated
  CP-5 `Blocked` accepts nothing: on a run `_end_blocked` has ended, CP-5 has
  every input met, no artifact and one unaccepted attempt, so the run document
  carries `state: RUNNABLE` with `gate_verdict: READY`, and the workspace's
  `runningOf` draws it pulsing "in the frontier" with a tally of `1 RUNNABLE ·
  0 BLOCKED` beside a `Status` of BLOCKED. The analysis document carries no run
  status at all, so that page shows `2 ACCEPTED` and CP-5 pending — the same
  page a run still in flight would show — and nothing on either page names the
  verdict. The status cell, the case register's tag and the handoff count are
  honest, and those are what `journey: an insufficient-evidence run ends
  BLOCKED and is shown as such, not as success` asserts through the production
  stack; the graph's state for CP-5 and the pending list are left unasserted
  rather than asserted as expected. Found by driving the case, not by reading.
  *Upgrade:* `reasonOf` no longer says "in the frontier" on an ended run, which
  needed no wire change. What is still owed is the analysis document carrying
  the run status, and — for naming *why* it ended rather than only that it did —
  the run document carrying which node blocked it, which `blocked_verdict` can
  supply. Both are wire changes, so a model change and an updated pinned key set
  each.

**Rebuild Phase 8 (historical).**

- **Narrative is now structured, but its figure screen is syntactic.** Task
  5.3 stores bounded paragraphs of text and anchored citation references.
  ASCII digits in text refuse; numbers spelled in words and misleading prose
  still require independent human review. Historical string payloads remain
  renderable, but cannot enter the new save API. *Upgrade:* a separately
  specified semantic review if those claims must be machine-checked.
- ~~**A citation renders without its page when the payload omits one.**~~
  Closed by Completion Phase 12 Task 12.4: `_page` refuses a page that is
  absent, not an integer, a bool, or below 1, with the same
  `DELIVERABLE_PAYLOAD_INVALID` the two fields beside it already raised
  (`tests/test_deliverable_render.py::test_a_citation_without_a_page_is_refused_like_the_fields_beside_it`).
  The original entry:
  `_citation` read `str(citation.get("page", ""))`, while `matched_text` and
  `document_sha256` beside it are refused when absent — so a payload with no
  `page` prints "page " rather than refusing. Unreachable from any real run:
  `AnchoredCitation` (`server/evidence/citations.py`) declares `page` a
  required `int` with no default, and `record_bytes`
  (`server/methodology/handoff.py`) serialises it into every stored record, so
  only an external hand-built render payload can carry a citation without one. The
  cost is a cosmetic line on the page rather than a false assurance, which is
  why it was recorded and not fixed until a task owned the renderer beside it.

**Rebuild Phase 7 (historical).**

- ~~**`_ratio` divides at the process-global `Decimal` context.**~~ Closed by
  repair Task 5.1 (§54): the entire forecast runs in one local precision-38,
  half-even context, with bounded string numerics and fixed output scales.
  `test_same_request_is_byte_identical_under_changed_ambient_context` changes
  precision, rounding, exponent limits and traps without changing output bytes.
- **The residual tolerance is absolute, in declared units.** Repair Task 5.1
  requires currency and scale and carries them with the perimeter. The default
  `0.001` therefore means 0.001 units, thousands, millions or billions as
  explicitly requested, and equality passes. Each signed debt/cash residual
  remains visible and either magnitude above tolerance makes the row unavailable.
  *Upgrade:* relative tolerance if a real model requires scale-independent
  materiality. Accessible cash currently equals closing cash; policy, restricted
  cash and liquidity runway require a later declared contract (§54).

**Phase 6.**

- **The bundle's disqualifier list conflates a fixture with thin evidence.**
  `full_run_disqualifiers` puts `SOURCE_LIMITED_NOT_COMMITTEE_READY` beside
  `INTEGRATION_FIXTURE_ONLY` and `SYNTHETIC_FORWARD_ASSUMPTIONS`. The first says
  the evidence is thin, which is true of every honest handoff over this corpus;
  the others say the document is not real work. `completeness_check` reads
  neither list, and §66 records why enforcing them as written was implemented,
  measured and rejected: it refuses seven of the 25 retained real bodies, two of
  them the accepted artifacts of the only complete snapshot, each for declaring
  the thin-evidence flag truthfully. Honouring the list whole refuses honest
  work; honouring part of it would be the host choosing which of the bundle's
  rules count, which invariant 4 forbids. Meanwhile `limitation_flags` is
  already projected and already one of `matrix.PROJECTION_FIELDS`, so a
  qualification key asserts on it today. *Upgrade:* the bundle's, not this
  host's — split the fixture markers from the evidence-status markers, and the
  first group can then be enforced as completeness while the second stays a
  projection. Until that split exists the host enforces neither, deliberately.

- ~~**Two more CP-5 columns may need T5B.5's exemption.**~~ Measured, and they
  do not. §63 exempted T5B.5's `Status` and `Claim Status`; the review that
  proposed it flagged `T5B.3 Traceability Status` and `T5B.7 Assessment` as
  possibly the same shape, on reading rather than on evidence. Every CP-5 body
  this repository has retained — nine, across every live run including the three
  that were refused — was parsed for those two columns: **no cell in either
  holds any of the seven disqualifying phrases.** Where CP-5 records restraint
  it records it in the two columns already exempt. So the exemption is not owed,
  and widening it would weaken the disqualifiers for a case nothing has produced.
  *Upgrade:* none. If a future run is refused on one of those columns the
  evidence will say so, and the change is then one line with a run behind it
  rather than a guess.

- ~~**Nothing can sign a verdict.**~~ Closed by
  `server/api/commands/qualification.py` (`docs/DECISIONS.md` §65):
  `POST /api/v1/qualification/{evidence_sha256}/verdict` takes the reviewer's
  six-binding document, reads it with `read_verdict` against the store's
  clock, and calls `record_verdict` with `reviewer_id` taken from the
  authenticated `Actor` and from nowhere else — a body naming one is refused
  as undeclared before a connection opens. The floor is the top global rank
  (`ADMIN`, by `at_least`), because a verdict is the first authority here that
  is account-wide rather than case-scoped; below it, and for evidence the store
  does not hold, the answer is one private 404. What it does not do: nothing
  here lets the host call itself qualified — the route records a person's
  assertion over evidence `record_verdict` already bound, and refuses when the
  snapshot is not `complete` or the bindings do not match. Both of the limits
  this entry recorded are closed by Task 8.3: the one-verdict constraint is
  mapped by its declared name to `VERDICT_ALREADY_RECORDED` (409), so a
  retried request can tell "already signed" from "wrong bindings"
  (`test_a_second_signature_over_the_same_evidence_is_already_recorded_not_invalid`,
  `test_the_one_verdict_constraint_is_mapped_by_name_not_by_message`); and the
  write now records a `command_requests` receipt under the nil scope in the
  verdict's own transaction, so a replayed request is answered from it
  (`test_a_replayed_signature_with_the_same_key_is_answered_by_its_receipt`,
  `test_the_verdict_command_requires_an_idempotency_key`).
- **The run-to-case binding lives in the matrix's only caller, not the matrix.**
  `build_matrix` accepts any `runs` mapping and checks only that a label is
  present; everything that makes a run the case's run — title, ceiling, profile,
  selection, documents, provider, model — is enforced in `harness._eligible`.
  Correct today because `perform` is the only path, and the transplant suite
  proves it there. A second caller gets none of it. *Upgrade:* make
  `build_matrix` private to the harness, or move the binding into it, the day
  anything else wants a matrix.

- ~~**CP-5 cannot say a claim is unverifiable in a column its contract calls
  critical.**~~ Closed by `docs/DECISIONS.md` §63, the owner's second
  authorised override of invariant 4: T5B.5's `Status` and `Claim Status`
  now sit in `disqualifier_exempt_columns`, beside T5B.3's `Claim Status`
  and T5.2's `Evidence Status`, and the three refused bodies of run
  `36d87283…` replay clean while a placeholder in any of T5B.5's seven
  substantive columns is still refused
  (`test_cp5_exempts_only_its_status_columns_from_the_disqualifiers`). The
  build moved with it, `cdea0c9f` -> `30222a49`. The original entry, for the
  reader who wants the reason: `cp-5-evidence-trace-validator/SKILL.md` lists `insufficient
  information`, `not calculable from provided materials`, `not assessable` and
  `unavailable` among `critical_cell_values_casefold`, and T5B.5's Claim Status
  column exempts none of them. Run `36d87283…` refused CP-5 three times,
  `$0.856` of billed attempts, each for writing one of those phrases about a
  claim two earnings releases genuinely do not support — which is the answer
  CP-5's own runbook asks it for. A module that traces claims to sources can
  then pass only by overstating what the evidence carries. Run `42e17048…`'s
  CP-5 was accepted over the same corpus because it phrased the same restraint
  differently, so what the rule selects for is wording. The projection keys
  cannot see it either: a refused CP-5 leaves no artifact, so its conclusion is
  unreadable and the row reads as a run that stopped. *Upgrade:* the mechanism
  exists — `disqualifier_exempt_columns`, which T5.2 already uses for
  `Evidence Status` (the entry as first written credited T5B.6, which exempts
  `Classification`) — so the question is which of CP-5's status columns should
  carry it. A bundle change, needing its own authorisation, and it belongs with
  the `completeness_check.load_contract` half §61 left open.
  Deferred by the owner on 16 September 2026 (`docs/DECISIONS.md` §62) and
  resolved by the owner's instruction the same day (§63).

- ~~**`CONDITIONAL` is a CP-0 verdict with no stated meaning and no discharge.**~~
  Closed by `docs/DECISIONS.md` §61, the owner's authorised override of
  invariant 4: the verdict now names a source the effective-source set does not
  carry, says how it is discharged, and says an upstream analytical handoff not
  yet produced is never a readiness ground — in the same words in all three
  places CP-0 reads it, with `test_cp0_defines_conditional_as_a_source_condition_everywhere_it_is_read`
  failing the day one of them drifts. The build moved with it, `a43cb903` ->
  `cdea0c9f`. The original entry, for the reader who wants the reason:
  `cp-0-source-readiness/SKILL.md` defines it only as "emit `DO NOT RUN`", and
  nothing there says the condition must be a *source* condition — while line
  359 of the same file says source readiness must not assert whether upstream
  analytical handoffs exist. Run `62698a60…`'s CP-0 marked CP-5 `CONDITIONAL`
  on "CP-L10 must first produce the selected-route analytical handoff", which
  is the sequencing claim that line forbids, and the route ended BLOCKED with
  two modules paid for. Nothing discharges the status inside a run: the
  vendor's own `prepare_invocation.py` and `handoffs.py` refuse a conditional
  module exactly as `server/engine/route.py` does, so the host is faithful and
  the misuse is terminal either way. *Upgrade:* the bundle's, in a new build —
  define the condition as source-only, name its discharge, and say that an
  upstream-handoff dependency is never a readiness ground. What the host may do
  without editing upstream is quote line 359 verbatim in `_GATE_INSTRUCTION`,
  which restates the bundle rather than adding to it (done, `a40b2b4`). The set
  also measures the failure directly through `expects_ready`.
- **The bundle gates per consumer; the owner's statement of intent does not.**
  Told on 16 September 2026 that CP-0 "only classifies the documents to assess
  which pathways are available", the audit found the vendored methodology says
  otherwise: `SKILL.md` §331 requires readiness "against the evidence demand of
  each proposed downstream module", §349 a verdict per consumer, §357 `DO NOT
  RUN` for CONDITIONAL and BLOCKED, and `CANON_SHARED.md` §632 "CP-0 determines
  readiness". The vendor's own scripts refuse a non-ready module. So the host
  enforcing it is invariant 4 working, and a host that stopped would be
  dropping a constraint the bundle states. *Upgrade:* a dated decision entry
  saying which governs. If the intent is policy, it is a bundle change and a
  new build, not a host change — this entry exists so nobody closes the gap by
  quietly weakening `route.py`.

- **The borrowing-capacity key names a subordinate clause, not the fact.** One
  block per line (§5's group is unbuilt), so the sentence on Q4 page 4 is three
  blocks, and the key is the first: "When compliance reporting requirements
  have been completed and assuming no change from 31". The credit content is
  the *next* line. Seven v3 handoffs have cited 13 distinct lines between them
  and none has cited this one, while Terra's CP-L10 twice paraphrased the whole
  sentence correctly in prose. The key is satisfiable -- all three lines are
  candidates -- but it asks a module to quote the clause that carries no fact.
  Moving it from CP-0 to CP-5 earlier today moved the wrong thing. *Upgrade:*
  name the fact-carrying line, or the sentence as a block range once §5's
  bounded line group exists, and note that the AFCF key's text appears in both
  releases, so a module citing the Q3 copy misses a key aimed at Q4.
- **A citation key measures neither the conclusion nor its soundness.** Terra
  stated the borrowing condition correctly and scored a miss; DeepSeek's CP-0
  claimed `Committee Ready` at 93 over a self-declared MATERIAL source gap and
  was accepted. The Phase 10 entry conceded the first half of this; the second
  is worse, because the apparatus is silent where the answer is wrong rather
  than merely differently evidenced. The host already projects the fields that
  would say so -- `qa_status`, `committee_status`, `confidence_score`,
  `limitation_flags`, CP-0's T8 readiness rows -- and the bundle ships a
  register parser. *Upgrade:* keys of the form
  `(module, register_id, row, column, expected)` over those projections, the
  pattern `ExpectedForecast` already uses.
- ~~**The host accepts a handoff the vendor's own rule contradicts.**~~ Half
  closed by `docs/DECISIONS.md` §61: `validate_handoff.py` now reads every
  unfenced table headed `Severity` and refuses CRITICAL under any status but
  `Blocked`, MATERIAL under `Passed` — the canon's own rule, which it had never
  enforced. Verified against the artifact that exposed it: the DeepSeek CP-0
  declaring `Passed` at 93 over its own MATERIAL row now errors with the body
  line, and every module of the passing run still validates clean. What is
  still open is the second half, `completeness_check.load_contract`, which reads
  only the `critical_cell_*` disqualifiers and never
  `frontmatter_limitation_flags`, `frontmatter_validation_warnings` or
  `document_substrings_casefold`. That is a different rule with different
  semantics and needs its own authorisation and entry. The original, for the
  reader who wants the reason:
  `validate_text` checks `Restricted -> <=59` and `Blocked -> <=39` and nothing
  the other way, and `completeness_check.load_contract` reads only cell
  disqualifiers, never the `frontmatter_*` ones. So a module may declare a
  MATERIAL source gap and still call itself `Passed` / `Committee Ready` at 93,
  which DeepSeek's accepted CP-0 did minutes before the same model's CP-L10 was
  refused for breaking the same rule in the direction the validator does check.
  Invariant 4 says the bundle is the authority and the host adds nothing, so
  this is the bundle's gap to close -- but a reviewer reading an accepted
  artifact should know the host asserted nothing about it. *Upgrade:* none the
  host may take alone; record it against the bundle.
- ~~**`expected_refusal` cannot be met by any run this system can produce.**~~
  Closed. It read only the proof's refusal, and a validated Blocked handoff
  leaves a sound proof and writes no `attempt_refusals` row -- while `complete`
  demanded every run reach `COMPLETE`, which a blocked run never does. Both
  halves now read the run: `_refusal_met` takes the proof's refusal, a recorded
  attempt refusal, or `HANDOFF_BLOCKED` against a run whose own status is
  BLOCKED; and `complete` exempts a case from the `COMPLETE` requirement when
  the refusal it declared was met, because declaring a refusal is declaring
  that the run will not finish. The "deliberately restricted case"
  `docs/REPAIR_PLAN.md` Phase 6 names is now expressible, and
  `test_a_case_that_declared_the_block_it_expected_is_signable` proves it over
  a real blocked run rather than a hand-built dataclass.

- **The VMO2 set measures two of its three modules by key.** CP-0's expectation
  asked `SourceReadiness` for the issuer's current borrowing-capacity
  statement, which is a credit fact and belongs to CP-5's reading; it was moved
  there on 16 September 2026 and the set digest moved with it
  (`ec84bf8b…` → `ae70850d…`), so the two runs performed are not comparable to
  anything after. CP-0 is still measured by its proof — artifact accepted, host
  record valid, every citation anchored — but not by evidence selection, which
  is the half a key adds. *Upgrade:* a CP-0 expectation authored the way the
  original was, from the Q4 release and CP-0's own contract. It must not be
  taken from what either run cited: their output is on the record now, and a
  key chosen from it would measure the model against itself.

- ~~**A billed call whose diagnostic body cannot be stored is billed again.**~~
  Closed the same day it was raised. `_diagnostic` returning no body still commits the charge with
  `diagnostic_sha256` NULL, and `replay_billed` excludes exactly those rows, so
  the next pass over the node starts a fresh attempt, reserves again and calls
  the provider again. Nothing between `replay_billed` and `start_attempt` asks
  whether the node already holds a charged, unexplained, body-less outcome. The
  run ceiling bounds it, so this is two charges for one node rather than an
  unbounded spend, but it happens with no operator decision in between — and
  `docs/DECISIONS.md` and the handoff both say every typed store fault releases
  the attempt for safe replay, which is not true of this one. *Upgrade:* one
  query beside `replay_billed` in `_drive` for a ready node with a ledger charge,
  no artifact, no refusal row and a NULL diagnostic, raising a code that is not
  in `_NOT_AN_EXPLANATION` so the second charge is an explained, requeued
  decision. That is what `canonical.unexplained_charge` now is: `_drive` asks it
  for a ready node with a ledger charge, no artifact, no refusal row and a NULL
  diagnostic, and refuses `CALL_OUTCOME_UNEXPLAINED` before reserving anything.
  The run parks with the code, which is the operator's decision this entry said
  nobody was making. Paying again is still allowed -- it is just chosen now.
- **The post-bill original recheck is a fault point, and it stays.** Recorded
  because the Phase 6 adversarial audit asked for its removal and that
  recommendation was not taken; a contested finding is worth a ledger entry
  either way.
  `_answer` re-reads every original PDF after the money is spent, but the
  answer's validity does not depend on those bytes: evidence comes from
  `source_blocks` and `source_tokens`, the record embeds no original, and
  `assert_orchestration_proof` never opens one. What the recheck adds is a
  fault point between the charge and acceptance, where a transient `OSError` on
  a multi-megabyte read leaves a billed, unexplained node. The pre-call check in
  `_source_preparation` is the one with a consumer, and replay runs it again
  before any new spend. The audit is right that the recheck guards no reader.
  It is wrong about the price: v3 also made `BLOB_*` faults re-raise out of
  `replay_billed` rather than become a verdict, so the billed node this recheck
  can strand is replayed from its stored body once the original is restored --
  `test_a_lost_original_after_billing_replays_after_it_is_restored` is that
  path. A recoverable fault point that re-verifies a pinned digest against the
  store is the direction invariant 3 asks for, so it is kept.
  *Upgrade:* none planned. Revisit if a real run is ever stranded here, which
  would mean the recovery does not work as that test claims.
- ~~**A filename an admitter chose is rendered under a host-attributed marker.**~~
  Closed the same day it was raised.
  `invocation.py` writes `member.filename` inside `HOST SOURCE PREPARATION`,
  which the prompt labels host-owned, and `_TAGGED` warns the model only about
  untagged *markers*. `BoundaryText` accepts U+FEFF, U+2028 and U+2029 that
  `handoff._INVISIBLE` refuses, so a document admitted under such a filename,
  copied into CP-0's inventory exactly as the instruction demands, is refused
  `HANDOFF_MALFORMED` — a host defect recorded as the model's answer. Cannot
  fire on a frozen ASCII corpus, which is why it is recorded rather than fixed
  under an authorized run. `invocation._printable` now drops those characters
  from the rendered filename, and `handoff.INVISIBLE` is public so the prompt
  builder and the reader that refuses them cannot drift apart. The document
  keeps its real name everywhere the host owns the comparison. *Upgrade:* the
  section's own label still says "host-owned preparation metadata" without
  saying that its string values are not instructions; worth adding the day a
  document is admitted by anyone but this repository's operator.

- **Identity before the store rests on parameter order.** Every section read
  (`server/api/reads/*.py`, since §50 the retired `read_run`'s successors) and
  `read_case_events` declare `actor: Caller` ahead of `conn: Store`, and that is
  the whole of what refuses an anonymous request before a connection is opened:
  FastAPI builds a route's dependency list in signature order (`get_dependant`)
  and solves it sequentially (`solve_dependencies`), so the ordering is a
  property of a pinned dependency rather than something the code says out loud.
  `test_an_anonymous_request_opens_no_store_connection` counts the dependency's
  calls, so a reorder and a FastAPI that stopped doing this both fail there --
  which is what makes this a limit rather than a defect. Since §73.4 the order
  is remembered in one place rather than per route: all twenty-one routes reach
  the store through shared dependencies in `server/api/deps.py`, and the
  store-touching one resolves the actor before the connection in its own
  signature, so it cannot be ahead of identity even where a route declares it
  first. That makes the property hold more robustly and does **not** discharge
  this entry, because it still holds by signature order. *Upgrade:* unchanged --
  `dependencies=[Depends(actor_from_request)]` on each decorator, which FastAPI
  inserts at the front of the list whatever the parameters say. What has gone
  is the reason to defer it: the order no longer has to be remembered per
  route, so the change is now one edit per decorator over one known set.
- **A case stream polls.** `server/api/stream.py`'s `case_tail` re-reads the
  case's audit actions, the run's events and the caller's standing every
  `POLL_INTERVAL` (0.5 s) until `TAIL_DEADLINE` (300 s) or standing is lost,
  on one store connection held for the stream's life. Every §9 rule holds and
  events are timely, but an idle watcher costs three queries a poll -- six a
  second -- while its run is open, and two a poll once the run's terminal is
  delivered, per open connection, with one more standing check per named
  frame. *Upgrade:* `LISTEN`/`NOTIFY` on the event and audit appends, making
  the poll a fallback rather than the mechanism; worth doing when there are
  enough concurrent watchers to measure it, not before.
- ~~**The role an actor carries is global, and nothing reads it.**~~ Closed
  by Phase 4 Task 4.2 (§51.2): every command reads the global role -- create
  case and every case-scoped write refuse a global READER `NOT_AUTHORISED`
  whatever its case standing -- and the section reads' availability does the
  same. Case standing is still the authority checked at commit.

- ~~**`GET /api/health` is specified and not served.**~~ Closed by Phase 4
  Task 4.5b (§53.8): `server/api/health.py` serves a closed `HealthDocument`
  from probes of store, bundle and blob root run every 10 s on one lifespan
  task, 503 unless all three are `OK` and fresh, with no identity, token or
  I/O on the request. The worker still serves none (Repair Phase 4 above).

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
- **A run's price is supplied by its caller; what it buys is now priced and
  recorded.** `docs/DECISIONS.md` §40: `run_route` refuses a price for any model
  but the provider's configured one before an attempt exists. Two of the three
  things this entry asked for are done, by Completion Phase 8 Task 8.2. A
  reservation is priced on the request that was actually built and bounded --
  `pricing.priced_request(price, invocation.request_size(provider, prompt))`,
  input per request byte because a token is at least one byte, output at the
  completion cap -- rather than on `MAX_REQUEST_BYTES`, so the ~$3.64 worst case
  that stopped a two-node route finishing under the $5 default ceiling is no
  longer what is set aside: three LITE nodes now fit one ceiling
  (`tests/test_loop_charges.py::test_a_small_prompt_reserves_its_priced_cost_not_the_byte_ceiling`).
  `worst_case` stays the run-ceiling admission check, so invariant 8's "refuse
  before overspend" is unchanged. And migration `0024` stores the dated price
  beside the amount (`price_model`, `price_input`, `price_output`,
  `price_as_of`), so a row reads back to what produced it rather than only to a
  number
  (`tests/test_budget.py::test_a_reservation_records_the_dated_price_that_produced_it`);
  rows written before it say `legacy` and keep their amounts
  (`tests/test_store_schema.py::test_the_migration_keeps_existing_reservation_amounts`).
  Pricing the request rather than the ceiling creates a hazard the ceiling hid:
  the loop prices the prompt `check_context` built, and the attempt unit builds
  its own again, so a larger rebuild would be sent under too small a
  reservation. `canonical._within_reservation` re-prices the request about to be
  sent against the price its reservation was taken under and refuses
  `CONTEXT_OVER_CEILING` before the provider is reached
  (`tests/test_loop_charges.py::test_a_prompt_rebuilt_larger_than_the_one_priced_is_refused_before_the_call`,
  which was watched failing with the guard removed). That guard borrows
  `CONTEXT_OVER_CEILING`, whose clearance text reads "Deliver less context to the
  module" -- true of the ceiling check it was written for and misleading here,
  where the context is unchanged and the reservation no longer covers it. The
  code is right and the sentence a reader gets is not.
  **Three things remain, and they are listed together rather than each beside its
  own paragraph, because an entry carrying an upgrade clause per sentence is one
  nobody reads to the end of.** First, nothing in the tree says what the live
  model costs, so `tests/test_live_run.py` still prices it from a flat estimate,
  and every priced reservation is exact arithmetic over an unconfirmed number.
  Second, the qualification driver does not see the saving:
  `server/qualification/harness.py`'s `_affordable` still refuses
  `QUALIFICATION_SET_OVER_CEILING` when `worst_case(price) x len(route.nodes)`
  exceeds a run's ceiling, so at Terra's rates three LITE nodes are refused
  against the $5 default before any case is prepared, and `scripts/qualify.py`
  admits exactly what it admitted before this task even though `run_route` now
  finishes such a run. That sentence left the tree in a rewrite and is restored
  here, which is the failure this ledger's own gate exists to catch, read the
  other way round. Third, the borrowed clearance above.
  *Upgrade:* a user-confirmed dated price for the configured live model, which is
  the owner's to give; the harness's floor priced on measured requests, or per-run
  ceilings derived from the set's, which is what the Rebuild Phase 10 entry "a
  qualification run costs real money" already owes; and a refusal code of its own
  for the reservation check, the day an operator meets it on a real run. The
  second and third were found by the Task 8.2 acceptance review.
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
- **The gate's evidence demands are dropped, and the host cannot read them at
  all.** A readiness row keeps `module_id` and `readiness` -- **two** fields, not
  the three this entry used to claim: `readiness_effect` appears nowhere under
  `server/` and is not a field of the vendor's `Recommendation`. The entry
  described the JSON payload schema's row as though it were the host's record,
  which is the error that matters here, because the same confusion is what the
  repair was specified against. CP-0's *schema* also declares `evidence_demand`,
  `active_representation_ids` and a `content_to_module_map` (`docs/DECISIONS.md`
  §27), and those live in `runtime_output` -- which
  `invocation.py`'s `_FINAL_CHECK` explicitly tells the model **not** to author,
  naming it among the fields that belong outside canonical front matter. So the
  host asks CP-0 not to produce the very rows a per-module selection would read,
  and no accepted record has ever carried one. The two ways to invent the fact
  both breach invariant 4: all sixteen CP-0 registers declare `columns: none`,
  so parsing the Markdown means a host table contract the bundle does not state;
  and T8's fifth column, `Source files to attach`, is validated for row width by
  the vendor and then discarded -- `parse_t8` reads cells 0,1,2,3,6,7 and never
  cell 4 -- so keeping it would make the host a second reader of one table that
  can disagree with the bundle's own. The catalog offers no third way: no
  `evidence_demand`, `active_representation`, `source_files` or `evidence_class`
  appears in it. Measured by Completion Phase 10 Task 10.1, which stopped rather
  than build. *Upgrade:* not per-module selection as specified. It needs one of
  three things first -- a bundle build whose `Recommendation` carries T8's fifth
  column, which is the smallest and keeps invariant 4; or a dated decision taking
  host ownership of a CP-0 register's shape, in the pattern of §61 and §63, which
  has to answer whether a model-authored register may decide what evidence a
  *downstream* node can cite; or a selection rule needing no gate row at all,
  which narrows nothing and closes none of the entries this one is grouped with.
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
  not happen. The cause is not lost: the readiness the gate
  recorded is on the artifact and is where the state came from, and the run
  surface carries it as `NodeView.gate_verdict`. (This entry said
  `readiness_effect`, a field the host does not keep -- the same schema-for-record
  confusion corrected in the evidence-demands entry above.) Widening `limitations_of` is
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
  **That day is measurable and close.** On the catalog's widest
  pathway, `FULL_CREDIT_32/FULL_CREDIT_ASSESSMENT`, CP-5 carries **16 direct
  upstreams**, and its own delivered authority is 165,548 bytes. At a modest
  20 KB per upstream handoff the authority and upstream sections alone come to
  493,228 bytes -- 47 % of `MAX_REQUEST_BYTES` -- before a single byte of
  evidence, and the evidence section carries every block of every pinned source.
  The only route ever measured is LITE's, three nodes and at most two upstreams,
  whose prompts run about 210 KB. So the first FULL pathway to run is a
  plausible `CONTEXT_OVER_CEILING`, which refuses the whole request rather than
  truncating it: the run does not proceed at all, and a pathway that cannot run
  cannot be qualified. Measured on 17 September 2026 from the vendored catalog
  and the bundle's own authority bytes, because nobody had taken the number this
  deferral rested on.
  *Upgrade:* a declared per-section bound, owed with Phase 11's first wide
  pathway rather than on a future measurement, and Phase 4's lease fencing the
  node's inputs between the two checks.

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

- **A route's predicates are frozen and never evaluated, and an edge that would
  need one is refused.** `ResolvedRoute` carries them, `route_digest` covers
  them, and `server/store/routes.py` writes and reads them back — and no code
  consults them. That is the fail-closed direction, and the only one available:
  a condition the host cannot evaluate must not be assumed met, and the
  predecessor's failure was the opposite — edges that did not enforce what they
  claimed. But invariant 10's "frozen predicates" are, for now, frozen without
  yet being predicates, and a reader of the pin could take the presence of a
  predicate for its enforcement. What closes the reachable half of that reading
  is Completion Phase 10 Task 10.2: `_edges_among` refuses
  `ROUTE_EDGE_UNSUPPORTED` for a `CONDITIONAL` **edge** before the `Edge` is
  built, so no such route resolves and none can be pinned — where before it
  would have pinned a route whose target blocks whatever the evidence said. The
  refusal is scoped to the route, not to the bundle: the membership filter runs
  first, so a CONDITIONAL edge whose source or target is outside the resolved
  node set is skipped as any other out-of-route edge is, and a build carrying
  one off every pathway refuses nothing. That is deliberate — an edge no pin
  carries misleads no reader of a pin — and it means this guard fires at the
  first build that puts such an edge **on a resolved route**, not at the first
  build that declares one anywhere. `CONDITIONAL` stays in `BLOCKING` and stays
  in the bundle's vocabulary (`CONTEXT.md`): it remains a CP-0 *verdict*, which
  `tests/test_route_resolution.py::test_a_conditional_verdict_blocks_like_a_blocked_one`
  still holds, and only an edge of that type is refused. The refusal is a 503:
  the pinned build's own catalog, not the caller's request, and no profile or
  pathway a caller could name instead would avoid it. The branch is unreachable
  on this bundle — the vendored catalog declares 60 REQUIRED, 26 OPTIONAL, 29
  ADVISORY and one QA_GATE typed edge and **no** CONDITIONAL edge, pinned by
  `tests/test_bundle_pin.py::test_the_catalog_declares_no_conditional_edge`
  since `4f06337` and now as a whole census, through the engine and against a
  mutated copy, by
  `tests/test_bundle_pin.py::test_the_vendored_catalog_carries_no_edge_this_engine_cannot_evaluate`
  — so a grammar written for it today would be code for a route that does not
  exist. `tests/test_route_resolution.py::test_a_profile_with_a_conditional_edge_is_refused_at_resolution`
  is the guard, and
  `test_the_four_edge_types_this_engine_evaluates_still_resolve` says the guard
  is one type rather than a narrowing of the other four. *Upgrade:* an
  evaluator, owed the day that guard fires — which is also the first day an
  upstream build carries a real predicate for a grammar to parse, and the day
  the frozen `predicates` field has something to be read against.

**Phase 2.**

- **A quote matches whole tokens exactly, typography at its edges aside.**
  `matched_text` is split on whitespace and each word must equal a token,
  punctuation included -- except that the first and last tokens of the body's
  window may carry quotation marks (`_QUOTATION`). That exception was paid for:
  a module writes its Evidence Trace as prose, prose puts quotation marks
  around a quotation, and the CP-L10 attempt of the second paid Terra run was
  refused `HANDOFF_MALFORMED` for `“The preliminary` where the quote said
  `The preliminary`. It is the body check only -- `verify_citations` still
  anchors against the document's own tokens exactly, so nothing about what may
  be cited moved. A module
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
  that transaction cannot roll back. The admission command (§51) extracts
  before any transaction but still puts each document's bytes inside its
  governed unit (`admit_prepared`), so a unit that fails after a put -- a
  store fault on a later insert, the audit link or the commit -- leaves them
  too.
  The orphans are harmless — content-
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
- **The recorded digests prove the declared history did not change, not that the
  database still matches it.** `apply_schema` compares each migration's SHA-256
  against its `store_migrations` row, and the SHA-256 of the whole ordered
  `(version, name, digest)` history against `store_schema.applied_digest`. It
  reads no `information_schema`, so a table altered or dropped outside this code
  afterwards passes unnoticed. What it catches is a declared history that
  disagrees with the applied one — edited, reordered, missing, or newer than this
  build knows — and not tampering, which `docs/DECISIONS.md` §20a says in the
  same breath as the migration policy: a checksum cannot see a change made to
  the schema and its metadata together. The older database this entry used to
  name as the caught case is no longer refused at all; §20a's prefix advancement
  migrates it. *Upgrade:* apply the declared schema into a scratch namespace and
  diff `information_schema` against the live one, the day a database is edited by
  anything but this function.
- ~~**`budget_ledger` records a charge and enforces no ceiling.**~~ Closed by the
  phase its own upgrade path named. `server/store/budget.py::_reserve` refuses
  `BUDGET_CEILING_REACHED` under the run row lock before any call, and
  `_remaining` subtracts `greatest(reservations.amount, ledger.amount)` per
  attempt, so a charge that came in above its reservation consumes the capacity
  the next reservation is measured against.
  `tests/test_budget.py::test_a_reservation_past_the_ceiling_is_refused_before_it_is_taken`
  and `test_concurrent_reservations_at_the_ceiling_refuse` hold it. What cannot
  be refused is a bill already incurred, which is not this entry's claim and is
  covered by the Repair Phase 2 entries on indeterminate exposure. Found by the
  Completion Phase 7 confidence review, which is the reason the entry above this
  one says the gate cannot read prose.
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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **caos-v2** (10131 symbols, 24716 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/caos-v2/context` | Codebase overview, check index freshness |
| `gitnexus://repo/caos-v2/clusters` | All functional areas |
| `gitnexus://repo/caos-v2/processes` | All execution flows |
| `gitnexus://repo/caos-v2/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
