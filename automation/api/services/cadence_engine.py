"""
Cadence Engine — Sequence Scheduling & Sending.

Manages the 4-step outreach sequence: Initial → Value → Social Proof → Breakup,
plus optional Day-90 resurrection. Smart timing per industry. Uses the existing
email_service.py for actual SMTP delivery.

Phase 6 of OUTREACH_AGENT_PLAN.md (§8).
"""

import logging
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import Prospect, OutreachEmail, OutreachSequence

logger = logging.getLogger("outreach.cadence")

# ─── Send Windows (§8.2) ──────────────────────────────────────────────
# days: 0=Monday, 6=Sunday. hours: (start, end) in UTC
SEND_WINDOWS = {
    "restaurant":     {"days": [1, 2, 3], "hours": (15, 17)},    # Tue-Thu 9-11 CT
    "bakery":         {"days": [0, 1, 2], "hours": (15, 17)},    # Mon-Wed 9-11 CT
    "cafe":           {"days": [0, 1, 2], "hours": (15, 17)},
    "dental_office":  {"days": [1, 2, 3, 4], "hours": (13, 15)}, # Before patients
    "law_firm":       {"days": [0, 1, 2, 3, 4], "hours": (14, 16)},
    "plumber":        {"days": [0, 4], "hours": (23, 25)},       # Mon/Fri evening CT (wrap)
    "electrician":    {"days": [0, 4], "hours": (23, 25)},
    "roofing":        {"days": [0, 4], "hours": (23, 25)},
    "beauty_salon":   {"days": [0, 1], "hours": (14, 16)},
    "real_estate":    {"days": [1, 2, 3], "hours": (14, 16)},
    "veterinarian":   {"days": [1, 2, 3], "hours": (13, 15)},
    "auto_repair":    {"days": [0, 4], "hours": (23, 25)},
    "gym":            {"days": [0, 1], "hours": (14, 16)},
    "photographer":   {"days": [1, 2, 3], "hours": (15, 17)},
    "default":        {"days": [1, 2, 3], "hours": (15, 17)},    # Tue-Thu 9-11 CT
}

# Sequence step timing (days after previous step)
STEP_DELAYS = {1: 0, 2: 3, 3: 7, 4: 14, 5: 90}

# Max emails per day (anti-spam + warm-up)
MAX_DAILY_SENDS = 20


# ─── Timing Helpers ────────────────────────────────────────────────────

def get_next_send_time(business_type: str, after: Optional[datetime] = None) -> datetime:
    """
    Calculate the next valid send time for a given business type.
    Respects industry-specific send windows.
    """
    window = SEND_WINDOWS.get(business_type, SEND_WINDOWS["default"])
    now = after or datetime.now(timezone.utc)

    # Check each day starting from now
    for day_offset in range(8):  # At most look 7 days ahead
        candidate = now + timedelta(days=day_offset)
        if candidate.weekday() in window["days"]:
            start_h = window["hours"][0] % 24
            end_h = window["hours"][1] % 24
            if end_h == 0:
                end_h = 24

            # If same day and still in window
            if day_offset == 0 and start_h <= candidate.hour < end_h:
                return candidate.replace(minute=0, second=0, microsecond=0)

            # Schedule for start of window
            if day_offset > 0 or candidate.hour < start_h:
                return candidate.replace(
                    hour=start_h, minute=0, second=0, microsecond=0
                )

    # Fallback: tomorrow at 9 AM UTC
    return (now + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)


def is_in_send_window(business_type: str) -> bool:
    """Check if current time is in the send window for this business type."""
    window = SEND_WINDOWS.get(business_type, SEND_WINDOWS["default"])
    now = datetime.now(timezone.utc)
    start_h = window["hours"][0] % 24
    end_h = window["hours"][1] % 24
    if end_h == 0:
        end_h = 24
    return now.weekday() in window["days"] and start_h <= now.hour < end_h


# ─── Domain Blocklist (registrar, platform, chain, generic addresses) ──

