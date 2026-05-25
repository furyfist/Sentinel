import sqlite3
import os

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sentinel.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS file_risk_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                commit_sha TEXT,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cost_delta REAL DEFAULT 0,
                error_delta INTEGER DEFAULT 0,
                risk_score REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS incident_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                detection_type TEXT,
                severity TEXT,
                report_text TEXT,
                related_commits TEXT,
                related_errors TEXT,
                cost_impact REAL DEFAULT 0,
                slack_thread_ts TEXT
            );

            CREATE TABLE IF NOT EXISTS cost_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hourly_cost REAL,
                daily_cost REAL,
                source TEXT DEFAULT 'langfuse'
            );
        """)


init_db()


def save_incident(
    detection_type: str,
    severity: str,
    report_text: str,
    related_commits: list = None,
    related_errors: list = None,
    cost_impact: float = 0.0,
    slack_thread_ts: str = None,
) -> int:
    import json
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO incident_reports
               (detection_type, severity, report_text, related_commits, related_errors, cost_impact, slack_thread_ts)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                detection_type,
                severity,
                report_text,
                json.dumps(related_commits or []),
                json.dumps(related_errors or []),
                cost_impact,
                slack_thread_ts,
            ),
        )
        return cur.lastrowid


def get_incidents(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM incident_reports ORDER BY detected_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_cost_baseline(hourly_cost: float, daily_cost: float, source: str = "langfuse") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO cost_baselines (hourly_cost, daily_cost, source) VALUES (?, ?, ?)",
            (hourly_cost, daily_cost, source),
        )
        return cur.lastrowid


def get_baselines(limit: int = 168) -> list[dict]:
    """Returns last `limit` baseline rows (default 168 = 7 days of hourly samples)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM cost_baselines ORDER BY recorded_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_file_risk(
    file_path: str,
    commit_sha: str,
    cost_delta: float = 0.0,
    error_delta: int = 0,
    risk_score: float = 0.0,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO file_risk_history (file_path, commit_sha, cost_delta, error_delta, risk_score)
               VALUES (?, ?, ?, ?, ?)""",
            (file_path, commit_sha, cost_delta, error_delta, risk_score),
        )
        return cur.lastrowid


def get_file_risk_history(file_path: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM file_risk_history WHERE file_path = ? ORDER BY change_date DESC",
            (file_path,),
        ).fetchall()
        return [dict(r) for r in rows]
