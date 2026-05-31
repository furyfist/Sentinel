"""
Demo seeder — writes only to SQLite, no external API calls.
Idempotent: checks if data already exists before inserting.

Run: python scripts/seed_demo_sqlite.py
Railway startup uses this via DEMO_MODE=true in api/main.py.
"""
import os
import sys
import json
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import memory


def _utcnow():
    return datetime.now(timezone.utc)


def _already_seeded() -> bool:
    with memory.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM incident_reports").fetchone()[0]
    return count > 0


def seed_incidents():
    now = _utcnow()
    incidents = [
        {
            "detection_type": "loop_detected",
            "severity": "critical",
            "report_text": (
                "**Agent Loop Detected** — trace `a3f9d21b` fired 22 consecutive `retry-search` "
                "generations in 4 minutes on model `gpt-4`. Estimated cost: $0.28 (projected $4.20/hr "
                "if unchecked). Pattern: identical tool input each cycle — likely a failed exit condition "
                "after upstream API returned empty results.\n\n"
                "**Root cause:** `search_knowledge_base` returned empty list; agent retried without "
                "backoff or nil-guard. Recommend: add nil-check on tool output before re-queuing."
            ),
            "related_commits": ["c7a2e81", "b0f3d44"],
            "related_errors": ["RateLimitError: Too many requests (attempt 18)", "RateLimitError: Too many requests (attempt 22)"],
            "cost_impact": 0.28,
            "detected_at": (now - timedelta(minutes=47)).isoformat(),
        },
        {
            "detection_type": "cost_spike",
            "severity": "high",
            "report_text": (
                "**Cost Spike Detected** — hourly cost jumped to $4.20/hr vs $0.80/hr baseline (5.3×). "
                "Triggered by `runaway-agent` traces using `gpt-4` with 5000-token context windows.\n\n"
                "**Root cause:** PR #41 changed `max_tokens=500` → `max_tokens=4096` in the summariser "
                "pipeline. Commit `d9c3e11` by @alice, merged 2h ago. Sentry shows 0 errors — silent "
                "cost regression. Recommend: revert `max_tokens` or add per-trace cost cap."
            ),
            "related_commits": ["d9c3e11"],
            "related_errors": [],
            "cost_impact": 4.20,
            "detected_at": (now - timedelta(hours=2, minutes=12)).isoformat(),
        },
        {
            "detection_type": "drift_detected",
            "severity": "high",
            "report_text": (
                "**Prompt Drift Detected** — `support-bot` schema break at 80% fail rate. "
                "Expected output keys: `response`, `confidence`, `category`. "
                "Actual output keys: `answer`, `score` (missing `response`, `category`).\n\n"
                "**Root cause:** Commit `f1a8b33` by @bob rewrote the system prompt to use Q&A framing. "
                "The downstream parser still expects the old 3-key format. 10 of the last 12 traces fail "
                "JSON extraction silently. Recommend: update output parser or pin the old prompt."
            ),
            "related_commits": ["f1a8b33"],
            "related_errors": ["JSONDecodeError: Expecting property name", "KeyError: 'category'"],
            "cost_impact": 0.05,
            "detected_at": (now - timedelta(hours=5, minutes=3)).isoformat(),
        },
        {
            "detection_type": "tool_failure",
            "severity": "high",
            "report_text": (
                "**Silent Tool Failure** — `search_knowledge_base` returned HTTP 200 OK but Sentry "
                "logged `JSONDecodeError` 30s later on the same trace window. Tool output byte size: "
                "8B (average: 420B). The agent consumed the empty response and continued — no exception "
                "raised, no fallback triggered.\n\n"
                "**Root cause:** Knowledge-base API under load returned `{}` (empty JSON object) instead "
                "of raising a 503. The agent's tool wrapper does not validate response schema. "
                "Recommend: add schema validation wrapper around tool calls."
            ),
            "related_commits": ["e4d7c92"],
            "related_errors": ["JSONDecodeError: Expecting value at position 0"],
            "cost_impact": 0.02,
            "detected_at": (now - timedelta(hours=9, minutes=30)).isoformat(),
        },
        {
            "detection_type": "cost_spike",
            "severity": "medium",
            "report_text": (
                "**Moderate Cost Increase** — hourly cost at $1.60/hr vs $0.80/hr baseline (2×). "
                "Spike correlates with increased traffic on `invoice-parser` feature, not a bug. "
                "No errors in Sentry. Sampling efficiency: 91% noise dropped, all actionable traces kept."
            ),
            "related_commits": [],
            "related_errors": [],
            "cost_impact": 1.60,
            "detected_at": (now - timedelta(days=1, hours=3)).isoformat(),
        },
        {
            "detection_type": "weekly_digest",
            "severity": "info",
            "report_text": (
                "## Weekly Sentinel Digest\n\n"
                "**What shipped:** 14 PRs merged. Highlights: invoice-parser v2 (PR #38), "
                "retry-backoff fix (PR #39), max_tokens regression (PR #41 — see cost spike).\n\n"
                "**What broke:** 1 silent cost regression (PR #41, $4.20/hr peak). "
                "1 schema drift on support-bot (PR #40). 2 agent loops — both resolved.\n\n"
                "**What to watch:** `invoice-parser` schema has 3 new optional keys — parser "
                "is forwards-compatible but monitor fail rate. `gpt-4o-mini` rolling out to 3 "
                "features next week — expect cost baseline to shift down ~40%."
            ),
            "related_commits": ["d9c3e11", "f1a8b33", "c7a2e81"],
            "related_errors": [],
            "cost_impact": 0.0,
            "detected_at": (now - timedelta(days=2)).isoformat(),
        },
    ]

    with memory.get_connection() as conn:
        for inc in incidents:
            conn.execute(
                """INSERT INTO incident_reports
                   (detection_type, severity, report_text, related_commits, related_errors,
                    cost_impact, detected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    inc["detection_type"],
                    inc["severity"],
                    inc["report_text"],
                    json.dumps(inc["related_commits"]),
                    json.dumps(inc["related_errors"]),
                    inc["cost_impact"],
                    inc["detected_at"],
                ),
            )
    print(f"  Seeded {len(incidents)} incidents.")


def seed_loops():
    now = _utcnow()
    loops = [
        {
            "trace_id": "a3f9d21b-" + str(uuid.uuid4())[:4] + "-demo",
            "loop_count": 22,
            "cost_burned": 0.28,
            "tool_pattern": json.dumps({"name": "retry-search", "count": 22}),
            "status": "active",
            "detected_at": (now - timedelta(minutes=47)).isoformat(),
        },
        {
            "trace_id": "b8c1e543-" + str(uuid.uuid4())[:4] + "-demo",
            "loop_count": 15,
            "cost_burned": 0.024,
            "tool_pattern": json.dumps({"name": "fetch_context", "count": 15}),
            "status": "active",
            "detected_at": (now - timedelta(hours=1, minutes=10)).isoformat(),
        },
        {
            "trace_id": "c2d4f897-" + str(uuid.uuid4())[:4] + "-demo",
            "loop_count": 18,
            "cost_burned": 0.19,
            "tool_pattern": json.dumps({"name": "retry-search", "count": 18}),
            "status": "killed",
            "kill_method": "slack_approval",
            "detected_at": (now - timedelta(hours=6)).isoformat(),
        },
    ]
    with memory.get_connection() as conn:
        for loop in loops:
            conn.execute(
                """INSERT INTO loop_detections
                   (trace_id, detected_at, loop_count, cost_burned, tool_pattern, status, kill_method)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    loop["trace_id"],
                    loop["detected_at"],
                    loop["loop_count"],
                    loop["cost_burned"],
                    loop["tool_pattern"],
                    loop["status"],
                    loop.get("kill_method"),
                ),
            )
    print(f"  Seeded {len(loops)} loop detections.")


