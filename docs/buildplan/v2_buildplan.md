# Sentinel V2 — Comprehensive Build Plan

> **5 Industry Problems. 6 Phases. 1 Agent.**
> **Window:** May 27–31, 2026 (5 days)
> **Builder:** Himanshu (solo)
> **Philosophy:** Ship everything. Rough edges > missing features.
> **Hackathon:** Pirates of the Coral-bean — Track 1: Enterprise Agent

---

## The Five Problems This Plan Solves

| # | Problem | Industry Pain | What Sentinel Does |
|---|---|---|---|
| P1 | Agent Loop Cost Explosions | Multi-agent retry loops burn $400 at 3am before anyone notices | Detects loop patterns in Langfuse traces via Coral SQL, fires kill signal + interactive Slack alert |
| P2 | Prompt Drift & Fragility | Minor prompt changes silently break JSON parsing downstream | Maintains output schema snapshots per feature, validates every trace, blames the commit that broke it |
| P3 | Silent Tool Call Failures | Tool returns `200 OK` but output is semantically garbage | Semantic validation layer on tool outputs + cross-reference with Sentry errors in the same trace window |
| P4 | No Human-in-the-Loop Governance | Agents execute high-risk actions without checkpoints | Interactive Slack approval gates with Approve/Reject buttons, pending approvals queue in web UI |
| P5 | Telemetry Data Saturation | "Log everything" breaks observability budgets | Smart tail sampling via Coral query scoring — keep errors, cost spikes, and novel patterns; drop noise |

---

## What Gets Built (Total New Surface Area)

### Backend (Python)
- 1 webhook infrastructure module (Slack interactive + GitHub webhooks)
- 5 detection/analysis modules (one per problem)
- 4 new API route files
- 2 new agent modes
- Refactored anomaly detector (class-based, multi-type)
- Extended SQLite schema (5 new tables)

### Frontend (Next.js)
- 1 new page: Forensics (React Flow dependency graph)
- 1 new page: Approvals (HITL governance queue)
- Extended dashboard (loop alerts, drift status, sampling stats)
- Extended incidents page (dependency graph tab)

### Infrastructure
- Slack interactivity endpoint (`/api/slack/actions`)
- React Flow integration (`@xyflow/react` v12.10.2)
- 2 new Coral sources (PagerDuty, Linear)

---

## New Dependencies

```
# Python (add to requirements.txt)
numpy                          # Forecasting / statistics
hashlib                        # Built-in — args deduplication
hmac                           # Built-in — Slack signature verification

# Node (add to web/package.json)
@xyflow/react@^12.10.2         # React Flow v12 — dependency graph
```

**Important:** The old `reactflow` package is deprecated. The current package is `@xyflow/react` with named imports:
```tsx
import { ReactFlow, MiniMap, Controls, Background } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
```

---

## New Coral Sources

```bash
# PagerDuty — already bundled in Coral
# Requires: API key from app.pagerduty.com → User Settings → API Access
PAGERDUTY_API_KEY=xxx coral source add pagerduty

# Linear — already bundled in Coral
# Requires: API key from linear.app → Settings → API → Personal API keys
LINEAR_API_KEY=lin_api_xxx coral source add linear

# Verify
coral sql "SELECT schema_name, table_name FROM coral.tables WHERE schema_name IN ('pagerduty', 'linear') ORDER BY 1, 2"
```

**Total sources after V2: 7** (GitHub, Sentry, Datadog, Slack, Langfuse, PagerDuty, Linear)

---

## New SQLite Schema (add to memory.py)

```sql
-- P1: Agent loop tracking
CREATE TABLE IF NOT EXISTS loop_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    loop_count INTEGER,
    cost_burned REAL,
    tool_pattern TEXT,             -- JSON: repeated tool name + args hash
    status TEXT DEFAULT 'active',  -- active | killed | acknowledged
    kill_method TEXT,              -- slack_button | auto | timeout
    slack_ts TEXT                  -- Slack message ts for button tracking
);

-- P2: Schema snapshots for drift detection
CREATE TABLE IF NOT EXISTS schema_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL,    -- maps to langfuse observation name
    schema_json TEXT NOT NULL,     -- JSON schema of expected output shape
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sample_count INTEGER DEFAULT 0,
    UNIQUE(feature_name)
);

CREATE TABLE IF NOT EXISTS drift_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    drift_type TEXT,              -- schema_break | score_regression | format_change
    severity TEXT,                -- low | medium | high | critical
    blame_commit_sha TEXT,
    blame_commit_message TEXT,
    validation_fail_rate REAL,
    details TEXT                   -- JSON: specific failures
);

-- P4: HITL approval queue
CREATE TABLE IF NOT EXISTS approval_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,     -- kill_loop | create_issue | request_changes | post_rca
    context TEXT NOT NULL,         -- JSON: full context for the reviewer
    status TEXT DEFAULT 'pending', -- pending | approved | rejected | expired
    resolved_at TIMESTAMP,
    resolved_by TEXT,              -- Slack user ID
    slack_channel TEXT,
    slack_ts TEXT,                 -- Message ts for button reference
    expires_at TIMESTAMP          -- Auto-expire after N hours
);

-- P5: Sampling policy + stats
CREATE TABLE IF NOT EXISTS sampling_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_traces INTEGER,
    sampled_traces INTEGER,
    dropped_traces INTEGER,
    keep_reasons TEXT              -- JSON: {"error": 12, "cost_spike": 3, "novel": 5}
);
```

