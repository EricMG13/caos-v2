# Virgin Media O2 FY2025 live qualification result

## Corpus and key

This case uses two existing public issuer documents:

- `Virgin-Media-O2-Q3-2025-Earnings-Release.pdf`, SHA-256
  `505bf1a0f4181c9cdffeeac7e6af3253d1883788e9cd1a81e65952e008aa17a1`
- `Virgin-Media-O2-Q4-2025-Earnings-Release.pdf`, SHA-256
  `66055bbb8d27721d07a5e8cb834c9b96a256ada45a0812ea4fb2e7202ee4f64d`

The answer key was fixed from those issuer documents before the provider run.
It tests a current borrowing-capacity statement under CP-0, the £1,021.7
million Q4 goodwill impairment under CP-L10, and the issuer's non-GAAP
liquidity limitation under CP-5. The qualification-set digest is
`ec84bf8bbb1b45fd715d52466b9142778b4346ab13b252951db0b589209d07d1`.

A first prepared pack also included the Q3 2025 quarterly bond report. Its
CP-0 request exceeded the host's 1 MiB request ceiling and refused as
`CONTEXT_OVER_CEILING` before an attempt, reservation, provider call or charge.
The detailed bond report was removed rather than weakening the resource gate;
the final two-document CP-0 request was 448,826 bytes.

## Run

- Route: `LITE_CREDIT_22 / LITE_EARNINGS_UPDATE` (`CP-0`, `CP-L10`, `CP-5`)
- Provider/model: `openrouter/ionstream/default / deepseek/deepseek-v4-pro-0813`
- Price configuration: `$0.96` input and `$2.88` output per million tokens,
  dated 2026-09-15
- Run ceiling: `$22.00`
- Local development run: `2abc6c57-bb8f-4840-970e-91830191d494`
- Source-set approval preview:
  `0bc48fd15025fe6a3a3ce51c389211c767d46cd7a7f2148c8aa5457489c196e4`
- Research-plan approval preview:
  `01760913dd364272c2ec0354e28a893793a955bd40fb3a3c6648e0a2baf00fa0`

## Result

The model is **not qualified**. CP-0 made three billed attempts and no
canonical handoff was accepted:

| Attempt | Charge | Host result | Deterministic diagnosis |
|---|---:|---|---|
| `92d8e655-cec3-46b8-ac88-9068fff2d9e2` | `$0.170135040` | `HANDOFF_MALFORMED` | Returned 94 citations; none of their exact quotes appeared in the Markdown body. |
| `28ef1818-9de3-47e7-85c1-a5756e50b675` | `$0.163118848` | `CITATION_NOT_DELIVERED` | Returned 61 citations, changed one pinned source UUID's final digit, and quoted none in the body. |
| `de292860-6163-4310-a523-9319eb60d36c` | `$0.154520128` | `HANDOFF_MALFORMED` | Used valid source IDs but quoted none of 14 citations and emitted `## Analysis` twice. |

Stored provider reconciliation identities:

- Attempt 1: generation `gen-1789467788-3tCVdQqEtUfF8VCYyhYf`, response digest
  `7e0fade839db3719855f64433f9caa9171b9e948c800abed35ce766a247900f9`
- Attempt 2: generation `gen-1789468111-xAuTdtAonxIKAKRnCubv`, response digest
  `873afcbac528a8379a6f6213896d493d0c33a234f9321338f5b951d75682dc71`
- Attempt 3: generation `gen-1789468381-JhS0gxgw8RWuDXWEI7A9`, response digest
  `503c8882bf480036399a338aeaa1895a66bac41f2fff373696d67e78af7f2119`

Total recorded charge was `$0.487774016`. CP-L10 and CP-5 were not called.
No artifact, orchestration proof, qualification matrix, evidence row or verdict
was produced. The exhausted run was closed as `FAILED` after the third attempt
so it cannot be resumed accidentally. It must not be represented as
`QUALIFIED`.

The adapter prompt was revised between these failed attempts to isolate the
observed copying defects. This cross-revision sequence is diagnostic only and
cannot support a positive qualification decision. Any future qualification
must start a fresh prepared run against one frozen adapter revision.

