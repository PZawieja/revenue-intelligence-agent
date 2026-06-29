# Agentic OS — Operating Summary

## Architecture
**Mode**: Harness-wrapper over Claude Code (strong single-agent baseline)
**Runtime**: Python 3.9 FastAPI + DuckDB + anthropic SDK
**Execution engine**: Claude API (claude-sonnet-4-6 default, claude-haiku-4-5 for cheap tasks)
**Task store**: SQLite (WAL mode) at `aos/engine/aos.db`
**Memory**: File-based JSON in `aos/artifacts/memory.jsonl` + `aos/runs/`
**Control plane**: FastAPI routes at `/api/aos/*`
**State protocol**: Files in `aos/` are canonical; DB is operational index

## First Milestone
Prove the full closed loop end-to-end:
1. Accept goal via `POST /api/aos/goals`
2. Decompose into typed tasks via planner (Claude API)
3. Execute each task via executor (Claude API with skill profile)
4. Verify output with structured assertions
5. Record memory entry with what worked / what failed
6. Return evidence to human via `GET /api/aos/goals/{id}`
7. Update `momentum.md` with learnings

Target: any natural-language goal relevant to revenue intelligence produces a verified result with evidence trail.

## Next Three Milestones
- **M2**: Eval harness — 10 scenario tests, pass rate tracked, regression detection
- **M3**: Self-improvement loop — one-change bounded improvement with before/after eval comparison
- **M4**: Proactive monitoring — scheduled scan of project state, auto-generate goals for stale work

## Guardrails
- Max 3 retries per task (retry with variation, not repeat)
- Max delegation depth: 5
- Budget tracked per goal (token count); pause at 50k tokens per goal
- No destructive filesystem actions without `risk_level=high` + explicit approval
- Tasks fail-safe: failed task blocks dependent tasks, escalates to human
- All side effects logged before execution

## Runtime Constraints (current)
- No browser automation (defer to M5)
- No desktop automation (defer to M5)
- No cron scheduling (defer to M4)
- No multi-machine support (single-node, defer)
- No Playwright installed by default (can add)
- Python 3.9: use `Optional[X]` not `X | None`, `from __future__ import annotations`

## Re-read during long runs
This file summarizes the full operating posture. Read it at the start of each new session before acting.
