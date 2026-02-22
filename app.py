import time
import uuid
from datetime import date, datetime
from typing import Optional

import duckdb
import pandas as pd
import streamlit as st

from scripts.ai_sql_guard import get_allowed_assets, validate_sql
from scripts.ai_intents import SQL_TEMPLATES
from scripts.ai_interpreters import INTERPRETERS
from scripts.ai_question_packs import (
    PERSONA_QUESTION_PACKS,
    PERSONA_DESCRIPTIONS,
    FOLLOWUP_SUGGESTIONS,
    QUICK_QUESTIONS_ALL,
    QUICK_QUESTIONS_GROUPED,
)
from scripts.ui_theme import inject_css, CONTRAST_AUDIT
from scripts.sql_guardrails import compute_guardrails
from scripts.response_format import (
    format_response,
    format_renewals_at_risk,
    format_expansion_shortlist,
    format_arr_exposure_overview,
)

DB_PATH = "duckdb/revenue_intel.duckdb"

INTENT_ASSET = {
    "account_overview": "ai_dm_account_overview",
    "health_summary": "ai_fct_account_health_score",
    "expansion_potential": "ai_fct_account_expansion_potential",
    "renewals_at_risk": "ai_fct_renewals_at_risk",
    "expansion_shortlist": "ai_fct_expansion_shortlist",
    "arr_exposure_overview": "ai_arr_exposure",
}


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


@st.cache_data(show_spinner=False)
def load_account_names():
    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        """
        select distinct account_name
        from ai_dm_account_overview
        order by 1
        """
    ).fetchall()
    return [r[0] for r in rows]


def detect_intent(question: str, known_names: Optional[list] = None) -> str:
    q = question.lower().strip()
    renewals_triggers = (
        "renewals at risk",
        "renewals next",
        "renewals in the next",
        "renewal risk",
        "renewals upcoming",
    )
    if any(t in q for t in renewals_triggers):
        if known_names:
            for name in known_names:
                if name.lower() in q:
                    return "account_overview"
        return "renewals_at_risk"
    arr_exposure_triggers = (
        "arr exposure",
        "revenue at risk",
        "how much arr is at risk",
        "arr by health",
        "health band revenue",
    )
    if any(t in q for t in arr_exposure_triggers):
        return "arr_exposure_overview"
    expansion_shortlist_triggers = (
        "expansion shortlist",
        "upsell candidates",
        "accounts with expansion potential",
        "top expansion",
        "where can we expand",
    )
    if any(t in q for t in expansion_shortlist_triggers):
        if known_names:
            for name in known_names:
                if name.lower() in q:
                    return "expansion_potential"
        return "expansion_shortlist"
    if "health" in q or "risk" in q:
        return "health_summary"
    if "expand" in q or "expansion" in q or "upsell" in q:
        return "expansion_potential"
    if "overview" in q or "tell me about" in q or "summary" in q:
        return "account_overview"
    return "account_overview"


def parse_renewals_params(question: str) -> tuple:
    """Return (horizon_days: int, health_threshold: float). Default 90, 0.65."""
    import re
    q = question.lower()
    horizon_days = 90
    for m in re.finditer(r"\b(30|60|90|120)\s*days?", q):
        horizon_days = int(m.group(1))
        break
    health_threshold = 0.65
    for m in re.finditer(r"0\.(\d+)", q):
        v = float("0." + m.group(1))
        if 0 < v < 1:
            health_threshold = v
            break
    return (horizon_days, health_threshold)


def parse_expansion_shortlist_params(question: str) -> tuple:
    """Return (top_n: int, minimum_health: float). Default 10, 0.6. top_n capped at 50."""
    import re
    q = question.lower()
    top_n = 10
    for m in re.finditer(r"\btop\s*(\d+)\b", q):
        top_n = min(50, max(1, int(m.group(1))))
        break
    minimum_health = 0.6
    if "health" in q and (">" in q or "above" in q or "min" in q or "0." in q):
        for m in re.finditer(r"0\.(\d+)", q):
            v = float("0." + m.group(1))
            if 0 < v < 1:
                minimum_health = v
                break
    return (top_n, minimum_health)


def parse_arr_exposure_params(question: str) -> float:
    """Return risk_threshold (health < threshold = at risk). Default 0.6."""
    import re
    q = question.lower()
    risk_threshold = 0.6
    for m in re.finditer(r"0\.(\d+)", q):
        v = float("0." + m.group(1))
        if 0 < v < 1:
            risk_threshold = v
            break
    return risk_threshold


def detect_account_name(question: str, known_names: list[str], fallback: str) -> str:
    q = question.lower()
    for name in known_names:
        if name.lower() in q:
            return name
    return fallback


