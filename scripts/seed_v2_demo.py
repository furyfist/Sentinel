"""
Seed all V2 demo data in one shot.

Creates:
  1. Loop scenario         — 15 GENERATION obs on one trace in 3 min
  2. Drift scenario        — 50 good obs + snapshot + 10 broken-schema obs
  3. Silent tool failure   — approval record simulating tool failure detection
  4. Approval queue        — 2 pending, 1 approved, 1 rejected
  5. Sampling baseline     — 300 synthetic sampling stats rows (show 85% reduction)

Usage:
  python scripts/seed_v2_demo.py
"""
import os
import sys
import uuid
import json
import random
import requests
import base64
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from agent.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
from agent import memory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _langfuse_ingest(events: list) -> None:
    auth = base64.b64encode(f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()).decode()
    resp = requests.post(
        f"{LANGFUSE_BASE_URL}/api/public/ingestion",
        json={"batch": events},
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        timeout=30,
    )
    if resp.status_code not in (200, 207):
        raise RuntimeError(f"Langfuse ingestion failed ({resp.status_code}): {resp.text[:200]}")


def seed_loop_scenario() -> str:
    """15 GENERATIONs on same trace within 3 minutes."""
    print("\n[1/5] Seeding loop scenario...")
    trace_id = str(uuid.uuid4())
    now_str = _utcnow().isoformat()
    loop_start = _utcnow() - timedelta(minutes=5)

    events = [{
        "id": str(uuid.uuid4()),
        "type": "trace-create",
        "timestamp": now_str,
        "body": {"id": trace_id, "name": "loop-scenario", "userId": "demo", "timestamp": loop_start.isoformat()},
    }]

    for i in range(15):
        start = loop_start + timedelta(seconds=i * 12)
        events.append({
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": now_str,
            "body": {
                "id": str(uuid.uuid4()),
                "traceId": trace_id,
                "name": "retry-search",
                "model": "gpt-4",
                "startTime": start.isoformat(),
                "endTime": (start + timedelta(seconds=4)).isoformat(),
                "usage": {"input": 800, "output": 200, "unit": "TOKENS"},
            },
        })

    _langfuse_ingest(events)
    memory.save_loop_detection(
        trace_id=trace_id,
        loop_count=15,
        cost_burned=0.024,
        tool_pattern=json.dumps({"name": "retry-search", "count": 15}),
    )
    print(f"  Done. trace_id={trace_id[:12]}…  loop saved to SQLite.")
    return trace_id


RESPONSES = [
    "I can help you with your billing query.",
    "Your shipment is on the way.",
    "Returns are accepted within 30 days.",
    "Let me check your account details.",
    "This is a known technical issue we are working on.",
]
CATEGORIES = ["billing", "shipping", "returns", "technical", "account"]


def _make_generation_events(trace_id: str, name: str, output: dict, start: datetime) -> list:
    now_str = _utcnow().isoformat()
    return [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": now_str,
            "body": {"id": trace_id, "name": name, "userId": "demo", "timestamp": start.isoformat()},
        },
        {
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": now_str,
            "body": {
                "id": str(uuid.uuid4()),
                "traceId": trace_id,
                "name": name,
                "model": "gpt-4o-mini",
                "startTime": start.isoformat(),
                "endTime": (start + timedelta(seconds=1)).isoformat(),
                "output": json.dumps(output),
                "usage": {"input": 200, "output": 80, "unit": "TOKENS"},
            },
        },
    ]


def seed_drift_scenario():
    """50 good observations + schema snapshot + 10 drifted observations."""
    print("\n[2/5] Seeding drift scenario...")

    batch = []
    base = _utcnow() - timedelta(hours=2)
    for i in range(50):
        start = base + timedelta(seconds=i * 60)
        output = {
            "response": random.choice(RESPONSES),
            "confidence": round(random.uniform(0.85, 0.99), 2),
            "category": random.choice(CATEGORIES),
        }
        batch.extend(_make_generation_events(str(uuid.uuid4()), "support-bot", output, start))
        if len(batch) >= 100:
            _langfuse_ingest(batch)
            batch = []
    if batch:
        _langfuse_ingest(batch)
    print("  50 good observations ingested.")

    good_samples = [
        json.dumps({"response": "sample", "confidence": 0.95, "category": "billing"}),
        json.dumps({"response": "sample2", "confidence": 0.90, "category": "shipping"}),
    ]
    memory.save_schema_snapshot(
        feature_name="support-bot",
        schema={"response": "str", "confidence": "float", "category": "str"},
        sample_count=len(good_samples),
    )
    print("  Schema snapshot saved to SQLite.")

    batch = []
    base2 = _utcnow() - timedelta(minutes=20)
    for i in range(10):
        start = base2 + timedelta(seconds=i * 30)
        output = {"answer": random.choice(RESPONSES), "score": round(random.uniform(0.85, 0.99), 2)}
        batch.extend(_make_generation_events(str(uuid.uuid4()), "support-bot", output, start))
    _langfuse_ingest(batch)
    print("  10 drifted observations ingested.")

    memory.save_drift_event(
        feature_name="support-bot",
        drift_type="schema_break",
        severity="high",
        validation_fail_rate=0.8,
        details={"missing_keys": ["response", "category"], "unexpected_keys": ["answer", "score"]},
    )
    print("  Drift event saved to SQLite.")


