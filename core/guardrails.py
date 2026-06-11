from __future__ import annotations
import re

BLOCKED_KEYWORDS = [
    "insert", "update", "delete", "merge", "create",
    "drop", "alter", "truncate", "grant", "revoke", "call",
]

PII_PATTERNS = [
    "email", "e_mail", "phone", "mobile", "address", "street",
    "postcode", "zip", "iban", "card", "credit", "password", "token",
]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", name or "").lower()


def extract_tables(sql: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"(?:from|join)\s+([a-zA-Z0-9_]+)", sql, re.IGNORECASE)]


def _extract_select_columns(sql: str) -> list[str]:
    match = re.search(r"select\s+(.*?)\s+from\s", sql, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    parts = re.split(r",(?![^()]*\))", match.group(1))
    cols = []
    for part in parts:
        tok = part.strip()
        if not tok:
            continue
        tok = re.split(r"\s+as\s+", tok, flags=re.IGNORECASE)[0]
        tok = tok.split()[0].split(".")[-1]
        cols.append(tok)
    return cols


def _blocked_found(sql: str) -> list[str]:
    return [kw.upper() for kw in BLOCKED_KEYWORDS if re.search(rf"\b{kw}\b", sql, re.IGNORECASE)]


def compute_guardrails(sql: str, allowed_assets: set[str], df_shape: tuple[int, int]) -> dict:
    s = (sql or "").strip()
    low = s.lower()
    blocked = _blocked_found(s)
    select_only = (low.startswith("select") or low.startswith("with")) and not blocked
    tables = extract_tables(s)
    allowlisted = bool(tables) and all(_normalize(t) in {a.lower() for a in allowed_assets} for t in tables)
    has_limit = bool(re.search(r"\blimit\s+\d+\b", s, re.IGNORECASE))
    cols = _extract_select_columns(s)
    pii_hits = [c for c in cols if any(p in _normalize(c) for p in PII_PATTERNS)]
    no_pii = len(pii_hits) == 0 if cols else True
    rows, ncols = df_shape
    return {
        "select_only": select_only,
        "allowlisted_assets": allowlisted,
        "row_limit_present": has_limit,
        "no_pii_columns": no_pii,
        "blocked_keywords_found": blocked,
        "tables_used": tables,
        "result_rows": rows,
        "result_cols": ncols,
    }