---

# PHASE 1 — Webhook Infrastructure + Anomaly Detector Refactor

> **Goal:** Build the write-back plumbing that all 5 problems need. Without this, nothing is interactive.

### Step 1.1 — Add Slack Signing Secret to environment

Add `SLACK_SIGNING_SECRET` to `.env`. Get it from:
Slack App → Settings → Basic Information → App Credentials → Signing Secret

```env
SLACK_SIGNING_SECRET=your_signing_secret_here
```

### Step 1.2 — Build Slack signature verification middleware

File: `api/middleware/slack_verify.py`

```python
import hashlib
import hmac
import time
from fastapi import Request, HTTPException

async def verify_slack_signature(request: Request, signing_secret: str):
    """
    Verify incoming Slack request using HMAC-SHA256.
    Slack sends: X-Slack-Signature, X-Slack-Request-Timestamp headers.
    Body is URL-encoded (not JSON).
    Must respond within 3 seconds or Slack retries.
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Reject requests older than 5 minutes (replay attack prevention)
    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request too old")

    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    return body
```

### Step 1.3 — Build Slack actions endpoint

File: `api/routes/slack_actions.py`

```python
POST /api/slack/actions
```

This is the single endpoint Slack sends ALL interactive payloads to.
Set this URL in Slack App → Interactivity & Shortcuts → Request URL.

The payload arrives as `application/x-www-form-urlencoded` with a `payload` field containing JSON.

Key action IDs to handle:
- `sentinel_approve_{approval_id}` → approve a queued action
- `sentinel_reject_{approval_id}` → reject a queued action
- `sentinel_kill_loop_{trace_id}` → acknowledge a loop kill

For each action:
1. Parse the payload
2. Look up the approval_queue row by ID
3. Update status to approved/rejected
4. If approved → execute the action (create issue, post RCA, etc.)
5. If rejected → log and close
6. Update the original Slack message to show the result (use `response_url` from payload)
7. Return `200 OK` immediately (Slack requires < 3 seconds)

### Step 1.4 — Upgrade slack_poster.py with Block Kit interactive messages

Extend the existing poster to send messages with buttons:

```python
def post_approval_request(channel: str, approval_id: int, action_type: str, context: dict):
    """Post a message with Approve/Reject buttons."""
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🚨 Sentinel needs approval*\nAction: {action_type}\n{context.get('summary', '')}"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve"},
                    "style": "primary",
                    "action_id": f"sentinel_approve_{approval_id}",
                    "value": str(approval_id)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "action_id": f"sentinel_reject_{approval_id}",
                    "value": str(approval_id)
                }
            ]
        }
    ]
    # ... post via chat.postMessage
```

### Step 1.5 — Refactor anomaly_detector.py to class-based multi-type

Current: flat functions.
New: `AnomalyDetector` class with pluggable detection methods.

```python
@dataclass
class AnomalyResult:
    type: str              # "loop_detected", "drift_detected", "tool_failure", etc.
    severity: str          # "low", "medium", "high", "critical"
    detected_at: datetime
    description: str
    metadata: dict
    requires_approval: bool  # True → goes to HITL queue instead of auto-acting
    suggested_action: str    # "kill_loop", "create_issue", "request_changes", etc.

class AnomalyDetector:
    def __init__(self, coral_client, memory, config):
        self.coral = coral_client
        self.memory = memory
        self.config = config

    def detect_agent_loop(self) -> AnomalyResult | None: ...
    def detect_prompt_drift(self) -> AnomalyResult | None: ...
    def detect_silent_tool_failure(self) -> AnomalyResult | None: ...
    def detect_cost_spike(self) -> AnomalyResult | None: ...

    def run_all(self) -> list[AnomalyResult]:
        """Run all detectors, return list of anomalies found."""
        detectors = [
            self.detect_agent_loop,
            self.detect_prompt_drift,
            self.detect_silent_tool_failure,
            self.detect_cost_spike,
        ]
        results = []
        for detector in detectors:
            result = detector()
            if result:
                results.append(result)
        return results
```

### Step 1.6 — Add new SQLite tables to memory.py

Add all 5 new tables from the schema above. Run migrations on startup.

### Step 1.7 — Add PagerDuty + Linear sources to Coral

Run the two `coral source add` commands. Verify with `coral.tables`.

### Step 1.8 — Wire Slack actions route into api/main.py

```python
from api.routes.slack_actions import router as slack_router
app.include_router(slack_router, prefix="/api/slack")
```

### Step 1.9 — Test the webhook flow end-to-end

