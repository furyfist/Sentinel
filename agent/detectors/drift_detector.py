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
            rows = self.coral.query(sql, timeout=120)
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
            return self.coral.query(sql, timeout=120)
        except Exception as e:
            print(f"[DriftDetector] get_recent_outputs error: {e}")
            return []

    def _infer_schema(self, parsed) -> dict:
        """Recursively extract key→type map from a parsed JSON value."""
        if isinstance(parsed, dict):
            return {k: self._infer_schema(v) for k, v in parsed.items()}
        elif isinstance(parsed, list):
            return {"_type": "array", "_item": self._infer_schema(parsed[0]) if parsed else "unknown"}
        else:
            return type(parsed).__name__

    def _merge_schemas(self, schemas: list[dict]) -> dict:
        """Produce the union of keys seen across multiple schema samples."""
        if not schemas:
            return {}
        merged = {}
        for schema in schemas:
            if isinstance(schema, dict):
                for k, v in schema.items():
                    if k not in merged:
                        merged[k] = v
        return merged

    def capture_schema_snapshot(self, feature_name: str, sample_outputs: list[str]) -> dict:
        """
        Analyze N sample outputs for a feature, derive a JSON schema, and store it.
        If outputs are JSON → infer key-type map.
        If outputs are plain text → store {"type": "text"}.
        """
        schemas = []
        for output in sample_outputs:
            if not output:
                continue
            try:
                parsed = json.loads(output)
                schemas.append(self._infer_schema(parsed))
            except (json.JSONDecodeError, TypeError):
                schemas.append({"_type": "text"})

        consensus = self._merge_schemas(schemas) if schemas else {"_type": "text"}

        if self.memory:
            self.memory.save_schema_snapshot(feature_name, consensus, sample_count=len(sample_outputs))

        return consensus

    def _validate_against_schema(self, output: str, snapshot: dict) -> bool:
        """
        Returns True if the output conforms to the stored schema.
        For JSON outputs: checks that all expected top-level keys are present.
        For text outputs: passes if non-empty.
        """
        if not output:
            return False

        if snapshot.get("_type") == "text":
            return len(output.strip()) > 0

        try:
            parsed = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return False

        if not isinstance(parsed, dict):
            return True

        expected_keys = {k for k in snapshot.keys() if not k.startswith("_")}
        actual_keys = set(parsed.keys())
        return expected_keys.issubset(actual_keys)

    def _describe_mismatch(self, output: str, snapshot: dict) -> str:
        """Human-readable description of what's wrong with this output."""
        try:
            parsed = json.loads(output)
            expected = {k for k in snapshot.keys() if not k.startswith("_")}
            actual = set(parsed.keys()) if isinstance(parsed, dict) else set()
            missing = expected - actual
            extra = actual - expected
            parts = []
            if missing:
                parts.append(f"missing keys: {sorted(missing)}")
            if extra:
                parts.append(f"extra keys: {sorted(extra)}")
            return "; ".join(parts) or "structure mismatch"
        except Exception:
            return "not valid JSON"

    def validate_observations(self, feature_name: str, observations: list[dict]) -> dict:
        """
        Validate each observation's output against the stored schema snapshot.
        Returns summary with total, passed, failed, fail_rate, and failures list.
        """
        if not self.memory:
            return {"status": "no_memory"}

        snapshot_row = self.memory.get_schema_snapshot(feature_name)
        if not snapshot_row:
            return {"status": "no_snapshot", "feature": feature_name}

        snapshot = snapshot_row["schema_json"]
        passed, failed, failures = 0, 0, []

        for obs in observations:
            output = obs.get("output", "") or ""
            if self._validate_against_schema(output, snapshot):
                passed += 1
            else:
                failed += 1
                failures.append({
                    "observation_id": obs.get("id", ""),
                    "trace_id": obs.get("trace_id", ""),
                    "mismatch": self._describe_mismatch(output, snapshot),
                })

        total = passed + failed
        return {
            "feature": feature_name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "fail_rate": round(failed / total, 4) if total else 0.0,
            "failures": failures[:10],
        }

    def blame_commit(
        self,
        drift_start: str,
        owner: str = GITHUB_OWNER,
        repo: str = GITHUB_REPO,
    ) -> dict | None:
        """
        Find the most recent commit that touched prompt-related files
        in the 48 hours before the drift was first detected.
        Returns the closest commit dict, or None if none found.
        """
        if not self.coral:
            return None
        safe_start = str(drift_start).replace("'", "")
        sql = f"""
            SELECT
                sha,
                commit__message as message,
                author__login as author,
                commit__author__date as committed_date
            FROM github.commits
            WHERE owner = '{owner}'
                AND repo = '{repo}'
                AND CAST(commit__author__date AS TIMESTAMP) BETWEEN
                    CAST('{safe_start}' AS TIMESTAMP) - INTERVAL '48 hours'
                    AND CAST('{safe_start}' AS TIMESTAMP)
                AND (
                    commit__message ILIKE '%prompt%'
                    OR commit__message ILIKE '%system%'
                    OR commit__message ILIKE '%template%'
                    OR commit__message ILIKE '%llm%'
                    OR commit__message ILIKE '%model%'
                )
            ORDER BY commit__author__date DESC
            LIMIT 5
        """
        try:
            rows = self.coral.query(sql)
            return rows[0] if rows else None
        except Exception as e:
            print(f"[DriftDetector] blame_commit error: {e}")
            return None

    def detect(self, feature_name: str) -> dict | None:
        """
        Run both strategies for a single feature.
        Returns a drift event dict if drift detected, else None.
        """
        observations = self.get_recent_outputs(feature_name, limit=20)
        if not observations:
            return None

        if not self.memory or not self.memory.get_schema_snapshot(feature_name):
            outputs = [o.get("output", "") or "" for o in observations]
            self.capture_schema_snapshot(feature_name, outputs)
            return None

        validation = self.validate_observations(feature_name, observations)
        fail_rate = validation.get("fail_rate", 0.0)

        if fail_rate < self.fail_rate_threshold:
            score_reg = self.check_score_regression(feature_name)
            if not score_reg:
                return None
            drift_type = "score_regression"
            severity = "medium"
            details = score_reg
        else:
            drift_type = "schema_break"
            severity = "high" if fail_rate > 0.5 else "medium"
            details = validation

        drift_start = str(observations[0].get("start_time", ""))
        blame = self.blame_commit(drift_start)

        return {
            "feature_name": feature_name,
            "drift_type": drift_type,
            "severity": severity,
            "validation_fail_rate": fail_rate,
            "details": details,
            "blame_commit_sha": blame.get("sha") if blame else None,
            "blame_commit_message": blame.get("message") if blame else None,
        }

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
