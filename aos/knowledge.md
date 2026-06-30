# AOS Knowledge Base

## System Architecture Facts

**Task execution model**: Pull-based. Goals decompose into tasks stored in SQLite. Each task is claimed atomically, executed, verified, and the result stored. No unbounded retry — 3 attempts max, then fail with classification.

**Module patching for mock mode**: `_executor_mod.execute_task` reference in `orchestrator.py` is replaceable at runtime by patching `aos.engine.executor.execute_task`. This works because orchestrator imports the module not the function. Used for testing and eval mock mode.

**Verification strategy**: Two-layer. Rule-based check first (non-empty, no error flag, required fields). LLM judge second (claude-haiku-4-5 for cost efficiency). LLM judge is skipped if no API key — system degrades gracefully.

**Memory system**: File-based (`aos/artifacts/memory.jsonl`) + SQLite index. Every run writes a memory entry. The JSONL file is human-readable and survives DB corruption.

**Planner fallback**: When API key is missing, planner creates a single "Execute goal directly" task instead of failing. This allows the system to attempt work even without AI decomposition.

## Domain Knowledge — Revenue Intelligence

- Health bands: red (<0.50), yellow (0.50-0.75), green (>0.75)
- 50 accounts, €4.1M ARR total
- Seat utilization >85% = expansion signal
- Renewals <30 days = urgent, 30-90 = proactive

## Skill Profile Routing

| Skill tag | System prompt | Best for |
|---|---|---|
| revenue_intel | B2B SaaS CS analysis prompt | Account health, expansion, renewal |
| planning | Strategic planner prompt | Action plans, priority lists |
| data_analysis | Data analyst prompt | ARR breakdowns, trend analysis |
| writing | Business writer prompt | Email drafts, CRM notes |
| research | Research analyst prompt | Market intel, competitor info |
| verification | QA evaluator prompt | Checking prior task outputs |

## Lessons Learned

**2026-06-30 M2 eval run**:
- Executor max_tokens=1000 is insufficient for tasks covering 5+ items (accounts, QBR sections, etc.) — fixed to 2500
- Verifier bug: `str(output)[:2000]` produces Python dict repr; LLM judge sees `'result': 'text cut here'` and reports truncation even when output is complete — fixed to structured `[summary]` + `[result truncated at 1800 chars with explicit note]`
- Executor prior context bug: only passed `summary` (2 sentences) to downstream tasks; validation tasks had nothing to validate — fixed to pass summary + first 800 chars of result
- `cost_per_task` metric in tokens: simple analysis ~1300-1500, complex multi-item ~2000-2500, multi-task goals ~4000+
- ri_005 (CS action plan with validation task) is the hardest case — planner generates a "validate the plan" task that needs full prior output to work; combination of F003 + F004 fixes should resolve it
- Regression detection unit-tested: correctly classifies regressions, improvements, stable-pass, stable-fail, new-cases

**2026-06-29 M1 build**:
- Python 3.9 requires `Optional[X]` not `X | None`; list comprehension conditional syntax is `[x for x in l if (condition)]` not `[x for x in l if a if b else c]`
- Eval harness must check output_summary string content, not dict key names in result dict
- Module-level monkey-patching works for executor swap because orchestrator references `_executor_mod.execute_task` not a local binding
- SQLite WAL mode required for concurrent reads during FastAPI serving
