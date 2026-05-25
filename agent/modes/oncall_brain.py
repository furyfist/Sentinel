import argparse
from agent import query_library, memory, narrator
from agent.anomaly_detector import detect_cost_spike
from agent.actions import slack_poster, github_issue_creator
from agent.config import SLACK_INCIDENTS_CHANNEL


def _compute_baseline(cost_rows: list) -> float:
    """7-day rolling avg from SQLite baselines; falls back to 24h Coral data."""
    stored = memory.get_baselines(limit=168)
    if stored:
        return sum(r["hourly_cost"] for r in stored) / len(stored)
    if cost_rows:
        return sum(r["hourly_cost"] or 0 for r in cost_rows) / len(cost_rows)
    return 0.0


def run(dry_run: bool = False) -> None:
    print(f"Starting On-Call Brain (dry_run={dry_run})...")

    # Step 1 — fetch last 24h of hourly cost and compute baseline
    print("  [1/7] Fetching Langfuse cost data...")
    cost_rows = query_library.cost_spike_detection()

    current_hourly_cost = cost_rows[0]["hourly_cost"] if cost_rows else 0.0
    baseline_avg = _compute_baseline(cost_rows)
    print(f"        current={current_hourly_cost:.4f}  baseline_avg={baseline_avg:.4f}")

    for row in cost_rows:
        memory.save_cost_baseline(
            hourly_cost=row["hourly_cost"] or 0.0,
            daily_cost=0.0,
        )

    # Step 2 — detect spike; pull Sentry errors if triggered
    print("  [2/7] Checking for cost spike...")
    spike_detected = detect_cost_spike(current_hourly_cost, baseline_avg)

    if not spike_detected and baseline_avg > 0:
        print("        No anomaly detected. Exiting.")
        return

    if baseline_avg == 0:
        print("        No baseline yet — running full pipeline to seed data.")

    print(f"        Spike detected={spike_detected}. Querying Sentry errors...")
    error_rows = query_library.error_cascade_detection()

    # Step 3 — GitHub commits in last 48h
    print("  [3/7] Fetching GitHub commits (last 48h)...")
    commit_rows = query_library.commit_to_cost_blame()

    # Step 4 — Slack context in the spike window
    print("  [4/7] Fetching Slack incident context...")
    spike_start = cost_rows[0]["hour"] if cost_rows else "2026-01-01T00:00:00Z"
    slack_rows = query_library.slack_incident_context(
        incident_start=str(spike_start),
        incident_end="2099-12-31T23:59:59Z",
    )

    context = {
        "cost": cost_rows[:5],
        "errors": error_rows,
        "commits": commit_rows[:10],
        "slack": slack_rows,
        "current_hourly_cost": current_hourly_cost,
        "baseline_avg": baseline_avg,
    }

    # Step 5 — narrate
    print("  [5/7] Narrating incident with Groq...")
    report = narrator.narrate_incident(context, detection_type="cost_spike")
    print("\n--- INCIDENT REPORT ---")
    print(report)
    print("--- END REPORT ---\n")

    # Step 6 — post to Slack
    print("  [6/7] Posting to Slack...")
    slack_ts = None
    if dry_run:
        print(f"        [DRY RUN] Would post to {SLACK_INCIDENTS_CHANNEL}")
    else:
        slack_ts = slack_poster.post_to_slack(SLACK_INCIDENTS_CHANNEL, report)
        print(f"        Posted. ts={slack_ts}")

    # Step 7 — create GitHub issue
    print("  [7/7] Creating GitHub issue...")
    issue_url = None
    if dry_run:
        print("        [DRY RUN] Would create GitHub issue")
    else:
        first_commit = commit_rows[0].get("commit_message", "unknown") if commit_rows else "unknown"
        issue_url = github_issue_creator.create_incident_issue(
            title=f"[Sentinel] Cost spike detected — possible cause: {first_commit[:60]}",
            body=report,
        )
        print(f"        Issue created: {issue_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel On-Call Brain — Mode A")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack post and GitHub issue creation")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
