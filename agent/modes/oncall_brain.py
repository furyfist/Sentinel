import argparse
from agent import query_library, memory
from agent.anomaly_detector import detect_cost_spike


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel On-Call Brain — Mode A")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack post and GitHub issue creation")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
