from fastapi import APIRouter, HTTPException
from api.models import IncidentReport
from agent import memory

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentReport])
def list_incidents(limit: int = 20):
    rows = memory.get_incidents(limit=limit)
    return [IncidentReport.from_row(r) for r in rows
            if r.get("detection_type") != "weekly_digest"]


@router.get("/{incident_id}", response_model=IncidentReport)
def get_incident(incident_id: int):
    with memory.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM incident_reports WHERE id = ?", (incident_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentReport.from_row(dict(row))