## Compatibility conclusion

OpenRouter returned well-formed closed JSON bodies, generation identifiers and
charges on all three attempts. The remaining incompatibility is therefore not
the provider transport. OpenRouter reconciliation subsequently established that
all three attempts were served by Ionstream with zero reasoning tokens. The
result therefore rejects only the `openrouter/ionstream/default` deployment
profile; it is not evidence that first-party or reasoning-enabled DeepSeek is
incapable of the contract.

Strict host validation remains unchanged. The shared prompt now distinguishes
eligible from required citations, forbids enumerating unquoted candidates,
names their required Markdown location, and repeats the exact delivered source
IDs at the generation point. Those clarifications improve the contract but do
not qualify this model. Use a separately qualified model for this route.

## Controlled profile follow-up — 2026-09-15

The runtime now sends an optional lowercase OpenRouter endpoint tag and
reasoning effort, and binds both into qualification identity. A fresh adapter
revision, `canonical-markdown-v2`, prevents the revised prompt from borrowing a
v1 verdict.

OpenRouter's public endpoint catalog reported the first-party endpoint live
under tag `deepseek`, with reasoning, reasoning-effort and JSON response-format
support. Nevertheless, harmless probes and a fresh prepared qualification run
all returned `404 No endpoints found for deepseek/deepseek-v4-pro-0813` before
generation. They produced no generation ID and no charge. Since the same model
remains available through Ionstream, this is an account/workspace routing or
data-policy restriction, not a demonstrated model or parameter failure.

An `openrouter/ionstream/xhigh` JSON probe succeeded as generation
`gen-1789472086-Xy5p8onbmebuRtteQRNK`: 15 prompt, 21 completion and 15 native
reasoning tokens, `finish_reason=stop`, charge `$0.00007488`. This proves that
the available deployment honors the requested reasoning profile.

The subsequently authorized full-corpus run
`62307d9b-f2d4-49f3-b015-82fea3b07298` bound
`openrouter/ionstream/xhigh`, adapter `canonical-markdown-v2`, and the unchanged
qualification-set digest. CP-0 generation
`gen-1789475926-OwNgVKf0G7QapLweplaL` used 153,892 prompt, 10,285 completion
and 6,286 native reasoning tokens, finished normally with `stop`, and charged
`$0.177133888`. The host rejected it as `CITATION_NOT_DELIVERED`; CP-L10 and
CP-5 were not called, and no artifact, proof, matrix, evidence row or verdict
was produced.

This rules out fallback routing, disabled reasoning and truncation as causes of
the observed contract failure. DeepSeek V4 Pro remains a capable general agent,
but this deployment is not compatible with the current one-shot canonical
handoff contract. Repeating the same frozen temperature-zero call would not add
a new controlled variable and was not purchased.

## Gemini 3.8 Flash follow-up — 2026-09-15

The replacement candidate used model `google/gemini-3.8-flash`, pinned
OpenRouter endpoint `google-ai-studio`, reasoning effort `high`, the same public
corpus and qualification-set digest, adapter `canonical-markdown-v2`, and the
same `$22.00` run ceiling. Current dated pricing was `$0.75` input and `$3.75`
output per million tokens. Google documents 1,048,576 input and 65,536 output
tokens for this model, but the unchanged CAOS provider ceiling remained 32,768
completion tokens.

Fresh run `7c9c8d60-7b42-4f38-9b42-bb4e1d1afb47` stopped at CP-0 as
`PROVIDER_OUTPUT_TRUNCATED`. Generation
`gen-1789477949-PdZ0oPgEZZGQjoUQbTE1` reconciled to Google AI Studio, 174,278
native prompt tokens, 32,761 native completion tokens, 29,454 native reasoning
tokens, `finish_reason=length`, and `$0.25356225` total cost. CP-L10 and CP-5
were not called, and no artifact, proof, matrix, evidence row or verdict was
produced.

