"""
SMTP Provider Pool — Multi-provider email sending with quota rotation.

Aggregates free tiers from multiple SMTP providers to increase total
daily send capacity. Tracks per-provider quotas, resets at midnight,
and falls back to alternate providers when one is exhausted.
"""

import asyncio
import logging
import re
import smtplib
from datetime import date, datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import select, update

from api.config import settings
from api.database import async_session_factory
from api.models.smtp_provider import SmtpProvider

logger = logging.getLogger("outreach.smtp_pool")


async def pick_provider() -> SmtpProvider | None:
    """
    Select the best available SMTP provider:
    1. Reset daily_sent if last_reset != today
    2. Filter enabled providers with remaining quota
    3. Return highest-priority provider with lowest utilization
    """
    today = date.today()

    async with async_session_factory() as db:
        # Reset counts for any provider whose last_reset is before today
        await db.execute(
            update(SmtpProvider)
            .where(SmtpProvider.last_reset < today)
            .values(daily_sent=0, last_reset=today)
        )
        await db.commit()

        result = await db.execute(
            select(SmtpProvider)
            .where(
                SmtpProvider.enabled == True,  # noqa: E712
                SmtpProvider.daily_sent < SmtpProvider.daily_limit,
            )
            .order_by(
                SmtpProvider.priority.desc(),
                SmtpProvider.daily_sent.asc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


async def send_via_pool(
    to: str,
    subject: str,
    body_html: str,
    reply_to: str | None = None,
) -> dict:
    """
    Send email through the SMTP provider pool.
    Tries providers in priority order, falls back if one fails.
    Returns {"success": bool, "provider": str, "message": str, ...}
    """
    today = date.today()

    async with async_session_factory() as db:
        # Reset stale counts
        await db.execute(
            update(SmtpProvider)
            .where(SmtpProvider.last_reset < today)
            .values(daily_sent=0, last_reset=today)
        )
        await db.commit()

        # Get all available providers
        result = await db.execute(
            select(SmtpProvider)
            .where(
                SmtpProvider.enabled == True,  # noqa: E712
                SmtpProvider.daily_sent < SmtpProvider.daily_limit,
            )
            .order_by(
                SmtpProvider.priority.desc(),
                SmtpProvider.daily_sent.asc(),
            )
        )
        providers = result.scalars().all()

    if not providers:
        logger.warning("All SMTP providers exhausted for today")
        return {
            "success": False,
            "limit_exceeded": True,
            "message": "All SMTP providers have hit daily limits",
        }

    last_error = None
    for provider in providers:
        result = await _send_via_provider(provider, to, subject, body_html, reply_to)
        if result["success"]:
            # Increment the sent counter
            async with async_session_factory() as db:
                await db.execute(
                    update(SmtpProvider)
                    .where(SmtpProvider.id == provider.id)
                    .values(daily_sent=SmtpProvider.daily_sent + 1)
                )
                await db.commit()
            result["provider"] = provider.name
            result["provider_id"] = str(provider.id)
            return result

        last_error = result
        # If it was a bounce, don't try other providers
        if result.get("bounce"):
            result["provider"] = provider.name
            result["provider_id"] = str(provider.id)
            return result

        # If provider hit its limit, try next
        if result.get("limit_exceeded"):
            async with async_session_factory() as db:
                await db.execute(
                    update(SmtpProvider)
                    .where(SmtpProvider.id == provider.id)
                    .values(daily_sent=SmtpProvider.daily_limit)  # mark as exhausted
                )
                await db.commit()
            logger.warning("Provider %s hit limit, trying next", provider.name)
            continue

        # Other failure — try next provider
        logger.warning("Provider %s failed: %s — trying next", provider.name, result.get("message"))

    return last_error or {"success": False, "message": "All providers failed"}


def _sync_send(host: str, port: int, use_tls: bool, username: str, password: str,
               sender: str, to: str, raw_msg: str) -> None:
    """Blocking SMTP send — runs in a thread to avoid blocking the event loop."""
    if use_tls and port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            server.login(username, password)
            server.sendmail(sender, [to], raw_msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            server.login(username, password)
            server.sendmail(sender, [to], raw_msg)


async def _send_via_provider(
    provider: SmtpProvider,
    to: str,
    subject: str,
    body_html: str,
    reply_to: str | None = None,
) -> dict:
    """Send a single email through a specific SMTP provider."""
    sender = provider.from_email or settings.smtp_email
    sender_name = provider.from_name or settings.sender_name or "AjayaDesign"

    if not sender:
        return {"success": False, "message": f"No from_email for provider {provider.name}"}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{sender}>"
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Plain text fallback
    plain_text = re.sub(r"<[^>]+>", "", body_html.replace("<br>", "\n").replace("<br/>", "\n"))
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        await asyncio.to_thread(
            _sync_send, provider.host, provider.port, provider.use_tls,
            provider.username, provider.password, sender, to, msg.as_string(),
        )

        logger.info("✅ [%s] Email sent to %s: %s", provider.name, to, subject[:50])
        return {"success": True, "message": f"Sent via {provider.name}"}

    except smtplib.SMTPRecipientsRefused as e:
        codes = {code for _, (code, _) in e.recipients.items()}
        return {"success": False, "bounce": True, "message": f"Recipient refused ({codes}): {to}"}
    except smtplib.SMTPAuthenticationError as e:
        return {"success": False, "message": f"Auth failed for {provider.name}: {e}"}
    except smtplib.SMTPSenderRefused as e:
        msg_str = str(e).lower()
        if any(kw in msg_str for kw in ("limit", "quota", "too many")):
            return {"success": False, "limit_exceeded": True, "message": f"{provider.name} daily limit exceeded"}
        return {"success": False, "message": f"Sender refused ({provider.name}): {e}"}
    except smtplib.SMTPDataError as e:
        msg_str = str(e).lower()
        if any(kw in msg_str for kw in ("limit", "quota", "too many")):
            return {"success": False, "limit_exceeded": True, "message": f"{provider.name} daily limit exceeded"}
        return {"success": False, "message": f"SMTP data error ({provider.name}): {e}"}
    except Exception as e:
        msg_str = str(e).lower()
        if any(kw in msg_str for kw in ("daily limit", "quota exceeded", "too many", "rate limit")):
            return {"success": False, "limit_exceeded": True, "message": f"{provider.name} limit: {e}"}
        is_bounce = any(kw in msg_str for kw in (
            "does not exist", "user unknown", "no such user", "mailbox not found",
            "invalid recipient", "550 ", "551 ", "address rejected",
        ))
        if is_bounce:
            return {"success": False, "bounce": True, "message": f"Bounce via {provider.name}: {e}"}
        return {"success": False, "message": f"{provider.name} error: {e}"}


async def test_provider(provider_id: str) -> dict:
    """Test SMTP connection for a provider (sends test email to self)."""
    async with async_session_factory() as db:
        provider = await db.get(SmtpProvider, provider_id)
        if not provider:
            return {"success": False, "message": "Provider not found"}

    test_to = provider.from_email or settings.smtp_email
    if not test_to:
        return {"success": False, "message": "No test email address configured"}

    return await _send_via_provider(
        provider,
        to=test_to,
        subject=f"[Test] SMTP Provider: {provider.name}",
        body_html=f"<p>SMTP connection test for <strong>{provider.name}</strong> ({provider.host}:{provider.port}) successful.</p>",
    )


async def get_pool_status() -> dict:
    """Get aggregated pool status — total capacity, usage, per-provider breakdown."""
    today = date.today()

    async with async_session_factory() as db:
        # Reset stale counts
        await db.execute(
            update(SmtpProvider)
            .where(SmtpProvider.last_reset < today)
            .values(daily_sent=0, last_reset=today)
        )
        await db.commit()

        result = await db.execute(
            select(SmtpProvider).order_by(SmtpProvider.priority.desc())
        )
        providers = result.scalars().all()

    total_limit = sum(p.daily_limit for p in providers if p.enabled)
    total_sent = sum(p.daily_sent for p in providers if p.enabled)
    total_remaining = total_limit - total_sent

    return {
        "total_limit": total_limit,
        "total_sent": total_sent,
        "total_remaining": total_remaining,
        "provider_count": len([p for p in providers if p.enabled]),
        "providers": [p.to_dict() for p in providers],
    }
