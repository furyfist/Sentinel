import argparse
from agent import query_library, memory


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel On-Call Brain — Mode A")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack post and GitHub issue creation")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
