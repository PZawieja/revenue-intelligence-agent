from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .schemas import Task
from .planner import SKILL_SYSTEM_PROMPTS, DEFAULT_SKILL_SYSTEM, _get_api_client

logger = logging.getLogger(__name__)

REVENUE_CONTEXT = """Portfolio context (as of current data):
- 50 B2B SaaS accounts, €4.1M total ARR
- Health scoring: Critical/red <0.50, Warning/yellow 0.50-0.75, Healthy/green >0.75
- 11 Critical accounts: ~€1.43M ARR at churn risk
- 11 Warning accounts: ~€1.07M ARR requiring attention
- 28 Healthy accounts: ~€1.60M ARR — primary expansion pool
- Seat utilization >85% = strong add-seats signal
- Renewals within 30 days = urgent; 30-90 days = proactive outreach

Available data views: ai_dm_account_overview, ai_fct_account_health_score,
ai_fct_account_expansion_potential, ai_fct_renewals_at_risk, ai_fct_expansion_shortlist,
ai_arr_exposure, ai_fct_account_usage_trend"""


def _build_system_prompt(skill_tags: List[str]) -> str:
    for tag in skill_tags:
        if tag in SKILL_SYSTEM_PROMPTS:
            system = SKILL_SYSTEM_PROMPTS[tag]
            if tag == "revenue_intel":
                system += f"\n\n{REVENUE_CONTEXT}"
            return system
    return DEFAULT_SKILL_SYSTEM


def _parse_output(raw: str) -> Dict[str, Any]:
    try:
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
    except Exception:
        return {"result": raw, "summary": raw[:200]}


def execute_task(
    task: Task,
    goal_description: str,
    prior_task_outputs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    client = _get_api_client()
    if not client:
        return {
            "result": "ANTHROPIC_API_KEY not set — cannot execute task",
            "summary": "No API key",
            "error": True,
        }

    system = _build_system_prompt(task.skill_tags)

    context_parts = [
        f"Goal: {goal_description}",
        f"Task: {task.title}",
        f"Task description: {task.description}",
    ]
    if prior_task_outputs:
        context_parts.append("Prior task outputs:")
        for i, output in enumerate(prior_task_outputs):
            summary = output.get("summary", "")
            result_preview = str(output.get("result", ""))[:800]
            entry = f"  Task {i+1} summary: {summary}"
            if result_preview:
                entry += f"\n  Task {i+1} result excerpt: {result_preview}"
            context_parts.append(entry)

    context_parts.append(
        "\nExecute this task and return structured JSON output. "
        "Always include 'result' (primary output) and 'summary' (1-2 sentence summary) keys."
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=system,
            messages=[{"role": "user", "content": "\n\n".join(context_parts)}],
            max_tokens=2500,
        )
        raw = response.content[0].text.strip()
        output = _parse_output(raw)
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        output["_tokens"] = tokens_used
        output["_model"] = "claude-sonnet-4-6"
        output["_executed_at"] = datetime.now(timezone.utc).isoformat()
        return output

    except Exception as exc:
        logger.warning("Task execution failed (%s): %s", task.id, exc)
        return {
            "result": None,
            "summary": f"Execution failed: {exc}",
            "error": True,
            "_executed_at": datetime.now(timezone.utc).isoformat(),
        }
