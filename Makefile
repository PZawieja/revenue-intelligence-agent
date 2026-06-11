VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
DBT=$(VENV)/bin/dbt

.PHONY: setup deps seed build app

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

deps:
	$(DBT) deps --project-dir dbt --profiles-dir dbt

seed:
	$(DBT) seed --project-dir dbt --profiles-dir dbt

build:
	$(DBT) build --project-dir dbt --profiles-dir dbt

app:
	$(VENV)/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
