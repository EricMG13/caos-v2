"""CI hygiene: every job bounds its own runtime, and superseded runs are cancelled.

A job with no timeout can hold a runner for six hours on a hung step, and two
runs of one branch racing each other report whichever finished last. Both are
facts about the CI file, so both are asserted against that file itself.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CI_YAML = REPO / ".github" / "workflows" / "ci.yml"


def _jobs(text: str) -> dict[str, str]:
    """Job name -> job body, split on the two-space-indented keys under `jobs:`."""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"\n  ([a-z][a-z0-9_-]*):\n", "\n" + body)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def test_every_job_declares_a_timeout() -> None:
    jobs = _jobs(CI_YAML.read_text(encoding="utf-8"))
    assert jobs, "no jobs parsed; the workflow layout changed under this test"
    missing = [name for name, body in jobs.items() if "timeout-minutes:" not in body]
    assert not missing, f"jobs without timeout-minutes: {missing}"


def test_ci_cancels_superseded_runs() -> None:
    text = CI_YAML.read_text(encoding="utf-8")
    assert "cancel-in-progress: true" in text


def test_every_install_is_wheels_only() -> None:
    """--require-hashes pins which bytes arrive. It does not stop those bytes
    being a source distribution, and a source distribution's setup.py runs at
    install time -- so a pinned dependency would still be something CI executes
    rather than merely installs. `--only-binary :all:` is what closes that, and
    this is what stops the next job being added without it."""
    installs = [
        line.strip()
        for line in CI_YAML.read_text(encoding="utf-8").splitlines()
        if "pip install" in line and "--require-hashes" in line
    ]

    assert installs, "CI installs something; this test found nothing"
    for install in installs:
        assert "--only-binary :all:" in install, install
