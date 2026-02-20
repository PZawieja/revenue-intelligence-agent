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
)
from scripts.ui_theme import inject_css, CONTRAST_AUDIT

DB_PATH = "duckdb/revenue_intel.duckdb"

INTENT_ASSET = {
    "account_overview": "ai_dm_account_overview",
    "health_summary": "ai_fct_account_health_score",
    "expansion_potential": "ai_fct_account_expansion_potential",
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


def detect_intent(question: str) -> str:
    q = question.lower().strip()
    if "health" in q or "risk" in q:
        return "health_summary"
    if "expand" in q or "expansion" in q or "upsell" in q:
        return "expansion_potential"
    if "overview" in q or "tell me about" in q or "summary" in q:
        return "account_overview"
    return "account_overview"


def detect_account_name(question: str, known_names: list[str], fallback: str) -> str:
    q = question.lower()
    for name in known_names:
        if name.lower() in q:
            return name
    return fallback


def run_intent(con, allowed_assets, intent: str, account_name: str):
    if intent not in SQL_TEMPLATES:
        return {"error": f"Unknown intent: {intent}"}

    expected_asset = INTENT_ASSET.get(intent)
    if not expected_asset:
        return {"error": f"No asset mapping for intent: {intent}"}

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


st.set_page_config(page_title="Revenue Intelligence Agent", layout="wide")
inject_css()
st.markdown("<div class='app-container'>", unsafe_allow_html=True)
st.markdown("### Revenue Intelligence")
st.markdown(
    "<p class='ri-subtitle'>Ask about ARR/MRR, renewals, health and expansion — governed SQL.</p>",
    unsafe_allow_html=True,
)
if CONTRAST_AUDIT:
    st.warning("Readability audit enabled")

known_accounts = load_account_names()
PERSONAS = list(PERSONA_QUESTION_PACKS.keys())

with st.sidebar:
    st.header("Context")
    if "persona" not in st.session_state:
        st.session_state.persona = PERSONAS[0]
    persona = st.selectbox(
        "Persona",
        PERSONAS,
        index=PERSONAS.index(st.session_state.persona),
        key="persona_select",
    )
    st.session_state.persona = persona
    selected_account = st.selectbox(
        "Default account",
        known_accounts,
        index=0,
        key="default_account_select",
    )
    if st.button("New chat", type="primary", use_container_width=True, key="new_chat_button"):
        st.session_state.pop("messages", None)
        st.session_state.pop("queued_question", None)
        st.session_state.pop("evidence_by_msg_id", None)
        st.session_state.pop("details_open", None)
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
                "bullets": [
                    "Ask about account overview, health, or expansion.",
                    "Use the default account if you omit a name.",
                ],
                "so_what": "Start with an account overview to get context.",
                "kpis": [],
                "followups": [],
            },
        }
    ]
if "evidence_by_msg_id" not in st.session_state:
    st.session_state.evidence_by_msg_id = {}
if "details_open" not in st.session_state:
    st.session_state.details_open = {}

