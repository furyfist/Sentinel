from collections import Counter
from agent.config import AGENT_LOOP_GENERATION_THRESHOLD


class LoopDetector:
    def __init__(self, coral_client, memory=None, config: dict = None):
        self.coral = coral_client
        self.memory = memory
        self.config = config or {}

    def detect_loops(self) -> list[dict]:
        """
        Find traces with abnormally high generation counts in the last 2 hours.
        A loop looks like: same trace_id with 8+ GENERATIONs in a short window.
        """
        threshold = self.config.get("loop_gen_threshold", AGENT_LOOP_GENERATION_THRESHOLD)
        sql = f"""
            SELECT
                trace_id,
                COUNT(*) as gen_count,
                MIN(start_time) as first_gen,
                MAX(start_time) as last_gen,
                SUM(total_cost) as total_cost,
                COUNT(DISTINCT name) as unique_names
            FROM langfuse.observations
            WHERE type = 'GENERATION'
                AND start_time > NOW() - INTERVAL '2 hours'
            GROUP BY trace_id
            HAVING COUNT(*) > {threshold}
            ORDER BY gen_count DESC
            LIMIT 20
        """
        try:
            return self.coral.query(sql)
        except Exception as e:
            print(f"[LoopDetector] detect_loops error: {e}")
            return []

    def fingerprint_loop(self, trace_id: str) -> dict:
        """
        Pull full observation chain for a trace and compute loop fingerprint:
        - name_histogram: how many times each observation name appears
        - most_repeated_name / repeat_count: the dominant repeated call
        - cost_velocity: cost per minute during the loop window
        """
        sql = f"""
            SELECT name, start_time, total_cost, model
            FROM langfuse.observations
            WHERE trace_id = '{trace_id}'
            ORDER BY start_time ASC
        """
        try:
            observations = self.coral.query(sql)
        except Exception as e:
            return {"error": str(e), "trace_id": trace_id}

        if not observations:
            return {"trace_id": trace_id, "gen_count": 0}

        name_counts = Counter(o.get("name", "unknown") for o in observations)
        most_repeated, repeat_count = name_counts.most_common(1)[0]

        total_cost = sum(float(o.get("total_cost") or 0) for o in observations)

        cost_velocity = 0.0
        if len(observations) >= 2:
            first = observations[0].get("start_time")
            last = observations[-1].get("start_time")
            if first and last:
                try:
                    from datetime import datetime
                    if isinstance(first, str):
                        first = datetime.fromisoformat(first.replace("Z", "+00:00"))
                    if isinstance(last, str):
                        last = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    span_minutes = (last - first).total_seconds() / 60
                    cost_velocity = total_cost / max(span_minutes, 0.1)
                except Exception:
                    pass

        return {
            "trace_id": trace_id,
            "gen_count": len(observations),
            "name_histogram": dict(name_counts),
            "most_repeated_name": most_repeated,
            "repeat_count": repeat_count,
            "total_cost": total_cost,
            "cost_velocity_per_min": round(cost_velocity, 6),
        }

    def fire_loop_alert(self, loop: dict, channel: str) -> str | None:
        """
        Save loop to SQLite and post a Slack alert with a Kill Loop button.
        Returns the Slack message ts, or None if Slack is unavailable.
        """
        from agent.actions.slack_poster import post_loop_alert
        trace_id = loop.get("trace_id", "unknown")
        gen_count = int(loop.get("gen_count", 0))
        cost = float(loop.get("total_cost") or 0)
        fp = self.fingerprint_loop(trace_id)
        tool_pattern = fp.get("most_repeated_name", "unknown")

        slack_ts = None
        try:
            slack_ts = post_loop_alert(
                channel=channel,
                trace_id=trace_id,
                gen_count=gen_count,
                cost=cost,
                tool_pattern=f"{tool_pattern} x{fp.get('repeat_count', gen_count)}",
            )
        except Exception as e:
            print(f"[LoopDetector] Slack alert failed: {e}")

        if self.memory:
            import json
            self.memory.save_loop_detection(
                trace_id=trace_id,
                loop_count=gen_count,
                cost_burned=cost,
                tool_pattern=json.dumps(fp.get("name_histogram", {})),
                slack_ts=slack_ts,
            )

        return slack_ts

    def run(self, channel: str) -> list[dict]:
        """Detect all loops and fire alerts. Returns list of loops found."""
        loops = self.detect_loops()
        for loop in loops:
            self.fire_loop_alert(loop, channel)
        return loops
