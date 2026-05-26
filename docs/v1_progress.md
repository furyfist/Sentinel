# Sentinel — Build Progress vs Plan

> Comparing actual build against `docs/buildplan/v1_buildplan.md`
> Builder: Himanshu | Sessions: 3–10 | Date completed: May 26, 2026

---

## What Was Built (All Sessions)

| Session | Focus | Status |
|---|---|---|
| 3 | Coral sources + Langfuse source spec | Done |
| 4 | Agent core (coral_client, query_library, anomaly_detector, narrator, memory) | Done |
| 5 | Three agent modes (oncall_brain, pr_risk_scorer, weekly_digest) | Done |
| 6 | Actions layer (slack_poster, github_commenter, github_issue_creator) | Done |
| 7 | FastAPI backend (8 routes across 4 router files) | Done |
| 8 | Seeding + scheduler + test scripts | Done |
| 9 | Next.js web UI (dashboard, incidents, risk, digest, settings) | Done |
| 10 | MCP config, GitHub Action, Dockerfile, README fix, gitignore cleanup | Done |

---

## Deviations from the Build Plan

### LLM Provider — narrator file name

**Plan:** `agent/claude_narrator.py`
**Built:** `agent/narrator.py`

The plan itself correctly identified Groq (llama-3.3-70b-versatile) as the LLM in section 2.4, but named the file `claude_narrator.py`. The actual file was named `narrator.py` to be LLM-agnostic. The README also incorrectly said "Claude API" — fixed in Session 10.

---

### Web UI Theme — light instead of dark

**Plan:** "Dark theme (matches the demo vibe), minimal, data-dense"
**Built:** Light theme — `bg-slate-50` background, white cards, indigo accents

User explicitly chose light theme during Session 9.

---

### Web folder structure — `src/` layout

**Plan:**
```
web/
├── app/
├── components/
└── lib/
```

**Built:**
```
web/src/
├── app/
├── components/
│   ├── layout/   (nav.tsx)
│   └── features/ (stat-card, risk-badge, incident-card, digest-section)
├── lib/          (api.ts, utils.ts)
└── types/        (index.ts)
```

Adopted the senior engineer `src/` directory layout with separated `layout/` and `features/` component folders. Types extracted to a dedicated `types/` module.

---

### `timeline.tsx` — not built

**Plan:** `components/timeline.tsx` listed in folder structure
**Built:** Not created. The incident detail page renders related commits as chips and errors as badges inline — a separate timeline component wasn't needed.

---

### Langfuse seeding — SDK API dropped

**Plan:** Seed via `lf.trace()` and `trace.generation()` SDK calls
**Built:** Langfuse SDK v4.6.1 dropped the `.trace()` API. Rewrote `scripts/seed_demo_data.py` to call the Langfuse REST ingestion API directly (`POST /api/public/ingestion`) with `trace-create` + `generation-create` batch events.

---

### Langfuse baseline volume — extra seeding needed

**Plan:** 100 baseline traces (days 1–7) + 20 spike traces
**Built:** 100 baseline traces (days 1–7) + 60 baseline traces at 3/hr across hours 3–22 of the current day + 20 spike traces in the last 45 minutes

The initial seeding had all 24h data as spike data (no baseline contrast). Added the hourly baseline seeding round to create a realistic spike-vs-normal ratio. Current spike: ~$7.59/hr vs baseline ~$0.000135/hr.

---

### Coral MCP args

**Plan:** `"args": ["mcp-stdio"]`
**Built:** `"args": ["mcp"]`

`coral mcp` is the correct invocation — `mcp-stdio` is not a valid subcommand.

---

### Slack channel — ID required, not name

**Plan:** `SLACK_INCIDENTS_CHANNEL=#incidents`
**Built:** `SLACK_INCIDENTS_CHANNEL=C0B61Q7K11Q`

`#incidents` returned `channel_not_found`. The Slack API requires a channel ID when using Bot tokens. User provided the channel ID directly.

---

### GitHub PAT — PR created manually

**Plan:** Push commits with known messages (`fix: update retry logic...`, etc.) via CLI
**Built:** PR #3 created via GitHub web UI

The fine-grained PAT lacked `contents:write` permission for git object creation via API. User created the demo PR manually through the GitHub web interface.

---

### `settings.json` — runtime config file (not in plan)

**Plan:** No mention of a settings file
**Built:** `settings.json` in project root, gitignored, with `settings.example.json` committed

The settings page (`/settings`) needs to persist threshold changes. Rather than modifying `.env` at runtime, a `settings.json` file is read/written by `api/routes/settings.py`. Defaults are defined as `_DEFAULTS` in code as a fallback.

---

### `docker-compose.yml` — not built

**Plan:** `docker-compose.yml` (agent + API + web services)
**Built:** Not created. Deployment was explicitly skipped. Only the `Dockerfile` for the FastAPI backend was created.

---

### `sources/langfuse/README.md` and `LICENSE` — not created

**Plan:** Both listed in folder structure
**Built:** Neither created. Not necessary for the hackathon submission itself.

---

### Additional files not in plan

| File | Why added |
|---|---|
| `scripts/test_api.py` | Verify all 8 FastAPI routes return correct data |
| `scripts/test_narrator.py` | Verify Groq narrator produces valid output |
| `scripts/test_queries.py` | Smoke test all 7 query library functions |
| `scripts/test_cross_join.sh` | Verify Coral cross-source JOINs work |
| `scripts/verify_sources.sh` | Check all 5 Coral sources are connected |
| `web/src/lib/utils.ts` | Required `cn()` helper for shadcn components |
| `web/src/types/index.ts` | TypeScript interfaces for all API response types |

---

## What Was Completed vs Planned

| Plan Section | Status | Notes |
|---|---|---|
| Phase 1 — Coral foundation | Done | All 5 sources connected; Langfuse custom spec built and installed |
| Phase 2 — Agent core | Done | All 5 modules (coral_client, query_library, anomaly_detector, narrator, memory) |
| Phase 3 — Three modes | Done | oncall_brain, pr_risk_scorer, weekly_digest — all with --dry-run and --force flags |
| Phase 4 — Actions layer | Done | slack_poster, github_commenter, github_issue_creator |
| Phase 5 — Web command center | Done | FastAPI + Next.js; 6 routes total (plan listed 8 — /risk/current/:pr merged into risk history) |
| Phase 6 — MCP + polish | Done | MCP config, GitHub Action, Dockerfile; docker-compose skipped |
| Seeding strategy | Done | Langfuse REST API, Sentry SDK, Slack bot — all seeded |
| Deployment | Skipped | User decision — Dockerfile exists but no Railway/Vercel deploy |

---

## Coral Features Checklist (Judges)

| Feature | Used | Where |
|---|---|---|
| Cross-source JOINs | Yes | `query_library.py` — every query joins 2–3 sources |
| Custom source spec | Yes | `sources/langfuse/manifest.yaml` — Langfuse (not bundled in Coral) |
| SQL interface | Yes | All data retrieval via `coral sql --format json` subprocess |
| Schema introspection | Yes | `coral.tables`, `coral.columns` used during setup and verification |
| Built-in caching | Yes | Automatic on repeated queries — reduces Langfuse/Sentry API traffic |
| MCP integration | Yes | `mcp/claude-code-config.json` — exposes Coral to Claude Code |
| 5+ data sources | Yes | GitHub, Sentry, Datadog, Slack, Langfuse |
