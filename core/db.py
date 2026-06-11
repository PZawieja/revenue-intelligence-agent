from __future__ import annotations
import duckdb
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "duckdb" / "revenue_intel.duckdb"


@contextmanager
def get_conn():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        yield con
    finally:
        con.close()


def query(sql: str, params: list = None) -> list[dict]:
    with get_conn() as con:
        res = con.execute(sql, params or [])
        cols = [d[0] for d in res.description]
        return [dict(zip(cols, row)) for row in res.fetchall()]


def query_one(sql: str, params: list = None) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None
