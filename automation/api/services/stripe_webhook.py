"""
AjayaDesign — Stripe webhook handler + course auto-provisioning.

Handles checkout.session.completed events:
1. Verifies webhook signature (if STRIPE_WEBHOOK_SECRET set)
2. Adds customer to Firebase /approved_users with correct tier
3. Sends Telegram notification to AJ
"""

import hmac
import hashlib
import json
import logging
import time
from typing import Optional

from api.config import settings

logger = logging.getLogger(__name__)

# Map Stripe price IDs / payment link IDs to course tiers
# These are the buy.stripe.com link suffixes from the 3D-print page
PRICE_TO_TIER = {
    # STL Starter Pack - $29
    "6oUbJ06jF2s87U72lG7Re08": "stl",
    # Full Course - $97
    "8x2aEW6jF6Iofmz7G07Re09": "course",
    # 1-on-1 Session - $149
    "9B6aEWazV3wccanf8s7Re0a": "session",
    # Complete Bundle - $349
    "8x2dR8eQb9UAfmzgcw7Re0b": "bundle",
}

TIER_LABELS = {
    "stl": "STL Starter Pack ($29)",
    "course": "Full Course ($97)",
    "session": "1-on-1 Session ($149)",
    "bundle": "Complete Bundle ($349)",
}

TIER_AMOUNTS = {
    "stl": 29,
    "course": 97,
    "session": 149,
    "bundle": 349,
}


def verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify Stripe webhook signature."""
    if not secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping verification")
        return True  # Allow in dev mode

    try:
        elements = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = elements.get("t", "")
        signature = elements.get("v1", "")

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Timing-safe comparison
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error(f"Stripe signature verification failed: {e}")
        return False


def detect_tier_from_session(session: dict) -> str:
    """Detect course tier from Stripe checkout session metadata."""
    # Check metadata first (most reliable)
    metadata = session.get("metadata", {}) or {}
    if "tier" in metadata:
        return metadata["tier"]

    # Check payment_link ID
    payment_link = session.get("payment_link", "")
    if payment_link:
        for link_suffix, tier in PRICE_TO_TIER.items():
            if link_suffix in payment_link:
                return tier

    # Check client_reference_id for referral tracking
    # Fall back to amount
    amount = session.get("amount_total", 0)
    if amount:
        amount_dollars = amount / 100
        for tier, price in TIER_AMOUNTS.items():
            if abs(amount_dollars - price) < 1:
                return tier

    return "course"  # Default fallback


async def handle_checkout_completed(session: dict) -> dict:
    """
    Process a completed Stripe checkout session.

    Returns dict with results for logging.
    """
    from api.services.firebase import is_initialized as fb_initialized
    from api.services.notify import _esc_md, _send_tg_message

    customer_email = session.get("customer_details", {}).get("email", "")
    customer_name = session.get("customer_details", {}).get("name", "Unknown")
    amount_total = session.get("amount_total", 0) / 100
    tier = detect_tier_from_session(session)
    session_id = session.get("id", "unknown")
    ref_id = session.get("client_reference_id", "")

    result = {
        "email": customer_email,
        "name": customer_name,
        "tier": tier,
        "amount": amount_total,
        "session_id": session_id,
        "referral": ref_id,
    }

    logger.info(f"💰 New sale! {TIER_LABELS.get(tier, tier)} from {customer_email}")

    # 1. Add to Firebase /approved_users (auto-grant portal access)
    if fb_initialized() and customer_email:
        try:
            import firebase_admin
            from firebase_admin import auth as fb_auth, db as firebase_db

            # Try to find existing user by email
            try:
                user = fb_auth.get_user_by_email(customer_email)
                uid = user.uid
            except firebase_admin.exceptions.NotFoundError:
                # Create user if they don't exist yet
                user = fb_auth.create_user(
                    email=customer_email,
                    display_name=customer_name,
                )
                uid = user.uid
                logger.info(f"Created Firebase user {uid} for {customer_email}")

            # Add to approved_users
            firebase_db.reference(f"approved_users/{uid}").set({
                "email": customer_email,
                "tier": tier,
                "name": customer_name,
                "stripe_session": session_id,
                "approved_at": int(time.time() * 1000),
            })

            # Also add to pre_approved for belt-and-suspenders
            firebase_db.reference("pre_approved").push({
                "email": customer_email,
                "tier": tier,
                "source": "stripe",
                "ts": int(time.time() * 1000),
            })

            result["firebase"] = "approved"
            logger.info(f"✅ Added {customer_email} to approved_users (tier: {tier})")
        except Exception as e:
            logger.error(f"Firebase approval failed for {customer_email}: {e}")
            result["firebase"] = f"error: {e}"
    else:
        result["firebase"] = "skipped (not initialized or no email)"

    # 2. Send Telegram notification to AJ
    try:
        tier_label = TIER_LABELS.get(tier, tier)
        amount_str = f"${amount_total:.0f}"
        ref_note = f"\n🔗 *Referral:* `{_esc_md(ref_id)}`" if ref_id else ""

        message = "\n".join([
            "💰 *NEW SALE\\!*",
            "",
            f"📦 *Product:* {_esc_md(tier_label)}",
            f"💵 *Amount:* {_esc_md(amount_str)}",
            f"📧 *Customer:* `{_esc_md(customer_email)}`",
            f"👤 *Name:* {_esc_md(customer_name)}",
            f"🔑 *Portal:* {'✅ Auto\\-approved' if result.get('firebase') == 'approved' else '⚠️ Manual approval needed'}",
            ref_note,
            "",
            "🎉 _Money in the bank\\!_",
        ])

        await _send_tg_message({
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
        })
        result["telegram"] = "sent"
    except Exception as e:
        logger.error(f"Telegram sale notification failed: {e}")
        result["telegram"] = f"error: {e}"

    return result
