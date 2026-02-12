def interpret_account_overview(row: dict) -> str:
    return f"""
--- ACCOUNT OVERVIEW ---

Account: {row['account_name']}
Plan: {row['plan']}
Status: {row['subscription_status']}
Renewal Date: {row['renewal_date']}

MRR: €{row['current_mrr_eur']}
ARR: €{row['current_arr_eur']}

Seats Purchased: {row['seats_purchased']}
"""


def interpret_health_summary(row: dict) -> str:
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

    return f"""
--- HEALTH SUMMARY ---

Account: {row['account_name']}
Health Score: {row['health_score']:.2f}
Health Band: {row['health_band']}

Days to renewal: {row['days_to_renewal']}

Why?
- {reason_text}
"""


def interpret_expansion_potential(row: dict) -> str:
    return f"""
--- EXPANSION POTENTIAL ---

Account: {row['account_name']}

Health Score: {row['health_score']:.2f}
Seat Utilization: {row['seat_utilization_ratio']:.2f}

Expansion Score: {row['expansion_score']:.2f}
Expansion Band: {row['expansion_band']}

Recommendation:
- {'Strong upsell candidate' if row['expansion_band'] == 'high' else 'Moderate opportunity' if row['expansion_band'] == 'medium' else 'Focus on retention before expansion'}
"""

INTERPRETERS = {
    "account_overview": interpret_account_overview
}

INTERPRETERS["health_summary"] = interpret_health_summary
INTERPRETERS["expansion_potential"] = interpret_expansion_potential
