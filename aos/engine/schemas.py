from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class GoalStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
    blocked = "blocked"


class TaskStatus(str, Enum):
    pending = "pending"
    claimed = "claimed"
    complete = "complete"
    failed = "failed"
    blocked = "blocked"
    skipped = "skipped"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class MemoryType(str, Enum):
    success = "success"
    failure = "failure"
    skill = "skill"
    fact = "fact"
    improvement = "improvement"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())[:8]


class Goal:
    def __init__(
        self,
        title: str,
        description: str,
        id: Optional[str] = None,
        status: GoalStatus = GoalStatus.pending,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        tokens_used: int = 0,
        budget_tokens: int = 50000,
        task_ids: Optional[List[str]] = None,
    ):
        self.id = id or new_id()
        self.title = title
        self.description = description
        self.status = status
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()
        self.result = result or {}
        self.evidence = evidence or []
        self.tokens_used = tokens_used
        self.budget_tokens = budget_tokens
        self.task_ids = task_ids or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, GoalStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "evidence": self.evidence,
            "tokens_used": self.tokens_used,
            "budget_tokens": self.budget_tokens,
            "task_ids": self.task_ids,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Goal":
        return cls(
            id=d["id"],
            title=d["title"],
            description=d["description"],
            status=GoalStatus(d.get("status", "pending")),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            result=d.get("result") or {},
            evidence=d.get("evidence") or [],
            tokens_used=d.get("tokens_used", 0),
            budget_tokens=d.get("budget_tokens", 50000),
            task_ids=d.get("task_ids") or [],
        )


class Task:
    def __init__(
        self,
        goal_id: str,
        title: str,
        description: str,
        skill_tags: Optional[List[str]] = None,
        depends_on: Optional[List[str]] = None,
        id: Optional[str] = None,
        status: TaskStatus = TaskStatus.pending,
        priority: int = 5,
        risk_level: RiskLevel = RiskLevel.low,
        attempts: int = 0,
        max_attempts: int = 3,
        output: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        verification_plan: Optional[str] = None,
        tokens_used: int = 0,
    ):
        self.id = id or new_id()
        self.goal_id = goal_id
        self.title = title
        self.description = description
        self.skill_tags = skill_tags or []
        self.depends_on = depends_on or []
        self.status = status
        self.priority = priority
        self.risk_level = risk_level
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.output = output or {}
        self.evidence = evidence or []
        self.error = error
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()
        self.verification_plan = verification_plan or "output must be non-empty and contain required fields"
        self.tokens_used = tokens_used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "skill_tags": self.skill_tags,
            "depends_on": self.depends_on,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else self.risk_level,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "output": self.output,
            "evidence": self.evidence,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "verification_plan": self.verification_plan,
            "tokens_used": self.tokens_used,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        return cls(
            id=d["id"],
            goal_id=d["goal_id"],
            title=d["title"],
            description=d["description"],
            skill_tags=d.get("skill_tags") or [],
            depends_on=d.get("depends_on") or [],
            status=TaskStatus(d.get("status", "pending")),
            priority=d.get("priority", 5),
            risk_level=RiskLevel(d.get("risk_level", "low")),
            attempts=d.get("attempts", 0),
            max_attempts=d.get("max_attempts", 3),
            output=d.get("output") or {},
            evidence=d.get("evidence") or [],
            error=d.get("error"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            verification_plan=d.get("verification_plan"),
            tokens_used=d.get("tokens_used", 0),
        )


class MemoryEntry:
    def __init__(
        self,
        type: MemoryType,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        id: Optional[str] = None,
        created_at: Optional[str] = None,
        source_task_id: Optional[str] = None,
        source_goal_id: Optional[str] = None,
    ):
        self.id = id or new_id()
        self.type = type
        self.content = content
        self.tags = tags or []
        self.created_at = created_at or _now()
        self.source_task_id = source_task_id
        self.source_goal_id = source_goal_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, MemoryType) else self.type,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "source_task_id": self.source_task_id,
            "source_goal_id": self.source_goal_id,
        }
