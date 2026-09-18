# Request: split the fixture markers from the thin-evidence marker

Date: 2026-09-17. Bundle: `vendor/deploy-v` at build `30222a49`.

**Status (2026-09-18):** done in build `62a94ccd` under the owner's
authorisation (`docs/DECISIONS.md` §92, `docs/VENDOR_CHANGES.md`): every
`SKILL.md` declares `fixture_*` lists under its disqualifiers and a
`projected_evidence_limitations` block beside them, and the bundle's own
`completeness_check` enforces the fixture lists and enforces nothing on the
projected ones
(`tests/test_bundle_pin.py::test_the_fixture_markers_are_split_from_the_thin_evidence_marker`).

## What is asked

`full_run_disqualifiers.frontmatter_limitation_flags` lists four flags in one
list: `INTEGRATION_FIXTURE_ONLY`, `PRESENTATION_FIXTURE_NOT_CURRENT_GOLDEN`,
`SOURCE_LIMITED_NOT_COMMITTEE_READY`, `SYNTHETIC_FORWARD_ASSUMPTIONS`. It is
declared in `skills/cp-0-source-readiness/SKILL.md` line 77 (and its structured
copy at 273) and `skills/cp-l10-financial-change-screen/SKILL.md` line 60 (with
copies at 399, 582, 765 and 948), and in 21 of the 25 `skills/*/SKILL.md`
files (all but CP-1D, CP-MEMO, CP-MODEL and CP-OS). `document_substrings_casefold` beside it (CP-0 line
76, CP-L10 line 59) has the same shape: `integration fixture`, `synthetic test
input` and `not a current analytical golden` sit next to `source-limited`.

The request: the bundle declares two lists with two meanings. One names the
markers that say a document is not real work (a fixture, a synthetic
assumption, a non-golden presentation), and is a completeness disqualifier.
The other names the markers that say the evidence is thin
(`SOURCE_LIMITED_NOT_COMMITTEE_READY`, `source-limited`), and is a projected
limitation a reader and a qualification key see. The same split applies to
`frontmatter_validation_warnings` (CP-0 line 78), where
`FULL_UNDERWRITING_SOURCE_SET_NOT_RETAINED` is an evidence statement beside
three fixture markers. Whatever the field names, each list must say which
class it is.

## Evidence in this tree

- `docs/DECISIONS.md` §66 records that enforcing the three frontmatter and
  substring lists as written was implemented, replayed against all 25 retained
  real handoff bodies, and rejected: it newly refuses seven -- CP-0 and CP-L10
  from runs `33ca320e`, `729b0682`, `42e17048` and `54ec3752`, every one for
  declaring `SOURCE_LIMITED_NOT_COMMITTEE_READY`. Two of the seven are the
  accepted artifacts of `42e17048`, the first complete qualification snapshot
  (`qualification/vmo2-fy2025/RESULT.md`). The one substring hit was a CP-5
  describing an upstream as "source-limited", which is the same conflation
  read from the consumer's side.
- §61 "Decided against, here" and §63 "Decided against, here" both leave this
  rule open by name: it is a different rule from the severity floor and the
  T5B.5 exemption, with its own semantics.
- `CLAUDE.md` line 988, "The bundle's disqualifier list conflates a fixture
  with thin evidence": honouring the list whole refuses honest work; honouring
  part of it would be the host choosing which of the bundle's rules count,
  which invariant 4 forbids.
- The bundle's own checker reads neither list:
  `skills/cp-os-credit-os/scripts/completeness_check.py` lines 196-198 load
  only `critical_cell_values_casefold` and `critical_cell_substrings_casefold`.
  So today nothing in the bundle or the host enforces the flag lists; the
  conflation is latent, and would bite the day either side enforced them.

## What it unblocks

Closing the ledger entry at `CLAUDE.md` line 988 and the "What stays open"
paragraph of §66. Once split, the fixture list can be enforced as
completeness -- one more rule the host runs through the vendor's own checker
rather than reimplementing (see the unshipped-rules request) -- while
`limitation_flags` stays a projection (`server/methodology/handoff.py::Projections`,
`matrix.PROJECTION_FIELDS`) that a qualification key asserts on. It also
removes the reason the corpus's honest CP-0 and CP-L10 handoffs would be
refused on any future enforcement of the declared rule.

## How it can land

Preferred: an upstream build. The lists are declared in every module's
`SKILL.md` and the bundle's `verify_package.py --refresh` refuses shared
drift, so this is an edit across the whole tree and belongs to the vendor;
the host pulls the tree and moves §13's pin and the host pins §63 lists in one
`docs/DECISIONS.md` entry. If the vendor also ships checker code for the new
fixture list, `completeness_check.py` moves with it.

Otherwise: an authorised in-tree edit under §61's precedent, with its own dated
decision entry naming the two lists and every file touched, the refresh, and
the pin move. That edit is larger than §61's or §63's -- it changes a declared
contract in many `SKILL.md` files, not one register's exemption -- which is a
reason to prefer upstream.

## What the host does meanwhile

Enforces neither list, deliberately (§66). It projects `limitation_flags` and
`validation_warnings` on every accepted record, where a key or a reader can
see `SOURCE_LIMITED_NOT_COMMITTEE_READY` for what it is, and refuses nothing
on them. It runs only the vendor's cell-level disqualifiers through
`completeness_check.check`.
