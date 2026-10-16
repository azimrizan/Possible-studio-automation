.PHONY: install test lint format up down clean dev-api dev-gateway dev-hello dev-web test-e2e

PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ./packages/mcp-common -e ./packages/model-gateway -r requirements-dev.txt

test:
	$(PYTEST) tests/ -v

test-e2e:
	$(PYTEST) tests/e2e/test_phase0_e2e.py -v

lint:
	$(PYTHON) -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true

up:
	docker compose up -d

down:
	docker compose down

dev-api:
	$(PYTHON) -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir apps/api --reload-dir apps/agent-runtime

dev-gateway:
	$(PYTHON) -m uvicorn apps.mcp_gateway.gateway.server:app --host 0.0.0.0 --port 8100 --reload

dev-hello:
	$(PYTHON) -m uvicorn mcp_servers.mcp_hello.server:app --host 0.0.0.0 --port 8101 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache platform_data.db
