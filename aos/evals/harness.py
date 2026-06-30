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
BASELINE_PATH = EVALS_DIR / "baseline.json"


class EvalCase:
    def __init__(
        self,
        id: str,
        name: str,
        goal_title: str,
        goal_description: str,
        expected_status: str = "complete",
        min_tasks: int = 1,
        max_tokens: int = 50000,
        tags: Optional[List[str]] = None,
    ):
        self.id = id
        self.name = name
        self.goal_title = goal_title
        self.goal_description = goal_description
        self.expected_status = expected_status
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

    @property
    def cost_per_task(self) -> float:
        return round(self.tokens_used / self.tasks_count, 1) if self.tasks_count else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "actual_status": self.actual_status,
            "tasks_count": self.tasks_count,
            "tokens_used": self.tokens_used,
            "cost_per_task": self.cost_per_task,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "issues": self.issues,
        }


REVENUE_INTEL_EVALS: List[EvalCase] = [
    EvalCase(
        id="ri_001",
        name="health_briefing",
        goal_title="Weekly account health briefing",
        goal_description="Identify the top 3 accounts most at risk this week based on health scores and renewal dates. Summarize primary risk driver and one concrete action per account.",
        tags=["revenue_intel", "health"],
    ),
    EvalCase(
        id="ri_002",
        name="expansion_opportunities",
        goal_title="Find expansion opportunities",
        goal_description="Identify the top 3 accounts best positioned for expansion (seat add or upsell). For each, explain why they're a good fit and what angle to use.",
        tags=["revenue_intel", "expansion"],
    ),
    EvalCase(
        id="ri_003",
        name="renewal_risk_report",
        goal_title="Renewal risk report for next 30 days",
        goal_description="Which accounts renew in the next 30 days and are at health risk? Prioritize by ARR at stake and provide recommended outreach sequence.",
        tags=["revenue_intel", "renewal"],
    ),
    EvalCase(
        id="ri_004",
        name="arr_exposure_analysis",
        goal_title="Portfolio ARR exposure by health band",
        goal_description="Summarize ARR distribution across health bands (red/yellow/green). Calculate what percentage of ARR is at risk and where the biggest concentration is.",
        tags=["revenue_intel", "arr"],
    ),
    EvalCase(
        id="ri_005",
        name="cs_action_plan",
        goal_title="CS team action plan for this week",
        goal_description="Create a prioritized action plan for a CS team covering: critical account interventions, proactive renewal outreach, and expansion conversations to start. Group by urgency.",
        tags=["revenue_intel", "planning"],
        min_tasks=2,
    ),
    EvalCase(
        id="ri_006",
        name="churn_risk_scoring",
        goal_title="Churn risk scoring and prioritization",
        goal_description="Score all critical (red) accounts by churn probability using health score, days to renewal, and support ticket volume. Output a ranked list with a one-line risk rationale per account.",
        tags=["revenue_intel", "health", "churn"],
    ),
    EvalCase(
        id="ri_007",
        name="usage_anomaly_report",
        goal_title="Usage anomaly detection report",
        goal_description="Identify accounts with significant usage drops in the last 30 days. For each anomaly, estimate the ARR at risk and suggest whether this warrants an emergency check-in or standard follow-up.",
        tags=["revenue_intel", "usage", "health"],
    ),
    EvalCase(
        id="ri_008",
        name="qbr_prep",
        goal_title="Quarterly business review preparation",
        goal_description="Prepare a QBR agenda outline for the top 5 accounts by ARR. For each account include: health trend, key wins, open risks, and one expansion opportunity if applicable.",
        tags=["revenue_intel", "planning", "writing"],
        min_tasks=2,
    ),
    EvalCase(
        id="ri_009",
        name="monthly_revenue_health",
        goal_title="Monthly revenue health check",
        goal_description="Produce a monthly revenue health summary: total ARR, ARR at risk by band, net ARR change risk (churn minus expansion), and top 3 priorities for the CS team this month.",
        tags=["revenue_intel", "arr", "planning"],
        min_tasks=2,
    ),
    EvalCase(
        id="ri_010",
        name="new_csm_account_brief",
        goal_title="New CSM onboarding account brief",
        goal_description="A new Customer Success Manager is joining and needs a briefing on the 5 most important accounts to understand immediately. For each: size, health status, biggest risk, and the most important relationship to know.",
        tags=["revenue_intel", "writing", "planning"],
    ),
]

