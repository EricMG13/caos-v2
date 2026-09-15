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
- Provider/model: `openrouter / deepseek/deepseek-v4-pro-0813`
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
the provider transport. DeepSeek repeatedly failed the canonical Markdown and
citation-copying contract even after the final prompt clarified that eligible
citations are optional, supplied the exact source-ID whitelist, and required
each selected quote under `## Evidence Trace`.

Strict host validation remains unchanged. The shared prompt now distinguishes
eligible from required citations, forbids enumerating unquoted candidates,
names their required Markdown location, and repeats the exact delivered source
IDs at the generation point. Those clarifications improve the contract but do
not qualify this model. Use a separately qualified model for this route.
