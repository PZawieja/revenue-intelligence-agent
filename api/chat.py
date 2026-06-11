import duckdb
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from core.db import query, query_one, DB_PATH
from core.intent import detect_intent
from core.guardrails import compute_guardrails
from core.interpreters import interpret
from core.question_packs import FOLLOWUP_SUGGESTIONS

router = APIRouter(prefix="/api")

SQL_TEMPLATES: dict[str, str] = {
    "account_overview": """
        SELECT account_id, account_name, plan, subscription_status, renewal_date,
               current_mrr_eur, current_arr_eur, seats_purchased
        FROM ai_dm_account_overview
        WHERE lower(account_name) = lower('{account_name}')
        LIMIT 1
    """,
    "health_summary": """
        SELECT account_id, account_name, health_score, health_band,
               days_to_renewal, usage_drop_ratio, tickets_high, unpaid_invoices
        FROM ai_fct_account_health_score
        WHERE lower(account_name) = lower('{account_name}')
        LIMIT 1
    """,
    "expansion_potential": """
        SELECT account_id, account_name, health_score,
               seat_utilization_ratio, expansion_score, expansion_band
        FROM ai_fct_account_expansion_potential
        WHERE lower(account_name) = lower('{account_name}')
        LIMIT 1
    """,
    "renewals_at_risk": """
        SELECT account_id, account_name, renewal_date, days_to_renewal,
               health_score, health_band, current_arr_eur,
               usage_drop_ratio, tickets_high, unpaid_invoices, primary_risk_driver
        FROM ai_fct_renewals_at_risk
        WHERE days_to_renewal BETWEEN 0 AND {horizon_days}
          AND health_score < {health_threshold}
        ORDER BY health_score ASC, current_arr_eur DESC NULLS LAST
        LIMIT {limit_n}
    """,
    "expansion_shortlist": """
        SELECT account_id, account_name, expansion_score, current_arr_eur,
               utilization, health_score, recommended_angle, supporting_signal
        FROM ai_fct_expansion_shortlist
        WHERE health_score >= {minimum_health}
        ORDER BY expansion_score DESC NULLS LAST, current_arr_eur DESC NULLS LAST
        LIMIT {top_n}
    """,
    "arr_exposure_overview": """
        SELECT health_band
             , SUM(current_arr_eur) AS arr_eur
             , COUNT(*) AS accounts_count
        FROM ai_arr_exposure
        GROUP BY health_band
        ORDER BY CASE health_band WHEN 'green' THEN 1 WHEN 'yellow' THEN 2 WHEN 'red' THEN 3 END
    """,
}


class ChatRequest(BaseModel):
    question: str
    account_id: Optional[str] = None


@router.post("/chat")
def chat(req: ChatRequest):
    accounts_raw = query("SELECT account_id, account_name FROM ai_dm_account_overview ORDER BY account_name")
    account_names = [r["account_name"] for r in accounts_raw]
    allowed = {r["asset_name"] for r in query("SELECT asset_name FROM dim_ai_allowed_assets WHERE is_allowed_for_ai")}

    parsed = detect_intent(req.question, account_names)
    intent = parsed["intent"]

    if req.account_id and not parsed["account_name"]:
        acc = query_one("SELECT account_name FROM ai_dm_account_overview WHERE account_id = ?", [req.account_id])
        if acc:
            parsed["account_name"] = acc["account_name"]
            if "account_name" in parsed["params"]:
                parsed["params"]["account_name"] = acc["account_name"]

    needs_account = intent in ("account_overview", "health_summary", "expansion_potential")
    if needs_account and not parsed.get("account_name"):
        return {
            "intent": intent,
            "account_name": None,
            "title": "Account not found",
            "narrative": "I couldn't identify an account in your question. Try mentioning the account name, or select one from the context bar.",
            "bullets": [],
            "next_action": "",
            "followups": FOLLOWUP_SUGGESTIONS.get(intent, []),
            "evidence": {"sql": "", "guardrails": {}},
            "rows": [],
        }

    template = SQL_TEMPLATES.get(intent)
    if not template:
        return {"error": f"No template for intent: {intent}"}

    try:
        sql = template.format(**parsed["params"])
    except KeyError as e:
        return {"error": f"Missing parameter: {e}"}

    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        res = con.execute(sql)
        cols = [d[0] for d in res.description]
        rows = [dict(zip(cols, row)) for row in res.fetchall()]
        con.close()
    except Exception as exc:
        return {"error": str(exc), "intent": intent}

    guardrails = compute_guardrails(sql, allowed, (len(rows), len(cols) if cols else 0))
    interpreted = interpret(intent, rows[0] if rows else {}, rows)
    followups = FOLLOWUP_SUGGESTIONS.get(intent, [])[:3]

    return {
        "intent": intent,
        "account_name": parsed.get("account_name"),
        "title": interpreted["title"],
        "narrative": interpreted["narrative"],
        "bullets": interpreted["bullets"],
        "next_action": interpreted.get("next_action", ""),
        "followups": followups,
        "evidence": {"sql": sql.strip(), "guardrails": guardrails},
        "rows": rows,
    }
