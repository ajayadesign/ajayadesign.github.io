"""
AjayaDesign Automation — Bounce Recovery Service.

Uses crawl4ai to crawl bounced prospects' websites, extract valid
email addresses, and re-enqueue them.  Falls back to phone_outreach
when no email can be found.

Pipeline per prospect:
  1. Crawl website (contact → about → homepage) with crawl4ai
  2. Regex-extract all emails from HTML + markdown
  3. Filter out generic/platform/bounced addresses
  4. Ask our AI service to pick the best owner/direct email
  5. MX-verify the chosen domain actually accepts mail
  6. Update prospect email & re-enqueue  (or → phone_outreach)
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import dns.resolver
from sqlalchemy import select

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import Prospect, OutreachEmail

logger = logging.getLogger("outreach.bounce_recovery")

# ── Regex ────────────────────────────────────────────────
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.ASCII
)

# Emails / domains we never want
IGNORE_PREFIXES = {
    "noreply@", "no-reply@", "mailer-daemon@", "postmaster@",
    "webmaster@", "hostmaster@", "abuse@", "root@", "admin@",
    "sentry@", "privacy@", "support@wix", "support@squarespace",
    "support@godaddy", "support@shopify", "trustandsafety@",
}
IGNORE_DOMAINS = {
    "sentry.io", "google.com", "facebook.com", "twitter.com",
    "instagram.com", "youtube.com", "linkedin.com", "wix.com",
    "squarespace.com", "godaddy.com", "cloudflare.com",
    "amazonaws.com", "googleusercontent.com", "apple.com",
    "microsoft.com", "outlook.com", "yahoo.com", "w3.org",
    "schema.org", "example.com", "placeholder.com",
    "gravatar.com", "wordpress.com", "wp.com",
}

# Contact page path candidates (tried in order)
CONTACT_PATHS = [
    "/contact", "/contact-us", "/contact.html", "/contacto",
    "/about", "/about-us", "/about.html",
    "/",  # homepage last resort
]


# ── Helpers ──────────────────────────────────────────────

def _is_ignorable(email_addr: str) -> bool:
    """Return True if the email should be ignored."""
    lower = email_addr.lower()
    for prefix in IGNORE_PREFIXES:
        if lower.startswith(prefix):
            return True
    domain = lower.split("@", 1)[-1]
    if domain in IGNORE_DOMAINS:
        return True
    # Skip image/css filenames that look like emails
    if any(lower.endswith(ext) for ext in (".png", ".jpg", ".gif", ".svg", ".css", ".js")):
        return True
    return False


def _extract_emails(text: str) -> set[str]:
    """Pull all email-like strings from text, filtering garbage."""
    raw = set(EMAIL_RE.findall(text))
    return {e.lower() for e in raw if not _is_ignorable(e)}


def _domain_of(email_addr: str) -> str:
    return email_addr.rsplit("@", 1)[-1].lower()


async def _has_mx(domain: str) -> bool:
    """Check if a domain has MX records (can receive email)."""
    try:
        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None, lambda: dns.resolver.resolve(domain, "MX")
        )
        return len(answers) > 0
    except Exception:
        return False


def _contact_urls(base_url: str) -> list[str]:
    """Generate candidate contact page URLs from a base website URL."""
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    seen = set()
    urls = []
    for path in CONTACT_PATHS:
        url = urljoin(origin, path)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


# ── Core: crawl a single prospect ────────────────────────

async def recover_email_by_crawl(prospect_id: str) -> dict:
    """Crawl a bounced prospect's website to find a valid email.

    Returns dict with keys: status, email|phone, message
    """
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return {"status": "error", "message": "Prospect not found"}

        website = prospect.website_url
        if not website:
            # No website — fall back to phone
            if prospect.phone:
                prospect.status = "phone_outreach"
                prospect.notes = (prospect.notes or "") + "\n📞 No website — switched to phone outreach"
                await db.commit()
                return {"status": "phone_outreach", "phone": prospect.phone}
            return {"status": "error", "message": "No website and no phone"}

        old_email = prospect.owner_email or ""
        bounced_domain = _domain_of(old_email) if old_email else ""

        # ── Step 1: Crawl contact pages ──────────────────
        logger.info(f"🔍 Crawling {prospect.business_name} → {website}")
        all_emails: set[str] = set()
        page_texts: list[str] = []

        browser_cfg = BrowserConfig(
            headless=True,
            verbose=False,
        )
        run_cfg = CrawlerRunConfig(
            word_count_threshold=1,
            exclude_external_links=True,
            exclude_social_media_links=True,
            page_timeout=30000,
            wait_until="domcontentloaded",
        )

        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                urls_to_try = _contact_urls(website)
                for url in urls_to_try:
                    try:
                        result = await crawler.arun(url=url, config=run_cfg)
                        if result and result.success:
                            # Extract emails from HTML
                            if result.html:
                                all_emails |= _extract_emails(result.html)
                            # Extract from markdown (cleaner text)
                            md = ""
                            if hasattr(result, "markdown") and result.markdown:
                                if isinstance(result.markdown, str):
                                    md = result.markdown
                                elif hasattr(result.markdown, "raw_markdown"):
                                    md = result.markdown.raw_markdown or ""
                                elif hasattr(result.markdown, "fit_markdown"):
                                    md = result.markdown.fit_markdown or ""
                            if md:
                                all_emails |= _extract_emails(md)
                                page_texts.append(md[:3000])  # keep first 3k chars

                            # If we found candidate emails, stop crawling more pages
                            candidates = all_emails - {old_email.lower()}
                            if candidates:
                                logger.info(
                                    f"  Found {len(candidates)} candidate(s) on {url}"
                                )
                                break
                    except Exception as e:
                        logger.warning(f"  Failed to crawl {url}: {e}")
                        continue
        except Exception as e:
            logger.error(f"  Browser error for {prospect.business_name}: {e}")
            # Fall through to phone fallback

        # Remove the already-bounced email
        all_emails.discard(old_email.lower())

        # ── Step 2: Pick best email ──────────────────────
        best_email = await _pick_best_email(
            prospect, all_emails, page_texts, bounced_domain
        )

        if best_email:
            # ── Step 3: MX verify ────────────────────────
            domain = _domain_of(best_email)
            has_mx = await _has_mx(domain)
            if has_mx:
                logger.info(
                    f"  ✅ Recovered {prospect.business_name}: "
                    f"{old_email} → {best_email} (MX verified)"
                )
                prospect.owner_email = best_email
                prospect.email_source = "crawl4ai_recovery"
                prospect.email_verified = False
                prospect.status = "enriched"
                prospect.notes = (
                    (prospect.notes or "")
                    + f"\n🔄 Email recovered via crawl4ai: {old_email} → {best_email}"
                )
                await db.commit()
                return {
                    "status": "recovered",
                    "old_email": old_email,
                    "new_email": best_email,
                    "method": "crawl4ai",
                }
            else:
                logger.warning(
                    f"  ⚠️ {best_email} has no MX records — skipping"
                )

        # ── Step 4: Fallback to phone ────────────────────
        if prospect.phone:
            prospect.status = "phone_outreach"
            prospect.notes = (
                (prospect.notes or "")
                + "\n📞 crawl4ai found no valid email — switched to phone outreach"
            )
            await db.commit()
            logger.info(
                f"  📞 {prospect.business_name} → phone_outreach ({prospect.phone})"
            )
            return {
                "status": "phone_outreach",
                "phone": prospect.phone,
                "emails_found": list(all_emails)[:5],
            }

        # No email, no phone — truly dead
        logger.info(f"  💀 {prospect.business_name} — no recovery path")
        return {
            "status": "no_email_found",
            "message": "No valid email found and no phone number",
            "emails_found": list(all_emails)[:5],
        }


async def _pick_best_email(
    prospect: Prospect,
    candidates: set[str],
    page_texts: list[str],
    bounced_domain: str,
) -> Optional[str]:
    """Use AI to pick the best email from candidates, or return the
    highest-confidence one based on heuristics."""

    if not candidates:
        return None

    # Quick win: exactly one candidate
    if len(candidates) == 1:
        return candidates.pop()

    # Heuristic scoring
    scored: list[tuple[float, str]] = []
    biz_domain = _domain_of(prospect.owner_email or "") if prospect.owner_email else ""
    biz_name_slug = (prospect.business_name or "").lower().replace(" ", "").replace("'", "")

    for email_addr in candidates:
        score = 0.0
        local, domain = email_addr.rsplit("@", 1)

        # Prefer emails on the business's own domain
        if biz_domain and domain == biz_domain and domain != bounced_domain:
            score += 3.0
        # Prefer domains matching business name
        if biz_name_slug and biz_name_slug[:6] in domain.replace(".", ""):
            score += 2.0
        # Prefer owner-like local parts
        if local in ("owner", "info", "contact", "hello", "admin"):
            score += 1.0
        if local in ("orders", "sales", "booking", "reservations"):
            score += 0.5
        # Penalize generic/noreply
        if local.startswith("noreply") or local.startswith("no-reply"):
            score -= 5.0
        # Penalize same domain as bounced (already failed)
        if domain == bounced_domain:
            score -= 2.0

        scored.append((score, email_addr))

    scored.sort(key=lambda x: -x[0])

    # If we have clear winner or <= 3 candidates, use heuristic
    if len(scored) <= 3 or scored[0][0] > scored[1][0] + 1.5:
        return scored[0][1]

    # Use AI for tiebreaker (if available)
    try:
        context = "\n\n".join(page_texts[:2]) if page_texts else ""
        prompt = f"""Pick the BEST direct email for reaching the business owner of "{prospect.business_name}" ({prospect.business_type or 'local business'} in {prospect.city or 'Austin, TX'}).

