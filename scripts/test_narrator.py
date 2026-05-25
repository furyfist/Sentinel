"""Smoke test: verifies Groq narration and memory round-trips."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import narrator, memory

FAKE_INCIDENT = {
    "commits": [
        {"sha": "abc123", "message": "fix: increase max_tokens to 8000", "author": "furyfist", "date": "2026-05-25T10:00:00Z"}
    ],
    "errors": [
        {"title": "RateLimitError: Too many requests", "count": 15, "first_seen": "2026-05-25T10:05:00Z"}
    ],
    "cost": [
        {"hour": "2026-05-25T10:00:00Z", "hourly_cost": 4.20, "generation_count": 82}
    ],
}

FAKE_HISTORY = [
    {"file": "agent/modes/oncall_brain.py", "commit": "abc123", "cost_after": 4.20, "errors_after": 15},
    {"file": "agent/modes/oncall_brain.py", "commit": "def456", "cost_after": 1.10, "errors_after": 2},
]

FAKE_DIGEST = {
    "shipped": [{"title": "feat: add narrator module", "author": "furyfist", "additions": 80}],
    "errors": [{"title": "RateLimitError", "count": 15}],
    "cost_trend": [{"day": "2026-05-25", "daily_cost": 9.50}],
}

passed = 0
failed = 0


def check(label, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  OK  {label}")
        return result
    except Exception as e:
        print(f" FAIL {label}: {e}")
        failed += 1
        return None


print("--- narrator ---")

report = check("narrate_incident returns non-empty string", lambda: (
    r := narrator.narrate_incident(FAKE_INCIDENT, "cost_spike"),
    (None if r and len(r) > 10 else (_ for _ in ()).throw(ValueError("empty response"))),
    r
)[-1])

if report:
    passed += 1
    print(f"\n  Incident report preview:\n  {report[:200].strip()}...\n")

risk = check("narrate_pr_risk returns non-empty string", lambda: (
    r := narrator.narrate_pr_risk(FAKE_HISTORY, 82),
    (None if r and len(r) > 10 else (_ for _ in ()).throw(ValueError("empty response"))),
    r
)[-1])
if risk:
    passed += 1

digest = check("narrate_weekly_digest returns non-empty string", lambda: (
    r := narrator.narrate_weekly_digest(FAKE_DIGEST["shipped"], FAKE_DIGEST["errors"], FAKE_DIGEST["cost_trend"]),
    (None if r and len(r) > 10 else (_ for _ in ()).throw(ValueError("empty response"))),
    r
)[-1])
if digest:
    passed += 1

print("\n--- memory round-trips ---")

row_id = check("save_incident returns an id", lambda: memory.save_incident(
    detection_type="cost_spike",
    severity="high",
    report_text=report or "test report",
    related_commits=["abc123"],
    related_errors=["RateLimitError"],
    cost_impact=4.20,
))
if row_id:
    passed += 1

rows = check("get_incidents returns the saved row", lambda: memory.get_incidents(limit=1))
if rows:
    assert rows[0]["detection_type"] == "cost_spike", "wrong detection_type"
    passed += 1

bl_id = check("save_cost_baseline returns an id", lambda: memory.save_cost_baseline(4.20, 22.50))
if bl_id:
    passed += 1

baselines = check("get_baselines returns the saved row", lambda: memory.get_baselines(limit=1))
if baselines:
    assert baselines[0]["hourly_cost"] == 4.20, "wrong hourly_cost"
    passed += 1

fr_id = check("save_file_risk returns an id", lambda: memory.save_file_risk(
    "agent/modes/oncall_brain.py", "abc123", cost_delta=4.20, error_delta=15, risk_score=82.0
))
if fr_id:
    passed += 1

history = check("get_file_risk_history returns the saved row", lambda: memory.get_file_risk_history("agent/modes/oncall_brain.py"))
if history:
    assert history[0]["risk_score"] == 82.0, "wrong risk_score"
    passed += 1

print(f"\n{passed} passed, {failed} failed")
