"""
AjayaDesign Automation — IMAP Bounce Checker.

Connects to Gmail via IMAP, searches for bounce/undeliverable
notifications (NDRs), parses out the failed recipient email,
and updates the corresponding OutreachEmail record → "bounced".

Runs on APScheduler every 5 minutes + on-demand via API.
Uses the same SMTP_EMAIL / SMTP_APP_PASSWORD credentials (Gmail
app passwords work for both SMTP and IMAP).
"""

import asyncio
import email
import email.policy
import imaplib
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select, and_

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import Prospect, OutreachEmail

logger = logging.getLogger("outreach.bounce_checker")

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Senders of bounce notifications
BOUNCE_SENDERS = [
    "mailer-daemon@googlemail.com",
    "mailer-daemon@google.com",
    "postmaster@",
    "MAILER-DAEMON",
]

# Subject patterns indicating a bounce
BOUNCE_SUBJECT_PATTERNS = [
    r"delivery status notification",
    r"undeliverable",
    r"undelivered mail",
    r"mail delivery failed",
    r"returned mail",
    r"failure notice",
    r"delivery failure",
    r"delivery has failed",
    r"address not found",
    r"message not delivered",
    r"could not be delivered",
]

# Body patterns to extract the bounced email address
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Patterns in body confirming this is a bounce
BOUNCE_BODY_KEYWORDS = [
    "address not found",
    "does not exist",
    "user unknown",
    "mailbox not found",
    "mailbox unavailable",
    "no such user",
    "recipient rejected",
    "550 ",
    "551 ",
    "552 ",
    "553 ",
    "554 ",
    "wasn't found at",
    "couldn't be delivered",
    "could not be delivered",
    "delivery has failed",
    "permanent failure",
    "message delivery to",
]


def _connect_imap():
    """Connect and authenticate to Gmail IMAP."""
    imap_user = settings.smtp_email
    imap_pass = settings.smtp_app_password
    if not imap_user or not imap_pass:
        raise RuntimeError("SMTP_EMAIL / SMTP_APP_PASSWORD not configured")

    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(imap_user, imap_pass)
    return conn


def _is_bounce_subject(subject: str) -> bool:
    """Check if email subject matches bounce patterns."""
    subj_lower = (subject or "").lower()
    return any(re.search(p, subj_lower) for p in BOUNCE_SUBJECT_PATTERNS)


def _extract_bounced_emails(msg) -> list[str]:
    """
    Extract the bounced recipient email addresses from a bounce notification.
    Checks:
    1. DSN (message/delivery-status) parts
    2. Plain-text body for email addresses near bounce keywords
    """
    bounced = set()

    # Walk all parts
    full_text = ""
    for part in msg.walk():
        ctype = part.get_content_type()

        # DSN delivery-status part — structured, reliable
        if ctype == "message/delivery-status":
            payload = part.get_payload()
            if isinstance(payload, list):
                for dsn_part in payload:
                    dsn_text = str(dsn_part)
                    # Look for "Final-Recipient: rfc822; user@example.com"
                    for m in re.finditer(
                        r"Final-Recipient:\s*rfc822;\s*([\w.+-]+@[\w-]+\.[\w.-]+)",
                        dsn_text, re.IGNORECASE,
                    ):
                        bounced.add(m.group(1).lower())
                    # Also "Original-Recipient"
                    for m in re.finditer(
                        r"Original-Recipient:\s*rfc822;\s*([\w.+-]+@[\w-]+\.[\w.-]+)",
                        dsn_text, re.IGNORECASE,
                    ):
                        bounced.add(m.group(1).lower())

        # Collect plain text for keyword search
        if ctype in ("text/plain", "text/html"):
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    full_text += payload.decode("utf-8", errors="replace") + "\n"
            except Exception:
                pass

    # If DSN gave us results, use those
    if bounced:
        return list(bounced)

    # Fallback: search plain text for email addresses near bounce keywords
    text_lower = full_text.lower()
    has_bounce_keyword = any(kw in text_lower for kw in BOUNCE_BODY_KEYWORDS)
    if has_bounce_keyword:
        # Find all email addresses in the body
        all_emails = EMAIL_PATTERN.findall(full_text)
        # Filter out our own address and common system addresses
        our_addr = (settings.smtp_email or "").lower()
        for addr in all_emails:
            addr_lower = addr.lower()
            if addr_lower == our_addr:
                continue
            if any(x in addr_lower for x in [
                "mailer-daemon", "postmaster", "noreply", "no-reply",
                "google.com", "googlemail.com", "gmail.com",
            ]):
                continue
            bounced.add(addr_lower)

    return list(bounced)


