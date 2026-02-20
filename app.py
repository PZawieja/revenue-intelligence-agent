import re
import duckdb
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

# ---------------- UI ----------------

st.set_page_config(page_title="Revenue Intelligence Agent", layout="wide")
st.title("Revenue Intelligence Agent")
st.caption("Ask about ARR/MRR, renewal date, health score, and expansion potential. (Demo: allowlisted + guarded SQL)")

known_accounts = load_account_names()

PERSONAS = list(PERSONA_QUESTION_PACKS.keys())

with st.sidebar:
    st.header("Demo Controls")
    if "persona" not in st.session_state:
        st.session_state.persona = PERSONAS[0]
    persona = st.selectbox(
        "Persona",
        PERSONAS,
        index=PERSONAS.index(st.session_state.persona),
    )
    st.session_state.persona = persona
    st.caption(PERSONA_DESCRIPTIONS.get(persona, ""))
    selected_account = st.selectbox("Default account", known_accounts, index=0)
    st.divider()
    st.markdown("**Example questions (no names needed)**")
    st.markdown("- Give me an account overview")
    st.markdown("- Is this account healthy?")
    st.markdown("- What is the expansion potential?")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Ask me about a customer (overview, health, expansion)."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.markdown("### Try these")
question_tiles = PERSONA_QUESTION_PACKS.get(st.session_state.persona, [])
tile_cols = st.columns(3)
for idx, q in enumerate(question_tiles):
    if tile_cols[idx % 3].button(q, use_container_width=True):
        st.session_state["queued_question"] = q
        st.rerun()

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
                st.markdown(f"**{interpretation.get('title', 'Summary')}**")
                for bullet in interpretation.get("summary_bullets", [])[:5]:
                    st.markdown(f"- {bullet}")
                if interpretation.get("narrative"):
                    st.markdown(interpretation["narrative"])
                for warning in interpretation.get("warnings", []):
                    st.warning(warning)
            else:
                st.markdown("No results found for this question.")

            # Suggested next questions (always visible)
            st.markdown("### Suggested next questions")
            base_suggestions = FOLLOWUP_SUGGESTIONS.get(intent, [])
            persona_pack = PERSONA_QUESTION_PACKS.get(st.session_state.persona, [])
            suggestions = [q for q in base_suggestions if q in persona_pack]
            if len(suggestions) < 4:
                for q in persona_pack:
                    if q not in suggestions:
                        suggestions.append(q)
                    if len(suggestions) >= 6:
                        break
            suggestion_cols = st.columns(3)
            for idx, q in enumerate(suggestions[:6]):
                if suggestion_cols[idx % 3].button(q, key=f"suggest-{intent}-{idx}"):
                    st.session_state["queued_question"] = q
                    st.rerun()

            # Evidence (collapsed by default)
            st.markdown("### Evidence")
            if result.get("chart"):
                with st.expander("See chart", expanded=False):
                    st.altair_chart(result["chart"], use_container_width=True)
            with st.expander("See data", expanded=False):
                st.code(format_table(cols, rows), language="markdown")
            with st.expander("See SQL", expanded=False):
                st.code(result["sql"], language="sql")
            with st.expander("Definitions / assumptions", expanded=False):
                if rows and intent in INTERPRETERS:
                    for item in interpretation.get("definitions", []):
                        st.markdown(f"- {item}")
                else:
                    st.markdown("No definitions available.")
            with st.expander("Debug", expanded=False):
                st.markdown(f"- Intent: `{intent}`")
                st.markdown(f"- Rows: {len(rows)}")

            # Save assistant message content (concise)
            answer_text = f"Result for **{account_name}** (intent: `{intent}`)\n\n" \
                          f"```\n{format_table(cols, rows)}\n```"
            st.session_state.messages.append({"role": "assistant", "content": answer_text})
