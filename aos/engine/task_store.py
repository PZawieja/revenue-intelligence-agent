from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .schemas import Goal, GoalStatus, Task, TaskStatus, MemoryEntry, MemoryType

DB_PATH = Path(__file__).parent.parent / "engine" / "aos.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT '{}',
                evidence TEXT NOT NULL DEFAULT '[]',
                tokens_used INTEGER NOT NULL DEFAULT 0,
                budget_tokens INTEGER NOT NULL DEFAULT 50000,
                task_ids TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                skill_tags TEXT NOT NULL DEFAULT '[]',
                depends_on TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 5,
                risk_level TEXT NOT NULL DEFAULT 'low',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                output TEXT NOT NULL DEFAULT '{}',
                evidence TEXT NOT NULL DEFAULT '[]',
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                verification_plan TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            );

            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                source_task_id TEXT,
                source_goal_id TEXT
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_goal ON tasks(goal_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(type);
        """)


def _goal_from_row(row: sqlite3.Row) -> Goal:
    return Goal.from_dict({
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "result": json.loads(row["result"]),
        "evidence": json.loads(row["evidence"]),
        "tokens_used": row["tokens_used"],
        "budget_tokens": row["budget_tokens"],
        "task_ids": json.loads(row["task_ids"]),
    })


def _task_from_row(row: sqlite3.Row) -> Task:
    return Task.from_dict({
        "id": row["id"],
        "goal_id": row["goal_id"],
        "title": row["title"],
        "description": row["description"],
        "skill_tags": json.loads(row["skill_tags"]),
        "depends_on": json.loads(row["depends_on"]),
        "status": row["status"],
        "priority": row["priority"],
        "risk_level": row["risk_level"],
        "attempts": row["attempts"],
        "max_attempts": row["max_attempts"],
        "output": json.loads(row["output"]),
        "evidence": json.loads(row["evidence"]),
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "verification_plan": row["verification_plan"],
        "tokens_used": row["tokens_used"],
    })


def create_goal(goal: Goal) -> Goal:
    with _conn() as con:
        con.execute(
            """INSERT INTO goals (id, title, description, status, created_at, updated_at,
               result, evidence, tokens_used, budget_tokens, task_ids)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                goal.id, goal.title, goal.description,
                goal.status.value if isinstance(goal.status, GoalStatus) else goal.status,
                goal.created_at, goal.updated_at,
                json.dumps(goal.result), json.dumps(goal.evidence),
                goal.tokens_used, goal.budget_tokens, json.dumps(goal.task_ids),
            ),
        )
    return goal


def get_goal(goal_id: str) -> Optional[Goal]:
    with _conn() as con:
        row = con.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return _goal_from_row(row) if row else None


def list_goals(status: Optional[str] = None, limit: int = 50) -> List[Goal]:
    with _conn() as con:
        if status:
            rows = con.execute(
                "SELECT * FROM goals WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM goals ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [_goal_from_row(r) for r in rows]


def update_goal(goal: Goal) -> None:
    goal.updated_at = _now()
    with _conn() as con:
        con.execute(
            """UPDATE goals SET status=?, updated_at=?, result=?, evidence=?,
               tokens_used=?, task_ids=? WHERE id=?""",
            (
                goal.status.value if isinstance(goal.status, GoalStatus) else goal.status,
                goal.updated_at,
                json.dumps(goal.result), json.dumps(goal.evidence),
                goal.tokens_used, json.dumps(goal.task_ids), goal.id,
            ),
        )


def create_task(task: Task) -> Task:
    with _conn() as con:
        con.execute(
            """INSERT INTO tasks (id, goal_id, title, description, skill_tags, depends_on,
               status, priority, risk_level, attempts, max_attempts, output, evidence,
               error, created_at, updated_at, verification_plan, tokens_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id, task.goal_id, task.title, task.description,
                json.dumps(task.skill_tags), json.dumps(task.depends_on),
                task.status.value if isinstance(task.status, TaskStatus) else task.status,
                task.priority,
                task.risk_level.value if hasattr(task.risk_level, "value") else task.risk_level,
                task.attempts, task.max_attempts,
                json.dumps(task.output), json.dumps(task.evidence),
                task.error, task.created_at, task.updated_at,
                task.verification_plan, task.tokens_used,
            ),
        )
    return task


def get_task(task_id: str) -> Optional[Task]:
    with _conn() as con:
        row = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _task_from_row(row) if row else None


def list_tasks(goal_id: Optional[str] = None, status: Optional[str] = None) -> List[Task]:
    with _conn() as con:
        if goal_id and status:
            rows = con.execute(
                "SELECT * FROM tasks WHERE goal_id=? AND status=? ORDER BY priority ASC",
                (goal_id, status)
            ).fetchall()
        elif goal_id:
            rows = con.execute(
                "SELECT * FROM tasks WHERE goal_id=? ORDER BY priority ASC", (goal_id,)
            ).fetchall()
        elif status:
            rows = con.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY priority ASC", (status,)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
    return [_task_from_row(r) for r in rows]


def update_task(task: Task) -> None:
    task.updated_at = _now()
    with _conn() as con:
        con.execute(
            """UPDATE tasks SET status=?, updated_at=?, attempts=?, output=?,
               evidence=?, error=?, tokens_used=? WHERE id=?""",
            (
                task.status.value if isinstance(task.status, TaskStatus) else task.status,
                task.updated_at, task.attempts,
                json.dumps(task.output), json.dumps(task.evidence),
                task.error, task.tokens_used, task.id,
            ),
        )


def create_memory_entry(entry: MemoryEntry) -> MemoryEntry:
    with _conn() as con:
        con.execute(
            """INSERT INTO memory_entries (id, type, content, tags, created_at,
               source_task_id, source_goal_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id,
                entry.type.value if isinstance(entry.type, MemoryType) else entry.type,
                json.dumps(entry.content), json.dumps(entry.tags),
                entry.created_at, entry.source_task_id, entry.source_goal_id,
            ),
        )
    return entry


def list_memory(type: Optional[str] = None, limit: int = 50) -> List[MemoryEntry]:
    with _conn() as con:
        if type:
            rows = con.execute(
                "SELECT * FROM memory_entries WHERE type=? ORDER BY created_at DESC LIMIT ?",
                (type, limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM memory_entries ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [
        MemoryEntry(
            id=r["id"],
            type=MemoryType(r["type"]),
            content=json.loads(r["content"]),
            tags=json.loads(r["tags"]),
            created_at=r["created_at"],
            source_task_id=r["source_task_id"],
            source_goal_id=r["source_goal_id"],
        )
        for r in rows
    ]


def record_metric(name: str, value: float) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO metrics (name, value, recorded_at) VALUES (?, ?, ?)",
            (name, value, _now()),
        )


def get_metrics_summary() -> dict:
    with _conn() as con:
        total_goals = con.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        complete_goals = con.execute(
            "SELECT COUNT(*) FROM goals WHERE status='complete'"
        ).fetchone()[0]
        total_tasks = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        complete_tasks = con.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='complete'"
        ).fetchone()[0]
        failed_tasks = con.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='failed'"
        ).fetchone()[0]
        total_tokens = con.execute(
            "SELECT COALESCE(SUM(tokens_used), 0) FROM tasks"
        ).fetchone()[0]
        memory_count = con.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
    return {
        "goals_total": total_goals,
        "goals_complete": complete_goals,
        "tasks_total": total_tasks,
        "tasks_complete": complete_tasks,
        "tasks_failed": failed_tasks,
        "tokens_total": total_tokens,
        "memory_entries": memory_count,
    }
