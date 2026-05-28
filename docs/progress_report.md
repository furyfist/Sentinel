# Sentinel V2 — Progress Report

**Project:** Pirates of the Coral-bean Hackathon — Track 1: Enterprise Agent  
**Builder:** Himanshu  
**Window:** May 27–31, 2026  
**Branch:** `feature/sentinel-v2`  
**Total commits on branch:** 60+  
**Codebase:** 27 agent modules · 17 API modules · 27 frontend components · 12 scripts

---

## What Was Built

Sentinel V2 is an AI agent observability platform that solves 5 real enterprise problems using Coral SQL across 7 live data sources (GitHub, Sentry, Datadog, Slack, Langfuse, PagerDuty, Linear).

---

## Phase 1 — Webhook Infrastructure

**Problem solved:** Slack interactive messages need HMAC verification and a clean routing layer.

| File | What it does |
|---|---|
| `agent/config.py` | Added `SLACK_SIGNING_SECRET` |
| `api/middleware/slack_verify.py` | HMAC-SHA256 Slack signature verification, 5-min replay attack prevention |
| `api/routes/slack_actions.py` | Single endpoint for all Slack interactive payloads — routes approve/reject/kill |
| `agent/actions/slack_poster.py` | Block Kit interactive messages — approval requests + loop alerts with buttons |
| `agent/anomaly_detector.py` | Rewritten as class-based `AnomalyDetector` + `AnomalyResult` dataclass |
| `agent/memory.py` | 5 new SQLite tables: `loop_detections`, `schema_snapshots`, `drift_events`, `approval_queue`, `sampling_stats` |
| `scripts/test_webhook_flow.py` | Test script that fires a real Slack approval request |

**Status:** Complete. All routes registered, middleware verified, HMAC logic tested.

---

## Phase 2 — Loop Detection (Problem 1)

**Problem solved:** Multi-agent retry loops burn $400 at 3am before anyone notices.

| File | What it does |
|---|---|
| `agent/detectors/loop_detector.py` | Coral SQL detects traces with gen_count > threshold in last 2h |
| `agent/detectors/loop_detector.py` | `fingerprint_loop()` — name histogram, most_repeated_name, cost_velocity_per_min |
| `agent/detectors/loop_detector.py` | `run()` — fires Slack alert with Kill Loop button, saves to SQLite |
| `agent/query_library.py` | Q16: loop detection query · Q17: loop fingerprint query |
| `api/routes/loops.py` | `GET /loops/active` · `/loops/history` · `/loops/{id}/fingerprint` |
| `web/src/app/page.tsx` | Active Loops stat card (red if > 0) + alert banner with trace details |
| `scripts/seed_loop_scenario.py` | Seeds 15 GENERATIONs on one trace in 3 min for demo |

**Status:** Complete. Dashboard shows live loop count, API returns active/history, fingerprinting works.

---

## Phase 3 — Prompt Drift Detection (Problem 2)

**Problem solved:** Minor prompt changes silently break JSON parsing downstream.

| File | What it does |
|---|---|
| `agent/detectors/drift_detector.py` | Schema snapshot per feature name, validates recent outputs against snapshot |
| `agent/detectors/drift_detector.py` | `blame_commit()` — Coral JOIN on GitHub commits within 48h of drift |
| `agent/modes/drift_patrol.py` | Scheduled mode: scans all features, bootstraps snapshots, posts Slack |
| `api/routes/quality.py` | `GET /quality/snapshots` · `/quality/drift` · `POST /quality/scan` · `/quality/feature/{name}/validation` |
| `scripts/seed_drift_scenario.py` | Seeds 50 good observations + schema snapshot + 10 drifted observations |

**Status:** Complete. Drift patrol runs with `--dry-run`, schema validation catches renamed keys, blame commit works if GitHub commits exist.

---

## Phase 4 — Silent Tool Failures + Forensics Graph (Problem 3)

**Problem solved:** Tool returns `200 OK` but output is semantically garbage. No way to visualise what happened in a trace.

