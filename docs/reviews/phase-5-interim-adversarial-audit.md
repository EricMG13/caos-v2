# CAOS Repair Phase 5 — interim adversarial audit

- **Model and effort:** Codex `gpt-6-astra`, `xhigh`.
- **Scope:** `0deb4a4..fdb202f`, the Phase 4 acceptance through the first
  integrated Phase 5 candidate. Later CP-CF and revision commits are outside
  this audit; the deliverable files it examined did not change before the
  documented remediation.
- **Method:** the three-persona `adversarial-reviewer` workflow: Saboteur,
  New Hire and Security Auditor. This is an interim review requested before
  Phase 5 completion, not the phase-exit audit.

## Verdict: BLOCK at the reviewed commit; remediated afterwards

### AR-1 — generated packages could reject themselves (Critical)

The Saboteur and New Hire reproduced a valid, highly repetitive canonical
handoff whose `payload.json` and `deliverable.html` exceeded the verifier's
100:1 compression ratio. `build_package` DEFLATEd every member, while
`verify_package` rejected the resulting archive. The content was below every
absolute member limit.

`351dd6e` fixes the producer rather than weakening the verifier: it computes
the deterministic raw-DEFLATE size and stores only a member that would exceed
the ratio. The regression builds a 20,000-repeat narrative, verifies it in the
host and an isolated archived verifier, and asserts the two high-ratio members
are stored. Existing hostile-ratio and hard output-cap tests remain green.

### AR-2 — host refusal retained a hidden exception context (P2)

The New Hire showed that `raise ... from None` inside the `except` suppressed
display but retained `__context__`. `351dd6e` records the safe code inside the
handler and raises outside it; the regression now asserts both `__cause__` and
`__context__` are absent.

### Recorded limits

- An archive proves internal consistency only. The verifier's own bytes have
  no external signature trust anchor; this is an explicit §55 limit, not an
  arbitrary-code execution path in the trusted verifier.
- CP-CF transport and lineage tests do not economically qualify an LLM's use
  of workbook content; §56 records that limit.

No unpatched blocker from this audit remains. Phase 5 is still incomplete.
