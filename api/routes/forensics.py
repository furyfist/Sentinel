import os
from fastapi import APIRouter, HTTPException
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from agent import coral_client
from agent.forensics.trace_reconstructor import TraceReconstructor
from agent.forensics.incident_graph_builder import IncidentGraphBuilder

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=4)
QUERY_TIMEOUT = 300

_DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Demo static data — only used when DEMO_MODE=true (Railway deploy)
# Trace IDs match what seed_demo_sqlite.py puts in loop_detections
# ---------------------------------------------------------------------------

_DEMO_WORST_TRACES = [
    {
        "trace_id": "a3f9d21b-demo",
        "total_cost": 0.28,
        "observation_count": 22,
        "error_count": 3,
        "started_at": "2026-05-31T04:13:00Z",
    },
    {
        "trace_id": "b8c1e543-demo",
        "total_cost": 0.024,
        "observation_count": 15,
        "error_count": 1,
        "started_at": "2026-05-31T03:50:00Z",
    },
    {
        "trace_id": "c2d4f897-demo",
        "total_cost": 0.19,
        "observation_count": 18,
        "error_count": 2,
        "started_at": "2026-05-30T23:00:00Z",
    },
]

# Trace graph: commit → trace root → 3 generation nodes → error node
_DEMO_TRACE_GRAPHS = {
    "a3f9d21b-demo": {
        "nodes": [
            {"id": "commit-1", "type": "commit", "position": {"x": 0, "y": 0},
             "data": {"label": "d9c3e11", "detail": "refactor: raise max_tokens 500→4096", "author": "alice"}},
            {"id": "trace-1", "type": "trace", "position": {"x": 220, "y": 0},
             "data": {"label": "runaway-agent", "detail": "22 generations · 4 min", "trace_id": "a3f9d21b-demo"}},
            {"id": "gen-1", "type": "generation", "position": {"x": 440, "y": -120},
             "data": {"label": "retry-search #1", "model": "gpt-4", "cost": 0.013, "tokens": 1000}},
            {"id": "gen-2", "type": "generation", "position": {"x": 440, "y": 0},
             "data": {"label": "retry-search #2–21", "model": "gpt-4", "cost": 0.247, "tokens": 21000}},
            {"id": "gen-3", "type": "generation", "position": {"x": 440, "y": 120},
             "data": {"label": "retry-search #22", "model": "gpt-4", "cost": 0.013, "tokens": 1000, "is_error": True}},
            {"id": "error-1", "type": "error", "position": {"x": 660, "y": 0},
             "data": {"label": "RateLimitError", "detail": "Too many requests to OpenAI API (attempt 22)"}},
            {"id": "slack-1", "type": "message", "position": {"x": 880, "y": 0},
             "data": {"label": "@alice", "detail": "costs are 10x normal, trace runaway-agent spiking"}},
        ],
        "edges": [
            {"id": "e1", "source": "commit-1", "target": "trace-1", "label": "triggered"},
            {"id": "e2", "source": "trace-1", "target": "gen-1"},
            {"id": "e3", "source": "trace-1", "target": "gen-2"},
            {"id": "e4", "source": "trace-1", "target": "gen-3"},
            {"id": "e5", "source": "gen-3", "target": "error-1", "label": "raised"},
            {"id": "e6", "source": "error-1", "target": "slack-1", "label": "context"},
        ],
    },
    "b8c1e543-demo": {
        "nodes": [
            {"id": "trace-2", "type": "trace", "position": {"x": 0, "y": 0},
             "data": {"label": "support-bot", "detail": "15 generations · fetch_context loop", "trace_id": "b8c1e543-demo"}},
            {"id": "gen-a", "type": "generation", "position": {"x": 220, "y": -80},
             "data": {"label": "fetch_context #1–14", "model": "gpt-4o-mini", "cost": 0.020, "tokens": 14000}},
            {"id": "gen-b", "type": "generation", "position": {"x": 220, "y": 80},
             "data": {"label": "fetch_context #15", "model": "gpt-4o-mini", "cost": 0.004, "tokens": 1000, "is_error": True}},
            {"id": "error-2", "type": "error", "position": {"x": 440, "y": 80},
             "data": {"label": "JSONDecodeError", "detail": "Expecting value at position 0 — empty tool response"}},
        ],
        "edges": [
            {"id": "e1", "source": "trace-2", "target": "gen-a"},
            {"id": "e2", "source": "trace-2", "target": "gen-b"},
            {"id": "e3", "source": "gen-b", "target": "error-2", "label": "raised"},
        ],
    },
    "c2d4f897-demo": {
        "nodes": [
            {"id": "commit-3", "type": "commit", "position": {"x": 0, "y": 0},
             "data": {"label": "f1a8b33", "detail": "refactor: rewrite support-bot prompt to Q&A format", "author": "bob"}},
            {"id": "trace-3", "type": "trace", "position": {"x": 220, "y": 0},
             "data": {"label": "invoice-parser", "detail": "18 generations · schema drift", "trace_id": "c2d4f897-demo"}},
            {"id": "gen-c", "type": "generation", "position": {"x": 440, "y": -80},
             "data": {"label": "parse_invoice #1–17", "model": "gpt-4o-mini", "cost": 0.17, "tokens": 17000}},
            {"id": "gen-d", "type": "generation", "position": {"x": 440, "y": 80},
             "data": {"label": "parse_invoice #18", "model": "gpt-4o-mini", "cost": 0.02, "tokens": 1000, "is_error": True}},
            {"id": "error-3", "type": "error", "position": {"x": 660, "y": 80},
             "data": {"label": "KeyError: 'category'", "detail": "Downstream parser expects old 3-key schema"}},
            {"id": "slack-3", "type": "message", "position": {"x": 660, "y": -80},
             "data": {"label": "@bob", "detail": "pushed fix: reverted max_tokens change, monitoring now"}},
        ],
        "edges": [
            {"id": "e1", "source": "commit-3", "target": "trace-3", "label": "introduced drift"},
            {"id": "e2", "source": "trace-3", "target": "gen-c"},
            {"id": "e3", "source": "trace-3", "target": "gen-d"},
            {"id": "e4", "source": "gen-d", "target": "error-3", "label": "raised"},
            {"id": "e5", "source": "error-3", "target": "slack-3", "label": "context"},
        ],
    },
}

