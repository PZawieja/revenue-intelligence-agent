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


def format_renewals_at_risk(
    df: pd.DataFrame,
    horizon_days: int,
    health_threshold: float,
    persona: str,
) -> Dict:
    """Build content contract for renewals_at_risk portfolio view. No KPI repetition in key_points."""
    n = 0 if df is None or df.empty else len(df)
    health_col = "health_score"
    threshold = health_threshold
    high_risk = (
        df[df[health_col].astype(float) < threshold]
        if (df is not None and not df.empty and health_col in df.columns)
        else pd.DataFrame()
    )
    high_count = len(high_risk)
    arr_col = "current_arr_eur"
    at_risk_arr = high_risk[arr_col].sum() if arr_col in high_risk.columns and not high_risk.empty else 0
    days_col = "days_to_renewal"
    median_days = (
        int(df[days_col].dropna().median())
        if df is not None and not df.empty and days_col in df.columns and not df[days_col].dropna().empty
        else None
    )

    title = f"Renewals at risk — next {horizon_days} days"
    kpis = [
        {"label": "Renewals", "value": str(n), "tone": "neutral"},
        {"label": "High risk", "value": str(high_count), "tone": "bad" if high_count > 0 else "neutral"},
        {"label": "ARR at risk", "value": f"€{at_risk_arr:,.0f}" if at_risk_arr else "€0", "tone": "warn" if at_risk_arr else "neutral"},
        {"label": "Median days", "value": str(median_days) if median_days is not None else "—", "tone": "neutral"},
    ]
    summary = (
        f"You have {n} renewals in the next {horizon_days} days. "
        f"{high_count} are high risk representing €{at_risk_arr:,.0f} ARR."
    )
    if n == 0:
        summary = f"No renewals at risk in the next {horizon_days} days."

    driver_col = "primary_risk_driver"
    key_points = []
    if df is not None and not df.empty and driver_col in df.columns:
        drivers = df[driver_col].dropna().value_counts()
        if not drivers.empty:
            top = drivers.index[0]
            key_points.append(f"Primary driver distribution: {top} leads.")
        if len(drivers) > 1:
            key_points.append("Mix of risk drivers; prioritize by ARR and days to renewal.")
    key_points.append("Start with highest ARR and lowest health score for outreach.")
    key_points = key_points[:3]

    next_best_action = (
        "Start outreach with the top 3 ARR accounts flagged as high risk and confirm adoption plan this week."
    )
    if n == 0:
        next_best_action = "No at-risk renewals in this window; keep monitoring health for the next horizon."

    talk_track = (
        "I’d like to align on a quick plan before your renewal so we can address any concerns in advance."
        if persona == "Customer Success"
        else None
    )

    followups = [
        "Show me the top 10 by ARR at risk",
        "Break down risk drivers",
    ]
    if df is not None and not df.empty and "account_name" in df.columns:
        first_name = df.iloc[0]["account_name"]
        if first_name:
            followups.append(f"Open {first_name}")
    followups = followups[:3]

    return {
        "title": title,
        "kpis": kpis[:4],
        "summary": summary,
        "key_points": key_points[:3],
        "next_best_action": next_best_action,
        "talk_track": talk_track,
        "followups": followups[:3],
    }


def format_expansion_shortlist(
    df: pd.DataFrame,
    top_n: int,
    minimum_health: float,
    persona: str,
) -> Dict:
    """Build content contract for expansion_shortlist portfolio view."""
    n = 0 if df is None or df.empty else len(df)
    arr_col = "current_arr_eur"
    total_arr = df[arr_col].sum() if df is not None and not df.empty and arr_col in df.columns else 0
    score_col = "expansion_score"
    avg_score = (
        df[score_col].mean()
        if df is not None and not df.empty and score_col in df.columns and df[score_col].notna().any()
        else None
    )
    health_col = "health_score"
    healthy_count = (
        (df[health_col].astype(float) >= minimum_health).sum()
        if df is not None and not df.empty and health_col in df.columns
        else 0
    )
    healthy_share = (100.0 * healthy_count / n) if n else 0

    title = f"Expansion shortlist — top {top_n}"
    kpis = [
        {"label": "Candidates", "value": str(n), "tone": "neutral"},
        {"label": "Total ARR", "value": f"€{total_arr:,.0f}" if total_arr else "€0", "tone": "neutral"},
        {
            "label": "Avg expansion score",
            "value": f"{avg_score:.2f}" if avg_score is not None and avg_score == avg_score else "—",
            "tone": "good" if avg_score is not None and avg_score >= 0.6 else "neutral",
        },
        {"label": "Healthy share", "value": f"{healthy_share:.0f}%", "tone": "neutral"},
    ]
    summary = (
        f"You have {n} expansion candidates. "
        f"Estimated focus set totals €{total_arr:,.0f} ARR with strong utilization signals."
    )
    if n == 0:
        summary = f"No expansion candidates meeting health >= {minimum_health}."

    angle_col = "recommended_angle"
    key_points = []
    if df is not None and not df.empty and angle_col in df.columns:
        angles = df[angle_col].dropna().value_counts()
        if not angles.empty:
            top_angle = angles.index[0]
            key_points.append(f"Recommended angle distribution: {top_angle} leads.")
        if len(angles) > 1:
            key_points.append("Mix of angles; prioritize by expansion score and ARR.")
    key_points.append("Start with top ARR and highest expansion score; validate seat or module need.")
    key_points = key_points[:3]

    next_best_action = (
        "Start with top 3 ARR accounts where expansion_score is highest and utilization is strong; "
        "validate seat/module need."
    )
    if n == 0:
        next_best_action = "No candidates in this filter; try lowering minimum health or broadening criteria."

    talk_track = (
        "I see strong usage and health—can we schedule a short call to explore adding seats or a module?"
        if persona == "Customer Success"
        else None
    )

    followups = [
        "Show only health > 0.8",
        "Group by recommended angle",
    ]
    if df is not None and not df.empty and "account_name" in df.columns:
        first_name = df.iloc[0]["account_name"]
        if first_name:
            followups.append(f"Open {first_name}")
    followups = followups[:3]

    return {
        "title": title,
        "kpis": kpis[:4],
        "summary": summary,
        "key_points": key_points[:3],
        "next_best_action": next_best_action,
        "talk_track": talk_track,
        "followups": followups[:3],
    }


