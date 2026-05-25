#!/usr/bin/env bash
# Validates that all 5 Coral sources are connected and returning data.
# Run after setup_coral.sh to confirm the environment is healthy.
# Usage: bash scripts/verify_sources.sh

set -uo pipefail

PASS=0
FAIL=0

log()  { echo "[verify] $*"; }
pass() { echo "[verify] PASS: $*"; ((PASS++)); }
fail() { echo "[verify] FAIL: $*" >&2; ((FAIL++)); }

run_sql() {
  coral sql --format json "$1" 2>/dev/null
}

assert_rows() {
  local label="$1"
  local sql="$2"
  local result
  result=$(run_sql "$sql") || { fail "$label — query error"; return; }
  local count
  count=$(echo "$result" | python -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "0")
  if [[ "$count" -gt 0 ]]; then
    pass "$label (${count} rows)"
  else
    fail "$label — 0 rows returned"
  fi
}

# ── 1. Catalog: all 5 schemas present ────────────────────────────────────────

log ""
log "=== 1. Schema catalog ==="
result=$(run_sql "SELECT DISTINCT schema_name FROM coral.tables ORDER BY schema_name") || die "Catalog query failed"
for schema in github sentry datadog slack langfuse; do
  if echo "$result" | grep -q "\"$schema\""; then
    pass "Schema: $schema"
  else
    fail "Schema: $schema — not found in coral.tables"
  fi
done

# ── 2. Bundled source smoke tests ─────────────────────────────────────────────

log ""
log "=== 2. Bundled source smoke tests ==="

assert_rows "github.repos" \
  "SELECT id, name FROM github.repos LIMIT 1"

assert_rows "sentry.projects" \
  "SELECT id, name, slug FROM sentry.projects LIMIT 1"

assert_rows "datadog.monitors" \
  "SELECT id, name, type FROM datadog.monitors LIMIT 1"

assert_rows "slack.channels" \
  "SELECT id, name FROM slack.channels LIMIT 1"

# ── 3. Langfuse validation checklist (§4.4) ───────────────────────────────────

log ""
log "=== 3. Langfuse validation (§4.4) ==="

assert_rows "langfuse.projects" \
  "SELECT id, name FROM langfuse.projects LIMIT 1"

assert_rows "langfuse.traces" \
  "SELECT id, name, timestamp FROM langfuse.traces LIMIT 1"

assert_rows "langfuse.observations" \
  "SELECT id, trace_id, type, model, total_cost FROM langfuse.observations WHERE type = 'GENERATION' LIMIT 1"

assert_rows "langfuse.scores" \
  "SELECT id, trace_id, name, value FROM langfuse.scores LIMIT 1"

assert_rows "langfuse.sessions" \
  "SELECT id, created_at FROM langfuse.sessions LIMIT 1"

# Verify total_cost column specifically (critical for anomaly detection)
log ""
log "Checking total_cost column on langfuse.observations..."
result=$(run_sql "SELECT SUM(total_cost) as total FROM langfuse.observations WHERE type = 'GENERATION' LIMIT 100") || { fail "total_cost column query failed"; }
if echo "$result" | grep -q "total"; then
  pass "langfuse.observations.total_cost column is queryable"
else
  fail "langfuse.observations.total_cost — column not found or null"
fi

# ── 4. Result summary ─────────────────────────────────────────────────────────

log ""
log "=== Results ==="
log "PASSED: $PASS"
log "FAILED: $FAIL"
log ""

if [[ "$FAIL" -gt 0 ]]; then
  log "Some checks failed. Review output above."
  log "Common fixes:"
  log "  - Re-run scripts/setup_coral.sh with correct API keys"
  log "  - For Langfuse scores 404: see sources/langfuse/README.md Known Issues"
  log "  - For 0 rows on a source: confirm the API key has read permissions"
  exit 1
else
  log "All checks passed. Environment is ready for Session 3."
  exit 0
fi
