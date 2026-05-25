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