This profile is not qualified at the shipped 32,768-token ceiling. A same-cap
retry changes no controlled variable and must not be purchased. A 65,536-token
experiment would be materially different, but requires an intentional runtime
change, fresh build identity and fresh authorization before spend.

## 65,536-token attempt — result collection indeterminate

After the authorized ceiling/profile change at `691637b`, the prepared attempt
used `openrouter/google-ai-studio/high/65536` with the same frozen corpus and
`$22.00` set/run ceilings. `perform()` returned to its temporary qualification
collector, but the collector then raised while JSON-encoding the proof's
`frozenset` of anchored citations. Its `finally` block dropped the disposable
database before it printed the run ID, generation IDs, charges, node status or
matrix.

The OpenRouter activity endpoint is aggregate-only and requires a management
key for this account; reconciliation therefore returned `403`. The number of
provider calls, their individual charges and the canonical outcome are
unrecoverable from the surviving record. No artifact, evidence row or verdict
may be claimed from this attempt. Future `perform()` calls persist the complete
or partial immutable snapshot and its bound evidence row before returning; the
collector serializes its digest and retains the disposable database/blob root
for external review. This is not permission to repeat the indeterminate paid
attempt.

## Recovered 65,536-token retry — Gemini protocol incompatibility confirmed

The recovery candidate at `40a13dd` persisted the complete immutable performed
snapshot and its bound evidence row before its collector returned. The fresh
run `1590edfc-a747-4c69-ae1a-06455edeb1a7` used the same frozen
qualification-set digest and profile
`openrouter/google-ai-studio/high/65536`. CP-0 generation
`gen-1789486082-I1BG57GiSspM6MntssMu` was served by Google AI Studio, finished
normally with `stop`, used 177,062 native prompt, 36,606 native completion and
28,952 native reasoning tokens, and cost `$0.270069`.

The retained diagnostic was a valid closed JSON transport with canonical
Markdown and four citations. Each citation named delivered evidence and
uniquely anchored in that evidence. The vendor Markdown validator also passed.
The host nevertheless correctly refused CP-0 as `HANDOFF_MALFORMED`: none of
the four evidence quotations occurred character-for-character in the Markdown
body. Safe replay found case-insensitive matches for three and punctuation-
normalized matches for all four, including an Evidence Trace section. Gemini
therefore rewrote the quotations while retaining their meaning, instead of
copying them verbatim as the pinned canonical protocol requires.

No artifact, orchestration proof, matrix, evidence row for a verdict, or
qualification verdict exists. The performed snapshot digest is
`713ba25de76d8edf3dcde577c1ac9cc0d3000fc0079ea009d8d98f04ba26933f` and its
bound evidence digest is
`0e5e64d3948bbc149ac313185d1d47343987d10d87e41f11a9c0b33eaedd192c`.
The retention failure is fixed; Gemini 3.8 Flash is not qualified for this
one-shot canonical handoff contract. Do not buy another Gemini retry without a
materially different, explicitly authorized protocol experiment.

## OpenAI Terra provenance diagnosis — 2026-09-15

The separately authorized Terra run used `openai/gpt-5.6-terra` through pinned
`openrouter/openai/flex/high/65536`, with the same two-document VMO2 set and a
`$22.00` maximum. CP-0 made one billed call: run
`650a2618-0fbd-48d3-ad12-27bbbd7edc10`, attempt
`9307791d-bdb5-456b-a8ea-36b82e8bbc99`, generation
`gen-1789491046-8S6zV4AASHeN1hdJmopq`, charge `$0.23236475`.

The response returned a controlled source-readiness block. Its diagnostic and
performed evidence are retained locally (diagnostic digest
`2c52bf3ac3ea29d1d1b2304087579a643b50fef374a12393c27c40cbdc07c1dd`,
performed digest
`17cd20b9a79fe742e37233ac1874e2fd342afec3ccc7447a8e7a067edb72b0cd`).
It correctly observed that CP-0 had received evidence excerpts but not the
host's immutable-original, source-root, extraction-manifest or managed-run
facts needed to author P1–P8. It also identified the genuine limitation that
the two earnings releases alone omit primary financial/legal material.

