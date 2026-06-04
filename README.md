# Revenue Intelligence Agent

> A governance-first AI demo for Customer Success teams — built on warehouse signals, not gut feeling.

[![dbt](https://img.shields.io/badge/dbt-FF694B?style=flat&logo=dbt&logoColor=white)](#)
[![DuckDB](https://img.shields.io/badge/DuckDB-FDD023?style=flat&logo=duckdb&logoColor=black)](#)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](#)

---

## The problem this solves

Most AI demos aimed at revenue teams share a common flaw: they let an LLM query raw CRM tables without guardrails, then present the output as truth. The result is confident, fast, and frequently wrong.

This project takes the opposite approach. The AI layer is narrow and governed. It can only query a curated set of pre-validated analytics assets. Every query is validated before execution. Every result comes with a business-language explanation, not just a number.

The architecture mirrors how I'd build this in production at a B2B SaaS company: warehouse as source of truth, dbt models as the contract layer, and AI as a read-only signal amplifier — never a data mutator.

---

## Architecture

```
Seed data (customers · subscriptions · invoices · usage · tickets)
    ↓
dbt gold layer
    ├── dim_customers          — account master with lifecycle stage
    ├── fct_mrr                — subscription revenue at monthly grain
    ├── fct_health_scores      — XGBoost-style health signal (deterministic)
    └── fct_expansion_signals  — usage + billing expansion indicators
    ↓
dim_ai_allowed_assets          — semantic contract (allowlist)
    ↓
SQL guardrail                  — validates intent, table refs, query shape
    ↓
AI query runner                — intent → template → validated SQL → result → explanation
    ↓
Streamlit UI                   — AE-facing interface
```

**Key design decisions:**
- `select *` is blocked at the guardrail layer
- Only `SELECT` statements are permitted — no mutations
- Every asset in the allowlist has a defined grain and business description
- Health scoring is deterministic and explainable (no black-box LLM scoring)

---

## Supported queries

| Intent | Example |
|---|---|
| Account overview | *"Give me an overview for Acme GmbH"* |
| Health assessment | *"Is Acme healthy?"* |
| Expansion potential | *"What's the expansion potential for Acme?"* |

The intent router maps natural-language questions to parameterised SQL templates — not free-form LLM SQL generation. This is intentional. Parameterised templates are auditable, testable, and safe.

---

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

cd dbt
../.venv/bin/dbt deps --profiles-dir .
../.venv/bin/dbt seed --profiles-dir .
../.venv/bin/dbt build --profiles-dir .
cd ..

.venv/bin/python scripts/ai_query_runner.py
```

Optional Streamlit UI:

```bash
.venv/bin/streamlit run app.py
```

---

## Project structure

```
revenue-intelligence-agent/
├── dbt/
│   ├── seeds/              # Demo data: customers, subscriptions, invoices, usage, tickets
│   ├── models/
│   │   ├── gold/           # Fact and dimensional models (the analytics contract)
│   │   ├── ai/             # AI-safe views (read-only, stripped PII)
│   │   └── semantic/       # dim_ai_allowed_assets — the allowlist
│   └── profiles.yml
├── scripts/
│   ├── ai_sql_guard.py     # Table extraction + allowlist validation
│   ├── ai_intents.py       # Intent → SQL template mapping
│   ├── ai_interpreter.py   # Result → business-language explanation
│   └── ai_query_runner.py  # Orchestrator
├── .streamlit/
├── app.py                  # Streamlit UI entry point
└── README.md
```

---

## Why this architecture matters

The pattern here — **allowlist → guardrail → governed query → explainable result** — is the same pattern I've used for ML model outputs at production scale. A customer health score is only useful if a CS manager trusts it. Trust comes from explainability and auditability, not from accuracy alone.

This project is a concrete demo of that principle applied to an AI-assisted workflow.

---

## Related work

This project is part of a larger GTM analytics engineering portfolio:

- [Experimentation Analytics Platform](https://github.com/PZawieja/experimentation-analytics-platform) — A/B testing pipeline with statistical guardrails
- [Air Traffic Pulse](https://github.com/PZawieja/air-traffic-pulse) — Anomaly detection on live data streams
- [Event Analytics Platform](https://github.com/PZawieja/event-analytics-platform) — Behavioural event pipeline
