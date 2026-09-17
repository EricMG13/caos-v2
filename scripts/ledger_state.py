#!/usr/bin/env python3
"""Read the known-gaps ledger in CLAUDE.md as structured entries.

The ledger is the contract's honest record of accepted limitations, and it rots
in one direction: an entry stays open after the work that closed it has landed,
so a reader is warned about a gap the tree no longer has. `CLAUDE.md` already
says an entry describing a gap the tree has since closed "is the same defect as
a missing one, read the other way round" -- this module is what lets a test say
so mechanically instead of trusting a reviewer to notice.

It parses and judges nothing. `tests/test_ledger.py` holds the rules, because
which entries may be open is repository policy rather than a property of the
text. `--report` prints what this reader sees, which is how a person checks the
parser itself rather than the ledger.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "CLAUDE.md"
HEADING = "## Known gaps (honest ledger)"

# A struck entry opens `- ~~**Title.**~~`; an open one `- **Title.**`. The bold
# run may wrap, so the title is read from the whole entry rather than line one.
_TITLE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_TEST = re.compile(r"\btest_[a-z0-9_]+")
# A commit as this repository writes one: seven or more hex digits in backticks.
_COMMIT = re.compile(r"`([0-9a-f]{7,40})`")
_PHASE = re.compile(r"^\*\*(.+?)\.?\*\*$")
_MOVED = f"the contract has no {HEADING!r} section"


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """One ledger bullet: what it claims, and the evidence it cites."""

    phase: str
    title: str
    struck: bool
    tests: tuple[str, ...]
    commits: tuple[str, ...]
    upgrade: bool
    body: str

    @property
    def open(self) -> bool:
        return not self.struck


def _ledger_text(text: str) -> str:
    """The ledger section alone, or `ValueError` if the heading has moved.

    A reader that silently returned nothing would make every rule above it
    vacuously true, which is the failure mode `scan_floors.py` exists to stop.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(HEADING)]
    if not starts:
        raise ValueError(_MOVED)
    start = starts[0]
    # An H1 ends the section as surely as an H2: the contract carries an
    # appended `# GitNexus` block, which was being read as ledger body.
    after = [
        i
        for i, line in enumerate(lines)
        if i > start and (line.startswith("## ") or line.startswith("# "))
    ]
    end = after[0] if after else len(lines)
    return "\n".join(lines[start:end])


def entries(text: str) -> list[LedgerEntry]:
    """Every top-level bullet of the ledger section, in file order."""
    phase = ""
    collected: list[LedgerEntry] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        body = "\n".join(current).strip()
        found = _TITLE.search(body)
        title = " ".join(found.group(1).split()) if found else body[:80]
        collected.append(
            LedgerEntry(
                phase=phase,
                title=title.rstrip("."),
                struck=current[0].startswith("- ~~"),
                tests=tuple(sorted(frozenset(_TEST.findall(body)))),
                commits=tuple(sorted(frozenset(_COMMIT.findall(body)))),
                upgrade="*Upgrade:*" in body,
                body=body,
            )
        )
        current.clear()

    # A phase heading in this file always follows a blank line. Without that,
    # a wrapped entry line that happens to be exactly a bold phrase splits the
    # entry in two and relabels the phase.
    blank_before = True
    for line in _ledger_text(text).splitlines():
        heading = _PHASE.fullmatch(line.strip())
        was_blank, blank_before = blank_before, not line.strip()
        if heading is not None and was_blank and not line.startswith("- "):
            flush()
            phase = heading.group(1)
            continue
        if line.startswith("- "):
            flush()
            current.append(line)
        elif current:
            current.append(line)
    flush()
    return collected


def read(path: Path = CONTRACT) -> list[LedgerEntry]:
    """The ledger of one contract file."""
    return entries(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument(
        "--report", action="store_true", help="print one line per entry"
    )
    args = parser.parse_args(argv)

    try:
        found = read(args.contract)
    except (OSError, ValueError) as error:
        print(f"ledger unreadable: {error}", file=sys.stderr)
        return 2
    if not found:
        print("read no ledger entries; a scan of nothing is a failure", file=sys.stderr)
        return 2

    if args.report:
        for entry in found:
            state = "closed" if entry.struck else "open  "
            evidence = ",".join(entry.tests or entry.commits) or "-"
            print(f"{state} [{entry.phase}] {entry.title[:72]} :: {evidence[:60]}")
    closed = sum(1 for entry in found if entry.struck)
    print(f"{len(found)} entries, {closed} closed, {len(found) - closed} open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
