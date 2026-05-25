from fastapi import APIRouter
from api.models import RiskHistory
from agent import memory
from agent.modes.pr_risk_scorer import _get_pr_files, _compute_risk_score
from agent.config import GITHUB_OWNER, GITHUB_REPO

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/history", response_model=list[RiskHistory])
def risk_history(limit: int = 50):
    with memory.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM file_risk_history ORDER BY change_date DESC LIMIT ?", (limit,)
        ).fetchall()
    return [RiskHistory(**dict(r)) for r in rows]


@router.get("/current/{pr_number}")
def current_pr_risk(pr_number: int, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO):
    files = _get_pr_files(pr_number, owner, repo)
    file_histories = {f: memory.get_file_risk_history(f) for f in files}
    score = _compute_risk_score(file_histories)
    return {
        "pr_number": pr_number,
        "risk_score": score,
        "files_changed": files,
        "file_count": len(files),
    }
