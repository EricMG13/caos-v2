"""The argument-count suppressions are a budget, and a budget only falls (W11).

`# noqa: PLR0913` is the one lint suppression this tree hands out for width,
and each is a function whose parameter list nobody has yet found the type
for. Counting them pins the total so a change can spend none: the number
below is measured, not aspired to, and the only edit it admits is downward.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKER = "noqa: PLR0913"


def test_argument_count_suppressions_only_fall() -> None:
    """52 measured on 2026-09-17 (Task 12, `sdd/t12`). Lower this number when
    you remove one; never raise it. The repo's ceiling is ruff's default of
    five, so a six-parameter reader still carries one -- narrowing a signature
    is not the same as clearing it, and this count says which happened."""
    files = [
        *(REPO / "server").rglob("*.py"),
        *(REPO / "scripts").rglob("*.py"),
    ]
    # A scanner that scanned nothing is a failure, not a pass.
    assert len(files) > 100, len(files)
    hits = sum(path.read_text(encoding="utf-8").count(MARKER) for path in files)
    assert hits <= 52, hits
