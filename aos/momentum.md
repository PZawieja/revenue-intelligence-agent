# AOS Momentum — Live State
_Last updated: 2026-06-30_

## NOW
M2 eval harness in progress. 10-case suite built, regression detection wired, cost_per_task tracking live.
Re-running 5 cases that failed due to executor max_tokens=1000 cap (fixed to 2500). Confirming pass rate.

## NEXT
1. **M2 final** — establish official 10-case baseline (`POST /api/aos/evals/baseline`) once 9+/10 passing
2. **M2 commit** — commit all M2 artifacts + baseline + executor fix
3. **M3: Self-improvement loop** — bounded prompt improvement: choose one skill profile, modify, eval before/after, keep if better
4. **Adaptive token budget** — planner should signal task complexity so executor picks 1000 vs 2500 token budget

## BLOCKED
- Browser automation blocked on Playwright not installed (defer M5)

## IMPROVE
From M2 run:
- Executor max_tokens=1000 too low for multi-item tasks (5 accounts, 5 QBR sections) — fixed to 2500; adds ~3K tokens/task but passes verifier
- LLM judge correctly diagnosed truncation even at 2000-char output preview — calibrated well
- The 5 new eval cases (ri_006–ri_010) provide diverse coverage: churn scoring, usage anomalies, QBR prep, monthly health, CSM onboarding
- `fast=true` mode (3 cases, ~18s mock / ~4min real) is the right cadence for pre-commit checks
- Regression detection unit-tested: correctly classified regressions, improvements, and stable-fail states

## RECURRING
- `GET /api/aos/momentum` — check this at start of every session
- `POST /api/aos/evals/run?mock=true&fast=true` — quick sanity check before any prompt/skill changes
- `POST /api/aos/evals/run?mock=false&fast=false` — full real suite after any significant change
- `GET /api/aos/evals/history` — weekly trend view
- `GET /api/aos/metrics` — weekly cost and reliability check

## CURRENT METRICS
```
goals_total: 53+
goals_complete: 35+ (66%+ completion rate, lower since M2 evals added failing cases)
tasks_total: 100+
tasks_complete: 80+ (~80% completion rate)
tokens_total: 77,701+ (real LLM from M2 eval runs)
memory_entries: 68+
eval_suite: 10 cases (ri_001–ri_010)
eval_pass_rate: ~0.5 (pre-fix), confirming fix now → target 9+/10
avg_tokens_per_goal: ~6,128 (M2 run, higher than M1 due to max_tokens fix)
avg_cost_per_task: ~1,892 tokens/task
```

## EVAL ENDPOINTS (M2)
```
GET  /api/aos/evals/history          — list all past runs
GET  /api/aos/evals/baseline         — view current baseline
POST /api/aos/evals/baseline         — promote latest run to baseline
POST /api/aos/evals/run?mock=false   — full real run (10 cases, ~21 min)
POST /api/aos/evals/run?mock=false&fast=true  — 3-case quick check (~4 min)
```
