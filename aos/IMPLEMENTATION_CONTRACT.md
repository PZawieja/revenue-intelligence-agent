# Implementation Contract

## Mission
Build a durable, observable, self-improving agentic operating system layered on top of the existing Revenue Intelligence Agent. Start with a strong single-agent baseline, prove the full goal→task→execute→verify→memory→learn loop, then expand capability systematically.

## Runtime Profile
- **Host**: macOS Darwin 25.5.0, Python 3.9.6
- **Framework**: FastAPI SPA + DuckDB + dbt-duckdb
- **Agent**: Claude Code (harness-wrapper mode)
- **Execution model**: Synchronous task execution via Claude API; async expansion in M2
- **Deployment**: Local-first, single-node

## First Milestone
Prove end-to-end loop on the revenue intelligence domain:
- Goal intake → task decomposition → execution → verification → memory → evidence → learning
- Success: any revenue intelligence goal (e.g. "identify which accounts need attention this week") produces a structured, verified response with task trace and evidence

## Non-Goals for v1
- Browser/desktop automation
- Multi-machine orchestration
- Cron scheduling
- External webhook triggers
- Scientific experiment harness
- Company-running harness (beyond revenue intelligence)
- Semantic search over memory (defer to M3+)

## Constraints
- Python 3.9 compatibility (Optional[X], from __future__ import annotations)
- No new pip dependencies beyond what's already in requirements.txt except: `pydantic>=2` already available via fastapi
- SQLite for task store (stdlib)
- anthropic SDK for LLM calls (already installed)
- ruff-clean code, no comments, no docstrings

## Safety Posture
- `risk_level` on every task: low (auto-proceed), medium (log + proceed), high (require approval)
- Approval queue at `/api/aos/approvals`
- No destructive filesystem or external actions without explicit `approved=true`
- All tool calls logged before execution
- Budget cap: 50k tokens per goal, 200k per day (tracked in task store)

## Proof-of-Progress Metrics (track from day 1)
- tasks_completed (count)
- tasks_verified (count)
- tasks_failed (count)
- median_task_tokens (int)
- intervention_rate (pct tasks needing human action)
- eval_pass_rate (pct)
- memory_entries (count)

## Verification Strategy
Each task defines a `verification_plan` field. Verifier checks:
1. Output has required fields (schema check)
2. Output is non-empty
3. Output is consistent with task description (LLM judge for non-trivial tasks)
4. No error markers in result
