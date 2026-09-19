# Vendor changes — the record the owner asked for

Invariant 4 says never edit a file that exists upstream. On 18 September 2026
the owner wrote: "Vendor files - approved to alter but keep a record of
changes." This file is that record. Every file under `vendor/deploy-v/` that
this repository has changed since the upstream pull is listed here, with the
request each change answers, the build it produced and a one-line reason; the
binding decision for each build is in `docs/DECISIONS.md` (§61, §63, §92, §98).
Upstream is `github.com/EricMG13/Deploy-V@c4d2e356` and carries none of it;
the next upstream pull either carries every change forward or supersedes it
with a decision entry.

The mechanism is always the bundle's own: edit once at the `SHARED` owner
(`cp-0-source-readiness/scripts/` for the validators), run
`verify_package.py --refresh` (with `--rebuild-authorities` when a pinned
runtime authority such as the catalog moves), which synchronises the shared
copies, runs the bundle's self-checks and unit tests, and regenerates
`DEPLOY_V_INTEGRITY_v1.json`, `DEPLOY_V_MANIFEST.json`,
`DEPLOY_V_BASELINE.json`, `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json` and the two
Copilot memory prompts. Those regenerated files move with every build and are
listed once, below, rather than per change.

Vendor diff base: `8dee6ab160a42bd3e800647eed89f4e98827b0a5`.
`tests/test_vendor_change_record.py` emits the changed paths from Git and holds
this sorted inventory exactly equal to them.

## Exact changed-path inventory

