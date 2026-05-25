# Langfuse Source Spec for Coral

A custom Coral source spec that exposes Langfuse traces, observations, scores,
and sessions as queryable SQL tables.

## Tables

| Table | Description |
|---|---|
| `langfuse.projects` | Projects accessible with the configured API keys |
| `langfuse.traces` | Top-level LLM application traces |
| `langfuse.observations` | Spans, generations, and events within traces |
| `langfuse.scores` | Evaluation scores attached to traces or observations |
| `langfuse.sessions` | Multi-turn conversation sessions |

## Setup

```bash
# 1. Lint the spec
coral source lint ./sources/langfuse/manifest.yaml

# 2. Add the source (prompts for credentials)
coral source add --file ./sources/langfuse/manifest.yaml

# 3. Verify connectivity
coral source test langfuse

# 4. Confirm tables are visible
coral sql "SELECT schema_name, table_name FROM coral.tables WHERE schema_name = 'langfuse'"

# 5. Smoke test
coral sql "SELECT id, name, total_cost FROM langfuse.observations WHERE type = 'GENERATION' LIMIT 5"
```

## Credentials

| Variable | Where to find it |
|---|---|
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` (EU), `https://us.cloud.langfuse.com` (US), or your self-hosted URL |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project Settings → API Keys |
| `LANGFUSE_SECRET_KEY` | Langfuse project Settings → API Keys |

## Known Issues

**Scores table returns 404 on old self-hosted instances**
The `scores` table uses the `/api/public/v2/scores` endpoint. Langfuse Cloud
supports v2. Self-hosted instances older than ~mid-2024 may not. Fix: edit
`manifest.yaml` and change the scores table `path` from `/api/public/v2/scores`
to `/api/public/scores`. The column schema is identical.

## Useful Queries

```sql
-- Cost by hour (last 24h)
SELECT
  date_trunc('hour', start_time) as hour,
  SUM(total_cost) as hourly_cost,
  COUNT(*) as generation_count
FROM langfuse.observations
WHERE type = 'GENERATION'
  AND start_time > NOW() - INTERVAL '24 hours'
GROUP BY 1 ORDER BY 1 DESC;

-- Most expensive traces
SELECT trace_id, SUM(total_cost) as cost, COUNT(*) as generations
FROM langfuse.observations
WHERE type = 'GENERATION'
GROUP BY trace_id
ORDER BY cost DESC
LIMIT 10;

-- Error observations
SELECT id, trace_id, name, status_message, start_time
FROM langfuse.observations
WHERE level = 'ERROR'
ORDER BY start_time DESC
LIMIT 20;
```
