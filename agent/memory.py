import sqlite3
import os
import json
from datetime import datetime, timezone

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

            CREATE TABLE IF NOT EXISTS loop_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                loop_count INTEGER,
                cost_burned REAL,
                tool_pattern TEXT,
                status TEXT DEFAULT 'active',
                kill_method TEXT,
                slack_ts TEXT
            );

            CREATE TABLE IF NOT EXISTS schema_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sample_count INTEGER DEFAULT 0,
                UNIQUE(feature_name)
            );

            CREATE TABLE IF NOT EXISTS drift_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                drift_type TEXT,
                severity TEXT,
                blame_commit_sha TEXT,
                blame_commit_message TEXT,
                validation_fail_rate REAL,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS approval_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                anomaly_type TEXT,
                severity TEXT,
                context TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                resolved_at TIMESTAMP,
                resolved_by TEXT,
                slack_channel TEXT,
                slack_ts TEXT,
                expires_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sampling_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_traces INTEGER,
                sampled_traces INTEGER,
                dropped_traces INTEGER,
                keep_reasons TEXT
            );
        """)
        for col, col_type in [("anomaly_type", "TEXT"), ("severity", "TEXT")]:
            try:
                conn.execute(f"ALTER TABLE approval_queue ADD COLUMN {col} {col_type}")
            except Exception:
                pass


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


def save_loop_detection(
    trace_id: str,
    loop_count: int,
    cost_burned: float,
    tool_pattern: str,
    slack_ts: str = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO loop_detections (trace_id, loop_count, cost_burned, tool_pattern, slack_ts)
               VALUES (?, ?, ?, ?, ?)""",
            (trace_id, loop_count, cost_burned, tool_pattern, slack_ts),
        )
        return cur.lastrowid


def get_loop_detections(status: str = None, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM loop_detections WHERE status = ? ORDER BY detected_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM loop_detections ORDER BY detected_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def update_loop_detection(trace_id: str, status: str, kill_method: str = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE loop_detections SET status = ?, kill_method = ? WHERE trace_id = ?",
            (status, kill_method, trace_id),
        )


def save_schema_snapshot(feature_name: str, schema: dict, sample_count: int = 0) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO schema_snapshots (feature_name, schema_json, sample_count)
               VALUES (?, ?, ?)
               ON CONFLICT(feature_name) DO UPDATE SET
                   schema_json = excluded.schema_json,
                   captured_at = CURRENT_TIMESTAMP,
                   sample_count = excluded.sample_count""",
            (feature_name, json.dumps(schema), sample_count),
        )


def get_schema_snapshot(feature_name: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM schema_snapshots WHERE feature_name = ?", (feature_name,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["schema_json"] = json.loads(result["schema_json"])
        return result


def get_all_schema_snapshots() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM schema_snapshots ORDER BY feature_name").fetchall()
        return [dict(r) for r in rows]


def save_drift_event(
    feature_name: str,
    drift_type: str,
    severity: str,
    validation_fail_rate: float,
    details: dict,
    blame_commit_sha: str = None,
    blame_commit_message: str = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO drift_events
               (feature_name, drift_type, severity, validation_fail_rate, details, blame_commit_sha, blame_commit_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_name,
                drift_type,
                severity,
                validation_fail_rate,
                json.dumps(details),
                blame_commit_sha,
                blame_commit_message,
            ),
        )
        return cur.lastrowid


def get_drift_events(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM drift_events ORDER BY detected_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_approval(
    action_type: str,
    context: dict,
    anomaly_type: str = None,
    severity: str = None,
    slack_channel: str = None,
    slack_ts: str = None,
    expires_hours: int = 4,
) -> int:
    from datetime import timedelta
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO approval_queue (action_type, anomaly_type, severity, context, slack_channel, slack_ts, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (action_type, anomaly_type, severity, json.dumps(context), slack_channel, slack_ts, expires_at),
        )
        return cur.lastrowid


def get_approval(approval_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM approval_queue WHERE id = ?", (approval_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["context"] = json.loads(result["context"])
        return result


def get_approvals(status: str = None, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM approval_queue WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM approval_queue ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["context"] = json.loads(d["context"])
            result.append(d)
        return result


def update_approval(approval_id: int, status: str = None, resolved_by: str = None, slack_ts: str = None) -> None:
    with get_connection() as conn:
        if slack_ts is not None:
            conn.execute(
                "UPDATE approval_queue SET slack_ts = ? WHERE id = ?",
                (slack_ts, approval_id),
            )
        if status is not None:
            conn.execute(
                """UPDATE approval_queue
                   SET status = ?, resolved_at = CURRENT_TIMESTAMP, resolved_by = ?
                   WHERE id = ?""",
                (status, resolved_by, approval_id),
            )


def get_expired_approvals() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM approval_queue
               WHERE status = 'pending' AND expires_at < CURRENT_TIMESTAMP""",
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["context"] = json.loads(d["context"])
            result.append(d)
        return result


def save_sampling_stats(
    total_traces: int,
    sampled_traces: int,
    dropped_traces: int,
    keep_reasons: dict,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO sampling_stats (total_traces, sampled_traces, dropped_traces, keep_reasons)
               VALUES (?, ?, ?, ?)""",
            (total_traces, sampled_traces, dropped_traces, json.dumps(keep_reasons)),
        )
        return cur.lastrowid


def get_sampling_stats(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sampling_stats ORDER BY recorded_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
