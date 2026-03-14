"""
Data Enrichment Agent — Deep Business Intelligence Wrapper.

Wraps the existing deep_enrichment.py service for Paperclip orchestration.
Enriches prospects with GBP data, DNS records, social media presence, etc.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models.prospect import Prospect
from api.services.recon_engine import batch_recon_prospects

logger = logging.getLogger("agents.enrichment")


async def execute_enrichment_cycle(
    batch_size: int = 20,
    timeout_seconds: int = 120,
) -> Dict[str, Any]:
    """
    Execute one Enrichment Agent cycle — gather deep intelligence on prospects.

    Finds prospects with status='audited' (website analyzed, not yet enriched),
    runs deep enrichment (GBP, DNS, social media, public records), updates to 'enriched'.

    Args:
        batch_size: Maximum prospects to enrich this cycle
        timeout_seconds: Timeout per prospect enrichment

    Returns:
        {
            "enriched": int,        # Prospects successfully enriched
            "failed": int,          # Enrichments that errored
            "avg_data_points": int, # Average data points collected
            "cost": float,          # USD spent (API calls)
            "log": str,             # Execution summary
        }
    """
    logger.info(f"[Enrichment] Starting cycle — batch_size={batch_size}")

    try:
        # Use existing batch enrichment function
        enriched_count = await batch_recon_prospects(limit=batch_size)

        log_output = (
            f"Enrichment cycle completed:\n"
            f"  - Prospects enriched: {enriched_count}\n"
            f"  - Batch size: {batch_size}\n"
        )

        logger.info(log_output)

        return {
            "enriched": enriched_count,
            "failed": 0,
            "avg_data_points": 0,
            "cost": 0.0,
            "log": log_output,
        }

    except Exception as e:
        logger.error(f"[Enrichment] Cycle failed: {e}", exc_info=True)
        raise


async def get_enrichment_stats() -> Dict[str, Any]:
    """Get Enrichment Agent performance statistics."""
    async with async_session() as session:
        # Total enriched
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status.in_(["enriched", "scored", "queued", "contacted"])
        )
        result = await session.execute(stmt)
        total_enriched = result.scalar() or 0

        # Enriched today
        stmt = select(func.count(Prospect.id)).where(
            and_(
                Prospect.last_enriched_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
                Prospect.status.in_(["enriched", "scored", "queued", "contacted"])
            )
        )
        result = await session.execute(stmt)
        enriched_today = result.scalar() or 0

        # Awaiting enrichment
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "audited"
        )
        result = await session.execute(stmt)
        awaiting_enrichment = result.scalar() or 0

        # Email reachability rate
        stmt = select(
            func.count(Prospect.id).filter(Prospect.owner_email.isnot(None)).label("with_email"),
            func.count(Prospect.id).label("total")
        ).where(
            Prospect.status.in_(["enriched", "scored", "queued", "contacted"])
        )
        result = await session.execute(stmt)
        row = result.one()
        email_rate = (row.with_email / row.total * 100) if row.total > 0 else 0.0

    return {
        "total_enriched": total_enriched,
        "enriched_today": enriched_today,
        "awaiting_enrichment": awaiting_enrichment,
        "email_reachability_rate": round(email_rate, 1),
    }
