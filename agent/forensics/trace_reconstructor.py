class TraceReconstructor:
    """
    Pulls all observations for a Langfuse trace and builds a React Flow
    node/edge graph ready to be sent to the frontend.
    """

    def __init__(self, coral_client):
        self.coral = coral_client

    def reconstruct_trace(self, trace_id: str) -> dict:
        safe_id = trace_id.replace("'", "")
        sql = f"""
            SELECT
                id,
                trace_id,
                name,
                type,
                model,
                start_time,
                end_time,
                total_cost,
                input_tokens,
                output_tokens,
                level,
                status_message
            FROM langfuse.observations
            WHERE trace_id = '{safe_id}'
            ORDER BY start_time ASC
        """
        try:
            observations = self.coral.query(sql, timeout=60)
        except Exception as e:
            return {"nodes": [], "edges": [], "error": str(e)}

        if not observations:
            return {"nodes": [], "edges": [], "trace_id": trace_id}

        nodes = []
        edges = []

        for obs in observations:
            obs_type = obs.get("type", "")
            if obs_type == "GENERATION":
                node_type = "generation"
            elif obs_type == "SPAN":
                node_type = "span"
            else:
                node_type = "event"

            prompt_tokens = obs.get("input_tokens") or 0
            completion_tokens = obs.get("output_tokens") or 0
            level = obs.get("level", "DEFAULT")
            is_error = level in ("ERROR", "WARNING")

            nodes.append({
                "id": obs["id"],
                "type": node_type,
                "data": {
                    "label": obs.get("name", obs["id"][:8]),
                    "model": obs.get("model", ""),
                    "cost": float(obs.get("total_cost") or 0),
                    "tokens": int(prompt_tokens) + int(completion_tokens),
                    "status": level,
                    "is_error": is_error,
                },
                "position": {"x": 0, "y": 0},
            })

        for i in range(1, len(nodes)):
            src = nodes[i - 1]["id"]
            tgt = nodes[i]["id"]
            is_err = nodes[i]["data"]["is_error"]
            edges.append({
                "id": f"e-{src}-{tgt}",
                "source": src,
                "target": tgt,
                "animated": is_err,
                "style": {"stroke": "#ef4444"} if is_err else {},
            })

        total_cost = sum(float(o.get("total_cost") or 0) for o in observations)
        error_count = sum(1 for o in observations if o.get("level") in ("ERROR", "WARNING"))

        return {
            "trace_id": trace_id,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_observations": len(observations),
                "total_cost": total_cost,
                "error_count": error_count,
            },
        }

    def get_worst_traces(self, limit: int = 10) -> list[dict]:
        """Return the most expensive traces by total cost."""
        sql = f"""
            SELECT
                trace_id,
                COUNT(*) as observation_count,
                SUM(total_cost) as total_cost,
                MIN(start_time) as started_at,
                SUM(CASE WHEN level IN ('ERROR', 'WARNING') THEN 1 ELSE 0 END) as error_count
            FROM langfuse.observations
            WHERE start_time > NOW() - INTERVAL '7 days'
            GROUP BY trace_id
            ORDER BY total_cost DESC NULLS LAST
            LIMIT {limit}
        """
        try:
            return self.coral.query(sql, timeout=120)
        except Exception as e:
            print(f"[TraceReconstructor] get_worst_traces error: {e}")
            return []
