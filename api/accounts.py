from fastapi import APIRouter, HTTPException
from core.db import query, query_one

router = APIRouter(prefix="/api")


@router.get("/accounts/names")
def account_names():
    rows = query("""
        SELECT ao.account_id, ao.account_name, h.health_band
        FROM ai_dm_account_overview ao
        LEFT JOIN ai_fct_account_health_score h ON ao.account_id = h.account_id
        ORDER BY ao.account_name
    """)
    return [{"id": r["account_id"], "name": r["account_name"], "health": r.get("health_band")} for r in rows]


@router.get("/accounts")
def list_accounts():
    return query("""
        SELECT
            ao.account_id
          , ao.account_name
          , ao.segment
          , ao.country
          , ao.owner_ae
          , ao.plan
          , ao.renewal_date
          , ao.current_arr_eur
          , h.health_score
          , h.health_band
          , h.days_to_renewal
          , h.usage_drop_ratio
          , h.tickets_high
          , h.unpaid_invoices
          , ae.primary_risk_driver
        FROM ai_dm_account_overview ao
        JOIN ai_fct_account_health_score h ON ao.account_id = h.account_id
        JOIN ai_arr_exposure ae ON ao.account_id = ae.account_id
        ORDER BY h.health_score ASC, ao.current_arr_eur DESC NULLS LAST
    """)


@router.get("/accounts/{account_id}")
def get_account(account_id: str):
    overview = query_one(
        "SELECT * FROM ai_dm_account_overview WHERE account_id = ?", [account_id]
    )
    if not overview:
        raise HTTPException(status_code=404, detail="Account not found")

    health = query_one(
        "SELECT * FROM ai_fct_account_health_score WHERE account_id = ?", [account_id]
    )
    expansion = query_one(
        "SELECT * FROM ai_fct_account_expansion_potential WHERE account_id = ?", [account_id]
    )
    usage_trend = query(
        """
        SELECT date_day, active_users, key_events
        FROM ai_fct_account_usage_trend
        WHERE account_id = ?
        ORDER BY date_day ASC
        """,
        [account_id],
    )
    exposure = query_one(
        "SELECT primary_risk_driver FROM ai_arr_exposure WHERE account_id = ?", [account_id]
    )

    return {
        "overview": overview,
        "health": health,
        "expansion": expansion,
        "usage_trend": usage_trend,
        "primary_risk_driver": exposure["primary_risk_driver"] if exposure else None,
    }
