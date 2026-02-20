"""
Recon Engine — Decision-Maker Finder.

Discovers business owner names & emails through a waterfall of methods:
Website scrape → WHOIS → Hunter.io → Pattern guess + SMTP verify → Fallback.

Phase 4 of OUTREACH_AGENT_PLAN.md (§6).
"""

import asyncio
import logging
import re
import socket
from email.utils import parseaddr
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import dns.resolver

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import Prospect

logger = logging.getLogger("outreach.recon")

# ─── Constants ─────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

# Common role emails to skip (we want owner/personal emails)
ROLE_EMAILS = {
    "info", "contact", "admin", "support", "hello", "help",
    "sales", "billing", "no-reply", "noreply", "webmaster",
    "postmaster", "abuse", "marketing", "team", "office",
}

# Pages likely to contain owner info
CONTACT_PATHS = [
    "/contact", "/contact-us", "/about", "/about-us", "/team",
    "/our-team", "/staff", "/leadership", "/owner",
]

# Common owner-indicator phrases
OWNER_PHRASES = re.compile(
    r"(owner|founder|proprietor|principal|ceo|president|manager|director)",
    re.IGNORECASE,
)

# Disposable email domains (top offenders)
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com",
    "tempmail.com", "throwaway.email", "yopmail.com",
    "trashmail.com", "sharklasers.com", "grr.la",
}

# Known national/franchise chain domains — don't waste Hunter.io calls on these
CHAIN_DOMAINS = {
    "chick-fil-a.com", "mcdonalds.com", "subway.com", "wendys.com",
    "burgerking.com", "dominos.com", "pizzahut.com", "papajohns.com",
    "starbucks.com", "dunkindonuts.com", "chipotle.com", "sonic.com",
    "whataburger.com", "chickfila.com", "tacobell.com", "kfc.com",
    "walmart.com", "target.com", "walgreens.com", "cvs.com",
    "homedepot.com", "lowes.com", "autozone.com", "oreillyauto.com",
    "advanceautoparts.com", "oreilly.com",
    "att.com", "t-mobile.com", "verizon.com", "sprint.com",
    "bankofamerica.com", "chase.com", "wellsfargo.com",
    "dollartree.com", "dollargeneral.com", "familydollar.com",
    "chilis.com", "applebees.com", "dennys.com", "ihop.com",
    "jackinbox.com", "popeyes.com", "arbys.com", "hardees.com",
    "raisingcanes.com", "pandaexpress.com", "fiveguys.com",
    "crackerbarrel.com", "olivegarden.com", "redlobster.com",
    "7-eleven.com", "circlek.com",
    "planetfitness.com", "lafitness.com", "anytimefitness.com",
    "orangetheory.com", "goldsgym.com",
    "heb.com", "kroger.com", "costco.com", "samsclub.com",
    "dutchbros.com", "7brew.com", "scooterscoffee.com",
    "wingstop.com", "buffalowildwings.com", "zaxbys.com",
    "jamba.com", "smoothieking.com", "baskinrobbins.com",
    "valvoline.com", "jiffylube.com", "firestonecompleteautocare.com",
    "goodyear.com", "ntb.com", "maaco.com", "meineke.com",
    "dollartree.com", "five-below.com", "biglots.com",
    "sherwin-williams.com", "ppg.com",
    "allstate.com", "statefarm.com", "geico.com", "progressive.com",
    "mattressfirm.com", "sleepnumber.com",
    "gamestop.com", "bestbuy.com",
}


def _is_known_chain(domain: str) -> bool:
    """Check if a domain belongs to a known national chain.
    Also checks subdomains like 'stores.advanceautoparts.com'."""
    if not domain:
        return False
    d = domain.lower().replace("www.", "")
    # Direct match
    if d in CHAIN_DOMAINS:
        return True
    # Subdomain match: 'stores.advanceautoparts.com' → 'advanceautoparts.com'
    parts = d.split(".")
    if len(parts) > 2:
        parent = ".".join(parts[-2:])
        if parent in CHAIN_DOMAINS:
            return True
    return False


# ─── Email Format Validation ──────────────────────────────────────────

