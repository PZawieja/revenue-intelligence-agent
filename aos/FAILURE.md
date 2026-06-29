# Failure Register

## Active Failures

### F001 — No API key for real execution
**Date**: 2026-06-29
**Severity**: High (blocks real AI execution)
**Goal**: `73134054` — Weekly account health briefing
**Error**: `ANTHROPIC_API_KEY not set`
**Classification**: `missing_tool_or_credential`
**Tasks exhausted**: 3 retries (all failed with "No API key")
**Resolution**: Set `ANTHROPIC_API_KEY` in `.env` file
**Status**: OPEN

## Resolved Failures

_None yet._

## Failure Pattern Registry

| Pattern | Count | Classification | Guardrail Added |
|---|---|---|---|
| Missing API key | 1 | missing_tool_or_credential | — |
| Python syntax error (list comprehension condition) | 1 | bad_output_format | — |
| Eval key check too strict (dict key vs string content) | 1 | bad_verification | Fixed in harness.py |
| Module import binding (mock patching) | 1 | execution_error | Fixed to module-level ref |

## Improvement Queue (from failures)

- [ ] Add pre-flight API key check at startup and warn clearly in `/api/aos/health`
- [ ] Add rule-based planner fallback that creates structured tasks even without Claude API
- [ ] Add eval regression detector (compare pass rate vs last run, alert on drop)
