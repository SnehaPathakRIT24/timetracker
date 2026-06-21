"""Local SQLite buffer for when the server is unreachable."""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional

DB_PATH = os.path.expanduser("~/.timetracker/buffer.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                app_name TEXT NOT NULL,
                window_title TEXT,
                url TEXT,
                duration_seconds INTEGER DEFAULT 60,
                machine_id TEXT,
                synced INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


def buffer_record(
    timestamp: datetime,
    app_name: str,
    window_title: Optional[str],
    url: Optional[str],
    duration_seconds: int,
    machine_id: str,
):
    with _conn() as conn:
        conn.execute(
            """INSERT INTO pending_records
               (timestamp, app_name, window_title, url, duration_seconds, machine_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (timestamp.isoformat(), app_name, window_title, url, duration_seconds, machine_id),
        )
        conn.commit()


def get_pending_records(limit: int = 300) -> List[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pending_records WHERE synced=0 ORDER BY timestamp LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def mark_synced(ids: List[int]):
    if not ids:
        return
    with _conn() as conn:
        conn.execute(
            f"UPDATE pending_records SET synced=1 WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        )
        conn.commit()


def get_config(key: str, default: str = "") -> str:
    with _conn() as conn:
        row = conn.execute("SELECT value FROM agent_config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_config(key: str, value: str):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO agent_config (key, value) VALUES (?, ?)", (key, value)
        )
        conn.commit()