def is_valid_email_format(email: str) -> bool:
    """Check basic email format validity."""
    if not email or len(email) > 254:
        return False
    _, addr = parseaddr(email)
    if not addr:
        return False
    return bool(EMAIL_REGEX.fullmatch(addr))


def is_role_email(email: str) -> bool:
    """Check if email is a generic role address."""
    local = email.split("@")[0].lower()
    return local in ROLE_EMAILS


def is_disposable(email: str) -> bool:
    """Check if email is from a disposable provider."""
    domain = email.split("@")[-1].lower()
    return domain in DISPOSABLE_DOMAINS


# ─── DNS/MX Verification ──────────────────────────────────────────────

async def check_mx_records(domain: str) -> list[str]:
    """Resolve MX records for a domain. Returns list of MX hosts."""
    try:
        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None,
            lambda: dns.resolver.resolve(domain, "MX"),
        )
        return sorted(
            [str(r.exchange).rstrip(".") for r in answers],
            key=lambda x: x,
        )
    except Exception:
        return []


async def smtp_verify(email: str) -> dict:
    """
    Verify email via SMTP handshake (RCPT TO without sending).
    Returns {'valid': bool, 'catch_all': bool, 'code': int}.
    """
    domain = email.split("@")[-1]
    mx_hosts = await check_mx_records(domain)
    if not mx_hosts:
        return {"valid": False, "catch_all": False, "code": 0}

    for mx_host in mx_hosts[:2]:  # Try first two MX
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(mx_host, 25),
                timeout=10,
            )
            # Read greeting
            greeting = await asyncio.wait_for(reader.readline(), timeout=5)

            # EHLO
            writer.write(b"EHLO ajayadesign.com\r\n")
            await writer.drain()
            await asyncio.wait_for(reader.readline(), timeout=5)

            # MAIL FROM
            writer.write(b"MAIL FROM:<verify@ajayadesign.com>\r\n")
            await writer.drain()
            await asyncio.wait_for(reader.readline(), timeout=5)

            # RCPT TO — the actual check
            writer.write(f"RCPT TO:<{email}>\r\n".encode())
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=5)
            code = int(response[:3])

            # Check for catch-all (try obviously fake address)
            fake = f"xyzzy_noreply_test_{id(email)}@{domain}"
            writer.write(f"RCPT TO:<{fake}>\r\n".encode())
            await writer.drain()
            fake_response = await asyncio.wait_for(reader.readline(), timeout=5)
            fake_code = int(fake_response[:3])
            is_catch_all = fake_code == 250

            # Quit
            writer.write(b"QUIT\r\n")
            await writer.drain()
            writer.close()

            return {
                "valid": code == 250 and not is_catch_all,
                "catch_all": is_catch_all,
                "code": code,
            }

        except Exception as e:
            logger.debug("SMTP verify failed for %s via %s: %s", email, mx_host, e)
            continue

    return {"valid": False, "catch_all": False, "code": 0}


async def verify_email(email: str) -> dict:
    """
    Full email verification pipeline (§6.2).
    Returns {'email', 'format_valid', 'domain_exists', 'mx_records',
             'smtp_valid', 'disposable', 'catch_all', 'score'}.
    """
    result = {
        "email": email,
        "format_valid": False,
        "domain_exists": False,
        "mx_records": False,
        "smtp_valid": False,
        "disposable": False,
        "catch_all": False,
        "score": 0,
    }

    # 1. Format check
    if not is_valid_email_format(email):
        return result
    result["format_valid"] = True
    result["score"] += 20

    domain = email.split("@")[-1]

    # 2. Disposable check
    result["disposable"] = is_disposable(email)
    if result["disposable"]:
        return result

    # 3. DNS/MX check
    mx_hosts = await check_mx_records(domain)
    result["domain_exists"] = len(mx_hosts) > 0
    result["mx_records"] = len(mx_hosts) > 0
    if not mx_hosts:
        return result
    result["score"] += 30

    # 4. SMTP verification
    smtp_result = await smtp_verify(email)
    result["smtp_valid"] = smtp_result["valid"]
    result["catch_all"] = smtp_result["catch_all"]

    if result["smtp_valid"]:
        result["score"] += 40
    elif smtp_result["code"] == 250 and result["catch_all"]:
        result["score"] += 15  # Catch-all — uncertain

    # Bonus for non-role emails
    if not is_role_email(email):
        result["score"] += 10

    return result


