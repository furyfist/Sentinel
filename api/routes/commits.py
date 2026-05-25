import requests
from fastapi import APIRouter, Query

from agent.config import GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO

router = APIRouter()


def _fetch_commit(sha: str, owner: str, repo: str) -> dict:
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
        timeout=8,
    )
    if resp.status_code != 200:
        return {"sha": sha, "message": None, "author": None, "url": f"https://github.com/{owner}/{repo}/commit/{sha}"}
    data = resp.json()
    return {
        "sha": sha,
        "message": data["commit"]["message"].split("\n")[0],
        "author": data["commit"]["author"]["name"],
        "url": data["html_url"],
    }


@router.get("/commits")
def get_commits(
    shas: str = Query(..., description="Comma-separated list of commit SHAs"),
    owner: str = Query(GITHUB_OWNER),
    repo: str = Query(GITHUB_REPO),
):
    sha_list = [s.strip() for s in shas.split(",") if s.strip()]
    return [_fetch_commit(sha, owner, repo) for sha in sha_list]