_BLOCKED_EMAIL_DOMAINS = {
    "namebright.com", "godaddy.com", "homedepot.com", "square.site",
    "mysite.com", "key.me", "vagaro.com", "wix.com", "squarespace.com",
    "weebly.com", "wordpress.com", "shopify.com", "sentry.io",
}
_BLOCKED_EMAIL_PREFIXES = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "support", "postmaster", "mailer-daemon", "abuse",
}
_BLOCKED_BUSINESS_WORDS = {
    "home depot", "elementary school", "middle school", "high school",
    "walmart", "target", "starbucks", "mcdonalds", "dollar general",
    "dollar tree", "family dollar", "autozone", "walgreens", "cvs",
}


def _is_blocked_email(email: str) -> bool:
    """Return True if email goes to a registrar, platform, chain, etc."""
    email = (email or "").lower().strip()
    if not email or "@" not in email:
        return True
    local, domain = email.rsplit("@", 1)
    if domain in _BLOCKED_EMAIL_DOMAINS:
        return True
    if local in _BLOCKED_EMAIL_PREFIXES:
        return True
    return False


def _is_blocked_business(name: str) -> bool:
    """Return True if business name matches a chain/non-local entity."""
    name_lower = (name or "").lower()
    return any(w in name_lower for w in _BLOCKED_BUSINESS_WORDS)


# ─── Sequence Management ──────────────────────────────────────────────

async def enqueue_prospect(prospect_id: str) -> Optional[str]:
    """
    Enqueue a prospect for the outreach sequence.
    Creates the first email draft and schedules it.
    Returns the email ID or None.
    """
    from api.services.template_engine import compose_email

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return None

        # Guard: don't re-enqueue
        if prospect.status in ("contacted", "follow_up_1", "follow_up_2",
                                "follow_up_3", "replied", "meeting_booked",
                                "promoted", "dead", "do_not_contact"):
            logger.info("Skipping %s — already in state %s", prospect.business_name, prospect.status)
            return None

        if not prospect.owner_email:
            logger.warning("Cannot enqueue %s — no email", prospect.business_name)
            return None

        # Guard: block registrar/platform/chain emails
        if _is_blocked_email(prospect.owner_email):
            logger.warning("Blocked %s — bad email domain: %s", prospect.business_name, prospect.owner_email)
            prospect.status = "dead"
            await db.commit()
            return None

        if _is_blocked_business(prospect.business_name):
            logger.warning("Blocked %s — chain/non-local business", prospect.business_name)
            prospect.status = "dead"
            await db.commit()
            return None

        # Guard: prevent duplicate step-1 emails
        existing = await db.execute(
            select(OutreachEmail.id).where(
                OutreachEmail.prospect_id == prospect.id,
                OutreachEmail.sequence_step == 1,
            ).limit(1)
        )
        if existing.first():
            logger.info("Skipping %s — step 1 email already exists", prospect.business_name)
            if prospect.status != "queued":
                prospect.status = "queued"
                await db.commit()
            return None

        # Compose step 1
        composed = await compose_email(str(prospect.id), sequence_step=1)
        if not composed:
            logger.error("Failed to compose email for %s", prospect.business_name)
            return None

        # Schedule based on industry
        send_time = get_next_send_time(prospect.business_type or "default")

        # Create email record
        tracking_id = str(uuid4())
        email = OutreachEmail(
            id=uuid4(),
            prospect_id=prospect.id,
            sequence_step=1,
            subject=composed["subject"],
            body_html=composed["body_html"],
            body_text=composed["body_text"],
            personalization=composed["variables"],
            template_id=composed["template_id"],
            tracking_id=tracking_id,
            status="pending_approval",
            scheduled_for=send_time,
        )
        db.add(email)

        # Update prospect status — stays queued until operator approves
        prospect.status = "queued"
        await db.commit()

        logger.info(
            "Enqueued %s step 1 → scheduled for %s",
            prospect.business_name,
            send_time.isoformat(),
        )
        return str(email.id)