| File | What it does |
|---|---|
| `agent/detectors/tool_failure_detector.py` | Strategy A: JSON/non-JSON switching · Strategy B: Sentry correlation JOIN · Strategy C: output length anomaly via QUALIFY |
| `agent/forensics/trace_reconstructor.py` | Pulls Langfuse observations, builds React Flow nodes/edges per trace |
| `agent/forensics/incident_graph_builder.py` | Cross-source causal graph: commit → error → trace → Slack message |
| `api/routes/forensics.py` | `GET /forensics/trace/{id}` · `/forensics/incident` · `/forensics/worst-traces` (with 10s timeout) |
| `web/src/app/forensics/page.tsx` | Left sidebar of worst traces + React Flow canvas + incident graph toggle |
| `web/src/app/incidents/[id]/page.tsx` | Report / Dependency Graph tabs, graph loads ±2h incident window |
| `web/src/components/features/graph/` | 6 custom node types: commit (indigo), error (red), trace (amber), message (teal), generation (violet), span (sky) |
| `web/src/lib/graph-layout.ts` | `autoLayout()` — horizontal (tiered by type) and vertical (topological sort) |
| `@xyflow/react` | React Flow v12 installed, CSS imported in globals.css |

**Status:** Complete. Forensics page renders, graph layout works, incident graph builds from 4 sources. Timeout wrapper prevents Coral hangs.

---

## Phase 5 — Human-in-the-Loop Governance (Problem 4)

**Problem solved:** Agents execute high-risk actions without human checkpoints.

| File | What it does |
|---|---|
| `agent/governance/approval_gate.py` | `should_auto_act()` — auto-kills loops > 20 gens or cost > $10 · `route()` — queues everything else for human review |
| `agent/governance/approval_gate.py` | `execute_action_for_approval()` — runs kill_loop or create_github_issue on approval |
| `agent/governance/approval_gate.py` | `expire_stale_approvals()` — marks expired after 4h, updates Slack message |
| `scripts/run_agent.py` | New `anomaly_gate` job (every 15 min) + `expire_approvals` job (every 30 min) |
| `api/routes/approvals.py` | `GET /approvals` · `POST /approvals/{id}/approve` · `POST /approvals/{id}/reject` · `GET /approvals/stats` |
| `web/src/app/approvals/page.tsx` | Pending / Approved / Rejected / Expired tab view with Approve/Reject buttons |
| `web/src/components/layout/nav.tsx` | Approvals nav link with red badge showing live pending count, polls every 30s |

**Status:** Complete. Full approval flow works — create via anomaly gate, approve via web UI or Slack button, action executes, expiry runs on schedule.

---

## Phase 6 — Smart Sampling + Dashboard Polish (Problem 5)

**Problem solved:** "Log everything" breaks observability budgets — need to keep errors, spikes, and novelty; drop noise.

| File | What it does |
|---|---|
| `agent/sampling/smart_sampler.py` | Scores traces: +100 error, +80 cost spike, +70 schema fail, +60 novel pattern, +40 high-gen. Threshold ≥ 40 = keep |
| `agent/modes/oncall_brain.py` | Step 0 now runs smart sampler before any analysis, saves stats to SQLite |
| `agent/query_library.py` | `get_recent_traces()` — fetches all trace metadata for sampler input |
| `api/routes/sampling.py` | `GET /sampling/stats` · `GET/PUT /sampling/policy` |
| `web/src/app/page.tsx` | Sampling efficiency widget: "47 of 300 traces analysed, 85% noise dropped" with progress bar |
| `web/src/app/page.tsx` | Dashboard polish: 5-column stat grid, drift status indicator, pending approvals count, projected 6h cost, all cards link to detail pages |
| `web/src/app/quality/page.tsx` | Quality page: drift events list + schema snapshots list |
| `web/src/components/layout/nav.tsx` | Quality link added between Forensics and Approvals |
| `scripts/seed_v2_demo.py` | All-in-one demo seeder: loop + drift + silent failure + approval queue + sampling baseline |

**Status:** Complete. Sampler runs in scheduler, dashboard shows live sampling stats, Quality page renders drift events.

---

## Testing

### Automated (all passing)

| Suite | Result |
|---|---|
| Python unit tests — 23 assertions across all phases | 23/23 PASS |
| HTTP endpoint tests — 15 routes | 15/15 PASS |
| TypeScript compilation | Clean (0 errors) |
| Memory CRUD — all 5 tables | PASS |
| Approval flow via HTTP | PASS |

Run with:
```bash
.\venv\Scripts\python.exe scripts\test_v2_automated.py
.\venv\Scripts\python.exe scripts\test_memory_crud.py
.\venv\Scripts\python.exe scripts\test_slack_verify.py
cd web && npx tsc --noEmit
```