This is not a Terra or OpenRouter protocol failure. The v2 prompt omitted
metadata that the host already retained. `canonical-markdown-v3` now supplies
the verified CP-0 source-preparation context and rechecks original blobs at
acceptance/replay; it is a materially changed candidate. The v2 run produced no
accepted artifact or qualification verdict and cannot be reused. A fresh,
explicitly authorized live run is required after v3's local gates and, if the
source set changes, after a new frozen qualification key is prepared.

## OpenAI Terra v3 qualification run — 2026-09-16

The first run of this set to finish its route. `canonical-markdown-v3` through
the same pinned profile, the same frozen two-document corpus and the same
answer key; the model is **still not qualified**, but for a different and much
narrower reason than either run before it.

- Adapter: `canonical-markdown-v3`
- Provider/model: `openrouter/openai/flex/high/65536` / `openai/gpt-5.6-terra`
- Price configuration: `$0.000002` input and `$0.000012` output per token
  ($2.00 / $12.00 per million), dated 2026-09-16, read from OpenRouter's
  published model list on the day of the run
- Run ceiling: `$22.00`; reservation per call `$2.883584`
- Local development run: `e0e101b5-a908-4b9b-913d-45184a6f3a54`
- Qualification-set digest (unchanged):
  `ec84bf8bbb1b45fd715d52466b9142778b4346ab13b252951db0b589209d07d1`
- Evidence digest: `0a1b6faa43f5361b66f9acd391793a9ceeb56d54e8b05e676e8a41651d735476`
- Performed digest: `fd20bb5f19dbd16fd3fe6f3e78229a4c9057c33bb6c42ff6191ee0245084b170`
- Retained database `caos_test_d5b8c78452644d28be02943a6c3750c5`, blob root
  `/var/folders/81/bwblpst93lb6wb3lwrk8k6800000gn/T/caos-vmo2-v3-yn_c83lm`

### Run

The route ran to `COMPLETE`. Every module answered on its **first** attempt —
no retry, no refusal row, no replay:

| Module | Charge | Generation | Result |
|---|---:|---|---|
| CP-0 | `$0.2534435` | `gen-1789546489-g3Hv4o2ZMMQ5ASVL5nxI` | accepted |
| CP-L10 | `$0.28338425` | `gen-1789546572-n2msOOtl3OBd1ozbsiZx` | accepted |
| CP-5 | `$0.2856555` | `gen-1789546646-XaxBVRgUVG4KHpSobgxk` | accepted |

Total recorded charge `$0.82248325` against the `$22.00` ceiling. Three
artifacts, fourteen citations, and the host re-located **all fourteen** in its
own token index. The orchestration proof re-derived every record and every
citation. `attempt_refusals` is empty.

That settles what the two earlier runs could not. DeepSeek V4 Pro failed the
literal-quotation contract three times and Terra under v2 returned a controlled
readiness block; under v3 the same provider, corpus and key produce a completed
route whose every quote anchors. The missing CP-0 provenance context was the
cause, and supplying it was the fix.

### Verdict

**Not qualified.** The matrix row reads `proven=true, met=2, missed=1`:

- **CP-L10 — met.** The £1,021.7 million Q4 goodwill impairment, quoted exactly.
- **CP-5 — met.** The issuer's non-GAAP liquidity limitation, quoted exactly.
- **CP-0 — missed.** The key names the current borrowing-capacity statement
  ("When compliance reporting requirements have been completed and assuming no
  change from 31…"). CP-0 cited four blocks from the correct documents,
  including the consolidated third-party debt nominal amounts, but not that
  sentence.

This is a genuine evidence-selection miss, not a protocol failure: the module
answered, quoted the right documents, and every quote it gave anchored. It
simply did not select the block the key names.

`qualification_performed.complete` is **false** and no verdict was recorded.
That is the gate landed at `b456966` doing its job — before it, `complete` was
`matrix is not None`, and this snapshot, missing a key, would have been
signable as QUALIFIED. Nothing here may be represented as a qualified build.

An upgrade attempt must be a new, separately authorized run; the corpus and key
are unchanged, so it would not be a new qualification identity.