show_quick = not any(m["role"] == "user" for m in st.session_state.messages)
if show_quick:
    with st.expander(f"Quick questions for {st.session_state.persona}", expanded=True):
        st.markdown("<div class='tile-grid'>", unsafe_allow_html=True)
        question_tiles = PERSONA_QUESTION_PACKS.get(st.session_state.persona, [])
        primary_tiles = question_tiles[:6]
        extra_tiles = question_tiles[6:]
        tile_cols = st.columns(3)
        for idx, q in enumerate(primary_tiles):
            with tile_cols[idx % 3]:
                if st.button(q, key=f"quick-tile-{idx}"):
                    st.session_state["queued_question"] = q
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        if extra_tiles:
            with st.expander("Show more"):
                extra_cols = st.columns(3)
                st.markdown("<div class='tile-grid'>", unsafe_allow_html=True)
                for idx, q in enumerate(extra_tiles):
                    with extra_cols[idx % 3]:
                        if st.button(q, key=f"quick-tile-extra-{idx}"):
                            st.session_state["queued_question"] = q
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
            bullets = content.get("bullets", [])
            so_what = content.get("so_what", "Use this summary to decide the next best action.")
            kpis = content.get("kpis", [])
        else:
            title = str(content)
            bullets = []
            so_what = "Use this summary to decide the next best action."
            kpis = []
        ev = st.session_state.evidence_by_msg_id.get(msg_id, {})
        header_title = title

        st.markdown("<div class='answer-card'>", unsafe_allow_html=True)
        header_cols = st.columns([0.78, 0.22])
        with header_cols[0]:
            st.markdown(f"<div class='answer-title'>{header_title}</div>", unsafe_allow_html=True)
        with header_cols[1]:
            has_details = bool(ev.get("sql") or ev.get("df") is not None or ev.get("definitions"))
            if has_details:
                is_open = st.session_state.details_open.get(msg_id, False)
                label = "Details ▴" if is_open else "Details ▾"
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

        bullets_html = "".join([f"<li>{b}</li>" for b in bullets[:4]])
        if bullets_html:
            st.markdown(f"<ul class='answer-list'>{bullets_html}</ul>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='answer-muted'>No summary available.</div>", unsafe_allow_html=True)

        st.markdown(f"<div class='so-what'>{so_what}</div>", unsafe_allow_html=True)

        if msg_id == last_assistant_id and ev.get("intent"):
            base_suggestions = FOLLOWUP_SUGGESTIONS.get(ev.get("intent", ""), [])
            persona_pack = PERSONA_QUESTION_PACKS.get(st.session_state.persona, [])
            suggestions = [q for q in base_suggestions if q in persona_pack]
            if len(suggestions) < 4:
                for q in persona_pack:
                    if q not in suggestions:
                        suggestions.append(q)
                    if len(suggestions) >= 4:
                        break
            if suggestions:
                st.markdown("<div class='pill'>", unsafe_allow_html=True)
                for s_idx, q in enumerate(suggestions[:4]):
                    if st.button(q, key=f"suggest-{msg_id}-{s_idx}-{abs(hash(q))}"):
                        st.session_state["queued_question"] = q
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.details_open.get(msg_id, False):
            st.markdown("<div class='details-section'>", unsafe_allow_html=True)
            tab = st.radio(
                "Details",
                ["Results", "SQL", "Definitions", "Debug"],
                key=f"tabs_{msg_id}",
                horizontal=True,
                label_visibility="collapsed",
            )
            if tab == "Results":
                df = ev.get("df")
                if df is not None and not df.empty:
                    st.dataframe(df.head(15), height=260, use_container_width=True)
                else:
                    st.markdown("No rows returned.")
            elif tab == "SQL":
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

question = st.chat_input(
    "Type your question… (use the default account if you omit a name)",
    key="chat_input",
)
if not question and st.session_state.get("queued_question"):
    question = st.session_state.pop("queued_question")
if question:
    user_id = new_msg_id("user")
    st.session_state.messages.append({"id": user_id, "role": "user", "content": question})
    with st.spinner("Thinking…"):
        con = duckdb.connect(DB_PATH)
        allowed_assets = get_allowed_assets(con)

        intent = detect_intent(question)
        account_name = detect_account_name(question, known_accounts, selected_account)

        result = run_intent(con, allowed_assets, intent, account_name)

    if "error" in result:
        assistant_id = new_msg_id("asst")
        st.session_state.messages.append(
            {
                "id": assistant_id,
                "role": "assistant",
                "content": {
                    "title": "Something went wrong",
                    "bullets": [str(result["error"])],
                    "so_what": "Use this summary to decide the next best action.",
                    "kpis": [],
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
            "intent": intent,
            "account_name": account_name,
            "row0": {},
        }
        st.session_state.details_open[assistant_id] = False
        st.rerun()
    else:
        cols, rows = result["cols"], result["rows"]
        if rows and intent in INTERPRETERS:
            row0 = dict(zip(cols, rows[0]))
            interpretation = INTERPRETERS[intent](row0)
            bullets = interpretation.get("bullets") or interpretation.get("summary_bullets", [])
            bullets = bullets[:4]
            df = to_dataframe(cols, rows)
            title_map = {
                "account_overview": "Account overview",
                "health_summary": "Health summary",
                "expansion_potential": "Expansion potential",
            }
            title = title_map.get(intent, "Answer")
            title = f"{title} — {account_name}" if account_name else title
            content = {
                "title": title,
                "bullets": bullets,
                "so_what": build_so_what(intent, df),
                "kpis": build_kpis(intent, df),
                "followups": [],
            }
            assistant_id = new_msg_id("asst")
            st.session_state.messages.append(
                {"id": assistant_id, "role": "assistant", "content": content}
            )
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
                        "bullets": ["No rows matched this question."],
                        "so_what": "Use this summary to decide the next best action.",
                        "kpis": [],
                        "followups": [],
                    },
                }
            )
            df = to_dataframe(cols, rows) if rows else None
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
                "intent": intent,
                "account_name": account_name,
                "row0": {},
            }
            st.session_state.details_open[assistant_id] = False
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
