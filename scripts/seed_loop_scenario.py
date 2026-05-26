"""
Seed a loop scenario in Langfuse: 15 GENERATION observations on the same trace
within 3 minutes, all with name='retry-search', model='gpt-4'.

Run after seeding:
  python scripts/seed_loop_scenario.py

Then verify detection:
  .\venv\Scripts\python -c "
  from agent import coral_client, memory
  from agent.detectors.loop_detector import LoopDetector
  d = LoopDetector(coral_client, memory)
  loops = d.detect_loops()
  print('Loops found:', len(loops))
  for l in loops:
      print(' ', l)
  "
"""
import os
import sys
import uuid
import requests
import base64
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from agent.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL


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


def seed_loop():
    trace_id = str(uuid.uuid4())
    now_str = _utcnow().isoformat()
    loop_start = _utcnow() - timedelta(minutes=5)

    print(f"Seeding loop scenario on trace_id: {trace_id}")
    print("  15 GENERATION observations, 12 seconds apart, name='retry-search', model='gpt-4'")

    events = [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": now_str,
            "body": {
                "id": trace_id,
                "name": "loop-scenario",
                "userId": "loop-demo",
                "timestamp": loop_start.isoformat(),
            },
        }
    ]

    for i in range(15):
        start = loop_start + timedelta(seconds=i * 12)
        end = start + timedelta(seconds=4)
        gen_id = str(uuid.uuid4())
        events.append({
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": now_str,
            "body": {
                "id": gen_id,
                "traceId": trace_id,
                "name": "retry-search",
                "model": "gpt-4",
                "startTime": start.isoformat(),
                "endTime": end.isoformat(),
                "usage": {"input": 800, "output": 200, "unit": "TOKENS"},
            },
        })

    _langfuse_ingest(events)
    print(f"  Ingested {len(events)} events to Langfuse.")
    print(f"\nTrace ID: {trace_id}")
    print("Wait ~30s for Langfuse to process, then run the loop detector.")
    return trace_id


if __name__ == "__main__":
    seed_loop()