1. Start FastAPI server
2. Use ngrok to expose locally: `ngrok http 8000`
3. Set ngrok URL as Slack's Interactivity Request URL: `https://xxx.ngrok.io/api/slack/actions`
4. Post a test message with buttons via `post_approval_request()`
5. Click Approve in Slack → verify the callback hits your endpoint
6. Check SQLite → approval_queue row should update to "approved"

**Phase 1 is done when:** clicking a Slack button updates state in SQLite and the original message changes to show the result.

---

# PHASE 2 — Agent Loop Cost Explosion Detection (Problem 1)

> **Goal:** Detect loop patterns in Langfuse traces, fire alerts, offer kill signal.

### Step 2.1 — Build agent/detectors/loop_detector.py

The core detection logic. Queries Langfuse observations via Coral, identifies traces with suspiciously high generation counts:

```python
def detect_loops(self) -> list[dict]:
    """
    A loop looks like:
    - Same traceId with 10+ GENERATION observations in < 60 seconds
    - Same observation name repeated 5+ times in a trace
    - Same tool args hash appearing 3+ times (dedupe detection)
    """
    # Q: traces with abnormal generation counts
    results = self.coral.query("""
        SELECT
            traceId,
            COUNT(*) as gen_count,
            MIN(startTime) as first_gen,
            MAX(startTime) as last_gen,
            SUM(calculatedTotalCost) as total_cost,
            COUNT(DISTINCT name) as unique_names
        FROM langfuse.observations
        WHERE type = 'GENERATION'
            AND startTime > NOW() - INTERVAL '2 hours'
        GROUP BY traceId
        HAVING COUNT(*) > 8
        ORDER BY gen_count DESC
        LIMIT 20
    """)
    # ...
```

### Step 2.2 — Build loop fingerprinting

For each suspicious trace, pull the full observation chain and compute:
- `name_histogram`: how many times each observation name appears (catches "the agent called `search` 15 times")
- `args_hash_duplicates`: how many times the same tool was called with identical arguments (catches retry loops)
- `cost_velocity`: cost per minute during the loop

```python
def fingerprint_loop(self, trace_id: str) -> dict:
    observations = self.coral.query(f"""
        SELECT name, startTime, calculatedTotalCost, model
        FROM langfuse.observations
        WHERE traceId = '{trace_id}'
        ORDER BY startTime ASC
    """)
    # Count name repetitions
    name_counts = Counter(obs['name'] for obs in observations)
    most_repeated = name_counts.most_common(1)[0]

    # Cost velocity (dollars per minute)
    if len(observations) >= 2:
        time_span = (observations[-1]['startTime'] - observations[0]['startTime']).total_seconds() / 60
        cost_velocity = sum(o['calculatedTotalCost'] or 0 for o in observations) / max(time_span, 0.1)
    ...
```

### Step 2.3 — Build loop alert with kill signal

When a loop is detected:
1. Calculate severity based on cost velocity and generation count
2. If cost > threshold from settings → `requires_approval = False` (auto-kill)
3. If cost < threshold → `requires_approval = True` (ask human via Slack)
4. Create entry in `loop_detections` table
5. Post interactive Slack message with loop details + Kill/Ignore buttons
6. If auto-kill: post non-interactive alert + create GitHub issue

### Step 2.4 — Wire into anomaly_detector.detect_agent_loop()

The existing method gets replaced with the new loop_detector logic.
Returns `AnomalyResult` with `type="loop_detected"`.

### Step 2.5 — Add loop detection query to query_library.py

Add Q16 (loop detection) and Q17 (loop fingerprinting) as named queries.

### Step 2.6 — Add API route for loop data

File: `api/routes/loops.py`
- `GET /api/loops/active` → currently active loops from SQLite
- `GET /api/loops/history` → past loop detections with outcomes
- `GET /api/loops/{trace_id}/fingerprint` → live fingerprint via Coral query

### Step 2.7 — Extend dashboard with loop alert widget

Add to the main dashboard page:
- "Active Loops" card showing count of active loops (red if > 0)
- Most recent loop: trace_id, cost burned, status (active/killed/acknowledged)
- Link to forensics page for the trace

### Step 2.8 — Test with seeded data

Seed a loop in Langfuse: 15 GENERATION observations on the same trace within 3 minutes, all with name="retry-search", model="gpt-4".

Run the detector. Verify it fires. Verify Slack message appears with buttons. Click Kill. Verify state updates.

**Phase 2 is done when:** a seeded loop triggers a Slack alert with Kill/Ignore buttons that actually work.

---

# PHASE 3 — Prompt Drift & Fragility Detection (Problem 2)

> **Goal:** Catch when a prompt change breaks output structure before users report it.

### Step 3.1 — Build agent/detectors/drift_detector.py

Two detection strategies:

**Strategy A — Schema Contract Testing:**
- For each unique observation `name` (which maps to a feature/prompt), maintain a JSON schema snapshot of what valid output looks like
- On each scan, validate the latest observations' outputs against the snapshot
- If validation fail rate crosses threshold (e.g., > 15%) → drift detected

