"""
Opens a demo PR on furyfist/Sentinel that touches high-risk agent files
so the PR risk scorer produces a meaningful score on camera.

Usage:
    python scripts/open_demo_pr.py

Prints the PR number and URL when done. Pass that PR number to:
    python agent/modes/pr_risk_scorer.py --pr <N>
"""
import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from agent.config import GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO

BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

BRANCH = "demo/retry-logic-patch"

# Touches oncall_brain and the loop detector — two historically risky files
FILES = {
    "agent/modes/oncall_brain.py": "# retry-logic: increased max_retries to 5 for upstream resilience\n",
    "agent/detectors/loop_detector.py": "# retry-logic: relaxed loop threshold for high-throughput workloads\n",
    "settings.json": None,  # read live, append a comment line
}


def get_default_branch() -> str:
    r = requests.get(BASE, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()["default_branch"]


def get_ref_sha(ref: str) -> str:
    r = requests.get(f"{BASE}/git/ref/heads/{ref}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()["object"]["sha"]


def branch_exists(branch: str) -> bool:
    r = requests.get(f"{BASE}/git/ref/heads/{branch}", headers=HEADERS, timeout=10)
    return r.status_code == 200


def create_branch(branch: str, from_sha: str):
    r = requests.post(
        f"{BASE}/git/refs",
        headers=HEADERS,
        json={"ref": f"refs/heads/{branch}", "sha": from_sha},
        timeout=10,
    )
    r.raise_for_status()


def get_file(path: str, branch: str) -> tuple[str, str]:
    """Returns (content_str, sha)."""
    r = requests.get(
        f"{BASE}/contents/{path}",
        headers=HEADERS,
        params={"ref": branch},
        timeout=10,
    )
    r.raise_for_status()
    import base64
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def update_file(path: str, content: str, file_sha: str, branch: str, message: str):
    import base64
    r = requests.put(
        f"{BASE}/contents/{path}",
        headers=HEADERS,
        json={
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "sha": file_sha,
            "branch": branch,
        },
        timeout=10,
    )
    r.raise_for_status()


def open_pr(branch: str, base: str) -> dict:
    r = requests.post(
        f"{BASE}/pulls",
        headers=HEADERS,
        json={
            "title": "feat: increase retry limits and relax loop threshold for resilience",
            "body": (
                "## What\n"
                "Bumps `max_retries` in the on-call brain and relaxes the loop detection "
                "threshold in the loop detector to handle high-throughput workloads better.\n\n"
                "## Why\n"
                "Upstream LLM APIs have been returning transient 429s under load. "
                "The current retry ceiling is too aggressive and causing false negatives.\n\n"
                "## Risk\n"
                "Touches two high-frequency agent files. Loop detector change could affect "
                "detection sensitivity. Needs careful review.\n\n"
                "> Opened automatically by Sentinel demo script for PR risk scoring demo."
            ),
            "head": branch,
            "base": base,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def run():
    print(f"\nOpening demo PR on {GITHUB_OWNER}/{GITHUB_REPO}...\n")

    default = get_default_branch()
    print(f"  Default branch: {default}")

    base_sha = get_ref_sha(default)
    print(f"  Base SHA: {base_sha[:12]}")

    if branch_exists(BRANCH):
        print(f"  Branch '{BRANCH}' already exists, reusing it.")
    else:
        create_branch(BRANCH, base_sha)
        print(f"  Created branch: {BRANCH}")

    for path, prepend in FILES.items():
        if prepend is None:
            continue
        try:
            current, file_sha = get_file(path, BRANCH)
            new_content = prepend + current
            update_file(
                path, new_content, file_sha, BRANCH,
                message=f"refactor({path.split('/')[0]}): adjust retry and loop config for resilience",
            )
            print(f"  Updated: {path}")
        except Exception as e:
            print(f"  Warning: could not update {path}: {e}")

    pr = open_pr(BRANCH, default)
    print(f"\n  PR #{pr['number']} opened: {pr['html_url']}")
    print(f"\nNow run:")
    print(f"  python agent/modes/pr_risk_scorer.py --pr {pr['number']}\n")


if __name__ == "__main__":
    run()
