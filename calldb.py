"""
Call-screening data store for Bridge.
Two things live here:
  - trusted_numbers: contacts the owner has whitelisted, who skip alerting
    entirely -- calls just connect, same as normal.
  - call_logs: a record of every incoming call and what Bridge decided
    about it (connected silently, alerted, or blocked), so the owner has
    a history to check on demand instead of the app interrupting them.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from scamdb import normalize_number  # reuse the same number normalization everywhere

DB_PATH = os.getenv(
    "CALL_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "call_screening.db"),
)


@contextmanager
def _connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trusted_numbers (
                number TEXT PRIMARY KEY,
                label TEXT,
                added_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                caller_number TEXT NOT NULL,
                action TEXT NOT NULL,
                risk_level TEXT,
                transcript TEXT,
                recording_url TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_call_logs_caller ON call_logs(caller_number)")


def is_trusted(number: str) -> bool:
    normalized = normalize_number(number)
    with _connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM trusted_numbers WHERE number = ?", (normalized,)
        ).fetchone()
    return row is not None


def add_trusted(number: str, label: str = "") -> dict:
    normalized = normalize_number(number)
    with _connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO trusted_numbers (number, label, added_at) VALUES (?, ?, ?)",
            (normalized, label, datetime.now(timezone.utc).isoformat()),
        )
    return {"number": normalized, "label": label}


def remove_trusted(number: str) -> bool:
    normalized = normalize_number(number)
    with _connection() as conn:
        cursor = conn.execute("DELETE FROM trusted_numbers WHERE number = ?", (normalized,))
    return cursor.rowcount > 0


def list_trusted() -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT number, label, added_at FROM trusted_numbers ORDER BY added_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def log_call(
    caller_number: str,
    action: str,
    session_id: str = "",
    risk_level: str = None,
    transcript: str = None,
    recording_url: str = None,
) -> dict:
    """action is one of: connected_trusted, connected_alerted, blocked_known_scammer."""
    normalized = normalize_number(caller_number)
    created_at = datetime.now(timezone.utc).isoformat()
    with _connection() as conn:
        cursor = conn.execute(
            """INSERT INTO call_logs
               (session_id, caller_number, action, risk_level, transcript, recording_url, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, normalized, action, risk_level, transcript, recording_url, created_at),
        )
        log_id = cursor.lastrowid
    return {
        "id": log_id, "session_id": session_id, "caller_number": normalized, "action": action,
        "risk_level": risk_level, "transcript": transcript, "recording_url": recording_url,
        "created_at": created_at,
    }


def has_called_before(number: str) -> bool:
    """True if this number has appeared in call_logs at all before now --
    used so an unverified caller is only alerted on once, not every time
    they call back."""
    normalized = normalize_number(number)
    with _connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM call_logs WHERE caller_number = ? LIMIT 1", (normalized,)
        ).fetchone()
    return row is not None


def recent_calls(limit: int = 20) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT * FROM call_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


init_db()