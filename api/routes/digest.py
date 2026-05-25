from fastapi import HTTPException
from fastapi import APIRouter
from api.models import DigestEntry
from agent import memory

router = APIRouter(prefix="/digest", tags=["digest"])


def _get_digests(limit: int) -> list[DigestEntry]:
    with memory.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM incident_reports WHERE detection_type = 'weekly_digest' ORDER BY detected_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [DigestEntry(id=r["id"], detected_at=r["detected_at"],
                        report_text=r["report_text"], cost_impact=r["cost_impact"] or 0.0)
            for r in rows]


@router.get("/latest", response_model=DigestEntry)
def latest_digest():
    digests = _get_digests(limit=1)
    if not digests:
        raise HTTPException(status_code=404, detail="No digests found")
    return digests[0]


@router.get("/history", response_model=list[DigestEntry])
def digest_history(limit: int = 20):
    return _get_digests(limit=limit)