FAST_EVALS = REVENUE_INTEL_EVALS[:3]


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
    fast: bool = False,
    compare_baseline: bool = True,
) -> Dict[str, Any]:
    from aos.engine.orchestrator import run_goal as default_run

    if cases is None:
        cases = FAST_EVALS if fast else REVENUE_INTEL_EVALS
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
    avg_cost_per_task = sum(r.cost_per_task for r in results) / total if total else 0

    summary: Dict[str, Any] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "pass_rate": round(pass_rate, 3),
        "passed": passed,
        "total": total,
        "avg_tokens": round(avg_tokens),
        "avg_cost_per_task": round(avg_cost_per_task, 1),
        "avg_elapsed_seconds": round(avg_elapsed, 2),
        "fast_mode": fast,
        "results": [r.to_dict() for r in results],
    }

    if compare_baseline:
        baseline = load_baseline()
        if baseline:
            summary["regression_report"] = compare_to_baseline(summary, baseline)

    if save_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = RESULTS_DIR / f"eval_{ts}.json"
        out_path.write_text(json.dumps(summary, indent=2))
        logger.info("Eval results saved to %s", out_path)

    return summary


def save_baseline(summary: Dict[str, Any]) -> None:
    payload = dict(summary)
    payload["established_at"] = datetime.now(timezone.utc).isoformat()
    BASELINE_PATH.write_text(json.dumps(payload, indent=2))
    logger.info("Baseline saved to %s (pass_rate=%.3f)", BASELINE_PATH, payload["pass_rate"])


def load_baseline() -> Optional[Dict[str, Any]]:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text())
    except Exception as exc:
        logger.warning("Could not load baseline: %s", exc)
        return None


def compare_to_baseline(current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    baseline_by_id: Dict[str, Dict] = {r["case_id"]: r for r in baseline.get("results", [])}
    current_by_id: Dict[str, Dict] = {r["case_id"]: r for r in current.get("results", [])}

    regressions = []
    improvements = []
    stable_pass = []
    stable_fail = []
    new_cases = []

    for case_id, cur in current_by_id.items():
        if case_id not in baseline_by_id:
            new_cases.append(case_id)
            continue
        was_passing = baseline_by_id[case_id]["passed"]
        now_passing = cur["passed"]
        if was_passing and not now_passing:
            regressions.append({
                "case_id": case_id,
                "was": True,
                "now": False,
                "issues": cur.get("issues", []),
                "tokens_delta": cur["tokens_used"] - baseline_by_id[case_id]["tokens_used"],
            })
        elif not was_passing and now_passing:
            improvements.append({"case_id": case_id, "was": False, "now": True})
        elif now_passing:
            stable_pass.append(case_id)
        else:
            stable_fail.append(case_id)

    pass_rate_delta = round(current["pass_rate"] - baseline["pass_rate"], 3)
    tokens_delta = round(current["avg_tokens"] - baseline["avg_tokens"])

    status = "ok"
    if regressions:
        status = "regression"
    elif improvements:
        status = "improvement"

    return {
        "status": status,
        "pass_rate_delta": pass_rate_delta,
        "avg_tokens_delta": tokens_delta,
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
        "regressions": regressions,
        "improvements": improvements,
        "stable_pass": stable_pass,
        "stable_fail": stable_fail,
        "new_cases": new_cases,
        "baseline_run_at": baseline.get("run_at", "unknown"),
    }


def list_eval_history(limit: int = 20) -> List[Dict[str, Any]]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(RESULTS_DIR.glob("eval_*.json"), reverse=True)[:limit]
    history = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            history.append({
                "file": f.name,
                "run_at": data.get("run_at"),
                "pass_rate": data.get("pass_rate"),
                "passed": data.get("passed"),
                "total": data.get("total"),
                "avg_tokens": data.get("avg_tokens"),
                "fast_mode": data.get("fast_mode", False),
                "has_regression": data.get("regression_report", {}).get("regression_count", 0) > 0,
            })
        except Exception:
            pass
    return history
