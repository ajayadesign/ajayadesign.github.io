"""
Tracking Sync — Firebase RTDB → PostgreSQL.

Reads open/click/unsubscribe events from Firebase RTDB (written by
the GitHub Pages tracking pages) and syncs them to PostgreSQL via
the existing record_open/record_click/record_unsubscribe functions.

Runs every 2 minutes via APScheduler.
"""

import logging

logger = logging.getLogger("outreach.tracking_sync")


async def sync_tracking_from_rtdb():
    """
    Pull tracking events from Firebase RTDB and process them.
    After processing, delete the events from RTDB to avoid re-processing.
    """
    try:
        import firebase_admin.db as firebase_db
    except Exception:
        return  # Firebase not available

    from api.services.email_tracker import record_open, record_click, record_unsubscribe

    processed = {"opens": 0, "clicks": 0, "unsubs": 0}

    # ── Process opens ──
    try:
        opens_ref = firebase_db.reference("tracking/opens")
        opens = opens_ref.get() or {}
        for key, event in opens.items():
            tracking_id = event.get("tracking_id")
            if not tracking_id:
                continue
            try:
                await record_open(tracking_id)
                processed["opens"] += 1
            except Exception as e:
                logger.warning("Failed to process open %s: %s", key, e)
            # Delete processed event
            try:
                opens_ref.child(key).delete()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Error reading RTDB opens: %s", e)

    # ── Process clicks ──
    try:
        clicks_ref = firebase_db.reference("tracking/clicks")
        clicks = clicks_ref.get() or {}
        for key, event in clicks.items():
            tracking_id = event.get("tracking_id")
            url = event.get("url", "")
            if not tracking_id:
                continue
            try:
                await record_click(tracking_id, url)
                processed["clicks"] += 1
            except Exception as e:
                logger.warning("Failed to process click %s: %s", key, e)
            # Delete processed event
            try:
                clicks_ref.child(key).delete()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Error reading RTDB clicks: %s", e)

    # ── Process unsubscribes ──
    try:
        unsubs_ref = firebase_db.reference("tracking/unsubscribes")
        unsubs = unsubs_ref.get() or {}
        for key, event in unsubs.items():
            tracking_id = event.get("tracking_id")
            if not tracking_id:
                continue
            try:
                await record_unsubscribe(tracking_id)
                processed["unsubs"] += 1
            except Exception as e:
                logger.warning("Failed to process unsub %s: %s", key, e)
            # Delete processed event
            try:
                unsubs_ref.child(key).delete()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Error reading RTDB unsubs: %s", e)

    total = sum(processed.values())
    if total > 0:
        logger.info(
            "Tracking sync: %d opens, %d clicks, %d unsubs",
            processed["opens"], processed["clicks"], processed["unsubs"],
        )
