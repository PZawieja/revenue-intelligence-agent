from fastapi import APIRouter
from core.db import query

router = APIRouter(prefix="/api")


@router.get("/portfolio")
def get_portfolio():
    risk_rows = query("""
        SELECT
            ae.account_id
          , ae.account_name
          , ao.segment
          , ae.health_score
          , ae.health_band
          , ae.current_arr_eur
          , ae.primary_risk_driver
          , h.days_to_renewal
          , h.usage_drop_ratio
          , h.tickets_high
          , h.unpaid_invoices
          , ao.renewal_date
          , ao.owner_ae
        FROM ai_arr_exposure ae
        JOIN ai_dm_account_overview ao ON ae.account_id = ao.account_id
        JOIN ai_fct_account_health_score h ON ae.account_id = h.account_id
        ORDER BY ae.health_score ASC, ae.current_arr_eur DESC NULLS LAST
    """)

    total_arr = sum(r["current_arr_eur"] or 0 for r in risk_rows)
    red_arr = sum(r["current_arr_eur"] or 0 for r in risk_rows if r["health_band"] == "red")

    health_counts: dict[str, int] = {"green": 0, "yellow": 0, "red": 0}
    for r in risk_rows:
        band = r["health_band"] or "green"
        health_counts[band] = health_counts.get(band, 0) + 1

    eligible = [r for r in risk_rows if r["days_to_renewal"] is not None and r["days_to_renewal"] >= 0]
    next_renewal = min(eligible, key=lambda x: x["days_to_renewal"]) if eligible else None

    arr_bands = query("""
        SELECT health_band
             , SUM(current_arr_eur) AS arr_eur
             , COUNT(*) AS accounts_count
        FROM ai_arr_exposure
        GROUP BY health_band
        ORDER BY CASE health_band WHEN 'green' THEN 1 WHEN 'yellow' THEN 2 WHEN 'red' THEN 3 END
    """)

    renewals = query("""
        SELECT account_id, account_name, renewal_date, days_to_renewal,
               health_score, health_band, current_arr_eur, primary_risk_driver
        FROM ai_fct_renewals_at_risk
        WHERE days_to_renewal BETWEEN 0 AND 90
        ORDER BY days_to_renewal ASC, health_score ASC
        LIMIT 20
    """)

    return {
        "kpis": {
            "total_arr": total_arr,
            "total_accounts": len(risk_rows),
            "arr_at_risk": red_arr,
            "arr_at_risk_pct": round(red_arr / total_arr * 100, 1) if total_arr else 0,
            "red_count": health_counts.get("red", 0),
            "yellow_count": health_counts.get("yellow", 0),
            "green_count": health_counts.get("green", 0),
            "next_renewal_days": next_renewal["days_to_renewal"] if next_renewal else None,
            "next_renewal_name": next_renewal["account_name"] if next_renewal else None,
        },
        "arr_bands": arr_bands,
        "renewals_90d": renewals,
        "risk_matrix": risk_rows,
    }
