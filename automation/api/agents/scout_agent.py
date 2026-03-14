"""
Scout Agent — Business Discovery Wrapper.

Wraps the existing crawl_engine.py service for Paperclip orchestration.
Discovers local businesses via Google Maps API and creates Prospect records.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import select, func

from api.database import async_session
from api.models.prospect import Prospect, GeoRing
from api.services.crawl_engine import crawl_ring

logger = logging.getLogger("agents.scout")


async def execute_scout_cycle(
    geo_ring: str = "manor",
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Execute one Scout Agent cycle — discover businesses in specified geo ring.

    Args:
        geo_ring: Geographic area to search (manor, pflugerville, round_rock, etc.)
        limit: Maximum businesses to discover this cycle

    Returns:
        {
            "count": int,           # Businesses discovered
            "geo_ring": str,        # Ring searched
            "api_calls": int,       # Google Maps API calls made
            "duplicates": int,      # Prospects skipped (already exist)
            "cost": float,          # USD spent (Google Maps API)
            "log": str,             # Execution summary
        }
    """
    logger.info(f"[Scout] Starting cycle — geo_ring={geo_ring}, limit={limit}")

    # Count existing prospects before discovery
    async with async_session() as session:
        # Get ring ID from ring name
        stmt = select(GeoRing).where(GeoRing.name == geo_ring)
        result = await session.execute(stmt)
        ring = result.scalar_one_or_none()

        if not ring:
            logger.warning(f"Ring '{geo_ring}' not found")
            return {
                "count": 0,
                "geo_ring": geo_ring,
                "error": f"Ring '{geo_ring}' not found",
                "log": f"Ring '{geo_ring}' not found in database",
            }

        ring_id = str(ring.id)

        # Count existing prospects
        stmt = select(func.count(Prospect.id))
        result = await session.execute(stmt)
        count_before = result.scalar() or 0

    # Execute discovery using existing crawl_ring function
    try:
        discovery_result = await crawl_ring(ring_id)

        # Count prospects after discovery
        async with async_session() as session:
            stmt = select(func.count(Prospect.id))
            result = await session.execute(stmt)
            count_after = result.scalar() or 0

        new_count = count_after - count_before
        discovered = discovery_result.get("total_found", 0)
        categories_done = discovery_result.get("categories_done", 0)

        # Estimate API calls (rough approximation)
        api_calls = categories_done * 5  # Approximate calls per category

        # Calculate cost (Google Maps API pricing)
        # Places Nearby: $32 / 1,000 calls = $0.032 per call
        cost = api_calls * 0.032

        log_output = (
            f"Scout cycle completed:\n"
            f" - Geo ring: {geo_ring}\n"
            f"  - New businesses: {new_count}\n"
            f"  - Discovered: {discovered}\n"
            f"  - Categories: {categories_done}\n"
            f"  - Est. API calls: {api_calls}\n"
            f"  - Est. cost: ${cost:.4f}\n"
            f"  - Total prospects in DB: {count_after}\n"
        )

        logger.info(log_output)

        return {
            "count": new_count,
            "geo_ring": geo_ring,
            "api_calls": api_calls,
            "discovered": discovered,
            "categories_done": categories_done,
            "cost": cost,
            "log": log_output,
        }

    except Exception as e:
        logger.error(f"[Scout] Discovery failed: {e}", exc_info=True)
        raise


async def get_scout_stats() -> Dict[str, Any]:
    """Get Scout Agent performance statistics."""
    async with async_session() as session:
        # Total prospects discovered
        stmt = select(func.count(Prospect.id))
        result = await session.execute(stmt)
        total_discovered = result.scalar() or 0

        # Prospects discovered today
        stmt = select(func.count(Prospect.id)).where(
            Prospect.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
        )
        result = await session.execute(stmt)
        discovered_today = result.scalar() or 0

        # Active geo rings
        stmt = select(func.count(GeoRing.id)).where(GeoRing.is_active == True)
        result = await session.execute(stmt)
        active_rings = result.scalar() or 0

    return {
        "total_discovered": total_discovered,
        "discovered_today": discovered_today,
        "active_rings": active_rings,
    }
