"""
Geo-Ring Manager — Ring expansion logic with manual Telegram approval.

Manages the progression of outreach from inner rings to outer rings.
Checks ring completion criteria and pauses for Telegram approval
before expanding (§9 of OUTREACH_AGENT_PLAN.md).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory
from api.models.prospect import GeoRing, Prospect

logger = logging.getLogger("outreach.geo_ring")


async def get_ring_stats(db: AsyncSession, ring_id) -> dict:
    """Compute completion stats for a ring."""
    ring = await db.get(GeoRing, ring_id)
    if not ring:
        return {}

    total = (await db.execute(
        select(func.count()).where(Prospect.geo_ring_id == ring_id)
    )).scalar() or 0

    contacted = (await db.execute(
        select(func.count()).where(
            Prospect.geo_ring_id == ring_id,
            Prospect.status.in_([
                "contacted", "follow_up_1", "follow_up_2", "follow_up_3",
                "replied", "meeting_booked", "promoted",
            ]),
        )
    )).scalar() or 0

    opened = (await db.execute(
        select(func.count()).where(
            Prospect.geo_ring_id == ring_id,
            Prospect.emails_opened > 0,
        )
    )).scalar() or 0

    replied = (await db.execute(
        select(func.count()).where(
            Prospect.geo_ring_id == ring_id,
            Prospect.status.in_(["replied", "meeting_booked", "promoted"]),
        )
    )).scalar() or 0

    meetings = (await db.execute(
        select(func.count()).where(
            Prospect.geo_ring_id == ring_id,
            Prospect.status.in_(["meeting_booked", "promoted"]),
        )
    )).scalar() or 0

    contacted_pct = (contacted / total * 100) if total > 0 else 0
    open_rate = (opened / contacted * 100) if contacted > 0 else 0
    reply_rate = (replied / contacted * 100) if contacted > 0 else 0

    return {
        "ring_id": str(ring_id),
        "ring_name": ring.name,
        "businesses_found": total,
        "contacted_count": contacted,
        "contacted_pct": round(contacted_pct, 1),
        "opened_count": opened,
        "open_rate": round(open_rate, 1),
        "replied_count": replied,
        "reply_rate": round(reply_rate, 1),
        "meetings": meetings,
        "crawl_started": ring.crawl_started.isoformat() if ring.crawl_started else None,
    }


async def check_ring_completion(ring_id) -> bool:
    """
    Check if a ring meets completion criteria (§9.2).
    If complete, pause agent and send Telegram notification for approval.
    Returns True if ring is complete.
    """
    from api.services.telegram_outreach import notify_ring_complete
    from api.services.firebase_summarizer import push_agent_status

    async with async_session_factory() as db:
        ring = await db.get(GeoRing, ring_id)
        if not ring or ring.status == "complete":
            return ring.status == "complete" if ring else False

        stats = await get_ring_stats(db, ring_id)
        total = stats.get("businesses_found", 0)
        contacted_pct = stats.get("contacted_pct", 0)

        # Completion criteria
        is_complete = (
            total >= 50 and
            contacted_pct >= 80 and
            ring.crawl_started is not None and
            (datetime.now(timezone.utc) - ring.crawl_started).days >= 7
        )

        if is_complete:
            ring.status = "complete"
            ring.crawl_completed = datetime.now(timezone.utc)
            await db.commit()

            # Push agent to awaiting_approval state
            await push_agent_status("paused", ring.name, 0)

            # Get next ring info
            next_ring = await get_next_ring(db, ring.ring_number)
            next_name = next_ring.name if next_ring else "No more rings"

            # Notify via Telegram
            await notify_ring_complete(
                ring_name=ring.name,
                stats=stats,
                next_ring_name=next_name,
            )

            logger.info("Ring %s complete — awaiting approval for expansion to %s",
                        ring.name, next_name)
            return True

    return False


async def get_next_ring(db: AsyncSession, current_number: int) -> Optional[GeoRing]:
    """Get the next ring in sequence."""
    result = await db.execute(
        select(GeoRing)
        .where(GeoRing.ring_number == current_number + 1)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_active_ring() -> Optional[dict]:
    """Get the currently active ring (crawling or latest complete)."""
    async with async_session_factory() as db:
        # First try active ring
        result = await db.execute(
            select(GeoRing)
            .where(GeoRing.status == "active")
            .order_by(GeoRing.ring_number)
            .limit(1)
        )
        ring = result.scalar_one_or_none()
        if ring:
            return ring.to_dict()

        # Fallback: Get lowest pending ring
        result = await db.execute(
            select(GeoRing)
            .where(GeoRing.status == "pending")
            .order_by(GeoRing.ring_number)
            .limit(1)
        )
        ring = result.scalar_one_or_none()
        return ring.to_dict() if ring else None


async def expand_to_next_ring() -> Optional[dict]:
    """
    Approve expansion to the next ring.
    Called from Telegram callback or dashboard button.
    """
    from api.services.firebase_summarizer import push_agent_status

    async with async_session_factory() as db:
        # Find latest complete ring
        result = await db.execute(
            select(GeoRing)
            .where(GeoRing.status == "complete")
            .order_by(GeoRing.ring_number.desc())
            .limit(1)
        )
        completed = result.scalar_one_or_none()
        current_number = completed.ring_number if completed else -1

        # Activate next ring
        next_ring = await get_next_ring(db, current_number)
        if not next_ring:
            logger.info("No more rings to expand to")
            return None

        next_ring.status = "active"
        await db.commit()

        await push_agent_status("running", next_ring.name, 0)

        logger.info("Expanded to ring %d: %s", next_ring.ring_number, next_ring.name)
        return next_ring.to_dict()


async def get_all_rings_summary() -> list[dict]:
    """Get summary of all rings for dashboard sidebar."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(GeoRing).order_by(GeoRing.ring_number)
        )
        rings = result.scalars().all()

        summaries = []
        for ring in rings:
            stats = await get_ring_stats(db, ring.id)
            summaries.append({
                "id": str(ring.id),
                "name": ring.name,
                "ring_number": ring.ring_number,
                "radius_miles": float(ring.radius_miles),
                "status": ring.status,
                "businesses_found": stats.get("businesses_found", 0),
                "contacted_pct": stats.get("contacted_pct", 0),
                "replied_count": stats.get("replied_count", 0),
            })

        return summaries