def run_intent(
    con,
    allowed_assets,
    intent: str,
    account_name: str,
    renewals_params: Optional[tuple] = None,
    expansion_shortlist_params: Optional[tuple] = None,
    arr_exposure_params: Optional[float] = None,
):
    expected_asset = INTENT_ASSET.get(intent)

    if intent == "arr_exposure_overview":
        risk_threshold = arr_exposure_params if arr_exposure_params is not None else 0.6
        sql1 = SQL_TEMPLATES["arr_exposure_overview_bands"]
        sql2 = SQL_TEMPLATES["arr_exposure_overview_top"].format(risk_threshold=risk_threshold)
        expected = INTENT_ASSET["arr_exposure_overview"].lower()
        for sql in (sql1, sql2):
            ok, referenced, violations = validate_sql(sql, allowed_assets)
            if not ok:
                return {"error": f"Blocked by SQL guard: {violations}", "sql": sql, "referenced": referenced}
            if set(referenced) != {expected}:
                return {
                    "error": "Blocked: query must reference only the declared allowlisted asset.",
                    "sql": sql,
                    "referenced": referenced,
                    "expected_asset": INTENT_ASSET["arr_exposure_overview"],
                }
        start1 = time.perf_counter()
        res1 = con.execute(sql1)
        rows1 = res1.fetchall()
        cols1 = [d[0] for d in res1.description]
        runtime1 = int((time.perf_counter() - start1) * 1000)
        start2 = time.perf_counter()
        res2 = con.execute(sql2)
        rows2 = res2.fetchall()
        cols2 = [d[0] for d in res2.description]
        runtime2 = int((time.perf_counter() - start2) * 1000)
        return {
            "multi": True,
            "q1": {"sql": sql1, "cols": cols1, "rows": rows1, "runtime_ms": runtime1},
            "q2": {"sql": sql2, "cols": cols2, "rows": rows2, "runtime_ms": runtime2},
        }

    if intent not in SQL_TEMPLATES:
        return {"error": f"Unknown intent: {intent}"}

    if not expected_asset:
        return {"error": f"No asset mapping for intent: {intent}"}

    if intent == "renewals_at_risk" and renewals_params:
        horizon_days, health_threshold = renewals_params
        sql = SQL_TEMPLATES[intent].format(
            horizon_days=horizon_days,
            health_threshold=health_threshold,
            limit_n=50,
        )
    elif intent == "expansion_shortlist" and expansion_shortlist_params:
        top_n, minimum_health = expansion_shortlist_params
        sql = SQL_TEMPLATES[intent].format(
            top_n=top_n,
            minimum_health=minimum_health,
        )
    else:
        sql = SQL_TEMPLATES[intent].format(account_name=sql_escape(account_name))
    ok, referenced, violations = validate_sql(sql, allowed_assets)
    if not ok:
        return {"error": f"Blocked by SQL guard: {violations}", "sql": sql, "referenced": referenced}

    if set(referenced) != {expected_asset.lower()}:
        return {
            "error": "Blocked: query must reference only the declared allowlisted asset for this intent.",
            "sql": sql,
            "referenced": referenced,
            "expected_asset": expected_asset,
        }

    start = time.perf_counter()
    res = con.execute(sql)
    rows = res.fetchall()
    cols = [d[0] for d in res.description]
    runtime_ms = int((time.perf_counter() - start) * 1000)
    return {"sql": sql, "cols": cols, "rows": rows, "runtime_ms": runtime_ms}


def to_dataframe(cols, rows):
    return pd.DataFrame(rows, columns=cols)


def render_user_bubble(content: str):
    st.markdown(f"<div class='chat-bubble chat-bubble-user'>{content}</div>", unsafe_allow_html=True)


