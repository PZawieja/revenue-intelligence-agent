# AGENTS.md — Operator Guide

## What this is
A project-level agentic operating system (AOS) layered on top of the Revenue Intelligence Agent FastAPI app. Provides goal intake, task decomposition, execution, verification, memory, and evaluation.

## Quick start for any agent entering this project

1. Read `aos/OPERATING_SUMMARY.md` — architecture, milestone, guardrails
2. Check `aos/momentum.md` — what's happening now and what's next
3. Check `GET /api/aos/momentum` — live system state
4. Read `aos/knowledge.md` — key architectural facts and domain knowledge

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/aos/health` | GET | System health + metrics |
| `/api/aos/momentum` | GET | Live now/next/blocked/improve queues |
| `/api/aos/goals` | GET | List all goals |
| `/api/aos/goals` | POST | Create a new goal |
| `/api/aos/goals/{id}/run` | POST | Run a pending goal |
| `/api/aos/run` | POST | Create + run in one call |
| `/api/aos/run/mock` | POST | Create + run with mock executor (no API key needed) |
| `/api/aos/goals/{id}` | GET | Goal detail with tasks |
| `/api/aos/tasks` | GET | List tasks (filterable by goal_id, status) |
| `/api/aos/memory` | GET | Memory entries |
| `/api/aos/metrics` | GET | Aggregate metrics |
| `/api/aos/evals/run?mock=true` | POST | Run eval suite (mock or real) |

## Key files

```
aos/
├── OPERATING_SUMMARY.md   ← read this first every session
├── CAPABILITY_MATRIX.md   ← runtime capabilities and gaps
├── IMPLEMENTATION_CONTRACT.md  ← mission, constraints, safety
├── plan.md                ← milestone plan and progress
├── momentum.md            ← live now/next/blocked/improve
├── knowledge.md           ← architectural facts, domain knowledge, lessons
├── AGENTS.md              ← this file
├── FAILURE.md             ← failure register
├── engine/
│   ├── aos.db             ← SQLite task/goal/memory store (WAL mode)
│   ├── schemas.py         ← Goal, Task, MemoryEntry types
│   ├── task_store.py      ← CRUD + metrics
│   ├── planner.py         ← goal → task decomposition via Claude
│   ├── executor.py        ← task execution via Claude with skill routing
│   ├── verifier.py        ← rule + LLM verification
│   ├── memory.py          ← write memory entries, file + DB
│   └── orchestrator.py    ← main execution loop
├── evals/
│   ├── harness.py         ← 5 eval cases, run_eval_suite()
│   ├── mock_executor.py   ← mock outputs for testing without API key
│   └── results/           ← eval run JSON files
├── artifacts/
│   └── memory.jsonl       ← human-readable memory log
└── runs/                  ← future run transcripts
```

## Safety rules
- `risk_level=high` tasks block on approval (not yet implemented — defer M2)
- Max 3 retries per task, then fail with gap classification
- Budget cap: 50k tokens per goal
- No destructive filesystem ops without explicit confirmation

## Adding a new skill
1. Add entry to `SKILL_SYSTEM_PROMPTS` dict in `engine/planner.py`
2. Add mock output in `evals/mock_executor.py`
3. Add eval case in `evals/harness.py`
4. Run eval suite to verify: `POST /api/aos/evals/run?mock=true`

## Continuation protocol
Any agent can continue work from this folder by:
1. Reading `aos/OPERATING_SUMMARY.md` and `aos/momentum.md`
2. Calling `GET /api/aos/momentum` to see current state
3. Picking up from the next queue items