**Strategy B — Output Score Regression:**
- Pull Langfuse scores (if available) and check for rolling average decline
- Compare last 24h average vs 7-day baseline
- If delta > 0.1 → flag as regression

### Step 3.2 — Build schema snapshot capture

```python
def capture_schema_snapshot(self, feature_name: str, sample_outputs: list[str]) -> dict:
    """
    Analyze N sample outputs for a feature.
    Derive a JSON schema that describes the common structure.
    Store in schema_snapshots table.

    Simple approach: if output is JSON, infer key names and types.
    If output is plain text, store regex pattern for structure.
    """
    schemas = []
    for output in sample_outputs:
        try:
            parsed = json.loads(output)
            schema = self._infer_schema(parsed)  # recursive key-type extraction
            schemas.append(schema)
        except json.JSONDecodeError:
            schemas.append({"type": "text", "pattern": self._infer_pattern(output)})

    consensus_schema = self._merge_schemas(schemas)
    self.memory.save_schema_snapshot(feature_name, consensus_schema)
    return consensus_schema
```

### Step 3.3 — Build validation runner

```python
def validate_observations(self, feature_name: str, observations: list[dict]) -> dict:
    """
    Validate each observation's output against the stored schema snapshot.
    Returns: { "total": 20, "passed": 17, "failed": 3, "fail_rate": 0.15, "failures": [...] }
    """
    snapshot = self.memory.get_schema_snapshot(feature_name)
    if not snapshot:
        return {"status": "no_snapshot", "feature": feature_name}

    passed, failed, failures = 0, 0, []
    for obs in observations:
        output = obs.get("output", "")
        if self._validate_against_schema(output, snapshot):
            passed += 1
        else:
            failed += 1
            failures.append({
                "observation_id": obs["id"],
                "trace_id": obs["traceId"],
                "expected": snapshot,
                "got": self._describe_mismatch(output, snapshot)
            })
    ...
```

### Step 3.4 — Build commit blame for drift events

When drift is detected, JOIN with GitHub commits to find the commit closest in time that touched prompt-related files:

```sql
SELECT
    g.sha,
    g.message,
    g.author__login,
    g.committed_date
FROM github.commits g
WHERE g.owner = '{owner}'
    AND g.repo = '{repo}'
    AND g.committed_date BETWEEN '{drift_start}' - INTERVAL '48 hours' AND '{drift_start}'
    AND (g.message ILIKE '%prompt%'
         OR g.message ILIKE '%system%'
         OR g.message ILIKE '%template%')
ORDER BY g.committed_date DESC
LIMIT 5
```

### Step 3.5 — Wire into anomaly_detector.detect_prompt_drift()

Returns `AnomalyResult` with `type="drift_detected"`, includes blame commit if found.
Always sets `requires_approval = True` — drift events need human review before any action.

### Step 3.6 — New agent mode: modes/drift_patrol.py

Scheduled job (runs every 4 hours):
1. Query unique observation names from last 24h
2. For each feature: pull latest 20 observations' outputs
3. If no schema snapshot exists → capture one (bootstrap)
4. If snapshot exists → validate against it
5. If fail rate > threshold → detect drift → blame commit → create drift_event
6. Narrate the drift + blame → post to Slack (with Acknowledge button)
7. Store in SQLite for web UI

### Step 3.7 — Add API routes

File: `api/routes/quality.py`
- `GET /api/quality/snapshots` → all schema snapshots
- `GET /api/quality/drift` → drift events from SQLite
- `POST /api/quality/scan` → trigger a drift scan now
- `GET /api/quality/feature/{name}/validation` → live validation for a specific feature

### Step 3.8 — Seed drift scenario for demo

1. Seed 50 observations with name="support-bot" and valid JSON output: `{"response": "...", "confidence": 0.95, "category": "billing"}`
2. Capture schema snapshot
3. Seed 10 more observations where the output structure changed: `{"answer": "...", "score": 0.95}` (keys renamed)
4. Push a GitHub commit with message "refactor: update support bot system prompt"
5. Run drift_patrol → should detect the schema break and blame the commit

**Phase 3 is done when:** drift patrol detects the seeded schema break, blames the correct commit, and posts to Slack.

---

# PHASE 4 — Silent Tool Call Failures + Forensics Graph (Problem 3)

> **Goal:** Detect semantically incorrect tool outputs + build the visual dependency graph.

### Step 4.1 — Build agent/detectors/tool_failure_detector.py

Three validation strategies for tool call outputs:

**Strategy A — Schema validation** (fast, deterministic):
If the tool output claims to be JSON but isn't valid JSON → failure.
If the JSON is valid but missing expected keys → failure.

**Strategy B — Sentry cross-reference** (Coral JOIN):
If errors appeared in Sentry within the same trace window, the "successful" tool call was likely involved:

