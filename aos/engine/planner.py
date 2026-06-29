from __future__ import annotations
import json
import logging
import os
from typing import List

from .schemas import Goal, Task, RiskLevel

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are a task planner for an agentic operating system.
Given a goal, decompose it into 1-5 concrete, executable tasks.

Each task must be:
- Specific and actionable (a worker can execute it without clarification)
- Scoped to one logical unit of work
- Tagged with skill domains from: [revenue_intel, data_analysis, writing, research, planning, verification]

Risk levels: low (read-only analysis), medium (generates content/recommendations), high (external actions, data mutations)

Return ONLY valid JSON — no text outside:
{
  "tasks": [
    {
      "title": "short task name",
      "description": "full description of what to do and what output is expected",
      "skill_tags": ["revenue_intel"],
      "priority": 1,
      "risk_level": "low",
      "depends_on": [],
      "verification_plan": "what to check to confirm this task succeeded"
    }
  ]
}

Rules:
- Sequence tasks correctly using depends_on (reference task index 0, 1, 2...)
- Priority 1 = highest
- For depends_on use the title of the task it depends on (exact match)
- Keep to 1-3 tasks for simple goals, 4-5 for complex ones
"""

SKILL_SYSTEM_PROMPTS = {
    "revenue_intel": """You are a Revenue Intelligence analyst with access to B2B SaaS account data.
Portfolio: 50 accounts, €4.1M ARR. Health bands: red (<0.50), yellow (0.50-0.75), green (>0.75).
Provide specific, data-grounded analysis. Return structured JSON output.""",
    "data_analysis": """You are a data analyst. Provide structured, evidence-based analysis.
Return findings as JSON with keys: summary, key_findings (list), recommendations (list), confidence.""",
    "writing": """You are a professional business writer. Produce concise, actionable content.
Return JSON with appropriate keys for the content type (email: subject+body, report: title+sections).""",
    "research": """You are a research analyst. Synthesize information from available context.
Return JSON with: findings, sources_consulted, confidence, gaps.""",
    "planning": """You are a strategic planner. Create clear, actionable plans.
Return JSON with: objective, steps (list), risks, success_criteria.""",
    "verification": """You are a quality verifier. Check work for completeness and correctness.
Return JSON with: passed (bool), issues (list), score (0.0-1.0), recommendation.""",
}

DEFAULT_SKILL_SYSTEM = """You are a capable AI assistant executing a specific task.
Analyze the task carefully, do the work, and return structured JSON output.
The JSON must contain a "result" key with the primary output and a "summary" key."""


def _get_api_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


def decompose_goal(goal: Goal) -> List[Task]:
    client = _get_api_client()
    if not client:
        task = Task(
            goal_id=goal.id,
            title="Execute goal directly",
            description=goal.description,
            skill_tags=["revenue_intel"],
            priority=1,
            risk_level=RiskLevel.low,
            verification_plan="output must be non-empty with result key",
        )
        return [task]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=PLANNER_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Goal title: {goal.title}\n\nGoal description: {goal.description}\n\nDecompose into concrete tasks."
            }],
            max_tokens=1200,
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        parsed = json.loads(raw)
        raw_tasks = parsed.get("tasks", [])

        title_to_task: dict[str, Task] = {}
        tasks: List[Task] = []
        for rt in raw_tasks[:5]:
            task = Task(
                goal_id=goal.id,
                title=rt.get("title", "Task"),
                description=rt.get("description", ""),
                skill_tags=rt.get("skill_tags", ["revenue_intel"]),
                priority=int(rt.get("priority", 5)),
                risk_level=RiskLevel(rt.get("risk_level", "low")),
                depends_on=[],
                verification_plan=rt.get("verification_plan", "output must be non-empty"),
            )
            title_to_task[task.title] = task
            tasks.append(task)

        for i, rt in enumerate(raw_tasks[:5]):
            for dep_title in rt.get("depends_on", []):
                dep_task = title_to_task.get(dep_title)
                if dep_task:
                    tasks[i].depends_on.append(dep_task.id)

        return tasks

    except Exception as exc:
        logger.warning("Planner decomposition failed: %s", exc)
        task = Task(
            goal_id=goal.id,
            title="Execute goal directly",
            description=goal.description,
            skill_tags=["revenue_intel"],
            priority=1,
            risk_level=RiskLevel.low,
            verification_plan="output must be non-empty with result key",
        )
        return [task]
