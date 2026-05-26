"""Routes anomalies through approval gate — auto-act on obvious threats, queue the rest."""
from datetime import datetime
from agent.anomaly_detector import AnomalyResult
from agent.config import SLACK_INCIDENTS_CHANNEL


class ApprovalGate:
    def __init__(self, memory=None, channel: str = None):
        self.memory = memory
        self.channel = channel or SLACK_INCIDENTS_CHANNEL

    def should_auto_act(self, anomaly: AnomalyResult) -> bool:
        if anomaly.type == "loop_detected" and anomaly.metadata.get("gen_count", 0) > 20:
            return True
        if anomaly.type == "cost_spike" and anomaly.metadata.get("current_cost", 0) > 10.0:
            return True
        return False

    def execute_action(self, anomaly: AnomalyResult):
        """Immediately execute the suggested action without human approval."""
        from agent.actions import slack_poster
        action = anomaly.suggested_action
        if action == "kill_loop":
            trace_id = anomaly.metadata.get("trace_id", "")
            if self.memory and trace_id:
                self.memory.update_loop_detection(trace_id, status="killed", kill_method="auto")
            slack_poster.post_to_slack(
                self.channel,
                f"🤖 Auto-killed loop on trace `{trace_id}` — {anomaly.description}",
            )
        else:
            slack_poster.post_to_slack(
                self.channel,
                f"⚡ Auto-action `{action}` executed — {anomaly.description}",
            )

    def create_approval_request(self, anomaly: AnomalyResult) -> int:
        """Save approval record and return its ID."""
        if not self.memory:
            return -1
        context_summary = anomaly.description[:500]
        approval_id = self.memory.save_approval(
            action_type=anomaly.suggested_action or "review",
            anomaly_type=anomaly.type,
            severity=anomaly.severity,
            context={"summary": context_summary, "severity": anomaly.severity, **anomaly.metadata},
            expires_hours=4,
        )
        return approval_id

    def post_approval_to_slack(self, approval_id: int, anomaly: AnomalyResult):
        if approval_id < 0:
            return
        from agent.actions import slack_poster
        try:
            ts = slack_poster.post_approval_request(
                channel=self.channel,
                approval_id=approval_id,
                action_type=anomaly.suggested_action or "review",
                context={
                    "summary": anomaly.description,
                    "severity": anomaly.severity,
                },
            )
            if self.memory:
                self.memory.update_approval(approval_id, slack_ts=ts)
        except Exception:
            pass

    def notify_slack(self, anomaly: AnomalyResult, auto: bool = False):
        from agent.actions import slack_poster
        prefix = "🤖 Auto-acted" if auto else "ℹ️ Sentinel"
        try:
            slack_poster.post_to_slack(
                self.channel,
                f"{prefix}: {anomaly.description}",
            )
        except Exception:
            pass

    def expire_stale_approvals(self):
        """Mark expired pending approvals and update their Slack messages."""
        if not self.memory:
            return
        stale = self.memory.get_expired_approvals()
        for approval in stale:
            self.memory.update_approval(approval["id"], status="expired")
            slack_ts = approval.get("slack_ts")
            slack_channel = approval.get("slack_channel") or self.channel
            if slack_ts and slack_channel:
                try:
                    from agent.actions import slack_poster
                    import requests
                    from agent.config import SLACK_BOT_TOKEN
                    requests.post(
                        "https://slack.com/api/chat.update",
                        json={
                            "channel": slack_channel,
                            "ts": slack_ts,
                            "text": "⏰ Approval expired (no action taken)",
                            "blocks": [],
                        },
                        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                        timeout=5,
                    )
                except Exception:
                    pass

    def route(self, anomaly: AnomalyResult):
        if self.should_auto_act(anomaly):
            self.execute_action(anomaly)
        else:
            approval_id = self.create_approval_request(anomaly)
            self.post_approval_to_slack(approval_id, anomaly)
