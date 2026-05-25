# Sentinel — 10-Session Build Distribution

> **Deadline:** May 31, 2026 · **Today:** May 25, 2026 · **6 days, ~2 sessions/day**
> This maps `v1_buildplan.md` phases to concrete chat sessions. Each session has a clear start state, exit criteria, and the exact files to produce. Never start a session until the previous session's exit criteria are met.

---

## Session Map Overview

| Session | Theme | Build Plan Phase | Key Deliverable |
|---|---|---|---|
| 1 | Repo scaffold + Langfuse source spec | Phase 1 (partial) | `sources/langfuse/manifest.yaml` linting clean |
| 2 | Coral environment + source verification | Phase 1 (complete) | All 5 sources connected, cross-source JOIN working |
| 3 | Agent plumbing | Phase 2 (partial) | `coral_client.py`, `query_library.py`, `anomaly_detector.py` |
| 4 | Claude integration + persistence | Phase 2 (complete) | `claude_narrator.py`, `memory.py`, smoke test passing |
| 5 | On-Call Brain (Mode A) | Phase 3 (partial) | `oncall_brain.py` end-to-end, Slack post confirmed |
| 6 | PR Risk Scorer + Weekly Digest (Modes B & C) | Phase 3 (complete) | Both modes run without errors |
| 7 | Actions layer | Phase 4 | Slack post, GitHub comment, GitHub issue all tested |
| 8 | FastAPI backend | Phase 5 (partial) | All 8 API routes serving real data |
| 9 | Next.js web UI | Phase 5 (complete) | All 5 pages render real data, dark theme |
| 10 | MCP + GitHub Action + Seed + Deploy | Phase 6 + Appendices | Live deploy, demo script rehearsed |

---

## Session 1 — Repo Scaffold + Langfuse Source Spec
**Duration estimate:** ~3 hours  
**Build plan refs:** §5 (folder structure), §4 (Langfuse source spec)

### What to do
1. Initialize the full folder structure from §5 exactly — all dirs and placeholder `__init__.py` files.
2. Create `.env.example` with every required env var documented.
3. Write `sources/langfuse/manifest.yaml` following §4.1–4.3 (BasicAuth, 4 tables: traces, observations, scores, sessions).
4. Write `sources/langfuse/README.md` explaining standalone use.
5. Run `coral source lint ./sources/langfuse/manifest.yaml` — must pass clean.
6. Create `docs/buildplan/session_plan.md` (this file) and `README.md` skeleton.

### Files produced
```
sentinel/
├── README.md                        (skeleton)
├── .env.example
├── sources/langfuse/
│   ├── manifest.yaml                ← main deliverable
│   └── README.md
├── agent/__init__.py                (empty)
├── agent/modes/__init__.py          (empty)
├── agent/actions/__init__.py        (empty)
├── api/__init__.py                  (empty)
├── scripts/                         (empty dir)
├── mcp/                             (empty dir)
└── web/                             (next.js init deferred to Session 9)
```

### Exit criteria
- [ ] `coral source lint ./sources/langfuse/manifest.yaml` returns no errors
- [ ] Full folder structure matches §5 exactly
- [ ] `.env.example` lists: GITHUB_TOKEN, SENTRY_AUTH_TOKEN, DD_API_KEY, DD_APP_KEY, SLACK_BOT_TOKEN, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST, ANTHROPIC_API_KEY, GITHUB_OWNER, GITHUB_REPO, SLACK_INCIDENTS_CHANNEL

---

## Session 2 — Coral Environment + Source Verification
**Duration estimate:** ~2 hours  
**Build plan refs:** §1.1–1.5 (Phase 1 steps), §4.4 (Langfuse validation)

### Start state
Session 1 exit criteria all green.

### What to do
1. Install Coral binary (`curl -fsSL https://withcoral.com/install | sh`).
2. Add all 4 bundled sources: github, sentry, datadog, slack.
3. Add the custom Langfuse source: `coral source add --file ./sources/langfuse/manifest.yaml`.
4. Run the full §4.4 validation checklist for Langfuse (lint → add → test → verify tables → smoke query).
5. Run the cross-source JOIN from §1.5 to confirm Coral works end-to-end.
6. Write `scripts/setup_coral.sh` — the repeatable setup script for anyone (or CI) to run.

### Files produced
```
scripts/setup_coral.sh
```

### Exit criteria
- [ ] `coral sql "SELECT schema_name, table_name FROM coral.tables ORDER BY 1,2"` returns rows from github, sentry, datadog, slack, langfuse schemas
- [ ] `SELECT * FROM langfuse.observations LIMIT 5` returns rows with `calculatedTotalCost` column
- [ ] Cross-source JOIN (§1.5) returns rows without error
- [ ] `scripts/setup_coral.sh` runs cleanly in a fresh shell

