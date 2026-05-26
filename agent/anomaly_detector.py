from dataclasses import dataclass, field
from datetime import datetime
from agent.config import COST_SPIKE_MULTIPLIER, AGENT_LOOP_GENERATION_THRESHOLD


@dataclass
class AnomalyResult:
    type: str
    severity: str
    detected_at: datetime
    description: str
    metadata: dict = field(default_factory=dict)
    requires_approval: bool = True
    suggested_action: str = ""


class AnomalyDetector:
    def __init__(self, coral_client=None, memory=None, config: dict = None):
        self.coral = coral_client
        self.memory = memory
        self.config = config or {}

    def detect_agent_loop(self) -> AnomalyResult | None:
        """Detect traces with excessive generation counts indicating a loop."""
        if not self.coral:
            return None
        try:
            results = self.coral.query("""
                SELECT
                    traceId,
                    COUNT(*) as gen_count,
                    SUM(calculatedTotalCost) as total_cost
                FROM langfuse.observations
                WHERE type = 'GENERATION'
                    AND startTime > NOW() - INTERVAL '2 hours'
                GROUP BY traceId
                HAVING COUNT(*) > 8
                ORDER BY gen_count DESC
                LIMIT 1
            """)
            if not results:
                return None

            row = results[0]
            gen_count = row.get("gen_count", 0)
            cost = float(row.get("total_cost") or 0)
            trace_id = row.get("traceId", "")
            threshold = self.config.get("loop_gen_threshold", AGENT_LOOP_GENERATION_THRESHOLD)

            if gen_count <= threshold:
                return None

            severity = "critical" if gen_count > 20 else "high"
            return AnomalyResult(
                type="loop_detected",
                severity=severity,
                detected_at=datetime.utcnow(),
                description=f"Agent loop: {gen_count} generations on trace {trace_id}, cost ${cost:.4f}",
                metadata={"trace_id": trace_id, "gen_count": gen_count, "cost": cost},
                requires_approval=gen_count <= 20,
                suggested_action="kill_loop",
            )
        except Exception:
            return None

    def detect_prompt_drift(self) -> AnomalyResult | None:
        """Stub — implemented fully in drift_detector.py (Phase 3)."""
        return None

    def detect_silent_tool_failure(self) -> AnomalyResult | None:
        """Stub — implemented fully in tool_failure_detector.py (Phase 4)."""
        return None

    def detect_cost_spike(self) -> AnomalyResult | None:
        """Detect when current hourly cost exceeds the rolling baseline."""
        if not self.memory:
            return None
        try:
            baselines = self.memory.get_baselines(limit=168)
            if not baselines:
                return None

            avg = sum(b["hourly_cost"] for b in baselines) / len(baselines)
            latest = baselines[0]["hourly_cost"]
            multiplier = self.config.get("cost_spike_multiplier", COST_SPIKE_MULTIPLIER)

            if latest <= avg * multiplier:
                return None

            ratio = latest / avg if avg > 0 else 0
            severity = "critical" if ratio > 5 else "high"
            return AnomalyResult(
                type="cost_spike",
                severity=severity,
                detected_at=datetime.utcnow(),
                description=f"Cost spike: ${latest:.4f}/hr vs ${avg:.4f}/hr baseline ({ratio:.1f}x)",
                metadata={"current_cost": latest, "baseline_avg": avg, "ratio": ratio},
                requires_approval=latest < 10.0,
                suggested_action="kill_loop" if latest >= 10.0 else "create_issue",
            )
        except Exception:
            return None

    def run_all(self) -> list[AnomalyResult]:
        """Run all detectors and return found anomalies."""
        detectors = [
            self.detect_agent_loop,
            self.detect_prompt_drift,
            self.detect_silent_tool_failure,
            self.detect_cost_spike,
        ]
        results = []
        for detector in detectors:
            result = detector()
            if result:
                results.append(result)
        return results
