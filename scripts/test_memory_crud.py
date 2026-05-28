"""Quick memory CRUD checks for loop/drift/snapshot."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from agent import memory

memory.save_loop_detection("trace-abc-999", loop_count=18, cost_burned=0.055, tool_pattern='{"name":"retry"}')
loops = memory.get_loop_detections(limit=10)
found = [l for l in loops if l["trace_id"] == "trace-abc-999"]
assert found, "Loop not found"
assert found[0]["loop_count"] == 18
assert found[0]["status"] == "active"
memory.update_loop_detection("trace-abc-999", status="killed", kill_method="slack_button")
loops2 = memory.get_loop_detections(limit=10)
killed = [l for l in loops2 if l["trace_id"] == "trace-abc-999"]
assert killed[0]["status"] == "killed"
assert killed[0]["kill_method"] == "slack_button"
print("Loop detection CRUD: PASS")

active = memory.get_loop_detections(status="active", limit=5)
print(f"Active loops filtered: {len(active)}")

memory.save_schema_snapshot("feat-x", {"key": "str"}, sample_count=3)
snap = memory.get_schema_snapshot("feat-x")
assert snap and snap["feature_name"] == "feat-x"
print("Schema snapshot CRUD: PASS")

memory.save_drift_event("feat-x", "schema_break", "high", 0.75, {"missing": ["key"]})
evts = memory.get_drift_events(limit=5)
assert any(e["feature_name"] == "feat-x" for e in evts)
print("Drift event CRUD: PASS")

print("\nAll memory CRUD checks: PASS")
