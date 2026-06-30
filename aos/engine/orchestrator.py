from __future__ import annotations
import logging
from typing import Dict, List

from .schemas import Goal, GoalStatus, Task, TaskStatus
from .task_store import (
    create_task, get_goal, get_task,
    list_tasks, update_goal, update_task, record_metric,
)
from .planner import decompose_goal
from . import executor as _executor_mod
from .verifier import verify_task_output
from .memory import record_goal_success, record_goal_failure, record_learning

logger = logging.getLogger(__name__)


def _ready_tasks(tasks: List[Task]) -> List[Task]:
    complete_ids = {t.id for t in tasks if _is_complete(t)}
    return [
        t for t in tasks
        if t.status == TaskStatus.pending
        and all(dep in complete_ids for dep in t.depends_on)
    ]


def _is_complete(task: Task) -> bool:
    return task.status in (TaskStatus.complete, "complete")


def _is_failed(task: Task) -> bool:
    return task.status in (TaskStatus.failed, "failed")


def run_goal(goal_id: str) -> Dict:
    goal = get_goal(goal_id)
    if not goal:
        return {"error": f"Goal {goal_id} not found"}

    goal.status = GoalStatus.running
    update_goal(goal)

    tasks = list_tasks(goal_id=goal_id)
    if not tasks:
        new_tasks = decompose_goal(goal)
        for task in new_tasks:
            create_task(task)
        goal.task_ids = [t.id for t in new_tasks]
        update_goal(goal)
        tasks = new_tasks

    max_rounds = 20
    round_count = 0

    while round_count < max_rounds:
        round_count += 1
        all_tasks = list_tasks(goal_id=goal_id)

        if all(_is_complete(t) for t in all_tasks):
            break

        if any(_is_failed(t) for t in all_tasks):
            failed = [t for t in all_tasks if _is_failed(t)]
            exhausted = [t for t in failed if t.attempts >= t.max_attempts]
            if exhausted:
                _finalize_failure(goal, all_tasks, f"{len(exhausted)} task(s) exhausted retries")
                return _goal_result(goal, all_tasks)

        ready = _ready_tasks(all_tasks)
        if not ready:
            all_tasks_fresh = list_tasks(goal_id=goal_id)
            if all(_is_complete(t) for t in all_tasks_fresh):
                break
            blocked = [t for t in all_tasks_fresh if not _is_complete(t) and not _is_failed(t)]
            logger.warning("No ready tasks but %d not complete — possible dependency cycle", len(blocked))
            break

        prior_outputs = [
            get_task(dep_id).output
            for task in ready
            for dep_id in task.depends_on
            if get_task(dep_id) and get_task(dep_id).output
        ]

        for task in ready:
            _execute_and_verify(task, goal.description, prior_outputs)

            if goal.tokens_used > goal.budget_tokens:
                logger.warning("Goal %s exceeded budget (%d tokens)", goal.id, goal.tokens_used)
                break

            goal = get_goal(goal_id)

    all_tasks = list_tasks(goal_id=goal_id)

    if all(_is_complete(t) for t in all_tasks):
        _finalize_success(goal, all_tasks)
    else:
        failed = [t for t in all_tasks if _is_failed(t)]
        if failed:
            _finalize_failure(goal, all_tasks, f"Tasks failed: {[t.title for t in failed]}")
        else:
            _finalize_failure(goal, all_tasks, "Goal did not complete within max rounds")

    return _goal_result(get_goal(goal_id), list_tasks(goal_id=goal_id))


def _execute_and_verify(task: Task, goal_description: str, prior_outputs: List[Dict]) -> None:
    task.status = TaskStatus.claimed
    task.attempts += 1
    update_task(task)

    output = _executor_mod.execute_task(task, goal_description, prior_outputs or [])
    tokens = output.pop("_tokens", 0)
    task.tokens_used = tokens

    goal = get_goal(task.goal_id)
    if goal:
        goal.tokens_used = (goal.tokens_used or 0) + tokens
        update_goal(goal)

    verification = verify_task_output(task.description, task.verification_plan, output)
    task.evidence.append({
        "type": "execution",
        "output_summary": str(output.get("summary", ""))[:300],
        "verification": verification,
    })

    v_passed = verification.get("passed") or (verification.get("score", 0) >= 0.6)
    if v_passed:
        task.output = output
        task.status = TaskStatus.complete
        task.error = None
        record_metric("task_complete", 1)
    elif task.attempts < task.max_attempts:
        task.status = TaskStatus.pending
        task.error = f"Verification failed: {verification.get('issues')}"
    else:
        task.output = output
        task.status = TaskStatus.failed
        task.error = f"Verification failed after {task.attempts} attempts: {verification.get('issues')}"
        record_metric("task_failed", 1)

    update_task(task)


def _finalize_success(goal: Goal, tasks: List[Task]) -> None:
    outputs = {t.title: t.output.get("summary", "") for t in tasks}
    goal.status = GoalStatus.complete
    goal.result = {
        "status": "complete",
        "tasks_completed": len(tasks),
        "outputs": outputs,
    }
    goal.evidence.append({"type": "completion", "task_count": len(tasks)})
    update_goal(goal)
    memory_entry = record_goal_success(goal, tasks)
    record_learning(
        what_worked=f"Decomposed into {len(tasks)} tasks, all completed",
        what_failed=None,
        improvement_candidate=None,
        goal_id=goal.id,
    )
    record_metric("goal_complete", 1)
    record_metric("tokens_per_goal", goal.tokens_used)


def _finalize_failure(goal: Goal, tasks: List[Task], reason: str) -> None:
    goal.status = GoalStatus.failed
    goal.result = {"status": "failed", "reason": reason}
    update_goal(goal)
    record_goal_failure(goal, tasks, reason)
    record_metric("goal_failed", 1)


def _goal_result(goal: Goal, tasks: List[Task]) -> Dict:
    return {
        "goal_id": goal.id,
        "title": goal.title,
        "status": goal.status.value if hasattr(goal.status, "value") else goal.status,
        "result": goal.result,
        "tokens_used": goal.tokens_used,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "skill_tags": t.skill_tags,
                "attempts": t.attempts,
                "output_summary": t.output.get("summary", "")[:300] if t.output else "",
                "evidence": t.evidence,
                "tokens_used": t.tokens_used,
            }
            for t in tasks
        ],
        "evidence": goal.evidence,
    }
