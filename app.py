import re
import duckdb
import pandas as pd
import streamlit as st
from tabulate import tabulate

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

# Which single allowlisted asset each intent is allowed to touch
INTENT_ASSET = {
    "account_overview": "ai_dm_account_overview",
    "health_summary": "ai_fct_account_health_score",
    "expansion_potential": "ai_fct_account_expansion_potential",
}

def sql_escape(value: str) -> str:
    # basic SQL literal escaping for demo safety
    return value.replace("'", "''")

@st.cache_data(show_spinner=False)
def load_account_names():
    con = duckdb.connect(DB_PATH)
    rows = con.execute("""
        select distinct account_name
        from ai_dm_account_overview
        order by 1
    """).fetchall()
    return [r[0] for r in rows]

def detect_intent(question: str) -> str:
    q = question.lower().strip()

    if "health" in q or "risk" in q:
        return "health_summary"
    if "expand" in q or "expansion" in q or "upsell" in q:
        return "expansion_potential"
    if "overview" in q or "tell me about" in q or "summary" in q:
        return "account_overview"

    # default for MVP
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

    # Enforce single-asset scope (strong safety signal for demos)
    if set(referenced) != {expected_asset.lower()}:
        return {
            "error": "Blocked: query must reference only the declared allowlisted asset for this intent.",
            "sql": sql,
            "referenced": referenced,
            "expected_asset": expected_asset,
        }

    res = con.execute(sql)
    rows = res.fetchall()
    cols = [d[0] for d in res.description]

    return {"sql": sql, "cols": cols, "rows": rows}

def format_table(cols, rows) -> str:
    if not rows:
        return "No rows returned."
    return tabulate(rows, headers=cols, tablefmt="github")

def to_dataframe(cols, rows):
    return pd.DataFrame(rows, columns=cols)

def render_chat_message(role: str, content: str):
    if role != "assistant":
        st.markdown(content)
        return
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    title = lines[0] if lines else "Answer"
    bullets = [line[2:] for line in lines[1:] if line.startswith("- ")]
    bullets_html = "".join([f"<li>{b}</li>" for b in bullets])
    st.markdown(
        f"""
<div class="chat-bubble">
  <div class="chat-title">{title}</div>
  <ul>{bullets_html}</ul>
</div>
        """,
        unsafe_allow_html=True,
    )

# ---------------- UI ----------------

st.set_page_config(page_title="Revenue Intelligence Agent", layout="wide")
inject_css()
st.markdown("<div class='app-container'>", unsafe_allow_html=True)
st.markdown("## Revenue Intelligence")
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
    )
    st.session_state.persona = persona
    selected_account = st.selectbox("Default account", known_accounts, index=0)
    if st.button("New chat", type="primary", use_container_width=True):
        st.session_state.pop("messages", None)
        st.session_state.pop("queued_question", None)
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Ask me about a customer (overview, health, expansion)."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        render_chat_message(msg["role"], msg["content"])

st.markdown(f"### Quick questions for {st.session_state.persona}")
question_tiles = PERSONA_QUESTION_PACKS.get(st.session_state.persona, [])
primary_tiles = question_tiles[:6]
extra_tiles = question_tiles[6:]
tile_cols = st.columns(3)
st.markdown("<div class='tile-grid'>", unsafe_allow_html=True)
for idx, q in enumerate(primary_tiles):
    with tile_cols[idx % 3]:
        if st.button(q, key=f"tile-{idx}"):
            st.session_state["queued_question"] = q
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
if extra_tiles:
    with st.expander("Show more"):
        extra_cols = st.columns(3)
        st.markdown("<div class='tile-grid'>", unsafe_allow_html=True)
        for idx, q in enumerate(extra_tiles):
            with extra_cols[idx % 3]:
                if st.button(q, key=f"tile-extra-{idx}"):
                    st.session_state["queued_question"] = q
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

