# Host adapter contract

Observed at `26d7ee99f6c90396ddb5f7c3614cdd733af4ed76`; target contract
decided in [DECISIONS.md §29](DECISIONS.md#2026-09-12-29--canonical-markdown-is-the-authoritative-handoff).

## Authority and handoff

Deploy V requires each `CANONICAL_MARKDOWN` module to author and validate one
exact Markdown artifact. That Markdown, including its YAML envelope and complete
registers, is the authoritative downstream handoff; chat, HTML and other views
are not another analytical report ([vendor contract](../vendor/deploy-v/CANON_SHARED.md#cp-markdown-only-handoff-specification)).

The host owns the run, source-set and extraction-manifest identities, resolved
route, bundle manifest/build, adapter version, and accepted upstream artifact
identities. Typed UI fields are closed, validated sidecar projections of the
accepted Markdown. They neither replace it nor become model-authored authority.
The UI/report renders host-held Markdown and projections.

CP-0 is the catalog-selected preparation/readiness node. The host extraction
manifest is preparation metadata supplied to CP-0; it is not a second LLM route
stage. `CP-PARSE` remains an authority alias for archived compatibility, not an
additional executable node. Preparation runs once
([catalog preparation](../vendor/deploy-v/skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json#L1351),
[host alias](../server/methodology/bundle.py#L35)). Excel and Word remain out of
scope; their archived contracts remain archived
([decision §14](DECISIONS.md#2026-09-10-14--the-host-places-no-model-build-and-no-publication-module-the-deliverable-is-rendered-by-the-host)).

## Current versus target

| | Current implementation | Target adapter |
|---|---|---|
| Provider response | Closed JSON: cited `claims`, plus CP-0 readiness | Exact canonical Markdown plus validated projections |
| Stored handoff | Host JSON envelope of claims/readiness | Validated canonical Markdown, unchanged, with host identity metadata and sidecars |
| Upstream context | Direct predecessors' claim summaries | Direct predecessors' exact accepted Markdown and pinned identities |
| Presentation | JSON-derived UI/report | Host rendering of the authoritative Markdown and projections |

The current JSON claims executor does **not** implement the target Markdown
contract ([executor](../server/methodology/executor.py),
[stored envelope](../server/methodology/runner.py)).

## Illustrative examples (not vendor-conformance fixtures)

- **Valid:** exact Markdown passes the vendor filename/envelope/heading/status
  gates; host identities match the pinned run; sidecars validate and downstream
  receives those exact bytes.
- **Restricted:** Markdown is valid with the vendor-declared restricted status;
  the host preserves the exact handoff and presents validated limitations.
- **Blocked:** Markdown is malformed, identity mismatches, or declares a blocking
  status; the host accepts no analytical handoff and releases no downstream node.

These examples explain host behavior only. Vendor schemas and validators remain
the conformance authority; no vendor field is added here.
