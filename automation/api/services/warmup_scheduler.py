"""
Email Warm-Up Scheduler — Gradual sending ramp-up per address.

Protects sender reputation by enforcing daily send limits that increase
over a 29-day warm-up period. Emails exceeding the daily cap are queued
for the next business day automatically.

Usage:
    from api.services.warmup_scheduler import can_send_today, record_send

    ok, info = await can_send_today("outreach@ajayadesign.com")
    if not ok:
        # queue for tomorrow
        ...
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Column, Date, DateTime, Integer, String, select, update
from sqlalchemy.dialects.postgresql import UUID

from api.database import Base, async_session_factory

logger = logging.getLogger("outreach.warmup")


# ── Warm-up schedule ──────────────────────────────────────────────
# Maps (min_day, max_day) → daily send limit
WARMUP_TIERS = [
    (1, 3, 5),
    (4, 7, 10),
    (8, 14, 20),
    (15, 21, 50),
    (22, 28, 100),
    (29, None, 200),  # cap for cold outreach — never exceed
]

MAX_COLD_DAILY = 200


def daily_limit_for_day(day_number: int) -> int:
    """Return the max emails/day for a given warm-up day number (1-indexed)."""
    for lo, hi, limit in WARMUP_TIERS:
        if hi is None or lo <= day_number <= hi:
            return limit
    return MAX_COLD_DAILY


# ── DB model ──────────────────────────────────────────────────────
class SenderWarmup(Base):
    """Tracks warm-up state and daily send counts per sending address."""

    __tablename__ = "sender_warmup"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_email = Column(String, nullable=False, unique=True, index=True)
    warmup_start_date = Column(Date, nullable=False, default=date.today)
    daily_sent = Column(Integer, nullable=False, default=0)
    last_reset_date = Column(Date, nullable=False, default=date.today)
    total_sent = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def warmup_day(self, today: date | None = None) -> int:
        """1-indexed day number since warm-up started."""
        today = today or date.today()
        return max((today - self.warmup_start_date).days + 1, 1)

    def current_limit(self, today: date | None = None) -> int:
        return daily_limit_for_day(self.warmup_day(today))

    def remaining(self, today: date | None = None) -> int:
        return max(self.current_limit(today) - self.daily_sent, 0)


# ── Public API ────────────────────────────────────────────────────
async def get_or_create_warmup(sender_email: str) -> SenderWarmup:
    """Get or create a warm-up record for a sender address."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(SenderWarmup).where(SenderWarmup.sender_email == sender_email)
        )
        warmup = result.scalar_one_or_none()

        if warmup is None:
            warmup = SenderWarmup(
                sender_email=sender_email,
                warmup_start_date=date.today(),
                daily_sent=0,
                last_reset_date=date.today(),
            )
            db.add(warmup)
            await db.commit()
            await db.refresh(warmup)
            logger.info("Created warm-up tracker for %s (day 1, limit 5/day)", sender_email)

        # Reset daily count if new day
        today = date.today()
        if warmup.last_reset_date < today:
            warmup.daily_sent = 0
            warmup.last_reset_date = today
            await db.commit()
            await db.refresh(warmup)

        return warmup


async def can_send_today(sender_email: str) -> tuple[bool, dict]:
    """
    Check if the sender can send another email today.

    Returns:
        (allowed, info_dict) where info_dict contains:
        - warmup_day, daily_limit, daily_sent, remaining
    """
    warmup = await get_or_create_warmup(sender_email)
    today = date.today()
    info = {
        "warmup_day": warmup.warmup_day(today),
        "daily_limit": warmup.current_limit(today),
        "daily_sent": warmup.daily_sent,
        "remaining": warmup.remaining(today),
        "warmup_start_date": warmup.warmup_start_date.isoformat(),
    }
    allowed = warmup.remaining(today) > 0
    if not allowed:
        logger.info(
            "Warm-up limit reached for %s: day %d, sent %d/%d",
            sender_email, info["warmup_day"], info["daily_sent"], info["daily_limit"],
        )
    return allowed, info


async def record_send(sender_email: str) -> dict:
    """
    Record that an email was sent. Call after successful send.
    Returns updated info dict.
    """
    async with async_session_factory() as db:
        result = await db.execute(
            select(SenderWarmup).where(SenderWarmup.sender_email == sender_email)
        )
        warmup = result.scalar_one_or_none()
        if warmup is None:
            warmup = await get_or_create_warmup(sender_email)
            result = await db.execute(
                select(SenderWarmup).where(SenderWarmup.sender_email == sender_email)
            )
            warmup = result.scalar_one()

        today = date.today()
        if warmup.last_reset_date < today:
            warmup.daily_sent = 0
            warmup.last_reset_date = today

        warmup.daily_sent += 1
        warmup.total_sent += 1
        await db.commit()

        return {
            "warmup_day": warmup.warmup_day(today),
            "daily_limit": warmup.current_limit(today),
            "daily_sent": warmup.daily_sent,
            "remaining": warmup.remaining(today),
            "total_sent": warmup.total_sent,
        }


async def get_warmup_status(sender_email: str | None = None) -> list[dict]:
    """Get warm-up status for one or all senders."""
    async with async_session_factory() as db:
        q = select(SenderWarmup)
        if sender_email:
            q = q.where(SenderWarmup.sender_email == sender_email)
        result = await db.execute(q)
        warmups = result.scalars().all()

    today = date.today()
    return [
        {
            "sender_email": w.sender_email,
            "warmup_start_date": w.warmup_start_date.isoformat(),
            "warmup_day": w.warmup_day(today),
            "daily_limit": w.current_limit(today),
            "daily_sent": w.daily_sent,
            "remaining": w.remaining(today),
            "total_sent": w.total_sent,
        }
        for w in warmups
    ]