- `CANON_SHARED.md`
- `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json`
- `DEPLOY_V_BASELINE.json`
- `DEPLOY_V_COPILOT_MEMORY_PROMPT.md`
- `DEPLOY_V_COPILOT_MEMORY_PROMPT_URL_BOUND.md`
- `DEPLOY_V_INTEGRITY_v1.json`
- `DEPLOY_V_MANIFEST.json`
- `skills/cp-0-source-readiness/SKILL.md`
- `skills/cp-0-source-readiness/references/CP-0__SourceReadiness__payload.schema.txt`
- `skills/cp-0-source-readiness/references/REF_CP-0_STEPS.md`
- `skills/cp-0-source-readiness/scripts/completeness_check.py`
- `skills/cp-0-source-readiness/scripts/validate_handoff.py`
- `skills/cp-1-canonical-data-foundation/SKILL.md`
- `skills/cp-1-canonical-data-foundation/scripts/completeness_check.py`
- `skills/cp-1-canonical-data-foundation/scripts/validate_handoff.py`
- `skills/cp-1a-business-transaction-fact-pack/SKILL.md`
- `skills/cp-1a-business-transaction-fact-pack/scripts/completeness_check.py`
- `skills/cp-1a-business-transaction-fact-pack/scripts/validate_handoff.py`
- `skills/cp-1b-earnings-delta/SKILL.md`
- `skills/cp-1b-earnings-delta/scripts/completeness_check.py`
- `skills/cp-1b-earnings-delta/scripts/validate_handoff.py`
- `skills/cp-1c-peer-benchmark/SKILL.md`
- `skills/cp-1c-peer-benchmark/scripts/completeness_check.py`
- `skills/cp-1c-peer-benchmark/scripts/validate_handoff.py`
- `skills/cp-1d-earnings-quality/scripts/completeness_check.py`
- `skills/cp-1d-earnings-quality/scripts/validate_handoff.py`
- `skills/cp-2-fundamental-credit-synthesizer/SKILL.md`
- `skills/cp-2-fundamental-credit-synthesizer/scripts/completeness_check.py`
- `skills/cp-2-fundamental-credit-synthesizer/scripts/validate_handoff.py`
- `skills/cp-2a-downside-pathway/SKILL.md`
- `skills/cp-2a-downside-pathway/scripts/completeness_check.py`
- `skills/cp-2a-downside-pathway/scripts/validate_handoff.py`
- `skills/cp-2d-liquidity-cash-flow-bridge/SKILL.md`
- `skills/cp-2d-liquidity-cash-flow-bridge/scripts/completeness_check.py`
- `skills/cp-2d-liquidity-cash-flow-bridge/scripts/validate_handoff.py`
- `skills/cp-2e-macro-fx-hedging-sensitivity/SKILL.md`
- `skills/cp-2e-macro-fx-hedging-sensitivity/scripts/completeness_check.py`
- `skills/cp-2e-macro-fx-hedging-sensitivity/scripts/validate_handoff.py`
- `skills/cp-2g-forward-credit-model/SKILL.md`
- `skills/cp-2g-forward-credit-model/scripts/completeness_check.py`
- `skills/cp-2g-forward-credit-model/scripts/validate_handoff.py`
- `skills/cp-2h-ratings-migration-trigger/SKILL.md`
- `skills/cp-2h-ratings-migration-trigger/scripts/completeness_check.py`
- `skills/cp-2h-ratings-migration-trigger/scripts/validate_handoff.py`
- `skills/cp-3-relative-value-security-selection/SKILL.md`
- `skills/cp-3-relative-value-security-selection/scripts/completeness_check.py`
- `skills/cp-3-relative-value-security-selection/scripts/validate_handoff.py`
- `skills/cp-3c-refinancing-lme-risk/SKILL.md`
- `skills/cp-3c-refinancing-lme-risk/scripts/completeness_check.py`
- `skills/cp-3c-refinancing-lme-risk/scripts/validate_handoff.py`
- `skills/cp-3d-market-implied-risk/SKILL.md`
- `skills/cp-3d-market-implied-risk/scripts/completeness_check.py`
- `skills/cp-3d-market-implied-risk/scripts/validate_handoff.py`
- `skills/cp-4-legal-covenant-interpreter/SKILL.md`
- `skills/cp-4-legal-covenant-interpreter/scripts/completeness_check.py`
- `skills/cp-4-legal-covenant-interpreter/scripts/validate_handoff.py`
- `skills/cp-4c-restructuring-fulcrum/SKILL.md`
- `skills/cp-4c-restructuring-fulcrum/scripts/completeness_check.py`
- `skills/cp-4c-restructuring-fulcrum/scripts/validate_handoff.py`
- `skills/cp-5-evidence-trace-validator/SKILL.md`
- `skills/cp-5-evidence-trace-validator/scripts/completeness_check.py`
- `skills/cp-5-evidence-trace-validator/scripts/validate_handoff.py`
- `skills/cp-6-ic-debate-challenge/SKILL.md`
- `skills/cp-6-ic-debate-challenge/scripts/completeness_check.py`
- `skills/cp-6-ic-debate-challenge/scripts/validate_handoff.py`
- `skills/cp-8-decision-ledger-post-mortem/SKILL.md`
- `skills/cp-8-decision-ledger-post-mortem/scripts/completeness_check.py`
- `skills/cp-8-decision-ledger-post-mortem/scripts/validate_handoff.py`
- `skills/cp-dr-deep-research/SKILL.md`
- `skills/cp-dr-deep-research/scripts/validate_handoff.py`
- `skills/cp-l10-financial-change-screen/SKILL.md`
- `skills/cp-l10-financial-change-screen/scripts/completeness_check.py`
- `skills/cp-l10-financial-change-screen/scripts/validate_handoff.py`
- `skills/cp-model/scripts/validate_handoff.py`
- `skills/cp-os-credit-os/references/CREDIT_OS_V_AUTHORITY_BUNDLE_v2.json`
- `skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json`
- `skills/cp-os-credit-os/scripts/completeness_check.py`
- `skills/cp-os-credit-os/scripts/credit_os_v/navigation.py`
- `skills/cp-os-credit-os/scripts/validate_handoff.py`
- `tests/test_module_workflow.py`
- `tests/test_research_workflow.py`

## Build `91c219fb` (2026-09-18, §98) — from `62a94ccd`

Old build `62a94ccd0ef6439f797d60ebb72e6a44e1d42db16cd8af217fc41b7f1d6ea72c`;
new build `91c219fb7147cf1e0089b6119bca7de013ad94bcd7f4b6cea6536a88776f2c77`.
`DEPLOY_V_INTEGRITY_v1.json` SHA-256 `4945d137…` -> `fad44352…`, still 68,657
bytes. No runtime authority moved, so `--rebuild-authorities` was not run and
`authority_bundle_sha256` is unchanged (`e3d0f8b2…`). The refresh ran the
bundle's 52 unit tests and 10 helper self-checks, green.