# Incident graph: commit → trace → errors + slack, all sources joined
_DEMO_INCIDENT_GRAPH = {
    "nodes": [
        {"id": "commit-i1", "type": "commit", "position": {"x": 0, "y": 100},
         "data": {"label": "d9c3e11", "detail": "refactor: raise max_tokens 500→4096", "author": "alice"}},
        {"id": "trace-i1", "type": "trace", "position": {"x": 220, "y": 0},
         "data": {"label": "runaway-agent", "detail": "$0.28 burned · 22 gens", "trace_id": "a3f9d21b-demo"}},
        {"id": "trace-i2", "type": "trace", "position": {"x": 220, "y": 200},
         "data": {"label": "support-bot", "detail": "$0.024 · schema drift", "trace_id": "b8c1e543-demo"}},
        {"id": "gen-i1", "type": "generation", "position": {"x": 440, "y": 0},
         "data": {"label": "retry-search ×22", "model": "gpt-4", "cost": 0.28, "tokens": 23000}},
        {"id": "error-i1", "type": "error", "position": {"x": 660, "y": -60},
         "data": {"label": "RateLimitError ×22", "detail": "OpenAI rate limit hit after loop"}},
        {"id": "error-i2", "type": "error", "position": {"x": 660, "y": 60},
         "data": {"label": "JSONDecodeError", "detail": "Empty tool response on fetch_context"}},
        {"id": "slack-i1", "type": "message", "position": {"x": 880, "y": -60},
         "data": {"label": "@alice", "detail": "Seeing elevated API costs in the last hour"}},
        {"id": "slack-i2", "type": "message", "position": {"x": 880, "y": 60},
         "data": {"label": "@alice", "detail": "pushed fix: reverted max_tokens change, monitoring now"}},
    ],
    "edges": [
        {"id": "ei1", "source": "commit-i1", "target": "trace-i1", "label": "triggered"},
        {"id": "ei2", "source": "commit-i1", "target": "trace-i2", "label": "triggered"},
        {"id": "ei3", "source": "trace-i1", "target": "gen-i1"},
        {"id": "ei4", "source": "gen-i1", "target": "error-i1", "label": "raised"},
        {"id": "ei5", "source": "trace-i2", "target": "error-i2", "label": "raised"},
        {"id": "ei6", "source": "error-i1", "target": "slack-i1", "label": "context"},
        {"id": "ei7", "source": "error-i2", "target": "slack-i2", "label": "context"},
    ],
}

# ---------------------------------------------------------------------------


def _with_timeout(fn, *args, timeout=QUERY_TIMEOUT, fallback=None):
    try:
        future = _executor.submit(fn, *args)
        return future.result(timeout=timeout)
    except (FuturesTimeout, Exception):
        return fallback


@router.get("/forensics/trace/{trace_id}")
def get_trace_graph(trace_id: str):
    if _DEMO_MODE:
        return _DEMO_TRACE_GRAPHS.get(trace_id, {"nodes": [], "edges": []})
    recon = TraceReconstructor(coral_client)
    result = _with_timeout(recon.reconstruct_trace, trace_id,
                           fallback={"nodes": [], "edges": [], "error": "query timeout"})
    return result


@router.get("/forensics/incident")
def get_incident_graph(start: str, end: str):
    if _DEMO_MODE:
        return _DEMO_INCIDENT_GRAPH
    builder = IncidentGraphBuilder(coral_client)
    result = _with_timeout(builder.build_incident_graph, start, end,
                           fallback={"nodes": [], "edges": [], "error": "query timeout"})
    return result


@router.get("/forensics/worst-traces")
def get_worst_traces(limit: int = 10):
    if _DEMO_MODE:
        return _DEMO_WORST_TRACES[:limit]
    recon = TraceReconstructor(coral_client)
    result = _with_timeout(recon.get_worst_traces, limit, fallback=[])
    return result