async def schedule_next_step(prospect_id: str, current_step: int) -> Optional[str]:
    """
    Schedule the next step in the sequence for a prospect.
    Called after successful send or after waiting period.
    """
    from api.services.template_engine import compose_email

    next_step = current_step + 1
    if next_step > 5:
        return None  # Sequence complete

    delay_days = STEP_DELAYS.get(next_step, 3)

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return None

        # Check exit conditions (§8.3)
        if prospect.status in ("replied", "meeting_booked", "promoted",
                                "dead", "do_not_contact"):
            logger.info("Not scheduling step %d for %s — status: %s",
                        next_step, prospect.business_name, prospect.status)
            return None

        # Step 5 (resurrection) — only if they opened any email
        if next_step == 5 and prospect.emails_opened == 0:
            logger.info("Skipping resurrection for %s — never opened", prospect.business_name)
            return None

        composed = await compose_email(str(prospect.id), sequence_step=next_step)
        if not composed:
            return None

        # Schedule
        after = datetime.now(timezone.utc) + timedelta(days=delay_days)
        send_time = get_next_send_time(prospect.business_type or "default", after=after)

        tracking_id = str(uuid4())
        email = OutreachEmail(
            id=uuid4(),
            prospect_id=prospect.id,
            sequence_step=next_step,
            subject=composed["subject"],
            body_html=composed["body_html"],
            body_text=composed["body_text"],
            personalization=composed["variables"],
            template_id=composed["template_id"],
            tracking_id=tracking_id,
            status="pending_approval",
            scheduled_for=send_time,
        )
        db.add(email)

        # Update prospect status
        step_status_map = {2: "follow_up_1", 3: "follow_up_2", 4: "follow_up_3", 5: "follow_up_3"}
        prospect.status = step_status_map.get(next_step, prospect.status)
        await db.commit()

        logger.info(
            "Scheduled %s step %d → %s",
            prospect.business_name,
            next_step,
            send_time.isoformat(),
        )
        return str(email.id)


async def send_email_record(email_id: str) -> bool:
    """
    Send a scheduled email via SMTP.
    Updates status and tracking, notifies via Telegram.
    """
    from api.services.email_service import send_email as smtp_send
    from api.services.telegram_outreach import send_message
    from api.services.firebase_summarizer import _safe_set
    from api.services.email_tracker import inject_tracking

    async with async_session_factory() as db:
        email = await db.get(OutreachEmail, email_id)
        if not email:
            return False

        prospect = await db.get(Prospect, email.prospect_id)
        if not prospect or not prospect.owner_email:
            email.status = "failed"
            email.error_message = "No recipient email"
            await db.commit()
            return False

        # Inject tracking pixel + click tracking
        tracked_html = inject_tracking(
            email.body_html,
            email.tracking_id,
        )

        try:
            # Use existing email_service.py
            result = await smtp_send(
                to=prospect.owner_email,
                subject=email.subject,
                body_html=tracked_html,
                reply_to=settings.smtp_email,
            )

            email.status = "sent"
            email.sent_at = datetime.now(timezone.utc)
            email.message_id = result.get("message_id") if isinstance(result, dict) else None

            # Update prospect tracking
            prospect.emails_sent = (prospect.emails_sent or 0) + 1
            prospect.last_email_at = email.sent_at
            if prospect.status == "queued":
                prospect.status = "contacted"

            await db.commit()

            # Notify
            await send_message(
                f"📧 Sent to *{prospect.business_name}*\n"
                f"📋 Step {email.sequence_step}: {email.subject[:50]}...\n"
                f"📬 To: {prospect.owner_email}"
            )

            await _safe_set("outreach/stats/last_send", {
                "name": prospect.business_name,
                "step": email.sequence_step,
                "ts": int(_time.time()),
            })

            # Schedule next step
            await schedule_next_step(str(prospect.id), email.sequence_step)

            logger.info("Sent email %s to %s", email_id, prospect.owner_email)
            return True

        except Exception as e:
            email.status = "failed"
            email.error_message = str(e)[:500]
            await db.commit()

            logger.error("Send failed for %s: %s", prospect.business_name, e)
            return False


# ─── Batch Sending (Main Scheduler Entry Point) ──────────────────────

