import re
from typing import Optional, Tuple


BLOCKED_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "merge",
    "create",
    "drop",
    "alter",
    "truncate",
    "grant",
    "revoke",
    "call",
]

PII_PATTERNS = [
    "email",
    "e_mail",
    "phone",
    "mobile",
    "address",
    "street",
    "postcode",
    "zip",
    "iban",
    "card",
    "credit",
    "password",
    "token",
]


def _normalize_identifier(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", name or "").lower()


def extract_tables(sql: str) -> list[str]:
    pattern = r"(?:from|join)\s+([a-zA-Z0-9_]+)"
    return [m.group(1) for m in re.finditer(pattern, sql, flags=re.IGNORECASE)]


def extract_select_columns(sql: str) -> list[str]:
    # Best-effort: grab text between SELECT and FROM in the first statement
    match = re.search(r"select\s+(.*?)\s+from\s", sql, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    select_clause = match.group(1)
    # split on commas not inside parentheses
    parts = re.split(r",(?![^()]*\))", select_clause)
    cols = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        # remove aliases
        token = re.split(r"\s+as\s+", token, flags=re.IGNORECASE)[0]
        token = token.split()[:1][0]
        token = token.split(".")[-1]
        cols.append(token)
    return cols


def find_limit(sql: str) -> Tuple[bool, Optional[int]]:
    match = re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE)
    if not match:
        return False, None
    try:
        return True, int(match.group(1))
    except ValueError:
        return True, None


def blocked_keywords(sql: str) -> list[str]:
    found = []
    for kw in BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", sql, flags=re.IGNORECASE):
            found.append(kw.upper())
    return found


def compute_guardrails(sql: str, allowlisted_assets: set[str], df_shape: Tuple[int, int]) -> dict:
    s = (sql or "").strip()
    lowered = s.lower()
    select_only = (
        (lowered.startswith("select") or lowered.startswith("with"))
        and len(blocked_keywords(s)) == 0
    )
    tables = extract_tables(s)
    normalized_tables = {_normalize_identifier(t) for t in tables}
    allowlisted = bool(tables) and all(
        _normalize_identifier(t) in {a.lower() for a in allowlisted_assets} for t in normalized_tables
    )
    limit_present, limit_value = find_limit(s)
    columns = extract_select_columns(s)
    pii_hits = []
    if columns:
        for col in columns:
            norm = _normalize_identifier(col)
            if any(p in norm for p in PII_PATTERNS):
                pii_hits.append(col)
    no_pii = False if not columns else len(pii_hits) == 0
    rows, cols = df_shape
    return {
        "select_only": select_only,
        "allowlisted_assets": allowlisted,
        "row_limit_present": limit_present,
        "row_limit_value": limit_value,
        "no_pii_columns": no_pii,
        "blocked_keywords_found": blocked_keywords(s),
        "tables_used": tables,
        "columns_selected": columns,
        "result_rows": rows,
        "result_cols": cols,
    }
