# Scripts

Run these in order when setting up a fresh environment.

## Order of execution

| Script | When to run | What it does |
|---|---|---|
| `setup_coral.sh` | Once, on fresh machine | Installs Coral + registers all 5 sources |
| `verify_sources.sh` | After setup, and after any credential change | Validates all sources return data |
| `test_cross_join.sh` | After verify passes | Confirms multi-source JOINs work |
| `seed_demo_data.py` | Before demo (Session 7) | Seeds Langfuse cost spike + Sentry errors |
| `test_queries.py` | After Session 3 | Smoke-tests all 7 SQL query library functions |
| `run_agent.py` | Production / local dev | Starts the scheduled agent (all 3 modes) |

## Prerequisites

- Coral installed (`coral --version` should work)
- All values in `.env` filled in
- Python 3.12+ with `pip install -r requirements.txt`

## Running setup

```bash
# Load env vars
set -a && source .env && set +a

# Install Coral + add sources
bash scripts/setup_coral.sh

# Confirm everything works
bash scripts/verify_sources.sh

# Confirm cross-source JOINs work
bash scripts/test_cross_join.sh
```

## Notes

- All `.sh` scripts require Bash. On Windows use Git Bash or WSL.
- `setup_coral.sh` is idempotent — safe to re-run if a source add fails midway.
- `verify_sources.sh` exits 1 if any check fails — useful in CI pre-flight.
- `test_cross_join.sh` requires `GITHUB_OWNER` and `GITHUB_REPO` set in `.env`.
