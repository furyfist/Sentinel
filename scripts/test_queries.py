"""Smoke test: runs all 7 query library functions and prints row counts."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import query_library, coral_client
from agent.anomaly_detector import detect_cost_spike

QUERIES = [
    ("7.1 cost_spike_detection",       lambda: query_library.cost_spike_detection()),
    ("7.2 commit_to_cost_blame",        lambda: query_library.commit_to_cost_blame()),
    ("7.3 error_cascade_detection",     lambda: query_library.error_cascade_detection()),
    ("7.4 slack_incident_context",      lambda: query_library.slack_incident_context("2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")),
    ("7.5 pr_risk_historical",          lambda: query_library.pr_risk_historical()),
    ("7.6 weekly_digest_shipped",       lambda: query_library.weekly_digest_shipped()),
    ("7.7 agent_loop_detection",        lambda: query_library.agent_loop_detection()),
]

passed = 0
failed = 0

for name, fn in QUERIES:
    try:
        rows = fn()
        print(f"  OK  {name}: {len(rows)} rows")
        passed += 1
    except Exception as e:
        print(f" FAIL {name}: {e}")
        failed += 1

print(f"\n{passed} passed, {failed} failed")

# Exit criteria checks
print("\n--- anomaly_detector assertions ---")
assert detect_cost_spike(10.0, 2.0) is True,  "FAIL: detect_cost_spike(10.0, 2.0) should be True"
print("  OK  detect_cost_spike(10.0, 2.0) -> True")
assert detect_cost_spike(1.0, 2.0) is False, "FAIL: detect_cost_spike(1.0, 2.0) should be False"
print("  OK  detect_cost_spike(1.0, 2.0) -> False")

print("\n--- coral_client error handling ---")
try:
    coral_client.query("THIS IS NOT VALID SQL AT ALL")
    print(" FAIL coral_client.query(bad sql) should have raised RuntimeError")
except RuntimeError as e:
    print(f"  OK  bad SQL raises RuntimeError: {str(e)[:80]}")

print("\nDone.")