def seed_approvals():
    now = _utcnow()
    entries = [
        {
            "action_type": "kill_loop",
            "anomaly_type": "loop_detected",
            "severity": "critical",
            "context": {"summary": "Agent loop: 22 generations on trace a3f9d21b, cost $0.28. Kill signal will terminate the trace.", "gen_count": 22, "trace_id": "a3f9d21b"},
            "status": "pending",
            "expires_at": (now + timedelta(hours=4)).isoformat(),
            "created_at": (now - timedelta(minutes=47)).isoformat(),
        },
        {
            "action_type": "create_issue",
            "anomaly_type": "drift_detected",
            "severity": "high",
            "context": {"summary": "Prompt drift on 'support-bot': schema_break, 80% fail rate. Will open GitHub issue and assign to @bob.", "feature": "support-bot"},
            "status": "pending",
            "expires_at": (now + timedelta(hours=4)).isoformat(),
            "created_at": (now - timedelta(hours=5, minutes=3)).isoformat(),
        },
        {
            "action_type": "create_issue",
            "anomaly_type": "cost_spike",
            "severity": "high",
            "context": {"summary": "Cost spike: $4.20/hr vs $0.80/hr baseline (5.3×). Will open GitHub issue tagged cost-regression.", "multiplier": 5.3},
            "status": "approved",
            "resolved_by": "demo_user",
            "expires_at": (now - timedelta(hours=1)).isoformat(),
            "created_at": (now - timedelta(hours=2, minutes=12)).isoformat(),
            "resolved_at": (now - timedelta(hours=1, minutes=55)).isoformat(),
        },
        {
            "action_type": "request_changes",
            "anomaly_type": "tool_failure",
            "severity": "medium",
            "context": {"summary": "Tool 'fetch_weather' output anomaly: 8B vs 420B average. Requesting PR changes on commit e4d7c92.", "tool": "fetch_weather"},
            "status": "rejected",
            "resolved_by": "demo_user",
            "expires_at": (now - timedelta(hours=5)).isoformat(),
            "created_at": (now - timedelta(hours=9, minutes=30)).isoformat(),
            "resolved_at": (now - timedelta(hours=9)).isoformat(),
        },
    ]
    with memory.get_connection() as conn:
        for e in entries:
            conn.execute(
                """INSERT INTO approval_queue
                   (action_type, anomaly_type, severity, context, status,
                    expires_at, created_at, resolved_by, resolved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    e["action_type"],
                    e["anomaly_type"],
                    e["severity"],
                    json.dumps(e["context"]),
                    e["status"],
                    e["expires_at"],
                    e["created_at"],
                    e.get("resolved_by"),
                    e.get("resolved_at"),
                ),
            )
    print(f"  Seeded {len(entries)} approval queue entries.")


def seed_drift():
    now = _utcnow()
    with memory.get_connection() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO schema_snapshots (feature_name, schema_json, sample_count, captured_at)
               VALUES (?, ?, ?, ?)""",
            (
                "support-bot",
                json.dumps({"response": "str", "confidence": "float", "category": "str"}),
                50,
                (now - timedelta(hours=6)).isoformat(),
            ),
        )
        conn.execute(
            """INSERT INTO drift_events
               (feature_name, detected_at, drift_type, severity, validation_fail_rate, details,
                blame_commit_sha, blame_commit_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "support-bot",
                (now - timedelta(hours=5, minutes=3)).isoformat(),
                "schema_break",
                "high",
                0.80,
                json.dumps({"missing_keys": ["response", "category"], "unexpected_keys": ["answer", "score"]}),
                "f1a8b33",
                "refactor: rewrite support-bot prompt to Q&A format",
            ),
        )
    print("  Seeded schema snapshot + drift event.")


def seed_sampling():
    memory.save_sampling_stats(
        total_traces=300,
        sampled_traces=47,
        dropped_traces=253,
        keep_reasons={"has_error": 12, "cost_spike": 8, "schema_failed": 3, "novel_pattern": 2, "high_gen": 22},
    )
    print("  Seeded sampling stats (300 traces, 85% noise dropped).")


def seed_file_risk():
    now = _utcnow()
    files = [
        ("agent/detectors/cost_detector.py", "d9c3e11", 3.40, 0, 0.82),
        ("agent/narrator.py", "f1a8b33", 0.05, 2, 0.61),
        ("api/routes/loops.py", "c7a2e81", 0.28, 1, 0.55),
        ("agent/detectors/drift_detector.py", "f1a8b33", 0.04, 4, 0.74),
        ("web/src/app/(app)/approvals/page.tsx", "b0f3d44", 0.0, 0, 0.12),
    ]
    with memory.get_connection() as conn:
        for path, sha, cost_d, err_d, risk in files:
            conn.execute(
                """INSERT INTO file_risk_history (file_path, commit_sha, cost_delta, error_delta, risk_score, change_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (path, sha, cost_d, err_d, risk, (now - timedelta(days=1)).isoformat()),
            )
    print(f"  Seeded {len(files)} file risk history entries.")


if __name__ == "__main__":
    print("=== Sentinel Demo Seeder (SQLite-only) ===")
    if _already_seeded():
        print("  Data already present — skipping.")
        sys.exit(0)

    seed_incidents()
    seed_loops()
    seed_approvals()
    seed_drift()
    seed_sampling()
    seed_file_risk()
    print("=== Done. ===")
