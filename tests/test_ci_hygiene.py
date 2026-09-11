"""Build hygiene: facts about the files that build and ship this, asserted here.

A job with no timeout can hold a runner for six hours on a hung step, and two
runs of one branch racing each other report whichever finished last. Both are
facts about the CI file, so both are asserted against that file itself.

The Dockerfile is here for the same reason and was not, which is the gap: it is
the other place this repository installs packages and the only one whose result
ships, and no gate read it. `check_tested.py` reads Python; Trivy answers "are
the installed packages known-vulnerable", never "was this build hashed,
wheels-only, digest-pinned and unprivileged".
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CI_YAML = REPO / ".github" / "workflows" / "ci.yml"
DOCKERFILE = REPO / "Dockerfile"


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


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


def test_the_runtime_image_installs_the_way_ci_does() -> None:
    """The Dockerfile is the other place this repository runs `pip install`,
    and the only one whose result ships.

    The test above reads `ci.yml` and stops there, so the image was outside
    every gate that judges how a dependency arrives: `check_tested.py` reads
    Python, and Trivy answers "are the installed packages known-vulnerable",
    never "was this build hashed and wheels-only". Dropping either flag here
    would be a source distribution executing its own `setup.py` inside the
    artifact that runs in production, and nothing would have said so.
    """
    installs = [
        line.strip()
        for line in _dockerfile().splitlines()
        if "pip install" in line and not line.lstrip().startswith("#")
    ]

    assert installs, "the image installs something; this test found nothing"
    for install in installs:
        assert "--require-hashes" in install, install
        assert "--only-binary :all:" in install, install


def test_the_runtime_image_pins_its_base_and_drops_its_privileges() -> None:
    """Three facts about the shipped artifact, none of them Trivy's job.

    A tag is not a pin, root is not a runtime, and `pip` is a build-time tool
    that carries its own vendored msgpack and setuptools into every image that
    keeps it -- CVEs in a tool this process never calls.
    """
    text = _dockerfile()

    assert re.search(r"^FROM \S+@sha256:[0-9a-f]{64}$", text, re.MULTILINE), (
        "the base image is named by a tag rather than pinned by digest"
    )
    assert re.search(r"^USER (?!root$)\S+$", text, re.MULTILINE), (
        "the image runs as root"
    )
    # `site-packages/pip` and not `site-packages/pip-*.dist-info`: the loose
    # form passed while the package directory itself was left in the image,
    # matching the line beside it. A check that cannot fail is not a check.
    assert re.search(r"site-packages/pip(?![-\w])", text), (
        "pip's package directory is still in the shipped image"
    )
    assert "/usr/local/bin/pip" in text, "pip's executables are still on PATH"
