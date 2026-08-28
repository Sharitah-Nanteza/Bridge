"""
Scam number reputation database for Bridge.

The module stores reports in SQLite and exposes small functions that can be
used by the web and USSD adapters.
"""

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DB_PATH = os.getenv(
    "SCAM_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "scam_reports.db"),
)

SUSPICIOUS_PREFIXES = ["0900", "0999", "0800"]

CATEGORY_KEYWORDS = {
    "mobile_money_fraud": ["pin", "mobile money", "momo", "agent", "otp", "airtel money", "mtn money"],
    "impersonation": ["police", "ura", "bank", "government", "official", "customs"],
    "prize_scam": ["prize", "winner", "lottery", "won", "congratulations"],
    "sim_swap": ["sim", "swap", "network lost", "line blocked"],
    "harassment": ["threat", "harass", "abuse", "blackmail"],
}


def normalize_number(number: str) -> str:
    """Normalize Ugandan local and +256 numbers to the same representation."""
    digits = re.sub(r"\D", "", number or "")
    if digits.startswith("256") and len(digits) == 12:
        digits = "0" + digits[3:]
    return digits


def classify_reason(reason: str) -> str:
    """Classify a free-text report reason into a UI-friendly category."""
    if not reason:
        return "unspecified"
    lowered = reason.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "unspecified"


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
    """Create the reports table and index if they do not exist."""
    with _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL,
                reporter TEXT,
                reason TEXT,
                category TEXT,
                reported_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_number ON reports(number)")


def report_number(number: str, reason: str, reporter: str = None) -> dict:
    """Save a report and return the saved record."""
    normalized = normalize_number(number)
    category = classify_reason(reason)
    reported_at = datetime.now(timezone.utc).isoformat()

    with _connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reports (number, reporter, reason, category, reported_at) VALUES (?, ?, ?, ?, ?)",
            (normalized, reporter, reason, category, reported_at),
        )
        report_id = cursor.lastrowid

    return {
        "id": report_id,
        "number": normalized,
        "reporter": reporter,
        "reason": reason,
        "category": category,
        "reported_at": reported_at,
    }


def _matches_suspicious_prefix(number: str) -> str | None:
    return next((prefix for prefix in SUSPICIOUS_PREFIXES if number.startswith(prefix)), None)


def check_number(number: str, recent_days: int = 90) -> dict:
    """Return the report history and risk assessment for a phone number."""
    normalized = normalize_number(number)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=recent_days)).isoformat()

    with _connection() as conn:
        rows = conn.execute(
            "SELECT reason, category, reported_at FROM reports WHERE number = ? ORDER BY reported_at DESC",
            (normalized,),
        ).fetchall()

    report_count = len(rows)
    recent_report_count = sum(1 for row in rows if row["reported_at"] >= cutoff)
    flags = []
    prefix_hit = _matches_suspicious_prefix(normalized)
    if prefix_hit:
        flags.append(f"Number starts with {prefix_hit}, a prefix associated with premium-rate or scam services.")

    if report_count == 0:
        risk_level = "medium" if prefix_hit else "unknown"
        if not prefix_hit:
            flags.append("No reports on file yet. Being unlisted does not guarantee it is safe.")
        return {
            "number": normalized, "risk_level": risk_level, "report_count": 0,
            "recent_report_count": 0, "top_category": None, "reasons": [],
            "first_reported": None, "last_reported": None, "flags": flags,
        }

    category_counts = {}
    for row in rows:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
    top_category = max(category_counts, key=category_counts.get)

    if report_count >= 5 or recent_report_count >= 2:
        risk_level = "high"
        flags.append(f"Reported {report_count} time(s), including {recent_report_count} in the last {recent_days} days.")
    elif report_count >= 2:
        risk_level = "medium"
        flags.append(f"Reported {report_count} times by other users.")
    else:
        risk_level = "low"
        flags.append("Reported once. Treat with caution and verify independently.")

    if top_category != "unspecified":
        flags.append(f"Most common report category: {top_category.replace('_', ' ')}.")

    return {
        "number": normalized, "risk_level": risk_level, "report_count": report_count,
        "recent_report_count": recent_report_count, "top_category": top_category,
        "reasons": [row["reason"] for row in rows[:3] if row["reason"]],
        "first_reported": rows[-1]["reported_at"], "last_reported": rows[0]["reported_at"],
        "flags": flags,
    }


def get_stats() -> dict:
    """Return aggregate report counts."""
    with _connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]
        unique_numbers = conn.execute("SELECT COUNT(DISTINCT number) AS c FROM reports").fetchone()["c"]
        by_category = conn.execute(
            "SELECT category, COUNT(*) AS c FROM reports GROUP BY category ORDER BY c DESC"
        ).fetchall()

    return {
        "total_reports": total,
        "unique_numbers_reported": unique_numbers,
        "by_category": {row["category"]: row["c"] for row in by_category},
    }


init_db()