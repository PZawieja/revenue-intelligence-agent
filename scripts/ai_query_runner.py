import duckdb
import json
from tabulate import tabulate

from ai_sql_guard import validate_sql, get_allowed_assets
from ai_intents import SQL_TEMPLATES
from ai_interpreters import INTERPRETERS

DB_PATH = "duckdb/revenue_intel.duckdb"

def stub_llm(question: str):
    q = question.lower()

    if "overview" in q or "tell me about" in q:
        return {
            "intent": "account_overview",
            "params": {
                "account_name": "Acme GmbH"
            }
        }

    return {"intent": "", "params": {}}

def run(question: str):
    con = duckdb.connect(DB_PATH)
    allowed = get_allowed_assets(con)

    plan = stub_llm(question)
    intent = plan["intent"]

    if intent not in SQL_TEMPLATES:
        print("No matching intent.")
        return

    sql = SQL_TEMPLATES[intent].format(**plan["params"])

    ok, referenced, violations = validate_sql(sql, allowed)

    if not ok:
        print("Blocked:", violations)
        return

    res = con.execute(sql)
    rows = res.fetchall()
    cols = [d[0] for d in res.description]

    print(tabulate(rows, headers=cols, tablefmt="github"))

    if rows:
        row = dict(zip(cols, rows[0]))
        print(INTERPRETERS[intent](row))

if __name__ == "__main__":
    run("Give me overview for Acme GmbH")
