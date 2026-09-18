# Request: map `decision_scope: SCREENING_ONLY` to the committee statuses it permits

Date: 2026-09-17. Bundle: `vendor/deploy-v` at build `30222a49`.

## What is asked

Every LITE pathway is declared `decision_scope: SCREENING_ONLY`, and nothing
in the bundle says which `committee_status` values a screening-only handoff
may carry. The request is one declared mapping, in the place the validator
reads: for each `decision_scope` (`SCREENING_ONLY` and `FULL`), the subset of
`COMMITTEE_STATUSES` a handoff on a pathway of that scope may declare, and
`validate_handoff.py` refusing a status outside it as it already refuses a
`confidence_band` inconsistent with its score. The obvious reading is that
`SCREENING_ONLY` never permits `Committee Ready`; whether it permits `Draft
Only`, `Restricted`, `Requires More Work`, `Insufficient Information` and
`Blocked`, or a narrower set, is the vendor's to say.

Files: `skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json`
(`decision_scope` at lines 2568, 2603, 2626, 2649, 2690, 2719, 2784, 2807 for
the eight LITE pathways, `FULL` at 1854-2325 for the ten FULL ones, CP-L10's
own at 691); `skills/cp-os-credit-os/scripts/validate_handoff.py` lines 71-78
(`COMMITTEE_STATUSES`) and 855-857 (the enum check); `CANON_SHARED.md` line
318 (SEC3 transitions) and 325 (D2 COMMITTEE, the six values).

## Evidence in this tree

- The catalog carries `decision_scope` nineteen times and `committee_status`
  never; `decision_scope` appears in no script under
  `skills/cp-os-credit-os/scripts/`. The enum check (line 856) accepts any of
  the six statuses for any module on any pathway.
- CP-L10 declares `decision_scope: SCREENING_ONLY` at
  `skills/cp-l10-financial-change-screen/SKILL.md` line 33 and in each absorbed
  phase's identity table (238, 319, 502, 685, 868); "Committee Ready" does not
  occur in that file. CP-3C's LITE block (lines 13-14): "Preserve
  SCREENING_ONLY limitations; ... A full decision requires a new FULL run."
  The catalog's `upgrade` block agrees: `NEW_RUN_ONLY`, target
  `FULL_CREDIT_32`. The intent is in prose; the rule that would carry it is
  absent.
- It has happened. Run `ff71c457-70b8-44bd-b6ef-2099927b8936` on
  `LITE_CREDIT_22 / LITE_EARNINGS_UPDATE` accepted a CP-0 declaring
  `qa_status: Passed`, `committee_status: Committee Ready`,
  `confidence_score: 93` (`qualification/vmo2-fy2025/RESULT.md` lines 445-447).
  §61 change 2 now refuses that body for its `SOURCE_GAP | MATERIAL` row; the
  same body with no MATERIAL row would still validate `Committee Ready` on a
  screening-only route.
- The host: `server/methodology/handoff.py::_decision_scope` (277-285) reads
  the pathway's scope from the catalog and refuses `HANDOFF_IDENTITY_MISMATCH`
  when it is missing; `Projections` carries it (line 126, comment at 124-125:
  "`SCREENING_ONLY` is never committee clearance, whatever `committee_status`
  the model wrote"); the `validate_markdown` docstring (306-307): projected,
  "not reconciled with `committee_status`, which the vendor does not map".
  `server/deliverable/render.py` (line 158) labels a `SCREENING_ONLY` record a
  screen whatever its status, `server/api/reads/analysis.py` line 291 carries
  the flag, and `server/qualification/matrix.py` line 32 says a screening-only
  record can never reach a reviewer as clearance. None refuses.
- `CLAUDE.md` line 389: "a LITE handoff saying `Committee Ready` validates;
  the host projects the scope beside the status and invents no refusal."

## What it unblocks

The second half of the ledger entry at `CLAUDE.md` line 389. With the mapping,
`decision_scope` stops being a label beside the status and becomes a bound the
vendor's validator enforces; a qualification key on `committee_status`
(`matrix.PROJECTION_FIELDS`) for a LITE case then measures the model against a
declared rule rather than the key author's reading. The three held LITE
pathways (Tasks 9.5-9.7) are screening-only routes ending in CP-5 or CP-4C,
so the mapping bears on every handoff they would produce.

## How it can land

Preferred: an upstream build. The rule belongs in `validate_handoff.py` at the
`SHARED` owner and in `CANON_SHARED.md`'s D2/SEC3 lines, refreshed into the 24
copies by `verify_package.py --refresh`; the host pulls the tree and moves
§13's pin and the host pins §63 lists. If the validator needs the pathway's
scope as an input, the host already carries it in `HostIdentity` and can pass
it the way it passes the module id.

Otherwise: an authorised in-tree edit under §61's precedent, a validator change
at the `SHARED` owner and one canon line, with its own dated decision entry,
the refresh and the pin move. Close in size to §61 change 2 and the fallback
if upstream is slow; second choice because the permitted set is a methodology
judgement the host should not make first.

## What the host does meanwhile

Projects `decision_scope` on every accepted record and refuses nothing on
`committee_status` beyond the vendor's enum. The deliverable labels a
screening-only record a screen whatever its status; the proof and matrix report
no status. A `Committee Ready` LITE handoff validates and is shown as a screen.