def _sync_scan_bounces() -> list[dict]:
    """
    Blocking IMAP scan for bounces — runs in a thread.
    Returns list of {addr, subject} dicts.
    """
    from datetime import timedelta as _td

    conn = _connect_imap()
    try:
        conn.select("INBOX")
        since_date = (datetime.now() - _td(days=7)).strftime("%d-%b-%Y")
        search_queries = [
            f'(FROM "mailer-daemon" SINCE {since_date})',
            f'(FROM "postmaster" SINCE {since_date})',
            f'(SUBJECT "Delivery Status Notification" SINCE {since_date})',
            f'(SUBJECT "undeliverable" SINCE {since_date})',
            f'(SUBJECT "Mail delivery failed" SINCE {since_date})',
            f'(SUBJECT "delivery failure" SINCE {since_date})',
        ]

        all_msg_ids = set()
        for query in search_queries:
            try:
                status, data = conn.search(None, query)
                if status == "OK" and data[0]:
                    all_msg_ids.update(data[0].split())
            except Exception:
                pass

        hits = []
        for msg_id in all_msg_ids:
            try:
                status, msg_data = conn.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw, policy=email.policy.default)
                subject = msg.get("Subject", "")
                from_addr = msg.get("From", "")

                is_bounce = False
                if any(s.lower() in from_addr.lower() for s in BOUNCE_SENDERS):
                    is_bounce = True
                if _is_bounce_subject(subject):
                    is_bounce = True
                if not is_bounce:
                    continue

                addrs = _extract_bounced_emails(msg)
                for addr in addrs:
                    hits.append({"addr": addr, "subject": subject})

                conn.store(msg_id, "+FLAGS", "\\Seen")
            except Exception:
                pass

        conn.close()
        conn.logout()
        return hits
    except Exception:
        try:
            conn.logout()
        except Exception:
            pass
        raise


