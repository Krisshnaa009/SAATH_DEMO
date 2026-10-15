"""
utils/state_store.py — SQLite-backed case state persistence.
Uses JSON serialisation of Pydantic models.
"""
import json
import sqlite3
import os
from datetime import datetime
from models import CaseState

DB_PATH = os.environ.get("SAATH_DB", "saath_cases.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_case(state: CaseState) -> None:
    state.updated_at = datetime.utcnow()
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO cases (case_id, state_json, updated_at) VALUES (?, ?, ?)",
        (state.case_id, state.model_dump_json(), state.updated_at.isoformat())
    )
    conn.commit()
    conn.close()


def load_case(case_id: str) -> CaseState | None:
    conn = _get_conn()
    row = conn.execute("SELECT state_json FROM cases WHERE case_id=?", (case_id,)).fetchone()
    conn.close()
    if row:
        return CaseState.model_validate_json(row["state_json"])
    return None


def list_cases() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT case_id, updated_at FROM cases ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [{"case_id": r["case_id"], "updated_at": r["updated_at"]} for r in rows]
