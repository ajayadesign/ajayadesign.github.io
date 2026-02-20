"""
Analytics Archiver — Firebase RTDB → PostgreSQL (monthly).

On the 1st of each month at 2 AM CT, downloads everything under
/site_analytics/ that belongs to the **previous month**, stores it in
the ``site_analytics_archive`` table, and then prunes the archived
date-keys from Firebase to reclaim RTDB storage.

Retry logic: if the API server or Firebase is unreachable, the archiver
retries up to ``MAX_RETRIES`` times with exponential back-off.  If all
retries are exhausted the job silently exits — APScheduler will try
again next month (or you can trigger it manually via ``/api/admin/archive-analytics``).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("analytics.archiver")

# ── tunables ──
MAX_RETRIES = 5
INITIAL_BACKOFF_S = 30          # 30 s → 60 s → 120 s → 240 s → 480 s
CATEGORIES = ("pageViews", "clicks", "scrollDepth", "performance", "sessions")


# ─────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────

def _previous_month_prefix() -> str:
    """Return 'YYYY-MM' for the calendar month before *today*."""
    first_of_this_month = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )
    last_month = first_of_this_month - timedelta(days=1)
    return last_month.strftime("%Y-%m")


def _date_keys_for_month(prefix: str) -> list[str]:
    """Generate all 'YYYY-MM-DD' strings that belong to *prefix* month."""
    year, month = int(prefix[:4]), int(prefix[5:7])
    d = datetime(year, month, 1)
    keys: list[str] = []
    while d.month == month:
        keys.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return keys


def _count_events(payload: dict) -> int:
    """Count total leaf events across all slugs in a date snapshot."""
    total = 0
    if not isinstance(payload, dict):
        return 0
    for slug_val in payload.values():
        if isinstance(slug_val, dict):
            total += len(slug_val)          # push-id children
        elif isinstance(slug_val, (int, float)):
            total += 1                      # scrollDepth counters
        else:
            total += 1
    return total


# ─────────────────────────────────────────────────────────────────────
# startup catch-up
# ─────────────────────────────────────────────────────────────────────

async def catch_up_if_needed() -> dict | None:
    """
    Called once at server startup.  Checks whether last month's
    analytics have already been archived.  If not, runs the archiver
    immediately so a missed cron window doesn't lose a whole month.
    """
    prefix = _previous_month_prefix()
    try:
        from api.database import async_session_factory
        from api.models.site_analytics import SiteAnalyticsArchive
        from sqlalchemy import select, func

        async with async_session_factory() as session:
            count = (
                await session.execute(
                    select(func.count()).select_from(SiteAnalyticsArchive).where(
                        SiteAnalyticsArchive.date_key.like(f"{prefix}%")
                    )
                )
            ).scalar_one()

        if count > 0:
            logger.info("✅ Archive for %s already present (%d rows) — no catch-up needed", prefix, count)
            return None

        logger.info("⚠️  No archive rows for %s — running catch-up now", prefix)
        return await archive_site_analytics(prefix)
    except Exception as e:
        logger.error("Catch-up check failed: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────
# core
# ─────────────────────────────────────────────────────────────────────

async def archive_site_analytics(month_prefix: str | None = None) -> dict:
    """
    Download last month's /site_analytics/ data from Firebase RTDB,
    store each (category, date) pair in PostgreSQL, then delete the
    archived keys from Firebase.

    Parameters
    ----------
    month_prefix : str, optional
        Override month to archive (``"YYYY-MM"``).  Defaults to the
        previous calendar month.

    Returns
    -------
    dict  with ``archived`` (int) and ``pruned`` (int) counts.
    """
    # ── lazy imports (match codebase pattern) ──
    try:
        import firebase_admin.db as firebase_db
    except Exception:
        logger.warning("⚠️  firebase_admin not available — skipping archive")
        return {"archived": 0, "pruned": 0}

    from api.services.firebase import is_initialized
    if not is_initialized():
        logger.warning("⚠️  Firebase not initialised — skipping archive")
        return {"archived": 0, "pruned": 0}

    from api.database import async_session_factory
    from api.models.site_analytics import SiteAnalyticsArchive
    from sqlalchemy import select

    prefix = month_prefix or _previous_month_prefix()
    date_keys = _date_keys_for_month(prefix)
    logger.info("📦 Archiving /site_analytics/ for %s (%d days)", prefix, len(date_keys))

    archived = 0
    pruned = 0

    for category in CATEGORIES:
        for date_key in date_keys:
            fb_path = f"site_analytics/{category}/{date_key}"

            # ── read from Firebase with retries ──
            snapshot = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    ref = firebase_db.reference(fb_path)
                    snapshot = ref.get()
                    break  # success
                except Exception as e:
                    wait = INITIAL_BACKOFF_S * (2 ** (attempt - 1))
                    logger.warning(
                        "⚠️  Read %s failed (attempt %d/%d): %s — retrying in %ds",
                        fb_path, attempt, MAX_RETRIES, e, wait,
                    )
                    await asyncio.sleep(wait)

            if snapshot is None:
                continue  # no data for this date/category (or all retries failed)

            raw_json = json.dumps(snapshot, default=str)
            size_bytes = len(raw_json.encode("utf-8"))
            event_count = _count_events(snapshot)

            # ── store in Postgres (upsert-style: skip if already archived) ──
            try:
                async with async_session_factory() as session:
                    exists = (
                        await session.execute(
                            select(SiteAnalyticsArchive.id).where(
                                SiteAnalyticsArchive.category == category,
                                SiteAnalyticsArchive.date_key == date_key,
                            )
                        )
                    ).scalar_one_or_none()

                    if exists:
                        logger.debug("⏭️  %s/%s already archived — skip", category, date_key)
                        # still prune from Firebase below
                    else:
                        row = SiteAnalyticsArchive(
                            category=category,
                            date_key=date_key,
                            event_count=event_count,
                            payload=snapshot,
                            size_bytes=size_bytes,
                        )
                        session.add(row)
                        await session.commit()
                        archived += 1
                        logger.debug(
                            "✅ Archived %s/%s — %d events, %d bytes",
                            category, date_key, event_count, size_bytes,
                        )
            except Exception as e:
                logger.error("❌ Postgres write for %s/%s failed: %s", category, date_key, e)
                continue  # skip prune — data not safely stored yet

            # ── prune from Firebase with retries ──
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    firebase_db.reference(fb_path).delete()
                    pruned += 1
                    break
                except Exception as e:
                    wait = INITIAL_BACKOFF_S * (2 ** (attempt - 1))
                    logger.warning(
                        "⚠️  Prune %s failed (attempt %d/%d): %s — retrying in %ds",
                        fb_path, attempt, MAX_RETRIES, e, wait,
                    )
                    await asyncio.sleep(wait)

    logger.info(
        "📦 Archive complete for %s — %d date/category pairs archived, %d pruned from RTDB",
        prefix, archived, pruned,
    )
    return {"archived": archived, "pruned": pruned}
