# Sentinel V2 — Testing Guide

Run all checks in order. Start the API and frontend first.

```bash
# Terminal 1 — API
cd c:/Users/himan/OneDrive/Desktop/Sentinel
.\venv\Scripts\uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd web && npm run dev

# Terminal 3 — ngrok (for Slack webhooks)
ngrok http 8000
# Set the printed URL as: Slack App → Interactivity → Request URL → https://<ngrok>/api/slack/actions
```

---

## Phase 1 — Webhook Infrastructure

### 1. Health check
```
GET http://localhost:8000/api/health
Expected: { "status": "ok", "coral": true }
```

### 2. Slack signature verification
```bash
# Should reject (missing headers)
curl -X POST http://localhost:8000/api/slack/actions
Expected: 403 Missing Slack headers

# Valid request (run via test script with real signing secret)
python scripts/test_webhook_flow.py
Expected: Slack message with Approve/Reject buttons appears in #incidents
```

### 3. Approve/Reject buttons
After running `test_webhook_flow.py`:
- Click **Approve** in Slack → message changes to "✅ Approved by @you"
- Verify in SQLite:
```bash
.\venv\Scripts\python -c "from agent import memory; print(memory.get_approvals())"
Expected: status = 'approved'
```
- Click **Reject** → status = 'rejected'

### 4. Loop kill button
After running `test_webhook_flow.py`:
- Click **Kill Loop** → message changes to "🛑 Loop kill acknowledged"
- Verify:
```bash
.\venv\Scripts\python -c "from agent import memory; print(memory.get_loop_detections())"
Expected: status = 'killed', kill_method = 'slack_button'
```

### 5. SQLite tables exist
```bash
.\venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('sentinel.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print([t[0] for t in tables])
"
Expected: loop_detections, schema_snapshots, drift_events, approval_queue, sampling_stats
```

### 6. AnomalyDetector class
```bash
.\venv\Scripts\python -c "
from agent.anomaly_detector import AnomalyDetector, AnomalyResult
d = AnomalyDetector()
results = d.run_all()
print('AnomalyDetector OK, results:', results)
"
Expected: no errors, returns empty list (no live data)
```

---

## Phase 2 — Loop Detection

### 7. Loop detector queries (requires Coral + Langfuse data)
```bash
python scripts/seed_loop_scenario.py
Expected: 15 GENERATION observations on same trace within 3 minutes
```

### 8. Loop detection via detector
```bash
.\venv\Scripts\python -c "
from agent import coral_client, memory
from agent.detectors.loop_detector import LoopDetector
detector = LoopDetector(coral_client, memory)
loops = detector.detect_loops()
print('Loops found:', len(loops))
for l in loops:
    print(' trace:', l['trace_id'], 'gens:', l['gen_count'], 'cost:', l['total_cost'])
"
Expected: at least 1 loop with gen_count >= 10
```

### 9. Loop fingerprint
```bash
.\venv\Scripts\python -c "
from agent import coral_client, memory
from agent.detectors.loop_detector import LoopDetector
detector = LoopDetector(coral_client, memory)
loops = detector.detect_loops()
if loops:
    fp = detector.fingerprint_loop(loops[0]['trace_id'])
    print('Fingerprint:', fp)
"
Expected: dict with most_repeated_name, repeat_count, cost_velocity
```

### 10. Loop alert fires to Slack
```bash
.\venv\Scripts\python -c "
from agent import coral_client, memory
from agent.config import SLACK_INCIDENTS_CHANNEL
from agent.detectors.loop_detector import LoopDetector
detector = LoopDetector(coral_client, memory)
detector.run(channel=SLACK_INCIDENTS_CHANNEL)
"
Expected: Slack message with loop info + Kill Loop button
```

### 11. Loop API endpoints
```
GET http://localhost:8000/api/loops/active
Expected: JSON array of active loop detections

GET http://localhost:8000/api/loops/history
Expected: JSON array of all loop detections

GET http://localhost:8000/api/loops/<trace_id>/fingerprint
Expected: JSON fingerprint dict
```

### 12. Dashboard loop widget
```
Open http://localhost:3000
Expected:
- "Active Loops" stat card appears (red value if > 0)
- Most recent loop shows trace_id, cost, and status
```

---

## Phase 3 — Prompt Drift Detection

### 13. Seed the drift scenario
```bash
python scripts/seed_drift_scenario.py
Expected: 50 good observations + snapshot captured + 10 drifted observations seeded
```

### 14. Run drift patrol (dry run)
```bash
.\venv\Scripts\python agent/modes/drift_patrol.py --dry-run
Expected:
- "support-bot" feature found
- Validation: N/20 passed, fail_rate > 15%
- Drift event saved to SQLite
- [DRY RUN] Would post to Slack
```

### 15. Drift events in SQLite
```bash
.\venv\Scripts\python -c "from agent import memory; print(memory.get_drift_events())"
Expected: at least 1 row with drift_type='schema_break', feature_name='support-bot'
```

### 16. Schema snapshots API
```
GET http://localhost:8000/api/quality/snapshots
Expected: JSON array including support-bot snapshot with keys: response, confidence, category
```

### 17. Drift events API
```
GET http://localhost:8000/api/quality/drift
Expected: JSON array with drift events
```

### 18. Feature validation API
```
GET http://localhost:8000/api/quality/feature/support-bot/validation
Expected: JSON with fail_rate > 0, failures list showing missing keys
```

### 19. Trigger scan via API
```
POST http://localhost:8000/api/quality/scan
Expected: {"status": "scan_started"}
Check server logs for drift patrol output
```

### 20. Validate blame commit (if commits exist)
```bash
.\venv\Scripts\python -c "
from agent import coral_client, memory
from agent.detectors.drift_detector import DriftDetector
d = DriftDetector(coral_client, memory)
blame = d.blame_commit('$(date -u +%Y-%m-%dT%H:%M:%SZ)')
print('Blame:', blame)
"
Expected: dict with sha + message, or None if no matching commits
```

---

## General Checks

### API routes all respond
```bash
curl http://localhost:8000/api/incidents
curl http://localhost:8000/api/risk/history
curl http://localhost:8000/api/digest/latest
curl http://localhost:8000/api/settings
curl http://localhost:8000/api/loops/active
```

### No import errors
```bash
.\venv\Scripts\python -c "
from api.main import app
from agent.anomaly_detector import AnomalyDetector
from agent.detectors.loop_detector import LoopDetector
from agent import memory
print('All imports OK')
"
```
