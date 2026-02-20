def interpret_account_overview(row: dict) -> dict:
    summary_bullets = [
        f"{row['account_name']} is on the {row['plan']} plan and is currently {row['subscription_status']}.",
        f"Renewal is on {row['renewal_date']}.",
        f"Current revenue is €{row['current_mrr_eur']} MRR (≈ €{row['current_arr_eur']} ARR).",
        f"Seats purchased: {row['seats_purchased']}.",
    ]

    return {
        "title": "Account overview",
        "summary_bullets": summary_bullets[:5],
        "narrative": "Use this to confirm renewal timing, current value, and plan context.",
        "definitions": [
            "MRR = monthly recurring revenue for the current subscription.",
            "ARR = annualized recurring revenue (MRR × 12).",
        ],
        "warnings": [],
    }


def interpret_health_summary(row: dict) -> dict:
    reasons = []

    if row["usage_drop_ratio"] >= 0.3:
        reasons.append("usage is declining")
    if row["tickets_high"] >= 1:
        reasons.append("high severity support tickets exist")
    if row["unpaid_invoices"] >= 1:
        reasons.append("there are unpaid invoices")
    if row["days_to_renewal"] is not None and row["days_to_renewal"] < 90:
        reasons.append("renewal is approaching soon")

    reason_text = " and ".join(reasons) if reasons else "no major risk signals detected"

    summary_bullets = [
        f"{row['account_name']} health score is {row['health_score']:.2f} ({row['health_band']}).",
        f"Days to renewal: {row['days_to_renewal']}.",
        f"Primary signal: {reason_text}.",
    ]

    return {
        "title": "Health summary",
        "summary_bullets": summary_bullets[:5],
        "narrative": "Use this to prioritize proactive outreach and renewal planning.",
        "definitions": [
            "Health score ranges from 0 (high risk) to 1 (healthy).",
            "Health band is a simple green/yellow/red categorization.",
        ],
        "warnings": [],
    }


def interpret_expansion_potential(row: dict) -> dict:
    recommendation = (
        "Strong upsell candidate"
        if row["expansion_band"] == "high"
        else "Moderate opportunity"
        if row["expansion_band"] == "medium"
        else "Focus on retention before expansion"
    )

    summary_bullets = [
        f"{row['account_name']} expansion score is {row['expansion_score']:.2f} ({row['expansion_band']}).",
        f"Health score: {row['health_score']:.2f}.",
        f"Seat utilization: {row['seat_utilization_ratio']:.2f}.",
        f"Recommendation: {recommendation}.",
    ]

    return {
        "title": "Expansion potential",
        "summary_bullets": summary_bullets[:5],
        "narrative": "Use this to target accounts for upsell based on health and utilization.",
        "definitions": [
            "Seat utilization approximates active usage relative to purchased seats.",
            "Expansion score combines health and utilization into a 0–1 signal.",
        ],
        "warnings": [],
    }

INTERPRETERS = {
    "account_overview": interpret_account_overview
}

INTERPRETERS["health_summary"] = interpret_health_summary
INTERPRETERS["expansion_potential"] = interpret_expansion_potential