| Vendor file | Request | Change |
| --- | --- | --- |
| `skills/cp-0-source-readiness/references/REF_CP-0_STEPS.md` | the owner's approval of page-level evidence selection for the Boeing and Ford 10-K texts (§98) | Step I, rule 5 gains the page-range form of a `Source files to attach` item -- `<filename> pages <first>-<last>` or `<filename> page <n>`, one range per item, pages being the `page` locators the evidence shows, a filename alone attaching the whole source; a new rule 8 says a source the host delivers as a page map is evidence only in the lines shown, is triaged `PARSE_TARGETED` (or `BLOCKED`), is attached by page and never whole, and carries the page-map limitation into each row. 740 bytes. |
| `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json`, `DEPLOY_V_BASELINE.json`, `DEPLOY_V_COPILOT_MEMORY_PROMPT.md`, `DEPLOY_V_COPILOT_MEMORY_PROMPT_URL_BOUND.md`, `DEPLOY_V_INTEGRITY_v1.json`, `DEPLOY_V_MANIFEST.json` | (regenerated) | By `verify_package.py --refresh`; no hand edit. |

## Build `62a94ccd` (2026-09-18, §92) — from `30222a49`

Old build `30222a494a5a1035c7955cb1ccfbe0b3b0fbbfa7d6426930f5dcf4d35aa1fc18`;
new build `62a94ccd0ef6439f797d60ebb72e6a44e1d42db16cd8af217fc41b7f1d6ea72c`.
`DEPLOY_V_INTEGRITY_v1.json` SHA-256 `8ccc8ed0…` -> `4945d137…`, still 68,657
bytes. The vendor's own `authority_bundle_sha256` moved `47fec65f…` ->
`e3d0f8b2…` because the catalog is one of its pinned components; the rebuild is
recorded by the vendor's own `local_rebuild` provenance inside the file.