# ─── Website Scraping ─────────────────────────────────────────────────

async def scrape_website_for_contacts(url: str) -> dict:
    """
    Scrape a business website for owner name, email, and phone.
    Checks contact/about/team pages. Returns best findings.
    """
    from bs4 import BeautifulSoup

    findings = {"emails": [], "names": [], "phones": [], "linkedin": []}
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    pages_to_scrape = [url] + [base_url + p for p in CONTACT_PATHS]

    async with aiohttp.ClientSession() as session:
        for page_url in pages_to_scrape:
            try:
                async with session.get(
                    page_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 AjayaDesign ReconBot/1.0"},
                ) as resp:
                    if resp.status != 200:
                        continue
                    html = await resp.text(errors="replace")

                soup = BeautifulSoup(html, "lxml")

                # Extract emails from mailto: links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("mailto:"):
                        email = href.replace("mailto:", "").split("?")[0].strip()
                        if is_valid_email_format(email):
                            findings["emails"].append(email)

                # Extract emails from body text
                text_emails = EMAIL_REGEX.findall(soup.get_text())
                for e in text_emails:
                    if is_valid_email_format(e) and e not in findings["emails"]:
                        findings["emails"].append(e)

                # Extract LinkedIn URLs
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "linkedin.com/in/" in href:
                        findings["linkedin"].append(href)

                # Look for owner/founder names (text near owner keywords)
                text = soup.get_text()
                for match in OWNER_PHRASES.finditer(text):
                    # Try to extract name near the match
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end]
                    # Look for capitalized name patterns
                    name_match = re.search(
                        r"([A-Z][a-z]+\s+[A-Z][a-z]+)", context
                    )
                    if name_match:
                        name = name_match.group(1).strip()
                        if name and len(name) > 3 and name not in findings["names"]:
                            # Filter out garbage: HTML element text, roles, departments
                            bad = {"select", "page", "click", "menu", "toggle", "learn",
                                   "more", "read", "view", "look", "search", "open",
                                   "close", "submit", "send", "download", "share",
                                   "follow", "subscribe", "login", "sign", "register",
                                   "home", "about", "contact", "professional",
                                   "assistant", "manager", "operator", "department",
                                   "stories", "studio", "dental", "financial", "legal",
                                   "property", "hamburger", "navigation", "header",
                                   "footer", "united", "states", "how", "did", "what"}
                            words = name.lower().split()
                            if not any(w in bad for w in words):
                                findings["names"].append(name)

                # Phone numbers
                phone_matches = re.findall(
                    r"[\+]?1?\s*[-.]?\s*\(?\d{3}\)?\s*[-.]?\s*\d{3}\s*[-.]?\s*\d{4}",
                    text,
                )
                for p in phone_matches:
                    cleaned = re.sub(r"\D", "", p)
                    if len(cleaned) >= 10 and cleaned not in findings["phones"]:
                        findings["phones"].append(cleaned)

            except Exception as e:
                logger.debug("Scrape error on %s: %s", page_url, e)
                continue

    return findings


# ─── Pattern Guessing ─────────────────────────────────────────────────

def generate_email_guesses(owner_name: str, domain: str) -> list[str]:
    """
    Generate common email patterns from a name and domain.
    e.g., John Smith + acme.com → [john@, jsmith@, john.smith@, etc.]
    """
    if not owner_name or not domain:
        return []

    parts = owner_name.strip().lower().split()
    if len(parts) < 2:
        first = parts[0]
        last = ""
    else:
        first = parts[0]
        last = parts[-1]

    guesses = []
    if first and last:
        guesses = [
            f"{first}@{domain}",
            f"{first}.{last}@{domain}",
            f"{first}{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}{last[0]}@{domain}",
            f"{last}@{domain}",
            f"{first[0]}.{last}@{domain}",
        ]
    elif first:
        guesses = [
            f"{first}@{domain}",
        ]

    # Always add common fallbacks
    guesses.extend([
        f"info@{domain}",
        f"contact@{domain}",
        f"hello@{domain}",
    ])

    return guesses


