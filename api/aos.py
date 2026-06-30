from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aos.engine.task_store import (
    init_db, create_goal, get_goal, list_goals,
    list_tasks, list_memory, get_metrics_summary,
)
from aos.engine.schemas import Goal, GoalStatus
from aos.engine.orchestrator import run_goal as _run_goal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/aos")

init_db()


class GoalRequest(BaseModel):
    title: str
    description: str
    budget_tokens: Optional[int] = 50000


class GoalRunRequest(BaseModel):
    synchronous: bool = True


@router.post("/goals")
def create_new_goal(req: GoalRequest):
    goal = Goal(
        title=req.title[:120],
        description=req.description[:2000],
        budget_tokens=req.budget_tokens or 50000,
    )
    create_goal(goal)
    return goal.to_dict()


@router.post("/goals/{goal_id}/run")
def run_goal(goal_id: str):
    goal = get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    if goal.status not in (GoalStatus.pending, "pending"):
        raise HTTPException(status_code=409, detail=f"Goal already in status: {goal.status}")
    result = _run_goal(goal_id)
    return result


@router.post("/goals/{goal_id}/execute")
def create_and_run_goal(goal_id: str):
    return run_goal(goal_id)


@router.post("/run")
def quick_run(req: GoalRequest):
    goal = Goal(
        title=req.title[:120],
        description=req.description[:2000],
        budget_tokens=req.budget_tokens or 50000,
    )
    create_goal(goal)
    return _run_goal(goal.id)


@router.get("/goals")
def get_goals(status: Optional[str] = None, limit: int = 20):
    goals = list_goals(status=status, limit=limit)
    return [g.to_dict() for g in goals]


@router.get("/goals/{goal_id}")
def get_goal_detail(goal_id: str):
    goal = get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    tasks = list_tasks(goal_id=goal_id)
    return {
        **goal.to_dict(),
        "tasks": [t.to_dict() for t in tasks],
    }


@router.get("/tasks")
def get_tasks(goal_id: Optional[str] = None, status: Optional[str] = None):
    tasks = list_tasks(goal_id=goal_id, status=status)
    return [t.to_dict() for t in tasks]


@router.get("/memory")
def get_memory(type: Optional[str] = None, limit: int = 20):
    entries = list_memory(type=type, limit=limit)
    return [e.to_dict() for e in entries]


@router.get("/metrics")
def get_metrics():
    return get_metrics_summary()


@router.get("/momentum")
def get_momentum():
    pending_goals = list_goals(status="pending", limit=5)
    running_goals = list_goals(status="running", limit=5)
    failed_goals = list_goals(status="failed", limit=5)
    recent_memory = list_memory(limit=5)
    metrics = get_metrics_summary()

    now = [g.to_dict() for g in running_goals]
    next_up = [g.to_dict() for g in pending_goals]
    blocked = [
        g.to_dict() for g in failed_goals
        if any(t.status in ("failed", "blocked") for t in list_tasks(goal_id=g.id))
    ]

    return {
        "now": now,
        "next": next_up,
        "blocked": blocked,
        "improve": [
            e.to_dict() for e in recent_memory
            if e.type.value in ("failure", "improvement") if hasattr(e.type, "value")
        ],
        "metrics": metrics,
        "milestone": "M1: Closed Loop",
        "milestone_status": "in_progress" if metrics["goals_total"] == 0 else (
            "complete" if metrics["goals_complete"] > 0 else "in_progress"
        ),
    }


@router.get("/health")
def health():
    import os
    metrics = get_metrics_summary()
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    warnings = []
    if not has_api_key:
        warnings.append("ANTHROPIC_API_KEY not set — real execution disabled, mock mode only")
    return {
        "status": "ok",
        "ai_enabled": has_api_key,
        "warnings": warnings,
        "metrics": metrics,
    }


