"""
Outreach Agent — Firebase Janitor.

Nightly self-cleaning system that enforces retention rules across all
Firebase RTDB outreach nodes. Runs at 3:00 AM daily via APScheduler.

Implements §13.7.5 of OUTREACH_AGENT_PLAN.md.
"""

import logging

from api.services.firebase_summarizer import prune_by_age, prune_firebase_node

logger = logging.getLogger(__name__)


async def firebase_janitor():
    """
    Single nightly sweep enforcing ALL retention rules across every node.
    Idempotent — safe to run multiple times. Acts as a safety net behind
    the per-push prune logic. If prunes were skipped or failed, this catches them.

    Schedule: APScheduler CronTrigger(hour=3, minute=0) in main.py
    """
    logger.info("🧹 Firebase janitor: starting nightly sweep...")

    # FIFO prunes (by child count)
    await prune_firebase_node("outreach/activity", max_children=50)
    await prune_firebase_node("outreach/log", max_children=200)
    await prune_firebase_node("outreach/alerts", max_children=20)

    # Age-based prunes
    await prune_by_age("outreach/snapshots", max_age_days=90)
    await prune_by_age("outreach/scorecard", max_age_days=84)   # 12 weeks
    await prune_by_age("outreach/health", max_age_hours=72)

    logger.info("🧹 Firebase janitor: nightly sweep complete")


# Alias expected by scheduler in main.py
nightly_prune = firebase_janitor
