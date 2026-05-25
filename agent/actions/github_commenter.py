import requests
from agent.config import GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO


def post_pr_comment(
    pr_number: int,
    body: str,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
) -> str:
    resp = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
        json={"body": body},
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    if resp.status_code != 201:
        raise RuntimeError(f"GitHub comment failed ({resp.status_code}): {resp.text[:200]}")
    return resp.json()["html_url"]
