# AOS Plan

## Milestone 1: Closed Loop (current)
**Goal**: Prove full goal→task→execute→verify→memory loop working end-to-end
**Status**: IN PROGRESS

### Phase 1a: Core engine (SQLite task store + schemas)
- [x] OPERATING_SUMMARY.md, CAPABILITY_MATRIX.md, IMPLEMENTATION_CONTRACT.md
- [x] aos/engine/schemas.py — typed task/goal/memory schema
- [x] aos/engine/task_store.py — SQLite-backed CRUD
- [x] aos/engine/planner.py — goal→task decomposition via Claude
- [x] aos/engine/executor.py — task execution via Claude with skill routing
- [x] aos/engine/verifier.py — structured verification
- [x] aos/engine/memory.py — file-based memory system
- [x] api/aos.py — FastAPI control plane routes
- [x] Update main.py with AOS router

### Phase 1b: First run evidence ✓ COMPLETE
- [x] Run first goal through full loop (mock + real failure path)
- [x] Verify output with evidence (verification layer working)
- [x] Record memory entry (27 memory entries recorded)
- [x] Update momentum.md
- [x] Eval suite: 5/5 cases passing (mock mode)
- [x] Failure correctly classified: missing_tool_or_credential for no API key

**M1 COMPLETE — 2026-06-29**
Evidence: `GET /api/aos/momentum` → milestone_status: "complete", 13 goals complete, 89% task completion rate

## Milestone 2: Eval Harness
**Status**: IN PROGRESS

- [x] 10 eval scenarios (ri_001–ri_010, 5 original + 5 new)
- [x] `fast=true` mode (3 cases, ~18s) for quick regression checks
- [x] `cost_per_task` metric on every EvalResult
- [x] Regression detection: `compare_to_baseline()` — regressions/improvements/stable
- [x] Baseline storage: `aos/evals/baseline.json` via `save_baseline()`
- [x] `/api/aos/evals/history` — list all past runs with pass rates
- [x] `/api/aos/evals/baseline` GET/POST — read and set baseline
- [ ] 10-case real LLM run complete + baseline saved (running…)
- [ ] Confirm regression detection fires correctly on a deliberate regression

## Milestone 3: Self-Improvement Loop
- One-change bounded improvement
- Before/after eval comparison
- Skill profile update when improvement validates

## Milestone 4: Proactive Monitoring
- Scheduled scan of project state
- Auto-generate goals for stale work, anomalies, missed opportunities
- APScheduler integration
