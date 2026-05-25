import requests
from agent.config import GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO


def create_incident_issue(
    title: str,
    body: str,
    labels: list = None,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
) -> str:
    resp = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        json={"title": title, "body": body, "labels": labels or ["incident", "sentinel"]},
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    if resp.status_code != 201:
        raise RuntimeError(f"GitHub issue creation failed ({resp.status_code}): {resp.text[:200]}")
    return resp.json()["html_url"]
