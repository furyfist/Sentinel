import argparse
import requests
from agent import memory, narrator
from agent.actions import github_commenter
from agent.config import GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO


def _get_pr_files(pr_number: int, owner: str, repo: str) -> list[str]:
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        return []
    return [f["filename"] for f in resp.json()]


def _compute_risk_score(file_histories: dict) -> int:
    """Weighted sum of past errors and cost deltas across all changed files. Returns 0-100."""
    total_errors = sum(
        sum(r["error_delta"] for r in rows) for rows in file_histories.values()
    )
    total_cost = sum(
        sum(r["cost_delta"] for r in rows) for rows in file_histories.values()
    )
    # errors weighted 4x, cost capped contribution at 50
    raw = (total_errors * 4) + min(total_cost * 10, 50)
    return min(100, int(raw))


def run(pr_number: int, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO, dry_run: bool = False) -> None:
    print(f"Starting PR Risk Scorer (pr={pr_number}, dry_run={dry_run})...")

    # Step 1 — get changed files
    print("  [1/5] Fetching PR changed files...")
    files = _get_pr_files(pr_number, owner, repo)
    print(f"        {len(files)} file(s): {files[:5]}")

    # Step 2 — look up file_risk_history for each file
    print("  [2/5] Querying file risk history from SQLite...")
    file_histories = {f: memory.get_file_risk_history(f) for f in files}
    total_history_rows = sum(len(v) for v in file_histories.values())
    print(f"        {total_history_rows} historical row(s) found")

    # Step 3 — compute risk score
    score = _compute_risk_score(file_histories)
    print(f"  [3/5] Risk score: {score}/100")

    # Step 4 — narrate
    print("  [4/5] Narrating risk summary with Groq...")
    history_list = [
        {"file": f, "history": rows} for f, rows in file_histories.items()
    ]
    summary = narrator.narrate_pr_risk(history_list, score)
    print(f"\n--- PR RISK REPORT (PR #{pr_number}) ---")
    print(f"Score: {score}/100")
    print(summary)
    print("--- END REPORT ---\n")

    # Step 5 — post comment + save to SQLite
    print("  [5/5] Posting PR comment and saving to SQLite...")
    comment_body = f"## Sentinel Risk Score: {score}/100\n\n{summary}"

    if dry_run:
        print(f"        [DRY RUN] Would post comment to PR #{pr_number}")
    else:
        try:
            url = github_commenter.post_pr_comment(pr_number, comment_body, owner, repo)
            print(f"        Comment posted: {url}")
        except RuntimeError as e:
            print(f"        Warning: {e}")

    for file_path, rows in file_histories.items():
        memory.save_file_risk(
            file_path=file_path,
            commit_sha=f"pr-{pr_number}",
            cost_delta=sum(r["cost_delta"] for r in rows),
            error_delta=sum(r["error_delta"] for r in rows),
            risk_score=score,
        )
    print(f"        Saved {len(files)} file risk row(s) to SQLite")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel PR Risk Scorer — Mode B")
    parser.add_argument("--pr", type=int, required=True, help="PR number to score")
    parser.add_argument("--owner", default=GITHUB_OWNER)
    parser.add_argument("--repo", default=GITHUB_REPO)
    parser.add_argument("--dry-run", action="store_true", help="Skip GitHub PR comment")
    args = parser.parse_args()
    run(pr_number=args.pr, owner=args.owner, repo=args.repo, dry_run=args.dry_run)
