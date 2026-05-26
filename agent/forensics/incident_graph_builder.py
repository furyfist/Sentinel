from agent.config import GITHUB_OWNER, GITHUB_REPO


class IncidentGraphBuilder:
    """
    Builds a cross-source causal graph for a time window.
    Node types: commit, error, trace, message
    Edges: commit → error (caused_by), error → trace (triggered), commit → trace (preceded)
    """

    def __init__(self, coral_client, config: dict = None):
        self.coral = coral_client
        self.config = config or {}

    def _query(self, sql: str) -> list[dict]:
        try:
            return self.coral.query(sql)
        except Exception as e:
            print(f"[IncidentGraphBuilder] query error: {e}")
            return []

    def _fetch_commits(self, start: str, end: str, owner: str, repo: str) -> list[dict]:
        sql = f"""
            SELECT sha, commit__message as message, author__login as author, commit__author__date as committed_date
            FROM github.commits
            WHERE owner = '{owner}' AND repo = '{repo}'
                AND CAST(commit__author__date AS TIMESTAMP) BETWEEN CAST('{start}' AS TIMESTAMP) AND CAST('{end}' AS TIMESTAMP)
            ORDER BY committed_date DESC
            LIMIT 15
        """
        return self._query(sql)

    def _fetch_errors(self, start: str, end: str) -> list[dict]:
        sql = f"""
            SELECT id, title, count, first_seen, last_seen
            FROM sentry.issues
            WHERE first_seen BETWEEN CAST('{start}' AS TIMESTAMP) AND CAST('{end}' AS TIMESTAMP)
            ORDER BY count DESC
            LIMIT 15
        """
        return self._query(sql)

    def _fetch_traces(self, start: str, end: str) -> list[dict]:
        sql = f"""
            SELECT trace_id, SUM(total_cost) as total_cost, COUNT(*) as gen_count, MIN(start_time) as started_at
            FROM langfuse.observations
            WHERE type = 'GENERATION'
                AND start_time BETWEEN CAST('{start}' AS TIMESTAMP) AND CAST('{end}' AS TIMESTAMP)
            GROUP BY trace_id
            ORDER BY total_cost DESC NULLS LAST
            LIMIT 10
        """
        return self._query(sql)

    def _fetch_messages(self, start: str, end: str) -> list[dict]:
        sql = f"""
            SELECT m.text, m.ts as posted_at, c.name as channel_name
            FROM slack.messages m
            JOIN slack.channels c ON c.id = m.channel
            WHERE m.ts BETWEEN '{start}' AND '{end}'
                AND c.name IN ('incidents', 'engineering', 'alerts', 'backend')
            ORDER BY m.ts ASC
            LIMIT 10
        """
        try:
            return self.coral.query(sql)
        except Exception:
            return []

    @staticmethod
    def _find_closest_prior(commits: list[dict], target_time) -> dict | None:
        """Return the most recent commit that happened before target_time."""
        target_str = str(target_time)
        candidates = [c for c in commits if str(c.get("committed_date", "")) < target_str]
        return candidates[0] if candidates else (commits[0] if commits else None)

    def build_incident_graph(
        self,
        window_start: str,
        window_end: str,
        owner: str = GITHUB_OWNER,
        repo: str = GITHUB_REPO,
    ) -> dict:
        commits = self._fetch_commits(window_start, window_end, owner, repo)
        errors = self._fetch_errors(window_start, window_end)
        traces = self._fetch_traces(window_start, window_end)
        messages = self._fetch_messages(window_start, window_end)

        nodes: list[dict] = []
        edges: list[dict] = []

        for c in commits:
            sha8 = (c.get("sha") or "")[:8]
            nodes.append({
                "id": f"commit-{sha8}",
                "type": "commit",
                "data": {
                    "label": sha8,
                    "detail": (c.get("message") or "")[:60],
                    "author": c.get("author", ""),
                    "committed_date": str(c.get("committed_date", "")),
                },
                "position": {"x": 0, "y": 0},
            })

        for e in errors:
            err_id = f"error-{e.get('id', '')}"
            nodes.append({
                "id": err_id,
                "type": "error",
                "data": {
                    "label": (e.get("title") or "error")[:40],
                    "detail": f"count: {e.get('count', 0)}",
                    "first_seen": str(e.get("first_seen", "")),
                },
                "position": {"x": 0, "y": 0},
            })
            closest = self._find_closest_prior(commits, e.get("first_seen", ""))
            if closest:
                sha8 = (closest.get("sha") or "")[:8]
                edges.append({
                    "id": f"e-commit-{sha8}-{err_id}",
                    "source": f"commit-{sha8}",
                    "target": err_id,
                    "label": "may have caused",
                })

        for t in traces:
            tid = (t.get("trace_id") or "")[:12]
            node_id = f"trace-{tid}"
            nodes.append({
                "id": node_id,
                "type": "trace",
                "data": {
                    "label": f"${float(t.get('total_cost') or 0):.4f}",
                    "detail": f"{t.get('gen_count', 0)} generations",
                    "trace_id": t.get("trace_id", ""),
                    "started_at": str(t.get("started_at", "")),
                },
                "position": {"x": 0, "y": 0},
            })
            closest_err = errors[0] if errors else None
            if closest_err:
                edges.append({
                    "id": f"e-error-trace-{tid}",
                    "source": f"error-{closest_err.get('id', '')}",
                    "target": node_id,
                    "label": "triggered",
                    "animated": True,
                })

        for i, m in enumerate(messages):
            msg_id = f"message-{i}"
            nodes.append({
                "id": msg_id,
                "type": "message",
                "data": {
                    "label": f"#{m.get('channel_name', 'slack')}",
                    "detail": (m.get("text") or "")[:60],
                    "posted_at": str(m.get("posted_at", "")),
                },
                "position": {"x": 0, "y": 0},
            })
            if errors:
                edges.append({
                    "id": f"e-error-msg-{i}",
                    "source": f"error-{errors[0].get('id', '')}",
                    "target": msg_id,
                    "label": "discussed",
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "window_start": window_start,
                "window_end": window_end,
                "commits": len(commits),
                "errors": len(errors),
                "traces": len(traces),
                "messages": len(messages),
            },
        }
