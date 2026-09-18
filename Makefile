# Gate order matches docs/AI_CODE_QUALITY.md: lint, types, tests, security.
PY  := .venv/bin/python
SEC := .venv-security/bin
IMAGE ?= caos-workbench:local
TRIVY_VERSION := 0.70.0
# The project's own pinned scanner (docs/DECISIONS.md §90); `make trivy`
# installs it, and TRIVY= still overrides.
TRIVY_DIR := .tools/trivy-$(TRIVY_VERSION)
TRIVY ?= $(TRIVY_DIR)/trivy

-include .env
export CAOS_DATABASE_URL CAOS_TEST_POSTGRES_URL CAOS_BLOB_ROOT
export CAOS_TRUST_ROLE_HEADER CAOS_REQUIRE_POSTGRES
export CAOS_DEV_USER CAOS_DEV_ROLE

.PHONY: bootstrap venv lock lint types test test-fast test-provider test-postgres-races \
	check-postgres security image smoke-production frontend-check check-fast check-size \
	check doctor dev dev-up dev-down dev-api dev-worker dev-ui dev-ui-demo index trivy

bootstrap: venv trivy  ## exact locked Python and Node environments, pinned Trivy
	npm --prefix frontend ci --ignore-scripts

trivy: $(TRIVY_DIR)/trivy  ## the image gate's scanner, pinned by archive digest

$(TRIVY_DIR)/trivy:
	scripts/install_trivy.sh $(TRIVY_VERSION) $(TRIVY_DIR)

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
	env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL \
		-u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT \
		-u CAOS_REQUIRE_PROVIDER CAOS_REQUIRE_POSTGRES=1 \
		$(PY) -m pytest -n auto -m "not production_image"
	$(PY) scripts/scan_floors.py coverage.xml --cobertura
	$(PY) scripts/io_budget.py --assert

test-fast:  ## partial: provider, PostgreSQL and image suites are skipped
	env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL \
		-u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT \
		-u CAOS_REQUIRE_PROVIDER -u CAOS_TEST_POSTGRES_URL CAOS_REQUIRE_POSTGRES=0 \
		$(PY) -m pytest --no-cov -m "not production_image"

check-postgres:  ## fail before complete gates when the configured test DB is absent
	@$(PY) scripts/check_postgres.py

test-postgres-races:
	env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL \
		-u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT \
		-u CAOS_REQUIRE_PROVIDER CAOS_REQUIRE_POSTGRES=1 \
		$(PY) -m pytest --no-cov tests/test_postgres_races.py

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

image:  ## build and run the exact CI Trivy floor and severity gate
	@command -v "$(TRIVY)" >/dev/null || { echo "Trivy is required; run make trivy, or set TRIVY=/path/to/trivy" >&2; exit 1; }
	@test "$$("$(TRIVY)" --version | sed -n 's/^Version: //p')" = "$(TRIVY_VERSION)" || { echo "Trivy $(TRIVY_VERSION) is required" >&2; exit 1; }
	docker build -t "$(IMAGE)" .
	"$(TRIVY)" image --format json --output trivy.json --severity HIGH,CRITICAL --ignore-unfixed --exit-code 0 "$(IMAGE)"
	$(PY) scripts/scan_floors.py trivy.json --trivy
	"$(TRIVY)" image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "$(IMAGE)"

smoke-production:  ## disposable production-image stack, then the real-browser journey
	docker build -t "$(IMAGE)" .
	env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL \
		-u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT \
		-u CAOS_REQUIRE_PROVIDER CAOS_REQUIRE_IMAGE=1 IMAGE="$(IMAGE)" \
		$(PY) -m pytest --no-cov -m production_image tests/test_production_image.py
	env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u OPENROUTER_BASE_URL \
		-u OPENROUTER_PROVIDER -u OPENROUTER_REASONING_EFFORT \
		-u CAOS_REQUIRE_PROVIDER IMAGE="$(IMAGE)" $(PY) tests/journey/run.py

frontend-check:
	npm --prefix frontend run lint
	npm --prefix frontend run typecheck
	npm --prefix frontend test
	npm --prefix frontend run build
	@for s in directory upload analysis book run model report committee admin; do \
		test -f "frontend/dist/$$s/index.html" || { echo "missing frontend/dist/$$s/index.html"; exit 1; }; \
	done
	npm --prefix frontend run build:demo
	env -u BASE -u ROUTES -u ENGINES -u VIEWPORTS -u A11Y_RESULT_FILE \
		npm --prefix frontend run a11y
	npm --prefix frontend run test:workbench

check-fast: lint types test-fast  ## partial offline gate; excludes DB, browser, security and image

check-size:
	@$(PY) scripts/check_pr_size.py "$(PR_BASE)"

# Recursive invocations keep this order even when the caller uses make -j.
check:
	@$(MAKE) --no-print-directory check-postgres
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory types
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory test-postgres-races
	@$(MAKE) --no-print-directory security
	@$(MAKE) --no-print-directory frontend-check
	@$(MAKE) --no-print-directory image
	@$(MAKE) --no-print-directory smoke-production

doctor:  ## versions and configuration presence; values are never printed
	@$(PY) scripts/dev_doctor.py

dev-up:  ## persistent dev DB/blob root plus an isolated ephemeral test-admin DB
	mkdir -p .dev-data/blobs
	docker compose up -d --wait dev-postgres test-postgres

dev-down:  ## stop only this project's services; preserve dev DB and blobs
	docker compose down

dev-api:  ## the guarded route surface. CAOS_DATABASE_URL and CAOS_BLOB_ROOT are read per request
	# No --reload: it needs watchfiles, and a dependency that only the developer
	# loop uses still has to be locked, audited and justified. --no-proxy-headers:
	# the edge guard's loopback check reads the real socket peer (finding 8).
	$(PY) -m uvicorn server.api.site:application --host 127.0.0.1 --port 8000 \
		--no-proxy-headers

dev-worker:  ## the one polling worker; needs the store, blob root, provider and CAOS_MODEL_PRICE
	$(PY) -m server.engine.worker

dev: dev-api  ## retained API alias

dev-ui:
	npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort

dev-ui-demo:  ## explicit read-only fixture workbench
	npm --prefix frontend run dev:demo -- --host 127.0.0.1 --port 5173 --strictPort

index:  ## installed GitNexus only; never downloads or publishes
	@if command -v gitnexus >/dev/null 2>&1; then \
		gitnexus analyze --index-only; \
	else \
		echo "gitnexus is required; install it before indexing" >&2; exit 1; \
	fi
