# CCL FY2025 live qualification result

## Corpus and key

The case uses the public Carnival Corporation & plc FY2025 SEC filing extract
from the existing three-issuer assessment. Its source document digest is
`8fa7fceda34be50b3b9b5406e0c9269b5269870d1cd8c2bdafb682755a1c88e6`.

Expected citations were selected from the human-authored answer key at
`/Users/ericguei/Documents/Co-Pilot Agents/assessment_3issuer_20260719/corpus/ANSWER_KEY_3ISSUER.md`,
whose digest at selection was
`5be464735d2794c0ef832dd4f2d739cf270e95cf17c522473f95466b5719c376`.
The key is deliberately not an admitted document: a model must not receive the
answers it is being evaluated against.

## Run

- Qualification-set digest: `f5555753cf7b39868fa4885d95a0b80847c61204a4b3ebe5fffe8345587c327e`
- Route: `LITE_CREDIT_22 / LITE_EARNINGS_UPDATE` (`CP-0`, `CP-L10`, `CP-5`)
- Provider/model: `openrouter / deepseek/deepseek-v4-pro-0813`
- Price configuration: `$0.96` input and `$2.88` output per million tokens, dated 2026-09-15
- Run ceiling: `$22.00`
- Local development run: `01b79673-cbe6-4e5c-8751-642ea69335cd`

## Result

The run is **not qualified**. CP-0 made three billed attempts and none produced
an accepted canonical handoff:

| Attempt | Refusal |
|---|---|
| 1 | `HANDOFF_INCOMPLETE` |
| 2 | `HANDOFF_MALFORMED` |
| 3 | `HANDOFF_MALFORMED` |

Recorded charge: `$0.465377216`. No artifact or matrix was produced, so no
evidence row or verdict was recorded. A qualification verdict must never turn
this failed host validation into `QUALIFIED`.

## Canonical compatibility diagnosis

All three stored provider bodies used the required closed JSON transport. The
canonical Markdown inside them failed for three concrete instruction-following
reasons: a non-canonical snake-case T8 header, an omitted T8 register, and
citations whose `matched_text` was not repeated verbatim in the Markdown body.
The request had placed its response contract before the large evidence section
and ended on evidence, leaving those constraints far from the generation point.

The host now closes the tagged evidence section and repeats the closed transport,
six-heading order, register, CP-0 T8-header, and citation checks at the end of the
prompt. Strict handoff and citation validation is unchanged.

A fresh validation run, `90dc1bb3-6301-4af7-955e-717824672a90`, reached the
provider twice but stopped both times with `PROVIDER_UNAVAILABLE`. Neither
attempt returned a body, generation ID, or charge, so live confirmation remains
pending and the model remains **not qualified**.
