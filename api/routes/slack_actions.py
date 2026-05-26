import json
import urllib.parse
import requests
from fastapi import APIRouter, Request, Response
from agent.config import SLACK_SIGNING_SECRET, SLACK_BOT_TOKEN
from agent import memory
from api.middleware.slack_verify import verify_slack_signature

router = APIRouter()


@router.post("/actions")
async def handle_slack_action(request: Request):
    """
    Single endpoint for all Slack interactive payloads.
    Slack sends application/x-www-form-urlencoded with a 'payload' JSON field.
    Must respond within 3 seconds.
    """
    if SLACK_SIGNING_SECRET:
        await verify_slack_signature(request, SLACK_SIGNING_SECRET)

    body = await request.body()
    parsed = urllib.parse.parse_qs(body.decode("utf-8"))
    payload_raw = parsed.get("payload", ["{}"])[0]
    payload = json.loads(payload_raw)

    actions = payload.get("actions", [])
    response_url = payload.get("response_url", "")
    user_id = payload.get("user", {}).get("id", "unknown")

    for action in actions:
        action_id = action.get("action_id", "")

        if action_id.startswith("sentinel_approve_"):
            approval_id = int(action_id.split("_")[-1])
            _handle_approve(approval_id, user_id, response_url)

        elif action_id.startswith("sentinel_reject_"):
            approval_id = int(action_id.split("_")[-1])
            _handle_reject(approval_id, user_id, response_url)

        elif action_id.startswith("sentinel_kill_loop_"):
            trace_id = action_id.replace("sentinel_kill_loop_", "")
            _handle_kill_loop(trace_id, user_id, response_url)

    return Response(content="", status_code=200)


def _handle_approve(approval_id: int, user_id: str, response_url: str):
    approval = memory.get_approval(approval_id)
    if not approval:
        return

    _execute_approved_action(approval)
    memory.update_approval(approval_id, status="approved", resolved_by=user_id)
    _update_slack_message(response_url, f"✅ Approved by <@{user_id}>")


def _execute_approved_action(approval: dict):
    action_type = approval.get("action_type", "")
    context = approval.get("context", {}) if isinstance(approval.get("context"), dict) else {}

    try:
        if action_type == "kill_loop":
            trace_id = context.get("trace_id", "")
            if trace_id:
                memory.update_loop_detection(trace_id, status="killed", kill_method="slack_approval")

        elif action_type in ("create_issue", "review"):
            from agent.actions import github_issue_creator
            summary = context.get("summary", "Sentinel anomaly detected")
            anomaly_type = approval.get("anomaly_type", "unknown")
            severity = approval.get("severity", "unknown")
            github_issue_creator.create_incident_issue(
                title=f"[Sentinel] {anomaly_type} — severity: {severity}",
                body=f"**Approved via Slack**\n\n{summary}",
            )

        elif action_type == "request_changes":
            pass

    except Exception:
        pass


def _handle_reject(approval_id: int, user_id: str, response_url: str):
    approval = memory.get_approval(approval_id)
    if not approval:
        return

    memory.update_approval(approval_id, status="rejected", resolved_by=user_id)
    _update_slack_message(response_url, f"❌ Rejected by <@{user_id}>")


def _handle_kill_loop(trace_id: str, user_id: str, response_url: str):
    memory.update_loop_detection(trace_id, status="killed", kill_method="slack_button")
    _update_slack_message(response_url, f"🛑 Loop kill acknowledged by <@{user_id}>")


def _update_slack_message(response_url: str, text: str):
    if not response_url:
        return
    try:
        requests.post(
            response_url,
            json={"text": text, "replace_original": True},
            timeout=5,
        )
    except Exception:
        pass
