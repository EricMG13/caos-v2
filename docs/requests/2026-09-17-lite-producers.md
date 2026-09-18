# Request: name the owner of every LITE object a consumer accepts

Date: 2026-09-17. Bundle: `vendor/deploy-v` at build `30222a49` (upstream
`EricMG13/Deploy-V@c4d2e356` plus §61's two edits and §63's one).

**Status (2026-09-18):** done, option 1, in build `62a94ccd` under the
owner's authorisation (`docs/DECISIONS.md` §92, `docs/VENDOR_CHANGES.md`):
`CP-L10 -> CP-2A` carries `lite_fundamental_credit_screen` and
`CP-L10 -> CP-3C` carries `lite_liquidity_sensitivity_screen` (a judgement,
recorded in §92), both `allowed_use: SCREENING_ONLY`; CP-3C's heading is
keyed and names its three objects
(`tests/test_bundle_pin.py::test_every_lite_edge_into_a_named_object_consumer_declares_the_object_it_carries`).
The three pathways stay disabled in `ADAPTER_ROUTES` until their own tasks.

## What is asked

The bundle declares four LITE objects that FULL modules accept under
`LITE_CREDIT_22`, and no catalog module owns them. One of two changes to
`vendor/deploy-v/skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json`:

1. **Preferred.** Every LITE edge whose target accepts a named object declares
   `accepted_object_id` naming one the source's handoff carries. Two already do
   (lines 2484 and 2491: `CP-L10 -> CP-2H` carries
   `lite_liquidity_sensitivity_screen`, `CP-L10 -> CP-4C` carries
   `lite_legal_structure_capacity_screen`). Two do not: `CP-L10 -> CP-2A`
   (CP-2A accepts `lite_fundamental_credit_screen` or the liquidity object)
   and `CP-L10 -> CP-3C` (CP-3C's row in `CP_DEPLOY_V_EXECUTION_PROFILES_v1.json`
   lines 152-155 accepts the liquidity, market-recovery and legal-capacity
   objects). With them, `skills/cp-3c-refinancing-lme-risk/SKILL.md` line 13
   gains the keyed heading `## LITE profile compatibility — CP-3C` and the
   three vendor fields the other consumers' blocks carry, so the host reads it.
2. **Alternative.** CP-L10's `artifact_contract` (catalog line 692) declares
   the five objects its handoff owns after absorption instead of one. This
   needs a host change too: `server/methodology/invocation.py::owned_objects`
   reads one string per module. Either way the bundle, not the host, says
   which object CP-L10's handoff carries to which consumer.

## Evidence in this tree

- The producers are absorbed, not missing: `superseded_module_ids` maps
  CP-L20, CP-L23, CP-L30 and CP-L40 to `absorbed_by: CP-L10`; CP-L10's
  `required_table_ids` carry TL20.*, TL23.*, TL30.* and TL40.*;
  `skills/cp-l10-financial-change-screen/SKILL.md` heads one "Absorbed phase"
  each at lines 293, 476, 659 and 842, with an `owned_object` at 303, 486, 669
  and 852, and line 10 says "complete the five internal screens ... within the
  one CP-L10 handoff". No `skills/cp-l2*`, `cp-l3*` or `cp-l4*` directory
  exists; the payload schemas ship as `references/CP-OS_MIRROR_CP-L20__…`,
  `L23`, `L30`, `L40`; the profile lists all four
  (`CP_DEPLOY_V_EXECUTION_PROFILES_v1.json` lines 42-45).
- The catalog owns one object: line 692, `lite_financial_change_screen`, is
  the only `owned_object` in the file. `lite_fundamental_credit_screen` and
  `lite_market_recovery_opportunity_screen` appear on no edge of either profile.
- Consumer blocks: `cp-2a-downside-pathway/SKILL.md` 45-51,
  `cp-2h-ratings-migration-trigger/SKILL.md` 48-54,
  `cp-4c-restructuring-fulcrum/SKILL.md` 49-55; CP-3C's (line 13) is unkeyed
  prose the host does not read (`CLAUDE.md` line 585).
- The host: `invocation.py::named_objects` (645-686) enforces a boundary only
  where an input on the pinned route owns or carries an accepted id (§46.1
  refinement: holding a node forever would be a host-invented graph).
  `tests/test_handoff_invocation.py::test_an_edge_carried_object_meets_the_boundary_on_other_lite_routes`
  shows the carried objects releasing CP-2H and CP-4C on
  `LITE_FULL_CREDIT_SCREEN` and `LITE_DISTRESSED_RESTRUCTURING`; CP-2A and
  CP-3C there have no enforceable boundary at all.
- `server/methodology/handoff.py` line 55: `ADAPTER_ROUTES` is LITE earnings
  and RELATIVE_VALUE only; `docs/COMPLETION_PLAN.md` O03 and the ledger's
  upgrade line ("a vendor owner for every accepted object before those routes
  are enabled") are why. The brief said no catalog edge carries these objects;
  two do, so the request is narrowed to the two that do not and the heading
  the host cannot read.

## What it unblocks

`LITE_COVENANT_REFINANCING` (CP-0, CP-L10, CP-3C, CP-5),
`LITE_DISTRESSED_RESTRUCTURING` (CP-0, CP-L10, CP-2A, CP-2H, CP-4C) and
`LITE_FULL_CREDIT_SCREEN` (nine nodes): Completion Tasks 9.5-9.7, held on O03;
the ledger entry at `CLAUDE.md` line 585 and its profile cross-check.

## How it can land

Preferred: an upstream build. Upstream edits the catalog and CP-3C's `SKILL.md`,
runs `verify_package.py --refresh`, and the host pulls the tree, moving §13's
pin and the six host pins §63 lists in one `docs/DECISIONS.md` entry. The
typed edge set is what `route_digest` covers, so every LITE route's digest
moves; that is a vendor fact and should arrive as one.

Otherwise: an authorised in-tree edit under §61's precedent, scoped to two edge
fields and one heading, with its own dated decision entry, the refresh and the
pin move. The host may not take it alone: the catalog is an upstream file
(invariant 4, §6), and which object CP-L10's handoff carries to CP-2A or CP-3C
is the vendor's claim about its own artifact, not something the host can
prove from bytes.

## What the host does meanwhile

Refuses the three pathways `HANDOFF_MODULE_UNSUPPORTED` at `execution_input`
and at acceptance, before any attempt, reservation or call; reads only keyed
`SKILL.md` blocks; enforces the boundary only where CP-L10's edges carry an
object; invents no owner. Tasks 9.5-9.7 stay held, briefs written.
