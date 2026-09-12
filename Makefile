# Gate order matches docs/AI_CODE_QUALITY.md: lint, types, tests, security.
PY  := .venv/bin/python
SEC := .venv-security/bin

.PHONY: venv lock lint types test test-provider security check dev

venv:  ## dev toolchain on 3.14, security toolchain on 3.12 (AI_CODE_QUALITY 4)
	uv venv --python 3.14 .venv
	uv pip install --python .venv --require-hashes --only-binary :all: \
		-r requirements-dev.txt
	uv venv --python 3.12 .venv-security
	uv pip install --python .venv-security --require-hashes --only-binary :all: \
		-r requirements-security.txt
	uv tool install pre-commit >/dev/null 2>&1 || true
	pre-commit install

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
	$(PY) -m pytest
	$(PY) scripts/scan_floors.py coverage.xml --cobertura
	$(PY) scripts/io_budget.py --assert

test-provider:  ## the live suite; credentials from the environment or an untracked .env (DECISIONS 16)
	@# Sourced silently: a shell quotes a line it cannot run, and in .env that line can be a key.
	@set -a; if [ -f .env ]; then . ./.env >/dev/null 2>&1; fi; set +a; \
	CAOS_REQUIRE_PROVIDER=1 CAOS_REQUIRE_POSTGRES=1 $(PY) -m pytest --no-cov \
		tests/test_provider.py tests/test_module_execution.py tests/test_live_run.py

security:  # the floor is checked first: a report that parsed nothing must fail
	$(SEC)/bandit -r scripts server -f json -o bandit.json || true
	$(PY) scripts/scan_floors.py bandit.json --no-parse-errors \
		--cover scripts server --unscanned tests
	$(SEC)/bandit -r scripts server
	$(SEC)/pip-audit --require-hashes -r requirements.txt -r requirements-dev.txt \
		-r requirements-security.txt
	gitleaks git --no-banner

check: lint types test security

dev:  ## the route surface. CAOS_DATABASE_URL and CAOS_BLOB_ROOT are read per request
	# No --reload: it needs watchfiles, and a dependency that only the developer
	# loop uses still has to be locked, audited and justified.
	$(PY) -m uvicorn server.api.app:app --port 8000
