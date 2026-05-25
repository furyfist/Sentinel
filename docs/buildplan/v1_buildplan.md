# Sentinel — Complete Build Plan v1

> **Hackathon:** Pirates of the Coral-bean (WeMakeDevs × Coral)
> **Track:** Track 1 — Build an Enterprise Agent
> **Deadline:** May 31, 2026
> **Builder:** Himanshu (solo)
> **Last updated:** May 25, 2026

---

## Table of Contents

1. [Product Summary](#1-product-summary)
2. [Research Findings — What Coral Actually Provides](#2-research-findings)
3. [Source Availability Audit](#3-source-availability-audit)
4. [Langfuse Source Spec — Custom Build Guide](#4-langfuse-source-spec)
5. [Folder Structure](#5-folder-structure)
6. [Step-by-Step Build Plan](#6-step-by-step-build-plan)
7. [SQL Query Library](#7-sql-query-library)
8. [Agent Architecture](#8-agent-architecture)
9. [Seeding Strategy](#9-seeding-strategy)
10. [Deployment Plan](#10-deployment-plan)
11. [Demo Script](#11-demo-script)
12. [Risk Register](#12-risk-register)

---

## 1. Product Summary

**Sentinel** is an AI-powered engineering observability agent that cross-queries
GitHub commits, Sentry errors, Langfuse LLM traces, Datadog metrics, and Slack
conversations via Coral's SQL interface — then uses Claude to narrate what went
wrong, why, and who caused it.

Three activation modes, one SQL brain:

| Mode | Trigger | Output |
|---|---|---|
| On-Call Brain | Incident fires (Datadog/Sentry spike) | RCA doc with commit blame + Slack context |
| PR Risk Scorer | GitHub PR opened | Risk score as GitHub PR comment |
| Weekly Digest | Monday 9am cron | "What shipped · What broke · What to watch" digest |

The non-obvious innovation: every mode JOINs Slack messages as social context
alongside technical data. No existing tool does this.

---

## 2. Research Findings

### 2.1 — Coral Core Facts

- **What it is:** A local SQL runtime that translates SQL into API calls. Not a database. No ETL. No data storage.
- **Binary:** Written in Rust. Install via `curl -fsSL https://withcoral.com/install | sh`
- **Source spec format:** YAML files (DSL version 3). Backend types: `http`, `jsonl`, `parquet`
- **Auth model:** `coral source add --interactive <name>` prompts for API keys. Stored locally. Credentials never leave machine.
- **CLI usage:** `coral sql "SELECT ..."` — returns tabular rows
- **MCP server:** `coral mcp-stdio` — exposes tools: `sql`, `list_catalog`, `search_catalog`, `describe_table`, `list_columns`
- **Skills:** Install with `npx skills add withcoral/skills` — teaches agents discovery-first SQL workflow
- **Introspection tables:** `coral.tables`, `coral.columns`, `coral.filters`, `coral.inputs`, `coral.table_functions`
- **Cross-source JOINs:** Standard SQL JOINs work across any combination of sources
- **Query pushdown + caching:** Built in. Reduces API traffic automatically.

### 2.2 — Bundled Sources (already in Coral)

| Source | Status | Tables Available |
|---|---|---|
| **GitHub** | ✅ Bundled | repos, issues, pulls, commits, workflows, actions, users, teams, orgs |
| **Sentry** | ✅ Bundled | issues, events, projects, releases, deployments, teams, members |
| **Datadog** | ✅ Bundled | monitors, events, incidents, dashboards, hosts, services, APM deps, downtimes, SLOs, synthetic tests, users, logs, spans, metrics |
| **Slack** | ✅ Bundled | channels, messages, thread_replies, users |
| **Langfuse** | ❌ NOT bundled, NOT in community | Must write custom source spec |

### 2.3 — Langfuse API Facts (for source spec)

- **Auth:** HTTP Basic Auth — `LANGFUSE_PUBLIC_KEY` as username, `LANGFUSE_SECRET_KEY` as password
- **Base URL:** `https://cloud.langfuse.com` (or self-hosted)
- **Key v1 endpoints (use these — v2 is cloud-only beta):**
  - `GET /api/public/traces` — list traces with pagination (page-based), filters: `name`, `userId`, `sessionId`, `fromTimestamp`, `toTimestamp`
  - `GET /api/public/traces/:traceId` — single trace detail
  - `GET /api/public/observations` — list observations (spans, generations, events). Filters: `traceId`, `type`, `name`, `fromStartTime`, `toStartTime`. Page-based pagination: `page`, `limit`
  - `GET /api/public/scores` — list scores. Filters: `name`, `userId`, `traceId`
  - `GET /api/public/metrics` — aggregated metrics (views: traces, observations, scores)
  - `GET /api/public/sessions` — list sessions
- **Observation types:** `GENERATION` (LLM calls with model, usage, cost), `SPAN` (generic), `EVENT` (point-in-time)
- **Key fields on observations:** `id`, `traceId`, `type`, `name`, `startTime`, `endTime`, `model`, `modelParameters`, `usage` (promptTokens, completionTokens, totalTokens), `calculatedTotalCost`, `level`, `statusMessage`
- **Pagination:** v1 uses `page` + `limit` (offset-based). Default limit varies. Max 100 per page.

### 2.4 — Coral Custom Source Spec Guide

From official docs, a custom HTTP source spec needs:

```yaml
name: my_source
version: 0.1.0
dsl_version: 3
backend: http
inputs:
  API_TOKEN:
    kind: secret
    hint: "Your API token"
base_url: "{{input.BASE_URL}}"
auth:
  type: HeaderAuth   # or BasicAuth
  headers:
    - name: Authorization
      from: template
      template: "Bearer {{input.API_TOKEN}}"
tables:
  - name: my_table
    description: "What this table contains"
    request:
      method: GET
      path: /api/endpoint
    response:
      rows_path:
        - data        # JSON path to the array of rows
    pagination:
      mode: page_number  # or link_header, cursor
      page_size:
        default: 50
        max: 100
        query_param: limit
    columns:
      - name: id
        type: Utf8
      - name: created_at
        type: Timestamp
```

Key details:
- **Lint before install:** `coral source lint ./my-source.yaml`
- **Install:** `coral source add --file ./my-source.yaml`
- **Test:** `coral source test my_source`
- **Nested fields:** Use `__` double underscore: `assignee__name`
- **Column types:** `Utf8`, `Int64`, `Float64`, `Boolean`, `Timestamp`, `Json`
- **Timestamp conversion:** Use `format_timestamp` expr with `input: iso8601` for ISO 8601 strings

---

## 3. Source Availability Audit

| Source | Available in Coral? | Auth Type | What We Query |
|---|---|---|---|
| GitHub | ✅ Bundled (`coral source add github`) | Personal Access Token | commits, pulls, issues |
| Sentry | ✅ Bundled (`coral source add sentry`) | API Token | issues, events |
| Datadog | ✅ Bundled (`coral source add datadog`) | API Key + App Key | monitors, events, logs, metrics |
| Slack | ✅ Bundled (`coral source add slack`) | Bot Token | messages, channels, users |
| Langfuse | ❌ Custom source spec needed | Basic Auth (pub key:secret key) | traces, observations, scores, sessions |

---

## 4. Langfuse Source Spec — Custom Build

This is the highest-risk, highest-value piece. Build first.

### 4.1 — File: `sources/langfuse/manifest.yaml`

Langfuse uses Basic Auth. Coral supports `BasicAuth` type natively. The v1 API
uses page-based pagination with `page` and `limit` query params.

Tables to expose:

| Table | Endpoint | Key Columns |
|---|---|---|
| `traces` | `GET /api/public/traces` | id, name, userId, sessionId, timestamp, tags, metadata |
| `observations` | `GET /api/public/observations` | id, traceId, type, name, model, startTime, endTime, usage (tokens), calculatedTotalCost, level, statusMessage |
| `scores` | `GET /api/public/scores` | id, traceId, observationId, name, value, dataType, comment |
| `sessions` | `GET /api/public/sessions` | id, createdAt, projectId |

### 4.2 — Auth Configuration

```yaml
inputs:
  LANGFUSE_HOST:
    kind: variable
    default: https://cloud.langfuse.com
    hint: "Langfuse host URL (cloud or self-hosted)"
  LANGFUSE_PUBLIC_KEY:
    kind: secret
    hint: "Langfuse public key (used as Basic Auth username)"
  LANGFUSE_SECRET_KEY:
    kind: secret
    hint: "Langfuse secret key (used as Basic Auth password)"

base_url: "{{input.LANGFUSE_HOST}}/api/public"

auth:
  type: BasicAuth
  username: "{{input.LANGFUSE_PUBLIC_KEY}}"
  password: "{{input.LANGFUSE_SECRET_KEY}}"
```

### 4.3 — Pagination Strategy

Langfuse v1 uses page-number pagination:
- Query params: `page=1&limit=50`
- Response: `{ "data": [...], "meta": { "totalItems": 150, "totalPages": 3, "page": 1 } }`

In Coral spec:
```yaml
pagination:
  mode: page_number
  page_size:
    default: 50
    max: 100
    query_param: limit
```

### 4.4 — Validation Steps

```bash
# 1. Lint the spec
coral source lint ./sources/langfuse/manifest.yaml

# 2. Install with credentials
LANGFUSE_HOST=https://cloud.langfuse.com \
LANGFUSE_PUBLIC_KEY=pk-lf-xxx \
LANGFUSE_SECRET_KEY=sk-lf-xxx \
coral source add --file ./sources/langfuse/manifest.yaml

# 3. Test connectivity
coral source test langfuse

# 4. Verify tables
coral sql "SELECT schema_name, table_name FROM coral.tables WHERE schema_name = 'langfuse'"

# 5. Smoke test
coral sql "SELECT id, name, type, model, calculatedTotalCost FROM langfuse.observations LIMIT 5"
```

### 4.5 — Fallback Plan

If the source spec has edge cases that block you for more than 3 hours:
1. Export Langfuse data via their API to JSONL files
2. Use `backend: jsonl` source spec (simpler, no auth/pagination)
3. Still works with Coral SQL, still counts as a custom source
4. Less impressive but unblocks you completely

---

## 5. Folder Structure

```
sentinel/
├── README.md                          # Project overview, setup, demo
├── LICENSE
├── .env.example                       # All required env vars documented
│
├── sources/                           # Coral source specs
│   └── langfuse/
│       ├── manifest.yaml              # The Langfuse source spec
│       └── README.md                  # How to use this source spec standalone
│
├── agent/                             # Python agent core
│   ├── __init__.py
│   ├── config.py                      # Env vars, constants, thresholds
│   ├── coral_client.py                # Wrapper: subprocess coral sql → parsed rows
│   ├── query_library.py              # All SQL queries as named functions
│   ├── anomaly_detector.py            # Rolling avg, spike detection logic
│   ├── claude_narrator.py             # Claude API call: SQL results → english
│   ├── memory.py                      # SQLite persistence layer
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── slack_poster.py            # Post reports to Slack
│   │   ├── github_commenter.py        # Post PR risk comments via GitHub API
│   │   └── github_issue_creator.py    # Auto-create issues from incidents
│   └── modes/
│       ├── __init__.py
│       ├── oncall_brain.py            # Mode A: incident → RCA
│       ├── pr_risk_scorer.py          # Mode B: PR → risk score
│       └── weekly_digest.py           # Mode C: cron → digest
│
├── web/                               # Next.js command center UI
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Dashboard home
│   │   ├── incidents/
│   │   │   └── page.tsx               # Incident investigation tab
│   │   ├── risk/
│   │   │   └── page.tsx               # PR risk history tab
│   │   ├── digest/
│   │   │   └── page.tsx               # Weekly digest viewer
│   │   └── settings/
│   │       └── page.tsx               # Configure thresholds, sources
│   ├── components/
│   │   ├── incident-card.tsx
│   │   ├── risk-badge.tsx
│   │   ├── digest-section.tsx
│   │   ├── timeline.tsx
│   │   └── nav.tsx
│   └── lib/
│       └── api.ts                     # Fetch from agent backend
│
├── api/                               # FastAPI backend serving web UI
│   ├── main.py
│   ├── routes/
│   │   ├── incidents.py
│   │   ├── risk.py
│   │   ├── digest.py
│   │   └── settings.py
│   └── models.py
│
├── scripts/
│   ├── seed_demo_data.py              # Seed fake but realistic data
│   ├── setup_coral.sh                 # Install coral + add all sources
│   └── run_agent.py                   # Entry point: schedule all modes
│
├── mcp/                               # MCP integration config
│   └── claude-code-config.json        # MCP stdio config for Claude Code
│
├── Dockerfile
├── docker-compose.yml                 # Agent + API + Web
├── requirements.txt
└── .github/
    └── workflows/
        └── pr-risk.yml                # GitHub Action: trigger PR Risk on PR open
```

### Tradeoff Decisions

| Decision | Why |
|---|---|
| Python for agent, not TypeScript | Coral CLI is called via subprocess. Python's subprocess handling is cleaner. Claude API SDK is native Python. |
| SQLite for memory, not Postgres | Zero setup. Single file. Good enough for demo. No deployment overhead. |
| FastAPI for API, not Express | You already know it from NTA. Shared Python codebase with agent. |
| Next.js for web, not raw HTML | You ship polished UIs fast in Next.js. Judges notice UI quality. |
| Subprocess for Coral, not SDK | Coral has no Python SDK. CLI via `coral sql "..."` is the intended interface. MCP is the other option but adds complexity. |
| GitHub Actions for PR trigger | Free, already in GitHub, zero infra. Runs `pr_risk_scorer.py` on PR open. |

---

## 6. Step-by-Step Build Plan

### Phase 1 — Foundation (Hours 1–4)

**Step 1.1 — Install Coral**
```bash
curl -fsSL https://withcoral.com/install | sh
coral --version
```

**Step 1.2 — Add bundled sources**
```bash
# GitHub
GITHUB_TOKEN=ghp_xxx coral source add github

# Sentry
SENTRY_AUTH_TOKEN=xxx coral source add sentry

# Datadog
DD_API_KEY=xxx DD_APP_KEY=xxx coral source add datadog

# Slack
SLACK_BOT_TOKEN=xoxb-xxx coral source add slack
```

**Step 1.3 — Verify all sources**
```bash
coral sql "SELECT schema_name, table_name FROM coral.tables ORDER BY 1, 2"
```
Expected: tables from github, sentry, datadog, slack schemas.

**Step 1.4 — Write Langfuse source spec**

Create `sources/langfuse/manifest.yaml` following section 4 above. This is the
hardest step. Budget 2–3 hours including debugging.

Validation checklist:
- [ ] `coral source lint` passes
- [ ] `coral source add --file` succeeds
- [ ] `coral source test langfuse` passes
- [ ] `SELECT * FROM langfuse.traces LIMIT 1` returns data
- [ ] `SELECT * FROM langfuse.observations LIMIT 1` returns data
- [ ] `calculatedTotalCost` column is queryable on observations

**Step 1.5 — Test a cross-source JOIN**
```bash
coral sql "
  SELECT g.sha, g.message, s.title as sentry_issue
  FROM github.commits g
  JOIN sentry.issues s ON s.first_seen > g.committed_at
  WHERE g.owner = 'YOUR_ORG' AND g.repo = 'YOUR_REPO'
  LIMIT 5
"
```
This validates the core Coral capability works before writing agent code.

---

### Phase 2 — Agent Core (Hours 5–10)

**Step 2.1 — coral_client.py**

Wrapper that calls `coral sql` via subprocess, parses JSON output.

```python
import subprocess
import json

def query(sql: str) -> list[dict]:
    """Execute Coral SQL and return parsed rows."""
    result = subprocess.run(
        ["coral", "sql", "--format", "json", sql],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Coral query failed: {result.stderr}")
    return json.loads(result.stdout)
```

Key detail: check if `coral sql` supports `--format json`. If not, parse the
tabular text output. Test this early.

Alternative: use `coral mcp-stdio` and talk MCP protocol from Python. More
complex but more robust. Decision: start with subprocess, migrate if needed.

**Step 2.2 — query_library.py**

All SQL queries as named functions. See section 7 for the full library.

**Step 2.3 — anomaly_detector.py**

```python
def detect_cost_spike(current_hourly_cost: float, baseline_avg: float, threshold: float = 2.5) -> bool:
    return current_hourly_cost > baseline_avg * threshold

def detect_error_cascade(error_count: int, retry_cost: float, threshold: float = 10.0) -> bool:
    return (error_count * retry_cost) > threshold

def detect_agent_loop(generation_count: int, time_window_seconds: int = 60, threshold: int = 10) -> bool:
    return generation_count > threshold
```

**Step 2.4 — claude_narrator.py**

Takes SQL result rows + detection metadata. Returns plain English report.

```python
import anthropic

def narrate_incident(sql_results: dict, detection_type: str) -> str:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system="You are Sentinel, an engineering observability agent. Write a concise incident report from the data provided. Be specific about commits, errors, costs, and timelines. No fluff.",
        messages=[{
            "role": "user",
            "content": f"Detection type: {detection_type}\nData:\n{json.dumps(sql_results, indent=2)}\n\nWrite the incident report."
        }]
    )
    return message.content[0].text
```

**Step 2.5 — memory.py (SQLite)**

```sql
CREATE TABLE IF NOT EXISTS file_risk_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    commit_sha TEXT,
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cost_delta REAL DEFAULT 0,
    error_delta INTEGER DEFAULT 0,
    risk_score REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS incident_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detection_type TEXT,
    severity TEXT,
    report_text TEXT,
    related_commits TEXT,  -- JSON array of SHAs
    related_errors TEXT,   -- JSON array of Sentry issue IDs
    cost_impact REAL DEFAULT 0,
    slack_thread_ts TEXT   -- Slack message ID if posted
);

CREATE TABLE IF NOT EXISTS cost_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hourly_cost REAL,
    daily_cost REAL,
    source TEXT DEFAULT 'langfuse'
);
```

---

### Phase 3 — Three Modes (Hours 11–18)

**Step 3.1 — Mode A: On-Call Brain**

File: `agent/modes/oncall_brain.py`

Flow:
1. Query Langfuse: hourly cost in last 1h vs 7-day rolling avg
2. If spike detected → query Sentry for errors in same window
3. JOIN with GitHub commits in last 48h
4. JOIN with Slack messages in #incidents / #engineering channels
5. Claude narrates the full picture
6. Post to Slack
7. Auto-create GitHub issue with the RCA

**Step 3.2 — Mode B: PR Risk Scorer**

File: `agent/modes/pr_risk_scorer.py`

Flow:
1. Triggered by GitHub Action on PR open (or polled)
2. Get list of changed files from the PR
3. Query file_risk_history from SQLite: what happened last N times these files changed?
4. Query Langfuse: cost trend for the models these files touch
5. Compute risk score (0-100)
6. Claude generates a human-readable risk summary
7. Post as GitHub PR comment via GitHub API
8. If risk > 70: request changes on PR automatically

**Step 3.3 — Mode C: Weekly Digest**

File: `agent/modes/weekly_digest.py`

Flow:
1. Query GitHub: PRs merged in last 7 days
2. Query Sentry: error rate change vs previous week
3. Query Langfuse: cost trend this week vs last week
4. Query Slack: messages mentioning PR numbers or issue IDs
5. Claude generates structured digest with 3 sections
6. Post to Slack
7. Store in SQLite for web UI

---

### Phase 4 — Actions Layer (Hours 19–22)

**Step 4.1 — slack_poster.py**

Uses Slack Web API directly (not via Coral — Coral is read-only).

```python
import requests

def post_to_slack(channel: str, text: str, blocks: list = None):
    requests.post("https://slack.com/api/chat.postMessage", json={
        "channel": channel,
        "text": text,
        "blocks": blocks
    }, headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"})
```

**Step 4.2 — github_commenter.py**

```python
def post_pr_comment(owner: str, repo: str, pr_number: int, body: str):
    requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
        json={"body": body},
        headers={"Authorization": f"token {GITHUB_TOKEN}"}
    )
```

**Step 4.3 — github_issue_creator.py**

```python
def create_incident_issue(owner: str, repo: str, title: str, body: str, labels: list):
    requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        json={"title": title, "body": body, "labels": labels},
        headers={"Authorization": f"token {GITHUB_TOKEN}"}
    )
```

---

### Phase 5 — Web Command Center (Hours 23–30)

**Step 5.1 — FastAPI backend**

4 route files, minimal. Reads from SQLite + calls Coral for live data.

```
GET /api/incidents          → list incident reports from SQLite
GET /api/incidents/:id      → single incident detail
GET /api/risk/history       → file risk history from SQLite
GET /api/risk/current/:pr   → compute risk for a specific PR (live Coral query)
GET /api/digest/latest      → latest weekly digest
GET /api/digest/history     → past digests
GET /api/settings           → current thresholds
PUT /api/settings           → update thresholds
GET /api/health             → Coral connectivity status
```

**Step 5.2 — Next.js UI**

4 pages:

| Page | What it shows |
|---|---|
| `/` (Dashboard) | Recent incidents, current risk alerts, cost trend sparkline |
| `/incidents` | Full incident list, click to drill into RCA with commit blame, Slack context |
| `/risk` | PR risk history, file heatmap (which files cause most trouble) |
| `/digest` | Latest weekly digest, archive of past digests |
| `/settings` | Cost spike threshold, risk score threshold, Slack channel config |

Design approach: Dark theme (matches the demo vibe), minimal, data-dense.
Use Tailwind + shadcn/ui components. You know this stack cold from NTA.

---

### Phase 6 — MCP Integration + Polish (Hours 31–34)

**Step 6.1 — MCP config**

```json
{
  "mcpServers": {
    "sentinel-coral": {
      "command": "coral",
      "args": ["mcp-stdio"]
    }
  }
}
```

This lets Claude Code or Cursor query Sentinel's data via Coral directly.
One config line, big judge points.

**Step 6.2 — GitHub Action for PR Risk**

```yaml
# .github/workflows/pr-risk.yml
name: Sentinel PR Risk
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  risk-score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Coral
        run: curl -fsSL https://withcoral.com/install | sh
      - name: Run PR Risk Scorer
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        run: python agent/modes/pr_risk_scorer.py --pr=${{ github.event.pull_request.number }}
```

---

## 7. SQL Query Library

### 7.1 — Cost Spike Detection (Langfuse)
```sql
SELECT
  date_trunc('hour', startTime) as hour,
  SUM(calculatedTotalCost) as hourly_cost,
  COUNT(*) as generation_count,
  AVG(calculatedTotalCost) as avg_cost_per_call
FROM langfuse.observations
WHERE type = 'GENERATION'
  AND startTime > NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', startTime)
ORDER BY hour DESC
```

### 7.2 — Commit-to-Cost Blame (GitHub × Langfuse × Sentry)
```sql
SELECT
  g.sha,
  g.message as commit_message,
  g.author__login as author,
  g.committed_date,
  COUNT(DISTINCT s.id) as errors_after_commit,
  SUM(l.calculatedTotalCost) as cost_after_commit
FROM github.commits g
LEFT JOIN sentry.issues s
  ON s.first_seen > g.committed_date
  AND s.first_seen < g.committed_date + INTERVAL '24 hours'
LEFT JOIN langfuse.observations l
  ON l.startTime > g.committed_date
  AND l.startTime < g.committed_date + INTERVAL '24 hours'
  AND l.type = 'GENERATION'
WHERE g.owner = '{owner}'
  AND g.repo = '{repo}'
  AND g.committed_date > NOW() - INTERVAL '7 days'
GROUP BY g.sha, g.message, g.author__login, g.committed_date
ORDER BY cost_after_commit DESC NULLS LAST
LIMIT 10
```

### 7.3 — Error Cascade Detection (Sentry × Langfuse)
```sql
SELECT
  s.title as error_title,
  s.count as error_count,
  s.first_seen,
  s.last_seen,
  SUM(l.calculatedTotalCost) as associated_cost,
  COUNT(l.id) as retry_generations
FROM sentry.issues s
JOIN langfuse.observations l
  ON l.startTime BETWEEN s.first_seen AND s.last_seen
  AND l.type = 'GENERATION'
WHERE s.first_seen > NOW() - INTERVAL '48 hours'
GROUP BY s.title, s.count, s.first_seen, s.last_seen
HAVING SUM(l.calculatedTotalCost) > 1.0
ORDER BY associated_cost DESC
LIMIT 10
```

### 7.4 — Slack Context for Incidents
```sql
SELECT
  m.text,
  m.user as author,
  m.ts as posted_at,
  c.name as channel_name
FROM slack.messages m
JOIN slack.channels c ON c.id = m.channel
WHERE m.ts > '{incident_start_time}'
  AND m.ts < '{incident_end_time}'
  AND c.name IN ('incidents', 'engineering', 'backend', 'alerts')
ORDER BY m.ts ASC
LIMIT 20
```

### 7.5 — PR Risk Historical Correlation
```sql
SELECT
  g.sha,
  g.message,
  g.committed_date,
  SUM(l.calculatedTotalCost) as cost_after,
  COUNT(s.id) as errors_after
FROM github.commits g
LEFT JOIN langfuse.observations l
  ON l.startTime BETWEEN g.committed_date AND g.committed_date + INTERVAL '24 hours'
  AND l.type = 'GENERATION'
LEFT JOIN sentry.issues s
  ON s.first_seen BETWEEN g.committed_date AND g.committed_date + INTERVAL '24 hours'
WHERE g.owner = '{owner}'
  AND g.repo = '{repo}'
  AND g.committed_date > NOW() - INTERVAL '90 days'
GROUP BY g.sha, g.message, g.committed_date
ORDER BY g.committed_date DESC
```

### 7.6 — Weekly Digest: What Shipped
```sql
SELECT
  p.title,
  p.number,
  p.user__login as author,
  p.merged_at,
  p.additions,
  p.deletions
FROM github.pulls p
WHERE p.owner = '{owner}'
  AND p.repo = '{repo}'
  AND p.state = 'closed'
  AND p.merged_at > NOW() - INTERVAL '7 days'
ORDER BY p.merged_at DESC
```

### 7.7 — Agent Loop Detection (Langfuse)
```sql
SELECT
  traceId,
  COUNT(*) as generation_count,
  MIN(startTime) as first_gen,
  MAX(startTime) as last_gen,
  SUM(calculatedTotalCost) as total_cost
FROM langfuse.observations
WHERE type = 'GENERATION'
  AND startTime > NOW() - INTERVAL '1 hour'
GROUP BY traceId
HAVING COUNT(*) > 10
ORDER BY generation_count DESC
LIMIT 10
```

---

## 8. Agent Architecture

```
                    ┌─────────────────┐
                    │   Scheduler     │
                    │  (run_agent.py) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │ On-Call     │ │ PR Risk    │ │ Weekly     │
     │ Brain      │ │ Scorer     │ │ Digest     │
     └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
           │              │              │
           └──────────────┼──────────────┘
                          ▼
                 ┌────────────────┐
                 │ query_library  │──→ coral_client ──→ Coral CLI
                 └────────┬───────┘
                          │
                 ┌────────▼───────┐
                 │ anomaly_detect │
                 └────────┬───────┘
                          │
                 ┌────────▼───────┐
                 │ claude_narrator│──→ Claude API
                 └────────┬───────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         slack_poster  gh_commenter  memory.db
```

---

## 9. Seeding Strategy

You don't have a real incident to demo. Seed one.

### 9.1 — Langfuse: Seed via SDK

```python
from langfuse import Langfuse

lf = Langfuse()

# Seed normal baseline (100 traces, low cost)
for i in range(100):
    trace = lf.trace(name="normal-query", user_id="user-1")
    trace.generation(
        name="gpt-4o-mini",
        model="gpt-4o-mini",
        usage={"input": 100, "output": 50},
        start_time=datetime.now() - timedelta(days=random.randint(1,7)),
    )

# Seed the spike (20 expensive traces in 1 hour)
spike_time = datetime.now() - timedelta(hours=6)
for i in range(20):
    trace = lf.trace(name="runaway-agent", user_id="agent-loop")
    trace.generation(
        name="gpt-4",
        model="gpt-4",
        usage={"input": 5000, "output": 3000},
        start_time=spike_time + timedelta(minutes=i*3),
    )
```

### 9.2 — GitHub: Create commits with known messages

Push 3-4 commits to a demo repo with messages like:
- `fix: update retry logic in agent handler`
- `feat: change system prompt for support bot`
- `refactor: increase max_tokens to 8000`

### 9.3 — Sentry: Trigger real errors

```python
import sentry_sdk
sentry_sdk.init(dsn="your-dsn")

# Trigger errors that match the spike timeline
for i in range(15):
    try:
        raise Exception("RateLimitError: Too many requests to OpenAI API")
    except:
        sentry_sdk.capture_exception()
    time.sleep(2)
```

### 9.4 — Slack: Post messages in test channel

Post messages in a #sentinel-demo channel that reference the commit and errors.
These become the social context the agent picks up.

---

## 10. Deployment Plan

| Component | Deploy To | Why |
|---|---|---|
| Agent (Python) | Railway | You already use Railway for NTA. One `Dockerfile` |
| API (FastAPI) | Railway (same service) | Share the SQLite file |
| Web (Next.js) | Vercel | Free, fast, you know the deploy flow |
| Coral | Runs locally or in Railway container | Agent calls CLI |
| SQLite | Volume mount in Railway | Persists between runs |

### Docker Setup

```dockerfile
FROM python:3.12-slim
RUN curl -fsSL https://withcoral.com/install | sh
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY agent/ ./agent/
COPY api/ ./api/
COPY sources/ ./sources/
CMD ["python", "scripts/run_agent.py"]
```

---

## 11. Demo Script (3 minutes)

**0:00–0:30 — The problem**
"Every engineering team has GitHub, Sentry, Langfuse, and Slack open in separate tabs.
When something breaks at 2am, the on-call engineer spends 30 minutes switching tabs
to figure out what happened. Sentinel does that in 8 seconds."

**0:30–1:00 — Mode A: On-Call Brain**
Show the seeded cost spike in Langfuse. Show Sentinel detecting it.
Show the Slack message: full RCA with commit blame, error correlation, and Slack context.
Show the auto-created GitHub issue.

**1:00–1:30 — Mode B: PR Risk Scorer**
Open a PR that touches `prompt_templates/`. Show the GitHub Action running.
Show the PR comment: "Risk: HIGH. Last 4 times this file changed, cost spiked 38%."

**1:30–2:00 — Mode C: Weekly Digest**
Show the auto-generated Monday digest in Slack.
Three sections: What shipped, What broke, What to watch.
Show Slack thread context enriching each item.

**2:00–2:30 — Web Command Center**
Walk through: Incidents tab (drill into RCA), Risk tab (file heatmap),
Digest tab (archive), Settings tab (configure thresholds).

**2:30–3:00 — Technical depth**
"Under the hood: Coral cross-queries 5 sources with standard SQL.
We wrote the first Langfuse source spec for Coral — open sourced.
MCP integration lets Claude Code query Sentinel directly."
Show a Coral SQL query running live.

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Langfuse source spec takes >4 hours | Medium | High | Fallback to JSONL export (section 4.5) |
| `coral sql` doesn't support JSON output format | Medium | Medium | Parse tabular text with regex, or use MCP protocol |
| Cross-source JOIN performance is slow | Low | Medium | Use smaller time windows, add WHERE filters |
| Slack messages don't have useful content for demo | Medium | Low | Seed specific messages before demo |
| Sentry and Langfuse timestamps don't align for JOINs | Medium | High | Use wider time windows (±2 hours) in JOIN conditions |
| Railway container can't run Coral binary | Low | High | Fall back to local demo with ngrok tunnel |
| Claude API rate limits during demo | Low | High | Pre-generate reports, cache in SQLite |
| GitHub API rate limit (5000/hr) | Low | Low | Token auth gives 5000/hr, more than enough |

---

## Appendix A — Coral Features Checklist (for Judges)

| Feature | Used? | Where |
|---|---|---|
| Cross-source JOINs | ✅ | Every query joins 2–3 sources |
| Custom source spec | ✅ | Langfuse source spec (open sourced) |
| SQL interface | ✅ | All data retrieval via `coral sql` |
| Schema learning | ✅ | `coral.tables`, `coral.columns` used in setup |
| Caching | ✅ | Built-in, reduces API calls on repeated queries |
| MCP integration | ✅ | Claude Code config for `coral mcp-stdio` |
| 5+ data sources | ✅ | GitHub, Sentry, Datadog, Slack, Langfuse |

---

## Appendix B — Key URLs

- Coral docs: https://withcoral.com/docs
- Coral quickstart: https://withcoral.com/docs/getting-started/quickstart
- Custom source guide: https://withcoral.com/docs/guides/write-a-custom-source
- Source spec reference: https://withcoral.com/docs/reference/source-spec-reference
- Bundled sources: https://withcoral.com/docs/reference/bundled-sources
- MCP guide: https://withcoral.com/docs/guides/use-coral-over-mcp
- Langfuse API reference: https://api.reference.langfuse.com/
- Langfuse Observations API: https://langfuse.com/docs/api-and-data-platform/features/observations-api
- Langfuse Public API: https://langfuse.com/docs/api-and-data-platform/features/public-api
- Hackathon page: https://www.wemakedevs.org/hackathons/coral

---

*This document is the single source of truth for the Sentinel build.
Follow it step by step. Don't freestyle. Ship it.*