async def process_send_queue() -> dict:
    """
    Process pending emails in the send queue.
    Called periodically by APScheduler. Respects daily limits and send windows.
    Returns stats dict.
    """
    stats = {"attempted": 0, "sent": 0, "failed": 0, "skipped": 0}
    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        # Count already sent today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_count_result = await db.execute(
            select(func.count(OutreachEmail.id))
            .where(
                OutreachEmail.status == "sent",
                OutreachEmail.sent_at >= today_start,
            )
        )
        today_count = today_count_result.scalar() or 0

        remaining = MAX_DAILY_SENDS - today_count
        if remaining <= 0:
            logger.info("Daily send limit reached (%d sent today)", today_count)
            stats["skipped"] = remaining
            return stats

        # Only send emails that have been explicitly approved by the operator
        result = await db.execute(
            select(OutreachEmail)
            .where(
                OutreachEmail.status == "approved",
                OutreachEmail.scheduled_for <= now,
            )
            .order_by(OutreachEmail.scheduled_for)
            .limit(remaining)
        )
        emails = result.scalars().all()

    for email in emails:
        stats["attempted"] += 1
        success = await send_email_record(str(email.id))
        if success:
            stats["sent"] += 1
        else:
            stats["failed"] += 1

        # Rate limit between sends (2 seconds)
        import asyncio
        await asyncio.sleep(2)

    logger.info(
        "Send queue processed: %d attempted, %d sent, %d failed",
        stats["attempted"], stats["sent"], stats["failed"],
    )
    return stats


async def handle_bounce(email_id: str):
    """
    Handle a bounced email. Mark prospect, try alternate email if available.
    """
    from api.services.telegram_outreach import send_message

    async with async_session_factory() as db:
        email = await db.get(OutreachEmail, email_id)
        if not email:
            return

        email.status = "bounced"
        prospect = await db.get(Prospect, email.prospect_id)
        if prospect:
            # Cancel all future emails in sequence
            future = await db.execute(
                select(OutreachEmail)
                .where(
                    OutreachEmail.prospect_id == prospect.id,
                    OutreachEmail.status == "scheduled",
                )
            )
            for fe in future.scalars().all():
                fe.status = "cancelled"

            prospect.status = "dead"
            prospect.notes = (prospect.notes or "") + f"\nBounced: {email.subject}"

            await send_message(
                f"📬 *Bounce:* {prospect.owner_email}\n"
                f"📋 {prospect.business_name} — marked dead"
            )

        await db.commit()


async def handle_unsubscribe(prospect_id: str):
    """Mark prospect as do_not_contact and cancel all pending emails."""
    from api.services.telegram_outreach import send_message

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return

        prospect.status = "do_not_contact"

        # Cancel all scheduled emails
        result = await db.execute(
            select(OutreachEmail)
            .where(
                OutreachEmail.prospect_id == prospect.id,
                OutreachEmail.status == "scheduled",
            )
        )
        for email in result.scalars().all():
            email.status = "cancelled"

        await db.commit()

        await send_message(
            f"🚫 *Unsubscribe:* {prospect.business_name}\n"
            f"📧 {prospect.owner_email} — marked do_not_contact"
        )


async def get_queue_status() -> dict:
    """Get current queue status for dashboard / Telegram /queue command."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async with async_session_factory() as db:
        # Pending
        pending_r = await db.execute(
            select(func.count(OutreachEmail.id))
            .where(OutreachEmail.status == "scheduled")
        )
        pending = pending_r.scalar() or 0

        # Sent today
        sent_r = await db.execute(
            select(func.count(OutreachEmail.id))
            .where(
                OutreachEmail.status == "sent",
                OutreachEmail.sent_at >= today_start,
            )
        )
        sent_today = sent_r.scalar() or 0

        # Failed today
        failed_r = await db.execute(
            select(func.count(OutreachEmail.id))
            .where(
                OutreachEmail.status == "failed",
                OutreachEmail.sent_at >= today_start,
            )
        )
        failed_today = failed_r.scalar() or 0

    return {
        "pending": pending,
        "sent_today": sent_today,
        "failed_today": failed_today,
        "daily_limit": MAX_DAILY_SENDS,
        "remaining": max(0, MAX_DAILY_SENDS - sent_today),
    }


async def batch_enqueue_prospects(limit: int = 10) -> int:
    """
    Enqueue up to `limit` enriched prospects into the send pipeline.
    Called by scheduler. Returns count of newly enqueued.
    """
    async with async_session_factory() as db:
        result = await db.execute(
            select(Prospect.id)
            .where(
                Prospect.status == "enriched",
                Prospect.owner_email.isnot(None),
            )
            .order_by(Prospect.priority_score.desc())
            .limit(limit)
        )
        prospect_ids = [str(r[0]) for r in result.fetchall()]

    count = 0
    for pid in prospect_ids:
        email_id = await enqueue_prospect(pid)
        if email_id:
            count += 1

    return count
