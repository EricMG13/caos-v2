# Gate order matches docs/AI_CODE_QUALITY.md: lint, types, tests, security.
PY  := .venv/bin/python
SEC := .venv-security/bin

-include .env
export CAOS_DATABASE_URL CAOS_TEST_POSTGRES_URL CAOS_BLOB_ROOT
export CAOS_TRUST_ROLE_HEADER CAOS_REQUIRE_POSTGRES

.PHONY: bootstrap venv lock lint types test test-provider security check doctor \
	dev dev-up dev-down dev-api dev-ui index

bootstrap: venv  ## exact locked Python and Node development environments
	npm --prefix frontend ci --ignore-scripts

venv:  ## dev toolchain on 3.14, security toolchain on 3.12 (AI_CODE_QUALITY 4)
	uv venv --python 3.14 .venv
	uv pip install --python .venv --require-hashes --only-binary :all: \
		-r requirements-dev.txt
	uv venv --python 3.12 .venv-security
	uv pip install --python .venv-security --require-hashes --only-binary :all: \
		-r requirements-security.txt
	.venv/bin/pre-commit install

lock:  ## recompile every lock with hashes; the answer to a red audit is a recompile
	uv pip compile --generate-hashes --python-version 3.14 -o requirements.txt requirements.in
	uv pip compile --generate-hashes --python-version 3.14 -o requirements-dev.txt requirements-dev.in
	uv pip compile --generate-hashes --python-version 3.12 -o requirements-security.txt requirements-security.in

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(PY) scripts/check_vocabulary.py
	$(PY) scripts/check_tested.py
	node frontend/scripts/check-vocabulary.mjs

types:
	$(PY) -m mypy scripts tests server

test:  # writes coverage.xml (pyproject.toml addopts); CI reads it in the sonarqube job
	$(PY) -m pytest -n auto
	$(PY) scripts/scan_floors.py coverage.xml --cobertura
	$(PY) scripts/io_budget.py --assert

test-provider:  ## the live suite; configuration comes only from the caller's environment
	CAOS_REQUIRE_PROVIDER=1 CAOS_REQUIRE_POSTGRES=1 $(PY) -m pytest --no-cov \
		--live-provider -m live_provider

security:  # the floor is checked first: a report that parsed nothing must fail
	$(SEC)/bandit -r scripts server -f json -o bandit.json || true
	$(PY) scripts/scan_floors.py bandit.json --no-parse-errors \
		--cover scripts server --unscanned tests
	$(SEC)/bandit -r scripts server
	$(SEC)/pip-audit --require-hashes -r requirements.txt -r requirements-dev.txt \
		-r requirements-security.txt
	gitleaks git --no-banner

check: lint types test security

doctor:  ## versions and configuration presence; values are never printed
	@python3 scripts/dev_doctor.py

dev-up:  ## persistent dev DB/blob root plus an isolated ephemeral test-admin DB
	mkdir -p .dev-data/blobs
	docker compose up -d --wait dev-postgres test-postgres

dev-down:  ## stop only this project's services; preserve dev DB and blobs
	docker compose down

dev-api:  ## the route surface. CAOS_DATABASE_URL and CAOS_BLOB_ROOT are read per request
	# No --reload: it needs watchfiles, and a dependency that only the developer
	# loop uses still has to be locked, audited and justified.
	$(PY) -m uvicorn server.api.app:app --host 127.0.0.1 --port 8000

dev: dev-api  ## retained API alias

dev-ui:
	npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort

index:  ## installed GitNexus only; never downloads or publishes
	@if command -v gitnexus >/dev/null 2>&1; then \
		gitnexus analyze --index-only; \
	else \
		echo "gitnexus is required; install it before indexing" >&2; exit 1; \
	fi
