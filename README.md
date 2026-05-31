# Sentinel

AI-powered engineering observability agent that cross-queries 7 production data sources via Coral SQL to detect, diagnose, and govern AI system failures — before your users notice.

Built for **Pirates of the Coral-bean** (WeMakeDevs × Coral).

---

## What it does

Sentinel runs four autonomous agents on a schedule, each pulling from a unified SQL layer across Langfuse, Sentry, GitHub, Slack, Datadog, PagerDuty, and Linear. When something breaks — a cost spike, an error cascade, a drifting prompt, a looping agent — Sentinel narrates the root cause, blames the commit, and routes the response through human approval before anything gets executed.

**Five anomaly classes detected:**
- Cost spikes (hourly cost > 2.5× rolling 7-day average)
- Error cascades (Sentry spike correlated with deploys)
- Prompt drift (output schema contracts broken by recent commit)
- Agent loops (>10 generations in a 2h window, cost burning)
- Silent tool failures (schema mismatch + Sentry correlation + output anomaly)

**Four operational modes:**

| Mode | Schedule | Output |
|------|----------|--------|
| On-Call Brain | Every 15 min | RCA report → Slack + GitHub issue |
| PR Risk Scorer | On PR open webhook | Risk score (0–100) → PR comment |
| Drift Patrol | Every 4 hours | Schema drift alert + commit blame |
| Weekly Digest | Monday 09:00 | "What Shipped · What Broke · What to Watch" |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  7 Data Sources                      │
│  Langfuse · Sentry · GitHub · Slack                  │
│  Datadog · PagerDuty · Linear                        │
└──────────────────┬──────────────────────────────────┘
                   │  Coral SQL (cross-source joins)
┌──────────────────▼──────────────────────────────────┐
│               Python Agent Layer                     │
│  anomaly_detector → narrator (Groq) → approval_gate │
│  On-Call Brain · PR Risk · Drift Patrol · Digest     │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   FastAPI      Slack       GitHub
   REST API   (HMAC-auth)   Issues/PRs
       │
       ▼
  Next.js Command Center
  (Dashboard · Incidents · Forensics · Risk ·
   Quality · Approvals · Digest · Settings)
```

**Key design decisions:**
- All cross-source queries run via `coral sql --format json` subprocess — one SQL interface, zero bespoke API clients per source
- Narration runs on Groq (Llama 3.3 70B) — single endpoint, three system prompts
- Approval model is hybrid: auto-kill obvious threats (>20 gens, >$10/hr cost burn), queue everything else as HITL with Slack buttons + web UI
- Forensics graphs are React Flow DAGs built from correlated commits/errors/traces/messages
- All state (incidents, approvals, loops, drift events, baselines) persists to SQLite with full audit trail

---

## Stack

**Agent / API**
- Python 3.12, FastAPI 0.115, APScheduler 3.10, uvicorn
- Groq SDK (llama-3.3-70b-versatile), Langfuse SDK, Sentry SDK
- SQLite3 for persistence, python-dotenv

**Web**
- Next.js 16.2.6 (React 19.2.4), TailwindCSS v4
- @xyflow/react (forensics dependency graphs)
- Framer Motion, Lucide React, React Markdown

**Infrastructure**
- Coral OSS (cross-source SQL engine)
- Custom Langfuse source spec (`sources/langfuse/`) — 5 tables, HTTP Basic Auth, pagination

---

## Quickstart

### Prerequisites
- Python 3.12+, Node.js 18+
- Coral CLI installed and on `PATH`
- Accounts / tokens for: Langfuse, Sentry, GitHub, Slack, Groq, Datadog, PagerDuty

### 1. Install Coral

```bash
curl -fsSL https://withcoral.com/install | sh
coral --version
```

### 2. Environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Groq (narration)
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# Langfuse
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Sentry
SENTRY_TOKEN=
SENTRY_ORG=

# GitHub
GITHUB_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=
GITHUB_TARGET_REPO=

# Slack
SLACK_TOKEN=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_INCIDENTS_CHANNEL=#incidents

# Datadog
DD_API_KEY=
DD_APPLICATION_KEY=

# PagerDuty
PAGERDUTY_TOKEN=

# Linear
LINEAR_API_KEY=

# Thresholds (optional — defaults in settings.json)
COST_SPIKE_MULTIPLIER=2.5
PR_RISK_THRESHOLD=70
AGENT_LOOP_GENERATION_THRESHOLD=10
ERROR_CASCADE_THRESHOLD=10.0
```

### 3. Add Coral sources

```bash
bash scripts/setup_coral.sh
```

Or register the custom Langfuse spec manually:

```bash
coral source add langfuse --spec sources/langfuse/manifest.yaml
```

### 4. Agent + API

```bash
pip install -r requirements.txt
python scripts/run_agent.py      # starts APScheduler + FastAPI on :8000
```

### 5. Web

```bash
cd web
npm install
npm run dev                      # http://localhost:3000
```

---

## Project layout

