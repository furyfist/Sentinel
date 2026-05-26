"""
Drift Patrol — scheduled mode that runs every 4 hours.

For each feature (observation name) seen in the last 24h:
  1. Pull latest 20 outputs
  2. If no schema snapshot → bootstrap one (no alert)
  3. If snapshot exists → validate against it
  4. If fail rate > threshold → record drift event, blame commit, post Slack alert
"""
import argparse
from agent import memory, coral_client
from agent.config import SLACK_INCIDENTS_CHANNEL
from agent.detectors.drift_detector import DriftDetector
from agent.actions.slack_poster import post_to_slack


def _build_drift_blocks(event: dict) -> list:
    feature = event["feature_name"]
    drift_type = event["drift_type"]
    fail_rate = event["validation_fail_rate"]
    blame = event.get("blame_commit_message") or "unknown"
    blame_sha = event.get("blame_commit_sha") or ""

    text = (
        f"*Prompt Drift Detected: `{feature}`*\n"
        f"Type: `{drift_type}` | Fail rate: `{fail_rate:.0%}`\n"
        f"Blame: `{blame_sha[:8]}` — {blame[:80]}"
    )
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Sentinel Drift Patrol — requires human review"}
            ],
        },
    ]


def run(dry_run: bool = False) -> None:
    print(f"Starting Drift Patrol (dry_run={dry_run})...")
    detector = DriftDetector(coral_client, memory)

    print("  Fetching distinct feature names from last 24h...")
    features = detector.get_recent_feature_names(hours=24)
    print(f"  Found {len(features)} feature(s): {features}")

    bootstrapped, drifts_found = 0, 0

    for feature in features:
        print(f"  Scanning feature: {feature}")
        observations = detector.get_recent_outputs(feature, limit=20)
        if not observations:
            print(f"    No observations found, skipping.")
            continue

        snapshot = memory.get_schema_snapshot(feature)
        if not snapshot:
            outputs = [o.get("output", "") or "" for o in observations]
            schema = detector.capture_schema_snapshot(feature, outputs)
            print(f"    Bootstrapped schema snapshot: {list(schema.keys())[:5]}")
            bootstrapped += 1
            continue

        validation = detector.validate_observations(feature, observations)
        fail_rate = validation.get("fail_rate", 0.0)
        print(f"    Validation: {validation['passed']}/{validation['total']} passed, fail_rate={fail_rate:.2%}")

        if fail_rate < detector.fail_rate_threshold:
            score_reg = detector.check_score_regression(feature)
            if not score_reg:
                print(f"    No drift detected.")
                continue
            event = {
                "feature_name": feature,
                "drift_type": "score_regression",
                "severity": "medium",
                "validation_fail_rate": 0.0,
                "details": score_reg,
                "blame_commit_sha": None,
                "blame_commit_message": None,
            }
        else:
            drift_start = str(observations[0].get("start_time", ""))
            blame = detector.blame_commit(drift_start)
            event = {
                "feature_name": feature,
                "drift_type": "schema_break",
                "severity": "high" if fail_rate > 0.5 else "medium",
                "validation_fail_rate": fail_rate,
                "details": validation,
                "blame_commit_sha": blame.get("sha") if blame else None,
                "blame_commit_message": blame.get("message") if blame else None,
            }

        drift_id = memory.save_drift_event(
            feature_name=event["feature_name"],
            drift_type=event["drift_type"],
            severity=event["severity"],
            validation_fail_rate=event["validation_fail_rate"],
            details=event["details"],
            blame_commit_sha=event.get("blame_commit_sha"),
            blame_commit_message=event.get("blame_commit_message"),
        )
        print(f"    Drift event saved (id={drift_id})")
        drifts_found += 1

        if dry_run:
            print(f"    [DRY RUN] Would post to Slack: {event['drift_type']} on {feature}")
        else:
            blocks = _build_drift_blocks(event)
            ts = post_to_slack(
                SLACK_INCIDENTS_CHANNEL,
                f"Prompt drift detected on '{feature}'",
                blocks,
            )
            print(f"    Posted to Slack (ts={ts})")

    print(f"\nDrift Patrol complete. Bootstrapped={bootstrapped}, DriftsFound={drifts_found}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel Drift Patrol")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack posting")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
