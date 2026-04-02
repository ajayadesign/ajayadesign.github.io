"""
AjayaDesign — Firebase RTDB lead & audit-request watcher.

Polls Firebase for new leads and audit requests, sends Telegram
notifications to AJ, and optionally sends auto-reply emails.

Runs as a background task in the FastAPI event loop.
"""

import asyncio
import logging
import time
from typing import Optional

from api.config import settings

logger = logging.getLogger(__name__)


async def notify_new_lead(lead: dict, source: str = "website") -> bool:
    """Send Telegram notification for a new lead."""
    from api.services.notify import _esc_md, _send_tg_message

    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        return False

    email = lead.get("email", "unknown")
    name = lead.get("name", "")
    lead_source = lead.get("source", source)
    business = lead.get("business", lead.get("businessName", ""))

    if source == "audit":
        audit_type = lead.get("audit_type", "website+ai")
        phone = lead.get("phone", "")
        website = lead.get("website", "")

        message = "\n".join([
            "🔍 *NEW AUDIT REQUEST\\!*",
            "",
            f"🏢 *Business:* {_esc_md(business)}",
            f"📧 *Email:* `{_esc_md(email)}`",
            f"📱 *Phone:* {_esc_md(phone)}" if phone else "",
            f"🌐 *Website:* {_esc_md(website)}" if website else "",
            f"📋 *Type:* {_esc_md(audit_type)}",
            "",
            "⏱️ _Respond within 24h\\!_",
        ])
    elif source == "3d-print":
        message = "\n".join([
            "🖨️ *NEW 3D PRINT LEAD\\!*",
            "",
            f"📧 *Email:* `{_esc_md(email)}`",
            f"👤 *Name:* {_esc_md(name)}" if name else "",
            f"📥 *Source:* {_esc_md(lead_source)}",
            "",
            "📨 _Free STL download requested_",
        ])
    else:
        message = "\n".join([
            "📥 *NEW LEAD\\!*",
            "",
            f"🏢 *Business:* {_esc_md(business)}" if business else "",
            f"📧 *Email:* `{_esc_md(email)}`",
            f"👤 *Name:* {_esc_md(name)}" if name else "",
            f"📥 *Source:* {_esc_md(lead_source)}",
        ])

    # Filter out empty lines
    message = "\n".join(line for line in message.split("\n") if line.strip())

    try:
        return await _send_tg_message({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
        })
    except Exception as e:
        logger.error(f"Lead notification failed: {e}")
        return False


async def send_auto_reply_email(email: str, name: str, lead_type: str = "audit") -> bool:
    """Send auto-reply email to customer confirming receipt."""
    from api.services.email_service import send_email

    if not settings.smtp_email or not settings.smtp_app_password:
        logger.warning("SMTP not configured — skipping auto-reply")
        return False

    if lead_type == "audit":
        subject = "Your Free Audit Request — AjayaDesign"
        body = f"""Hi {name or 'there'},

Thanks for requesting a free website & AI audit from AjayaDesign!

We've received your submission and will have your personalized audit report ready within 24-48 hours.

Here's what we'll analyze:
• Google PageSpeed & performance
• Mobile responsiveness
• SEO structure & meta tags
• AI automation opportunities for your business
• 3 custom recommendations

If you have any questions in the meantime, just reply to this email.

— Ajaya Dahal
AjayaDesign | Austin, Texas
https://ajayadesign.com
"""
    elif lead_type == "3d-print":
        subject = "Your Free STL File — 3D Print Academy"
        body = f"""Hi {name or 'there'},

Thanks for signing up! Here's what happens next:

1. Check your inbox for the free magnet frame STL file
2. Import it into your slicer (Cura or PrusaSlicer)
3. Print at 0.2mm layer height, 20% infill, PLA

Want the full course? 43 lessons, 15+ STL files, and business training:
https://ajayadesign.com/3D-print/#enroll

Questions? Just reply to this email.

— AJ
3D Print Academy by AjayaDesign
"""
    else:
        return False

    try:
        await send_email(
            to=email,
            subject=subject,
            body_html=f"<pre style='font-family:sans-serif;white-space:pre-wrap'>{body}</pre>",
        )
        logger.info(f"Auto-reply sent to {email} ({lead_type})")
        return True
    except Exception as e:
        logger.error(f"Auto-reply email failed for {email}: {e}")
        return False


async def poll_firebase_leads():
    """
    Background task: poll Firebase for new leads and audit requests.
    Runs every FIREBASE_POLL_INTERVAL seconds.
    """
    from api.services.firebase import is_initialized

    # Wait for Firebase to initialize
    for _ in range(30):
        if is_initialized():
            break
        await asyncio.sleep(2)

    if not is_initialized():
        logger.warning("Firebase not initialized — lead watcher disabled")
        return

    logger.info("🔔 Firebase lead watcher started")

    # Track what we've already notified about
    seen_leads: set = set()
    seen_audits: set = set()
    first_run = True

    while True:
        try:
            from firebase_admin import db as firebase_db

            # ─── Check /leads for new 3D-print signups ───
            leads_ref = firebase_db.reference("leads")
            leads_snap = leads_ref.order_by_child("status").equal_to("new").get()

            if leads_snap:
                for kid, lead in leads_snap.items():
                    if kid not in seen_leads:
                        seen_leads.add(kid)
                        if not first_run:
                            source = lead.get("source", "website")
                            lead_type = "3d-print" if "3d" in source.lower() or "stl" in source.lower() else "website"
                            await notify_new_lead(lead, source=lead_type)

                            # Send auto-reply for 3D-print leads
                            email = lead.get("email", "")
                            name = lead.get("name", "")
                            if email and lead_type == "3d-print":
                                await send_auto_reply_email(email, name, "3d-print")

            # ─── Check /audit-requests for new submissions ───
            audits_ref = firebase_db.reference("audit-requests")
            # Use get() without ordering — simpler and avoids index issues
            audits_snap = audits_ref.get()

            if audits_snap and isinstance(audits_snap, dict):
                for kid, audit in audits_snap.items():
                    if kid not in seen_audits and isinstance(audit, dict):
                        status = audit.get("status", "new")
                        if status == "new":
                            seen_audits.add(kid)
                            if not first_run:
                                await notify_new_lead(audit, source="audit")

                                # Send auto-reply
                                email = audit.get("email", "")
                                name = audit.get("business", "")
                                if email:
                                    await send_auto_reply_email(email, name, "audit")

            # ─── Check /chat-leads ───
            chat_ref = firebase_db.reference("chat-leads")
            chat_snap = chat_ref.get()
            if chat_snap and isinstance(chat_snap, dict):
                for kid, lead in chat_snap.items():
                    if kid not in seen_leads:
                        seen_leads.add(kid)
                        if not first_run:
                            await notify_new_lead(lead, source="chatbot")

            first_run = False

        except Exception as e:
            logger.error(f"Firebase lead poll error: {e}")

        await asyncio.sleep(settings.firebase_poll_interval)
