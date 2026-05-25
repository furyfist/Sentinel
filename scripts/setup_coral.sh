#!/usr/bin/env bash
# Installs Coral and registers all 5 data sources for Sentinel.
# Run once on a fresh machine or CI container.
# Requires all env vars from .env.example to be set in the environment.
# Usage: bash scripts/setup_coral.sh

set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────

log()  { echo "[setup] $*"; }
die()  { echo "[setup] ERROR: $*" >&2; exit 1; }

require_env() {
  for var in "$@"; do
    [[ -n "${!var:-}" ]] || die "Required env var \$$var is not set. Copy .env.example to .env and fill it in."
  done
}

# ── 1. Install Coral ──────────────────────────────────────────────────────────

if command -v coral &>/dev/null; then
  log "Coral already installed: $(coral --version)"
else
  log "Installing Coral..."
  curl -fsSL https://withcoral.com/install | sh
  # The installer places the binary in ~/.local/bin or ~/bin — reload PATH
  export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
  command -v coral &>/dev/null || die "Coral install completed but binary not found on PATH. Add ~/.local/bin to your PATH and re-run."
  log "Coral installed: $(coral --version)"
fi

# ── 2. Bundled sources ────────────────────────────────────────────────────────

log "Adding GitHub source..."
require_env GITHUB_TOKEN
GITHUB_TOKEN="$GITHUB_TOKEN" coral source add github || log "GitHub source already added, skipping."

log "Adding Sentry source..."
require_env SENTRY_AUTH_TOKEN
SENTRY_AUTH_TOKEN="$SENTRY_AUTH_TOKEN" coral source add sentry || log "Sentry source already added, skipping."

log "Adding Datadog source..."
require_env DD_API_KEY DD_APP_KEY
DD_API_KEY="$DD_API_KEY" DD_APP_KEY="$DD_APP_KEY" coral source add datadog || log "Datadog source already added, skipping."

log "Adding Slack source..."
require_env SLACK_BOT_TOKEN
SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN" coral source add slack || log "Slack source already added, skipping."

# ── 3. Custom Langfuse source ─────────────────────────────────────────────────

log "Linting Langfuse source spec..."
coral source lint ./sources/langfuse/manifest.yaml

log "Adding Langfuse source..."
require_env LANGFUSE_HOST LANGFUSE_PUBLIC_KEY LANGFUSE_SECRET_KEY
LANGFUSE_BASE_URL="$LANGFUSE_HOST" \
LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY" \
LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY" \
  coral source add --file ./sources/langfuse/manifest.yaml || log "Langfuse source already added, skipping."

# ── 4. Summary ────────────────────────────────────────────────────────────────

log ""
log "All sources registered. Run scripts/verify_sources.sh to confirm."
log ""
coral sql "SELECT schema_name, COUNT(*) as table_count FROM coral.tables GROUP BY schema_name ORDER BY schema_name"
