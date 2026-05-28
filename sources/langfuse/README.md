# Langfuse Source Spec for Coral

Query LLM traces, generations, evaluation scores, and sessions from Langfuse using SQL — on Langfuse Cloud or any self-hosted instance.

Built for **Sentinel V2** as part of the Pirates of the Coral-bean hackathon. This is the first community Coral source spec for Langfuse.

---

## Install

```bash
coral source add --file ./sources/langfuse/manifest.yaml
```

You will be prompted for three values:

| Variable | Where to find it |
|---|---|
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` (US), `https://cloud.langfuse.com` (EU), or your self-hosted URL |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project → Settings → API Keys → Public key |
| `LANGFUSE_SECRET_KEY` | Langfuse project → Settings → API Keys → Secret key |

Verify the connection:

```sql
SELECT * FROM langfuse.projects LIMIT 1;
SELECT COUNT(*) FROM langfuse.observations WHERE type = 'GENERATION';
```

---

## Tables

### `langfuse.observations`

The most useful table. Every LLM call, span, and event inside a trace.

| Column | Type | Description |
|---|---|---|
| `id` | text | Observation ID |
| `trace_id` | text | Parent trace ID — join to `langfuse.traces.id` |
| `type` | text | `GENERATION`, `SPAN`, or `EVENT` |
| `name` | text | Observation name (e.g. `chat-completion`, `retry-search`) |
| `model` | text | Model name (`gpt-4`, `claude-3-5-sonnet`, etc.) |
| `start_time` | text | Start timestamp (ISO 8601) |
| `end_time` | text | End timestamp (ISO 8601) |
| `latency` | float | Latency in seconds |
| `input_tokens` | int | Prompt token count |
| `output_tokens` | int | Completion token count |
| `total_tokens` | int | Total tokens (input + output) |
| `total_cost` | float | Calculated cost in USD |
| `input_cost` | float | Input cost in USD |
| `output_cost` | float | Output cost in USD |
| `level` | text | `DEBUG`, `DEFAULT`, `WARNING`, or `ERROR` |
| `status_message` | text | Error message or status detail |
| `model_parameters` | text | JSON object of model parameters |
| `environment` | text | `production`, `staging`, etc. |
| `version` | text | Application version tag |
| `created_at` | text | Record creation timestamp |
| `updated_at` | text | Record last-updated timestamp |

> **Note on token column names:** The Langfuse REST API returns `usage.input` and `usage.output`. This spec maps them to `input_tokens` and `output_tokens`. Some older Coral integrations may alias these as `prompt_tokens` / `completion_tokens` — use `input_tokens` / `output_tokens` with this spec.

---

### `langfuse.traces`

Top-level requests through your LLM application. One row per request.

| Column | Type | Description |
|---|---|---|
| `id` | text | Trace ID |
| `name` | text | Trace name — identifies the feature or use case |
| `user_id` | text | User associated with this trace |
| `session_id` | text | Session ID for multi-turn conversations |
| `timestamp` | text | Trace timestamp |
| `latency` | float | End-to-end latency in seconds |
| `total_cost` | float | Total cost across all observations |
| `release` | text | Application release tag |
| `version` | text | Application version tag |
| `tags` | text | JSON array of tags |
| `environment` | text | Deployment environment |
| `project_id` | text | Langfuse project ID |
| `created_at` | text | Record creation timestamp |
| `updated_at` | text | Record last-updated timestamp |

---

### `langfuse.scores`

Evaluation scores attached to traces or observations — from human annotation, LLM judges, or custom SDK calls.

| Column | Type | Description |
|---|---|---|
| `id` | text | Score ID |
| `trace_id` | text | Trace this score is attached to |
| `observation_id` | text | Observation this score is attached to (if observation-level) |
| `name` | text | Score name (`quality`, `relevance`, `hallucination`, etc.) |
| `value` | float | Numeric score value (null for categorical) |
| `string_value` | text | Categorical label (null for numeric) |
| `data_type` | text | `NUMERIC`, `CATEGORICAL`, or `BOOLEAN` |
| `source` | text | `API`, `ANNOTATION`, or `EVAL` |
| `comment` | text | Reviewer comment |
| `environment` | text | Deployment environment |
| `created_at` | text | Record creation timestamp |

> **Self-hosted note:** Scores use the `/api/public/v2/scores` endpoint. Langfuse Cloud (all regions) supports v2. If you are on a self-hosted instance older than mid-2024 and scores queries return 404, change the path in `manifest.yaml` from `/api/public/v2/scores` to `/api/public/scores`. The column schema is identical.

---

### `langfuse.sessions`

Groups of traces belonging to the same multi-turn conversation or workflow.

| Column | Type | Description |
|---|---|---|
| `id` | text | Session ID — filter traces with `WHERE session_id = '<id>'` |
| `project_id` | text | Project ID |
| `environment` | text | Deployment environment |
| `created_at` | text | Record creation timestamp |
| `updated_at` | text | Record last-updated timestamp |

---

### `langfuse.projects`

Projects accessible with the configured API keys. Mainly useful for connectivity testing.

