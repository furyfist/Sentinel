"""
Runs the commit-to-cost-blame Coral SQL query and prints a clean table.
Used during the demo to show cross-source JOINs live on camera.

Usage:
    python scripts/run_coral_blame.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from agent.config import GITHUB_OWNER, GITHUB_REPO
from agent import coral_client

SQL = f"""
SELECT
  g.sha,
  g.commit__message as commit_message,
  g.author__login as author,
  COUNT(DISTINCT s.id) as errors_after_commit,
  SUM(l.total_cost) as cost_after_commit
FROM github.commits g
LEFT JOIN sentry.issues s
  ON s.first_seen > CAST(g.commit__author__date AS TIMESTAMP)
  AND s.first_seen < CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
LEFT JOIN langfuse.observations l
  ON l.start_time > CAST(g.commit__author__date AS TIMESTAMP)
  AND l.start_time < CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
  AND l.type = 'GENERATION'
WHERE g.owner = '{GITHUB_OWNER}'
  AND g.repo = '{GITHUB_REPO}'
  AND CAST(g.commit__author__date AS TIMESTAMP) > NOW() - INTERVAL '7 days'
GROUP BY g.sha, g.commit__message, g.author__login
ORDER BY cost_after_commit DESC NULLS LAST
LIMIT 5
"""


FALLBACK_ROWS = [
    {"sha": "d9c3e11fa8b2", "commit_message": "feat: increase max_tokens in summariser pipeline", "author": "furyfist", "errors_after_commit": 0, "cost_after_commit": 4.2034},
    {"sha": "f1a8b33c9e41", "commit_message": "refactor: rewrite support-bot prompt to Q&A format", "author": "furyfist", "errors_after_commit": 2, "cost_after_commit": 0.0512},
    {"sha": "c7a2e81d3f90", "commit_message": "fix: retry-search exit condition after empty results", "author": "furyfist", "errors_after_commit": 1, "cost_after_commit": 0.2803},
    {"sha": "0267c5eb19ea", "commit_message": "fix: remove healthcheck and fix seed script import path", "author": "furyfist", "errors_after_commit": 0, "cost_after_commit": 0.0},
    {"sha": "61b76d3a9c12", "commit_message": "fix: run demo seed at import time to avoid blocking", "author": "furyfist", "errors_after_commit": 0, "cost_after_commit": 0.0},
]


def _print_table(rows):
    print(f"{'#':<3}  {'SHA':<12}  {'COST ($)':<10}  {'ERRORS':<7}  {'AUTHOR':<12}  COMMIT")
    print("-" * 90)
    for i, row in enumerate(rows, 1):
        sha     = str(row.get("sha", ""))[:12]
        cost    = row.get("cost_after_commit") or 0
        errors  = row.get("errors_after_commit") or 0
        author  = str(row.get("author", ""))[:12]
        message = str(row.get("commit_message", ""))[:50]
        print(f"{i:<3}  {sha:<12}  ${float(cost):<9.4f}  {int(errors):<7}  {author:<12}  {message}")
    print()
    print("Raw JSON:")
    print(json.dumps(rows, indent=2, default=str))


def run():
    print(f"\nRunning commit-to-cost blame query ({GITHUB_OWNER}/{GITHUB_REPO})...\n")

    try:
        rows = coral_client.query(SQL, timeout=60)
    except Exception as e:
        print(f"[warn] Coral live query failed ({e}), using seeded demo data.\n")
        rows = FALLBACK_ROWS

    if not rows:
        print("No results. Make sure Langfuse and GitHub sources are registered in Coral.")
        return

    _print_table(rows)


if __name__ == "__main__":
    run()
