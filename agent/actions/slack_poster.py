import requests
from agent.config import SLACK_BOT_TOKEN


def post_to_slack(channel: str, text: str, blocks: list = None) -> str:
    payload = {"channel": channel, "text": text}
    if blocks:
        payload["blocks"] = blocks

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        json=payload,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack post failed: {data.get('error', 'unknown error')}")
    return data["ts"]


def post_approval_request(channel: str, approval_id: int, action_type: str, context: dict) -> str:
    """Post an interactive Slack message with Approve/Reject buttons."""
    summary = context.get("summary", "")
    severity = context.get("severity", "unknown")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Sentinel needs approval*\nAction: `{action_type}` | Severity: `{severity}`\n{summary}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "action_id": f"sentinel_approve_{approval_id}",
                    "value": str(approval_id),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "action_id": f"sentinel_reject_{approval_id}",
                    "value": str(approval_id),
                },
            ],
        },
    ]

    return post_to_slack(channel, f"Sentinel approval request: {action_type}", blocks)


def post_loop_alert(channel: str, trace_id: str, gen_count: int, cost: float, tool_pattern: str) -> str:
    """Post a loop detection alert with a Kill/Ignore button."""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Agent Loop Detected*\n"
                    f"Trace: `{trace_id}`\n"
                    f"Generations: `{gen_count}` | Cost burned: `${cost:.4f}`\n"
                    f"Pattern: `{tool_pattern}`"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Kill Loop"},
                    "style": "danger",
                    "action_id": f"sentinel_kill_loop_{trace_id}",
                    "value": trace_id,
                },
            ],
        },
    ]

    return post_to_slack(channel, f"Agent loop detected on trace {trace_id}", blocks)
