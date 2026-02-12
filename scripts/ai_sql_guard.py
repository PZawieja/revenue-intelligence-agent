import re
import duckdb

DB_PATH = "duckdb/revenue_intel.duckdb"

def get_allowed_assets(con) -> set[str]:
    rows = con.execute("""
        select asset_name
        from dim_ai_allowed_assets
        where is_allowed_for_ai = true
    """).fetchall()
    return {r[0].lower() for r in rows}

def extract_referenced_assets(sql: str) -> set[str]:
    pattern = r"(?:from|join)\s+([a-zA-Z0-9_]+)"
    return {m.group(1).lower() for m in re.finditer(pattern, sql, flags=re.IGNORECASE)}

def validate_sql(sql: str, allowed_assets: set[str]):
    s = sql.lower().strip()
    violations = []

    if not s.startswith("select"):
        violations.append("only_select_allowed")

    if re.search(r"select\s+\*", s):
        violations.append("select_star_blocked")

    referenced = extract_referenced_assets(sql)
    not_allowed = [a for a in referenced if a not in allowed_assets]

    if not_allowed:
        violations.extend([f"non_allowlisted_asset:{a}" for a in not_allowed])

    return (len(violations) == 0, referenced, violations)
