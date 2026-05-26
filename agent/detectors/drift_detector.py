import json
from agent.config import GITHUB_OWNER, GITHUB_REPO

DRIFT_FAIL_RATE_THRESHOLD = 0.15
SCORE_REGRESSION_DELTA = 0.1


class DriftDetector:
    """
    Two detection strategies:

    Strategy A — Schema Contract Testing:
      Maintain a JSON schema snapshot per feature (observation name).
      Validate recent outputs against the snapshot.
      If fail rate > DRIFT_FAIL_RATE_THRESHOLD → drift detected.

    Strategy B — Output Score Regression:
      If Langfuse scores exist, compare last-24h average vs 7-day baseline.
      If delta > SCORE_REGRESSION_DELTA → regression flagged.
    """

    def __init__(self, coral_client=None, memory=None, config: dict = None):
        self.coral = coral_client
        self.memory = memory
        self.config = config or {}
        self.fail_rate_threshold = config.get("drift_fail_rate_threshold", DRIFT_FAIL_RATE_THRESHOLD) if config else DRIFT_FAIL_RATE_THRESHOLD

    def get_recent_feature_names(self, hours: int = 24) -> list[str]:
        """Return distinct observation names (features) seen in the last N hours."""
        if not self.coral:
            return []
        sql = f"""
            SELECT DISTINCT name
            FROM langfuse.observations
            WHERE type = 'GENERATION'
                AND start_time > NOW() - INTERVAL '{hours} hours'
            ORDER BY name
            LIMIT 50
        """
        try:
            rows = self.coral.query(sql)
            return [r["name"] for r in rows if r.get("name")]
        except Exception as e:
            print(f"[DriftDetector] get_recent_feature_names error: {e}")
            return []

    def get_recent_outputs(self, feature_name: str, limit: int = 20) -> list[dict]:
        """Pull the latest N observations for a feature, returning output text."""
        if not self.coral:
            return []
        safe_name = feature_name.replace("'", "''")
        sql = f"""
            SELECT id, trace_id, output, start_time
            FROM langfuse.observations
            WHERE name = '{safe_name}'
                AND type = 'GENERATION'
                AND start_time > NOW() - INTERVAL '24 hours'
            ORDER BY start_time DESC
            LIMIT {limit}
        """
        try:
            return self.coral.query(sql)
        except Exception as e:
            print(f"[DriftDetector] get_recent_outputs error: {e}")
            return []

    def check_score_regression(self, feature_name: str) -> dict | None:
        """
        Strategy B: compare last-24h avg score vs 7-day baseline.
        Returns regression info if delta > threshold, else None.
        """
        if not self.coral:
            return None
        safe_name = feature_name.replace("'", "''")
        sql = f"""
            SELECT
                AVG(CASE WHEN s.timestamp > NOW() - INTERVAL '24 hours' THEN s.value END) as recent_avg,
                AVG(CASE WHEN s.timestamp BETWEEN NOW() - INTERVAL '7 days' AND NOW() - INTERVAL '24 hours' THEN s.value END) as baseline_avg
            FROM langfuse.scores s
            JOIN langfuse.observations o ON o.trace_id = s.trace_id
            WHERE o.name = '{safe_name}'
        """
        try:
            rows = self.coral.query(sql)
            if not rows or rows[0].get("recent_avg") is None or rows[0].get("baseline_avg") is None:
                return None
            recent = float(rows[0]["recent_avg"])
            baseline = float(rows[0]["baseline_avg"])
            delta = baseline - recent
            if delta > self.config.get("score_regression_delta", SCORE_REGRESSION_DELTA):
                return {"recent_avg": recent, "baseline_avg": baseline, "delta": delta}
        except Exception:
            pass
        return None
