import argparse


def run(dry_run: bool = False) -> None:
    print(f"Starting On-Call Brain (dry_run={dry_run})...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel On-Call Brain — Mode A")
    parser.add_argument("--dry-run", action="store_true", help="Skip Slack post and GitHub issue creation")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
