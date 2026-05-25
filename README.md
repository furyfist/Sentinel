# Sentinel

AI-powered engineering observability agent for the [Pirates of the Coral-bean](https://www.wemakedevs.org/hackathons/coral) hackathon (WeMakeDevs × Coral).

Sentinel cross-queries GitHub, Sentry, Langfuse, Datadog, and Slack via Coral's SQL interface — then uses Claude to narrate what went wrong, why, and who caused it.

## Three Modes

| Mode | Trigger | Output |
|---|---|---|
| On-Call Brain | Cost spike or error cascade detected | RCA report posted to Slack + GitHub issue created |
| PR Risk Scorer | GitHub PR opened | Risk score comment on the PR |
| Weekly Digest | Monday 9am cron | "What shipped · What broke · What to watch" in Slack |

## Architecture

```
GitHub + Sentry + Datadog + Slack + Langfuse
              ↓ (SQL via Coral)
         Sentinel Agent (Python)
              ↓
         Claude API (narration)
              ↓
    Slack / GitHub / SQLite / Web UI
```

## Setup

### 1. Prerequisites

- Python 3.12+
- Node.js 20+
- [Coral](https://withcoral.com) binary
- API keys for: GitHub, Sentry, Datadog, Slack, Langfuse, Anthropic

### 2. Install Coral

```bash
curl -fsSL https://withcoral.com/install | sh
coral --version
```

### 3. Add data sources

```bash
bash scripts/setup_coral.sh
```

### 4. Configure environment

```bash
cp .env.example .env
# Fill in all values in .env
```

### 5. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the agent

```bash
python scripts/run_agent.py
```

### 7. Run the web UI

```bash
cd web && npm install && npm run dev
```

## Data Sources

| Source | Type | What Sentinel queries |
|---|---|---|
| GitHub | Bundled in Coral | Commits, PRs, issues |
| Sentry | Bundled in Coral | Errors, events |
| Datadog | Bundled in Coral | Monitors, incidents, metrics |
| Slack | Bundled in Coral | Messages, channels |
| Langfuse | Custom spec (`sources/langfuse/`) | Traces, observations, costs |

## Coral Features Used

- Cross-source JOINs across all 5 sources
- Custom source spec (Langfuse — open sourced in `sources/langfuse/`)
- Schema introspection via `coral.tables` / `coral.columns`
- MCP integration via `mcp/claude-code-config.json`
- Built-in query caching

## Project Structure

```
sentinel/
├── sources/langfuse/      Coral source spec for Langfuse
├── agent/                 Python agent core
│   ├── modes/             On-Call Brain, PR Risk Scorer, Weekly Digest
│   └── actions/           Slack poster, GitHub commenter/issue creator
├── api/                   FastAPI backend serving the web UI
├── web/                   Next.js command center UI
├── scripts/               Setup, seeding, and runner scripts
└── mcp/                   MCP config for Claude Code integration
```
