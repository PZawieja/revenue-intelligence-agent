from __future__ import annotations
import copy
import re
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
        "best accounts", "top accounts", "who should", "expansion",
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


_RISK_WORDS = {"at risk", "at-risk", "risk", "risky", "churn", "danger", "critical", "struggling", "troubled"}


def _extract_days(q: str) -> int | None:
    m = re.search(r"next\s+(\d+)\s+days?", q) or re.search(r"in\s+(\d+)\s+days?", q)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s+days?", q)
    if m:
        return int(m.group(1))
    if re.search(r"next\s+week|this\s+week", q):
        return 7
    if re.search(r"next\s+month|this\s+month", q):
        return 30
    if re.search(r"quarter", q):
        return 90
    return None


def _extract_limit(q: str) -> int | None:
    m = re.search(r"top\s+(\d+)", q)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s+accounts?", q)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 100:
            return n
    return None


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

    if best == "renewals_at_risk":
        days = _extract_days(q)
        if days is not None:
            params["horizon_days"] = days
        limit = _extract_limit(q)
        if limit is not None:
            params["limit_n"] = limit
        # Relax health filter when user asks about renewals generically (not specifically risky)
        if not any(w in q for w in _RISK_WORDS):
            params["health_threshold"] = 1.0

    if best == "expansion_shortlist":
        limit = _extract_limit(q)
        if limit is not None:
            params["top_n"] = limit

    return {
        "intent": best,
        "params": params,
        "account_found": bool(account),
        "account_name": account,
    }