def format_arr_exposure_overview(
    df_bands: pd.DataFrame,
    df_top: pd.DataFrame,
    risk_threshold: float,
    persona: str,
) -> Dict:
    """Build content contract for ARR exposure overview (CEO-level)."""
    total_arr = 0.0
    arr_at_risk = 0.0
    accounts_at_risk = 0
    if df_bands is not None and not df_bands.empty and "arr_eur" in df_bands.columns:
        total_arr = df_bands["arr_eur"].sum()
        red = df_bands[df_bands["health_band"].astype(str).str.lower() == "red"]
        if not red.empty:
            arr_at_risk = red["arr_eur"].sum()
            accounts_at_risk = int(red["accounts_count"].sum()) if "accounts_count" in red.columns else 0
    pct_at_risk = (100.0 * arr_at_risk / total_arr) if total_arr else 0.0
    n_top = len(df_top) if df_top is not None and not df_top.empty else 0

    title = "ARR exposure overview"
    kpis = [
        {"label": "Total ARR", "value": f"€{total_arr:,.0f}", "tone": "neutral"},
        {"label": "ARR at risk", "value": f"€{arr_at_risk:,.0f}", "tone": "warn" if arr_at_risk else "neutral"},
        {"label": "% at risk", "value": f"{pct_at_risk:.1f}%", "tone": "warn" if pct_at_risk > 0 else "neutral"},
        {"label": "Accounts at risk", "value": str(accounts_at_risk), "tone": "warn" if accounts_at_risk else "neutral"},
    ]
    summary = (
        f"{pct_at_risk:.1f}% of ARR is tied to accounts with health below {risk_threshold}. "
        f"Biggest exposure is concentrated in the top {n_top} accounts."
    )
    if total_arr == 0:
        summary = "No ARR exposure data available."

    key_points = []
    if df_bands is not None and not df_bands.empty:
        band_dist = df_bands.set_index("health_band")["arr_eur"].to_dict() if "health_band" in df_bands.columns else {}
        if band_dist:
            key_points.append(f"Band distribution: green/yellow/red ARR split by health band.")
        red_share = (100.0 * arr_at_risk / total_arr) if total_arr else 0
        if red_share > 20:
            key_points.append(f"Concentration: {red_share:.0f}% of ARR in at-risk band.")
    if df_top is not None and not df_top.empty and "current_arr_eur" in df_top.columns:
        top3_arr = df_top["current_arr_eur"].head(3).sum()
        top3_share = (100.0 * top3_arr / total_arr) if total_arr else 0
        key_points.append(f"Top 3 at-risk accounts represent {top3_share:.0f}% of total ARR.")
    key_points = key_points[:3]

    next_best_action = (
        "Review top ARR at-risk accounts and assign owners + mitigation plan this week."
    )
    talk_track = (
        "I’d like to align on a quick plan for the accounts with the highest exposure before renewal."
        if persona == "Customer Success"
        else None
    )
    followups = ["Show renewals at risk in the next 90 days", "Show expansion shortlist"]
    if df_top is not None and not df_top.empty and "account_name" in df_top.columns:
        first = df_top.iloc[0]["account_name"]
        if first:
            followups.append(f"Open {first}")
    followups = followups[:3]

    return {
        "title": title,
        "kpis": kpis[:4],
        "summary": summary,
        "key_points": key_points[:3],
        "next_best_action": next_best_action,
        "talk_track": talk_track,
        "followups": followups[:3],
    }


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
