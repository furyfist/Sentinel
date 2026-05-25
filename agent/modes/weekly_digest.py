import argparse
from agent import query_library, memory, narrator
from agent.actions import slack_poster
from agent.config import SLACK_INCIDENTS_CHANNEL


def run(dry_run: bool = False) -> None:
    print(f"Starting Weekly Digest (dry_run={dry_run})...")

    # Step 1 — PRs merged in last 7 days
    print("  [1/5] Fetching merged PRs (last 7 days)...")
    shipped = query_library.weekly_digest_shipped()
    print(f"        {len(shipped)} PR(s) merged")

    # Step 2 — Sentry error rate
    print("  [2/5] Fetching Sentry errors (last 48h)...")
    errors = query_library.error_cascade_detection()
    print(f"        {len(errors)} error group(s)")

    # Step 3 — Langfuse cost trend
    print("  [3/5] Fetching Langfuse cost trend (last 24h)...")
    cost_trend = query_library.cost_spike_detection()
    print(f"        {len(cost_trend)} hourly cost row(s)")

    # Step 4 — narrate
    print("  [4/5] Narrating weekly digest with Groq...")
    digest_text = narrator.narrate_weekly_digest(shipped, errors, cost_trend)
    print("\n--- WEEKLY DIGEST ---")
    print(digest_text)
    print("--- END DIGEST ---\n")

    # Step 5 — post to Slack + save to SQLite
    print("  [5/5] Posting to Slack and saving to SQLite...")
    if dry_run:
        print(f"        [DRY RUN] Would post to {SLACK_INCIDENTS_CHANNEL}")
    else:
        ts = slack_poster.post_to_slack(SLACK_INCIDENTS_CHANNEL, digest_text)
        print(f"        Posted. ts={ts}")

    incident_id = memory.save_incident(
        detection_type="weekly_digest",
        severity="info",
        report_text=digest_text,
        related_commits=[str(p.get("number", "")) for p in shipped],
        cost_impact=sum(r.get("hourly_cost") or 0 for r in cost_trend),
    )
    print(f"        Digest saved to SQLite (id={incident_id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel Weekly Digest — Mode C")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack post")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
