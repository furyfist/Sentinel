from fastapi import APIRouter, HTTPException
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from agent import coral_client
from agent.forensics.trace_reconstructor import TraceReconstructor
from agent.forensics.incident_graph_builder import IncidentGraphBuilder

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=4)
QUERY_TIMEOUT = 120


def _with_timeout(fn, *args, timeout=QUERY_TIMEOUT, fallback=None):
    """Run fn(*args) with a wall-clock timeout; return fallback on timeout/error."""
    try:
        future = _executor.submit(fn, *args)
        return future.result(timeout=timeout)
    except (FuturesTimeout, Exception):
        return fallback


@router.get("/forensics/trace/{trace_id}")
def get_trace_graph(trace_id: str):
    recon = TraceReconstructor(coral_client)
    result = _with_timeout(recon.reconstruct_trace, trace_id,
                           fallback={"nodes": [], "edges": [], "error": "query timeout"})
    return result


@router.get("/forensics/incident")
def get_incident_graph(start: str, end: str):
    builder = IncidentGraphBuilder(coral_client)
    result = _with_timeout(builder.build_incident_graph, start, end,
                           fallback={"nodes": [], "edges": [], "error": "query timeout"})
    return result


@router.get("/forensics/worst-traces")
def get_worst_traces(limit: int = 10):
    recon = TraceReconstructor(coral_client)
    result = _with_timeout(recon.get_worst_traces, limit, fallback=[])
    return result
