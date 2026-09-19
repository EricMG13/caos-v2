# GPT model and reasoning matrix

Current for new work from 19 September 2026. This is the Codex adaptation of
the owner's `claude_fable_and_opus_reasoning_matrix.md`. It supersedes
Claude-specific model routing in forward-looking plans and prompts. Historical
records keep the model and effort that actually ran.

## Model mapping

The source matrix defines two roles, not a two-model allow-list. Codex splits
those roles across the available GPT portfolio and chooses the narrowest model
that fits the work.

| Source role | GPT equivalents | Why |
|---|---|---|
| Claude Opus 5 — daily-driver workhorse and verification specialist | `gpt-5.6-luna` for mechanical edits; `gpt-5.6-terra` for routine implementation and ordinary review; `gpt-5.6-sol` for reliability-critical implementation and verification | preserves the source role while avoiding an expensive verification model for mechanical work |
| Claude Fable 5.1 — long-horizon autonomous engine and chief architect | `gpt-6-astra` | strongest available model for complex, multi-stage and architectural work |
| Defensive-security specialist | `gpt-daybreak-blue-latest` | broad defensive cybersecurity work, security review and remediation only |
| Previous-generation independent baseline | `gpt-5.5` | deliberate compatibility or second-opinion work where a previous-generation perspective is useful; never the default |

There is no Codex `ultrathink` prompt lever. A source request for
`ultrathink`, `max` or `ultra` maps to the actual Codex reasoning setting
`xhigh`, preserving the repository ceiling in `docs/DECISIONS.md` §81. Do not
put those source terms in a Codex prompt and do not dispatch above `xhigh`.

## Settings matrix

| Model | Effort | Workflow role | Use here |
|---|---|---|---|
| `gpt-5.6-luna` | `low` | mechanical work | configuration, formatting, generated ledgers, docstrings and straightforward fixture edits |
| `gpt-5.6-terra` | `medium` | default development | routine implementation, tests, bug fixes, API/UI wiring, PR preparation and ordinary exact-range review |
| `gpt-5.6-sol` | `medium` / `high` | reliability-critical development | deterministic calculations, store transitions, billing, migrations and localized concurrency work |
| `gpt-5.6-sol` | `xhigh` | confidence and targeted verification | invariant audits, high-consequence acceptance and the whole-phase `confidence-review` |
| `gpt-6-astra` | `medium` | long-horizon execution | multi-file root-cause fixes and phased autonomous implementation |
| `gpt-6-astra` | `high` | architecture and governance | plans, specifications, cross-system design and vendor request documents |
| `gpt-6-astra` | `xhigh` | independent adversarial verification | the whole-phase adversarial audit and the final all-phases review |
| `gpt-daybreak-blue-latest` | `high` / `xhigh` | defensive-security specialist | threat-led review, auth/secrets hardening, vulnerability remediation and security release gates |
| `gpt-5.5` | `medium` / `high` | previous-generation baseline | deliberate compatibility review or independent second opinion when that perspective adds evidence |

## Dispatch rules

- Use `gpt-5.6-terra` at `medium` for ordinary implementation and review;
  `gpt-5.6-luna` at `low` for bounded mechanical work.
- Use `gpt-5.6-sol` when correctness or verification risk is higher than an
  ordinary slice; raise effort only for a named risk.
- Use `gpt-6-astra` when the work is long-horizon, architectural, cross-cutting
  or deliberately independent from the implementation model.
- Use `gpt-daybreak-blue-latest` only for defensive-security work. Use
  `gpt-5.5` only when a previous-generation baseline is intentionally useful,
  not as routine fallback.
- At a phase freeze: `gpt-5.6-sol` `xhigh` confidence review, remediate and
  retest, then `gpt-6-astra` `xhigh` adversarial review, remediate and reverify.
- Use `gpt-5.6-sol` `xhigh` for targeted invariant audits and adversarial
  shootouts; use `gpt-6-astra` `xhigh` for the independent phase audit and the
  one final review across all phases.
- Record the actual model, version and effort at every formal checkpoint.
- These are routing defaults, not an allow-list: any available GPT model may be
  used when its documented strength is the best fit, with the reason recorded.
- Model choice never expands authority to spend, call a provider, edit the
  vendor bundle, push, merge or deploy.