| Column | Type | Description |
|---|---|---|
| `id` | text | Project ID |
| `name` | text | Project name |
| `created_at` | text | Project creation timestamp |

---

## Example Queries

### Hourly LLM cost for the last 24 hours

```sql
SELECT
  date_trunc('hour', start_time) AS hour,
  SUM(total_cost)                AS hourly_cost,
  COUNT(*)                       AS generation_count,
  AVG(total_cost)                AS avg_cost_per_call
FROM langfuse.observations
WHERE type = 'GENERATION'
  AND start_time > NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', start_time)
ORDER BY hour DESC
```

### Detect agent loops — traces with excessive generation counts

```sql
SELECT
  trace_id,
  COUNT(*)             AS gen_count,
  MIN(start_time)      AS first_gen,
  MAX(start_time)      AS last_gen,
  SUM(total_cost)      AS total_cost,
  COUNT(DISTINCT name) AS unique_names
FROM langfuse.observations
WHERE type = 'GENERATION'
  AND start_time > NOW() - INTERVAL '2 hours'
GROUP BY trace_id
HAVING COUNT(*) > 10
ORDER BY gen_count DESC
```

### Most expensive traces in the last 7 days

```sql
SELECT
  trace_id,
  COUNT(*)         AS observation_count,
  SUM(total_cost)  AS total_cost,
  MIN(start_time)  AS started_at,
  SUM(CASE WHEN level IN ('ERROR', 'WARNING') THEN 1 ELSE 0 END) AS error_count
FROM langfuse.observations
WHERE start_time > NOW() - INTERVAL '7 days'
GROUP BY trace_id
ORDER BY total_cost DESC NULLS LAST
LIMIT 20
```

### Detect prompt drift — recent outputs for a named feature

```sql
SELECT
  trace_id,
  name,
  output,
  start_time
FROM langfuse.observations
WHERE name = 'support-bot'
  AND type = 'GENERATION'
  AND start_time > NOW() - INTERVAL '24 hours'
ORDER BY start_time DESC
LIMIT 50
```

### Evaluation score regression — last 24h vs baseline

```sql
SELECT
  s.name       AS score_name,
  AVG(s.value) AS recent_avg,
  COUNT(*)     AS recent_count
FROM langfuse.scores s
JOIN langfuse.observations o ON o.trace_id = s.trace_id
WHERE s.data_type = 'NUMERIC'
  AND o.name = 'support-bot'
  AND s.created_at > NOW() - INTERVAL '24 hours'
GROUP BY s.name
```

### Silent tool failures — observations with abnormally short output

```sql
SELECT
  trace_id,
  name            AS tool_name,
  LENGTH(output)  AS output_len,
  AVG(LENGTH(output)) OVER (PARTITION BY name) AS avg_output_len,
  start_time
FROM langfuse.observations
WHERE type = 'GENERATION'
  AND start_time > NOW() - INTERVAL '6 hours'
QUALIFY LENGTH(output) < AVG(LENGTH(output)) OVER (PARTITION BY name) * 0.2
ORDER BY start_time DESC
```

### Join with GitHub commits to blame a cost spike

```sql
SELECT
  g.sha,
  g.commit__message AS commit_message,
  g.author__login   AS author,
  SUM(l.total_cost) AS cost_after_commit
FROM github.commits g
LEFT JOIN langfuse.observations l
  ON l.start_time BETWEEN CAST(g.commit__author__date AS TIMESTAMP)
                      AND CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
 AND l.type = 'GENERATION'
WHERE g.owner = 'your-org'
  AND g.repo  = 'your-repo'
  AND CAST(g.commit__author__date AS TIMESTAMP) > NOW() - INTERVAL '7 days'
GROUP BY g.sha, g.commit__message, g.author__login
ORDER BY cost_after_commit DESC NULLS LAST
LIMIT 10
```

---

## How It Works

Coral translates SQL into paginated REST API calls against the Langfuse public API. Each table maps to one endpoint:

| Table | Endpoint |
|---|---|
| `langfuse.observations` | `GET /api/public/observations` |
| `langfuse.traces` | `GET /api/public/traces` |
| `langfuse.scores` | `GET /api/public/v2/scores` |
| `langfuse.sessions` | `GET /api/public/sessions` |
| `langfuse.projects` | `GET /api/public/projects` |

Authentication is HTTP Basic Auth — `LANGFUSE_PUBLIC_KEY` as username, `LANGFUSE_SECRET_KEY` as password. Coral handles pagination automatically (page-based, up to 100 rows per request).

---

## Limitations

- **No `input` / `output` content columns.** The Langfuse API returns prompt and completion text, but this spec does not expose them as columns to avoid unbounded row sizes. Add them to `manifest.yaml` under `observations.columns` if needed.
- **Timestamps are strings.** Coral receives ISO 8601 strings from the API. Use `CAST(start_time AS TIMESTAMP)` in queries that need date arithmetic.
- **No real-time streaming.** Data reflects what Langfuse has indexed — expect up to ~30s lag after ingestion.
- **Rate limits.** Langfuse Cloud enforces API rate limits. Queries scanning large time windows may be throttled. Use `INTERVAL` filters to scope queries.
