"""
Email Tracker — Open Pixel & Click Redirect.

Provides open tracking (1x1 transparent PNG) and click tracking (URL redirect).
Also handles unsubscribe link generation.

Phase 6 of OUTREACH_AGENT_PLAN.md.
"""

import base64
import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote, unquote, urlencode

from api.config import settings

logger = logging.getLogger("outreach.tracker")

# 1x1 transparent PNG (43 bytes)
TRACKING_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
    "Nl7BcQAAAABJRU5ErkJggg=="
)

# Base URL for tracking endpoints
TRACKING_BASE = settings.tracking_base_url or "http://localhost:3001/api/v1"


def get_tracking_pixel_url(tracking_id: str) -> str:
    """Build the tracking pixel URL for an email."""
    return f"{TRACKING_BASE}/track/open/{tracking_id}.png"


def get_click_tracking_url(tracking_id: str, destination: str) -> str:
    """Build a click-tracking redirect URL."""
    return f"{TRACKING_BASE}/track/click/{tracking_id}?url={quote(destination)}"


def get_unsubscribe_url(tracking_id: str) -> str:
    """Build the unsubscribe URL."""
    return f"{TRACKING_BASE}/track/unsubscribe/{tracking_id}"


def inject_tracking(body_html: str, tracking_id: str) -> str:
    """
    Inject tracking pixel and rewrite links in an HTML email body.
    - Adds 1x1 pixel before </body>
    - Rewrites <a href="..."> to go through click tracker
    - Replaces {{tracking_pixel_url}} and {{unsubscribe_url}} placeholders
    """
    if not tracking_id:
        return body_html

    pixel_url = get_tracking_pixel_url(tracking_id)
    unsub_url = get_unsubscribe_url(tracking_id)

    # Replace template placeholders
    result = body_html.replace("{{ tracking_pixel_url }}", pixel_url)
    result = result.replace("{{tracking_pixel_url}}", pixel_url)
    result = result.replace("{{ unsubscribe_url }}", unsub_url)
    result = result.replace("{{unsubscribe_url}}", unsub_url)

    # Rewrite links for click tracking (but not mailto:, tel:, unsubscribe, or pixel)
    def rewrite_link(match):
        full_match = match.group(0)
        href = match.group(1)

        # Skip certain links
        if any(skip in href for skip in [
            "mailto:", "tel:", "/track/", "unsubscribe",
            tracking_id, ".png",
        ]):
            return full_match

        tracked_href = get_click_tracking_url(tracking_id, href)
        return full_match.replace(href, tracked_href)

    result = re.sub(r'href="([^"]+)"', rewrite_link, result)

    return result


async def record_open(tracking_id: str) -> bool:
    """
    Record an email open event.
    Updates OutreachEmail + Prospect models, notifies via Telegram.
    """
    from api.database import async_session_factory
    from api.models.prospect import OutreachEmail, Prospect
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(OutreachEmail).where(OutreachEmail.tracking_id == tracking_id)
        )
        email = result.scalar_one_or_none()
        if not email:
            logger.warning("Open: unknown tracking_id %s", tracking_id)
            return False

        now = datetime.now(timezone.utc)

        # Update email
        if not email.opened_at:
            email.opened_at = now
        email.open_count = (email.open_count or 0) + 1

        # Update prospect
        prospect = await db.get(Prospect, email.prospect_id)
        if prospect:
            prospect.emails_opened = (prospect.emails_opened or 0) + 1
            prospect.last_opened_at = now

        await db.commit()

        # Telegram notification on first open
        if email.open_count == 1 and prospect:
            from api.services.telegram_outreach import send_message
            await send_message(
                f"👀 *{prospect.business_name}* opened your email!\n"
                f"📋 Step {email.sequence_step}: {email.subject[:50]}..."
            )

        logger.info("Open recorded: %s (count: %d)", tracking_id, email.open_count)
        return True


async def record_click(tracking_id: str, url: str) -> bool:
    """
    Record a link click event.
    Updates OutreachEmail + Prospect models.
    """
    from api.database import async_session_factory
    from api.models.prospect import OutreachEmail, Prospect
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(OutreachEmail).where(OutreachEmail.tracking_id == tracking_id)
        )
        email = result.scalar_one_or_none()
        if not email:
            return False

        now = datetime.now(timezone.utc)

        # Update email
        if not email.clicked_at:
            email.clicked_at = now
        email.click_count = (email.click_count or 0) + 1
        email.clicked_links = (email.clicked_links or []) + [{"url": url, "ts": now.isoformat()}]

        # Update prospect
        prospect = await db.get(Prospect, email.prospect_id)
        if prospect:
            prospect.emails_clicked = (prospect.emails_clicked or 0) + 1
            prospect.last_clicked_at = now

        await db.commit()

        # Telegram on first click
        if email.click_count == 1 and prospect:
            from api.services.telegram_outreach import send_message
            await send_message(
                f"🔗 *{prospect.business_name}* clicked a link!\n"
                f"📋 Step {email.sequence_step}\n"
                f"🌐 URL: {url[:80]}"
            )

        logger.info("Click recorded: %s → %s", tracking_id, url[:80])
        return True


async def record_unsubscribe(tracking_id: str) -> bool:
    """
    Handle unsubscribe request.
    Marks prospect as do_not_contact, cancels all pending emails.
    """
    from api.database import async_session_factory
    from api.models.prospect import OutreachEmail, Prospect
    from api.services.cadence_engine import handle_unsubscribe
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(OutreachEmail).where(OutreachEmail.tracking_id == tracking_id)
        )
        email = result.scalar_one_or_none()
        if not email:
            return False

        prospect_id = str(email.prospect_id)

    await handle_unsubscribe(prospect_id)
    return True