```sql
SELECT
    o.traceId,
    o.name as tool_name,
    o.level,
    o.statusMessage,
    s.title as sentry_error,
    s.count as error_count,
    s.first_seen as error_start
FROM langfuse.observations o
JOIN sentry.issues s
    ON s.first_seen BETWEEN o.startTime AND o.startTime + INTERVAL '5 minutes'
WHERE o.type = 'SPAN'
    AND o.level = 'DEFAULT'     -- "successful" tools only
    AND o.startTime > NOW() - INTERVAL '6 hours'
    AND s.count > 2
```

**Strategy C — Output anomaly detection** (lightweight):
Compare output length against historical average. If a tool that normally returns 500 chars suddenly returns 12 → anomalous. If a tool that normally returns structured data returns a generic error string → failure.

### Step 4.2 — Wire into anomaly_detector.detect_silent_tool_failure()

Returns `AnomalyResult` with correlated Sentry errors if found.
Sets `requires_approval = True` — needs human to verify if the tool failure is real.

### Step 4.3 — Build forensics/trace_reconstructor.py

Pull all observations for a trace and build a parent-child tree:

```python
def reconstruct_trace(self, trace_id: str) -> dict:
    observations = self.coral.query(f"""
        SELECT
            id, traceId, parentObservationId, name, type,
            model, startTime, endTime,
            calculatedTotalCost,
            usage__promptTokens, usage__completionTokens,
            level, statusMessage
        FROM langfuse.observations
        WHERE traceId = '{trace_id}'
        ORDER BY startTime ASC
    """)

    nodes = []
    edges = []
    for obs in observations:
        node_type = "generation" if obs["type"] == "GENERATION" else "span" if obs["type"] == "SPAN" else "event"
        nodes.append({
            "id": obs["id"],
            "type": node_type,
            "data": {
                "label": obs["name"],
                "model": obs.get("model", ""),
                "cost": obs.get("calculatedTotalCost", 0),
                "tokens": (obs.get("usage__promptTokens", 0) or 0) + (obs.get("usage__completionTokens", 0) or 0),
                "status": obs.get("level", "DEFAULT"),
                "is_error": obs.get("level") in ["ERROR", "WARNING"],
            },
            "position": {"x": 0, "y": 0}  # auto-layout on frontend
        })
        if obs.get("parentObservationId"):
            edges.append({
                "id": f"e-{obs['parentObservationId']}-{obs['id']}",
                "source": obs["parentObservationId"],
                "target": obs["id"],
                "animated": obs.get("level") == "ERROR",
            })
    return {"nodes": nodes, "edges": edges}
```

### Step 4.4 — Build forensics/incident_graph_builder.py

The cross-source causal graph — joins multiple data sources for a time window:

```python
def build_incident_graph(self, window_start: str, window_end: str, owner: str, repo: str) -> dict:
    """
    Node types: commit, error, trace, message, incident
    Edges: caused_by, amplified, discussed, triggered

    Each node carries enough metadata for the React Flow custom node to render:
    - color (by type)
    - label
    - detail text
    - severity indicator
    """
    # Fetch from 4 sources via Coral
    commits = self.coral.query(COMMITS_IN_WINDOW_QUERY)
    errors = self.coral.query(SENTRY_IN_WINDOW_QUERY)
    traces = self.coral.query(EXPENSIVE_TRACES_IN_WINDOW_QUERY)
    messages = self.coral.query(SLACK_IN_WINDOW_QUERY)

    nodes, edges = [], []

    # Build commit nodes
    for c in commits:
        nodes.append({"id": f"commit-{c['sha'][:8]}", "type": "commit", "data": {...}, "position": {"x": 0, "y": 0}})

    # Build error nodes + edges from commits
    for e in errors:
        nodes.append({"id": f"error-{e['id']}", "type": "error", "data": {...}, ...})
        # Find which commit likely caused this error (closest prior commit)
        closest_commit = find_closest_prior(commits, e['first_seen'])
        if closest_commit:
            edges.append({
                "id": f"e-commit-error-{e['id']}",
                "source": f"commit-{closest_commit['sha'][:8]}",
                "target": f"error-{e['id']}",
                "label": f"{time_delta(closest_commit['committed_date'], e['first_seen'])} later",
            })

    # Build cost spike nodes + edges from errors
    # Build slack message nodes + edges from errors/commits
    ...
    return {"nodes": nodes, "edges": edges, "metadata": {...}}
```

### Step 4.5 — Add forensics API routes

File: `api/routes/forensics.py`
- `GET /api/forensics/trace/{trace_id}` → single trace graph (from trace_reconstructor)
- `GET /api/forensics/incident?start={}&end={}` → cross-source incident graph
- `GET /api/forensics/worst-traces` → top 10 most expensive traces (by cost)

### Step 4.6 — Install @xyflow/react in web project

```bash
cd web
npm install @xyflow/react
```

### Step 4.7 — Build custom React Flow node components

File: `web/src/components/features/graph/`

4 custom node types:
```tsx
// commit-node.tsx — indigo background, shows sha[:8] + message
// error-node.tsx — red background, shows error title + count
// trace-node.tsx — amber background, shows cost + generation count
// message-node.tsx — teal background, shows slack message preview
```

