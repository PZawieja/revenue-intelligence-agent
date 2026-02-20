import time

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


def parse_summary(content: str):
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    title = lines[0] if lines else "Answer"
    bullets = [line[2:] for line in lines[1:] if line.startswith("- ")]
    narrative = " ".join([line for line in lines[1:] if not line.startswith("- ")])
    return title, bullets, narrative


def build_kpi_chips(intent: str, row: dict) -> list[dict]:
    if not row:
        return []
    chips = []
    if intent == "health_summary":
        health_score = row.get("health_score")
        health_band = row.get("health_band")
        days_to_renewal = row.get("days_to_renewal")
        usage_drop_ratio = row.get("usage_drop_ratio")
        if health_score is not None:
            band = (health_band or "").lower()
            chip_class = f"chip-{band}" if band in {"green", "yellow", "red"} else "chip-neutral"
            chips.append({"text": f"Health {health_score:.2f}", "class": chip_class})
        if days_to_renewal is not None:
            chips.append({"text": f"{days_to_renewal} days to renewal", "class": "chip-neutral"})
        if usage_drop_ratio is not None:
            chips.append({"text": f"Usage ↓ {usage_drop_ratio:.0%}", "class": "chip-neutral"})
    elif intent == "account_overview":
        plan = row.get("plan")
        status = row.get("subscription_status")
        renewal_date = row.get("renewal_date")
        current_mrr = row.get("current_mrr_eur")
        if plan:
            chips.append({"text": f"Plan {plan}", "class": "chip-neutral"})
        if status:
            chips.append({"text": f"Status {status}", "class": "chip-neutral"})
        if renewal_date:
            chips.append({"text": f"Renewal {renewal_date}", "class": "chip-neutral"})
        if current_mrr is not None:
            chips.append({"text": f"MRR €{current_mrr}", "class": "chip-neutral"})
    elif intent == "expansion_potential":
        expansion_score = row.get("expansion_score")
        expansion_band = row.get("expansion_band")
        seat_util = row.get("seat_utilization_ratio")
        if expansion_score is not None:
            band = (expansion_band or "").lower()
            chip_class = f"chip-{band}" if band in {"high", "medium", "low"} else "chip-neutral"
            chips.append({"text": f"Expansion {expansion_score:.2f}", "class": chip_class})
        if seat_util is not None:
            chips.append({"text": f"Seat util {seat_util:.2f}", "class": "chip-neutral"})
    return chips


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
        st.session_state.pop("evidence", None)
        st.session_state.pop("details_open", None)
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Ask me about a customer (overview, health, expansion)."}
    ]
if "evidence" not in st.session_state:
    st.session_state.evidence = {}
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

last_assistant_idx = None
for i, m in enumerate(st.session_state.messages):
    if m["role"] == "assistant":
        last_assistant_idx = i

