"""Automated test suite for Sentinel V2 — runs without Coral or Slack."""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

PASS = 0
FAIL = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  PASS  {label}")


def fail(label, err):
    global FAIL
    FAIL += 1
    print(f"  FAIL  {label}: {err}")


print("\n=== Phase 1: Imports ===")
try:
    from api.main import app
    from agent.anomaly_detector import AnomalyDetector, AnomalyResult, detect_cost_spike
    from agent.detectors.loop_detector import LoopDetector
    from agent.detectors.drift_detector import DriftDetector
    from agent.detectors.tool_failure_detector import ToolFailureDetector
    from agent.governance.approval_gate import ApprovalGate
    from agent.sampling.smart_sampler import SmartSampler
    from agent.forensics.trace_reconstructor import TraceReconstructor
    from agent.forensics.incident_graph_builder import IncidentGraphBuilder
    from agent import memory
    ok("all core imports")
except Exception as e:
    fail("core imports", e)


print("\n=== Phase 2: SQLite Tables ===")
try:
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sentinel.db")
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    required = {"loop_detections", "schema_snapshots", "drift_events", "approval_queue", "sampling_stats"}
    missing = required - tables
    if missing:
        fail("required tables", f"missing: {missing}")
    else:
        ok(f"all required tables present ({len(tables)} total)")
    conn.close()
except Exception as e:
    fail("sqlite tables", e)


print("\n=== Phase 3: Memory CRUD ===")
try:
    aid = memory.save_approval(
        action_type="create_issue",
        anomaly_type="drift_detected",
        severity="high",
        context={"summary": "test drift"},
        expires_hours=4,
    )
    rec = memory.get_approval(aid)
    assert rec["status"] == "pending"
    assert rec["action_type"] == "create_issue"
    assert rec["anomaly_type"] == "drift_detected"
    ok("save_approval / get_approval")
except Exception as e:
    fail("save_approval", e)

try:
    memory.update_approval(aid, status="approved", resolved_by="tester")
    rec2 = memory.get_approval(aid)
    assert rec2["status"] == "approved"
    assert rec2["resolved_by"] == "tester"
    ok("update_approval status")
except Exception as e:
    fail("update_approval status", e)

try:
    memory.update_approval(aid, slack_ts="T123.456")
    rec3 = memory.get_approval(aid)
    assert rec3["slack_ts"] == "T123.456"
    ok("update_approval slack_ts")
except Exception as e:
    fail("update_approval slack_ts", e)

try:
    expired = memory.get_expired_approvals()
    ok(f"get_expired_approvals (found {len(expired)})")
except Exception as e:
    fail("get_expired_approvals", e)

try:
    sid = memory.save_loop_detection(trace_id="trace-test-001", loop_count=15, cost_burned=0.02, tool_pattern="{}")
    loops = memory.get_loop_detections(limit=5)
    assert any(l["trace_id"] == "trace-test-001" for l in loops)
    ok("save_loop_detection / get_loop_detections")
    memory.update_loop_detection("trace-test-001", status="killed", kill_method="auto")
    loops2 = memory.get_loop_detections(limit=5)
    killed = [l for l in loops2 if l["trace_id"] == "trace-test-001"]
    assert killed and killed[0]["status"] == "killed"
    ok("update_loop_detection")
except Exception as e:
    fail("loop detection CRUD", e)

try:
    memory.save_sampling_stats(total_traces=100, sampled_traces=30, dropped_traces=70, keep_reasons={"has_error": 10})
    stats = memory.get_sampling_stats(limit=1)
    assert stats and stats[0]["total_traces"] == 100
    ok("save/get sampling_stats")
except Exception as e:
    fail("sampling_stats CRUD", e)


print("\n=== Phase 4: AnomalyDetector ===")
try:
    from datetime import datetime, timezone
    d = AnomalyDetector()
    results = d.run_all()
    assert isinstance(results, list)
    ok(f"AnomalyDetector.run_all() returned list ({len(results)} items)")
except Exception as e:
    fail("AnomalyDetector.run_all", e)

try:
    r = AnomalyResult(
        type="loop_detected", severity="critical",
        detected_at=datetime.now(timezone.utc), description="test",
        metadata={"gen_count": 25, "trace_id": "abc"},
        requires_approval=False, suggested_action="kill_loop",
    )
    assert r.type == "loop_detected"
    assert r.metadata["gen_count"] == 25
    ok("AnomalyResult dataclass")
except Exception as e:
    fail("AnomalyResult", e)

try:
    assert detect_cost_spike(5.0, 1.0, 3.0) is True
    assert detect_cost_spike(2.0, 1.0, 3.0) is False
    assert detect_cost_spike(0.0, 0.0) is False
    ok("detect_cost_spike shim")
except Exception as e:
    fail("detect_cost_spike", e)