# ─── WHOIS Lookup ─────────────────────────────────────────────────────

async def lookup_whois(domain: str) -> dict:
    """
    Try to get registrant info from WHOIS.
    Many domains use privacy protection, so this often returns nothing.
    """
    try:
        import whois as python_whois
        loop = asyncio.get_event_loop()
        w = await loop.run_in_executor(None, python_whois.whois, domain)

        registrant_name = None
        registrant_email = None

        if hasattr(w, "name") and w.name:
            name_val = w.name if isinstance(w.name, str) else w.name[0]
            # Skip privacy services
            if not any(s in name_val.lower() for s in ["privacy", "proxy", "redacted", "whoisguard"]):
                registrant_name = name_val

        if hasattr(w, "emails") and w.emails:
            emails = w.emails if isinstance(w.emails, list) else [w.emails]
            for e in emails:
                if not any(s in e.lower() for s in ["abuse", "privacy", "proxy", "whois"]):
                    registrant_email = e
                    break

        return {
            "registrant_name": registrant_name,
            "registrant_email": registrant_email,
        }

    except ImportError:
        logger.info("python-whois not installed — skipping WHOIS lookup")
        return {}
    except Exception as e:
        logger.debug("WHOIS lookup failed for %s: %s", domain, e)
        return {}


# ─── Hunter.io Integration ────────────────────────────────────────────

# Simple daily call counter (resets on date change)
_hunter_calls = {"date": None, "count": 0}

def _check_hunter_limit() -> bool:
    """Check if we're under the daily Hunter.io call limit."""
    from datetime import date
    today = date.today().isoformat()
    if _hunter_calls["date"] != today:
        _hunter_calls["date"] = today
        _hunter_calls["count"] = 0
    return _hunter_calls["count"] < settings.hunter_daily_call_limit


def _increment_hunter_calls():
    """Increment the daily Hunter.io call counter."""
    from datetime import date
    today = date.today().isoformat()
    if _hunter_calls["date"] != today:
        _hunter_calls["date"] = today
        _hunter_calls["count"] = 0
    _hunter_calls["count"] += 1


async def hunter_domain_search(domain: str) -> dict:
    """
    Query Hunter.io Domain Search API for emails associated with a domain.

    Returns:
        {
            "emails": [{"email": str, "first_name": str, "last_name": str,
                         "position": str, "confidence": int, "type": str}],
            "organization": str,
        }
    """
    api_key = settings.hunter_api_key
    if not api_key:
        return {"emails": [], "organization": None}

    if not _check_hunter_limit():
        logger.info("Hunter.io daily limit reached (%d/%d) — skipping",
                     _hunter_calls["count"], settings.hunter_daily_call_limit)
        return {"emails": [], "organization": None}

    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.hunter.io/v2/domain-search"
            params = {"domain": domain, "api_key": api_key}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                _increment_hunter_calls()
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Hunter.io API error %d for %s: %s", resp.status, domain, body[:200])
                    return {"emails": [], "organization": None}

                data = await resp.json()
                payload = data.get("data", {})
                emails_raw = payload.get("emails", [])
                org = payload.get("organization")

                emails = []
                for e in emails_raw:
                    email_addr = e.get("value") or e.get("email")
                    if not email_addr or not is_valid_email_format(email_addr):
                        continue
                    emails.append({
                        "email": email_addr,
                        "first_name": e.get("first_name"),
                        "last_name": e.get("last_name"),
                        "position": e.get("position"),
                        "confidence": e.get("confidence", 0),
                        "type": e.get("type", "unknown"),  # "personal" or "generic"
                    })

                # Sort: personal first, then by confidence desc
                emails.sort(key=lambda x: (0 if x["type"] == "personal" else 1, -x["confidence"]))
                logger.info("Hunter.io: %s → %d emails found (org=%s)", domain, len(emails), org)
                return {"emails": emails, "organization": org}

    except asyncio.TimeoutError:
        logger.warning("Hunter.io timeout for %s", domain)
        return {"emails": [], "organization": None}
    except Exception as e:
        logger.error("Hunter.io error for %s: %s", domain, e)
        return {"emails": [], "organization": None}


