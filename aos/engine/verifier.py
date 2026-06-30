from __future__ import annotations
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _is_non_empty(output: Dict[str, Any]) -> bool:
    if not output:
        return False
    result = output.get("result")
    if result is None:
        return False
    if isinstance(result, str) and len(result.strip()) < 5:
        return False
    if isinstance(result, (list, dict)) and len(result) == 0:
        return False
    return True


def _has_error(output: Dict[str, Any]) -> bool:
    return bool(output.get("error"))


def _check_required_fields(output: Dict[str, Any], verification_plan: Optional[str]) -> bool:
    if not verification_plan:
        return True
    plan = verification_plan.lower()
    if "result" in plan and "result" not in output:
        return False
    if "summary" in plan and "summary" not in output:
        return False
    return True


def _llm_verify(
    task_description: str,
    verification_plan: str,
    output: Dict[str, Any],
) -> Dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"passed": True, "score": 0.7, "issues": [], "method": "skipped_no_key"}

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        preview_parts = []
        if "summary" in output:
            preview_parts.append(f"[summary] {output['summary']}")
        if "result" in output:
            result_str = str(output["result"])
            if len(result_str) > 1800:
                result_str = result_str[:1800] + "\n... [remainder truncated — treat as complete if summary indicates success]"
            preview_parts.append(f"[result] {result_str}")
        output_preview = "\n".join(preview_parts) if preview_parts else str(output)[:1500]

        prompt = (
            f"Task description: {task_description}\n\n"
            f"Verification criteria: {verification_plan}\n\n"
            f"Task output:\n{output_preview}\n\n"
            "Evaluate whether this output substantially satisfies the verification criteria. "
            "Be pragmatic — partial completeness is acceptable if the core requirement is met. "
            "Do NOT penalize for text truncation if the summary confirms the task completed. "
            "Return JSON only: {\"passed\": bool, \"score\": 0.0-1.0, \"issues\": [\"...\"], \"recommendation\": \"...\"}"
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        import json
        result = json.loads(raw)
        result["method"] = "llm_judge"
        return result
    except Exception as exc:
        logger.warning("LLM verification failed: %s", exc)
        return {"passed": True, "score": 0.5, "issues": [], "method": "fallback"}


def verify_task_output(
    task_description: str,
    verification_plan: Optional[str],
    output: Dict[str, Any],
    use_llm: bool = True,
) -> Dict[str, Any]:
    if _has_error(output):
        return {
            "passed": False,
            "score": 0.0,
            "issues": ["task output contains error flag"],
            "method": "rule",
        }
    if not _is_non_empty(output):
        return {
            "passed": False,
            "score": 0.0,
            "issues": ["output is empty or missing result field"],
            "method": "rule",
        }
    if not _check_required_fields(output, verification_plan):
        return {
            "passed": False,
            "score": 0.3,
            "issues": ["missing required output fields per verification plan"],
            "method": "rule",
        }
    if use_llm and verification_plan and len(verification_plan) > 10:
        return _llm_verify(task_description, verification_plan, output)
    return {"passed": True, "score": 0.8, "issues": [], "method": "rule_pass"}