for idx, msg in enumerate(st.session_state.messages):
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
        title, bullets, narrative = parse_summary(msg["content"])
        ev = st.session_state.evidence.get(idx, {})
        account_name = ev.get("account_name", "")
        intent_titles = {
            "account_overview": "Account overview",
            "health_summary": "Health summary",
            "expansion_potential": "Expansion potential",
        }
        friendly_title = intent_titles.get(ev.get("intent", ""), title)
        header_title = f"{friendly_title} — {account_name}" if account_name else friendly_title

        st.markdown("<div class='answer-card'>", unsafe_allow_html=True)
        header_cols = st.columns([0.78, 0.22])
        with header_cols[0]:
            st.markdown(f"<div class='answer-title'>{header_title}</div>", unsafe_allow_html=True)
        with header_cols[1]:
            has_details = bool(ev.get("sql") or ev.get("rows") or ev.get("definitions"))
            if has_details:
                is_open = st.session_state.details_open.get(idx, False)
                label = "Details ▴" if is_open else "Details ▾"
                if st.button(label, key=f"details-toggle-{idx}", type="secondary"):
                    st.session_state.details_open[idx] = not is_open
                    st.rerun()

        chips = build_kpi_chips(ev.get("intent", ""), ev.get("row0", {}))
        if chips:
            chips_html = "".join(
                [f"<span class='chip {c['class']}'>{c['text']}</span>" for c in chips]
            )
            st.markdown(f"<div class='kpi-row'>{chips_html}</div>", unsafe_allow_html=True)

        bullets_html = "".join([f"<li>{b}</li>" for b in bullets[:4]])
        if bullets_html:
            st.markdown(f"<ul class='answer-list'>{bullets_html}</ul>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='answer-muted'>No summary available.</div>", unsafe_allow_html=True)

        if narrative:
            st.markdown(f"<div class='answer-muted'>{narrative}</div>", unsafe_allow_html=True)

        if idx == last_assistant_idx and ev.get("intent"):
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
                    if st.button(q, key=f"suggest-{idx}-{s_idx}-{abs(hash(q))}"):
                        st.session_state["queued_question"] = q
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.details_open.get(idx, False):
            st.markdown("<div class='details-section'>", unsafe_allow_html=True)
            tabs = st.tabs(["Results", "SQL", "Definitions", "Debug"])
            with tabs[0]:
                rows = ev.get("rows", [])
                if rows:
                    st.dataframe(
                        to_dataframe(ev["cols"], rows[:15]),
                        height=240,
                        use_container_width=True,
                    )
                else:
                    st.markdown("No rows returned.")
            with tabs[1]:
                if st.button("Copy SQL", key=f"copy-sql-{idx}", type="secondary"):
                    st.toast("SQL ready to copy from below.")
                st.code(ev.get("sql", ""), language="sql")
            with tabs[2]:
                definitions = ev.get("definitions", [])
                if definitions:
                    for item in definitions:
                        st.markdown(f"- {item}")
                else:
                    st.markdown("No definitions available.")
            with tabs[3]:
                intent = ev.get("intent", "")
                st.markdown(f"- Intent: `{intent}`")
                st.markdown(f"- Asset: `{INTENT_ASSET.get(intent, '')}`")
                st.markdown(f"- Row count: {len(ev.get('rows', []))}")
                st.markdown(f"- Runtime: {ev.get('runtime_ms', 0)} ms")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

question = st.chat_input(
    "Type your question… (use the default account if you omit a name)",
    key="chat_input",
)
if not question and st.session_state.get("queued_question"):
    question = st.session_state.pop("queued_question")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Thinking…"):
        con = duckdb.connect(DB_PATH)
        allowed_assets = get_allowed_assets(con)

        intent = detect_intent(question)
        account_name = detect_account_name(question, known_accounts, selected_account)

        result = run_intent(con, allowed_assets, intent, account_name)

    if "error" in result:
        st.session_state.messages.append({"role": "assistant", "content": f"❌ {result['error']}"})
        assistant_index = len(st.session_state.messages) - 1
        st.session_state.evidence[assistant_index] = {
            "intent": intent,
            "account_name": account_name,
            "sql": result.get("sql", ""),
            "cols": [],
            "rows": [],
            "definitions": [],
            "row0": {},
            "runtime_ms": result.get("runtime_ms", 0),
        }
        st.rerun()
    else:
        cols, rows = result["cols"], result["rows"]
        if rows and intent in INTERPRETERS:
            row0 = dict(zip(cols, rows[0]))
            interpretation = INTERPRETERS[intent](row0)
            bullets = interpretation.get("summary_bullets", [])[:5]
            narrative = interpretation.get("narrative", "")
            intent_titles = {
                "account_overview": "Account overview",
                "health_summary": "Health summary",
                "expansion_potential": "Expansion potential",
            }
            title = intent_titles.get(intent, "Answer")
            summary_lines = [f"{title} — {account_name}"]
            for b in bullets[:5]:
                summary_lines.append(f"- {b}")
            if narrative:
                summary_lines.append(narrative)
            st.session_state.messages.append(
                {"role": "assistant", "content": "\n".join(summary_lines)}
            )
            assistant_index = len(st.session_state.messages) - 1
            st.session_state.evidence[assistant_index] = {
                "intent": intent,
                "account_name": account_name,
                "sql": result["sql"],
                "cols": cols,
                "rows": rows,
                "definitions": interpretation.get("definitions", []),
                "warnings": interpretation.get("warnings", []),
                "row0": row0,
                "runtime_ms": result.get("runtime_ms", 0),
            }
            st.rerun()
        else:
            st.session_state.messages.append(
                {"role": "assistant", "content": "No results found for this question."}
            )
            assistant_index = len(st.session_state.messages) - 1
            st.session_state.evidence[assistant_index] = {
                "intent": intent,
                "account_name": account_name,
                "sql": result["sql"],
                "cols": cols,
                "rows": rows,
                "definitions": [],
                "warnings": [],
                "row0": {},
                "runtime_ms": result.get("runtime_ms", 0),
            }
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
