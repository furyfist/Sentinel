# Demo Recording Guide

Recommended order. Run API + web UI first before anything else.

```bash
python scripts/run_agent.py        # API on :8000
cd web && npm run dev              # UI on :3000
```

---

## Step 1 — Seed data (do this first)

```bash
python scripts/seed_demo_data.py
```

Seeds Langfuse (baseline + spike observations), Sentry (10 RateLimitErrors), and Slack (4 incident context messages). Wait ~30s for Langfuse to process before running any agents.

---

## Step 2 — On-Call Brain → Slack RCA + GitHub issue

```bash
python agent/modes/oncall_brain.py --force
```

What happens:
- Detects cost spike (gpt-4 spike vs gpt-4o-mini baseline)
- Correlates with Sentry errors + recent GitHub commits + Slack messages
- Narrates RCA via Groq
- Posts report to Slack `#incidents`
- Creates GitHub issue titled `[Sentinel] Cost spike detected — ...`
- If spike doesn't hit auto-kill threshold → also posts Approve/Reject buttons to Slack

**Show in UI:** Dashboard (stat cards update), Incidents page (new entry)

---

## Step 3 — Approval flow → Slack interactive buttons

The Approve/Reject message fires automatically at the end of Step 2. If you want to seed one independently:

```bash
python -c "
from agent import memory
from agent.actions.slack_poster import post_approval_request
from agent.config import SLACK_INCIDENTS_CHANNEL
aid = memory.save_approval('create_issue', 'cost_spike', 'high', {'summary': 'Demo approval request', 'severity': 'high'}, expires_hours=4)
post_approval_request(SLACK_INCIDENTS_CHANNEL, aid, 'create_issue', {'summary': 'Demo approval request', 'severity': 'high'})
print('approval_id:', aid)
"
```

Click **Approve** in Slack → message updates to `✅ Approved by @you` → GitHub issue created.
Click **Reject** → message updates to `❌ Rejected by @you`.

**Show in UI:** Approvals page (pending → resolved)

---

## Step 4 — Agent Loop → Slack Kill Loop button

```bash
python scripts/seed_loop_scenario.py
```

Wait ~30s, then trigger detection:

```bash
curl http://localhost:8000/api/loops/detect
```

What happens:
- Finds the trace with 15 GENERATION observations (`retry-search` x15)
- Posts Slack alert: trace ID, gen count, cost burned, tool pattern
- Shows **Kill Loop** button

Click **Kill Loop** in Slack → message updates to `🛑 Loop kill acknowledged by @you`.

**Show in UI:** Dashboard (active loops card), Loops section

---

## Step 5 — Prompt Drift → Quality page

```bash
python scripts/seed_drift_scenario.py
```

Seeds 50 good observations (`{"response", "confidence", "category"}` schema), captures snapshot, then seeds 10 drifted ones (`{"answer", "score"}` — keys renamed).

Wait ~30s, then trigger scan:

```bash
curl -X POST http://localhost:8000/api/quality/scan
```

Or run directly (add `--dry-run` to skip Slack):

```bash
python agent/modes/drift_patrol.py
```

What happens:
- Validates recent `support-bot` outputs against snapshot
- Fail rate >15% → drift detected
- Blames the nearest GitHub commit
- Posts Slack alert

**Show in UI:** Quality page (schema snapshots, drift events with blame commit)

---

## Step 6 — PR Risk Scorer → PR comment on GitHub

Open a real PR on your GitHub repo, then:

```bash
python agent/modes/pr_risk_scorer.py --pr <PR_NUMBER>

# dry-run to preview score without posting
python agent/modes/pr_risk_scorer.py --pr <PR_NUMBER> --dry-run
```

What happens:
- Fetches changed files from GitHub API
- Looks up each file's error/cost history in SQLite
- Computes 0–100 risk score (`errors × 4 + min(cost × 10, 50)`)
- Narrates summary via Groq
- Posts comment to PR: `## Sentinel Risk Score: XX/100`
- If score >70 → requests changes

**Show in UI:** Risk page (file history, score breakdown)

---

## Step 7 — Weekly Digest → Slack

```bash
python agent/modes/weekly_digest.py
```

Posts "What Shipped · What Broke · What to Watch" to Slack.

**Show in UI:** Digest page

---

## Forensics page (no trigger needed)

After Steps 2–4, the Forensics page will have data. Open it to show the React Flow causal graph: commits → errors → traces → Slack messages.

```
http://localhost:3000/forensics
```

---

## Quick reference — all manual triggers

| Feature | Command |
|---------|---------|
| Seed all demo data | `python scripts/seed_demo_data.py` |
| On-Call Brain | `python agent/modes/oncall_brain.py --force` |
| Seed loop | `python scripts/seed_loop_scenario.py` |
| Trigger loop detection | `curl http://localhost:8000/api/loops/detect` |
| Seed drift | `python scripts/seed_drift_scenario.py` |
| Trigger drift scan | `curl -X POST http://localhost:8000/api/quality/scan` |
| Drift patrol direct | `python agent/modes/drift_patrol.py` |
| PR risk scorer | `python agent/modes/pr_risk_scorer.py --pr <N>` |
| Weekly digest | `python agent/modes/weekly_digest.py` |
