from __future__ import annotations
import copy
from rapidfuzz import process, fuzz

INTENT_PATTERNS: dict[str, list[str]] = {
    "account_overview": [
        "overview", "tell me about", "who is", "status", "summary",
        "details", "info", "information", "profile", "describe",
    ],
    "health_summary": [
        "health", "risk", "score", "at risk", "churn", "danger",
        "concern", "sick", "struggling", "troubled", "healthy",
    ],
    "expansion_potential": [
        "expand", "upsell", "growth", "seats", "upgrade", "potential",
        "opportunity", "grow", "expansion",
    ],
    "renewals_at_risk": [
        "renew", "renewal", "renewing", "expir", "due", "upcoming",
        "soon", "next 90", "this quarter", "at risk",
    ],
    "expansion_shortlist": [
        "shortlist", "candidates", "opportunities", "pipeline",
        "best accounts", "top accounts", "who should",
    ],
    "arr_exposure_overview": [
        "arr", "exposure", "portfolio", "breakdown", "distribution",
        "bands", "total arr", "revenue overview",
    ],
}

_DEFAULT_PARAMS: dict[str, dict] = {
    "account_overview":      {"account_name": None},
    "health_summary":        {"account_name": None},
    "expansion_potential":   {"account_name": None},
    "renewals_at_risk":      {"horizon_days": 90, "health_threshold": 0.75, "limit_n": 10},
    "expansion_shortlist":   {"minimum_health": 0.6, "top_n": 10},
    "arr_exposure_overview": {"risk_threshold": 0.6},
}


def extract_account(question: str, account_names: list[str]) -> str | None:
    if not account_names:
        return None
    match = process.extractOne(
        question, account_names, scorer=fuzz.partial_ratio, score_cutoff=70
    )
    return match[0] if match else None


def detect_intent(question: str, account_names: list[str]) -> dict:
    q = question.lower()

    scores = {
        intent: sum(1 for kw in keywords if kw in q)
        for intent, keywords in INTENT_PATTERNS.items()
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "account_overview"

    account = extract_account(question, account_names)
    params = copy.deepcopy(_DEFAULT_PARAMS[best])
    if "account_name" in params:
        params["account_name"] = account

    return {
        "intent": best,
        "params": params,
        "account_found": bool(account),
        "account_name": account,
    }
