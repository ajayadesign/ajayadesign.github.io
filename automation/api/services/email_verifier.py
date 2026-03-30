"""
Email Verification Service — MX + format + disposable + SMTP probe.

Pre-send verification saves SMTP quota by skipping undeliverable addresses.
Uses dns.resolver for MX lookups and smtplib for RCPT TO probes.
Includes disposable email domain blacklist and format validation.
"""

import asyncio
import logging
import re
import smtplib
import socket
from datetime import datetime, timezone

import dns.resolver
from sqlalchemy import select, update

from api.database import async_session_factory
from api.models.prospect import Prospect

logger = logging.getLogger("outreach.verify")

# ── Email format regex (RFC 5322 simplified) ──────────────────────
EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
)

# ── Domains known to block RCPT TO verification ──────────────────
NO_PROBE_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "aol.com", "icloud.com", "me.com", "mac.com",
    "protonmail.com", "proton.me",
}

# ── Disposable / temp email domain blacklist ──────────────────────
DISPOSABLE_DOMAINS = {
    # Major disposable providers
    "mailinator.com", "guerrillamail.com", "guerrillamail.de", "guerrillamail.net",
    "tempmail.com", "temp-mail.org", "temp-mail.io",
    "throwaway.email", "throwaway.com",
    "yopmail.com", "yopmail.fr", "yopmail.net",
    "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "dispostable.com", "trashmail.com", "trashmail.me", "trashmail.net",
    "mailnesia.com", "maildrop.cc", "discard.email",
    "fakeinbox.com", "fakemail.net",
    "getnada.com", "nada.email",
    "tempinbox.com", "tempail.com",
    "mailcatch.com", "mailexpire.com",
    "mohmal.com", "emailondeck.com",
    "10minutemail.com", "10minutemail.net",
    "minutemail.com", "tempmailo.com",
    "burnermail.io", "inboxbear.com",
    "harakirimail.com", "jetable.org",
    "mailforspam.com", "spamgourmet.com",
    "mytemp.email", "tempr.email",
    "mailsac.com", "receiveee.com",
    "tmail.ws", "tmpmail.net", "tmpmail.org",
    "getairmail.com", "filzmail.com",
    "crazymailing.com", "armyspy.com",
    "dayrep.com", "einrot.com", "fleckens.hu",
    "gustr.com", "jourrapide.com", "rhyta.com",
    "superrito.com", "teleworm.us",
    "mailnull.com", "spamfree24.org",
    "trashymail.com", "uggsrock.com",
    "mailmoat.com", "emailigo.de",
    "spaml.de", "trashinbox.com",
    "binkmail.com", "bobmail.info",
    "chammy.info", "devnullmail.com",
    "dingbone.com", "fudgerub.com",
    "lookugly.com", "mailinater.com",
    "nomail.xl.cx", "nowmymail.com",
    "pookmail.com", "sogetthis.com",
    "spamhereplease.com", "thisisnotmyrealemail.com",
    "mailtemp.info", "tempmailaddress.com",
}


def is_valid_format(email: str) -> bool:
    """Check if email matches a valid format."""
    if not email or len(email) > 254:
        return False
    return EMAIL_RE.match(email) is not None


def is_disposable(domain: str) -> bool:
    """Check if domain is a known disposable email provider."""
    return domain.lower() in DISPOSABLE_DOMAINS


