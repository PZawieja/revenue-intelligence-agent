from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.db import query
from core.llm import generate_action_asset, generate_briefing

router = APIRouter(prefix="/api")


def _detect_usage_anomalies() -> list[dict]:
    return query("""
        WITH ordered AS (
            SELECT
                account_id,
                active_users,
                ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY date_day ASC)  AS rn_asc,
                ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY date_day DESC) AS rn_desc,
                COUNT(*) OVER (PARTITION BY account_id) AS total_pts
            FROM ai_fct_account_usage_trend
        ),
        early_avg AS (
            SELECT account_id, AVG(active_users) AS avg_early
            FROM ordered
            WHERE rn_asc <= 3
            GROUP BY account_id
        ),
        recent_avg AS (
            SELECT account_id, AVG(active_users) AS avg_recent
            FROM ordered
            WHERE rn_desc <= 3 AND total_pts >= 5
            GROUP BY account_id
        )
        SELECT
            e.account_id,
            ao.account_name,
            ao.current_arr_eur,
            ROUND(e.avg_early, 1)  AS avg_early,
            ROUND(r.avg_recent, 1) AS avg_recent,
            ROUND(1.0 - r.avg_recent / NULLIF(e.avg_early, 0), 2) AS drop_ratio
        FROM early_avg e
        JOIN recent_avg r ON e.account_id = r.account_id
        JOIN ai_dm_account_overview ao ON e.account_id = ao.account_id
        WHERE e.avg_early > 0 AND r.avg_recent < e.avg_early * 0.7
        ORDER BY drop_ratio DESC NULLS LAST
        LIMIT 5
    """)


@router.get("/briefing")
def get_briefing():
    arr_data = query("""
        SELECT health_band, SUM(current_arr_eur) AS arr_eur, COUNT(*) AS cnt
        FROM ai_arr_exposure
        GROUP BY health_band
        ORDER BY CASE health_band WHEN 'red' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END
    """)
    urgent_renewals = query("""
        SELECT account_name, days_to_renewal, current_arr_eur, primary_risk_driver
        FROM ai_fct_renewals_at_risk
        WHERE days_to_renewal BETWEEN 0 AND 14
        ORDER BY days_to_renewal ASC, current_arr_eur DESC NULLS LAST
        LIMIT 3
    """)
    top_expansion = query("""
        SELECT account_name, expansion_score, current_arr_eur, recommended_angle
        FROM ai_fct_expansion_shortlist
        WHERE health_score >= 0.7
        ORDER BY expansion_score DESC NULLS LAST
        LIMIT 3
    """)
    anomalies = _detect_usage_anomalies()
    return generate_briefing(arr_data, urgent_renewals, top_expansion, anomalies)


class ActionRequest(BaseModel):
    action_type: str
    intent: str
    account_name: Optional[str] = None
    narrative: str
    bullets: list[str] = []
    next_action: str = ""


@router.post("/action-asset")
def create_action_asset(req: ActionRequest):
    return generate_action_asset(
        req.action_type,
        req.intent,
        req.account_name,
        req.narrative,
        req.bullets,
        req.next_action,
    )
