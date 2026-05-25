"""Sentinel scheduler — On-Call Brain every 15min, Weekly Digest Mondays 9am."""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.blocking import BlockingScheduler
from agent.modes import oncall_brain, weekly_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sentinel")

scheduler = BlockingScheduler()


@scheduler.scheduled_job("interval", minutes=15, id="oncall_brain")
def run_oncall():
    log.info("Running On-Call Brain...")
    try:
        oncall_brain.run()
    except Exception as e:
        log.error(f"On-Call Brain error: {e}")


@scheduler.scheduled_job("cron", day_of_week="mon", hour=9, minute=0, id="weekly_digest")
def run_weekly():
    log.info("Running Weekly Digest...")
    try:
        weekly_digest.run()
    except Exception as e:
        log.error(f"Weekly Digest error: {e}")


if __name__ == "__main__":
    log.info("Sentinel scheduler started.")
    log.info("  On-Call Brain : every 15 minutes")
    log.info("  Weekly Digest : Mondays at 09:00")
    log.info("  PR Risk Scorer: on-demand via GitHub Action (python -m agent.modes.pr_risk_scorer --pr=<N>)")
    log.info("Press Ctrl+C to stop.")
    scheduler.start()