---

## Session 3 — Agent Plumbing
**Duration estimate:** ~3 hours  
**Build plan refs:** §2.1–2.3, §7 (SQL query library)

### Start state
Session 2 exit criteria all green.

### What to do
1. Write `agent/config.py` — env vars loaded from `.env`, constants (thresholds, channel names, owner/repo).
2. Write `agent/coral_client.py` — subprocess wrapper from §2.1. Test both JSON and tabular fallback. Handle timeouts and non-zero exit codes.
3. Write `agent/query_library.py` — all 7 queries from §7 as named functions that call `coral_client.query()`. Parameterized with owner/repo/timestamps.
4. Write `agent/anomaly_detector.py` — 3 functions from §2.3: `detect_cost_spike`, `detect_error_cascade`, `detect_agent_loop`.
5. Write a simple `scripts/test_queries.py` that runs each query and prints row counts — manual smoke test.

### Files produced
```
agent/config.py
agent/coral_client.py
agent/query_library.py
agent/anomaly_detector.py
scripts/test_queries.py
requirements.txt                     (anthropic, requests, python-dotenv, langfuse)
```

### Exit criteria
- [ ] `python scripts/test_queries.py` runs all 7 queries without exceptions
- [ ] `detect_cost_spike(10.0, 2.0)` returns True, `detect_cost_spike(1.0, 2.0)` returns False
- [ ] `coral_client.query()` raises `RuntimeError` on a bad SQL string (not silently returns empty)

---

## Session 4 — Groq Narrator + Persistence
**Duration estimate:** ~2 hours  
**Build plan refs:** §2.4 (claude_narrator → now groq_narrator), §2.5 (memory/SQLite)

### Start state
Session 3 exit criteria all green.

### What to do
1. Write `agent/narrator.py` from §2.4. Three narration functions: `narrate_incident`, `narrate_pr_risk`, `narrate_weekly_digest`. Uses Groq SDK (`pip install groq`). Model: `llama-3.3-70b-versatile` (set via `GROQ_MODEL` env var). Groq SDK is OpenAI-compatible — `client.chat.completions.create(...)`.
2. Write `agent/memory.py` from §2.5. Three tables: `file_risk_history`, `incident_reports`, `cost_baselines`. Write helper functions: `save_incident`, `get_file_risk_history`, `save_cost_baseline`, `get_baselines`.
3. Write a `scripts/test_narrator.py` — sends a small hardcoded SQL result dict to Groq, prints the narration. Verifies GROQ_API_KEY works and prompt format is correct.
4. Update `requirements.txt` with any new deps (groq, not anthropic).

### Files produced
```
agent/narrator.py
agent/memory.py
scripts/test_narrator.py
```

### Exit criteria
- [ ] `python scripts/test_narrator.py` returns a coherent English incident report from Groq
- [ ] `memory.py` creates `sentinel.db` SQLite file with all 3 tables on first import
- [ ] `save_incident(...)` + `get_incidents()` round-trip returns the saved row

---

## Session 5 — On-Call Brain (Mode A)
**Duration estimate:** ~3 hours  
**Build plan refs:** §3.1 (oncall_brain flow), §4.1 (slack_poster), §4.3 (github_issue_creator)

### Start state
Session 4 exit criteria all green.

### What to do
1. Write `agent/actions/slack_poster.py` from §4.1 (needed by Mode A first).
2. Write `agent/actions/github_issue_creator.py` from §4.3 (needed by Mode A).
3. Write `agent/modes/oncall_brain.py` — full 7-step flow from §3.1:
   - Query Langfuse cost (last 1h vs 7-day avg)
   - Detect spike → query Sentry errors in window
   - JOIN GitHub commits in last 48h
   - JOIN Slack messages in incident channels
   - Claude narrates the full picture
   - Post to Slack
   - Auto-create GitHub issue
4. Add a `--dry-run` flag that skips the Slack post and GitHub issue (for testing without side effects).
5. Run against seeded/real data and verify Slack message arrives.

### Files produced
```
agent/actions/slack_poster.py
agent/actions/github_issue_creator.py
agent/modes/oncall_brain.py
```

### Exit criteria
- [ ] `python -m agent.modes.oncall_brain --dry-run` runs without exception and prints the narrated report
- [ ] Live run posts a Slack message to the configured channel
- [ ] Live run creates a GitHub issue with the RCA body
- [ ] Incident is saved to `incident_reports` table in SQLite