def _safe_value(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    return val


def _format_date(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        return val[:10]
    return str(val)


def _format_currency(val) -> Optional[str]:
    val = _safe_value(val)
    if val is None:
        return None
    try:
        return f"€{int(round(float(val)))}"
    except Exception:
        return f"€{val}"


def _format_percent(val) -> Optional[str]:
    val = _safe_value(val)
    if val is None:
        return None
    try:
        pct = float(val)
        if pct <= 1:
            pct *= 100
        return f"{int(round(pct))}%"
    except Exception:
        return None


def _days_until(date_val) -> Optional[int]:
    d = _format_date(date_val)
    if not d:
        return None
    try:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        return (dt - date.today()).days
    except Exception:
        return None


def build_kpis(intent: str, df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    row = df.iloc[0]
    kpis = []

    def add_kpi(label: str, value, tone: str = "neutral"):
        if value is None:
            return
        kpis.append({"label": label, "value": value, "tone": tone})

    if intent in {"health_summary", "risk_summary"}:
        health_score = _safe_value(row.get("health_score"))
        health_band = str(row.get("health_band") or "").lower()
        if health_score is not None:
            tone = "neutral"
            if health_band == "green":
                tone = "good"
            elif health_band == "yellow":
                tone = "warn"
            elif health_band == "red":
                tone = "bad"
            add_kpi("Health", f"{float(health_score):.2f}", tone)
        days_to_renewal = _safe_value(row.get("days_to_renewal"))
        if days_to_renewal is not None:
            tone = "warn" if int(days_to_renewal) <= 60 else "neutral"
            add_kpi("Days", f"{int(days_to_renewal)}", tone)
        usage_drop_ratio = _safe_value(row.get("usage_drop_ratio"))
        if usage_drop_ratio is not None:
            tone = "warn" if float(usage_drop_ratio) >= 0.20 else "neutral"
            add_kpi("Usage ↓", _format_percent(usage_drop_ratio), tone)
        tickets_high = _safe_value(row.get("tickets_high"))
        if tickets_high is not None:
            tone = "warn" if int(tickets_high) > 0 else "neutral"
            add_kpi("Tickets", f"{int(tickets_high)}", tone)
    elif intent in {"account_overview"}:
        add_kpi("Plan", _safe_value(row.get("plan")))
        status = _safe_value(row.get("subscription_status"))
        tone = "bad" if str(status).lower() == "cancelled" else "neutral"
        add_kpi("Status", status, tone)
        renewal_date = _format_date(_safe_value(row.get("renewal_date")))
        days = _days_until(renewal_date)
        add_kpi("Renewal", renewal_date, "warn" if days is not None and days <= 60 else "neutral")
        add_kpi("MRR", _format_currency(row.get("current_mrr_eur")))
    elif intent in {"expansion_summary", "expansion", "expansion_potential"}:
        expansion_score = _safe_value(row.get("expansion_score"))
        if expansion_score is not None:
            score = float(expansion_score)
            tone = "good" if score >= 0.7 else "warn" if score < 0.4 else "neutral"
            add_kpi("Expansion", f"{score:.2f}", tone)
        add_kpi("ARR", _format_currency(row.get("current_arr_eur")))
        seats = _safe_value(row.get("seats_purchased")) or _safe_value(row.get("seats_total"))
        add_kpi("Seats", f"{int(seats)}" if seats is not None else None)
        util = _safe_value(row.get("seat_utilization_pct")) or _safe_value(
            row.get("seat_utilization_ratio")
        )
        if util is not None:
            tone = "warn" if float(util) >= 0.85 else "neutral"
            add_kpi("Utilization", _format_percent(util), tone)
    elif intent == "renewals_at_risk":
        add_kpi("Renewals", len(df), "neutral")
        health_col = "health_score"
        threshold = 0.65
        high_risk = df[df[health_col].astype(float) < threshold] if health_col in df.columns else df
        add_kpi("High risk", len(high_risk), "bad" if len(high_risk) > 0 else "neutral")
        arr_col = "current_arr_eur"
        if arr_col in df.columns:
            at_risk_arr = high_risk[arr_col].sum() if not high_risk.empty else 0
            add_kpi("ARR at risk", _format_currency(at_risk_arr), "warn" if at_risk_arr else "neutral")
        days_col = "days_to_renewal"
        if days_col in df.columns:
            med = df[days_col].dropna().median()
            add_kpi("Median days", f"{int(med)}" if med == med else None, "neutral")

    return kpis[:4]


def build_so_what(intent: str, df: pd.DataFrame) -> str:
    if intent == "health_summary":
        if df is not None and not df.empty:
            row = df.iloc[0]
            days = _safe_value(row.get("days_to_renewal"))
            usage = _safe_value(row.get("usage_drop_ratio"))
            if days is not None and int(days) <= 60:
                return "Proactively reach out before renewal and address the main risk driver."
            if usage is not None and float(usage) >= 0.20:
                return "Investigate usage decline and confirm adoption plan with the customer."
        return "Monitor health signals and plan renewal outreach in advance."
    if intent == "account_overview":
        return "Use this to confirm renewal timing, current value, and plan context."
    if intent in {"expansion_summary", "expansion", "expansion_potential"}:
        if df is not None and not df.empty:
            score = _safe_value(df.iloc[0].get("expansion_score"))
            if score is not None and float(score) >= 0.7:
                return "This looks like a strong expansion candidate—review seats and product fit for upsell."
        return "Validate expansion drivers and identify 1–2 concrete upsell angles."
    return "Use this summary to decide the next best action."


st.set_page_config(page_title="Revenue Intelligence", layout="wide", initial_sidebar_state="expanded")
inject_css()
st.markdown("<div class='app-container'>", unsafe_allow_html=True)
st.markdown(
    "<div class='ri-hero'><h1>Revenue Intelligence</h1><p class='ri-hero-sub'>Ask about accounts, health, renewals, and expansion. Answers use verified data only.</p></div>",
    unsafe_allow_html=True,
)
if CONTRAST_AUDIT:
    st.warning("Readability audit enabled")

known_accounts = load_account_names()
PERSONAS = list(PERSONA_QUESTION_PACKS.keys())

with st.sidebar:
    st.markdown("**Session**")
    if "persona" not in st.session_state:
        st.session_state.persona = PERSONAS[0]
    persona = st.selectbox(
        "Persona",
        PERSONAS,
        index=PERSONAS.index(st.session_state.persona),
        key="persona_select",
        help="Affects suggested follow-ups and talk tracks.",
    )
    st.session_state.persona = persona
    selected_account = st.selectbox(
        "Default account",
        known_accounts,
        index=0,
        key="default_account_select",
        help="Used when your question doesn’t mention an account by name.",
    )
    st.markdown("---")
    if st.button("New chat", type="primary", use_container_width=True, key="new_chat_button"):
        st.session_state.pop("messages", None)
        st.session_state.pop("queued_question", None)
        st.session_state.pop("evidence_by_msg_id", None)
        st.session_state.pop("details_open", None)
        st.session_state.has_interacted = False
        st.session_state.quick_questions_open = False
        st.rerun()

def new_msg_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "id": new_msg_id("asst"),
            "role": "assistant",
            "content": {
                "title": "Welcome",
                "kpis": [],
                "summary": "Pick a question below or type your own. For a single account, we’ll use your default account if you don’t name one.",
                "key_points": [],
                "next_best_action": "",
                "talk_track": None,
                "followups": [],
            },
        }
    ]
if "evidence_by_msg_id" not in st.session_state:
    st.session_state.evidence_by_msg_id = {}
if "details_open" not in st.session_state:
    st.session_state.details_open = {}
if "has_interacted" not in st.session_state:
    st.session_state.has_interacted = False
if "quick_questions_open" not in st.session_state:
    st.session_state.quick_questions_open = False

# Keep has_interacted in sync with history
if not st.session_state.has_interacted:
    if any(m.get("role") == "user" for m in st.session_state.get("messages", [])):
        st.session_state.has_interacted = True

# Quick questions: grouped by "One account" vs "Portfolio" for clarity.
if not st.session_state.has_interacted:
    with st.expander("Start with a question", expanded=True):
        st.caption("Choose one or type your own in the box below.")
        for group_label, questions in QUICK_QUESTIONS_GROUPED.items():
            st.markdown(f"<div class='ri-section-label'>{group_label}</div>", unsafe_allow_html=True)
            st.markdown("<div class='tile-grid'>", unsafe_allow_html=True)
            tile_cols = st.columns(3)
            for idx, q in enumerate(questions):
                with tile_cols[idx % 3]:
                    if st.button(q, key=f"quick-tile-{group_label}-{idx}"):
                        st.session_state["queued_question"] = q
                        st.session_state.has_interacted = True
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

last_assistant_id = None
for m in st.session_state.messages:
    if m["role"] == "assistant":
        last_assistant_id = m.get("id")

for msg in st.session_state.messages:
    msg_id = msg.get("id")
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown("<div class='message-row'>", unsafe_allow_html=True)
            cols = st.columns([0.05, 0.95])
            with cols[0]:
                st.markdown("<div class='badge badge-human'></div>", unsafe_allow_html=True)
            with cols[1]:
                render_user_bubble(msg["content"])
            st.markdown("</div>", unsafe_allow_html=True)
        continue

    with st.chat_message("assistant"):
        content = msg.get("content", {})
        if isinstance(content, dict):
            title = content.get("title", "Answer")
            kpis = content.get("kpis", [])
            summary = content.get("summary", "")
            key_points = content.get("key_points", [])
            next_best_action = content.get("next_best_action", "")
            talk_track = content.get("talk_track")
            followups = content.get("followups", [])
        else:
            title = str(content)
            kpis = []
            summary = ""
            key_points = []
            next_best_action = "Use this summary to decide the next best action."
            talk_track = None
            followups = []
        ev = st.session_state.evidence_by_msg_id.get(msg_id, {})
        header_title = title
        persona = st.session_state.get("persona", "Customer Success")

        st.markdown("<div class='answer-card'>", unsafe_allow_html=True)
        is_welcome = header_title == "Welcome"
        if is_welcome:
            st.markdown("<div class='answer-title'>Welcome</div>", unsafe_allow_html=True)
        else:
            header_cols = st.columns([0.76, 0.24])
            with header_cols[0]:
                st.markdown(
                    f"<div class='answer-title'>{header_title} <span class='badge-governed'>Verified data</span></div>",
                    unsafe_allow_html=True,
                )
            with header_cols[1]:
                is_open = st.session_state.details_open.get(msg_id, False)
                label = "Data & SQL ▴" if is_open else "Data & SQL ▾"
                if st.button(label, key=f"details_toggle_{msg_id}", type="secondary"):
                    st.session_state.details_open[msg_id] = not is_open
                    st.rerun()

        if kpis:
            chips_html = "".join(
                [
                    f"<span class='kpi-chip kpi-{c.get('tone','neutral')}'>{c['label']}: {c['value']}</span>"
                    for c in kpis[:4]
                ]
            )
            st.markdown(f"<div class='kpi-row'>{chips_html}</div>", unsafe_allow_html=True)

        if summary:
            st.markdown(f"<div class='answer-summary'>{summary}</div>", unsafe_allow_html=True)
        key_points_html = "".join([f"<li>{b}</li>" for b in key_points[:3]])
        if key_points_html:
            st.markdown(f"<ul class='answer-list'>{key_points_html}</ul>", unsafe_allow_html=True)
        if next_best_action:
            st.markdown(
                f"<div class='next-best-action'><strong>Next best action</strong> {next_best_action}</div>",
                unsafe_allow_html=True,
            )
        if talk_track and persona == "Customer Success":
            st.markdown(
                f"<div class='talk-track'>What to say: “{talk_track}”</div>",
                unsafe_allow_html=True,
            )
        if followups:
            if len(followups) > 1:
                st.markdown(
                    "<div class='suggestion-label'>Suggested next questions</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("<div class='suggestion-row'>", unsafe_allow_html=True)
            for s_idx, q in enumerate(followups[:3]):
                if st.button(q, key=f"sugg_{msg_id}_{s_idx}"):
                    st.session_state["queued_question"] = q
                    st.session_state.has_interacted = True
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if ev.get("intent") == "renewals_at_risk" and ev.get("df") is not None and not ev["df"].empty:
            st.markdown(
                "<div class='answer-summary' style='color:#666;font-size:0.9em;'>Click an account to open the account view.</div>",
                unsafe_allow_html=True,
            )
            disp = ev["df"][
                [c for c in ["account_name", "renewal_date", "days_to_renewal", "health_score", "current_arr_eur", "primary_risk_driver"] if c in ev["df"].columns]
            ].copy()
            disp["days_to_renewal"] = disp["days_to_renewal"].fillna(0).astype(int)
            if "health_score" in disp.columns:
                disp["health_score"] = disp["health_score"].round(2)
            if "current_arr_eur" in disp.columns:
                disp["current_arr_eur"] = disp["current_arr_eur"].apply(lambda x: f"€{x:,.0f}" if x == x and x is not None else "—")
            st.dataframe(disp, height=320, use_container_width=True, hide_index=True)
            account_names = ev["df"]["account_name"].dropna().astype(str).unique().tolist() if "account_name" in ev["df"].columns else []
            open_label = "Open account"
            options = ["— Select —"] + account_names
            select_key = f"open_account_{msg_id}"
            prev_key = f"open_account_prev_{msg_id}"
            idx = st.selectbox(
                open_label,
                options=options,
                key=select_key,
                label_visibility="visible",
            )
            prev = st.session_state.get(prev_key, "— Select —")
            if idx and idx != "— Select —" and prev != idx:
                st.session_state["queued_question"] = f"Open account overview for {idx}"
                st.session_state[prev_key] = idx
                st.session_state.has_interacted = True
                st.rerun()
            st.session_state[prev_key] = idx

        if ev.get("intent") == "expansion_shortlist" and ev.get("df") is not None and not ev["df"].empty:
            st.markdown(
                "<div class='answer-summary' style='color:#666;font-size:0.9em;'>Click an account to open the account view.</div>",
                unsafe_allow_html=True,
            )
            disp_cols = [c for c in ["account_name", "expansion_score", "current_arr_eur", "utilization", "health_score", "recommended_angle"] if c in ev["df"].columns]
            disp = ev["df"][disp_cols].copy()
            if "expansion_score" in disp.columns:
                disp["expansion_score"] = disp["expansion_score"].round(2)
            if "utilization" in disp.columns:
                disp["utilization"] = disp["utilization"].apply(lambda x: f"{float(x)*100:.0f}%" if x == x and x is not None else "—")
            if "health_score" in disp.columns:
                disp["health_score"] = disp["health_score"].round(2)
            if "current_arr_eur" in disp.columns:
                disp["current_arr_eur"] = disp["current_arr_eur"].apply(lambda x: f"€{x:,.0f}" if x == x and x is not None else "—")
            st.dataframe(disp, height=320, use_container_width=True, hide_index=True)
            account_names = ev["df"]["account_name"].dropna().astype(str).unique().tolist() if "account_name" in ev["df"].columns else []
            options = ["— Select —"] + account_names
            prev_key = f"open_account_prev_{msg_id}"
            idx = st.selectbox(
                "Open account",
                options=options,
                key=f"open_account_exp_{msg_id}",
                label_visibility="visible",
            )
            prev = st.session_state.get(prev_key, "— Select —")
            if idx and idx != "— Select —" and prev != idx:
                st.session_state["queued_question"] = f"Open account overview for {idx}"
                st.session_state[prev_key] = idx
                st.session_state.has_interacted = True
                st.rerun()
            st.session_state[prev_key] = idx

        if ev.get("intent") == "arr_exposure_overview":
            df_bands = ev.get("df_bands")
            if df_bands is not None and not df_bands.empty:
                total = df_bands["arr_eur"].sum() if "arr_eur" in df_bands.columns else 1
                disp_bands = df_bands.copy()
                disp_bands["share_of_arr"] = (100.0 * disp_bands["arr_eur"] / total).round(1).astype(str) + "%"
                disp_bands["arr_eur"] = disp_bands["arr_eur"].apply(lambda x: f"€{x:,.0f}" if x == x and x is not None else "—")
                st.markdown(
                    "<div class='answer-summary' style='color:#666;font-size:0.9em;'>ARR by health band</div>",
                    unsafe_allow_html=True,
                )
                st.dataframe(disp_bands, height=140, use_container_width=True, hide_index=True)
            df_top = ev.get("df")
            if df_top is not None and not df_top.empty:
                st.markdown(
                    "<div class='answer-summary' style='color:#666;font-size:0.9em;'>Top ARR at risk</div>",
                    unsafe_allow_html=True,
                )
                disp_top = df_top[
                    [c for c in ["account_name", "health_score", "current_arr_eur", "primary_risk_driver"] if c in df_top.columns]
                ].copy()
                if "health_score" in disp_top.columns:
                    disp_top["health_score"] = disp_top["health_score"].round(2)
                if "current_arr_eur" in disp_top.columns:
                    disp_top["current_arr_eur"] = disp_top["current_arr_eur"].apply(lambda x: f"€{x:,.0f}" if x == x and x is not None else "—")
                st.dataframe(disp_top, height=220, use_container_width=True, hide_index=True)
                account_names = df_top["account_name"].dropna().astype(str).unique().tolist() if "account_name" in df_top.columns else []
                options = ["— Select —"] + account_names
                prev_key = f"open_account_prev_{msg_id}"
                idx = st.selectbox(
                    "Open account",
                    options=options,
                    key=f"open_account_arr_{msg_id}",
                    label_visibility="visible",
                )
                prev = st.session_state.get(prev_key, "— Select —")
                if idx and idx != "— Select —" and prev != idx:
                    st.session_state["queued_question"] = f"Open account overview for {idx}"
                    st.session_state[prev_key] = idx
                    st.session_state.has_interacted = True
                    st.rerun()
                st.session_state[prev_key] = idx
            elif df_bands is not None and not df_bands.empty:
                st.markdown(
                    "<div class='answer-summary' style='color:#666;font-size:0.9em;'>No accounts in at-risk band (top list empty).</div>",
                    unsafe_allow_html=True,
                )

        if st.session_state.details_open.get(msg_id, False):
            st.markdown("<div class='details-section'>", unsafe_allow_html=True)
            tab = st.radio(
                "Evidence",
                ["Data", "SQL", "Definitions", "Debug"],
                help="Inspect the data, query, and how the answer was built.",
                key=f"tabs_{msg_id}",
                horizontal=True,
                label_visibility="collapsed",
            )
            if tab == "Data":
                if ev.get("intent") == "arr_exposure_overview":
                    df_bands = ev.get("df_bands")
                    df_top = ev.get("df")
                    if df_bands is not None and not df_bands.empty:
                        st.markdown("**Q1: By health band**")
                        st.dataframe(df_bands.head(10), height=120, use_container_width=True)
                    if df_top is not None and not df_top.empty:
                        st.markdown("**Q2: Top ARR at risk**")
                        st.dataframe(df_top.head(10), height=200, use_container_width=True)
                    if (df_bands is None or df_bands.empty) and (df_top is None or df_top.empty):
                        st.markdown("No rows returned.")
                else:
                    df = ev.get("df")
                    if df is not None and not df.empty:
                        st.dataframe(df.head(15), height=260, use_container_width=True)
                    else:
                        st.markdown("No rows returned.")
            elif tab == "SQL":
                if ev.get("intent") == "arr_exposure_overview":
                    g1, g2 = ev.get("guardrails", {}), ev.get("guardrails_q2", {})
                    for label, guardrails, sql in [
                        ("Q1 (bands)", g1, ev.get("sql", "")),
                        ("Q2 (top at risk)", g2, ev.get("sql_q2", "")),
                    ]:
                        st.markdown(f"**{label}**")
                        if guardrails:
                            select_ok = guardrails.get("select_only", False)
                            allow_ok = guardrails.get("allowlisted_assets", False)
                            limit_ok = guardrails.get("row_limit_present", False)
                            st.markdown(f"{'✅' if select_ok else '⚠️'} Select-only · {'✅' if allow_ok else '⚠️'} Allowlisted · {'✅' if limit_ok else '⚠️'} LIMIT")
                        st.code(sql, language="sql")
                        st.markdown("")
                else:
                    guardrails = ev.get("guardrails", {})
                if guardrails and ev.get("intent") != "arr_exposure_overview":
                    issues = []
                    select_ok = guardrails.get("select_only", False)
                    allow_ok = guardrails.get("allowlisted_assets", False)
                    limit_ok = guardrails.get("row_limit_present", False)
                    pii_ok = guardrails.get("no_pii_columns", False)
                    blocked = guardrails.get("blocked_keywords_found", [])
                    if select_ok:
                        st.markdown("✅ Select-only query")
                    else:
                        st.markdown("⚠️ Non-select keywords detected")
                    if allow_ok:
                        st.markdown("✅ Uses allowlisted tables")
                    else:
                        tables = guardrails.get("tables_used", [])
                        st.markdown(f"⚠️ Non-allowlisted tables: {', '.join(tables) if tables else 'none'}")
                    if limit_ok:
                        limit_val = guardrails.get("row_limit_value")
                        suffix = f"(LIMIT {limit_val})" if limit_val is not None else "(LIMIT)"
                        st.markdown(f"✅ Row limit enforced {suffix}")
                    else:
                        st.markdown("⚠️ No LIMIT clause found")
                    if pii_ok:
                        st.markdown("✅ No PII columns selected")
                    else:
                        st.markdown("⚠️ Potential PII columns detected")
                    if blocked:
                        st.markdown(f"⚠️ Blocked keywords: {', '.join(blocked)}")
                    rows = guardrails.get("result_rows", 0)
                    cols = guardrails.get("result_cols", 0)
                    st.markdown(
                        f"<div class='guardrail-meta'>Returned: {rows} rows × {cols} columns</div>",
                        unsafe_allow_html=True,
                    )
                if ev.get("intent") != "arr_exposure_overview":
                    if st.button("Copy SQL", key=f"copy-sql-{msg_id}", type="secondary"):
                        st.toast("SQL ready to copy from below.")
                    st.code(ev.get("sql", ""), language="sql")
            elif tab == "Definitions":
                definitions = ev.get("definitions", [])
                if definitions:
                    for item in definitions:
                        st.markdown(f"- {item}")
                else:
                    st.markdown("No definitions available.")
            elif tab == "Debug":
                debug = ev.get("debug", {})
                if isinstance(debug, dict):
                    for k, v in debug.items():
                        st.markdown(f"- {k}: {v}")
                else:
                    st.markdown(str(debug) if debug else "No debug info.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

# Persistent chip strip: high-level options always visible above input (recognition over recall).
QUICK_CHIP_STRIP = [
    "Give me an account overview",
    "Is this account healthy?",
    "Show renewals at risk in the next 90 days",
    "ARR exposure by health band",
]
st.markdown("<div class='ri-chip-strip'>", unsafe_allow_html=True)
for idx, q in enumerate(QUICK_CHIP_STRIP):
    if st.button(q, key=f"chip-strip-{idx}"):
        st.session_state["queued_question"] = q
        st.session_state.has_interacted = True
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

question = st.chat_input(
    "Ask about an account or portfolio…",
    key="chat_input",
)
if st.session_state.has_interacted:
    st.markdown("<div class='quick-link'>", unsafe_allow_html=True)
    if hasattr(st, "popover"):
        with st.popover("All questions"):
            st.caption("One account or portfolio.")
            st.markdown("<div class='quickq-popover'>", unsafe_allow_html=True)
            st.markdown("<div class='quickq-row'>", unsafe_allow_html=True)
            for idx, q in enumerate(QUICK_QUESTIONS_ALL):
                if st.button(q, key=f"quick-pop-{idx}"):
                    st.session_state["queued_question"] = q
                    st.session_state.has_interacted = True
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        if st.button("All questions", key="quick-toggle-link", type="secondary"):
            st.session_state.quick_questions_open = not st.session_state.quick_questions_open
        if st.session_state.quick_questions_open:
            st.caption("One account or portfolio.")
            st.markdown("<div class='quickq-popover'>", unsafe_allow_html=True)
            st.markdown("<div class='quickq-row'>", unsafe_allow_html=True)
            for idx, q in enumerate(QUICK_QUESTIONS_ALL):
                if st.button(q, key=f"quick-mini-{idx}"):
                    st.session_state["queued_question"] = q
                    st.session_state.has_interacted = True
                    st.session_state.quick_questions_open = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
if not question and st.session_state.get("queued_question"):
    question = st.session_state.pop("queued_question")
if question:
    st.session_state.has_interacted = True
    user_id = new_msg_id("user")
    st.session_state.messages.append({"id": user_id, "role": "user", "content": question})
    with st.spinner("Thinking…"):
        con = duckdb.connect(DB_PATH)
        allowed_assets = get_allowed_assets(con)

        intent = detect_intent(question, known_accounts)
        account_name = detect_account_name(question, known_accounts, selected_account)
        renewals_params = parse_renewals_params(question) if intent == "renewals_at_risk" else None
        expansion_shortlist_params = (
            parse_expansion_shortlist_params(question) if intent == "expansion_shortlist" else None
        )
        arr_exposure_params = (
            parse_arr_exposure_params(question) if intent == "arr_exposure_overview" else None
        )
        result = run_intent(
            con,
            allowed_assets,
            intent,
            account_name,
            renewals_params=renewals_params,
            expansion_shortlist_params=expansion_shortlist_params,
            arr_exposure_params=arr_exposure_params,
        )

    if "error" in result:
        assistant_id = new_msg_id("asst")
        guardrails = {}
        if result.get("sql"):
            guardrails = compute_guardrails(result.get("sql", ""), allowed_assets, (0, 0))
        st.session_state.messages.append(
            {
                "id": assistant_id,
                "role": "assistant",
                "content": {
                    "title": "Something went wrong",
                    "kpis": [],
                    "summary": str(result["error"]),
                    "key_points": [],
                    "next_best_action": "Check the query or try a different question.",
                    "talk_track": None,
                    "followups": [],
                },
            }
        )
        st.session_state.evidence_by_msg_id[assistant_id] = {
            "df": None,
            "sql": result.get("sql", ""),
            "definitions": [],
            "debug": {
                "intent": intent,
                "asset": INTENT_ASSET.get(intent, ""),
                "row_count": 0,
                "runtime_ms": result.get("runtime_ms", 0),
            },
            "guardrails": guardrails,
            "intent": intent,
            "account_name": account_name,
            "row0": {},
        }
        st.session_state.details_open[assistant_id] = False
        st.rerun()
    else:
        if result.get("multi"):
            q1, q2 = result["q1"], result["q2"]
            df_bands = to_dataframe(q1["cols"], q1["rows"]) if q1["rows"] else None
            df_top = to_dataframe(q2["cols"], q2["rows"]) if q2["rows"] else None
            risk_threshold = arr_exposure_params if arr_exposure_params is not None else 0.6
            persona = st.session_state.get("persona", "Customer Success")
            content = format_arr_exposure_overview(df_bands, df_top, risk_threshold, persona)
            assistant_id = new_msg_id("asst")
            st.session_state.messages.append(
                {"id": assistant_id, "role": "assistant", "content": content}
            )
            guardrails1 = compute_guardrails(q1["sql"], allowed_assets, (len(q1["rows"]), len(q1["cols"])))
            guardrails2 = compute_guardrails(q2["sql"], allowed_assets, (len(q2["rows"]), len(q2["cols"])))
            st.session_state.evidence_by_msg_id[assistant_id] = {
                "df": df_top,
                "df_bands": df_bands,
                "sql": q1["sql"],
                "sql_q2": q2["sql"],
                "definitions": [
                    "Health bands: green = health >= 0.8, yellow = 0.6–0.8, red = health < 0.6.",
                    f"At risk = health score < {risk_threshold}.",
                ],
                "debug": {
                    "intent": intent,
                    "asset": INTENT_ASSET.get(intent, ""),
                    "risk_threshold": risk_threshold,
                    "q1_rows": len(q1["rows"]),
                    "q2_rows": len(q2["rows"]),
                    "q1_runtime_ms": q1["runtime_ms"],
                    "q2_runtime_ms": q2["runtime_ms"],
                },
                "guardrails": guardrails1,
                "guardrails_q2": guardrails2,
                "intent": intent,
                "account_name": None,
                "row0": {},
            }
            st.session_state.details_open[assistant_id] = False
            st.rerun()
        cols, rows = result.get("cols", []), result.get("rows", [])
        df = to_dataframe(cols, rows) if rows else None
        if intent == "renewals_at_risk" and df is not None:
            horizon_days, health_threshold = renewals_params or (90, 0.65)
            persona = st.session_state.get("persona", "Customer Success")
            content = format_renewals_at_risk(df, horizon_days, health_threshold, persona)
            assistant_id = new_msg_id("asst")
            st.session_state.messages.append(
                {"id": assistant_id, "role": "assistant", "content": content}
            )
            guardrails = compute_guardrails(result["sql"], allowed_assets, (len(df), len(df.columns)))
            st.session_state.evidence_by_msg_id[assistant_id] = {
                "df": df,
                "sql": result["sql"],
                "definitions": [
                    f"High risk = health score < {health_threshold}",
                    f"Horizon = {horizon_days} days",
                ],
                "debug": {
                    "intent": intent,
                    "asset": INTENT_ASSET.get(intent, ""),
                    "row_count": len(rows),
                    "runtime_ms": result.get("runtime_ms", 0),
                    "horizon_days": horizon_days,
                    "health_threshold": health_threshold,
                    "limit_n": 50,
                },
                "guardrails": guardrails,
                "intent": intent,
                "account_name": None,
                "row0": {},
                "renewals_params": renewals_params,
            }
            st.session_state.details_open[assistant_id] = False
            st.rerun()
        elif intent == "expansion_shortlist" and df is not None:
            top_n, minimum_health = expansion_shortlist_params or (10, 0.6)
            persona = st.session_state.get("persona", "Customer Success")
            content = format_expansion_shortlist(df, top_n, minimum_health, persona)
            assistant_id = new_msg_id("asst")
            st.session_state.messages.append(
                {"id": assistant_id, "role": "assistant", "content": content}
            )
            guardrails = compute_guardrails(result["sql"], allowed_assets, (len(df), len(df.columns)))
            st.session_state.evidence_by_msg_id[assistant_id] = {
                "df": df,
                "sql": result["sql"],
                "definitions": [
                    "Expansion score = 0.5 × health_score + 0.5 × seat_utilization_ratio (0–1).",
                    f"Candidate criteria: health >= {minimum_health}, top_n = {top_n}.",
                ],
                "debug": {
                    "intent": intent,
                    "asset": INTENT_ASSET.get(intent, ""),
                    "row_count": len(rows),
                    "runtime_ms": result.get("runtime_ms", 0),
                    "top_n": top_n,
                    "minimum_health": minimum_health,
                },
                "guardrails": guardrails,
                "intent": intent,
                "account_name": None,
                "row0": {},
                "expansion_shortlist_params": expansion_shortlist_params,
            }
            st.session_state.details_open[assistant_id] = False
            st.rerun()
        elif rows and intent in INTERPRETERS:
            row0 = dict(zip(cols, rows[0]))
            interpretation = INTERPRETERS[intent](row0)
            kpis = build_kpis(intent, df)
            raw_result = {"row0": row0, "interpretation": interpretation, "df": df}
            persona = st.session_state.get("persona", "Customer Success")
            content = format_response(
                intent,
                raw_result,
                persona,
                account_name,
                kpis,
                current_question=question,
            )
            assistant_id = new_msg_id("asst")
            st.session_state.messages.append(
                {"id": assistant_id, "role": "assistant", "content": content}
            )
            guardrails = compute_guardrails(result["sql"], allowed_assets, (len(df), len(df.columns)))
            st.session_state.evidence_by_msg_id[assistant_id] = {
                "df": df,
                "sql": result["sql"],
                "definitions": interpretation.get("definitions", []),
                "debug": {
                    "intent": intent,
                    "asset": INTENT_ASSET.get(intent, ""),
                    "row_count": len(rows),
                    "runtime_ms": result.get("runtime_ms", 0),
                },
                "guardrails": guardrails,
                "intent": intent,
                "account_name": account_name,
                "row0": row0,
            }
            st.session_state.details_open[assistant_id] = False
            st.rerun()
        else:
            assistant_id = new_msg_id("asst")
            st.session_state.messages.append(
                {
                    "id": assistant_id,
                    "role": "assistant",
                    "content": {
                        "title": "No results",
                        "kpis": [],
                        "summary": "No rows matched this question.",
                        "key_points": [],
                        "next_best_action": "Try another account or question.",
                        "talk_track": None,
                        "followups": [],
                    },
                }
            )
            df = to_dataframe(cols, rows) if rows else None
            guardrails = compute_guardrails(result["sql"], allowed_assets, (len(rows), len(cols)))
            st.session_state.evidence_by_msg_id[assistant_id] = {
                "df": df,
                "sql": result["sql"],
                "definitions": [],
                "debug": {
                    "intent": intent,
                    "asset": INTENT_ASSET.get(intent, ""),
                    "row_count": len(rows),
                    "runtime_ms": result.get("runtime_ms", 0),
                },
                "guardrails": guardrails,
                "intent": intent,
                "account_name": account_name,
                "row0": {},
            }
            st.session_state.details_open[assistant_id] = False
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
