"""
Deterministic business-first response formatter.
Produces a strict content contract: title, kpis, summary, key_points,
next_best_action, talk_track (CS only), followups (max 3).
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from scripts.ai_question_packs import FOLLOWUP_SUGGESTIONS, PERSONA_QUESTION_PACKS


# Persona-specific followup preference order (first N used, max 3)
FOLLOWUP_PREFERENCE_CS = [
    "Why is this account at risk?",
    "What is the expansion potential?",
    "Give me an account overview",
    "What is the health score for this account?",
    "Summarize the account status",
    "What are the renewal risks?",
]
FOLLOWUP_PREFERENCE_REVOPS = [
    "Give me an account overview",
    "What is the expansion potential?",
    "What is the health score for this account?",
    "Summarize the account status",
    "What are the renewal risks?",
    "Why is this account at risk?",
]
FOLLOWUP_PREFERENCE_FINANCE = [
    "Give me an account overview",
    "What is the health score for this account?",
    "What are the renewal risks?",
    "What is the expansion potential?",
    "Summarize the account status",
]


def _safe(val: Any) -> Any:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    return val


def _pick_followups(intent: str, persona: str, current_question: str, max_n: int = 3) -> List[str]:
    base = FOLLOWUP_SUGGESTIONS.get(intent, [])
    pack = PERSONA_QUESTION_PACKS.get(persona, [])
    allowed = [q for q in base if q in pack]
    if persona == "Customer Success":
        order = FOLLOWUP_PREFERENCE_CS
    elif persona == "RevOps":
        order = FOLLOWUP_PREFERENCE_REVOPS
    else:
        order = FOLLOWUP_PREFERENCE_FINANCE
    # Order by preference, then fill with rest
    ordered = [q for q in order if q in allowed]
    for q in allowed:
        if q not in ordered:
            ordered.append(q)
    # Remove current question (best-effort: normalize for comparison)
    current_lower = (current_question or "").strip().lower()
    ordered = [q for q in ordered if q.strip().lower() != current_lower]
    return ordered[:max_n]


def _summary_and_key_points(intent: str, row0: Dict, interpretation: Dict) -> tuple:
    """Return (summary: str, key_points: list[str]) with no KPI repetition."""
    account = row0.get("account_name", "This account")
    if intent == "account_overview":
        summary = f"{account} is on plan with clear renewal and revenue context."
        key_points = [
            "Plan and status set the context for renewal conversations.",
            "Renewal date drives timing of outreach.",
        ]
        return summary, key_points[:3]
    if intent == "health_summary":
        reasons = []
        if _safe(row0.get("usage_drop_ratio")) is not None and float(row0.get("usage_drop_ratio", 0)) >= 0.2:
            reasons.append("usage decline")
        if _safe(row0.get("tickets_high")) and int(row0.get("tickets_high", 0)) >= 1:
            reasons.append("support tickets")
        if _safe(row0.get("unpaid_invoices")) and int(row0.get("unpaid_invoices", 0)) >= 1:
            reasons.append("unpaid invoices")
        if _safe(row0.get("days_to_renewal")) is not None and int(row0.get("days_to_renewal", 999)) < 90:
            reasons.append("renewal approaching")
        driver = ", ".join(reasons) if reasons else "no major risk drivers"
        summary = f"{account} health is driven by: {driver}."
        key_points = [
            "Primary signal explains why the score is what it is.",
            "Use days to renewal to prioritize outreach.",
        ]
        if reasons:
            key_points.append("Address the main driver before renewal.")
        return summary, key_points[:3]
    if intent == "expansion_potential":
        band = (row0.get("expansion_band") or "").lower()
        summary = f"{account} expansion potential is {band}; use health and utilization to decide next steps."
        key_points = [
            "Expansion score combines health and seat utilization.",
            "High utilization with healthy account suggests upsell fit.",
        ]
        return summary, key_points[:3]
    summary = "Summary for this account."
    return summary, []


def _next_best_action(intent: str, row0: Dict, df: Optional[pd.DataFrame]) -> str:
    if intent == "health_summary":
        if df is not None and not df.empty:
            row = df.iloc[0]
            days = _safe(row.get("days_to_renewal"))
            usage = _safe(row.get("usage_drop_ratio"))
            if days is not None and int(days) <= 60:
                return "Proactively reach out before renewal and address the main risk driver."
            if usage is not None and float(usage) >= 0.20:
                return "Investigate usage decline and confirm adoption plan with the customer."
        return "Monitor health signals and plan renewal outreach in advance."
    if intent == "account_overview":
        return "Use this to confirm renewal timing, current value, and plan context."
    if intent in {"expansion_summary", "expansion", "expansion_potential"}:
        if df is not None and not df.empty:
            score = _safe(df.iloc[0].get("expansion_score"))
            if score is not None and float(score) >= 0.7:
                return "Review seats and product fit; propose a concrete upsell."
        return "Validate expansion drivers and identify 1–2 concrete upsell angles."
    return "Use this summary to decide the next best action."


def _talk_track(intent: str, row0: Dict) -> Optional[str]:
    """One sentence for CS: what to say to the customer. None for other personas (caller filters)."""
    account = row0.get("account_name", "the account")
    if intent == "account_overview":
        return f"I wanted to confirm your current plan and renewal date so we can align on next steps."
    if intent == "health_summary":
        return f"Based on recent signals, I’d like to align on a quick plan before your renewal."
    if intent == "expansion_potential":
        return f"I see some upside on seats and usage—can we schedule a short call to explore options?"
    return None


def format_response(
    intent: str,
    raw_result: Dict,
    persona: str,
    account_name: str,
    kpis: List[Dict],
    current_question: Optional[str] = None,
) -> Dict:
    """
    Build the strict content contract for an assistant message.
    raw_result must have: row0 (dict), interpretation (dict), df (DataFrame or None).
    """
    row0 = raw_result.get("row0") or {}
    interpretation = raw_result.get("interpretation") or {}
    df = raw_result.get("df")

    title_map = {
        "account_overview": "Account overview",
        "health_summary": "Health summary",
        "expansion_potential": "Expansion potential",
    }
    title = title_map.get(intent, "Answer")
    title = f"{title} — {account_name}" if account_name else title

    summary, key_points = _summary_and_key_points(intent, row0, interpretation)
    next_best_action = _next_best_action(intent, row0, df)
    talk_track = _talk_track(intent, row0) if persona == "Customer Success" else None
    followups = _pick_followups(intent, persona, current_question, max_n=3)

    return {
        "title": title,
        "kpis": kpis[:4],
        "summary": summary,
        "key_points": key_points[:3],
        "next_best_action": next_best_action,
        "talk_track": talk_track,
        "followups": followups[:3],
    }
