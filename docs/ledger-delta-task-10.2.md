# Ledger delta — Completion Phase 10 Task 10.2

Not a ledger. This file carries the replacement text for one `CLAUDE.md` entry,
ready to paste, because three tasks are editing that file this wave and the
coordinator applies ledger edits. Delete it in the commit that applies the edit.

## What changes

The **Phase 3** entry **"A route's predicates are frozen and never evaluated"**.
Replace the whole entry with the text under *Replacement* below.

What moved in the tree: the entry's own `*Upgrade:*` clause said "What
Completion Phase 10 still owes is the refusal -- `_edges_among`
`ROUTE_EDGE_UNSUPPORTED` rather than pinning a route whose target would block
whatever the evidence said." That refusal now exists, so the clause is stale in
the direction the Completion Phase 7 entry above it calls the worse defect: an
entry describing a gap the tree has since closed. The rest of the entry is
still true — the predicates are still frozen and still consulted by nothing —
so the entry is rewritten rather than struck.

## On the catalog counts and the second test

The counts are already pinned, and were before this task:
`tests/test_bundle_pin.py::test_the_catalog_declares_no_conditional_edge` has
held since `4f06337`. That test is left exactly as it was, because
`docs/PHASE_7_EXIT_EVIDENCE.md` and the ledger entry both cite it by name and a
rename would break two citations for nothing.

A second test is added beside it,
`tests/test_bundle_pin.py::test_the_vendored_catalog_carries_no_edge_this_engine_cannot_evaluate`,
rather than widening the first, because it makes three assertions the first
cannot and should not carry:

1. the **whole** typed-edge census — `{REQUIRED: 60, OPTIONAL: 26, ADVISORY:
   29, QA_GATE: 1}` as an exact equality, so a bundle pull that moves any count
   is visible, not only the one type that matters;
2. the census **through the engine** — every one of the 18 pathways resolves
   through `resolve_route` today, counted, so a census that counted nothing
   cannot read as a pass;
3. the **guard firing on the real catalog** — a deep-copied catalog with one
   edge retyped to `CONDITIONAL` refuses `ROUTE_EDGE_UNSUPPORTED` at
   `resolve_route` for every pathway carrying that edge. A hand-built profile
   (which `tests/test_route_resolution.py` also has) cannot show that the
   *vendored* catalog would be caught.

The older test stays what it is: the one-line pin that the entry and the exit
evidence name. A comment now points from it to the census beside it.

## Replacement

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
  would have pinned a route whose target blocks whatever the evidence said.
  `CONDITIONAL` stays in `BLOCKING` and stays in the bundle's vocabulary
  (`CONTEXT.md`): it remains a CP-0 *verdict*, which
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
