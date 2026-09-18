# The delivery backlog — measured 18 September 2026

> **Superseded in its central claim, 18 September 2026, later the same day.**
> This file says main is "mostly behind" this branch. Measured against the
> merge itself rather than against file lists, that is wrong. `git merge-tree`
> of `delivery/task-21` into `gh-origin/main` (`9b9b584`) conflicts in **195
> files**, `delivery/phase-12` in 211, and `HEAD` in 218. For each conflicted
> file, the test was whether main's blob appears anywhere in this branch's own
> history of that file. **125 pass**: main holds an older state of our own
> file, and our version wins without argument. **70 do not**: main has content
> this branch never had. They sit in the core, including `server/api/edge.py`,
> `deps.py` and `app.py`, `server/store/__init__.py`,
> `server/methodology/canonical.py` and `handoff.py`, CI and the Dockerfile.
> In each sampled case both sides changed the file by a similar amount since
> the merge base. Main's own stream, the `deploy/*` pull requests #312 to
> #320, has been refactoring those same files: de-privatised helpers,
> `committed_unit`, the extracted edge helpers. **None of the snapshot pull
> requests below can merge as they stand.** Delivery now needs one deliberate
> reconciliation of the two streams, with the `deploy/*` stream paused while
> it happens. The 70 real conflicts are a task, with the full gate after it,
> not a side effect of opening a pull request.

`codex/execute-repair-plan` is `abb509e`; `main` is `971c69f`. This file records
what main is missing, how it was measured, and what the options cost. It is a
record for the owner, who alone performs delivery: nothing in this repository
pushes or opens a pull request.

## The shape, and the thing that is easy to get wrong

**Main is mostly behind this branch rather than diverged from it -- but not
strictly behind.** The obvious reading of the commit graph is wrong, and so was
the first correction of it; both are written down, with what settles the
question at the end of this section.

`git cherry HEAD main` reports 131 of main's 180 commits as "missing" from this
branch. They are not. They are **squashed pull-request merges of this branch's
own earlier work** -- `(#119)`, `(#124)`, `Repair Phase 3 Task 3.1a-1 (#158)`
and so on. Squashing rewrites the patch-id, so `git cherry` cannot match them.
Checked by content instead, on three samples from different eras, all present
here:

| main commit | on this branch |
|---|---|
| `971c69f` (#317) the extraction child's exit status | `return out, child.returncode` in `server/evidence/pdf.py` |
| `8086d29` one canonical-JSON digest module | `server/digest.py` |
| `b0b5fcf` a tokenless deployment believes no client header | the rules in `identity.py` and `edge.py` |

**Do not merge main into this branch.** It was tried in a scratch worktree and
produces **215 conflicted files** -- every one an artefact of re-applying a
squashed copy of this branch's own work. The worktree was removed and `HEAD`
was not touched.

**And main is not strictly behind either -- 24 files exist there and not
here.** This was measured after the paragraph above was written, and it
narrows it: `git diff --diff-filter=D --name-only main HEAD`. Most are
deliberate -- the Book, Committee, Report and Model components and the
pre-`v1` `wire/*.ts` modules that Phase 12 replaced. Four are not, and they are
the reason this is a **two-way merge rather than a fast-forward**:

| file | what it is |
|---|---|
| `server/deliverable/host.py` | maps the portable renderer's `RenderRefused` to a closed `RefusalCode`. **Nothing on this branch catches `RenderRefused` at all**, and nothing needs to yet: `render()` has no production caller here, only tests. It becomes a real gap the day a route serves a rendered deliverable |
| `tests/test_digest.py` | main's dedicated test for `server/digest.py`, which this branch has without that test |
| `tests/test_api_deps.py` | direct unit tests for `deps.py`'s id parsers. This branch covers the same parsers inside `tests/test_api_routes.py` instead |
| `tests/test_pdf_page_frame.py` | `page_frame` in the section 47 child |

Any delivery must triage those four rather than assume them superseded.

**Main is not a *prefix* of this branch either.** It carries §75's
`TRANSIENT`/`PERMANENT` split (Task 21, newer) while lacking Phase 8's document
register (older), so it received independent pull requests rather than a linear
series. A stacked series in branch order will therefore not apply cleanly, and
delivery units have to be chosen by *concern* rather than by commit range.

## What main has, and what it lacks

Probed by marker file:

| | |
|---|---|
| **has** | the audit remediation (`server/api/deps.py`), §75 (`TRANSIENT`/`PERMANENT`), Phase 7.1's ledger gate (`scripts/ledger_state.py`, `tests/test_ledger.py`) |
| **lacks** | Phase 8 (`scripts/document_register.py`), Phase 9.1 (`tests/test_lite_portfolio_route.py`), Phase 10.3 (`server/store/0025_supersedes.sql`), Phase 12 (`server/api/reads/book.py`, `server/api/commands/deliverable.py`), Phase 13 (`server/store/0028_worker_heartbeats.sql`, `tests/test_concurrent_frontier.py`) |

So the frontier is **Phase 7**, and everything from Phase 8 onward is
undelivered. All of it is dated 17-18 September 2026.

## The size, measured two ways

The commit counts mislead, because squashing breaks the correspondence. The
**tree difference** is what main is actually missing:

```
git diff --shortstat main HEAD
  398 files changed, 45837 insertions(+), 8657 deletions(-)
```

| area | |
|---|---|
| `server` | 69 files, +6,422 / -1,508 |
| `frontend/src` | 62 files, +1,819 / -2,488 |
| `tests` | 98 files, +9,678 / -1,575 |
| `docs` | 53 files, +15,341 / -129 |
| `scripts` | 6 files, +436 / -42 |
| **code only** | **131 files, +8,241 / -3,996** |

By concern, for grouping pull requests:

| concern | |
|---|---|
| Phase 8, the qualification instrument | 9 files, +1,587 / -187 |
| Phase 9.1, LITE portfolio decision | 1 file, +268 |
| Phases 10.2 / 10.3, route semantics | 3 files, +250 / -24 |
| Phase 12, backend | 23 files, +2,449 / -561 |
| Phase 12, frontend | 62 files, +1,819 / -2,488 |
| Phases 10.5 / 13, engine | 6 files, +876 / -152 |

## The number that decides the approach

`scripts/check_pr_size.py` counts added **plus** removed lines against a limit
of **800**, excluding `docs/**`, `vendor/**`, `frontend/fixtures/**` and
lockfiles. Root `CLAUDE.md` is **not** excluded, and it alone is 1,754 counted
lines -- more than two pull requests for one file.

Applying the gate's own pathspec to the whole backlog:

```
  counted: 34,581 lines  (28,128 added, 6,453 removed)
  => at least 44 pull requests at the 800-line limit
```

The `size` job in `.github/workflows/ci.yml` runs `if: github.event_name ==
'pull_request'`. It is a policy about how pull requests are reviewed, not a
correctness gate, and it does not run on a direct push.

## Deliver by gated snapshot, not by file-set

Tried and abandoned, so nobody tries it twice: **reconstructing a phase as a
file-set does not work.** A `delivery/phase-8` branch was built off main by
taking Phase 8's owned files at their head state. It did not import --
`matrix.py` needs `server/methodology/verification.py`, which main lacks. Adding
that, its tests then needed `qualification/documents.json`; then the **vendored
bundle**, because main is on build `a43cb903` and the register keys need
`30222a49`, the build §61 and §63 moved it to; then `methodology/vendor.py`;
then the rest of `server/methodology/`, at which point the closure was still
expanding into the engine and the store. The worktree was removed.

The tree is cohesive, which is a virtue in the code and a cost in delivery.
What the experiment *did* establish is that the modules Phase 8 reaches carry
**no commits since Phase 8's own acceptance**, so a cut at that point is
semantically clean even though a file-set cut is not.

So deliver **commits, not file-sets**. Each of these is a real commit that
already carries an acceptance record and a green `make check`, and each PR's
base is the previous one's head:

| # | base -> head | what | counted by the gate |
|---|---|---|---|
| 1 | `main` -> `7e60121` | Completion Phases 7 and 8 | 23,319 |
| 2 | `7e60121` -> `29b2208` | Task 21 / §75, the 500-503 split | **265** |
| 3 | `29b2208` -> `4d7af97` | Completion Phase 12, accepted | 8,360 |
| 4 | `4d7af97` -> `HEAD` | Completion Phase 13 and Task 10.5 | 3,638 |

Only #2 fits the 800-line gate. The other three are the over-cap case, and each
has the thing that justifies it: an acceptance record naming its gates. **#1 is
the hard one** and it is hard because main is behind by much more than Phase 8 --
it is the accumulated remainder of everything the squashed pull requests did not
carry.

One ordering constraint, found the same way: **the vendored bundle must move
first or with #1.** Phase 8's register keys read registers through the bundle,
and on build `a43cb903` they answer `registers_met=False`. `vendor/**` is
excluded from the size gate, so that part costs nothing against it.

## Three options, with what each costs

1. **Forty-four stacked pull requests.** Honours the gate as written. It is
   also weeks of review of work that has *already* been reviewed -- every task
   had an ordinary review, every phase a `confidence-review` and a separate
   adversarial audit at `xhigh`, and every phase a complete `make check`.
   Re-reviewing it in 800-line slices would not find what those gates did not,
   because the slices cut across the concerns the gates were applied to.
2. **Six to eight over-cap pull requests, one per accepted phase.** Each is a
   coherent unit that already carries its own acceptance record and green gate,
   and the over-cap case is stated per pull request rather than assumed. This
   is the standing exception -- an over-cap merge is permitted where a change is
   provably indivisible, and a phase whose exit gates ran as a unit is the
   clearest form of that.
3. **Make this branch the trunk.** One operation, no pull requests, and the
   size job does not run because there is no pull request. It is the cheapest
   and it is the one that most needs to be chosen deliberately rather than
   arrived at: it forgoes pull-request review entirely, and the argument for it
   is only as good as the claim that the phase gates already did more than a
   pull request would.

## Recommended

**Option 2.** The 24 files above settle it. Option 3 would drop them silently:
a trunk swap moves a ref and says nothing about what the other side held, and
three of those four are tests -- exactly the thing that disappears without
anyone noticing. A pull request puts each deletion in a diff where a person
decides it. It keeps review at the boundary where review actually happened --
the phase -- and it makes each over-cap merge a stated decision with its
acceptance record attached, rather than a gate quietly not running. Option 3 is
defensible on the evidence and is materially cheaper; it should be taken only
as an explicit, dated decision, because "the gate did not run" and "the gate was
satisfied" must never read the same in this repository's record.

Whichever is chosen, **Phase 13 cannot be delivered as accepted**: it is
recorded as landed-but-not-accepted, because 13.4 and 13.6 end outside the tree
and its two whole-phase gates were deliberately not run.
