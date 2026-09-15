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