---

## Session 6 — PR Risk Scorer + Weekly Digest (Modes B & C)
**Duration estimate:** ~3 hours  
**Build plan refs:** §3.2 (pr_risk_scorer), §3.3 (weekly_digest)

### Start state
Session 5 exit criteria all green.

### What to do
1. Write `agent/actions/github_commenter.py` from §4.2.
2. Write `agent/modes/pr_risk_scorer.py` — full 8-step flow from §3.2. CLI args: `--pr=<number>`, `--owner`, `--repo`. Risk score formula: weighted sum of `errors_after` + `cost_after` from `file_risk_history`. Claude generates human-readable summary.
3. Write `agent/modes/weekly_digest.py` — full 7-step flow from §3.3. Structured 3-section digest: What Shipped, What Broke, What to Watch.
4. Add `--dry-run` to both modes.
5. Write `scripts/run_agent.py` — the scheduler that runs On-Call Brain every 15 min, PR Risk on demand, Weekly Digest on Monday 9am (use `schedule` library or `apscheduler`).

### Files produced
```
agent/actions/github_commenter.py
agent/modes/pr_risk_scorer.py
agent/modes/weekly_digest.py
scripts/run_agent.py
```

### Exit criteria
- [ ] `python -m agent.modes.pr_risk_scorer --dry-run --pr=1` outputs a risk score 0–100 and a summary
- [ ] `python -m agent.modes.weekly_digest --dry-run` outputs the 3-section digest text
- [ ] Both modes save their output to SQLite
- [ ] `scripts/run_agent.py` starts without error and logs the schedule

---

## Session 7 — Actions Layer Integration Test
**Duration estimate:** ~2 hours  
**Build plan refs:** §4 (complete), §9 (seeding strategy)

### Start state
Session 6 exit criteria all green.

### What to do
1. End-to-end integration test: run all 3 modes live (not dry-run) against real/seeded data.
2. Run `scripts/seed_demo_data.py` from §9 — seed Langfuse cost spike, GitHub commits, Sentry errors, Slack messages.
3. Trigger On-Call Brain and verify: Slack message ✓, GitHub issue ✓, SQLite row ✓.
4. Trigger PR Risk Scorer on a real PR and verify: GitHub PR comment ✓, SQLite row ✓.
5. Trigger Weekly Digest and verify: Slack message ✓, SQLite row ✓.
6. Fix any bugs found during live integration testing.

### Files produced
```
scripts/seed_demo_data.py            (from §9.1–9.4)
```

### Exit criteria
- [ ] All 3 modes complete without exceptions against seeded data
- [ ] Slack receives messages from all 3 modes
- [ ] GitHub shows PR comment from Mode B
- [ ] GitHub shows auto-created issue from Mode A
- [ ] SQLite has rows in all 3 tables

---

## Session 8 — FastAPI Backend
**Duration estimate:** ~2.5 hours  
**Build plan refs:** §5.1 (FastAPI routes)

### Start state
Session 7 exit criteria all green.

### What to do
1. Write `api/models.py` — Pydantic models for IncidentReport, RiskHistory, DigestEntry, HealthStatus, Settings.
2. Write `api/routes/incidents.py` — GET /api/incidents, GET /api/incidents/:id (reads from SQLite).
3. Write `api/routes/risk.py` — GET /api/risk/history, GET /api/risk/current/:pr (live Coral query for the latter).
4. Write `api/routes/digest.py` — GET /api/digest/latest, GET /api/digest/history.
5. Write `api/routes/settings.py` — GET/PUT /api/settings (reads/writes agent/config thresholds).
6. Write `api/main.py` — FastAPI app, mount all routers, add CORS for Next.js on localhost:3000, add GET /api/health that checks Coral connectivity.
7. Test all 8 routes with `curl` or a quick `scripts/test_api.py`.

### Files produced
```
api/models.py
api/routes/incidents.py
api/routes/risk.py
api/routes/digest.py
api/routes/settings.py
api/main.py
```

### Exit criteria
- [ ] `uvicorn api.main:app --reload` starts without error
- [ ] `GET /api/health` returns `{"status": "ok", "coral": true}`
- [ ] `GET /api/incidents` returns the seeded incident from Session 7
- [ ] `GET /api/digest/latest` returns the seeded digest from Session 7
- [ ] All 8 routes return valid JSON (no 500s)

---

## Session 9 — Next.js Web UI
**Duration estimate:** ~3 hours  
**Build plan refs:** §5.2 (Next.js UI), §5 (design: dark theme, shadcn/ui)

### Start state
Session 8 exit criteria all green.

