from fastapi import APIRouter, HTTPException
from agent import coral_client
from agent.forensics.trace_reconstructor import TraceReconstructor
from agent.forensics.incident_graph_builder import IncidentGraphBuilder

router = APIRouter()


@router.get("/forensics/trace/{trace_id}")
def get_trace_graph(trace_id: str):
    """Single-trace React Flow graph from trace_reconstructor."""
    try:
        recon = TraceReconstructor(coral_client)
        return recon.reconstruct_trace(trace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forensics/incident")
def get_incident_graph(start: str, end: str):
    """Cross-source incident graph for a time window."""
    try:
        builder = IncidentGraphBuilder(coral_client)
        return builder.build_incident_graph(start, end)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forensics/worst-traces")
def get_worst_traces(limit: int = 10):
    """Top N most expensive traces by total cost."""
    try:
        recon = TraceReconstructor(coral_client)
        return recon.get_worst_traces(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
