# AOS Momentum — Live State
_Last updated: 2026-06-29_

## NOW
M1 milestone is COMPLETE. Building eval harness (done). Moving to M2.

## NEXT
1. **M2: Real LLM loop** — requires `ANTHROPIC_API_KEY` in `.env`. Once set, run `POST /api/aos/run` for full AI execution.
2. **M2: Eval baseline** — run `POST /api/aos/evals/run?mock=false` with API key to establish real token costs and pass rates.
3. **M2: Regression detection** — add comparison logic to eval harness to detect regressions vs previous run.
4. **M3: Self-improvement loop** — bounded prompt improvement: choose one skill profile, modify, eval before/after, keep if better.

## BLOCKED
- Real LLM execution blocked on `ANTHROPIC_API_KEY` not set in `.env`.
- Browser automation blocked on Playwright not installed (defer M5).

## IMPROVE
From M1 run:
- The planner fallback (single task) is correct but weak — should always attempt decomposition even without API key using a rule-based approach.
- Eval harness correctly caught 0% pass rate before fixing output key check — good feedback loop.
- Memory is recording correctly: 27 entries from M1 test runs.
- Token tracking works (9,960 tokens from mock runs, 0 from real runs since no API key).

## RECURRING
- `GET /api/aos/momentum` — check this at start of every session
- `POST /api/aos/evals/run?mock=true` — run before and after any prompt/skill changes
- `GET /api/aos/metrics` — weekly cost and reliability check

## CURRENT METRICS
```
goals_total: 18
goals_complete: 13 (72% completion rate)
tasks_total: 27
tasks_complete: 24 (89% completion rate)  
tasks_failed: 1 (credential failure — expected)
tokens_total: 9,960 (mock runs only)
memory_entries: 27
eval_pass_rate: 1.0 (5/5 cases, mock mode)
```
