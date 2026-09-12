# Task 0 report — 2026-09-12

## Status

DONE_WITH_CONCERNS. Documentation and an isolated F02 reproduction were added;
application and vendor sources were not changed. Baseline was
`26d7ee99f6c90396ddb5f7c3614cdd733af4ed76`.

## F02 reproduction

Probe: `.superpowers/sdd/probe_f02_false_completion.py`.

Command (provider variables deliberately removed):

```sh
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL \
  CAOS_TEST_POSTGRES_URL=postgresql://postgres:caos@127.0.0.1:32777/caos \
  .venv/bin/python .superpowers/sdd/probe_f02_false_completion.py
```

Observed exit: `1`, as expected for the unfixed regression.

```text
stored_status=COMPLETE accepted_nodes=1/4
AssertionError: F02: blocked downstream nodes wrongly allowed terminal COMPLETE
```

The probe resolves the vendored `FULL_CREDIT_32` / `LIQUIDITY_REVIEW` route,
pins it, accepts CP-0 with complete BLOCKED verdicts for CP-1, CP-2 and CP-2D,
and supplies a provider that raises if called. No provider was called. The
empty frontier falls through to unconditional `complete_run` at
`server/engine/runtime.py:94`, producing the false terminal state. The probe
uses a UUID-named PostgreSQL database and drops it in `finally`.

## Contract reconciliation

Added `docs/DECISIONS.md` §29 and `docs/HOST_ADAPTER_CONTRACT.md`.

The recorded target preserves the vendor's exact validated canonical Markdown
as analytical authority and downstream handoff. Host-owned run, source-set,
extractor/extraction-manifest, route, bundle, adapter and upstream identities
travel beside it; UI fields are validated sidecar projections, and the
UI/report is host presentation. This follows the binding Markdown sequence in
`vendor/deploy-v/CANON_SHARED.md` under “CP Markdown-only handoff
specification.”

The current executor remains accurately described as closed claims/readiness
JSON (`server/methodology/executor.py`, `server/methodology/envelope.py`,
`server/methodology/runner.py`); the report does not claim it already preserves
canonical Markdown. The catalog's `preparation_stage` selects non-runnable
preparation under CP-0 and every `LIQUIDITY_REVIEW` route starts at CP-0
(`CREDIT_OS_V_MODULE_CATALOG_v2.json`). Accordingly, the host extraction
manifest is CP-0 preparation metadata, while CP-PARSE remains only the host
authority alias in `server/methodology/bundle.py`, not an extra executable LLM
node. No preparation is duplicated. The no-Excel/no-Word scope and archived
contracts are unchanged.

The valid/restricted/blocked examples are explicitly illustrative host behavior,
not vendor-conformance fixtures, and introduce no vendor fields.

## Focused checks

- `ruff check` on the probe: pass.
- `ruff format --check` on the probe: pass.
- Python `compile(...)` on the probe: pass without writing bytecode into the
  vendored-sensitive tree.
- `git diff --check`: pass.
- F02 isolated probe: expected failure; `COMPLETE`, one accepted node of four.
- Full baseline suite and index checks: delegated to the Phase 0 controller by
  the task brief.

## Confidence review — probe and contract documents

Least confident about (ranked):

1. The reproduction might call a provider or touch a shared application DB.
   Investigated the full path: accepted CP-0 makes every remaining node BLOCKED,
   `NoProvider.execute` is a tripwire, and the fixture pattern creates/drops a
   UUID-named database. Verdict: verified fine by the observed no-call failure
   and cleanup path; no patch required.
2. The accepted count might count attempts rather than accepted nodes.
   Investigated the query and schema path: it counts `artifacts`, the rows from
   which `accepted_artifacts` derives completion, scoped to the new run. Verdict:
   verified fine; observed `1/4`.
3. CP-PARSE wording might silently delete compatibility or duplicate CP-0.
   Compared catalog preparation/pathway nodes, §5, bundle `_CARVE_OUTS`, and the
   archived-scope decisions. Verdict: clarified as authority alias only, with
   extraction manifest retained as host metadata and no executable duplicate.
4. The target table might overstate current capability or invent vendor fields.
   Compared the current executor/envelope/runner with `CANON_SHARED.md` and the
   catalog. Verdict: verified fine after explicitly stating current JSON is not
   canonical Markdown and labeling examples non-conformance illustrations.

Fixed: probe lint/format findings and ambiguous CP-PARSE execution wording.
Verified fine: database isolation, no-provider path, accepted-node measurement,
source-linked current/target distinction. By design: the probe remains red
outside the normal suite until F02 is repaired. Still open: F02 itself and the
lossless Markdown adapter, both intentionally outside this reproduction-only
task.

No rewrite tournament was run because this is test-probe/documentation work;
no adversarial phase audit was run because the controller owns phase completion.

## Review corrections

The post-task review identified two bounded corrections. The F02 assertion now
rejects only the demonstrated false `COMPLETE` state; it does not prescribe
`RUNNING`, because the repaired blocked-state design belongs to Phase 2. Direct
source links now support the CP-0/CP-PARSE preparation reconciliation and the
no-Excel/no-Word archived scope.

Focused recheck: Ruff lint and format, Python compile, and `git diff --check`
passed. The isolated probe still exited `1` with
`stored_status=COMPLETE accepted_nodes=1/4`, the intended F02 reproduction.
