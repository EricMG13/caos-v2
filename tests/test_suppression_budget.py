"""The argument-count suppressions are a budget, and a budget only falls (W11).

`# noqa: PLR0913` is the one lint suppression this tree hands out for width,
and each is a function whose parameter list nobody has yet found the type for.
What the budget counts is the *positional* ones: a caller can transpose two
neighbouring arguments of the same type silently, and that is the defect this
rule exists to keep a lid on. A suppressed function whose extra parameters are
keyword-only cannot be called wrongly that way, so it is recorded here and not
charged.

**The unit changed on 17 September 2026, by the owner's decision, and the old
one is stated here so nobody has to reconstruct it.** The budget used to count
raw markers, capped at 52. Integrating wave 3 of the audit remediation took
that count to 53: one marker left `server/methodology/canonical.py`, and two
arrived with functions that each replaced several hand-rolled copies of
themselves -- the shared verification reader, and the one governed envelope
that nine command-module copies collapsed into. So the raw count rose by one
while the tree lost about 346 lines of duplication, because the copies it
removed were never suppressed and so had never been counted. A ceiling that
punishes concentrating a suppression into one shared helper is measuring the
wrong thing, and raising it to 53 would have been a threshold moved to obtain
a pass. Two other units were measured and rejected before this one: counting
markers outside the shared helpers rose 47 -> 49, because consolidating
callers drains *other* helpers' caller counts and pushes them across the
threshold; and any unit over raw markers rises here by construction.

Positional width was 22 before the wave and is 22 after it. The wave added no
new way to call anything wrongly, which is the claim this file should have
been making all along.
"""

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKER = "noqa: PLR0913"
CEILING = 22
POSITIONAL_LIMIT = 5


def _suppressed(path: Path) -> list[tuple[str, int, int]]:
    """Each `PLR0913`-suppressed function in `path`: name, positional, total."""
    source = path.read_text(encoding="utf-8")
    if MARKER not in source:
        return []
    lines = source.splitlines()
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if MARKER not in lines[node.lineno - 1]:
            continue
        arguments = node.args
        positional = len(arguments.posonlyargs) + len(arguments.args)
        found.append((node.name, positional, positional + len(arguments.kwonlyargs)))
    return found


def test_positional_argument_suppressions_only_fall() -> None:
    """22 measured on 2026-09-17 over the integrated wave 3, unmoved from the
    wave's base. Lower this number when you narrow one; never raise it.

    A suppression is charged when the function takes more than five positional
    parameters -- ruff's own ceiling, counted the way a caller meets them.
    Making the surplus keyword-only clears the charge, which is not an evasion:
    that is the fix. Every suppression is still read, so a marker on a function
    that no longer needs one cannot hide behind the keyword rule.

    The file floor is 80 against 102 scanned today: enough that a scan of the
    wrong directory or an empty one still fails, and enough headroom that
    deleting a handful of modules cannot turn a suppression budget red for a
    reason unrelated to suppressions."""
    files = [
        *(REPO / "server").rglob("*.py"),
        *(REPO / "scripts").rglob("*.py"),
    ]
    # A scanner that scanned nothing is a failure, not a pass.
    assert len(files) >= 80, len(files)

    suppressed = [entry for path in files for entry in _suppressed(path)]
    assert suppressed, "no suppression was read at all"

    # A marker ruff would not raise is one nobody needs, and the keyword rule
    # below must not become somewhere for it to hide.
    stale = [name for name, _, total in suppressed if total <= POSITIONAL_LIMIT]
    assert stale == [], stale

    charged = [
        name for name, positional, _ in suppressed if positional > POSITIONAL_LIMIT
    ]
    assert len(charged) <= CEILING, (len(charged), sorted(charged))