Each node component receives `data` via React Flow props. Size: ~30 lines each.

### Step 4.8 — Build forensics page

File: `web/src/app/forensics/page.tsx`

Layout:
- Left sidebar: list of worst traces (clickable)
- Main area: React Flow canvas
- Click a trace → loads single trace graph
- "View Incident Graph" button → loads cross-source graph for the trace's time window
- Custom node colors, animated error edges, zoom/pan controls

### Step 4.9 — Add dependency graph tab to incidents page

Extend `web/src/app/incidents/page.tsx`:
- New tab: "Dependency Graph"
- When viewing an incident, load the cross-source graph for that incident's time window
- Reuse the same React Flow components from forensics page

### Step 4.10 — Auto-layout nodes

React Flow nodes need positions. Use a simple horizontal tier layout:
```typescript
function autoLayout(nodes: Node[], edges: Edge[]): Node[] {
    // Tier 0: commits (leftmost)
    // Tier 1: errors (center-left)
    // Tier 2: traces/cost (center-right)
    // Tier 3: slack messages (rightmost)
    const tiers = { commit: 0, error: 200, trace: 400, message: 600 };
    const yCounters = { commit: 0, error: 0, trace: 0, message: 0 };

    return nodes.map(node => ({
        ...node,
        position: {
            x: tiers[node.type] || 0,
            y: (yCounters[node.type]++) * 120
        }
    }));
}
```

### Step 4.11 — Test with seeded incident

Use the existing seeded data from v1:
1. Load the forensics page
2. Click the worst trace → verify graph renders
3. Click "View Incident Graph" → verify 4-source graph renders
4. Verify node colors match types
5. Verify edge labels show time deltas

**Phase 4 is done when:** the React Flow graph renders a multi-source incident with commit → error → cost → slack nodes, and clicking a node shows its details.

---

# PHASE 5 — Human-in-the-Loop Governance (Problem 4)

> **Goal:** Route high-risk actions through human approval before execution.

### Step 5.1 — Build agent/governance/approval_gate.py

The central approval routing logic:

```python
class ApprovalGate:
    """
    Decides whether an AnomalyResult should be auto-acted on
    or routed to a human for approval.

    Rules:
    - cost_spike with cost > $10     → auto-kill + notify
    - cost_spike with cost < $10     → requires approval
    - loop_detected with gen > 20    → auto-kill + notify
    - loop_detected with gen < 20    → requires approval
    - drift_detected                 → always requires approval
    - silent_tool_failure            → always requires approval
    - create_github_issue            → requires approval
    - request_pr_changes             → requires approval
    """
    def should_auto_act(self, anomaly: AnomalyResult) -> bool:
        if anomaly.type == "loop_detected" and anomaly.metadata.get("gen_count", 0) > 20:
            return True
        if anomaly.type == "cost_spike" and anomaly.metadata.get("cost", 0) > 10.0:
            return True
        return False

    def route(self, anomaly: AnomalyResult):
        if self.should_auto_act(anomaly):
            self.execute_action(anomaly)
            self.notify_slack(anomaly, auto=True)
        else:
            approval_id = self.create_approval_request(anomaly)
            self.post_approval_to_slack(approval_id, anomaly)
```

### Step 5.2 — Wire approval gate into the agent scheduler

Modify `scripts/run_agent.py`:
```python
# Old: anomaly detected → immediately act
# New: anomaly detected → route through approval gate
detector = AnomalyDetector(...)
gate = ApprovalGate(...)

anomalies = detector.run_all()
for anomaly in anomalies:
    gate.route(anomaly)
```

### Step 5.3 — Handle approval callbacks in slack_actions.py

When Slack sends the button callback:
```python
if action_id.startswith("sentinel_approve_"):
    approval_id = int(action_id.split("_")[-1])
    approval = memory.get_approval(approval_id)

    # Execute the pending action
    if approval["action_type"] == "kill_loop":
        # Post loop kill notification
        ...
    elif approval["action_type"] == "create_issue":
        github_issue_creator.create_incident_issue(...)
    elif approval["action_type"] == "request_changes":
        github_commenter.request_changes(...)

    # Update approval status
    memory.update_approval(approval_id, status="approved", resolved_by=slack_user_id)

    # Update the original Slack message to show "✅ Approved by @user"
    requests.post(response_url, json={"text": f"✅ Approved by <@{user_id}>", "replace_original": True})
```

### Step 5.4 — Add expiry logic

Approvals expire after 4 hours (configurable in settings.json):
```python
def expire_stale_approvals(self):
    """Run every 30 minutes. Mark expired approvals and update Slack messages."""
    stale = self.memory.get_expired_approvals()
    for approval in stale:
        self.memory.update_approval(approval["id"], status="expired")
        if approval["slack_ts"]:
            # Update Slack message to show "⏰ Expired (no action taken)"
            ...
```

### Step 5.5 — Build approvals web page