question = st.chat_input("Type your question… (use the default account if you omit a name)")
if not question and st.session_state.get("queued_question"):
    question = st.session_state.pop("queued_question")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            con = duckdb.connect(DB_PATH)
            allowed_assets = get_allowed_assets(con)

            intent = detect_intent(question)
            account_name = detect_account_name(question, known_accounts, selected_account)

            result = run_intent(con, allowed_assets, intent, account_name)

        if "error" in result:
            st.error(result["error"])
            if "sql" in result:
                with st.expander("Show SQL (debug)"):
                    st.code(result["sql"], language="sql")
            if "referenced" in result:
                st.caption(f"Referenced assets: {result['referenced']}")
            st.session_state.messages.append({"role": "assistant", "content": f"❌ {result['error']}"})
        else:
            cols, rows = result["cols"], result["rows"]

            # Answer (always visible)
            st.markdown("### Answer")
            if rows and intent in INTERPRETERS:
                row0 = dict(zip(cols, rows[0]))
                interpretation = INTERPRETERS[intent](row0)
                bullets = interpretation.get("summary_bullets", [])[:5]
                bullets_html = "".join([f"<li>{b}</li>" for b in bullets])
                narrative = interpretation.get("narrative", "")
                intent_titles = {
                    "account_overview": "Account overview",
                    "health_summary": "Health summary",
                    "expansion_potential": "Expansion potential",
                }
                title = intent_titles.get(intent, "Answer")
                st.markdown(
                    f"""
<div class="answer-card">
  <div class="answer-label">Answer</div>
  <div class="answer-title">{title} — {account_name}</div>
  <ul>{bullets_html}</ul>
  <div class="answer-muted">{narrative}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
                for warning in interpretation.get("warnings", []):
                    st.warning(warning)
            else:
                st.markdown("No results found for this question.")

            # Suggested next questions (always visible)
            st.markdown("**Next best questions**")
            base_suggestions = FOLLOWUP_SUGGESTIONS.get(intent, [])
            persona_pack = PERSONA_QUESTION_PACKS.get(st.session_state.persona, [])
            suggestions = [q for q in base_suggestions if q in persona_pack]
            if len(suggestions) < 4:
                for q in persona_pack:
                    if q not in suggestions:
                        suggestions.append(q)
                    if len(suggestions) >= 6:
                        break
            suggestion_cols = st.columns(4)
            st.markdown("<div class='pill'>", unsafe_allow_html=True)
            for idx, q in enumerate(suggestions[:4]):
                with suggestion_cols[idx % 4]:
                    if st.button(q, key=f"suggest-{intent}-{idx}"):
                        st.session_state["queued_question"] = q
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            # Details (tabs)
            st.markdown("### Details")
            tab_labels = ["Data", "SQL", "Definitions", "Debug"]
            if result.get("chart"):
                tab_labels.append("Chart")
            tabs = st.tabs(tab_labels)
            with tabs[0]:
                st.dataframe(to_dataframe(cols, rows), use_container_width=True)
            with tabs[1]:
                copy_key = f"copy-sql-{intent}"
                if st.button("Copy SQL", key=copy_key):
                    st.toast("SQL ready to copy from below.")
                st.code(result["sql"], language="sql")
            with tabs[2]:
                if rows and intent in INTERPRETERS:
                    for item in interpretation.get("definitions", []):
                        st.markdown(f"- {item}")
                else:
                    st.markdown("No definitions available.")
            with tabs[3]:
                st.markdown(f"- Intent: `{intent}`")
                st.markdown(f"- Rows: {len(rows)}")
            if result.get("chart"):
                with tabs[4]:
                    st.altair_chart(result["chart"], use_container_width=True)

            # Save assistant message content (human summary only)
            if rows and intent in INTERPRETERS:
                summary_lines = [f"{title} — {account_name}"]
                for b in bullets[:5]:
                    summary_lines.append(f"- {b}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": "\n".join(summary_lines)}
                )
            else:
                st.session_state.messages.append(
                    {"role": "assistant", "content": "No results found for this question."}
                )

st.markdown("</div>", unsafe_allow_html=True)
