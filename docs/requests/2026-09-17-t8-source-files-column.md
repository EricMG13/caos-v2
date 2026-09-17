# Vendor change request — carry T8's `Source files to attach` into `Recommendation`

**Date:** 17 September 2026. **Status:** awaiting the vendor, or a dated
authorization in the pattern of `docs/DECISIONS.md` §61 and §63.

**Asks for:** the bundle's own T8 parser to keep the column it already
validates, so the host can read a per-module evidence demand without inventing
one.

**Unblocks:** Completion Phase 10 Task 10.1, per-node evidence selection, and
with it four known-gaps entries and the 541-page-credit-agreement case that the
whole-source delivery cannot run.

## What the host needs and cannot get

A node's prompt today carries every block of every pinned source. Narrowing that
to what a module actually needs requires a per-module statement of which sources
it needs, and CP-0 is the only module that produces one.

CP-0's JSON payload schema declares exactly that: `evidence_demand`,
`active_representation_ids` and a `content_to_module_map`. All three live under
`runtime_output`. The host never receives them, and not by accident —
`server/methodology/invocation.py`'s `_FINAL_CHECK` instructs the model to
return only `canonical_markdown` and `citations`, and names `runtime_output`
among the fields that belong outside canonical front matter. **The host asks
CP-0 not to author the rows it would need.**

## Why the host will not work around it

Both available workarounds breach invariant 4, which says the bundle is the
methodology authority and the host adds nothing.

1. **Parse the Markdown registers.** All sixteen CP-0 registers declare
   `columns: none`. Reading them would mean the host asserting a table contract
   the bundle does not state.
2. **Re-parse T8's fifth column.** T8's header does carry `Source files to
   attach`, which is the nearest thing in the tree to a per-module evidence
   demand. But the vendor's `parse_t8` reads cells 0, 1, 2, 3, 6 and 7 — never
   cell 4 — and `Recommendation` has no field for it. The column is validated
   for row width and then discarded. A host parser that kept it would be a
   second reader of one table, and two readers of one table can disagree.

The catalog offers no third route: it contains no `evidence_demand`,
`active_representation`, `source_files` or `evidence_class`.

## The change

Add the fifth column to the vendor's own `Recommendation`, so `parse_t8`
surfaces what the schema already declares and the validator already checks.
Nothing about the table's shape changes; the parser stops dropping a column.

That is the smallest change that unblocks the host **and** keeps one reader of
one table.

## The alternative, and the question it forces

The host could instead take ownership of a CP-0 register's shape by dated
decision, as §61 and §63 did for the CONDITIONAL verdict and the disqualifier
columns. That needs an answer to a question this request cannot settle:

**May a model-authored register decide what evidence a *downstream* node is
allowed to cite?**

Readiness is model-authored too, but it fails closed — a wrong readiness blocks
a node. Evidence selection does not. Narrowing is monotone downward on
anchoring: ambiguity is counted over every token on the page from the live
source, and the delivery check runs afterwards, so a narrowed delivery can never
rescue an ambiguous quote and can turn a downstream node's *truthful* quote of a
pinned source into `CITATION_NOT_DELIVERED`. One model-authored register would
then decide what a later module may prove. That is an owner's decision, not an
implementer's.

## What was measured

Completion Phase 10 Task 10.1, on 17 September 2026, which stopped rather than
build: sixteen CP-0 registers, sixteen `columns: none`; `parse_t8`'s cell
indices; `Recommendation`'s fields; `_FINAL_CHECK`'s exclusion of
`runtime_output`; and the absence of all four candidate keys from the catalog.
Its ledger delta records that the entry specifying this repair also misdescribed
the host's own readiness row, claiming a `readiness_effect` field that exists
nowhere under `server/` — the repair was specified against the schema rather
than against the record.