### Manual (requires live services)

See `docs/testing_guide.md` for the full checklist. Summary:

| # | Test | Requires |
|---|---|---|
| 1 | Slack button callbacks | ngrok + Slack |
| 2 | Langfuse loop seeding + detection | Langfuse |
| 3 | Drift patrol dry-run | Langfuse |
| 4 | Forensics graph page rendering | Browser |
| 5 | Nav badge live update | Browser |
| 6 | Approvals web page CRUD | Browser |
| 7 | GitHub issue on approval | GitHub token |
| 8 | Full V2 demo seed end-to-end | Langfuse |
| 9 | Incident dependency graph tab | Browser |
| 10 | Slack signing secret rejection | ngrok + Slack |

---

## Current File Map

```
agent/
  anomaly_detector.py        — AnomalyDetector class + AnomalyResult dataclass
  config.py                  — All env vars and thresholds
  coral_client.py            — Coral SQL client wrapper
  memory.py                  — SQLite: 9 tables, full CRUD
  narrator.py                — Groq narration for incident reports
  query_library.py           — 17 Coral SQL queries
  actions/
    slack_poster.py          — post_to_slack, post_approval_request, post_loop_alert
    github_issue_creator.py  — create_incident_issue
    github_commenter.py      — request_changes on PRs
  detectors/
    loop_detector.py         — Problem 1: loop detection + fingerprint
    drift_detector.py        — Problem 2: schema drift + blame commit
    tool_failure_detector.py — Problem 3: silent failures (3 strategies)
  forensics/
    trace_reconstructor.py   — Single-trace React Flow graph
    incident_graph_builder.py— Cross-source causal graph
  governance/
    approval_gate.py         — HITL routing: auto-act vs queue for approval
  sampling/
    smart_sampler.py         — Score-based trace filtering
  modes/
    oncall_brain.py          — Every 15 min: sample → detect → route
    weekly_digest.py         — Mondays 9am: shipped PRs + errors + cost
    drift_patrol.py          — Scheduled schema validation + Slack alerts
    pr_risk_scorer.py        — On-demand: risk score per PR

api/
  main.py                    — FastAPI app, all routers wired
  middleware/slack_verify.py — HMAC-SHA256 Slack signature verification
  routes/
    incidents.py             — /incidents
    loops.py                 — /loops/active, /history, /fingerprint
    quality.py               — /quality/snapshots, /drift, /scan, /validation
    forensics.py             — /forensics/trace, /incident, /worst-traces
    approvals.py             — /approvals, /approve, /reject, /stats
    sampling.py              — /sampling/stats, /policy
    slack_actions.py         — /slack/actions (Slack interactive callbacks)
    risk.py, digest.py, settings.py, commits.py

web/src/
  app/
    page.tsx                 — Dashboard: 5 stat cards + loop alert + sampling widget
    incidents/page.tsx       — Incident list
    incidents/[id]/page.tsx  — Incident detail + dependency graph tab
    forensics/page.tsx       — React Flow trace/incident graph explorer
    quality/page.tsx         — Drift events + schema snapshots
    approvals/page.tsx       — Pending/Approved/Rejected/Expired queue
    risk/page.tsx, digest/page.tsx, settings/page.tsx
  components/
    layout/nav.tsx           — Sticky nav with Approvals badge
    features/graph/          — 6 custom React Flow node types
    features/stat-card.tsx, incident-card.tsx, digest-section.tsx
  lib/
    api.ts                   — Typed fetch client for all API routes
    graph-layout.ts          — autoLayout() horizontal + vertical

scripts/
  run_agent.py               — APScheduler: oncall_brain + anomaly_gate + expire_approvals
  seed_v2_demo.py            — All-in-one V2 demo seeder
  seed_loop_scenario.py      — Loop demo seeder
  seed_drift_scenario.py     — Drift demo seeder
  test_v2_automated.py       — 23-assertion automated test suite
  test_memory_crud.py        — Memory CRUD targeted tests
  test_slack_verify.py       — HMAC logic tests
  test_webhook_flow.py       — Live Slack webhook test
```

---

## What's Left (Phase 6.8–6.10)

| Step | What | Status |
|---|---|---|
| 6.8 | Deploy — Railway (API) + Vercel (frontend) | Not started |
| 6.9 | Write `sources/langfuse/README.md` community spec | Not started |
| 6.10 | Demo video | Not started |
