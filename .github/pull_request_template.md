## One concern

<!-- Name the invariant or behaviour this PR protects, and nothing else. -->

## The failing test

<!-- Test name and the reason it failed before this change. -->

## Checklist

- [ ] Test first: the named test failed for the right reason before the implementation.
- [ ] One concern; the diff stays under the CI size gate.
- [ ] Any new dependency has a dated `docs/DECISIONS.md` entry.
- [ ] Any accepted limitation has a `CLAUDE.md` known-gaps entry in this PR.
- [ ] `confidence-review` was run after code changes.
- [ ] High-risk changed symbols had a max-reasoning rewrite tournament.
- [ ] `adversarial-reviewer` was run at phase completion, if this PR completes a phase.
- [ ] No document-derived text or credential appears in a log, a test fixture or this description.
