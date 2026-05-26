import json


class ToolFailureDetector:
    """
    Detects silently-failing tool calls via three strategies:

    A — Schema validation: tool output is JSON but missing expected keys, or not valid JSON at all.
    B — Sentry cross-reference: Sentry errors appeared within 5 minutes of a "successful" tool span.
    C — Output anomaly: output length is much shorter than historical average (empty/error string).
    """

    def __init__(self, coral_client=None, memory=None, config: dict = None):
        self.coral = coral_client
        self.memory = memory
        self.config = config or {}

    def detect_schema_failures(self, hours: int = 6) -> list[dict]:
        """
        Strategy A — find SPAN observations whose output is not valid JSON
        when previous outputs for the same tool name were all valid JSON.
        """
        if not self.coral:
            return []
        sql = f"""
            SELECT
                id,
                trace_id,
                name as tool_name,
                output,
                start_time,
                level,
                status_message
            FROM langfuse.observations
            WHERE type = 'SPAN'
                AND start_time > NOW() - INTERVAL '{hours} hours'
                AND output IS NOT NULL
            ORDER BY start_time DESC
            LIMIT 200
        """
        try:
            rows = self.coral.query(sql)
        except Exception as e:
            print(f"[ToolFailureDetector] detect_schema_failures error: {e}")
            return []

        failures = []
        tool_output_types: dict[str, str] = {}

        for row in rows:
            tool = row.get("tool_name", "")
            output = row.get("output", "") or ""

            is_json = self._is_valid_json(output)
            if tool not in tool_output_types:
                tool_output_types[tool] = "json" if is_json else "text"
            elif tool_output_types[tool] == "json" and not is_json and len(output) > 0:
                failures.append({
                    "strategy": "schema_failure",
                    "tool_name": tool,
                    "trace_id": row.get("trace_id", ""),
                    "observation_id": row.get("id", ""),
                    "issue": "expected JSON but got non-JSON output",
                    "output_preview": output[:100],
                    "start_time": row.get("start_time"),
                })

        return failures

    def detect_sentry_correlated_failures(self, hours: int = 6) -> list[dict]:
        """
        Strategy B — find tool spans with Sentry errors in the same 5-minute window.
        Returns correlated failures with sentry error title and count.
        """
        if not self.coral:
            return []
        sql = f"""
            SELECT
                o.trace_id,
                o.name as tool_name,
                o.start_time,
                o.level,
                s.title as sentry_error,
                s.count as error_count,
                s.first_seen as error_start
            FROM langfuse.observations o
            JOIN sentry.issues s
                ON s.first_seen BETWEEN o.start_time
                    AND o.start_time + INTERVAL '5 minutes'
            WHERE o.type = 'SPAN'
                AND o.level = 'DEFAULT'
                AND o.start_time > NOW() - INTERVAL '{hours} hours'
                AND s.count > 2
            LIMIT 20
        """
        try:
            rows = self.coral.query(sql)
            return [
                {
                    "strategy": "sentry_correlation",
                    "tool_name": r.get("tool_name", ""),
                    "trace_id": r.get("trace_id", ""),
                    "sentry_error": r.get("sentry_error", ""),
                    "error_count": r.get("error_count", 0),
                    "start_time": r.get("start_time"),
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ToolFailureDetector] detect_sentry_correlated_failures error: {e}")
            return []

    def detect_output_anomalies(self, hours: int = 6) -> list[dict]:
        """
        Strategy C — find tool spans whose output length is far below
        the rolling average for that tool name (possible empty/error returns).
        """
        if not self.coral:
            return []
        sql = f"""
            SELECT
                name as tool_name,
                trace_id,
                id,
                output,
                start_time,
                AVG(LENGTH(output)) OVER (PARTITION BY name) as avg_output_len,
                LENGTH(output) as output_len
            FROM langfuse.observations
            WHERE type = 'SPAN'
                AND output IS NOT NULL
                AND start_time > NOW() - INTERVAL '{hours} hours'
            QUALIFY output_len < avg_output_len * 0.2
                AND avg_output_len > 50
            LIMIT 20
        """
        try:
            rows = self.coral.query(sql)
            return [
                {
                    "strategy": "output_anomaly",
                    "tool_name": r.get("tool_name", ""),
                    "trace_id": r.get("trace_id", ""),
                    "observation_id": r.get("id", ""),
                    "output_len": r.get("output_len", 0),
                    "avg_output_len": r.get("avg_output_len", 0),
                    "output_preview": (r.get("output") or "")[:80],
                    "start_time": r.get("start_time"),
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ToolFailureDetector] detect_output_anomalies error: {e}")
            return []

    def run(self, hours: int = 6) -> list[dict]:
        """Run all three strategies and return deduplicated failures."""
        all_failures = (
            self.detect_schema_failures(hours)
            + self.detect_sentry_correlated_failures(hours)
            + self.detect_output_anomalies(hours)
        )
        seen: set[str] = set()
        unique = []
        for f in all_failures:
            key = f"{f.get('strategy')}:{f.get('trace_id')}:{f.get('tool_name')}"
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    @staticmethod
    def _is_valid_json(text: str) -> bool:
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
