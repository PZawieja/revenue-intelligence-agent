from __future__ import annotations
import os
from typing import Optional

import duckdb
from fastapi import APIRouter
from pydantic import BaseModel

from core.db import query, query_one, DB_PATH
from core.intent import detect_intent
from core.guardrails import compute_guardrails
from core.interpreters import interpret
from core.question_packs import FOLLOWUP_SUGGESTIONS
from core.llm import STATUS_MESSAGES, generate_insight

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
    history: list[dict] = []
    use_ai: bool = True


def _resolve_request(question: str, account_id: Optional[str]):
    accounts_raw = query("SELECT account_id, account_name FROM ai_dm_account_overview ORDER BY account_name")
    account_names = [r["account_name"] for r in accounts_raw]
    allowed = {r["asset_name"] for r in query("SELECT asset_name FROM dim_ai_allowed_assets WHERE is_allowed_for_ai")}

    parsed = detect_intent(question, account_names)
    intent = parsed["intent"]

    if account_id and not parsed["account_name"]:
        acc = query_one("SELECT account_name FROM ai_dm_account_overview WHERE account_id = ?", [account_id])
        if acc:
            parsed["account_name"] = acc["account_name"]
            if "account_name" in parsed["params"]:
                parsed["params"]["account_name"] = acc["account_name"]

    needs_account = intent in ("account_overview", "health_summary", "expansion_potential")
    if needs_account and not parsed.get("account_name"):
        return None, intent, parsed, None, allowed, "Account not identified — select one from the dropdown or mention the account name."

    template = SQL_TEMPLATES.get(intent)
    if not template:
        return None, intent, parsed, None, allowed, f"No template for intent: {intent}"

    try:
        sql = template.format(**parsed["params"])
    except KeyError as e:
        return None, intent, parsed, None, allowed, f"Missing parameter: {e}"

    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        res = con.execute(sql)
        cols = [d[0] for d in res.description]
        rows = [dict(zip(cols, row)) for row in res.fetchall()]
        con.close()
    except Exception as exc:
        return None, intent, parsed, None, allowed, str(exc)

    guardrails = compute_guardrails(sql, allowed, (len(rows), len(cols) if cols else 0))
    return rows, intent, parsed, {"sql": sql.strip(), "guardrails": guardrails}, allowed, None


@router.get("/chat/config")
def chat_config():
    return {"ai_available": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@router.get("/chat/snapshot")
def chat_snapshot():
    red = query("""
        SELECT COUNT(*) AS cnt, COALESCE(SUM(current_arr_eur), 0) AS arr
        FROM ai_arr_exposure WHERE health_band = 'red'
    """)
    urgent = query("""
        SELECT COUNT(*) AS cnt
        FROM ai_fct_renewals_at_risk
        WHERE days_to_renewal BETWEEN 0 AND 30
    """)
    urgent_next = query("""
        SELECT account_name, days_to_renewal
        FROM ai_fct_renewals_at_risk
        WHERE days_to_renewal BETWEEN 0 AND 30
        ORDER BY days_to_renewal ASC
        LIMIT 1
    """)
    exp = query("""
        SELECT COUNT(*) AS cnt,
               MAX(CASE WHEN rn = 1 THEN account_name END) AS top_name,
               MAX(CASE WHEN rn = 1 THEN expansion_score END) AS top_score
        FROM (
            SELECT account_name, expansion_score,
                   ROW_NUMBER() OVER (ORDER BY expansion_score DESC NULLS LAST) AS rn
            FROM ai_fct_expansion_shortlist
            WHERE health_score >= 0.6
        ) t
    """)
    return {
        "at_risk_count": red[0]["cnt"] if red else 0,
        "at_risk_arr": red[0]["arr"] if red else 0,
        "urgent_renewals": urgent[0]["cnt"] if urgent else 0,
        "urgent_account": urgent_next[0]["account_name"] if urgent_next else None,
        "urgent_days": urgent_next[0]["days_to_renewal"] if urgent_next else None,
        "expansion_count": exp[0]["cnt"] if exp else 0,
        "top_expansion_name": exp[0]["top_name"] if exp else None,
        "top_expansion_score": exp[0]["top_score"] if exp else None,
    }


@router.post("/chat")
def chat(req: ChatRequest):
    req.question = req.question.strip()[:400]
    rows, intent, parsed, evidence, allowed, error = _resolve_request(req.question, req.account_id)

    if error:
        return {
            "intent": intent,
            "account_name": parsed.get("account_name") if parsed else None,
            "title": "Account not identified" if "Account" in error else "Error",
            "narrative": error,
            "bullets": [],
            "next_action": "",
            "followups": FOLLOWUP_SUGGESTIONS.get(intent, []) if parsed else [],
            "evidence": {"sql": "", "guardrails": {}},
            "rows": [],
            "error": True,
        }

    insight = generate_insight(intent, rows, req.question, parsed.get("account_name"), req.history, req.use_ai)
    interpreted_title = interpret(intent, rows[0] if rows else {}, rows)["title"]

    return {
        "intent": intent,
        "account_name": parsed.get("account_name"),
        "title": interpreted_title,
        "narrative": insight.get("narrative", ""),
        "bullets": insight.get("bullets", []),
        "next_action": insight.get("next_action", ""),
        "followups": insight.get("followups", []),
        "evidence": evidence,
        "rows": rows,
        "status": STATUS_MESSAGES.get(intent, "Thinking…"),
    }
