.PHONY: venv install run test lint fmt

PY=python3.11
VENV=.venv
PIP=$(VENV)/bin/pip
PYTHON=$(VENV)/bin/python

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

run:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

fmt:
	$(PYTHON) -m ruff format .