```
sentinel/
├── agent/
│   ├── modes/               # oncall_brain, pr_risk_scorer, weekly_digest, drift_patrol
│   ├── detectors/           # drift_detector, loop_detector, tool_failure_detector
│   ├── forensics/           # incident_graph_builder, trace_reconstructor
│   ├── governance/          # approval_gate (HITL routing + auto-kill logic)
│   ├── actions/             # slack_poster, github_commenter, github_issue_creator
│   ├── coral_client.py      # coral sql subprocess wrapper
│   ├── memory.py            # SQLite CRUD (7 tables)
│   ├── narrator.py          # Groq API — 3 narration prompts
│   ├── query_library.py     # Cross-source SQL templates
│   └── anomaly_detector.py  # Orchestration layer
├── api/
│   ├── routes/              # 15+ endpoint groups
│   ├── middleware/          # Slack HMAC verification
│   ├── main.py
│   └── models.py
├── web/
│   └── src/app/
│       ├── (app)/           # 8 pages: dashboard, incidents, forensics, risk,
│       │                    #          quality, approvals, digest, settings
│       └── components/
├── sources/langfuse/        # Custom Coral source spec (5 tables)
├── scripts/
│   └── run_agent.py         # APScheduler entry point
├── settings.json            # Runtime thresholds
└── sentinel.db              # SQLite database
```

---

## Web UI

| Page | What you see |
|------|-------------|
| Dashboard | Live stat cards (incidents, projected cost, active loops, pending approvals), Coral health, recent incident feed |
| Incidents | Full incident list — cost spikes, error cascades, severity filters, drill-down |
| Forensics | React Flow causal graph: commits → errors → traces → Slack messages |
| Risk | File risk history, current PR score breakdown, historical delta correlation |
| Quality | Schema snapshots per feature, drift events with blame commit, trigger manual scan |
| Approvals | HITL queue — pending actions, approve/reject, resolution time stats |
| Digest | Latest weekly summary rendered as markdown |
| Settings | Runtime threshold configuration |

---

## Data sources

| Source | Tables queried | What Sentinel uses it for |
|--------|---------------|--------------------------|
| Langfuse | traces, observations, scores, sessions | Hourly cost, token counts, model breakdown, error levels, trace latency |
| Sentry | issues, events | Error counts, cascade detection, tool failure correlation |
| GitHub | commits, pull_requests | Deploy correlation, PR risk scoring, commit blame |
| Slack | messages, channels | Incident context window, approval button delivery |
| Datadog | monitors, incidents, metrics | Infrastructure anomaly correlation |
| PagerDuty | incidents, urgency, timelines | On-call incident enrichment |
| Linear | issues, sprints | Sprint context for weekly digest |

Langfuse uses a custom Coral source spec in `sources/langfuse/manifest.yaml`. All other sources use Coral's bundled connectors.

---

## Coral SQL query templates

Seven cross-source templates in `agent/query_library.py`:

| Template | Sources joined |
|----------|---------------|
| `hourly_cost_and_generations` | Langfuse |
| `rolling_7d_baseline` | Langfuse |
| `commit_to_cost_correlation` | GitHub × Langfuse |
| `error_cascade_detection` | Sentry |
| `slack_incident_context` | Slack |
| `agent_loop_fingerprints` | Langfuse |
| `tool_failure_candidates` | Langfuse × Sentry |

---

## Governance model

```
anomaly detected
      │
      ▼
 auto-kill?  ─── yes ──► execute immediately + audit log
 (>20 gens or             (loop kill / cost cap)
  >$10/hr)
      │ no
      ▼
 queue for HITL
      │
      ├── Slack interactive button (HMAC-signed)
      └── Web UI (/approvals)
            │
            ▼
       approve / reject
            │
            ▼
       execute action + write SQLite audit row
       (expires after configurable hours if no action taken)
```

---

## SQLite schema

| Table | Purpose |
|-------|---------|
| `incident_reports` | Detected incidents: type, severity, narrated RCA, related commits/errors, cost impact, Slack thread TS |
| `cost_baselines` | Hourly cost snapshots for rolling 7-day average computation |
| `loop_detections` | Agent loops: trace IDs, generation count, cost burned, tool histogram, kill status |
| `schema_snapshots` | Feature output schemas (JSON): baseline captured on first observation |
| `drift_events` | Drift detections: feature name, drift type, validation fail rate, blame commit SHA |
| `approvals` | HITL queue: action type, context JSON, status, Slack TS, resolved by, resolution timestamp |
| `file_risk_history` | Per-file PR history: cost delta, error delta, composite risk score, commit SHA |

---

## Thresholds

Configurable at runtime via `settings.json` or environment variables:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `COST_SPIKE_MULTIPLIER` | 2.5 | Trigger when current hour cost > N × 7d rolling average |
| `PR_RISK_THRESHOLD` | 70 | Score (0–100) above which PR review is requested |
| `AGENT_LOOP_GENERATION_THRESHOLD` | 10 | Generations in 2h window before loop is flagged |
| `ERROR_CASCADE_THRESHOLD` | 10.0 | Sentry error rate delta for cascade detection |

---

## License

MIT
