# Request: say whether CP-0 gates each consumer or only classifies sources

Date: 2026-09-17. Bundle: `vendor/deploy-v` at build `30222a49`.

**Status (2026-09-18):** decided, no change (`docs/DECISIONS.md` §92, item
6). The owner's recommendation taken is the fail-closed reading this request
preferred: the bundle governs, CP-0 gates each consumer, and `route.py` is not
weakened. No vendor file moved for this request, and the ledger entry that
owed the decision closes on §92.

## What is asked

A decision on which governs: the vendored methodology, which makes CP-0 a
per-consumer gate, or the owner's statement of 16 September 2026 that CP-0
"only classifies the documents to assess which pathways are available"
(`CLAUDE.md` line 1101). If the statement is the policy, the change is the
bundle's: `skills/cp-0-source-readiness/SKILL.md` lines 331, 349 and 357,
`CANON_SHARED.md` line 632, `references/REF_CP-0_STEPS.md` and
`references/CP-0__SourceReadiness__payload.schema.txt` (the three places §61
edited for `CONDITIONAL`), and the two scripts that refuse a non-ready module.
It is a new build, not a host change.

## Evidence in this tree

The bundle, verified at the cited lines:

- `skills/cp-0-source-readiness/SKILL.md` line 331 (hard rule 6): "Assess
  readiness against the user's stated objective and the evidence demand of
  each proposed downstream module".
- Line 349 (workflow step 6): "Determine `READY`, `READY_WITH_LIMITATIONS`,
  `CONDITIONAL` or `BLOCKED` for each proposed consumer".
- Line 357 (T8 contract): for `CONDITIONAL` and `BLOCKED`, "`exact_command` is
  exactly `DO NOT RUN`".
- `CANON_SHARED.md` line 632, routing rule R4: "CP-0 determines readiness;
  CP-OS presents navigation without analytical recomputation."
- The vendor's own scripts refuse a module CP-0 did not mark ready:
  `skills/cp-os-credit-os/scripts/prepare_invocation.py` line 79 and
  `scripts/credit_os_v/handoffs.py` line 68, both on
  `{'READY', 'READY_WITH_LIMITATIONS'}`.

The host, which follows the bundle: `server/engine/route.py` (`READY` at line
63, `_state_for` at 421) lets a node run only on a stored CP-0 verdict of
`READY` or `READY_WITH_LIMITATIONS` (§27), and `_readiness` in
`server/methodology/handoff.py` refuses `HANDOFF_INCOMPLETE` a CP-0 handoff
whose T8 rows do not cover every module the gate is expected to judge.

What the gate cost when it was used as a sequencing claim: run `62698a60…`'s
CP-0 marked CP-5 `CONDITIONAL` on an upstream handoff not yet produced and the
route ended BLOCKED with two modules paid for (`CLAUDE.md`, the closed
`CONDITIONAL` entry; `docs/DECISIONS.md` §61 change 1). §61 narrowed
`CONDITIONAL` to a source condition. It did not, and could not, change whether
CP-0 gates.

The ledger entry at `CLAUDE.md` line 1100 records the conflict and its
upgrade: "a dated decision entry saying which governs ... this entry exists so
nobody closes the gap by quietly weakening `route.py`."

## What it unblocks

The ledger entry at `CLAUDE.md` line 1100. If the answer is "the bundle
governs", the entry closes as a recorded decision and nothing else moves. If
the answer is "classification only", the host's route engine and handoff
validation keep enforcing the current bundle until a build removes the rule,
and the `CONDITIONAL`/`BLOCKED` cost above stops being possible on a route
whose sources are complete. Qualification cases that expect a readiness
verdict per consumer (`expects_ready`, `server/qualification/matrix.py` line
177, folded into the set digest at line 290) would need re-authoring under the
second answer.

## How it can land

If the bundle governs: a dated `docs/DECISIONS.md` entry and no file in
`vendor/` changes. This is the preferred outcome on the evidence: the rule is
stated in four places and enforced by two vendor scripts, and the host
following it is invariant 4 working.

If classification governs: an upstream build. The change touches CP-0's
contract, the canon, the reference sheet, the payload schema and two scripts;
`verify_package.py --refresh` synchronises the shared copies (24 of
`validate_handoff.py`, 22 of `completeness_check.py`) and regenerates the
integrity manifest; the host pulls the tree and moves §13's pin and the host
pins §63 lists. An authorised in-tree edit under §61's precedent is possible
in principle but is the wrong instrument here: §61 and §63 each changed one
rule in one contract, and this changes what CP-0 is.

## What the host does meanwhile

Enforces the bundle as vendored. `route.py` runs a node only on a `READY` or
`READY_WITH_LIMITATIONS` verdict; `CONDITIONAL` and `BLOCKED` hold it with no
attempt, reservation or call; the run document names the verdict as the cause
(`NodeView.gate_verdict`). The `_GATE_INSTRUCTION` restates line 359's rule that
source readiness does not assert whether upstream handoffs exist, which is the
bundle's own text and adds nothing. Nothing in `route.py` is weakened.
