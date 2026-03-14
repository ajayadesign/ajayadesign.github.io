"""
Audit Agent — Website Analysis Wrapper.

Wraps the existing intel_engine.py service for Paperclip orchestration.
Runs Lighthouse audits on discovered prospects.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models.prospect import Prospect, WebsiteAudit
from api.services.intel_engine import audit_prospect

logger = logging.getLogger("agents.audit")


async def execute_audit_cycle(
    batch_size: int = 10,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """
    Execute one Audit Agent cycle — analyze prospect websites.

    Finds prospects with status='discovered' (have website, not yet audited),
    runs Lighthouse + tech stack detection, updates to status='audited'.

    Args:
        batch_size: Maximum audits to run this cycle
        timeout_seconds: Timeout per audit (Lighthouse can hang)

    Returns:
        {
            "completed": int,       # Audits successfully completed
            "failed": int,          # Audits that errored
            "avg_perf": float,      # Average Lighthouse performance score
            "log": str,             # Execution summary
        }
    """
    logger.info(f"[Audit] Starting cycle — batch_size={batch_size}, timeout={timeout_seconds}s")

    # Get prospects ready for audit
    prospects_to_audit: List[Prospect] = []

    async with async_session() as session:
        stmt = (
            select(Prospect)
            .where(
                Prospect.status == "discovered",
                Prospect.website_url.isnot(None),
                Prospect.website_url != "",
            )
            .order_by(Prospect.created_at.desc())
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        prospects_to_audit = list(result.scalars().all())

    if not prospects_to_audit:
        logger.info("[Audit] No prospects ready for audit")
        return {
            "completed": 0,
            "failed": 0,
            "avg_perf": 0.0,
            "log": "No prospects ready for audit (none with status='discovered')",
        }

    logger.info(f"[Audit] Found {len(prospects_to_audit)} prospects to audit")

    completed = 0
    failed = 0
    perf_scores: List[float] = []

    for prospect in prospects_to_audit:
        try:
            logger.info(f"[Audit] Auditing {prospect.business_name} ({prospect.website_url})")

            # Run audit using existing intel engine
            audit_result = await audit_prospect(
                prospect_id=prospect.id,
                timeout_seconds=timeout_seconds,
            )

            if audit_result.get("success"):
                completed += 1
                if audit_result.get("performance_score"):
                    perf_scores.append(audit_result["performance_score"])

                # Update prospect status
                async with async_session() as session:
                    prospect = await session.get(Prospect, prospect.id)
                    if prospect:
                        prospect.status = "audited"
                        prospect.last_audited_at = datetime.now(timezone.utc)
                        await session.commit()

            else:
                failed += 1
                logger.warning(f"[Audit] Failed to audit {prospect.business_name}: {audit_result.get('error')}")

        except Exception as e:
            failed += 1
            logger.error(f"[Audit] Error auditing {prospect.business_name}: {e}", exc_info=True)

    avg_perf = sum(perf_scores) / len(perf_scores) if perf_scores else 0.0

    log_output = (
        f"Audit cycle completed:\n"
        f"  - Prospects audited: {len(prospects_to_audit)}\n"
        f"  - Successful: {completed}\n"
        f"  - Failed: {failed}\n"
        f"  - Avg performance score: {avg_perf:.1f}/100\n"
    )

    if perf_scores:
        log_output += f"  - Performance range: {min(perf_scores):.1f} - {max(perf_scores):.1f}\n"

    logger.info(log_output)

    return {
        "completed": completed,
        "failed": failed,
        "avg_perf": avg_perf,
        "log": log_output,
    }


async def get_audit_stats() -> Dict[str, Any]:
    """Get Audit Agent performance statistics."""
    async with async_session() as session:
        # Total audits completed
        stmt = select(func.count(WebsiteAudit.id))
        result = await session.execute(stmt)
        total_audits = result.scalar() or 0

        # Audits completed today
        stmt = select(func.count(WebsiteAudit.id)).where(
            WebsiteAudit.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        )
        result = await session.execute(stmt)
        audits_today = result.scalar() or 0

        # Prospects awaiting audit
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "discovered",
            Prospect.website_url.isnot(None),
        )
        result = await session.execute(stmt)
        awaiting_audit = result.scalar() or 0

        # Average performance score (last 100 audits)
        stmt = (
            select(func.avg(WebsiteAudit.performance_score))
            .order_by(WebsiteAudit.created_at.desc())
            .limit(100)
        )
        result = await session.execute(stmt)
        avg_performance = result.scalar() or 0.0

    return {
        "total_audits": total_audits,
        "audits_today": audits_today,
        "awaiting_audit": awaiting_audit,
        "avg_performance_score": round(float(avg_performance), 1),
    }
