"""
Pipeline Monitor Agent — Autonomous Recovery & Health Check.

Monitors the pipeline for stuck prospects, detects bottlenecks,
auto-recovers stalled workflows, and reports health metrics.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory
from api.models.prospect import Prospect

logger = logging.getLogger("agents.pipeline_monitor")

# Staleness thresholds (minutes)
STALE_THRESHOLDS = {
    "discovered": 720,  # 12 hours (should be audited quickly)
    "audited": 360,     # 6 hours (should be enriched)
    "enriched": 240,    # 4 hours (should be scored)
    "scored": 1440,     # 24 hours (high-priority should get emails)
}


async def execute_monitor_cycle() -> Dict[str, Any]:
    """
    Execute one Pipeline Monitor cycle — check for stuck prospects and recover.

    Detects:
    - Prospects stuck in status for too long
    - Prospects with missing data (audit failed, no email found)
    - Prospects that need retry

    Actions:
    - Reset stuck prospects to previous status
    - Mark unrecoverable prospects as 'manual_handling'
    - Report bottlenecks

    Returns:
        {
            "stuck_found": int,
            "recovered": int,
            "marked_manual": int,
            "bottlenecks": dict,
            "log": str,
        }
    """
    logger.info("[PipelineMonitor] Starting health check cycle")

    stuck_found = 0
    recovered = 0
    marked_manual = 0
    bottlenecks = {}

    async with async_session() as session:
        # Check each status for stale prospects
        for status, stale_minutes in STALE_THRESHOLDS.items():
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)

            # Find stale prospects
            stmt = select(Prospect).where(
                and_(
                    Prospect.status == status,
                    Prospect.updated_at < cutoff
                )
            ).limit(50)  # Process in batches

            result = await session.execute(stmt)
            stale_prospects = list(result.scalars().all())

            if stale_prospects:
                stuck_found += len(stale_prospects)
                bottlenecks[status] = len(stale_prospects)
                logger.warning(f"[PipelineMonitor] Found {len(stale_prospects)} stale prospects in '{status}'")

                # Attempt recovery
                for prospect in stale_prospects:
                    try:
                        # Check retry count
                        retry_count = getattr(prospect, 'retry_count', 0) or 0

                        if retry_count >= 3:
                            # Too many retries, mark for manual handling
                            prospect.status = "manual_handling"
                            prospect.error_message = f"Stuck in '{status}' for {stale_minutes}min, max retries exceeded"
                            marked_manual += 1
                            logger.info(f"[PipelineMonitor] Marked {prospect.business_name} for manual handling")
                        else:
                            # Reset to previous status for retry
                            previous_status = _get_previous_status(status)
                            if previous_status:
                                prospect.status = previous_status
                                prospect.retry_count = retry_count + 1
                                prospect.updated_at = datetime.now(timezone.utc)
                                recovered += 1
                                logger.info(
                                    f"[PipelineMonitor] Recovered {prospect.business_name} "
                                    f"(reset from '{status}' → '{previous_status}')"
                                )

                    except Exception as e:
                        logger.error(f"[PipelineMonitor] Error recovering prospect {prospect.id}: {e}")

                await session.commit()

        # Check for bottlenecks (status with disproportionate count)
        status_counts = await _get_status_distribution(session)
        total_prospects = sum(status_counts.values())

        for status, count in status_counts.items():
            if status in ["contacted", "replied"]:
                continue  # These can accumulate, not a problem

            percentage = (count / total_prospects * 100) if total_prospects > 0 else 0
            if percentage > 40:  # More than 40% stuck in one status
                bottlenecks[f"{status}_accumulation"] = {
                    "count": count,
                    "percentage": round(percentage, 1),
                    "threshold": "40%",
                    "recommendation": f"Increase frequency or capacity of {status} handler"
                }

    log_output = (
        f"Pipeline Monitor cycle completed:\n"
        f"  - Stuck prospects found: {stuck_found}\n"
        f"  - Recovered automatically: {recovered}\n"
        f"  - Marked for manual handling: {marked_manual}\n"
    )

    if bottlenecks:
        log_output += "  - Bottlenecks detected:\n"
        for status, info in bottlenecks.items():
            if isinstance(info, dict):
                log_output += f"    • {status}: {info['count']} ({info['percentage']}%, rec: {info['recommendation']})\n"
            else:
                log_output += f"    • {status}: {info} stale prospects\n"

    logger.info(log_output)

    return {
        "stuck_found": stuck_found,
        "recovered": recovered,
        "marked_manual": marked_manual,
        "bottlenecks": bottlenecks,
        "log": log_output,
    }


def _get_previous_status(current_status: str) -> str:
    """Map current status to previous status for retry."""
    status_flow = {
        "audited": "discovered",
        "enriched": "audited",
        "scored": "enriched",
        "queued": "scored",
    }
    return status_flow.get(current_status, "discovered")


async def _get_status_distribution(session: AsyncSession) -> Dict[str, int]:
    """Get count of prospects by status."""
    stmt = select(
        Prospect.status,
        func.count(Prospect.id).label("count")
    ).group_by(Prospect.status)

    result = await session.execute(stmt)
    return {row.status: row.count for row in result.all()}


async def get_pipeline_monitor_stats() -> Dict[str, Any]:
    """Get Pipeline Monitor performance statistics."""
    async with async_session() as session:
        # Total recovered (all time)
        stmt = select(func.count(Prospect.id)).where(
            Prospect.retry_count > 0
        )
        result = await session.execute(stmt)
        total_recovered = result.scalar() or 0

        # Manual handling queue
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "manual_handling"
        )
        result = await session.execute(stmt)
        manual_queue = result.scalar() or 0

        # Status distribution
        status_dist = await _get_status_distribution(session)

        # Pipeline health score (0-100)
        # Factors: bottlenecks, manual queue size, recovery rate
        health_score = 100
        total = sum(status_dist.values())

        if total > 0:
            # Deduct points for bottlenecks
            for status, count in status_dist.items():
                if status in ["contacted", "replied"]:
                    continue
                pct = count / total * 100
                if pct > 40:
                    health_score -= min(20, (pct - 40))  # Max 20 point deduction per bottleneck

        # Deduct for large manual queue
        if manual_queue > 50:
            health_score -= min(15, (manual_queue - 50) / 10)

        health_score = max(0, round(health_score))

    return {
        "total_recovered": total_recovered,
        "manual_queue_size": manual_queue,
        "status_distribution": status_dist,
        "pipeline_health_score": health_score,
    }
