## Confidence review — Phase 6 (`ca7b13a..d4bdde5`)

Least confident about (ranked):

1. Prepared work could be re-bound to a changed catalog or source set.
   Investigated → `PreparedCase` retains the set digest, provider, model and resolved route; `_eligible` checks that retained route. The regression mutates catalog/source state after preparation.
   Verdict → fixed in `a28423f`; verified by the focused suite and the full backend gate.
2. A reader could learn whether an evidence digest exists.
   Investigated → `read_qualification` returns `RESTRICTED` before its database read, and `_read` omits all metadata.
   Verdict → fine; exercised by the reader/PDF journey and API tests.
3. A stale or malformed verdict could be shown as current.
   Investigated → evidence and verdict identities are recomputed and compared; database time is used; future, expired and binding-invalid states fail closed.
   Verdict → fine; regression tests cover the clock and identity cases.
4. The qualification strip could display a response for a different digest.
   Investigated → transport rejects a substituted identity and the strip holds status only when its digest matches the current prop.
   Verdict → fine; covered by transport and strip tests.
5. The production journey could hide a real creation failure behind a timing-dependent success note.
   Investigated → Firefox reproduced a `201` followed by an immediate refetch that removed the intentionally transient note before paint.
   Verdict → confirmed test defect, fixed in `d4bdde5`: the journey now requires the durable `201` receipt and refreshed run. Firefox and WebKit passed all 14 tests after the repair.
6. Restore evidence could omit qualification rows.
   Investigated → the restore probe writes and reads the exact evidence/verdict pair; migrations 0018/0019 preserve both tables.
   Verdict → fine; recovery probe and production image tests passed.

Fixed: durable browser assertion in `d4bdde5`.

Verified fine: exact identity binding, reader non-disclosure, verdict time validation, UI response binding, restore persistence.

By design: no live provider call was made; the UI therefore cannot claim a release-qualified live route.

7. The live-provider smoke test could reserve a placeholder rather than the
   configured model's maximum possible call cost.
   Investigated → the production worker already parses one dated model price
   and reserves `worst_case(price)`, but the direct live test constructed its
   execution with a flat `0.10` estimate.
   Verdict → fixed locally: the test now requires the same dated price input
   as the worker plus a positive, explicit run ceiling, and CI supplies both
   only as repository variables. The authorized three-call DeepSeek run used
   the configured ceiling; the focused price/configuration suite passed.
8. Production evidence could be confused with a fixture-only browser result.
   Investigated → rebuilt the production image without its stale local Docker
   cache; the production-image suite passed and the disposable Chromium
   journey completed its real text/PDF, restricted-reader, crash/restart and
   cleanup flow. The reader assertion is deliberately `RESTRICTED`, never a
   fabricated qualification.
   Verdict → automated evidence is current.

Still open: an external, authenticated qualification verdict for the exact
provider/model/route/time window and hosted required-check confirmation. The
application correctly refuses to mint that release evidence itself.
