## One concern

<!-- Name the invariant or behaviour this PR protects, and nothing else. -->

## The failing test

<!-- Test name and the reason it failed before this change. -->

## Checklist

- [ ] Test first: the named test failed for the right reason before the implementation.
- [ ] One concern; the final committed diff against the actual PR base passes
      the 800-counted-line gate, including review remediation.
- [ ] Ordinary exact-range task review and its remediation are recorded.
- [ ] Any new dependency has a dated `docs/DECISIONS.md` entry.
- [ ] Any accepted limitation has a `CLAUDE.md` known-gaps entry in this PR.
- [ ] If this PR closes a phase: one `confidence-review` reviewed the whole
      phase diff and affected callers at actual `xhigh` reasoning, after normal
      checks and ordinary task reviews.
- [ ] If this PR closes a phase: a separate `adversarial-reviewer` audit ran
      after confidence-review remediation, at actual `xhigh` reasoning.
- [ ] No document-derived text or credential appears in a log, a test fixture or this description.
