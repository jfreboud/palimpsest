VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

.PHONY: install test lint format run

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -e ".[dev]" -q
	$(VENV)/bin/pre-commit install

test:
	$(PYTEST) tests/ -v

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

run:
	$(PYTHON) scripts/mcp_server/main.py
