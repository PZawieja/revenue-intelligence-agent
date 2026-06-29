from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

EVALS_DIR = Path(__file__).parent
RESULTS_DIR = EVALS_DIR / "results"


class EvalCase:
    def __init__(
        self,
        id: str,
        name: str,
        goal_title: str,
        goal_description: str,
        expected_status: str = "complete",
        expected_output_keys: Optional[List[str]] = None,
        min_tasks: int = 1,
        max_tokens: int = 50000,
        tags: Optional[List[str]] = None,
    ):
        self.id = id
        self.name = name
        self.goal_title = goal_title
        self.goal_description = goal_description
        self.expected_status = expected_status
        self.expected_output_keys = expected_output_keys or []
        self.min_tasks = min_tasks
        self.max_tokens = max_tokens
        self.tags = tags or []


class EvalResult:
    def __init__(
        self,
        case_id: str,
        passed: bool,
        actual_status: str,
        tasks_count: int,
        tokens_used: int,
        elapsed_seconds: float,
        issues: Optional[List[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ):
        self.case_id = case_id
        self.passed = passed
        self.actual_status = actual_status
        self.tasks_count = tasks_count
        self.tokens_used = tokens_used
        self.elapsed_seconds = elapsed_seconds
        self.issues = issues or []
        self.evidence = evidence or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "actual_status": self.actual_status,
            "tasks_count": self.tasks_count,
            "tokens_used": self.tokens_used,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "issues": self.issues,
        }


REVENUE_INTEL_EVALS: List[EvalCase] = [
    EvalCase(
        id="ri_001",
        name="health_briefing",
        goal_title="Weekly account health briefing",
        goal_description="Identify the top 3 accounts most at risk this week based on health scores and renewal dates. Summarize primary risk driver and one concrete action per account.",
        expected_output_keys=["result", "summary"],
        tags=["revenue_intel", "health"],
    ),
    EvalCase(
        id="ri_002",
        name="expansion_opportunities",
        goal_title="Find expansion opportunities",
        goal_description="Identify the top 3 accounts best positioned for expansion (seat add or upsell). For each, explain why they're a good fit and what angle to use.",
        expected_output_keys=["result", "summary"],
        tags=["revenue_intel", "expansion"],
    ),
    EvalCase(
        id="ri_003",
        name="renewal_risk_report",
        goal_title="Renewal risk report for next 30 days",
        goal_description="Which accounts renew in the next 30 days and are at health risk? Prioritize by ARR at stake and provide recommended outreach sequence.",
        expected_output_keys=["result", "summary"],
        tags=["revenue_intel", "renewal"],
    ),
    EvalCase(
        id="ri_004",
        name="arr_exposure_analysis",
        goal_title="Portfolio ARR exposure by health band",
        goal_description="Summarize ARR distribution across health bands (red/yellow/green). Calculate what percentage of ARR is at risk and where the biggest concentration is.",
        expected_output_keys=["result", "summary"],
        tags=["revenue_intel", "arr"],
    ),
    EvalCase(
        id="ri_005",
        name="cs_action_plan",
        goal_title="CS team action plan for this week",
        goal_description="Create a prioritized action plan for a CS team covering: critical account interventions, proactive renewal outreach, and expansion conversations to start. Group by urgency.",
        expected_output_keys=["result", "summary"],
        tags=["revenue_intel", "planning"],
        min_tasks=2,
    ),
]


def run_eval_case(case: EvalCase, run_goal_fn: Callable) -> EvalResult:
    from aos.engine.schemas import Goal
    from aos.engine.task_store import create_goal

    goal = Goal(title=case.goal_title, description=case.goal_description, budget_tokens=case.max_tokens)
    create_goal(goal)

    start = time.time()
    try:
        result = run_goal_fn(goal.id)
    except Exception as exc:
        elapsed = time.time() - start
        return EvalResult(
            case_id=case.id,
            passed=False,
            actual_status="exception",
            tasks_count=0,
            tokens_used=0,
            elapsed_seconds=elapsed,
            issues=[f"Exception: {exc}"],
        )

    elapsed = time.time() - start
    issues = []

    actual_status = result.get("status", "unknown")
    if actual_status != case.expected_status:
        issues.append(f"Expected status={case.expected_status}, got {actual_status}")

    tasks = result.get("tasks", [])
    if len(tasks) < case.min_tasks:
        issues.append(f"Expected >= {case.min_tasks} tasks, got {len(tasks)}")

    tokens = result.get("tokens_used", 0)
    if tokens > case.max_tokens:
        issues.append(f"Tokens {tokens} exceeded budget {case.max_tokens}")

    complete_tasks = [t for t in tasks if t.get("status") == "complete"]
    if not complete_tasks:
        issues.append("No tasks completed successfully")
    else:
        for task in complete_tasks:
            output_summary = task.get("output_summary", "")
            if not output_summary or len(output_summary) < 10:
                issues.append(f"Task '{task.get('title', '?')}' output_summary is empty or too short")

    passed = actual_status == case.expected_status and len(issues) == 0

    return EvalResult(
        case_id=case.id,
        passed=passed,
        actual_status=actual_status,
        tasks_count=len(tasks),
        tokens_used=tokens,
        elapsed_seconds=elapsed,
        issues=issues,
        evidence={"result_summary": str(result.get("result", ""))[:300]},
    )


def run_eval_suite(
    cases: Optional[List[EvalCase]] = None,
    run_goal_fn: Optional[Callable] = None,
    save_results: bool = True,
) -> Dict[str, Any]:
    from aos.engine.orchestrator import run_goal as default_run

    cases = cases or REVENUE_INTEL_EVALS
    run_fn = run_goal_fn or default_run

    results = []
    for case in cases:
        logger.info("Running eval: %s (%s)", case.id, case.name)
        result = run_eval_case(case, run_fn)
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = passed / total if total else 0.0
    avg_tokens = sum(r.tokens_used for r in results) / total if total else 0
    avg_elapsed = sum(r.elapsed_seconds for r in results) / total if total else 0

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "pass_rate": round(pass_rate, 3),
        "passed": passed,
        "total": total,
        "avg_tokens": round(avg_tokens),
        "avg_elapsed_seconds": round(avg_elapsed, 2),
        "results": [r.to_dict() for r in results],
    }

    if save_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = RESULTS_DIR / f"eval_{ts}.json"
        out_path.write_text(json.dumps(summary, indent=2))
        logger.info("Eval results saved to %s", out_path)

    return summary
