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

# The route surface (`docs/DECISIONS.md` §22). One worker: a run tail holds its
# connection for up to five minutes, so how many of those a deployment can
# afford is a question about its database's connection count -- not a default
# worth guessing here.
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server.api.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