| Vendor file | Request | Change |
| --- | --- | --- |
| `skills/cp-os-credit-os/scripts/credit_os_v/navigation.py` | `2026-09-17-t8-source-files-column` | `Recommendation` gains `source_files_to_attach`; `parse_t8` keeps T8's fifth column (cell 4 of the current header, cell 3 of the legacy one) instead of dropping it after width validation. |
| `skills/*/SKILL.md` (21 files: CP-0, CP-1, CP-1A, CP-1B, CP-1C, CP-2, CP-2A, CP-2D, CP-2E, CP-2G, CP-2H, CP-3, CP-3C, CP-3D, CP-4, CP-4C, CP-5, CP-6, CP-8, CP-DR, CP-L10) | `2026-09-17-disqualifier-marker-split` | In every `full_run_disqualifiers` and `screening_run_disqualifiers` block (117 lists across the profile and absorbed-phase copies), `frontmatter_limitation_flags`, `frontmatter_validation_warnings` and `document_substrings_casefold` become `fixture_limitation_flags`, `fixture_validation_warnings` and `fixture_document_substrings_casefold` holding the fixture markers only; the thin-evidence markers (`SOURCE_LIMITED_NOT_COMMITTEE_READY`, `FULL_UNDERWRITING_SOURCE_SET_NOT_RETAINED`, `source-limited`, `full-underwriting source set not retained`) move to a sibling `projected_evidence_limitations` block under the original key names (34 blocks). |
| `skills/cp-0-source-readiness/scripts/completeness_check.py` (SHARED owner; 22 copies synchronised) | `2026-09-17-disqualifier-marker-split`, `2026-09-17-unshipped-rules` | `load_contract` reads the fixture lists (enforced), the projected evidence lists (returned, enforced by nothing), `semantic_rules` and `payload_contract.required_payload_fields`; `_parse_tree` reads a `structured item` bullet as a nested mapping (before, the three CP-L10 rules collapsed into one); `check` refuses a front-matter fixture flag or warning and a fixture substring in the unfenced document, and enforces the five semantic rule kinds the profiles declare (`unique_columns`, `required_values`, `allowed_values`, `exact_values`, `at_least_one_row_populates`; an unknown kind is a violation, never a pass); `check_payload` judges a JSON payload's `runtime_output` against the required fields. Self-check extended for each. |
| `skills/cp-0-source-readiness/scripts/validate_handoff.py` (SHARED owner; 24 copies synchronised) | `2026-09-17-lite-scope-status` | Declares `COMMITTEE_STATUSES_BY_SCOPE` (`FULL`: every status; `SCREENING_ONLY`: every status but `Committee Ready`); `validate_text(..., decision_scope=None)` refuses a status the named scope does not permit and an undeclared scope. Without a scope the check is the bare enum, as before. |
| `CANON_SHARED.md` | `2026-09-17-lite-scope-status` | One line after D2 COMMITTEE, "D2 BY SCOPE", stating the mapping the validator enforces. |
| `skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json` | `2026-09-17-lite-producers` (option 1) | The `LITE_CREDIT_22` typed edges `CP-L10 -> CP-2A` and `CP-L10 -> CP-3C` declare `accepted_object_id` (`lite_fundamental_credit_screen`, `lite_liquidity_sensitivity_screen`) and `allowed_use: SCREENING_ONLY`, as the sibling edges to CP-2H and CP-4C already did. |
| `skills/cp-3c-refinancing-lme-risk/SKILL.md` | `2026-09-17-lite-producers` | The unkeyed `## LITE profile compatibility` heading becomes the keyed block `## LITE profile compatibility — CP-3C` with the three vendor fields, naming the three objects `CP_DEPLOY_V_EXECUTION_PROFILES_v1.json` already declared for CP-3C; the original prose is kept below the fields. |
| `skills/cp-os-credit-os/references/CREDIT_OS_V_AUTHORITY_BUNDLE_v2.json` | (consequence of the catalog edit) | `verify_package.py --refresh --rebuild-authorities`, the bundle's own release operation: the catalog component's digest and `authority_bundle_sha256` move, with `local_rebuild` provenance naming the previous digest. |
| `tests/test_module_workflow.py`, `tests/test_research_workflow.py` | `2026-09-17-unshipped-rules` (consequence) | The vendor's own test artifacts repeated one cell per register, which the semantic rules now refuse; `conforming_rows` derives each register's rows from the profile's own rules so the vendor's 52 tests hold under the rules they declared. |
| `CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json`, `DEPLOY_V_BASELINE.json`, `DEPLOY_V_COPILOT_MEMORY_PROMPT.md`, `DEPLOY_V_COPILOT_MEMORY_PROMPT_URL_BOUND.md`, `DEPLOY_V_INTEGRITY_v1.json`, `DEPLOY_V_MANIFEST.json` | (regenerated) | By `verify_package.py --refresh`; no hand edit. |

`2026-09-17-cp0-gating-vs-classification`: **no vendor file changed.** The
owner's recommendation taken is the fail-closed reading: the bundle's
per-consumer gating stays (§92).

## Build `30222a49` (2026-09-16, §63) — from `cdea0c9f`

| Vendor file | Request | Change |
| --- | --- | --- |
| `skills/cp-5-evidence-trace-validator/SKILL.md` | CP-5's status columns (§62 deferral, resolved §63) | T5B.5's `disqualifier_exempt_columns` moves from `none` to `Status; Claim Status`, 16 bytes. |
| (regenerated metadata as above) | | |

## Build `cdea0c9f` (2026-09-16, §61) — from `a43cb903`

| Vendor file | Request | Change |
| --- | --- | --- |
| `skills/cp-0-source-readiness/SKILL.md`, `skills/cp-0-source-readiness/references/REF_CP-0_STEPS.md`, `skills/cp-0-source-readiness/references/CP-0__SourceReadiness__payload.schema.txt` | `CONDITIONAL` verdict (§61 change 1) | `CONDITIONAL` names a source the effective-source set does not carry, discharged by supplying it and re-running CP-0; an unproduced upstream handoff is never a readiness ground. |
| `skills/cp-0-source-readiness/scripts/validate_handoff.py` (24 copies) | Severity floor (§61 change 2) | A CRITICAL finding row requires `qa_status: Blocked`, a MATERIAL one refuses `Passed`. |
| (regenerated metadata as above) | | |
