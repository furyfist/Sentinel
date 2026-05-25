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
