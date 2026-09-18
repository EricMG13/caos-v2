# The delivery backlog — measured 18 September 2026

`codex/execute-repair-plan` is `abb509e`; `main` is `971c69f`. This file records
what main is missing, how it was measured, and what the options cost. It is a
record for the owner, who alone performs delivery: nothing in this repository
pushes or opens a pull request.

## The shape, and the thing that is easy to get wrong

**Main is behind this branch, not diverged from it.** That reading is not
obvious from the commit graph and the obvious reading is wrong, so the evidence
is written down.

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

**Option 2.** It keeps review at the boundary where review actually happened --
the phase -- and it makes each over-cap merge a stated decision with its
acceptance record attached, rather than a gate quietly not running. Option 3 is
defensible on the evidence and is materially cheaper; it should be taken only
as an explicit, dated decision, because "the gate did not run" and "the gate was
satisfied" must never read the same in this repository's record.

Whichever is chosen, **Phase 13 cannot be delivered as accepted**: it is
recorded as landed-but-not-accepted, because 13.4 and 13.6 end outside the tree
and its two whole-phase gates were deliberately not run.