def verify_mx(domain: str) -> tuple[bool, str | None]:
    """Check if domain has MX records. Returns (has_mx, best_mx_host)."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        if answers:
            best = min(answers, key=lambda r: r.preference)
            return True, str(best.exchange).rstrip(".")
        return False, None
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False, None
    except Exception as e:
        logger.debug("MX lookup failed for %s: %s", domain, e)
        return False, None


def verify_smtp_rcpt(email: str, mx_host: str) -> tuple[bool, str]:
    """Probe SMTP server with RCPT TO to check if mailbox exists."""
    try:
        with smtplib.SMTP(mx_host, 25, timeout=10) as server:
            server.ehlo("ajayadesign.com")
            server.mail("verify@ajayadesign.com")
            code, msg = server.rcpt(email)
            if code == 250:
                return True, "Mailbox exists"
            elif code == 550:
                return False, "Mailbox does not exist"
            else:
                return True, f"Uncertain (code {code})"
    except smtplib.SMTPServerDisconnected:
        return True, "Server disconnected (assume valid)"
    except socket.timeout:
        return True, "Timeout (assume valid)"
    except Exception as e:
        return True, f"Probe error: {str(e)[:100]} (assume valid)"


def verify_email_address(email: str) -> dict:
    """
    Full verification of a single email address.
    Returns {"valid": bool, "reason": str, "mx": bool, "mx_host": str, "disposable": bool}.
    """
    result = {"valid": False, "reason": "", "mx": False, "mx_host": None, "disposable": False}

    # Step 1: Format check
    if not is_valid_format(email):
        result["reason"] = "invalid_format"
        return result

    domain = email.split("@")[1].lower()

    # Step 2: Disposable domain check
    if is_disposable(domain):
        result["reason"] = "disposable_domain"
        result["disposable"] = True
        return result

    # Step 3: MX check
    has_mx, mx_host = verify_mx(domain)
    result["mx"] = has_mx
    result["mx_host"] = mx_host
    if not has_mx:
        result["reason"] = f"no_mx_records:{domain}"
        return result

    # Step 4: SMTP RCPT TO probe (skip major providers that block it)
    if domain in NO_PROBE_DOMAINS:
        result["valid"] = True
        result["reason"] = f"mx_verified:{domain}_blocks_rcpt"
        return result

    is_valid, detail = verify_smtp_rcpt(email, mx_host)
    result["valid"] = is_valid
    result["reason"] = detail
    return result


async def batch_verify(limit: int = 50) -> dict:
    """
    Verify unverified prospect emails in batches.
    Marks invalid emails with status="invalid_email".
    Sets verified_at timestamp on successful verification.
    Returns {"verified": int, "invalid": int, "errors": int, "total": int}.
    """
    stats = {"verified": 0, "invalid": 0, "errors": 0, "total": 0}

    async with async_session_factory() as db:
        result = await db.execute(
            select(Prospect)
            .where(
                Prospect.owner_email.isnot(None),
                Prospect.email_verified != True,  # noqa: E712
                Prospect.status.in_(["imported", "discovered", "enriched", "queued", "audited"]),
            )
            .order_by(Prospect.created_at.desc())
            .limit(limit)
        )
        prospects = result.scalars().all()

    stats["total"] = len(prospects)

    for prospect in prospects:
        try:
            vresult = await asyncio.to_thread(verify_email_address, prospect.owner_email)

            async with async_session_factory() as db:
                p = await db.get(Prospect, prospect.id)
                if not p:
                    continue

                p.email_verified = vresult["valid"]
                now = datetime.now(timezone.utc)

                if vresult["valid"]:
                    # Set verified_at in enrichment JSONB
                    enrichment = p.enrichment or {}
                    enrichment["email_verified_at"] = now.isoformat()
                    enrichment["email_verification_detail"] = vresult["reason"]
                    p.enrichment = enrichment
                    stats["verified"] += 1
                else:
                    # Mark as invalid_email
                    p.status = "invalid_email"
                    enrichment = p.enrichment or {}
                    enrichment["email_invalid_reason"] = vresult["reason"]
                    enrichment["email_checked_at"] = now.isoformat()
                    p.enrichment = enrichment
                    stats["invalid"] += 1
                    logger.info("Invalid email: %s — %s", prospect.owner_email, vresult["reason"])

                # Infer mx_provider
                if vresult.get("mx_host"):
                    mx = vresult["mx_host"].lower()
                    if "google" in mx or "gmail" in mx:
                        p.mx_provider = "google"
                    elif "outlook" in mx or "microsoft" in mx:
                        p.mx_provider = "microsoft"
                    else:
                        p.mx_provider = "other"

                await db.commit()

        except Exception as e:
            stats["errors"] += 1
            logger.warning("Verification error for %s: %s", prospect.owner_email, e)

    logger.info(
        "Batch verify: %d verified, %d invalid, %d errors out of %d",
        stats["verified"], stats["invalid"], stats["errors"], stats["total"],
    )
    return stats