print("\n=== Phase 5: ApprovalGate ===")
try:
    from datetime import datetime, timezone
    gate = ApprovalGate()
    loop_high   = AnomalyResult("loop_detected", "critical", datetime.now(timezone.utc), "d", metadata={"gen_count": 25})
    loop_low    = AnomalyResult("loop_detected", "high",     datetime.now(timezone.utc), "d", metadata={"gen_count": 15})
    spike_big   = AnomalyResult("cost_spike",    "critical", datetime.now(timezone.utc), "d", metadata={"current_cost": 15.0})
    spike_small = AnomalyResult("cost_spike",    "high",     datetime.now(timezone.utc), "d", metadata={"current_cost": 5.0})
    assert gate.should_auto_act(loop_high)    is True
    assert gate.should_auto_act(loop_low)     is False
    assert gate.should_auto_act(spike_big)    is True
    assert gate.should_auto_act(spike_small)  is False
    ok("ApprovalGate.should_auto_act thresholds")
except Exception as e:
    fail("ApprovalGate.should_auto_act", e)

try:
    gate2 = ApprovalGate(memory=memory)
    from datetime import datetime, timezone
    anomaly = AnomalyResult("drift_detected", "high", datetime.now(timezone.utc), "schema break",
                            metadata={"feature": "bot"}, suggested_action="create_issue")
    aid2 = gate2.create_approval_request(anomaly)
    assert aid2 > 0
    rec = memory.get_approval(aid2)
    assert rec["status"] == "pending"
    ok("ApprovalGate.create_approval_request")
except Exception as e:
    fail("ApprovalGate.create_approval_request", e)

try:
    gate3 = ApprovalGate(memory=memory)
    gate3.expire_stale_approvals()
    ok("ApprovalGate.expire_stale_approvals (no error)")
except Exception as e:
    fail("ApprovalGate.expire_stale_approvals", e)


print("\n=== Phase 6: SmartSampler ===")
try:
    s = SmartSampler(keep_threshold=40)
    traces = [
        {"has_error": True,  "total_cost": 0.5,    "gen_count": 2},
        {"gen_count": 10,    "total_cost": 0.001},
        {"total_cost": 0.0001, "gen_count": 1},
        {"schema_failed": True, "total_cost": 0.01},
    ]
    kept, dropped = s.filter_traces(traces)
    assert len(kept) == 3, f"expected 3 kept, got {len(kept)}"
    assert len(dropped) == 1
    ok(f"SmartSampler.filter_traces (kept={len(kept)}, dropped={len(dropped)})")
except Exception as e:
    fail("SmartSampler.filter_traces", e)

try:
    reasons = s.get_reason_breakdown(kept)
    assert isinstance(reasons, dict)
    assert reasons.get("has_error", 0) >= 1
    ok("SmartSampler.get_reason_breakdown")
except Exception as e:
    fail("SmartSampler.get_reason_breakdown", e)

try:
    s2 = SmartSampler(memory=memory, keep_threshold=40)
    ok("SmartSampler init with memory")
except Exception as e:
    fail("SmartSampler init", e)


print("\n=== Phase 7: API Routes registered ===")
try:
    routes = {r.path for r in app.routes}
    required_routes = [
        "/api/health",
        "/api/incidents",
        "/api/loops/active",
        "/api/loops/history",
        "/api/quality/drift",
        "/api/quality/snapshots",
        "/api/quality/scan",
        "/api/approvals",
        "/api/approvals/stats",
        "/api/sampling/stats",
        "/api/sampling/policy",
        "/api/forensics/worst-traces",
        "/api/slack/actions",
    ]
    missing_routes = []
    for r in required_routes:
        if r not in routes:
            missing_routes.append(r)
    if missing_routes:
        fail("missing API routes", missing_routes)
    else:
        ok(f"all {len(required_routes)} required routes registered")
except Exception as e:
    fail("API routes check", e)


print("\n=== Phase 8: Middleware / Slack Verify ===")
try:
    from api.middleware.slack_verify import verify_slack_signature
    ok("slack_verify import OK")
except Exception as e:
    fail("slack_verify import", e)


print("\n=== Phase 9: Graph utilities ===")
try:
    from agent.forensics.trace_reconstructor import TraceReconstructor
    tr = TraceReconstructor(coral_client=None)
    ok("TraceReconstructor init")
except Exception as e:
    fail("TraceReconstructor", e)

try:
    from agent.forensics.incident_graph_builder import IncidentGraphBuilder
    igb = IncidentGraphBuilder(coral_client=None)
    ok("IncidentGraphBuilder init")
except Exception as e:
    fail("IncidentGraphBuilder", e)


print("\n=== Phase 10: Config values ===")
try:
    from agent.config import (
        SLACK_INCIDENTS_CHANNEL, COST_SPIKE_MULTIPLIER,
        AGENT_LOOP_GENERATION_THRESHOLD, SLACK_SIGNING_SECRET,
    )
    assert COST_SPIKE_MULTIPLIER > 0
    assert AGENT_LOOP_GENERATION_THRESHOLD > 0
    ok(f"config values (multiplier={COST_SPIKE_MULTIPLIER}, loop_threshold={AGENT_LOOP_GENERATION_THRESHOLD})")
except Exception as e:
    fail("config values", e)


print(f"\n{'='*40}")
print(f"Results: {PASS} PASS, {FAIL} FAIL")
if FAIL > 0:
    sys.exit(1)
