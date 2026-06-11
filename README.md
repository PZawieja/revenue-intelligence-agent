# Revenue Intelligence Agent

A premium, product-quality analytics application for customer success teams. Dark-themed SPA powered by FastAPI, DuckDB, and dbt — no LLM API key required.

## Architecture

```
seeds (CSV) → dbt medallion layers → DuckDB → FastAPI + vanilla SPA
```

**Data pipeline:**
- `dbt/seeds/` — 50 synthetic European B2B SaaS accounts with health signal variety
- `dbt/models/gold/` — core analytical models (health scoring, expansion potential, renewals)
- `dbt/models/ai/` — AI-safe views enforcing SQL allowlists
- `dbt/models/semantic/` — `dim_ai_allowed_assets` controls which models the chat layer can query

**Application:**
- `core/` — database access, SQL guardrails, intent detection (rapidfuzz), response interpreters
- `api/` — FastAPI routers: `/api/portfolio`, `/api/accounts`, `/api/chat`
- `templates/index.html` — SPA shell
- `static/` — dark design system CSS, JS modules for each view

## Features

**Portfolio** — KPI strip (total ARR, ARR at risk, health distribution, next renewal), health donut chart, ARR-by-band bar chart, renewals timeline, full account risk matrix.

**Accounts** — searchable/filterable table of all 50 accounts, instant drilldown panel with usage sparkline, risk signals, and expansion score.

**Intelligence** — natural language query interface. No LLM API needed: rapidfuzz fuzzy account name matching + keyword intent detection. Evidence accordion shows the exact SQL and guardrail status on every response.

## Setup

```bash
# 1. Create environment and install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Install dbt packages
make deps

# 3. Load seed data and build all models
make seed
make build

# 4. Run
make app
# → http://localhost:8000
```

## Try it

- Open `http://localhost:8000` — Portfolio loads with live charts
- Click **Accounts** → search "cologne" → click row to see usage sparkline and risk signals
- Click **Intelligence** → type "Show renewals at risk" → expand Evidence accordion to see the SQL
- Try: "Is Initech Ltd healthy?" or "Show expansion shortlist"

## Stack

| Layer | Technology |
|-------|-----------|
| Warehouse | DuckDB (embedded, no server) |
| Transformation | dbt-duckdb |
| Backend | FastAPI + Jinja2 |
| NLP | rapidfuzz (no LLM API key needed) |
| Frontend | Vanilla HTML/CSS/JS + Chart.js (CDN) |

## Data

All data is synthetic. 50 accounts modelled on European B2B SaaS with realistic segment distribution (50% SMB / 30% Mid-Market / 20% Enterprise), health signal variety (red/yellow/green), and 10 usage data points per account spanning 5 months.