async def check_bounces() -> dict:
    """
    Main entry point: scan Gmail inbox for bounce notifications,
    update OutreachEmail records, and call handle_bounce() for each.

    Returns summary dict: {checked, bounced, already_bounced, not_found, errors}
    """
    result = {
        "checked": 0,
        "bounced": 0,
        "already_bounced": 0,
        "not_found": 0,
        "errors": [],
        "details": [],
    }

    # Phase 1: All IMAP work in a thread (no event loop blocking)
    try:
        hits = await asyncio.to_thread(_sync_scan_bounces)
    except Exception as e:
        logger.error("IMAP bounce scan failed: %s", e)
        result["errors"].append(f"IMAP scan failed: {e}")
        return result

    if not hits:
        logger.info("Bounce check: no new bounce notifications found")
        return result

    logger.info("Bounce check: found %d potential bounced addresses", len(hits))

    # Phase 2: Process results with async DB
    from api.services.cadence_engine import handle_bounce

    for hit in hits:
        addr, subject = hit["addr"], hit["subject"]
        result["checked"] += 1
        try:
            async with async_session_factory() as db:
                email_row = (
                    await db.execute(
                        select(OutreachEmail)
                        .join(Prospect)
                        .where(
                            and_(
                                Prospect.owner_email == addr,
                                OutreachEmail.status == "sent",
                            )
                        )
                        .order_by(OutreachEmail.sent_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                if not email_row:
                    logger.debug("Bounce for %s — no matching sent email found", addr)
                    result["not_found"] += 1
                    continue

                if email_row.status == "bounced":
                    result["already_bounced"] += 1
                    continue

                email_row.status = "bounced"
                email_row.error_message = (
                    f"Async bounce detected via IMAP: {subject}"
                )[:500]
                email_id = str(email_row.id)
                prospect_id = email_row.prospect_id
                await db.commit()

            try:
                await handle_bounce(email_id)
            except Exception as e:
                logger.error("handle_bounce failed for %s: %s", email_id, e)

            async with async_session_factory() as db:
                prospect = await db.get(Prospect, prospect_id)
            biz_name = prospect.business_name if prospect else "Unknown"
            result["bounced"] += 1
            result["details"].append({
                "email": addr,
                "business": biz_name,
                "email_id": email_id,
            })
            logger.info("📬 Bounce detected: %s (%s) — marked bounced", addr, biz_name)

        except Exception as e:
            logger.error("Error processing bounce for %s: %s", addr, e)
            result["errors"].append(str(e))

    logger.info(
        "Bounce check complete: checked=%d bounced=%d already=%d not_found=%d",
        result["checked"], result["bounced"],
        result["already_bounced"], result["not_found"],
    )
    return result


# ═══════════════════════════════════════════════════════════════════
# Reply Detection — scan inbox for replies from prospects
# ═══════════════════════════════════════════════════════════════════

def _sync_scan_replies(addrs_to_check: list[str], since_date: str) -> list[str]:
    """
    Blocking IMAP scan for replies — runs in a thread.
    Returns list of email addresses that have replied.
    """
    conn = _connect_imap()
    try:
        conn.select("INBOX")
        replied = []
        for addr in addrs_to_check:
            try:
                query = f'(FROM "{addr}" SINCE {since_date})'
                status_code, data = conn.search(None, query)
                if status_code == "OK" and data[0] and data[0].split():
                    replied.append(addr)
            except Exception:
                pass
        conn.close()
        conn.logout()
        return replied
    except Exception:
        try:
            conn.logout()
        except Exception:
            pass
        raise


async def check_replies() -> dict:
    """
    Scan Gmail inbox for replies from prospects we've emailed.
    When a reply is found, mark the prospect as 'manual_handling'
    and cancel all pending automated emails.

    Returns summary: {checked, replies_found, already_handled, details}
    """
    result = {
        "checked": 0,
        "replies_found": 0,
        "already_handled": 0,
        "details": [],
        "errors": [],
    }

    # Phase 1: Get prospect map from DB
    async with async_session_factory() as db:
        sent_r = await db.execute(
            select(Prospect.owner_email, Prospect.id, Prospect.business_name, Prospect.status)
            .join(OutreachEmail)
            .where(OutreachEmail.status == "sent")
            .distinct()
        )
        prospect_map = {}
        for row in sent_r.fetchall():
            addr = (row[0] or "").lower().strip()
            if addr:
                prospect_map[addr] = {
                    "id": str(row[1]),
                    "name": row[2],
                    "status": row[3],
                }

    if not prospect_map:
        return result

    # Filter to only addresses worth checking
    addrs_to_check = [
        addr for addr, info in prospect_map.items()
        if info["status"] not in (
            "manual_handling", "replied", "meeting_booked",
            "promoted", "dead", "do_not_contact",
        )
    ]
    if not addrs_to_check:
        return result

    # Phase 2: All IMAP work in a thread (no event loop blocking)
    from datetime import timedelta as _td
    since_date = (datetime.now() - _td(days=14)).strftime("%d-%b-%Y")

    try:
        replied_addrs = await asyncio.to_thread(_sync_scan_replies, addrs_to_check, since_date)
    except Exception as e:
        logger.error("IMAP reply scan failed: %s", e)
        result["errors"].append(f"IMAP scan failed: {e}")
        return result

    # Phase 3: Process replies with async DB
    for addr in replied_addrs:
        info = prospect_map.get(addr)
        if not info:
            continue

        result["checked"] += 1

        try:
            async with async_session_factory() as db:
                prospect = await db.get(Prospect, info["id"])
                if not prospect:
                    continue

                if prospect.status == "manual_handling":
                    result["already_handled"] += 1
                    continue

                old_status = prospect.status
                prospect.status = "manual_handling"
                prospect.notes = (prospect.notes or "") + (
                    f"\n📩 Reply detected via IMAP — auto-set to manual_handling (was {old_status})"
                )

                latest_email_r = await db.execute(
                    select(OutreachEmail)
                    .where(
                        OutreachEmail.prospect_id == prospect.id,
                        OutreachEmail.status == "sent",
                    )
                    .order_by(OutreachEmail.sent_at.desc())
                    .limit(1)
                )
                latest_email = latest_email_r.scalar_one_or_none()
                if latest_email:
                    latest_email.replied_at = datetime.now(timezone.utc)

                pending_r = await db.execute(
                    select(OutreachEmail).where(
                        OutreachEmail.prospect_id == prospect.id,
                        OutreachEmail.status.in_(["pending_approval", "approved", "scheduled", "draft"]),
                    )
                )
                cancelled = 0
                for e in pending_r.scalars().all():
                    e.status = "cancelled"
                    e.error_message = "Reply detected — manual handling"
                    cancelled += 1

                await db.commit()

            result["replies_found"] += 1
            result["details"].append({
                "email": addr,
                "business": info["name"],
                "prospect_id": info["id"],
                "emails_cancelled": cancelled,
            })
            logger.info(
                "📩 Reply from %s (%s) — set to manual_handling, %d emails cancelled",
                addr, info["name"], cancelled,
            )

            try:
                from api.services.telegram_outreach import send_message
                await send_message(
                    f"📩 *Reply detected:* {info['name']}\n"
                    f"📧 From: {addr}\n"
                    f"🤝 Auto-set to manual handling — {cancelled} emails cancelled"
                )
            except Exception:
                pass

        except Exception as e:
            logger.debug("Reply processing for %s failed: %s", addr, e)

    if result["replies_found"] > 0:
        logger.info(
            "Reply check: %d replies found, %d already handled",
            result["replies_found"], result["already_handled"],
        )
    return result
