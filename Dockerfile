# One image, two commands: the API (this file's default) and the worker
# (`server/engine/worker`; the compose files override CMD). No supervisor and
# no reverse proxy inside the image -- the edge is operator infrastructure
# (`docs/DECISIONS.md` §53, Task 4.5 decision 1) -- and nothing here installs
# LibreOffice, poppler or a font (§14): that is 482 MB across 176 packages, and
# 176 packages of standing CVE triage `pip-audit` does not cover.

# ---- build: compile the static export; this stage never reaches the image ----
# Digest-pinned; a tag alone is not a pin. node:24-slim (Debian bookworm).
FROM node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS build
WORKDIR /app/frontend
# The lock alone first, so a source change does not re-resolve dependencies.
COPY frontend/package.json frontend/package-lock.json ./
# --ignore-scripts: no package's install script runs in a build this repository
# does not review line by line.
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
# Digest-pinned; a tag alone is not a pin. python:3.14-slim.
# Re-pinned for CVE-2026-14456 (openssl, HIGH) -- the answer to a red image
# scan is a re-pin, the same as a red audit is a recompile.
FROM python@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6

# The 3.14-slim digest above still carries twelve fixable HIGH/CRITICAL findings
# across four OS packages as of 2026-09-14. These are the exact fixed trixie
# candidates; --only-upgrade prevents this repair from expanding the image's
# package set.
# Provenance: security-tracker.debian.org/tracker/source-package/{gzip,perl,pcre2,sqlite3}
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade \
        gzip=1.13-1+deb13u1 \
        libpcre2-8-0=10.46-1~deb13u2 \
        libsqlite3-0=3.46.1-7+deb13u2 \
        perl-base=5.40.1-6+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

# Fail the build rather than the first request: a runtime that silently differs
# from the locked one is the thing --require-hashes exists to prevent.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CAOS_SITE_ROOT=/app/site

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
COPY methodology/ ./methodology/
COPY vendor/ ./vendor/
# Only the compiled export -- no Node, no npm, no node_modules and no frontend
# source reach this stage; the build stage above is discarded with it.
COPY --from=build /app/frontend/dist ./site

# Nothing here needs to write to the image or to be root to read it. The blob
# store and the database are outside the container by design. `/blobs` exists
# here only so a fresh, empty named volume mounted over it inherits this
# ownership on its first mount (the documented Docker volume-population
# behaviour) -- an operator's real deployment mounts its own blob root instead.
RUN useradd --system --uid 10001 --no-create-home caos \
    && mkdir -p /blobs \
    && chown -R caos:caos /app /blobs
USER 10001

# The route surface (`docs/DECISIONS.md` §22). One worker: a run tail holds its
# connection for up to five minutes, so how many of those a deployment can
# afford is a question about its database's connection count -- not a default
# worth guessing here. `--no-proxy-headers`: the edge guard reads the real
# socket peer, not a client-forwarded header (finding 8); `--no-server-header`
# names nothing about the process to an unauthenticated caller;
# `--limit-concurrency` bounds unpooled connections (§11).
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server.api.site:application", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--no-proxy-headers", "--no-server-header", "--limit-concurrency", "32"]