File: `web/src/app/approvals/page.tsx`

Layout:
- Tab bar: Pending | Approved | Rejected | Expired
- Each card shows: action type, severity, context summary, created_at, time remaining
- Pending cards have Approve/Reject buttons (hit the API, which proxies to the same logic)
- Approved/Rejected cards show who and when

### Step 5.6 — Add approvals API routes

File: `api/routes/approvals.py`
- `GET /api/approvals?status=pending` → filtered approval queue
- `POST /api/approvals/{id}/approve` → approve from web UI
- `POST /api/approvals/{id}/reject` → reject from web UI
- `GET /api/approvals/stats` → pending count, avg resolution time, approval rate

### Step 5.7 — Add pending count badge to nav

Update `web/src/components/layout/nav.tsx`:
- "Approvals" nav item shows a badge with pending count (red dot)
- Polls `/api/approvals/stats` every 30 seconds

### Step 5.8 — Test the full loop

1. Trigger a drift detection that requires approval
2. Verify Slack message appears with buttons
3. Click Approve in Slack
4. Verify GitHub issue gets created
5. Verify Slack message updates to "✅ Approved"
6. Verify web UI shows the approval as resolved

**Phase 5 is done when:** an anomaly flows through the approval gate, appears in Slack with buttons, gets approved/rejected, and the action executes.

---

# PHASE 6 — Smart Sampling + Dashboard Polish + Demo Prep (Problem 5)

> **Goal:** Intelligent trace filtering, polished UI, deployment, demo video.

### Step 6.1 — Build agent/sampling/smart_sampler.py

```python
class SmartSampler:
    """
    Scores each trace and decides: keep or drop.
    Keeps traces that are actionable. Drops noise.

    Scoring rules:
    - has_error (level = ERROR/WARNING)        → +100 (always keep)
    - cost > 2× average                        → +80  (keep)
    - novel tool pattern (not seen in 7 days)  → +60  (keep)
    - schema validation failed                 → +70  (keep)
    - generation count > 5                     → +40  (maybe keep)
    - routine successful trace                 → +0   (drop candidate)

    Keep threshold: score >= 40
    """
    def score_trace(self, trace_data: dict) -> int:
        score = 0
        if trace_data.get("has_error"):
            score += 100
        if trace_data.get("cost", 0) > self.avg_cost * 2:
            score += 80
        if trace_data.get("schema_failed"):
            score += 70
        if self._is_novel_pattern(trace_data.get("tool_names", [])):
            score += 60
        if trace_data.get("gen_count", 0) > 5:
            score += 40
        return score

    def filter_traces(self, traces: list[dict]) -> tuple[list[dict], list[dict]]:
        """Returns (kept, dropped) traces."""
        kept, dropped = [], []
        for t in traces:
            if self.score_trace(t) >= self.keep_threshold:
                kept.append(t)
            else:
                dropped.append(t)
        return kept, dropped
```

### Step 6.2 — Integrate sampler into agent modes

Before any mode runs its full analysis, run the sampler to filter which traces are worth looking at:
```python
# In oncall_brain.py, weekly_digest.py, etc.
all_traces = query_library.get_recent_traces(hours=24)
kept, dropped = sampler.filter_traces(all_traces)

# Record stats
memory.save_sampling_stats(
    total=len(all_traces),
    sampled=len(kept),
    dropped=len(dropped),
    keep_reasons=sampler.get_reason_breakdown(kept)
)

# Only analyze kept traces
for trace in kept:
    ...
```

### Step 6.3 — Add sampling stats to API

Extend `api/routes/settings.py`:
- `GET /api/sampling/stats` → latest sampling stats from SQLite
- `GET /api/sampling/policy` → current scoring weights
- `PUT /api/sampling/policy` → update scoring weights

### Step 6.4 — Add sampling widget to dashboard

On the main dashboard:
- "Sampling efficiency" card: "Analyzed 47 of 312 traces (85% noise reduction)"
- Breakdown: "Kept: 12 errors, 8 cost spikes, 3 novel patterns, 24 high-gen"

### Step 6.5 — Final dashboard polish

Update `web/src/app/page.tsx`:
- Add loop alert indicator (red pulsing dot if active loops)
- Add drift status indicator (amber if drift detected in last 24h)
- Add pending approvals count
- Add sampling efficiency metric
- Add forecast widget (from v1 plan): "Projected spend next 6h: $X.XX"
- Ensure all cards link to their respective detail pages

### Step 6.6 — Update nav with all V2 pages

```tsx
const navItems = [
    { name: "Dashboard", href: "/", icon: "ti-home" },
    { name: "Incidents", href: "/incidents", icon: "ti-alert-triangle" },
    { name: "Forensics", href: "/forensics", icon: "ti-graph" },          // NEW
    { name: "Risk", href: "/risk", icon: "ti-shield" },
    { name: "Quality", href: "/quality", icon: "ti-chart-line" },         // NEW
    { name: "Attribution", href: "/attribution", icon: "ti-currency" },   // NEW (if time)
    { name: "Approvals", href: "/approvals", icon: "ti-check", badge: pendingCount }, // NEW
    { name: "Digest", href: "/digest", icon: "ti-mail" },
    { name: "Settings", href: "/settings", icon: "ti-settings" },
];
```

