from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import Goal, Task, MemoryEntry, MemoryType
from .task_store import create_memory_entry, list_memory

MEMORY_FILE = Path(__file__).parent.parent / "artifacts" / "memory.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_to_file(entry: Dict[str, Any]) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def record_goal_success(goal: Goal, tasks: List[Task]) -> MemoryEntry:
    def _status_is(task: Task, s: str) -> bool:
        return (task.status.value == s) if hasattr(task.status, "value") else (task.status == s)

    completed = [t for t in tasks if _status_is(t, "complete")]
    failed = [t for t in tasks if _status_is(t, "failed")]

    content = {
        "goal_title": goal.title,
        "goal_description": goal.description,
        "tasks_total": len(tasks),
        "tasks_completed": len(completed),
        "tasks_failed": len(failed),
        "tokens_used": sum(t.tokens_used for t in tasks),
        "task_summaries": [
            {"title": t.title, "output_summary": t.output.get("summary", "")[:200]}
            for t in completed
        ],
        "pattern": f"Goal type: {_classify_goal(goal.description)}",
    }
    entry = MemoryEntry(
        type=MemoryType.success,
        content=content,
        tags=_extract_tags(goal),
        source_goal_id=goal.id,
    )
    create_memory_entry(entry)
    _append_to_file(entry.to_dict())
    return entry


def record_goal_failure(goal: Goal, tasks: List[Task], error: str) -> MemoryEntry:
    failed_tasks = [
        {"title": t.title, "error": t.error, "attempts": t.attempts}
        for t in tasks
        if (t.status.value == "failed" if hasattr(t.status, "value") else t.status == "failed")
    ]
    content = {
        "goal_title": goal.title,
        "goal_description": goal.description,
        "error": error,
        "failed_tasks": failed_tasks,
        "pattern": f"Failure in: {_classify_goal(goal.description)}",
        "gap_classification": _classify_gap(error, failed_tasks),
    }
    entry = MemoryEntry(
        type=MemoryType.failure,
        content=content,
        tags=_extract_tags(goal) + ["failure"],
        source_goal_id=goal.id,
    )
    create_memory_entry(entry)
    _append_to_file(entry.to_dict())
    return entry


def record_learning(
    what_worked: str,
    what_failed: Optional[str],
    improvement_candidate: Optional[str],
    goal_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> MemoryEntry:
    content = {
        "what_worked": what_worked,
        "what_failed": what_failed,
        "improvement_candidate": improvement_candidate,
        "recorded_at": _now(),
    }
    entry = MemoryEntry(
        type=MemoryType.improvement if improvement_candidate else MemoryType.fact,
        content=content,
        tags=["learning"],
        source_goal_id=goal_id,
        source_task_id=task_id,
    )
    create_memory_entry(entry)
    _append_to_file(entry.to_dict())
    return entry


def get_relevant_memory(goal_description: str, limit: int = 5) -> List[MemoryEntry]:
    all_entries = list_memory(limit=100)
    goal_words = set(goal_description.lower().split())
    scored = []
    for entry in all_entries:
        content_str = json.dumps(entry.content).lower()
        overlap = sum(1 for w in goal_words if w in content_str)
        scored.append((overlap, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:limit]]


def _classify_goal(description: str) -> str:
    d = description.lower()
    if any(w in d for w in ["health", "risk", "churn", "critical"]):
        return "account_health"
    if any(w in d for w in ["expand", "upsell", "growth", "seats"]):
        return "expansion"
    if any(w in d for w in ["renew", "renewal", "expir"]):
        return "renewal"
    if any(w in d for w in ["arr", "revenue", "portfolio"]):
        return "portfolio_overview"
    return "general"


def _classify_gap(error: str, failed_tasks: List[Dict]) -> str:
    err = (error or "").lower()
    if "api" in err or "key" in err:
        return "missing_tool_or_credential"
    if "parse" in err or "json" in err:
        return "bad_output_format"
    if failed_tasks and any("timeout" in str(t.get("error", "")).lower() for t in failed_tasks):
        return "timeout"
    return "execution_error"


def _extract_tags(goal: Goal) -> List[str]:
    tags = [_classify_goal(goal.description)]
    if "urgent" in goal.description.lower():
        tags.append("urgent")
    return tags
