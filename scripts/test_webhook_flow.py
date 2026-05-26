"""
Test the Slack webhook flow end-to-end.

Steps to run manually:
  1. Start the API:   uvicorn api.main:app --reload --port 8000
  2. Expose via ngrok: ngrok http 8000
  3. Set Slack Interactivity URL: https://<ngrok>.ngrok.io/api/slack/actions
  4. Run this script: python scripts/test_webhook_flow.py

This script:
  - Creates a test approval in SQLite
  - Posts an interactive Slack message with Approve/Reject buttons
  - Prints the SQLite row so you can verify state after clicking a button
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import memory
from agent.config import SLACK_INCIDENTS_CHANNEL
from agent.actions.slack_poster import post_approval_request, post_loop_alert


def test_approval_flow():
    print("Creating test approval in SQLite...")
    approval_id = memory.save_approval(
        action_type="create_issue",
        context={
            "summary": "Cost spike detected: $4.50/hr vs $1.20/hr baseline (3.75x)",
            "severity": "high",
            "trace_id": "test-trace-001",
        },
        slack_channel=SLACK_INCIDENTS_CHANNEL,
    )
    print(f"Approval created: id={approval_id}")

    print(f"\nPosting approval request to Slack channel {SLACK_INCIDENTS_CHANNEL}...")
    ts = post_approval_request(
        channel=SLACK_INCIDENTS_CHANNEL,
        approval_id=approval_id,
        action_type="create_issue",
        context={
            "summary": "Cost spike detected: $4.50/hr vs $1.20/hr baseline (3.75x)",
            "severity": "high",
        },
    )
    print(f"Message posted, ts={ts}")

    memory.update_approval(approval_id, status="pending", resolved_by=None)
    # Update slack_ts for reference
    with memory.get_connection() as conn:
        conn.execute("UPDATE approval_queue SET slack_ts = ? WHERE id = ?", (ts, approval_id))

    print("\nApproval in SQLite:")
    approval = memory.get_approval(approval_id)
    print(f"  id={approval['id']} status={approval['status']} action={approval['action_type']}")
    print("\nClick Approve or Reject in Slack, then re-check with:")
    print(f"  python -c \"from agent import memory; print(memory.get_approval({approval_id}))\"")


def test_loop_alert():
    print("\nPosting loop alert to Slack...")
    ts = post_loop_alert(
        channel=SLACK_INCIDENTS_CHANNEL,
        trace_id="test-loop-trace-001",
        gen_count=15,
        cost=0.0342,
        tool_pattern="retry-search x15",
    )
    print(f"Loop alert posted, ts={ts}")

    loop_id = memory.save_loop_detection(
        trace_id="test-loop-trace-001",
        loop_count=15,
        cost_burned=0.0342,
        tool_pattern="retry-search x15",
        slack_ts=ts,
    )
    print(f"Loop detection saved: id={loop_id}")
    print("Click 'Kill Loop' in Slack, then verify:")
    print("  python -c \"from agent import memory; print(memory.get_loop_detections())\"")


if __name__ == "__main__":
    test_approval_flow()
    test_loop_alert()
