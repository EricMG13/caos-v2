# Gate order matches docs/AI_CODE_QUALITY.md: lint, types, tests, security.
PY  := .venv/bin/python
SEC := .venv-security/bin

.PHONY: venv lock lint types test security check dev

venv:  ## dev toolchain on 3.14, security toolchain on 3.12 (AI_CODE_QUALITY 4)
	uv venv --python 3.14 .venv
	uv pip install --python .venv --require-hashes -r requirements-dev.txt
	uv venv --python 3.12 .venv-security
	uv pip install --python .venv-security --require-hashes -r requirements-security.txt
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

types:
	$(PY) -m mypy scripts tests server

test:
	$(PY) -m pytest
	$(PY) scripts/io_budget.py --assert

security:  # the floor is checked first: a report that parsed nothing must fail
	$(SEC)/bandit -r scripts server -f json -o bandit.json || true
	$(PY) scripts/scan_floors.py bandit.json --no-parse-errors \
		--cover scripts server --unscanned tests
	$(SEC)/bandit -r scripts server
	$(SEC)/pip-audit --require-hashes -r requirements.txt -r requirements-dev.txt \
		-r requirements-security.txt
	gitleaks git --no-banner

check: lint types test security

dev:
	@echo "no application code yet; the API and worker arrive in Phase 1" && exit 1
