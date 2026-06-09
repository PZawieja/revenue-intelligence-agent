VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
DBT=$(VENV)/bin/dbt

.PHONY: setup deps seed build app dashboard

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

deps:
	DBT_PROFILES_DIR=dbt $(DBT) deps --profiles-dir dbt

seed:
	DBT_PROFILES_DIR=dbt $(DBT) seed --profiles-dir dbt

build:
	DBT_PROFILES_DIR=dbt $(DBT) build --profiles-dir dbt

app:
	$(VENV)/bin/streamlit run app.py

dashboard:
	$(VENV)/bin/streamlit run dashboard.py
