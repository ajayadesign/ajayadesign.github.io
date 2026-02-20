"""
Email Tracker — Open, Click & Unsubscribe tracking via Firebase RTDB.

Tracking pages are hosted on GitHub Pages (ajayadesign.github.io/track/).
They write events to Firebase RTDB; a pipeline worker syncs them to PostgreSQL.

Also keeps local API-based tracking routes as fallback for dev/testing.
"""

import base64
import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote, unquote, urlencode

from api.config import settings

logger = logging.getLogger("outreach.tracker")

# 1x1 transparent PNG (43 bytes) — still used by local /track/open/ route
TRACKING_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
    "Nl7BcQAAAABJRU5ErkJggg=="
)

# GitHub Pages base — tracking pages are static HTML + Firebase JS SDK
TRACKING_BASE = "https://ajayadesign.github.io"

# Links that should NEVER be rewritten through the click tracker
_SKIP_DOMAINS = [
    "ajayadesign.github.io",   # our own portfolio site
]


def get_tracking_pixel_url(tracking_id: str) -> str:
    """Build the tracking pixel URL — uses open.html page that writes to RTDB."""
    return f"{TRACKING_BASE}/track/open.html?t={tracking_id}"


def get_click_tracking_url(tracking_id: str, destination: str) -> str:
    """Build a click-tracking redirect URL via GitHub Pages."""
    return f"{TRACKING_BASE}/track/click.html?t={tracking_id}&url={quote(destination)}"


def get_unsubscribe_url(tracking_id: str) -> str:
    """Build the unsubscribe URL via GitHub Pages."""
    return f"{TRACKING_BASE}/track/unsubscribe.html?t={tracking_id}"


def inject_tracking(body_html: str, tracking_id: str) -> str:
    """
    Inject tracking into an HTML email body.
    - Replaces {{tracking_pixel_url}} and {{unsubscribe_url}} placeholders
    - Rewrites <a href="..."> to go through click tracker
    - Skips mailto:, tel:, our own domain, and tracking links
    """
    if not tracking_id:
        return body_html

    pixel_url = get_tracking_pixel_url(tracking_id)
    unsub_url = get_unsubscribe_url(tracking_id)

    # Replace template placeholders (non-Jinja tokens so Jinja2 doesn't eat them)
    result = body_html.replace("__TRACKING_PIXEL_URL__", pixel_url)
    result = result.replace("__UNSUBSCRIBE_URL__", unsub_url)
    # Legacy Jinja-style placeholders (backwards compat)
    result = result.replace("{{ tracking_pixel_url }}", pixel_url)
    result = result.replace("{{tracking_pixel_url}}", pixel_url)
    result = result.replace("{{ unsubscribe_url }}", unsub_url)
    result = result.replace("{{unsubscribe_url}}", unsub_url)

    # Rewrite links for click tracking
    def rewrite_link(match):
        full_match = match.group(0)
        href = match.group(1)

        # Skip non-http links
        if any(href.startswith(p) for p in ["mailto:", "tel:", "#"]):
            return full_match

        # Skip our own domain (portfolio link) and tracking links
        if any(skip in href for skip in _SKIP_DOMAINS):
            return full_match

        # Skip links already going through tracker
        if "/track/" in href or tracking_id in href:
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
