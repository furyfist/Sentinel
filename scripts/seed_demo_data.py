"""Seed realistic demo data across Langfuse, Sentry, and Slack for Sentinel demo."""
import os
import sys
import random
import time
import requests
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agent.config import (
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL,
    SLACK_BOT_TOKEN, SLACK_INCIDENTS_CHANNEL, GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO,
)
from agent import memory


def _utcnow():
    return datetime.now(timezone.utc)


def clean_baselines():
    print("  Clearing cost_baselines so spike detection uses fresh Langfuse data...")
    with memory.get_connection() as conn:
        conn.execute("DELETE FROM cost_baselines")
    print("  Done.")


def seed_langfuse():
    from langfuse import Langfuse

    lf = Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_BASE_URL,
    )

    print("  Seeding 100 baseline observations (last 7 days, gpt-4o-mini)...")
    for i in range(100):
        days_ago = random.randint(1, 7)
        hours_ago = random.randint(0, 23)
        start = _utcnow() - timedelta(days=days_ago, hours=hours_ago)
        trace = lf.trace(name="normal-query", user_id="user-baseline")
        trace.generation(
            name="baseline-gen",
            model="gpt-4o-mini",
            start_time=start,
            end_time=start + timedelta(seconds=2),
            usage={"input": 100, "output": 50, "unit": "TOKENS"},
        )

    print("  Seeding 20 spike observations (last 45 minutes, gpt-4)...")
    spike_base = _utcnow() - timedelta(minutes=45)
    for i in range(20):
        start = spike_base + timedelta(minutes=i * 2)
        trace = lf.trace(name="runaway-agent", user_id="agent-loop-demo")
        trace.generation(
            name="spike-gen",
            model="gpt-4",
            start_time=start,
            end_time=start + timedelta(seconds=8),
            usage={"input": 5000, "output": 3000, "unit": "TOKENS"},
        )

    lf.flush()
    print("  Langfuse seeding complete and flushed.")


def seed_sentry():
    import sentry_sdk

    org = os.environ.get("SENTRY_ORG", "sentinel-ha")
    token = os.environ.get("SENTRY_TOKEN", "")

    print("  Fetching Sentry project DSN...")
    resp = requests.get(
        f"https://sentry.io/api/0/organizations/{org}/projects/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  Warning: could not list Sentry projects ({resp.status_code}). Skipping Sentry seeding.")
        return

    projects = resp.json()
    if not projects:
        print("  Warning: no Sentry projects found. Skipping.")
        return

    project_slug = projects[0]["slug"]
    print(f"  Using project: {project_slug}")

    keys_resp = requests.get(
        f"https://sentry.io/api/0/projects/{org}/{project_slug}/keys/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if keys_resp.status_code != 200 or not keys_resp.json():
        print(f"  Warning: could not get DSN ({keys_resp.status_code}). Skipping Sentry seeding.")
        return

    dsn = keys_resp.json()[0]["dsn"]["public"]
    print(f"  Got DSN. Capturing 10 RateLimitError exceptions...")

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0)
    for i in range(10):
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("seeded_by", "sentinel-demo")
            try:
                raise Exception(f"RateLimitError: Too many requests to OpenAI API (attempt {i+1})")
            except Exception:
                sentry_sdk.capture_exception()
        time.sleep(0.5)

    print("  Sentry seeding complete.")


def seed_slack():
    messages = [
        "🚨 Seeing elevated API costs in the last hour — anyone know what changed?",
        "Looks like the retry logic is hammering the LLM endpoint after the last deploy",
        "checking Langfuse now — costs are 10x normal, trace_id runaway-agent spiking",
        "FYI pushed a fix: reverted max_tokens change from last commit, monitoring now",
    ]

    print(f"  Posting {len(messages)} Slack context messages to channel {SLACK_INCIDENTS_CHANNEL}...")
    for msg in messages:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            json={"channel": SLACK_INCIDENTS_CHANNEL, "text": msg},
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            print(f"  Warning: Slack post failed: {data.get('error')}")
        time.sleep(0.3)

    print("  Slack seeding complete.")


if __name__ == "__main__":
    print("\n=== Sentinel Demo Data Seeder ===\n")

    print("[1/4] Cleaning stale SQLite baselines...")
    clean_baselines()

    print("\n[2/4] Seeding Langfuse...")
    seed_langfuse()

    print("\n[3/4] Seeding Sentry...")
    seed_sentry()

    print("\n[4/4] Seeding Slack...")
    seed_slack()

    print("\n=== Seeding complete. Wait ~30s for Langfuse to process, then run oncall_brain. ===\n")
