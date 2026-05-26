"""
Seed the prompt drift demo scenario in Langfuse.

Step 1: 50 observations with name='support-bot' and valid JSON:
        {"response": "...", "confidence": 0.95, "category": "billing"}

Step 2: Capture the schema snapshot from those 50 observations.

Step 3: 10 more observations where the output CHANGED structure:
        {"answer": "...", "score": 0.95}
        (keys renamed — 'response' gone, 'answer' added; 'category' gone)

Step 4: Run drift_patrol --dry-run to verify detection.

Usage:
  python scripts/seed_drift_scenario.py
  .\venv\Scripts\python agent/modes/drift_patrol.py --dry-run
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
from agent.detectors.drift_detector import DriftDetector
from agent import coral_client as coral

FEATURE_NAME = "support-bot"
CATEGORIES = ["billing", "shipping", "returns", "technical", "account"]
RESPONSES = [
    "I can help you with your billing query.",
    "Your shipment is on the way.",
    "Returns are accepted within 30 days.",
    "Let me check your account details.",
    "This is a known technical issue we are working on.",
]


def _utcnow():
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


def _make_generation(trace_id: str, name: str, output: dict, start: datetime) -> list:
    now_str = _utcnow().isoformat()
    gen_id = str(uuid.uuid4())
    end = start + timedelta(seconds=1)
    return [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": now_str,
            "body": {"id": trace_id, "name": name, "userId": "drift-demo", "timestamp": start.isoformat()},
        },
        {
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": now_str,
            "body": {
                "id": gen_id,
                "traceId": trace_id,
                "name": name,
                "model": "gpt-4o-mini",
                "startTime": start.isoformat(),
                "endTime": end.isoformat(),
                "output": json.dumps(output),
                "usage": {"input": 200, "output": 80, "unit": "TOKENS"},
            },
        },
    ]


def seed_good_observations(count: int = 50):
    """Seed observations with the original valid schema."""
    print(f"  Seeding {count} good observations (valid schema)...")
    batch = []
    base = _utcnow() - timedelta(hours=2)
    for i in range(count):
        start = base + timedelta(seconds=i * 60)
        output = {
            "response": random.choice(RESPONSES),
            "confidence": round(random.uniform(0.85, 0.99), 2),
            "category": random.choice(CATEGORIES),
        }
        events = _make_generation(str(uuid.uuid4()), FEATURE_NAME, output, start)
        batch.extend(events)
        if len(batch) >= 100:
            _langfuse_ingest(batch)
            batch = []
    if batch:
        _langfuse_ingest(batch)
    print(f"  Done. {count} observations seeded.")


def capture_snapshot():
    """Bootstrap the schema snapshot from the good observations."""
    print("  Capturing schema snapshot locally from known-good outputs...")
    good_samples = [
        json.dumps({"response": "sample", "confidence": 0.95, "category": "billing"}),
        json.dumps({"response": "sample2", "confidence": 0.90, "category": "shipping"}),
        json.dumps({"response": "sample3", "confidence": 0.88, "category": "returns"}),
    ]
    detector = DriftDetector(coral, memory)
    schema = detector.capture_schema_snapshot(FEATURE_NAME, good_samples)
    print(f"  Snapshot keys: {list(schema.keys())}")
    return schema


def seed_drifted_observations(count: int = 10):
    """Seed observations with the changed (drifted) schema."""
    print(f"  Seeding {count} drifted observations (keys renamed)...")
    batch = []
    base = _utcnow() - timedelta(minutes=20)
    for i in range(count):
        start = base + timedelta(seconds=i * 30)
        output = {
            "answer": random.choice(RESPONSES),
            "score": round(random.uniform(0.85, 0.99), 2),
        }
        events = _make_generation(str(uuid.uuid4()), FEATURE_NAME, output, start)
        batch.extend(events)
    _langfuse_ingest(batch)
    print(f"  Done. {count} drifted observations seeded.")


if __name__ == "__main__":
    print("\n=== Drift Scenario Seeder ===\n")

    print("[1/3] Seeding 50 good observations to Langfuse...")
    seed_good_observations(50)

    print("\n[2/3] Capturing schema snapshot...")
    capture_snapshot()

    print("\n[3/3] Seeding 10 drifted observations...")
    seed_drifted_observations(10)

    print("\n=== Done. Wait ~30s for Langfuse to process, then run: ===")
    print("  .\\venv\\Scripts\\python agent/modes/drift_patrol.py --dry-run")
    print("  or POST http://localhost:8000/api/quality/scan")
