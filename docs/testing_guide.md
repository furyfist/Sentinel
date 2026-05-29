# Sentinel V2 — Manual Testing Checklist

All automated checks pass (23 Python unit tests, 15 HTTP endpoints, TypeScript clean).
These items require live services — Slack, Langfuse, and optionally GitHub.

Start services first:
```bash
# Terminal 1 — API
.\venv\Scripts\uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd web && npm run dev

# Terminal 3 — ngrok (for Slack webhooks)
ngrok http 8000
# Set printed URL in: Slack App → Interactivity → Request URL → https://<ngrok>/api/slack/actions
```

---

## 1. Slack Button Callbacks

```bash
python scripts/test_webhook_flow.py
```

- Slack message with Approve / Reject / Kill Loop buttons appears in #incidents
- Click **Approve** → message changes to "✅ Approved by @you", DB status = `approved`
- Click **Reject** → message changes to "❌ Rejected by @you", DB status = `rejected`
- Click **Kill Loop** → message changes to "🛑 Loop kill acknowledged", DB status = `killed`

Verify in SQLite:
```bash
.\venv\Scripts\python scripts\test_memory_crud.py
```
Output:
Loop detection CRUD: PASS
Active loops filtered: 0
Schema snapshot CRUD: PASS
Drift event CRUD: PASS

All memory CRUD checks: PASS

---

## 2. Langfuse Loop Detection

```bash
python scripts/seed_loop_scenario.py
```

Wait ~30s for Langfuse to index, then:
```
GET http://localhost:8000/api/loops/active
Expected: JSON array with at least 1 loop entry, gen_count >= 15
```

Also verify fingerprint:
```
GET http://localhost:8000/api/loops/<trace_id>/fingerprint
Expected: { most_repeated_name, repeat_count, cost_velocity }
```
Output:
Detection is working end-to-end. Calling /detect now only fires new alerts for unseen traces.
---

## 3. Prompt Drift Detection

```bash
python scripts/seed_drift_scenario.py
.\venv\Scripts\python agent/modes/drift_patrol.py --dry-run
```

Expected output:
- `support-bot` feature found
- Validation: N/20 passed, fail_rate > 15%
- Drift event saved to SQLite
- `[DRY RUN] Would post to Slack`

Verify:
```
GET http://localhost:8000/api/quality/drift
Expected: at least 1 row with drift_type='schema_break', feature_name='support-bot'

GET http://localhost:8000/api/quality/feature/support-bot/validation
Expected: { fail_rate > 0, failures list showing missing keys }
```
Output: Test 3 is passing end-to-end.
---

## 4. Forensics Graph Page

**Status: ON HOLD — Langfuse rate limit (429)**

Open `http://localhost:3000/forensics`

The `/api/forensics/worst-traces` query hits Langfuse via Coral and currently triggers a 429 rate limit:
```
Coral query failed: Error: Source rate limit exceeded (429)
Detail: rate limit exceeded; retry after 28s
```

The sidebar stays blank while the rate limit is active. All code fixes are in place (column names corrected, timeouts increased to 120s). Retry after the rate limit window clears (~30s between attempts).

Once rate limit clears, expected behavior:
- Sidebar shows worst traces ranked by total cost
- Click a trace → React Flow canvas renders nodes (generation/span/event) linked sequentially
- "View Incident Graph" button → loads cross-source graph for ±2h window
- MiniMap and Controls render correctly

---

## 5. Approvals Nav Badge

Create a pending approval then check the badge:
```bash
.\venv\Scripts\python -c "
from agent import memory
memory.save_approval(action_type='create_issue', anomaly_type='drift_detected', severity='high', context={'summary': 'badge test'}, expires_hours=4)
print('Pending approval created')
"
```

Open `http://localhost:3000` — the **Approvals** nav item should show a red badge with the pending count. Badge should update within 30 seconds without a page reload.

Output: yes it goes from 3 -> 4
---

## 6. Approvals Web Page

Open `http://localhost:3000/approvals`

- Tab bar: Pending | Approved | Rejected | Expired
- Pending cards show action type, severity badge, context summary, time remaining
- Click **Approve** on a pending card → card disappears, status updates
- Click **Reject** on a pending card → same
- Switch to Approved tab → resolved cards show who approved and when

---

## 7. GitHub Issue on Approval (requires GITHUB_TOKEN in .env)

Seed a `create_issue` approval and approve it via the web UI or Slack button.

Expected: a GitHub issue titled `[Sentinel] drift_detected — severity: high` is created in the configured repo.

Verify in GitHub or:
```bash
.\venv\Scripts\python -c "
from agent import memory
approvals = memory.get_approvals(status='approved')
print([a['action_type'] for a in approvals])
"
```

---

## 8. Full V2 Demo Seed

Run the all-in-one seeder for demo data:
```bash
python scripts/seed_v2_demo.py
```

Expected:
- Loop scenario seeded to Langfuse + SQLite
- Drift scenario seeded (50 good + 10 drifted observations) + snapshot
- Silent failure approval record added
- Approval queue: 2 pending, 1 approved, 1 rejected
- Sampling stats: 47/300 traces kept (85% noise dropped)

Open `http://localhost:3000` and verify:
- Dashboard shows sampling efficiency widget (47 of 300, 85% noise dropped)
- Dashboard shows drift status as "Drift" (amber)
- Active Loops card shows > 0 (after Langfuse indexes)
- Pending Approvals card shows 2

Ouptut: seems working to me
---

## 9. Incident Dependency Graph Tab

Open `http://localhost:3000/incidents/<id>` for any incident.

- Two tabs render: **Report** | **Dependency Graph**
- Click Dependency Graph → React Flow canvas loads the ±2h incident window
- Nodes visible with correct colors, MiniMap and Controls present

---

## 10. Slack Signing Secret Verification

With ngrok running and Slack connected:
```bash
# Should reject — missing headers
curl -X POST http://localhost:8000/api/slack/actions
Expected: 403 Missing Slack headers
```
Output:Test 10 passes