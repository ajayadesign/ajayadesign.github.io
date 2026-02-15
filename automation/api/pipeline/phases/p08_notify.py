"""
Phase 8: Notifications — Telegram.
"""

import logging

from api.services.notify import send_telegram

logger = logging.getLogger(__name__)


async def notify(
    business_name: str,
    niche: str,
    goals: str,
    email: str,
    repo_full: str,
    live_url: str,
    page_count: int,
    *,
    log_fn=None,
) -> None:
    """Send build-complete notification via Telegram."""
    _log(log_fn, "📬 Sending Telegram notification")

    ok = await send_telegram(
        client_name=business_name,
        niche=niche,
        goals=goals,
        email=email,
        repo_full=repo_full,
        live_url=live_url,
        page_count=page_count,
    )

    _log(log_fn, "  ✅ Telegram notification sent" if ok else "  ⚠️ Telegram not sent (not configured or failed)")


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
