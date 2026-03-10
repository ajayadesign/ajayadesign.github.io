"""
Email Verification Service — MX + SMTP probe to verify deliverability.

Pre-send verification saves SMTP quota by skipping undeliverable addresses.
Uses dns.resolver for MX lookups and smtplib for RCPT TO probes.
"""

import logging
import smtplib
import socket
from datetime import datetime, timezone

import dns.resolver
from sqlalchemy import select, update

from api.database import async_session_factory
from api.models.prospect import Prospect

logger = logging.getLogger("outreach.verify")

# Domains known to block RCPT TO verification
NO_PROBE_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "aol.com", "icloud.com", "me.com", "mac.com",
    "protonmail.com", "proton.me",
}


def verify_mx(domain: str) -> tuple[bool, str | None]:
    """
    Check if domain has MX records.
    Returns (has_mx, best_mx_host).
    """
    try:
        answers = dns.resolver.resolve(domain, "MX")
        if answers:
            best = min(answers, key=lambda r: r.preference)
            return True, str(best.exchange).rstrip(".")
        return False, None
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False, None
    except dns.resolver.NoNameservers:
        return False, None
    except Exception as e:
        logger.debug("MX lookup failed for %s: %s", domain, e)
        return False, None


def verify_smtp_rcpt(email: str, mx_host: str) -> tuple[bool, str]:
    """
    Probe SMTP server with RCPT TO to check if mailbox exists.
    Returns (is_valid, detail_message).
    """
    try:
        with smtplib.SMTP(mx_host, 25, timeout=10) as server:
            server.ehlo("ajayadesign.com")
            # Some servers reject without MAIL FROM
            server.mail("verify@ajayadesign.com")
            code, msg = server.rcpt(email)
            if code == 250:
                return True, "Mailbox exists"
            elif code == 550:
                return False, "Mailbox does not exist"
            else:
                return True, f"Uncertain (code {code})"  # Assume valid if not rejected
    except smtplib.SMTPServerDisconnected:
        return True, "Server disconnected (assume valid)"
    except socket.timeout:
        return True, "Timeout (assume valid)"
    except Exception as e:
        return True, f"Probe error: {str(e)[:100]} (assume valid)"


def verify_email_address(email: str) -> dict:
    """
    Full verification of a single email address.
    Returns {"valid": bool, "mx": bool, "mx_host": str, "detail": str}.
    """
    if not email or "@" not in email:
        return {"valid": False, "mx": False, "mx_host": None, "detail": "Invalid format"}

    domain = email.split("@")[1].lower()

    # Step 1: MX check
    has_mx, mx_host = verify_mx(domain)
    if not has_mx:
        return {"valid": False, "mx": False, "mx_host": None,
                "detail": f"No MX records for {domain}"}

    # Step 2: RCPT TO probe (skip for major providers that block it)
    if domain in NO_PROBE_DOMAINS:
        return {"valid": True, "mx": True, "mx_host": mx_host,
                "detail": f"MX verified ({domain} blocks RCPT probe)"}

    is_valid, detail = verify_smtp_rcpt(email, mx_host)
    return {"valid": is_valid, "mx": True, "mx_host": mx_host, "detail": detail}


async def batch_verify(limit: int = 50) -> dict:
    """
    Verify unverified prospect emails in batches.
    Processes prospects with status='imported' and email_verified IS NULL.
    Returns {"verified": int, "invalid": int, "errors": int}.
    """
    stats = {"verified": 0, "invalid": 0, "errors": 0, "total": 0}

    async with async_session_factory() as db:
        result = await db.execute(
            select(Prospect)
            .where(
                Prospect.owner_email.isnot(None),
                # Match both NULL (never checked) and False (model default)
                Prospect.email_verified != True,  # noqa: E712
                Prospect.status.in_(["imported", "discovered", "enriched"]),
            )
            .order_by(Prospect.created_at.desc())
            .limit(limit)
        )
        prospects = result.scalars().all()

    stats["total"] = len(prospects)

    for prospect in prospects:
        try:
            result = verify_email_address(prospect.owner_email)

            async with async_session_factory() as db:
                p = await db.get(Prospect, prospect.id)
                if p:
                    p.email_verified = result["valid"]
                    if result.get("mx_host"):
                        # Infer mx_provider
                        mx = result["mx_host"].lower()
                        if "google" in mx or "gmail" in mx:
                            p.mx_provider = "google"
                        elif "outlook" in mx or "microsoft" in mx:
                            p.mx_provider = "microsoft"
                        else:
                            p.mx_provider = "other"
                    await db.commit()

            if result["valid"]:
                stats["verified"] += 1
            else:
                stats["invalid"] += 1
                logger.info("Invalid email: %s — %s", prospect.owner_email, result["detail"])

        except Exception as e:
            stats["errors"] += 1
            logger.warning("Verification error for %s: %s", prospect.owner_email, e)

    logger.info("Batch verify: %d verified, %d invalid, %d errors out of %d",
                stats["verified"], stats["invalid"], stats["errors"], stats["total"])
    return stats
