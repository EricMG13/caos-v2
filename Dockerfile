# One process, the standard library's calculators, and nothing that renders a
# document. `docs/DECISIONS.md` §14: no workbook build and no publication module,
# so nothing here installs LibreOffice, poppler or a font -- which is 482 MB
# across 176 packages, and 176 packages of standing CVE triage `pip-audit` does
# not cover.
#
# Digest-pinned; a tag alone is not a pin. python:3.14-slim.
# Re-pinned for CVE-2026-14456 (openssl, HIGH) -- the answer to a red image
# scan is a re-pin, the same as a red audit is a recompile.
FROM python@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6

# Fail the build rather than the first request: a runtime that silently differs
# from the locked one is the thing --require-hashes exists to prevent.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# The lock alone first, so a code change does not re-resolve dependencies.
COPY requirements.txt ./
# --require-hashes pins which bytes arrive; --only-binary :all: stops those bytes
# being a source distribution whose setup.py runs at install time
# (SonarCloud githubactions:S8541, fixed the same way in CI).
#
# pip is removed once installation is done. It is a build-time tool with
# nothing to do at runtime, and it carries its own vendored copies of msgpack
# and setuptools -- CVEs in those land on this image whenever pip's bundle is
# behind, for a tool this process never calls. `ensurepip`'s bundled wheel is
# the same pip a second time and goes with it.
RUN pip install --no-cache-dir --require-hashes --only-binary :all: \
        -r requirements.txt \
    && rm -rf /usr/local/lib/python3.14/site-packages/pip \
              /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
              /usr/local/lib/python3.14/ensurepip \
              /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.14

COPY server/ ./server/
COPY vendor/ ./vendor/

# Nothing here needs to write to the image or to be root to read it. The blob
# store and the database are outside the container by design.
RUN useradd --system --uid 10001 --no-create-home caos \
    && chown -R caos:caos /app
USER 10001

# There is no process to serve yet: the first HTTP route is a known gap, and an
# image whose entrypoint pretended otherwise would fail at deploy rather than
# here. What this image is for today is being scanned -- it carries the runtime
# dependencies, which is where the vulnerabilities live.
CMD ["python", "-c", "raise SystemExit('no HTTP route yet: see CLAUDE.md known gaps, Phase 6')"]