### Step 6.7 — Seed all V2 demo data

Run a comprehensive seeding script that creates:
1. Loop scenario: 15 generations on one trace in 3 minutes
2. Drift scenario: 50 good observations + 10 broken schema + blame commit
3. Silent failure: tool returned 200 but Sentry error appeared 30 seconds later
4. Approval queue: 2 pending, 1 approved, 1 rejected (show variety)
5. Sampling: 300 baseline traces (most boring/droppable) to show 85% reduction

### Step 6.8 — Deploy

```bash
# Backend (FastAPI + Agent) → Railway
railway up

# Frontend (Next.js) → Vercel
cd web && vercel --prod

# Set environment variables on Railway:
# SLACK_SIGNING_SECRET, LANGFUSE_*, GITHUB_TOKEN, etc.

# Update Slack interactivity URL to Railway URL:
# https://your-app.up.railway.app/api/slack/actions
```

### Step 6.9 — Write sources/langfuse/README.md

```markdown
# Langfuse Source Spec for Coral

The first community Coral source spec for Langfuse.
Exposes traces, observations, scores, and sessions as SQL tables.

## Install
coral source add --file ./sources/langfuse/manifest.yaml

## Tables
- langfuse.traces
- langfuse.observations
- langfuse.scores
- langfuse.sessions
```

### Step 6.10 — Record 3-minute demo video

Script:

**0:00–0:20 — The problem statement**
"AI agents in production have 5 failure modes that no single tool catches. Sentinel catches all of them."

**0:20–0:50 — Loop detection (P1)**
Show the seeded loop alert in Slack. Show the Kill button. Click it. Show the loop dying. Show cost burned.

**0:50–1:15 — Prompt drift (P2)**
Show the quality page. Point to the schema break. Show the blame commit. "This commit broke the support bot's JSON output. Sentinel caught it in 4 hours, not 4 days."

**1:15–1:45 — Forensics graph (P3 + P4)**
Open the forensics page. Click the worst trace. React Flow graph animates. "Every node is a different data source, JOINed by Coral SQL. Commit → error → cost spike → Slack thread. Nobody else does this."

**1:45–2:10 — Approval gate (P4)**
Show the approvals page. Show pending item. Approve from web UI. Show the GitHub issue that gets auto-created. "High-risk actions need human approval. EU AI Act Article 14 compliance, built in."

**2:10–2:30 — Smart sampling (P5)**
Show dashboard. Point to sampling card. "312 traces in the last 24 hours. Sentinel analyzed 47 — the ones that matter. 85% noise reduction."

**2:30–3:00 — Technical depth**
"Under the hood: 7 data sources, all queried via Coral SQL. One custom Langfuse source spec — open sourced. Interactive Slack buttons with write-back. This is what an enterprise observability agent looks like."

### Step 6.11 — Submit

- GitHub link (public repo, clean README)
- Deployed link (Railway + Vercel)
- 3-minute YouTube video
- Hackathon submission form

---

## Honest Priority Order (If Time Runs Short)

Ship in this order. Each is independently demo-able:

| Priority | Feature | Phase | Why |
|---|---|---|---|
| 1 | Webhook infra + approval gate | Phase 1 + 5 | Without write-back, nothing is interactive. This transforms Sentinel from a reporter to an agent. |
| 2 | React Flow forensics graph | Phase 4 | The visual judges will screenshot. Most memorable feature. |
| 3 | Loop detection with kill signal | Phase 2 | Most dramatic demo moment. Loop → alert → kill → cost stops. |
| 4 | Prompt drift detection | Phase 3 | Technically impressive. Schema contract testing is novel. |
| 5 | Smart sampling | Phase 6 | Easy to build, adds the "enterprise scale" narrative. |
| 6 | Deploy + demo video | Phase 6 | Non-negotiable for submission. Must happen. |

---

## Final Coral Features Checklist (V2)

| Feature | Used | Where |
|---|---|---|
| Cross-source JOINs | ✅ | Every query joins 2–4 sources. Incident graph joins all 5. |
| Custom source spec | ✅ | Langfuse source spec (open sourced in sources/langfuse/) |
| SQL interface | ✅ | All detection, attribution, forensics via `coral sql` |
| Schema introspection | ✅ | `coral.tables`, `coral.columns` used during setup |
| Built-in caching | ✅ | Automatic on repeated queries |
| MCP integration | ✅ | `claude-code-config.json` for Claude Code |
| 7 data sources | ✅ | GitHub, Sentry, Datadog, Slack, Langfuse, PagerDuty, Linear |
| Source discovery | ✅ | `coral source discover` in setup script |

---

*Build the webhook infra first. Everything else depends on it.
The graph is the screenshot. The approval gate is the story. Ship both.*