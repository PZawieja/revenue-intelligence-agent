from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


MOCK_OUTPUTS: Dict[str, Dict[str, Any]] = {
    "revenue_intel": {
        "result": {
            "accounts": [
                {"name": "Acme Corp", "health_score": 0.32, "arr": 85000, "risk": "renewal in 12 days, high ticket volume"},
                {"name": "Globex Ltd", "health_score": 0.41, "arr": 120000, "risk": "50% usage drop last 30 days"},
                {"name": "Initech SA", "health_score": 0.45, "arr": 95000, "risk": "unpaid invoice + renewal in 21 days"},
            ],
            "recommended_actions": [
                "Schedule executive call with Acme Corp this week — renewal imminent",
                "Investigate Globex usage drop — send health check email today",
                "Resolve Initech invoice before renewal discussion",
            ],
        },
        "summary": "3 critical accounts identified with combined €300k ARR at risk. Acme Corp renewal is most urgent (12 days). Recommended immediate outreach sequence provided.",
        "_tokens": 450,
        "_model": "mock",
        "_executed_at": datetime.now(timezone.utc).isoformat(),
    },
    "planning": {
        "result": {
            "priority_1_critical": ["Schedule Acme executive call", "Send Globex health-check email"],
            "priority_2_proactive": ["Renewal prep for Initech", "Usage review for 3 yellow accounts"],
            "priority_3_expansion": ["Book expansion discovery with HealthCo (score 0.89)"],
        },
        "summary": "7-action CS team plan for the week. 2 critical interventions first, then 2 proactive renewals, then 1 expansion conversation.",
        "_tokens": 380,
        "_model": "mock",
        "_executed_at": datetime.now(timezone.utc).isoformat(),
    },
    "data_analysis": {
        "result": {
            "summary": "Portfolio ARR split: 35% at risk (red+yellow), 65% healthy",
            "key_findings": ["€1.43M in red band", "€1.07M in yellow band", "€1.60M in green band"],
            "recommendations": ["Focus on red-band renewals first", "Upsell push in green band"],
        },
        "summary": "ARR exposure analysis complete: 35% of portfolio ARR in at-risk health bands.",
        "_tokens": 320,
        "_model": "mock",
        "_executed_at": datetime.now(timezone.utc).isoformat(),
    },
    "default": {
        "result": "Task completed successfully (mock mode — no API key configured)",
        "summary": "Mock execution completed. Configure ANTHROPIC_API_KEY for real AI execution.",
        "_tokens": 0,
        "_model": "mock",
        "_executed_at": datetime.now(timezone.utc).isoformat(),
    },
}


def mock_execute_task(
    task: Any,
    goal_description: str,
    prior_task_outputs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    skill = (task.skill_tags or ["default"])[0]
    output = dict(MOCK_OUTPUTS.get(skill, MOCK_OUTPUTS["default"]))
    output["_task_title"] = task.title
    output["_executed_at"] = datetime.now(timezone.utc).isoformat()
    return output


def mock_decompose_goal(goal: Any) -> List[Any]:
    from aos.engine.schemas import Task, RiskLevel

    return [
        Task(
            goal_id=goal.id,
            title="Analyze accounts data",
            description=f"Gather and analyze account data relevant to: {goal.description[:200]}",
            skill_tags=["revenue_intel"],
            priority=1,
            risk_level=RiskLevel.low,
            verification_plan="output must contain result and summary keys",
        ),
        Task(
            goal_id=goal.id,
            title="Generate recommendations",
            description="Based on the account analysis, generate prioritized recommendations.",
            skill_tags=["planning"],
            priority=2,
            risk_level=RiskLevel.low,
            depends_on=[],
            verification_plan="output must contain result and summary keys",
        ),
    ]