### What to do
1. `npx create-next-app@latest web --typescript --tailwind --app` — initialize the project.
2. Install `shadcn/ui` and pull needed components: card, badge, button, table, input, tabs.
3. Write `web/lib/api.ts` — typed fetch helpers for all 8 API routes.
4. Build 5 pages in order of demo importance:
   - `/` Dashboard: recent incidents, cost trend, risk alerts
   - `/incidents` list → detail with commit blame + Slack context
   - `/risk` PR risk history, file heatmap
   - `/digest` latest digest + archive
   - `/settings` threshold config form (PUT /api/settings)
5. Write shared components: `nav.tsx`, `incident-card.tsx`, `risk-badge.tsx`, `digest-section.tsx`, `timeline.tsx`.
6. Run dev server and manually walk through the full demo script (§11) in the browser.

### Files produced
```
web/                                 (full Next.js app)
  package.json
  next.config.js
  tailwind.config.js
  app/layout.tsx
  app/page.tsx
  app/incidents/page.tsx
  app/risk/page.tsx
  app/digest/page.tsx
  app/settings/page.tsx
  components/{nav,incident-card,risk-badge,digest-section,timeline}.tsx
  lib/api.ts
```

### Exit criteria
- [ ] `npm run dev` starts on port 3000 without errors
- [ ] Dashboard shows real incident data from the FastAPI backend
- [ ] Incident detail page shows commit blame, error list, and Slack messages
- [ ] Settings page can update thresholds via PUT /api/settings
- [ ] No console errors on any page
- [ ] Dark theme renders correctly

---

## Session 10 — MCP + GitHub Action + Deploy + Demo Rehearsal
**Duration estimate:** ~3 hours  
**Build plan refs:** §6 (MCP + GitHub Action), §10 (deployment), §11 (demo script)

### Start state
Session 9 exit criteria all green.

### What to do
1. Write `mcp/claude-code-config.json` from §6.1.
2. Write `.github/workflows/pr-risk.yml` from §6.2. Commit and push — trigger it on a real PR.
3. Write `Dockerfile` from §10 — python:3.12-slim, installs Coral, copies agent + api + sources.
4. Write `docker-compose.yml` — agent service + api service with SQLite volume mount.
5. Deploy to Railway (agent + API). Deploy web to Vercel. Confirm live URLs work.
6. Run the full demo script (§11) end-to-end: 3 minutes, real data, all 3 modes, web UI.
7. Write the final `README.md` — setup, demo, architecture diagram, judge-facing feature checklist (Appendix A).
8. Tag `v1.0.0` and submit.

### Files produced
```
mcp/claude-code-config.json
.github/workflows/pr-risk.yml
Dockerfile
docker-compose.yml
README.md                            (final version)
```

### Exit criteria
- [ ] `docker-compose up` boots agent + API cleanly
- [ ] GitHub Action triggers on PR open and posts a risk comment
- [ ] Railway deploy is live and API health endpoint returns 200
- [ ] Vercel deploy is live and web UI loads from production URL
- [ ] Full 3-minute demo script runs cleanly with no dead ends
- [ ] All 7 items in Appendix A judge checklist are demonstrable
- [ ] `README.md` has setup instructions that work from a cold clone

---

## Daily Schedule (6 days to deadline)

| Day | Date | Sessions | Goal |
|---|---|---|---|
| Day 1 | May 25 | 1 + 2 | Repo + Coral + all sources connected |
| Day 2 | May 26 | 3 + 4 | Full agent plumbing + Claude working |
| Day 3 | May 27 | 5 + 6 | All 3 modes running |
| Day 4 | May 28 | 7 + 8 | Integration tests green + API live |
| Day 5 | May 29 | 9 | Web UI complete |
| Day 6 | May 30 | 10 | Deploy + demo rehearsal. Buffer day = May 31 |

> **May 31 is a buffer day.** Use it only if a session slipped. Do not plan work for it — plan to be done on May 30.

---

## Context to pass into each session

Paste this block at the start of every new chat session:

```
Project: Sentinel — AI observability agent for the WeMakeDevs × Coral hackathon.
Deadline: May 31, 2026.
Build plan: docs/buildplan/v1_buildplan.md
Session plan: docs/buildplan/session_plan.md
Current session: [SESSION NUMBER]
Previous session exit criteria: [PASTE CHECKBOXES FROM PREVIOUS SESSION — ALL MUST BE CHECKED]

Today we are building: [PASTE THE FULL SESSION SECTION FROM THIS FILE]
```

---

*Follow the session plan. Don't jump ahead. Don't skip exit criteria. Ship it.*