def seed_silent_failure():
    """Add a silent tool failure approval record to simulate detection."""
    print("\n[3/5] Seeding silent tool failure approval record...")
    trace_id = str(uuid.uuid4())
    aid = memory.save_approval(
        action_type="create_issue",
        anomaly_type="tool_failure",
        severity="high",
        context={
            "summary": f"Tool 'search_knowledge_base' returned 200 OK but Sentry logged "
                       f"JSONDecodeError 30s later on trace {trace_id[:12]}",
            "trace_id": trace_id,
            "tool_name": "search_knowledge_base",
            "strategy": "sentry_correlation",
        },
        expires_hours=4,
    )
    print(f"  Silent failure approval saved (id={aid}).")


def seed_approval_queue():
    """2 pending + 1 approved + 1 rejected approvals."""
    print("\n[4/5] Seeding approval queue...")

    memory.save_approval(
        action_type="kill_loop",
        anomaly_type="loop_detected",
        severity="critical",
        context={"summary": "Agent loop: 22 generations on trace abc123, cost $0.18", "gen_count": 22},
        expires_hours=4,
    )
    memory.save_approval(
        action_type="create_issue",
        anomaly_type="drift_detected",
        severity="high",
        context={"summary": "Prompt drift on 'invoice-parser': schema_break (75% fail rate)"},
        expires_hours=4,
    )

    approved_id = memory.save_approval(
        action_type="create_issue",
        anomaly_type="cost_spike",
        severity="high",
        context={"summary": "Cost spike: $4.20/hr vs $0.80/hr baseline (5.3x)"},
        expires_hours=4,
    )
    memory.update_approval(approved_id, status="approved", resolved_by="U01DEMO")

    rejected_id = memory.save_approval(
        action_type="request_changes",
        anomaly_type="tool_failure",
        severity="medium",
        context={"summary": "Tool 'fetch_weather' output anomaly: 8B vs 420B average"},
        expires_hours=4,
    )
    memory.update_approval(rejected_id, status="rejected", resolved_by="U02DEMO")

    print("  Approval queue: 2 pending, 1 approved, 1 rejected.")


def seed_sampling_baseline():
    """Save sampling stats showing 85% noise reduction from 300 traces."""
    print("\n[5/5] Seeding sampling baseline stats...")
    total = 300
    sampled = 47
    dropped = total - sampled
    keep_reasons = {
        "has_error": 12,
        "cost_spike": 8,
        "schema_failed": 3,
        "novel_pattern": 2,
        "high_gen": 22,
    }
    memory.save_sampling_stats(
        total_traces=total,
        sampled_traces=sampled,
        dropped_traces=dropped,
        keep_reasons=keep_reasons,
    )
    noise_pct = round(dropped / total * 100)
    print(f"  Saved: {sampled}/{total} kept, {noise_pct}% noise dropped.")
    print(f"  Keep reasons: {keep_reasons}")


if __name__ == "__main__":
    print("=== Sentinel V2 Demo Seeder ===")

    loop_trace_id = seed_loop_scenario()
    seed_drift_scenario()
    seed_silent_failure()
    seed_approval_queue()
    seed_sampling_baseline()

    print("\n=== All V2 demo data seeded. ===")
    print(f"\nLoop trace: {loop_trace_id}")
    print("Wait ~30s for Langfuse to index, then open http://localhost:3000")
    print("Run the loop detector:  .\\venv\\Scripts\\python -c \"from agent import coral_client, memory; from agent.detectors.loop_detector import LoopDetector; d = LoopDetector(coral_client, memory); print(d.detect_loops())\"")
