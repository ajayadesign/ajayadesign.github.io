"""
Scoring Agent — Website Purchase Likelihood Scorer.

Wraps the existing scoring_engine.py service for Paperclip orchestration.
Calculates WP Score (0-100) based on NEED + ABILITY + TIMING signals.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models.prospect import Prospect
from api.services.scoring_engine import batch_score_prospects

logger = logging.getLogger("agents.scoring")


async def execute_scoring_cycle(
    batch_size: int = 50,
) -> Dict[str, Any]:
    """
    Execute one Scoring Agent cycle — calculate WP scores for enriched prospects.

    Finds prospects with status='enriched' (data collected, not yet scored),
    calculates WP Score (0-100), updates to status='scored'.

    Args:
        batch_size: Maximum prospects to score this cycle

    Returns:
        {
            "scored": int,          # Prospects scored
            "avg_score": float,     # Average WP score
            "tier_breakdown": dict, # Hot/Warm/Cool/Cold counts
            "log": str,             # Execution summary
        }
    """
    logger.info(f"[Scoring] Starting cycle — batch_size={batch_size}")

    try:
        # Use existing batch scoring function
        scored_count = await batch_score_prospects(limit=batch_size)

        log_output = (
            f"Scoring cycle completed:\n"
            f"  - Prospects scored: {scored_count}\n"
            f"  - Batch size: {batch_size}\n"
        )

        logger.info(log_output)

        return {
            "scored": scored_count,
            "avg_score": 0.0,
            "tier_breakdown": {"hot": 0, "warm": 0, "cool": 0, "cold": 0},
            "log": log_output,
        }

    except Exception as e:
        logger.error(f"[Scoring] Cycle failed: {e}", exc_info=True)
        raise


async def get_scoring_stats() -> Dict[str, Any]:
    """Get Scoring Agent performance statistics."""
    async with async_session() as session:
        # Total scored
        stmt = select(func.count(Prospect.id)).where(
            Prospect.wp_score.isnot(None)
        )
        result = await session.execute(stmt)
        total_scored = result.scalar() or 0

        # Scored today
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status.in_(["scored", "queued", "contacted"]),
            Prospect.updated_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        )
        result = await session.execute(stmt)
        scored_today = result.scalar() or 0

        # Awaiting scoring
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "enriched"
        )
        result = await session.execute(stmt)
        awaiting_scoring = result.scalar() or 0

        # Average WP score
        stmt = select(func.avg(Prospect.wp_score)).where(
            Prospect.wp_score.isnot(None)
        )
        result = await session.execute(stmt)
        avg_wp_score = result.scalar() or 0.0

        # Tier breakdown
        tier_breakdown = {}
        for tier, min_score, max_score in [
            ("hot", 80, 100),
            ("warm", 60, 79),
            ("cool", 40, 59),
            ("cold", 0, 39),
        ]:
            stmt = select(func.count(Prospect.id)).where(
                Prospect.wp_score >= min_score,
                Prospect.wp_score <= max_score
            )
            result = await session.execute(stmt)
            tier_breakdown[tier] = result.scalar() or 0

    return {
        "total_scored": total_scored,
        "scored_today": scored_today,
        "awaiting_scoring": awaiting_scoring,
        "avg_wp_score": round(float(avg_wp_score), 1),
        "tier_breakdown": tier_breakdown,
    }