# ─── Main Recon Pipeline ──────────────────────────────────────────────

async def recon_prospect(prospect_id: str) -> Optional[dict]:
    """
    Full recon pipeline for one prospect (§6.1 waterfall).
    1. Website scrape
    2. WHOIS lookup
    3. Hunter.io domain search
    4. Pattern guess + SMTP verify
    5. Fallback to info@domain
    Updates the Prospect record and returns findings dict.
    """
    from api.services.telegram_outreach import notify_recon
    from api.services.firebase_summarizer import _safe_set
    import time as _time

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return None

        domain = None
        if prospect.website_url:
            parsed = urlparse(prospect.website_url)
            domain = parsed.netloc.replace("www.", "")

        pid = str(prospect_id)
        result = {
            "prospect_id": pid,
            "owner_name": None,
            "owner_email": None,
            "email_source": None,
            "email_verified": False,
            "email_score": 0,
            "linkedin": None,
            "phone": None,
        }

        logger.info("Recon: %s (%s)", prospect.business_name, domain or "no domain")

        # ─── Step 1: Website Scrape ────────────────────────────────
        if prospect.website_url:
            findings = await scrape_website_for_contacts(prospect.website_url)

            # Best name
            if findings["names"] and not prospect.owner_name:
                result["owner_name"] = findings["names"][0]

            # LinkedIn
            if findings["linkedin"]:
                result["linkedin"] = findings["linkedin"][0]

            # Phone
            if findings["phones"] and not prospect.phone:
                result["phone"] = findings["phones"][0]

            # Prioritize personal emails over role emails
            personal = [e for e in findings["emails"] if not is_role_email(e)]
            role = [e for e in findings["emails"] if is_role_email(e)]

            for email in personal + role:
                verification = await verify_email(email)
                if verification["score"] >= 50:
                    result["owner_email"] = email
                    result["email_source"] = "website_scrape"
                    result["email_verified"] = verification["smtp_valid"]
                    result["email_score"] = verification["score"]
                    break

        # ─── Step 2: WHOIS ─────────────────────────────────────────
        if not result["owner_email"] and domain:
            whois_data = await lookup_whois(domain)
            if whois_data.get("registrant_name") and not result["owner_name"]:
                result["owner_name"] = whois_data["registrant_name"]
            if whois_data.get("registrant_email"):
                verification = await verify_email(whois_data["registrant_email"])
                if verification["score"] >= 50:
                    result["owner_email"] = whois_data["registrant_email"]
                    result["email_source"] = "whois"
                    result["email_verified"] = verification["smtp_valid"]
                    result["email_score"] = verification["score"]

        # ─── Step 3: Hunter.io Domain Search ───────────────────────
        # Gate: only use Hunter.io for high-value local prospects (free tier is limited)
        _is_chain = _is_known_chain(domain)
        _high_value = (prospect.priority_score or 0) >= 35
        _use_hunter = not _is_chain and _high_value

        if not result["owner_email"] and domain and _use_hunter:
            hunter_data = await hunter_domain_search(domain)
        elif not result["owner_email"] and domain and not _use_hunter:
            reason = "chain" if _is_chain else f"low priority ({prospect.priority_score or 0})"
            logger.info("Hunter.io skipped for %s — %s", domain, reason)
            hunter_data = {"emails": [], "organization": None}
        else:
            hunter_data = {"emails": [], "organization": None}

            # Extract org name if we don't have an owner name yet
            if hunter_data.get("organization") and not result["owner_name"]:
                pass  # org name ≠ person name, skip

            for h_email in hunter_data.get("emails", []):
                email_addr = h_email["email"]
                # Skip generic/role emails if we can — prefer personal
                if h_email.get("type") == "generic" and is_role_email(email_addr):
                    continue

                # Hunter confidence ≥ 70 is good enough, verify via SMTP if we can
                if h_email.get("confidence", 0) >= 50:
                    verification = await verify_email(email_addr)
                    if verification["score"] >= 50 or h_email["confidence"] >= 80:
                        result["owner_email"] = email_addr
                        result["email_source"] = "hunter.io"
                        result["email_verified"] = verification["smtp_valid"]
                        result["email_score"] = max(verification["score"], h_email["confidence"])

                        # Bonus: hunter gives us name + title
                        if h_email.get("first_name") and not result["owner_name"]:
                            name_parts = [h_email["first_name"]]
                            if h_email.get("last_name"):
                                name_parts.append(h_email["last_name"])
                            result["owner_name"] = " ".join(name_parts)

                        logger.info("Hunter.io hit: %s → %s (confidence=%d)",
                                    domain, email_addr, h_email["confidence"])
                        break
                await asyncio.sleep(0.3)

            # Fallback: accept even generic Hunter emails if nothing better
            if not result["owner_email"] and hunter_data.get("emails"):
                best = hunter_data["emails"][0]  # already sorted by type+confidence
                if best["confidence"] >= 60:
                    result["owner_email"] = best["email"]
                    result["email_source"] = "hunter.io"
                    result["email_verified"] = False
                    result["email_score"] = best["confidence"]
                    if best.get("first_name") and not result["owner_name"]:
                        result["owner_name"] = f"{best['first_name']} {best.get('last_name', '')}".strip()

        # ─── Step 4: Pattern Guess + SMTP Verify ──────────────────
        if not result["owner_email"] and domain:
            name = result["owner_name"] or prospect.owner_name
            guesses = generate_email_guesses(name, domain) if name else [
                f"info@{domain}", f"contact@{domain}", f"hello@{domain}",
            ]

            for email in guesses:
                verification = await verify_email(email)
                if verification["smtp_valid"]:
                    result["owner_email"] = email
                    result["email_source"] = "pattern_guess"
                    result["email_verified"] = True
                    result["email_score"] = verification["score"]
                    break
                elif verification["score"] >= 50:
                    result["owner_email"] = email
                    result["email_source"] = "pattern_guess"
                    result["email_verified"] = False
                    result["email_score"] = verification["score"]
                    # Don't break — keep looking for verified
                await asyncio.sleep(0.5)  # Rate limit SMTP checks

        # ─── Step 5: Fallback ─────────────────────────────────────
        if not result["owner_email"] and domain:
            result["owner_email"] = f"info@{domain}"
            result["email_source"] = "fallback"
            result["email_verified"] = False
            result["email_score"] = 20

        # ─── Update Prospect ──────────────────────────────────────
        if result["owner_name"]:
            prospect.owner_name = result["owner_name"]
        if result["owner_email"]:
            prospect.owner_email = result["owner_email"]
            prospect.email_source = result["email_source"]
            prospect.email_verified = result["email_verified"]
        if result["linkedin"]:
            prospect.owner_linkedin = result["linkedin"]
        if result["phone"] and not prospect.phone:
            prospect.phone = result["phone"]

        # Move to "enriched" status
        if prospect.status == "audited":
            prospect.status = "enriched"

        await db.commit()

        # Notifications
        if result["owner_email"]:
            await notify_recon(
                prospect.business_name,
                result["owner_email"],
                result["email_source"],
                result["email_verified"],
            )
            await _safe_set(f"outreach/stats/last_recon", {
                "name": prospect.business_name,
                "email": result["owner_email"],
                "verified": result["email_verified"],
                "ts": int(_time.time()),
            })

        logger.info(
            "Recon done: %s → %s (%s, verified=%s)",
            prospect.business_name,
            result["owner_email"],
            result["email_source"],
            result["email_verified"],
        )
        return result


async def batch_recon_prospects(limit: int = 10) -> int:
    """
    Recon up to `limit` audited prospects without emails.
    Returns count of prospects with emails found.
    """
    async with async_session_factory() as db:
        from sqlalchemy import select
        rows = await db.execute(
            select(Prospect.id)
            .where(
                Prospect.status == "audited",
                Prospect.owner_email.is_(None),
            )
            .order_by(Prospect.priority_score.desc())
            .limit(limit)
        )
        prospect_ids = [str(r[0]) for r in rows.fetchall()]

    count = 0
    for pid in prospect_ids:
        result = await recon_prospect(pid)
        if result and result.get("owner_email"):
            count += 1
        await asyncio.sleep(1)  # Rate limiting

    return count
