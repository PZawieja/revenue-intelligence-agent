# Revenue Intelligence Agent

An end-to-end, explainable revenue intelligence demo built with dbt, DuckDB, and
lightweight AI-safe query routing. It provides AE-friendly answers for:

- Account overview (ARR/MRR, plan, renewal)
- Health scoring with risk explanations
- Expansion potential scoring

Everything is deterministic, explainable, and governed by an allowlist of
AI-safe assets.

## Project Structure

- `dbt/` - dbt project and models
- `dbt/seeds/` - demo seed data (customers, subscriptions, invoices, usage, tickets)
- `dbt/models/gold/` - fact and dimensional models
- `dbt/models/ai/` - AI-safe views
- `dbt/models/semantic/` - allowlist of AI-safe assets
- `duckdb/` - local DuckDB database file (generated)
- `scripts/` - AI-safe SQL guard, intents, interpreters, and runner

## Requirements

- Python 3.9+
- dbt-core with DuckDB adapter

The repo uses a local virtual environment at `.venv/`.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install dbt-core dbt-duckdb duckdb tabulate
```

## Initialize dbt

The project uses a repo-local profile at `dbt/profiles.yml`.

```bash
cd dbt
../.venv/bin/dbt debug --profiles-dir .
```

## Load Seeds

```bash
cd dbt
../.venv/bin/dbt seed --profiles-dir .
```

## Build Models

```bash
cd dbt
../.venv/bin/dbt build --profiles-dir .
```

## AI-Safe Query Runner

Run the demo queries (overview, health, expansion):

```bash
.venv/bin/python scripts/ai_query_runner.py
```

## How It Works

1. The intent router maps a question to a fixed SQL template.
2. The SQL guard validates:
   - only `select`
   - no `select *`
   - only allowlisted assets
3. The query executes against AI-safe views.
4. The interpreter explains results in AE-friendly language.

## Example Questions

- "Give me overview for Acme GmbH"
- "Is Acme healthy?"
- "What is the expansion potential for Acme?"

## Notes

- DuckDB database file lives at `duckdb/revenue_intel.duckdb`.
- AI-safe assets are defined in `dbt/models/semantic/dim_ai_allowed_assets.sql`.
