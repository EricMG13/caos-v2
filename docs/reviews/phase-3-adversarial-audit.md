# CAOS Repair Phase 3 — whole-phase adversarial audit

- **Model:** Claude Opus 5 (`claude-opus-5`).
- **Effort:** `xhigh`. The session record read `effort: "xhigh"` at
  2026-09-14T06:05:49Z, before this audit began.
- **Target:** `codex/execute-repair-plan`, range `e2f2f9a..147ecf7`. That is
  Phase 3 through the confidence-review remediation, run after the wave gate
  passed on `147ecf7` (2,286 backend tests passed; the race tests passed).
- **Method:** `~/.claude/skills/adversarial-reviewer/SKILL.md`, using three
  personas: Saboteur, New Hire and Security Auditor. Every finding was checked
  against the source, and the resource findings were reproduced with the probes
  below.

## Verdict: CONCERNS

There is one P1, promoted because two personas raised it, and three P3s. There
is no P0.

## Findings

### P1: a small PDF defeats the extraction limits (Saboteur and Security Auditor)

`server/evidence/pdf.py:128-151` checks the deadline and the page limit only
between pages. `pdfminer.pdftypes.PDFStream.decode` inflates a `FlateDecode`
stream with an unbounded `zlib.decompress`, and `decompress_corrupted` builds
its output one byte at a time. Nothing bounds a document's memory, and no check
runs while a page is being laid out.

The probes called `PdfExtractor.extract`, the same call `admit_pack` makes:

| Document | Inflated to | Deadline | Outcome |
|---|---|---|---|
| 16,926 B, one page of `1 w ` operators | 16 MiB | 2.0 s | `SOURCE_EXTRACTION_TIMEOUT` after **23.2 s** |
| 65,843 B, one page of spaces | 64 MiB | 2.0 s | admitted, peak RSS **229 MiB** |
| 261,529 B, one page of spaces | 256 MiB | 2.0 s | admitted, peak RSS **806 MiB** |

The inflate ratio is about 1,000:1, and memory grows with the inflated size. A
20 MiB document, which is within `max_document_bytes`, therefore inflates to
about 20 GiB and exhausts the extracting process. Parsing that many operators
on one page takes hours.

REPAIR_PLAN Phase 3 exit check 1 requires that "oversized inputs produce
specific safe outcomes". The deadline ledger entry named its own upgrade
trigger: "the day a single page is shown to overrun it by more than the ceiling
can absorb". The probe above meets that trigger.

*Smallest root fix:* extract each PDF in a child process. The parent kills the
child at the admission deadline, which bounds every expansion and parsing
cost. Inside the child only, pdfminer's inflater gets a per-document decoded
byte budget, so a Flate bomb refuses `SOURCE_TOO_LARGE` before its bytes are
held. §44.2's decision against process isolation is superseded by a dated
decision.

### P3: plain-text tokens are counted once per line (Saboteur)

`server/evidence/extract.py:207` extends the token list with a whole line
before comparing it with `max_tokens`. A 4 MiB single line of `a ` built about
2 million tokens before refusing, taking 4.3 s and 633 MiB of peak memory. A
20 MiB line would build about 10 million tokens, roughly 3 GB. This is bounded
by the document byte limit, but it is still work past the limit.

*Fix:* build a line's tokens lazily and stop at the limit.

### P3: extraction runs inside the caller's open transaction (Saboteur)

`admit_pack` reads the case (`_require_case`) before extracting every
document. A pack of 50 documents at 60 s each can hold a transaction idle for
up to 50 minutes before `lock_case`.

*Fix:* not in Phase 3. Recorded in the ledger, and owned by Phase 4, which
moves upload and extraction to the worker.

### P3: two gates, one of them implicit (New Hire)

The confidence review split the gate: `ADAPTER_ROUTES` is enforced only by
`require_adapter_route`, while `host_identity`, `validate_markdown` and
`build_handoff_prompt` check `ADAPTER_MODULES` alone. A Phase 5 author who
extends one set and misses the other gets either a module that executes on an
unproven pathway or a proven pathway that refuses late. Some names are also
stale or misleading:

- `server/methodology/canonical.py`'s module docstring still describes "the
  claims executor's unit structure", after that executor was deleted.
- `executor.py` now only holds canonical helpers, yet `_delivered` and
  `_stored_identity` are imported across modules under private names.

*Fix:* a comment beside both constants naming the one enforcement point, and
the stale docstring corrected. No rename: that would be churn outside the
finding.

## Checked and fine

- Vendor loader: it compiles verified bytes into private modules. `sys` is a
  shim, and the private names occupy `sys.modules` only while a load runs.
- Root-file resolution: names come from the verified `SKILL.md` and must be
  listed in the manifest's `root_file_hashes`. Reads are bounded to the
  manifest size plus one byte.
- Acceptance requires a record for a canonical pin. Replay compares the record
  digest.
- The deliverable payload re-derives identity, lineage, projections and every
  rectangle under `verify=True`. The render escapes all model text.
- Migrations 0011/0012: the subject CHECK constraints match
  `_subject_valid`'s shape rules. The attempt ordinal is unique per node.

## Remediation

- **P1:** `PdfExtractor.extract` now runs `walk_pages` in a child interpreter,
  started with `python -I -c` and an empty environment, and the parent kills it
  at the deadline. Inside the child, a budgeted inflater stands in for
  pdfminer's `zlib`, so inflation stops at `max_decoded_bytes`. §47 supersedes
  §44.2.
  - A first attempt used `multiprocessing` with `spawn`. It was rejected when
    the timing probe showed the child re-running the caller's `__main__`.
  - The same probes after the change:
    - The 16 MiB operator page refused `SOURCE_EXTRACTION_TIMEOUT` at 2.0 s.
    - A 1 GiB inflate refused `SOURCE_TOO_LARGE` in 0.2 s.
    - The 4 MiB text line refused in 0.7 s at 124 MiB peak memory.
  - Each child costs 0.124 s to start on the development machine.
- **P3, plain text:** a line's tokens are built lazily and stop one past
  `max_tokens`.
- **P3, transaction:** recorded in the CLAUDE.md ledger entry that replaces the
  cooperative-deadline entry.
- **P3, New Hire:** the enforcement point is named beside both gate sets, and
  `canonical.py`'s stale module docstring is corrected.
- **Tests:**
  - `test_one_page_cannot_outrun_the_deadline`
  - `test_a_stream_that_inflates_past_the_ceiling_refuses[intact|corrupt checksum]`
  - `test_an_ordinary_flate_page_still_extracts_in_the_child`
  - `test_one_line_past_the_token_ceiling_stops_building_tokens`

  The page-ceiling spy now targets `walk_pages` in-process.
