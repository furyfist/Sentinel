#!/usr/bin/env bash
# Validates the core Coral cross-source JOIN capability (§1.5 of build plan).
# Runs a GitHub × Sentry JOIN to confirm multi-source queries work end-to-end
# before any agent code is written.
# Usage: bash scripts/test_cross_join.sh
#
# Correct github.commits column names (verified against Coral 0.3.0):
#   date    → commit__author__date
#   message → commit__message
#   author  → author__login
#   sha     → sha

set -euo pipefail

: "${GITHUB_OWNER:?Set GITHUB_OWNER in your .env (the GitHub org or user to query)}"
: "${GITHUB_REPO:?Set GITHUB_REPO in your .env (the GitHub repo name to query)}"

log() { echo "[cross-join] $*"; }

# ── Test 1: GitHub × Sentry commit-to-error JOIN ──────────────────────────────

log "Running GitHub × Sentry cross-source JOIN (§1.5)..."
coral sql --format json "
  SELECT
    g.sha,
    g.commit__message,
    g.commit__author__date,
    s.title AS sentry_issue,
    s.first_seen
  FROM github.commits g
  JOIN sentry.issues s
    ON s.first_seen > CAST(g.commit__author__date AS TIMESTAMP)
  WHERE g.owner = '${GITHUB_OWNER}'
    AND g.repo  = '${GITHUB_REPO}'
  LIMIT 5
" | python -c "
import sys, json
rows = json.load(sys.stdin)
print(f'[cross-join] GitHub x Sentry: {len(rows)} rows returned')
for r in rows[:3]:
    print(f'  sha={r.get(\"sha\",\"\")[:8]}  sentry={r.get(\"sentry_issue\",\"\")[:60]}')
"

# ── Test 2: Langfuse × GitHub cost-blame JOIN ─────────────────────────────────

log "Running Langfuse × GitHub cost-blame JOIN..."
coral sql --format json "
  SELECT
    g.sha,
    g.commit__message,
    g.commit__author__date,
    COUNT(l.id)         AS generations_after,
    SUM(l.total_cost)   AS cost_after
  FROM github.commits g
  LEFT JOIN langfuse.observations l
    ON l.start_time > CAST(g.commit__author__date AS TIMESTAMP)
   AND l.start_time < CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
   AND l.type = 'GENERATION'
  WHERE g.owner = '${GITHUB_OWNER}'
    AND g.repo  = '${GITHUB_REPO}'
    AND CAST(g.commit__author__date AS TIMESTAMP) > NOW() - INTERVAL '7 days'
  GROUP BY g.sha, g.commit__message, g.commit__author__date
  ORDER BY cost_after DESC NULLS LAST
  LIMIT 5
" | python -c "
import sys, json
rows = json.load(sys.stdin)
print(f'[cross-join] Langfuse x GitHub: {len(rows)} rows returned')
for r in rows[:3]:
    cost = r.get('cost_after') or 0
    print(f'  sha={str(r.get(\"sha\",\"\"))[:8]}  cost=\${cost:.4f}  gens={r.get(\"generations_after\",0)}')
"

# ── Test 3: 3-way JOIN (GitHub × Sentry × Langfuse) ─────────────────────────

log "Running 3-way GitHub × Sentry × Langfuse JOIN..."
coral sql --format json "
  SELECT
    g.sha,
    g.commit__message,
    COUNT(DISTINCT s.id)  AS errors_after,
    SUM(l.total_cost)     AS cost_after
  FROM github.commits g
  LEFT JOIN sentry.issues s
    ON s.first_seen BETWEEN g.commit__author__date AND CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
  LEFT JOIN langfuse.observations l
    ON l.start_time BETWEEN g.commit__author__date AND CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
   AND l.type = 'GENERATION'
  WHERE g.owner = '${GITHUB_OWNER}'
    AND g.repo  = '${GITHUB_REPO}'
    AND CAST(g.commit__author__date AS TIMESTAMP) > NOW() - INTERVAL '7 days'
  GROUP BY g.sha, g.commit__message
  ORDER BY errors_after DESC NULLS LAST
  LIMIT 5
" | python -c "
import sys, json
rows = json.load(sys.stdin)
print(f'[cross-join] 3-way JOIN: {len(rows)} rows returned')
for r in rows[:3]:
    cost = r.get('cost_after') or 0
    print(f'  sha={str(r.get(\"sha\",\"\"))[:8]}  errors={r.get(\"errors_after\",0)}  cost=\${cost:.4f}')
print('[cross-join] Cross-source JOINs working. Coral is ready.')
"
