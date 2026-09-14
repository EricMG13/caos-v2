# CAOS Repair Phase 5 — interim confidence review

- **Model and effort:** Codex `gpt-6-astra`, `xhigh`.
- **Scope:** `0deb4a4..e3b7b71`: forecast authority, saved revisions, filing,
  portable package verification and wire compatibility.
- **Method:** the `confidence-review` workflow: ranked low-confidence paths,
  source/caller tracing, and reproductions before remediation. This is not the
  single whole-phase confidence review required for acceptance.

## Verdict: BLOCK at the reviewed commit; both reproduced defects remediated

### CR-1 — CP-CF completed routes could not save a revision (P1)

The real ten-node forecast route reached `COMPLETE`, then `save_revision` failed
with `ARTIFACT_RECORD_MISMATCH`. Canonical deliverable proof required CP-CF in
CP-0's readiness set, even though the vendor readiness grammar cannot name the
host extension and acceptance/prompt construction already exclude it.

`0a7bddd` uses the shared model-module constant in the canonical gate set and
extends the accepted real forecast-route test through `save_revision`.

### CR-2 — current receipts could contradict their payload identity (P2)

The portable verifier accepted a payload whose case, run and revision IDs were
different from those in a current-format receipt, provided the payload digest
and renderer pin matched. `4c28ed0` requires all three current receipt IDs to
be non-empty strings equal to the decoded payload. Historical receipts that
omit all three remain supported. The regression proves both acceptance and
rejection paths.

## Checked and sound within implemented scope

Bounded forecast arithmetic, owner binding, restriction propagation, manifest
pins, immutable LITE revisions, filing actor separation, wire parity and the
archive output bounds all passed their focused suites. The integrated backend
suite after slice integration passed **2,719 tests** with **2 skipped**;
server mypy passed. These checks predate the two small confidence remediations,
which have their own focused, lint and type evidence above.

## Remaining Phase 5 work and gates

- Task 5.4b still owns authenticated live Model/Report/Committee reads, durable
  receipt linkage, and a CP-CF-accurate presentation (the generic “None
  performed by the host” text is not valid for CP-CF).
- Firefox production journey smoke remains an unresolved CP-0 `RUNNABLE`
  timeout. It blocks phase exit until root-caused and rerun.
- The 5.3 implementation range is 2,011 counted lines, above the 800-line PR
  ceiling; it needs an actual stacked-PR decomposition, not a waiver.
- Rebuild and scan the current image, refresh GitNexus at the final candidate,
  then run the one whole-phase confidence review followed by the separate
  adversarial audit at `xhigh`, with remediation and re-verification between
  them.
