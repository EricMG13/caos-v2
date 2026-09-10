# One process, the standard library's calculators, and nothing that renders a
# document. `docs/DECISIONS.md` §14: no workbook build and no publication module,
# so nothing here installs LibreOffice, poppler or a font -- which is 482 MB
# across 176 packages, and 176 packages of standing CVE triage `pip-audit` does
# not cover.
#
# Digest-pinned; a tag alone is not a pin. python:3.14-slim.
FROM python@sha256:cae66f2ef0ec51a9891263eeee7f987dacf0a9879e8aa9353d5606e0530619a5

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
RUN pip install --no-cache-dir --require-hashes --only-binary :all: \
        -r requirements.txt

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
