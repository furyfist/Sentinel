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