Their old email {prospect.owner_email} bounced.

Candidate emails found on their website:
{chr(10).join(f'  - {e}' for _, e in scored[:8])}

{f'Website text (excerpt):{chr(10)}{context[:2000]}' if context else ''}

Rules:
- Pick the email most likely to reach a real person / owner
- Prefer the business's own domain
- Avoid generic platform emails (wix, squarespace, etc.)
- Avoid the bounced domain {bounced_domain} unless it's clearly a different valid address

Reply with ONLY the chosen email address, nothing else."""

        response = await call_ai(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
        )
        chosen = response.strip().lower()
        # Validate AI picked one of our candidates
        if chosen in candidates:
            return chosen
        # AI might have returned an email with extra text
        found = EMAIL_RE.findall(chosen)
        if found and found[0].lower() in candidates:
            return found[0].lower()
    except Exception as e:
        logger.warning(f"  AI tiebreaker failed: {e}")

    # Fallback to top heuristic score
    return scored[0][1]


# ── Batch recovery ───────────────────────────────────────

async def batch_recover_bounced() -> dict:
    """Recover all dead+bounced prospects that have websites.
    Called from API route or scheduler."""
    async with async_session_factory() as db:
        bounced_prospect_ids = (
            select(OutreachEmail.prospect_id)
            .where(OutreachEmail.status == "bounced")
            .distinct()
            .subquery()
        )
        q = (
            select(Prospect)
            .where(
                Prospect.id.in_(select(bounced_prospect_ids.c.prospect_id)),
                Prospect.status == "dead",
            )
        )
        result = await db.execute(q)
        prospects = result.scalars().all()

    if not prospects:
        return {"total": 0, "recovered": 0, "phone_outreach": 0, "failed": 0, "details": []}

    logger.info(f"🔍 Batch bounce recovery: {len(prospects)} prospects")
    results = []
    for p in prospects:
        try:
            r = await recover_email_by_crawl(str(p.id))
            results.append({
                "prospect_id": str(p.id),
                "business": p.business_name,
                **r,
            })
        except Exception as e:
            logger.error(f"  Recovery error for {p.business_name}: {e}")
            results.append({
                "prospect_id": str(p.id),
                "business": p.business_name,
                "status": "error",
                "error": str(e),
            })
        # Small delay between crawls to be polite
        await asyncio.sleep(2)

    recovered = sum(1 for r in results if r.get("status") == "recovered")
    phone = sum(1 for r in results if r.get("status") == "phone_outreach")
    failed = sum(1 for r in results if r.get("status") in ("error", "no_email_found"))

    logger.info(
        f"🔍 Batch done: {recovered} recovered, {phone} → phone, {failed} failed"
    )
    return {
        "total": len(results),
        "recovered": recovered,
        "phone_outreach": phone,
        "failed": failed,
        "details": results,
    }
