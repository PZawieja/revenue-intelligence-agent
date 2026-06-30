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

## F002 — Executor max_tokens=1000 too low for complex multi-item tasks
**Date**: 2026-06-29
**Severity**: Medium (5/10 evals failing)
**Affected cases**: ri_004, ri_005, ri_007, ri_008, ri_010
**Pattern**: Tasks requiring output across 5+ accounts/items hit the 1000-token limit; LLM correctly produces partial output; verifier (LLM judge) correctly flags truncation; after 3 retries all fail
**Classification**: `bad_output_format` / executor constraint
**Resolution**: Increased max_tokens from 1000 → 2500 in `executor.py`
**Status**: FIXED — re-running failing cases to verify

## F003 — Verifier preview shows truncated dict repr, LLM judge penalizes for truncation
**Date**: 2026-06-30
**Severity**: High (causes repeated false failures on long-output tasks)
**Pattern**: `str(output)[:2000]` produces Python dict repr cutting mid-string; LLM judge reads "...'result': 'text cut here" as incomplete output, scores < 0.6, task retried 3× and fails
**Resolution**: Structured preview: `[summary]` field + `[result]` truncated at 1800 chars with explicit "treat as complete if summary confirms success" note
**Status**: FIXED in verifier.py

## F004 — Executor passes only `summary` to downstream tasks, starving validation tasks of context
**Date**: 2026-06-30
**Severity**: Medium (validation/review tasks fail because they have no real content to validate)
**Pattern**: `prior_task_outputs` only passed `summary` (1-2 sentences) to subsequent tasks; a "validate the plan" task receives 2 sentences instead of the actual plan it needs to review
**Resolution**: Executor now passes both `summary` + first 800 chars of `result` as context for each prior task
**Status**: FIXED in executor.py

## Improvement Queue (from failures)

- [x] Add pre-flight API key check at startup and warn clearly in `/api/aos/health`
- [ ] Add rule-based planner fallback that creates structured tasks even without Claude API
- [x] Add eval regression detector (compare pass rate vs last run, alert on drop)
- [ ] Add per-task adaptive token budget (simple tasks: 1000, complex/multi-item: 2500)
- [ ] Add task complexity signal to planner so executor can pick the right token budget