@router.post("/run/mock")
def quick_run_mock(req: GoalRequest):
    from aos.engine.schemas import Goal as _Goal
    from aos.engine.task_store import create_goal as _cg, create_task
    from aos.engine.orchestrator import _execute_and_verify, _finalize_success, _finalize_failure, _goal_result
    from aos.evals.mock_executor import mock_execute_task, mock_decompose_goal
    import aos.engine.executor as _exec

    original_exec = _exec.execute_task
    _exec.execute_task = mock_execute_task

    goal = _Goal(
        title=req.title[:120],
        description=req.description[:2000],
        budget_tokens=req.budget_tokens or 50000,
    )
    _cg(goal)

    tasks = mock_decompose_goal(goal)
    for t in tasks:
        create_task(t)
    from aos.engine.task_store import update_goal
    goal.task_ids = [t.id for t in tasks]
    update_goal(goal)

    from aos.engine.schemas import GoalStatus
    goal.status = GoalStatus.running
    update_goal(goal)

    for task in tasks:
        _execute_and_verify(task, goal.description, [])

    from aos.engine.task_store import list_tasks as _lt
    all_tasks = _lt(goal_id=goal.id)
    if all([t.status in ("complete", "complete") for t in all_tasks]):
        _finalize_success(goal, all_tasks)
    else:
        _finalize_failure(goal, all_tasks, "mock run failed")

    _exec.execute_task = original_exec

    from aos.engine.task_store import get_goal as _gg
    return _goal_result(_gg(goal.id), all_tasks)


def _mock_run_fn():
    from aos.engine.task_store import create_task as _ct, update_goal as _ug
    from aos.evals.mock_executor import mock_execute_task, mock_decompose_goal
    import aos.engine.executor as _exec
    from aos.engine.orchestrator import _execute_and_verify, _finalize_success, _goal_result
    from aos.engine.task_store import list_tasks as _lt, get_goal as _gg
    from aos.engine.schemas import GoalStatus

    original_exec = _exec.execute_task
    _exec.execute_task = mock_execute_task

    def mock_run_goal(goal_id: str):
        goal = _gg(goal_id)
        tasks = mock_decompose_goal(goal)
        for t in tasks:
            _ct(t)
        goal.task_ids = [t.id for t in tasks]
        goal.status = GoalStatus.running
        _ug(goal)
        for task in tasks:
            _execute_and_verify(task, goal.description, [])
        all_tasks = _lt(goal_id=goal.id)
        _finalize_success(goal, all_tasks)
        return _goal_result(_gg(goal_id), all_tasks)

    return mock_run_goal, original_exec, _exec


@router.post("/evals/run")
def run_evals(mock: bool = True, fast: bool = False):
    from aos.evals.harness import run_eval_suite
    if mock:
        run_fn, original_exec, _exec = _mock_run_fn()
        result = run_eval_suite(run_goal_fn=run_fn, fast=fast)
        _exec.execute_task = original_exec
    else:
        from aos.engine.orchestrator import run_goal as _run
        result = run_eval_suite(run_goal_fn=_run, fast=fast)
    return result


@router.get("/evals/history")
def eval_history(limit: int = 20):
    from aos.evals.harness import list_eval_history
    return list_eval_history(limit=limit)


@router.get("/evals/baseline")
def get_baseline():
    from aos.evals.harness import load_baseline
    baseline = load_baseline()
    if not baseline:
        raise HTTPException(status_code=404, detail="No baseline set. Run POST /api/aos/evals/baseline to establish one.")
    return baseline


@router.post("/evals/baseline")
def set_baseline():
    from aos.evals.harness import save_baseline, RESULTS_DIR
    import json
    files = sorted(RESULTS_DIR.glob("eval_*.json"), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No eval runs found. Run an eval first.")
    latest = json.loads(files[0].read_text())
    save_baseline(latest)
    return {"status": "baseline_saved", "pass_rate": latest["pass_rate"], "run_at": latest["run_at"]}
