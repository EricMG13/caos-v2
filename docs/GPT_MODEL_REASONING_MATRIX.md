# GPT model and reasoning matrix

Current for new work from 19 September 2026. This is the Codex adaptation of
the owner's `claude_fable_and_opus_reasoning_matrix.md`. It supersedes
Claude-specific model routing in forward-looking plans and prompts. Historical
records keep the model and effort that actually ran.

## Model mapping

| Source role | GPT equivalent | Why |
|---|---|---|
| Claude Opus 5 — daily-driver workhorse and verification specialist | `gpt-5.6-sol` | reliable agentic implementation and review workhorse |
| Claude Fable 5.1 — long-horizon autonomous engine and chief architect | `gpt-6-astra` | strongest available model for complex, multi-stage and architectural work |

There is no Codex `ultrathink` prompt lever. A source request for
`ultrathink`, `max` or `ultra` maps to the actual Codex reasoning setting
`xhigh`, preserving the repository ceiling in `docs/DECISIONS.md` §81. Do not
put those source terms in a Codex prompt and do not dispatch above `xhigh`.

## Settings matrix

| Model | Effort | Workflow role | Use here |
|---|---|---|---|
| `gpt-5.6-sol` | `low` | mechanical work | configuration, formatting, generated ledgers, straightforward fixtures and documentation |
| `gpt-5.6-sol` | `medium` | default development | routine implementation, tests, bug fixes, API/UI wiring, PR preparation and ordinary exact-range review |
| `gpt-5.6-sol` | `high` | critical implementation | deterministic calculations, store transitions, billing and localized concurrency work |
| `gpt-5.6-sol` | `xhigh` | confidence and acceptance | task acceptance and the whole-phase `confidence-review` |
| `gpt-6-astra` | `medium` | long-horizon execution | multi-file root-cause fixes and phased autonomous implementation |
| `gpt-6-astra` | `high` | architecture and governance | plans, specifications, cross-system design and vendor request documents |
| `gpt-5.6-sol` | `xhigh` | targeted verification | invariant audits, adversarial shootouts and task acceptance |
| `gpt-6-astra` | `xhigh` | independent adversarial verification | the whole-phase adversarial audit and the final all-phases review |

## Dispatch rules

- Use `gpt-5.6-sol` at `medium` by default; raise effort only for a named risk.
- Use `gpt-6-astra` when the work is long-horizon, architectural, cross-cutting
  or deliberately independent from the implementation model.
- At a phase freeze: `gpt-5.6-sol` `xhigh` confidence review, remediate and
  retest, then `gpt-6-astra` `xhigh` adversarial review, remediate and reverify.
- Use `gpt-5.6-sol` `xhigh` for targeted invariant audits and adversarial
  shootouts; use `gpt-6-astra` `xhigh` for the independent phase audit and the
  one final review across all phases.
- Record the actual model, version and effort at every formal checkpoint.
- Model choice never expands authority to spend, call a provider, edit the
  vendor bundle, push, merge or deploy.
