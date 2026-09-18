# Request: ship code for the three rules the bundle declares and does not check

Date: 2026-09-17. Bundle: `vendor/deploy-v` at build `30222a49`.

**Status (2026-09-18):** done in build `62a94ccd`, in the bundle's own
validators at the `SHARED` owner, under the owner's authorisation
(`docs/DECISIONS.md` §92, `docs/VENDOR_CHANGES.md`). `semantic_rules`: all
five declared kinds enforced by `completeness_check.check`
(`tests/test_bundle_pin.py::test_the_vendor_enforces_cp_l10s_semantic_rules`).
`document_substrings_casefold`: the fixture half enforced with the marker
split, the evidence half projected. `required_payload_fields`:
`completeness_check.check_payload` over a payload object
(`test_the_vendor_checks_a_lite_payloads_required_fields`) -- shipped and
callable, and unreachable from the canonical adapter, which never receives a
payload; the ledger says so. The vendor's own `tests/` were edited so their
artifacts conform to the rules they declare, which §92 records.

## What is asked

Three rules are declared in the bundle's `SKILL.md` contracts and implemented
by no script it ships. For each, either an implementation in the bundle's own
validators (the `SHARED` owner `cp-0-source-readiness/scripts/validate_handoff.py`
or `completeness_check.py`, synchronised by `verify_package.py --refresh`), or
a written statement that the host owns the rule -- which needs its own dated
`docs/DECISIONS.md` entry, since it makes the host a second conformance
authority beside the bundle, which invariant 4 says it is not.

1. `semantic_rules`. `skills/cp-l10-financial-change-screen/SKILL.md` lines
   185-204 declare three for CP-L10 -- `cp_l10.topic_ids_unique`
   (`unique_columns` on TL10.2 `topic_id`), `cp_l10.topic_ids_complete`
   (`required_values`, six topic ids) and `cp_l10.overall_screen_present` --
   and each absorbed phase declares its own (lines 430, 613, 796, 979).
   CP-0 declares `none` (lines 160, 277).
2. `document_substrings_casefold`. `cp-0-source-readiness/SKILL.md` line 76,
   `cp-l10-financial-change-screen/SKILL.md` lines 59 and 182
   (`screening_run_disqualifiers`), and the same list in 21 of 25 `SKILL.md`
   files. The marker-split request covers this list; the split should land
   before or with the code, or the code refuses the honest handoffs §66 measured.
3. `required_payload_fields`. `cp-l10-financial-change-screen/SKILL.md` lines
   64-77 (thirteen fields, `cross_topic_synthesis` to `upgrade_plan`) and the
   absorbed phases' lists at 404, 587, 770 and 953, each bound to a payload
   schema under `references/`.

## Evidence in this tree

- No Python file under `vendor/deploy-v` contains the string `semantic_rules`
  or `required_payload_fields` (zero matches across the tree), and
  `document_substrings_casefold` appears in none of the 22 copies of
  `completeness_check.py`: `load_contract` (lines 196-198) reads only
  `critical_cell_values_casefold` and `critical_cell_substrings_casefold`.
  The one mention of "semantic" in `validate_handoff.py` (line 408) is a
  comment about keeping one parser.
- `server/methodology/handoff.py::validate_markdown` (docstring at lines
  305-307): "Not implemented here, and recorded as gaps: the vendor's
  `semantic_rules` and `document_substrings_casefold`." The host calls
  `contract.validate_handoff.validate_text` and
  `contract.completeness_check.check` and nothing else of the vendor's.
- `docs/DECISIONS.md` §46 item 5: LITE `required_payload_fields` are not
  validated by the host, recorded beside `semantic_rules`. §61 and §63 each
  decline, by name, to fold the frontmatter and substring rule into an
  authorised edit; §66 measures what enforcing it would cost.
- `CLAUDE.md` line 389, "Three vendor rules have no Python implementation and
  are not enforced": reimplementing them "would make the host a second
  conformance authority beside the bundle (invariant 4)". Upgrade: "enforce
  each rule the day the vendor ships it, or by a dated decision that the host
  owns it."

## What it unblocks

The ledger entry at `CLAUDE.md` line 389, in whole or per rule. The semantic
rules are the only check that a CP-L10 topic register is complete and unique
(today a duplicated or missing topic id validates); `required_payload_fields`
the only check that a LITE handoff carries its declared payload; the substring
rule is bound to the marker split above.

## How it can land

Preferred: an upstream build. These are vendor validators for vendor contracts,
and the bundle has the seam: one `SHARED` owner, 24 byte-identical copies of
`validate_handoff.py`, and a refresh that refuses drift and runs the bundle's
52 unit tests. The host pulls the tree, moves §13's pin and the host pins §63
lists, and calls the new entry points through `VendorContract` -- a host
change of a few lines, one named test per rule.

Otherwise: an authorised in-tree implementation under §61's precedent (change
2 is the exact shape: a validator edit at the `SHARED` owner, refreshed into
every copy), with its own dated entry, the refresh and the pin move. Second
choice because three rules are three edits and the bundle's own `tests/` would
not be extended (upstream files outside any host authorisation).

Host ownership of `required_payload_fields` alone is workable, since the
payload schemas already ship as references; the other two rules are defined by
the vendor's registers and should stay its.

## What the host does meanwhile

Enforces none of the three. It runs the vendor's structural validator and the
cell-level completeness checker on every handoff, refuses `HANDOFF_MALFORMED`
and `HANDOFF_INCOMPLETE` on what those return, and projects
`limitation_flags`, `validation_warnings` and `decision_scope` for a reader or
a key. The day the vendor ships the code, the pin move is what lets the host
call it.
