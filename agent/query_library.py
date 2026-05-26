from agent import coral_client
from agent.config import GITHUB_OWNER, GITHUB_REPO


def cost_spike_detection() -> list[dict]:
    """Query 7.1 — hourly LLM cost for the last 24 hours."""
    sql = """
        SELECT
          date_trunc('hour', start_time) as hour,
          SUM(total_cost) as hourly_cost,
          COUNT(*) as generation_count,
          AVG(total_cost) as avg_cost_per_call
        FROM langfuse.observations
        WHERE type = 'GENERATION'
          AND start_time > NOW() - INTERVAL '24 hours'
        GROUP BY date_trunc('hour', start_time)
        ORDER BY hour DESC
    """
    return coral_client.query(sql)


def commit_to_cost_blame(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> list[dict]:
    """Query 7.2 — correlate commits with Sentry errors and Langfuse cost in the 24h after each commit."""
    sql = f"""
        SELECT
          g.sha,
          g.commit__message as commit_message,
          g.author__login as author,
          g.commit__author__date as committed_date,
          COUNT(DISTINCT s.id) as errors_after_commit,
          SUM(l.total_cost) as cost_after_commit
        FROM github.commits g
        LEFT JOIN sentry.issues s
          ON s.first_seen > CAST(g.commit__author__date AS TIMESTAMP)
          AND s.first_seen < CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
        LEFT JOIN langfuse.observations l
          ON l.start_time > CAST(g.commit__author__date AS TIMESTAMP)
          AND l.start_time < CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
          AND l.type = 'GENERATION'
        WHERE g.owner = '{owner}'
          AND g.repo = '{repo}'
          AND CAST(g.commit__author__date AS TIMESTAMP) > NOW() - INTERVAL '7 days'
        GROUP BY g.sha, g.commit__message, g.author__login, g.commit__author__date
        ORDER BY cost_after_commit DESC NULLS LAST
        LIMIT 10
    """
    return coral_client.query(sql)


def error_cascade_detection() -> list[dict]:
    """Query 7.3 — Sentry errors in last 48h with associated Langfuse retry cost."""
    sql = """
        SELECT
          s.title as error_title,
          s.count as error_count,
          s.first_seen,
          s.last_seen,
          SUM(l.total_cost) as associated_cost,
          COUNT(l.id) as retry_generations
        FROM sentry.issues s
        JOIN langfuse.observations l
          ON l.start_time BETWEEN s.first_seen AND s.last_seen
          AND l.type = 'GENERATION'
        WHERE s.first_seen > NOW() - INTERVAL '48 hours'
        GROUP BY s.title, s.count, s.first_seen, s.last_seen
        HAVING SUM(l.total_cost) > 1.0
        ORDER BY associated_cost DESC
        LIMIT 10
    """
    return coral_client.query(sql)


def slack_incident_context(incident_start: str, incident_end: str) -> list[dict]:
    """Query 7.4 — Slack messages in incident channels during a time window.

    incident_start / incident_end: ISO 8601 strings, e.g. '2026-05-25T00:00:00Z'
    Note: slack.messages requires channel context; returns empty list if table unavailable.
    """
    sql = f"""
        SELECT
          m.text,
          m.user as author,
          m.ts as posted_at,
          c.name as channel_name
        FROM slack.messages m
        JOIN slack.channels c ON c.id = m.channel
        WHERE m.ts > '{incident_start}'
          AND m.ts < '{incident_end}'
          AND c.name IN ('incidents', 'engineering', 'backend', 'alerts')
        ORDER BY m.ts ASC
        LIMIT 20
    """
    try:
        return coral_client.query(sql)
    except RuntimeError:
        return []


def pr_risk_historical(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> list[dict]:
    """Query 7.5 — per-commit cost and error deltas over the last 90 days for PR risk scoring."""
    sql = f"""
        SELECT
          g.sha,
          g.commit__message as message,
          g.commit__author__date as committed_date,
          SUM(l.total_cost) as cost_after,
          COUNT(s.id) as errors_after
        FROM github.commits g
        LEFT JOIN langfuse.observations l
          ON l.start_time BETWEEN CAST(g.commit__author__date AS TIMESTAMP)
            AND CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
          AND l.type = 'GENERATION'
        LEFT JOIN sentry.issues s
          ON s.first_seen BETWEEN CAST(g.commit__author__date AS TIMESTAMP)
            AND CAST(g.commit__author__date AS TIMESTAMP) + INTERVAL '24 hours'
        WHERE g.owner = '{owner}'
          AND g.repo = '{repo}'
          AND CAST(g.commit__author__date AS TIMESTAMP) > NOW() - INTERVAL '90 days'
        GROUP BY g.sha, g.commit__message, g.commit__author__date
        ORDER BY g.commit__author__date DESC
    """
    return coral_client.query(sql)


def weekly_digest_shipped(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> list[dict]:
    """Query 7.6 — PRs merged in the last 7 days."""
    sql = f"""
        SELECT
          p.title,
          p.number,
          p.user__login as author,
          p.merged_at,
          p.additions,
          p.deletions
        FROM github.pulls p
        WHERE p.owner = '{owner}'
          AND p.repo = '{repo}'
          AND p.state = 'closed'
          AND p.merged_at > NOW() - INTERVAL '7 days'
        ORDER BY p.merged_at DESC
    """
    return coral_client.query(sql)


def loop_detection_q16(threshold: int = 8) -> list[dict]:
    """Q16 — traces with abnormally high generation counts in the last 2 hours."""
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
    return coral_client.query(sql)


def loop_fingerprint_q17(trace_id: str) -> list[dict]:
    """Q17 — full observation chain for a specific trace (loop fingerprinting)."""
    sql = f"""
        SELECT name, start_time, total_cost, model
        FROM langfuse.observations
        WHERE trace_id = '{trace_id}'
        ORDER BY start_time ASC
    """
    return coral_client.query(sql)


def agent_loop_detection() -> list[dict]:
    """Query 7.7 — traces with >10 generations in the last hour (runaway agent loops)."""
    sql = """
        SELECT
          trace_id,
          COUNT(*) as generation_count,
          MIN(start_time) as first_gen,
          MAX(start_time) as last_gen,
          SUM(total_cost) as total_cost
        FROM langfuse.observations
        WHERE type = 'GENERATION'
          AND start_time > NOW() - INTERVAL '1 hour'
        GROUP BY trace_id
        HAVING COUNT(*) > 10
        ORDER BY generation_count DESC
        LIMIT 10
    """
    return coral_client.query(sql)
