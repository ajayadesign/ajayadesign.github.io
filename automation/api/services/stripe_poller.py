"""
AjayaDesign — Stripe checkout session poller.

Polls Stripe API for recently completed checkout sessions every 60s.
For each new session, auto-provisions the customer in Firebase and
sends a Telegram notification. No webhook endpoint needed.
"""

import asyncio
import logging
import time

import aiohttp

from api.config import settings

logger = logging.getLogger(__name__)

# Track processed sessions to avoid duplicates
_processed_sessions: set = set()


TIER_BY_AMOUNT = {
    2900: "stl",       # $29
    9700: "course",    # $97
    14900: "session",  # $149
    34900: "bundle",   # $349
}

TIER_LABELS = {
    "stl": "STL Starter Pack ($29)",
    "course": "Full Course ($97)",
    "session": "1-on-1 Session ($149)",
    "bundle": "Complete Bundle ($349)",
}


async def poll_stripe_sessions():
    """
    Background task: poll Stripe for completed checkout sessions.
    On new completed session → auto-provision + notify.
    """
    if not settings.stripe_secret_key:
        logger.info("ℹ️ STRIPE_SECRET_KEY not set — Stripe poller disabled")
        return

    logger.info("💳 Stripe checkout poller started")
    first_run = True

    while True:
        try:
            # Fetch recent completed sessions from last 24h
            since = int(time.time()) - 86400
            async with aiohttp.ClientSession() as session:
                url = "https://api.stripe.com/v1/checkout/sessions"
                params = {
                    "limit": "20",
                    "status": "complete",
                    "created[gte]": str(since),
                }
                headers = {
                    "Authorization": f"Bearer {settings.stripe_secret_key}",
                }
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Stripe API error {resp.status}: {body[:200]}")
                        await asyncio.sleep(60)
                        continue
                    data = await resp.json()

            sessions_list = data.get("data", [])

            for cs in sessions_list:
                cs_id = cs.get("id", "")
                if cs_id in _processed_sessions:
                    continue

                _processed_sessions.add(cs_id)

                if first_run:
                    continue  # Don't process existing sessions on startup

                # New completed checkout!
                customer_email = (cs.get("customer_details") or {}).get("email", "")
                customer_name = (cs.get("customer_details") or {}).get("name", "Unknown")
                amount = cs.get("amount_total", 0)
                tier = TIER_BY_AMOUNT.get(amount, "course")
                ref_id = cs.get("client_reference_id", "")

                logger.info(f"💰 New Stripe checkout: {TIER_LABELS.get(tier, tier)} from {customer_email}")

                # Auto-provision in Firebase
                await _provision_customer(customer_email, customer_name, tier, cs_id)

                # Telegram notification
                await _notify_sale(customer_email, customer_name, tier, amount / 100, ref_id)

            first_run = False

        except Exception as e:
            logger.error(f"Stripe poller error: {e}")

        await asyncio.sleep(60)


async def _provision_customer(email: str, name: str, tier: str, session_id: str):
    """Add customer to Firebase /approved_users."""
    from api.services.firebase import is_initialized
    if not is_initialized() or not email:
        return

    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth, db as firebase_db

        # Find or create Firebase user
        try:
            user = fb_auth.get_user_by_email(email)
            uid = user.uid
        except firebase_admin.exceptions.NotFoundError:
            user = fb_auth.create_user(email=email, display_name=name)
            uid = user.uid
            logger.info(f"Created Firebase user {uid} for {email}")

        # Approve in Firebase
        firebase_db.reference(f"approved_users/{uid}").set({
            "email": email,
            "tier": tier,
            "name": name,
            "stripe_session": session_id,
            "approved_at": int(time.time() * 1000),
        })

        # Also add to pre_approved
        firebase_db.reference("pre_approved").push({
            "email": email,
            "tier": tier,
            "source": "stripe",
            "ts": int(time.time() * 1000),
        })

        logger.info(f"✅ Provisioned {email} → tier={tier}")
    except Exception as e:
        logger.error(f"Firebase provision failed for {email}: {e}")


async def _notify_sale(email: str, name: str, tier: str, amount: float, ref_id: str):
    """Send Telegram notification for new sale."""
    from api.services.notify import _esc_md, _send_tg_message

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    tier_label = TIER_LABELS.get(tier, tier)
    ref_note = f"\n🔗 *Referral:* `{_esc_md(ref_id)}`" if ref_id else ""

    message = "\n".join(line for line in [
        "💰 *NEW SALE\\!*",
        "",
        f"📦 *Product:* {_esc_md(tier_label)}",
        f"💵 *Amount:* ${_esc_md(f'{amount:.0f}')}",
        f"📧 *Customer:* `{_esc_md(email)}`",
        f"👤 *Name:* {_esc_md(name)}",
        f"🔑 *Portal:* ✅ Auto\\-approved",
        ref_note,
        "",
        "🎉 _Money in the bank\\!_",
    ] if line.strip())

    try:
        await _send_tg_message({
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
        })
    except Exception as e:
        logger.error(f"Telegram sale notification failed: {e}")
