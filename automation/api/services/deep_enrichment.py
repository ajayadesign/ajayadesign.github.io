"""
Deep Enrichment Engine — Collect 80+ data points per business.

Runs AFTER audit, BEFORE recon.  Each enrichment function hits free
external sources (DNS lookups, Google Places detail, social HEAD checks,
public record APIs) with respectful rate limiting.

Pipeline state: audited → enriching → enriched
"""

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
import dns.resolver
import dns.asyncresolver

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import Prospect

logger = logging.getLogger("outreach.enrichment")

# ── Rate limiting ──────────────────────────────────────────────────────
_DELAY_BETWEEN_STEPS = 1.0  # seconds between enrichment sub-steps
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)
_USER_AGENT = "Mozilla/5.0 AjayaDesign EnrichBot/1.0"


# ═══════════════════════════════════════════════════════════════════════
# 3A. GBP Deep Enrichment
# ═══════════════════════════════════════════════════════════════════════

async def enrich_gbp(place_id: str) -> dict:
    """
    Pull extended fields from Google Places API (New) — Place Details.
    Uses the same API key as discovery.  Requests extra fields that the
    initial search didn't include.
    """
    api_key = settings.google_maps_api_key
    if not api_key or not place_id:
        return {}

    url = "https://places.googleapis.com/v1/places/" + place_id
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "id,displayName,rating,userRatingCount,reviews,"
            "currentOpeningHours,regularOpeningHours,photos,"
            "editorialSummary,priceLevel,types,primaryType,"
            "websiteUri,formattedAddress,nationalPhoneNumber"
        ),
    }

    try:
        async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning("GBP detail failed for %s: HTTP %d", place_id, resp.status)
                    return {}
                data = await resp.json()
    except Exception as e:
        logger.warning("GBP detail error for %s: %s", place_id, e)
        return {}

    # Parse opening hours completeness
    hours = data.get("regularOpeningHours", {}).get("periods", [])
    hours_days = set()
    for period in hours:
        open_day = period.get("open", {}).get("day")
        if open_day is not None:
            hours_days.add(open_day)
    gbp_hours_complete = len(hours_days) >= 6  # 6+ days listed

    # Photos
    photos = data.get("photos", [])
    gbp_photos_count = len(photos)

    # Reviews analysis
    reviews_raw = data.get("reviews", [])
    review_data = []
    owner_replies = 0
    for r in reviews_raw[:5]:  # API returns up to 5 most relevant
        has_reply = bool(r.get("authorAttribution", {}).get("displayName"))
        # Actually the reply is in r.get('response')
        # The Places API (New) doesn't perfectly expose owner replies
        # but we can check if there's an "originalText" reply field
        owner_replied = "response" in r
        if owner_replied:
            owner_replies += 1
        review_data.append({
            "text": (r.get("text", {}).get("text", ""))[:200],
            "rating": r.get("rating", 0),
            "owner_replied": owner_replied,
            "time": r.get("publishTime", ""),
        })

    total_reviews = data.get("userRatingCount", 0) or 0
    gbp_review_response_rate = (
        (owner_replies / len(reviews_raw) * 100) if reviews_raw else 0.0
    )

    # Review velocity (rough estimate from sample timestamps)
    review_velocity = _estimate_review_velocity(reviews_raw, total_reviews)

    return {
        "gbp_hours_complete": gbp_hours_complete,
        "gbp_photos_count": gbp_photos_count,
        "gbp_categories": data.get("types", []),
        "gbp_primary_type": data.get("primaryType", ""),
        "gbp_price_level": data.get("priceLevel", ""),
        "gbp_summary": (data.get("editorialSummary", {}).get("text", ""))[:300],
        "gbp_reviews": review_data,
        "gbp_review_response_rate": round(gbp_review_response_rate, 1),
        "gbp_review_velocity": round(review_velocity, 2),
    }


def _estimate_review_velocity(reviews: list, total_reviews: int) -> float:
    """Estimate reviews/month from sampled review timestamps."""
    if not reviews or total_reviews <= 0:
        return 0.0
    dates = []
    for r in reviews:
        ts = r.get("publishTime", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                dates.append(dt)
            except (ValueError, TypeError):
                pass
    if len(dates) < 2:
        # Fallback: assume reviews span 2 years
        return total_reviews / 24.0
    span = (max(dates) - min(dates)).days or 1
    # Scale from sample to total
    sample_rate = len(dates) / max(span / 30.0, 1)
    scale = total_reviews / max(len(dates), 1)
    return sample_rate * scale


# ═══════════════════════════════════════════════════════════════════════
# 3B. DNS & Email Intelligence
# ═══════════════════════════════════════════════════════════════════════

async def enrich_dns(domain: str) -> dict:
    """
    Pure DNS lookups — no API key needed.  Uses dnspython async resolver.
    Detects email provider, SPF/DKIM/DMARC, DNS/hosting provider.
    """
    if not domain:
        return {}

    result = {
        "mx_provider": "none",
        "has_professional_email": False,
        "has_spf": False,
        "has_dkim": False,
        "has_dmarc": False,
        "dns_provider": "",
        "hosting_provider": "",
    }

    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = 8  # seconds timeout

    # ── MX Records → email provider ──
    try:
        mx_records = await resolver.resolve(domain, "MX")
        mx_hosts = [str(r.exchange).lower() for r in mx_records]
        result["has_professional_email"] = True

        if any("google" in h or "gmail" in h or "googlemail" in h for h in mx_hosts):
            result["mx_provider"] = "google"
        elif any("outlook" in h or "microsoft" in h for h in mx_hosts):
            result["mx_provider"] = "microsoft"
        elif any("zoho" in h for h in mx_hosts):
            result["mx_provider"] = "zoho"
        elif any("protonmail" in h or "proton" in h for h in mx_hosts):
            result["mx_provider"] = "protonmail"
        elif any("mimecast" in h for h in mx_hosts):
            result["mx_provider"] = "mimecast"
        else:
            result["mx_provider"] = "other"
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, Exception):
        pass

    # ── TXT Records → SPF, DKIM, DMARC ──
    try:
        txt_records = await resolver.resolve(domain, "TXT")
        for rdata in txt_records:
            txt = str(rdata).lower()
            if "v=spf1" in txt:
                result["has_spf"] = True
    except Exception:
        pass

    # DMARC is at _dmarc.domain
    try:
        dmarc_records = await resolver.resolve(f"_dmarc.{domain}", "TXT")
        for rdata in dmarc_records:
            if "v=dmarc1" in str(rdata).lower():
                result["has_dmarc"] = True
    except Exception:
        pass

    # DKIM (check common selectors)
    for selector in ["google", "default", "selector1", "k1"]:
        try:
            dkim_records = await resolver.resolve(f"{selector}._domainkey.{domain}", "TXT")
            if dkim_records:
                result["has_dkim"] = True
                break
        except Exception:
            continue

    # ── NS Records → DNS provider ──
    try:
        ns_records = await resolver.resolve(domain, "NS")
        ns_hosts = [str(r.target).lower() for r in ns_records]
        ns_joined = " ".join(ns_hosts)
        if "cloudflare" in ns_joined:
            result["dns_provider"] = "cloudflare"
        elif "awsdns" in ns_joined:
            result["dns_provider"] = "aws-route53"
        elif "godaddy" in ns_joined or "domaincontrol" in ns_joined:
            result["dns_provider"] = "godaddy"
        elif "google" in ns_joined:
            result["dns_provider"] = "google-cloud"
        elif "digitalocean" in ns_joined:
            result["dns_provider"] = "digitalocean"
        elif "namecheap" in ns_joined or "registrar-servers" in ns_joined:
            result["dns_provider"] = "namecheap"
        else:
            result["dns_provider"] = ns_hosts[0] if ns_hosts else "unknown"
    except Exception:
        pass

    # ── CNAME / A → hosting provider ──
    try:
        try:
            cname = await resolver.resolve(domain, "CNAME")
            cname_target = str(cname[0].target).lower()
            result["hosting_provider"] = _detect_host_from_cname(cname_target)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            # No CNAME — try A record reverse lookup
            a_records = await resolver.resolve(domain, "A")
            if a_records:
                result["hosting_provider"] = str(a_records[0].address)
    except Exception:
        pass

    return result


def _detect_host_from_cname(cname: str) -> str:
    """Detect hosting provider from CNAME target."""
    patterns = {
        "wpengine": "wpengine",
        "squarespace": "squarespace",
        "shopify": "shopify",
        "wix": "wix",
        "weebly": "weebly",
        "netlify": "netlify",
        "vercel": "vercel",
        "github": "github-pages",
        "cloudfront": "aws-cloudfront",
        "amazonaws": "aws",
        "azurewebsites": "azure",
        "godaddy": "godaddy",
        "bluehost": "bluehost",
        "siteground": "siteground",
        "hostgator": "hostgator",
        "dreamhost": "dreamhost",
    }
    for key, provider in patterns.items():
        if key in cname:
            return provider
    return cname[:60]


# ═══════════════════════════════════════════════════════════════════════
# 3C. Social Media Scanner
# ═══════════════════════════════════════════════════════════════════════

async def enrich_social(
    business_name: str,
    website_url: str,
    city: str,
    existing_signals: dict | None = None,
) -> dict:
    """
    Check major social platforms for presence via HEAD requests.
    Also uses social links already extracted from the website HTML
    (passed in existing_signals from scan_page_signals).
    """
    result = {
        "social_facebook": {"exists": False},
        "social_instagram": {"exists": False},
        "social_yelp": {"exists": False},
        "social_youtube": {"exists": False},
        "social_tiktok": {"exists": False},
        "social_linkedin": {"exists": False},
        "social_score": 0,
    }

    # Use social links already found on their website
    on_site = (existing_signals or {}).get("social_links_on_site", {})

    # Normalize business name for URL guessing
    slug = re.sub(r'[^a-z0-9]+', '', business_name.lower())
    slug_dash = re.sub(r'[^a-z0-9]+', '-', business_name.lower()).strip('-')

    checks = {
        "social_facebook": on_site.get("facebook") or f"https://www.facebook.com/{slug}",
        "social_instagram": on_site.get("instagram") or f"https://www.instagram.com/{slug}",
        "social_yelp": on_site.get("yelp") or f"https://www.yelp.com/biz/{slug_dash}-{city.lower()}",
        "social_youtube": on_site.get("youtube"),
        "social_tiktok": on_site.get("tiktok"),
        "social_linkedin": on_site.get("linkedin"),
    }

    score = 0
    async with aiohttp.ClientSession(
        timeout=_HTTP_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    ) as session:
        for key, url in checks.items():
            if not url:
                continue
            if not url.startswith("http"):
                url = f"https://{url}"
            try:
                async with session.head(url, allow_redirects=True) as resp:
                    exists = resp.status == 200
                    result[key] = {"exists": exists, "url": str(resp.url) if exists else None}
                    if exists:
                        score += 15  # each platform worth 15 pts
            except Exception:
                pass
            await asyncio.sleep(0.5)  # be respectful

    # Bonus: if they have social links ON their website, they're engaged
    on_site_count = (existing_signals or {}).get("social_link_count", 0)
    score += min(10, on_site_count * 3)

    result["social_score"] = min(100, score)
    return result


# ═══════════════════════════════════════════════════════════════════════
# 3D. Public Records Lookup (Texas SOS)
# ═══════════════════════════════════════════════════════════════════════

async def enrich_public_records(
    business_name: str,
    state: str = "TX",
    city: str = "",
    business_type: str = "",
) -> dict:
    """
    Check free government databases for business registration info.
    Texas SOS provides a public search API.
    """
    result = {
        "sos_entity_type": None,
        "sos_formation_date": None,
        "sos_status": None,
        "sos_officers": [],
    }

    if state != "TX":
        return result

    # Texas SOS web search (scrape the public search page)
    try:
        search_url = "https://mycpa.cpa.state.tx.us/coa/coaSearchBtn"
        params = {
            "coession": "",
            "coession2": "",
            "coession3": "",
            "pession": "",
            "fession": "",
            "pession2": "",
            "pession3": "",
            "tession": "",
            "nession": business_name[:50],
            "nession2": "",
        }
        async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
            async with session.post(
                search_url,
                data=params,
                headers={"User-Agent": _USER_AGENT},
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Parse basic entity info from results
                    # Look for LLC, Corporation, etc.
                    name_lower = business_name.lower()
                    if "limited liability" in html.lower() or "llc" in html.lower():
                        result["sos_entity_type"] = "llc"
                    elif "corporation" in html.lower() or "inc" in html.lower():
                        result["sos_entity_type"] = "corp"
                    elif "dba" in html.lower() or "assumed name" in html.lower():
                        result["sos_entity_type"] = "dba"

                    # Formation date
                    date_match = re.search(
                        r'(?:file\s*date|formation|organized)[:\s]*(\d{2}/\d{2}/\d{4})',
                        html, re.IGNORECASE,
                    )
                    if date_match:
                        result["sos_formation_date"] = date_match.group(1)

                    # Status
                    if re.search(r'\bactive\b', html, re.IGNORECASE):
                        result["sos_status"] = "active"
                    elif re.search(r'\bforfeited\b', html, re.IGNORECASE):
                        result["sos_status"] = "forfeited"
    except Exception as e:
        logger.debug("TX SOS lookup failed for '%s': %s", business_name, e)

    return result


# ═══════════════════════════════════════════════════════════════════════
# 3E. Advertising & Hiring Intelligence
# ═══════════════════════════════════════════════════════════════════════

async def enrich_ads_and_hiring(
    business_name: str,
    website_url: str = "",
    city: str = "",
) -> dict:
    """
    Check Meta Ad Library and job boards for activity signals.
    """
    result = {
        "runs_meta_ads": False,
        "runs_google_ads": False,
        "ad_platforms": [],
        "is_hiring": False,
        "hiring_roles": [],
        "hiring_count": 0,
    }

    # ── Meta Ad Library ──
    try:
        meta_url = "https://www.facebook.com/ads/library/"
        params = {
            "active_status": "active",
            "ad_type": "all",
            "country": "US",
            "q": business_name,
        }
        async with aiohttp.ClientSession(
            timeout=_HTTP_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as session:
            async with session.get(meta_url, params=params, allow_redirects=True) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # If we find ad results mentioning the business
                    if business_name.lower() in html.lower() and "ad started running" in html.lower():
                        result["runs_meta_ads"] = True
                        result["ad_platforms"].append("meta")
    except Exception as e:
        logger.debug("Meta Ad Library check failed: %s", e)

    await asyncio.sleep(_DELAY_BETWEEN_STEPS)

    # ── Google Ads detection from existing audit data ──
    # If the website HTML contained googleads/adsbygoogle, they run Google Ads
    # This is already detected via page signals — just a note

    # ── Indeed / Hiring signals ──
    try:
        indeed_url = "https://www.indeed.com/jobs"
        params = {"q": f'"{business_name}"', "l": city}
        async with aiohttp.ClientSession(
            timeout=_HTTP_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as session:
            async with session.get(indeed_url, params=params) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Count job cards
                    job_matches = re.findall(r'class="job_seen_beacon"', html)
                    if job_matches:
                        result["is_hiring"] = True
                        result["hiring_count"] = len(job_matches)

                        # Extract role titles
                        titles = re.findall(
                            r'role="heading"[^>]*>([^<]+)',
                            html,
                        )
                        result["hiring_roles"] = list(set(titles[:5]))
                        result["ad_platforms"] = list(set(
                            result["ad_platforms"] + (["indeed"] if titles else [])
                        ))
    except Exception as e:
        logger.debug("Indeed check failed: %s", e)

    return result


# ═══════════════════════════════════════════════════════════════════════
# Orchestrator — called by pipeline worker
# ═══════════════════════════════════════════════════════════════════════

async def deep_enrich_prospect(prospect_id: str) -> dict:
    """
    Run ALL enrichment steps for a single prospect.
    Stores everything in prospects.enrichment JSONB + promoted columns.

    Returns the merged enrichment dict.
    """
    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            logger.warning("Prospect %s not found for enrichment", prospect_id)
            return {}

        # Mark as enriching
        prospect.status = "enriching"
        prospect.updated_at = datetime.now(timezone.utc)
        await db.commit()

        enrichment: dict = dict(prospect.enrichment or {})

        # Extract domain from website URL
        domain = ""
        if prospect.website_url:
            match = re.search(r'https?://(?:www\.)?([^/]+)', prospect.website_url)
            if match:
                domain = match.group(1)

        # Get existing page signals from latest audit
        page_signals = {}
        if prospect.audits:
            latest_audit = sorted(prospect.audits, key=lambda a: a.audited_at or datetime.min, reverse=True)[0]
            page_signals = latest_audit.page_signals or {}

        try:
            # 1. GBP deep enrichment
            if prospect.google_place_id:
                logger.info("Enriching GBP: %s", prospect.business_name)
                gbp_data = await enrich_gbp(prospect.google_place_id)
                enrichment["gbp"] = gbp_data
                # Promote key fields
                prospect.gbp_photos_count = gbp_data.get("gbp_photos_count")
                prospect.review_response_rate = gbp_data.get("gbp_review_response_rate")
                prospect.review_velocity = gbp_data.get("gbp_review_velocity")
                await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 2. DNS intelligence
            if domain:
                logger.info("Enriching DNS: %s", domain)
                dns_data = await enrich_dns(domain)
                enrichment["dns"] = dns_data
                # Promote
                prospect.mx_provider = dns_data.get("mx_provider")
                prospect.has_spf = dns_data.get("has_spf")
                prospect.has_dmarc = dns_data.get("has_dmarc")
                await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 3. Social media scan
            logger.info("Enriching Social: %s", prospect.business_name)
            social_data = await enrich_social(
                business_name=prospect.business_name,
                website_url=prospect.website_url or "",
                city=prospect.city,
                existing_signals=page_signals,
            )
            enrichment["social"] = social_data
            prospect.social_score = social_data.get("social_score")
            has_any_social = any(
                v.get("exists") for k, v in social_data.items()
                if isinstance(v, dict) and "exists" in v
            )
            prospect.has_social = has_any_social
            await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 4. Public records
            logger.info("Enriching Records: %s", prospect.business_name)
            records_data = await enrich_public_records(
                business_name=prospect.business_name,
                state=prospect.state or "TX",
                city=prospect.city,
                business_type=prospect.business_type or "",
            )
            enrichment["records"] = records_data
            prospect.entity_type = records_data.get("sos_entity_type")
            if records_data.get("sos_formation_date"):
                try:
                    prospect.formation_date = datetime.strptime(
                        records_data["sos_formation_date"], "%m/%d/%Y"
                    ).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass
            await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 5. Ads & hiring
            logger.info("Enriching Ads/Hiring: %s", prospect.business_name)
            ads_data = await enrich_ads_and_hiring(
                business_name=prospect.business_name,
                website_url=prospect.website_url or "",
                city=prospect.city,
            )
            enrichment["ads_hiring"] = ads_data
            prospect.is_hiring = ads_data.get("is_hiring", False)
            prospect.hiring_roles = ads_data.get("hiring_roles")
            prospect.runs_ads = ads_data.get("runs_meta_ads", False) or ads_data.get("runs_google_ads", False)
            prospect.ad_platforms = ads_data.get("ad_platforms")

            # ── Finalize ──
            enrichment["enriched_at"] = datetime.now(timezone.utc).isoformat()
            prospect.enrichment = enrichment
            prospect.enriched_at = datetime.now(timezone.utc)
            prospect.status = "enriched"
            prospect.updated_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info("Deep enrichment complete: %s", prospect.business_name)
            return enrichment

        except Exception as e:
            logger.exception("Deep enrichment failed for %s: %s", prospect.business_name, e)
            # Reset to audited so it can be retried
            prospect.status = "audited"
            prospect.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return {}


async def backfill_enrich_prospect(prospect_id: str) -> dict:
    """
    Run all enrichment steps on an EXISTING prospect without changing its
    pipeline status.  This is the backfill-safe variant of deep_enrich_prospect.

    Use for prospects that are already in enriched / queued / contacted / replied
    states — they keep their status, but gain enrichment data + wp_score inputs.
    """
    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            logger.warning("Backfill: prospect %s not found", prospect_id)
            return {}

        original_status = prospect.status
        enrichment: dict = dict(prospect.enrichment or {})

        # Extract domain
        domain = ""
        if prospect.website_url:
            match = re.search(r'https?://(?:www\.)?([^/]+)', prospect.website_url)
            if match:
                domain = match.group(1)

        # Get page signals from latest audit
        page_signals = {}
        if prospect.audits:
            latest_audit = sorted(
                prospect.audits,
                key=lambda a: a.audited_at or datetime.min,
                reverse=True,
            )[0]
            page_signals = latest_audit.page_signals or {}

        try:
            # 1. GBP
            if prospect.google_place_id and "gbp" not in enrichment:
                logger.info("Backfill GBP: %s", prospect.business_name)
                gbp_data = await enrich_gbp(prospect.google_place_id)
                enrichment["gbp"] = gbp_data
                prospect.gbp_photos_count = gbp_data.get("gbp_photos_count")
                prospect.review_response_rate = gbp_data.get("gbp_review_response_rate")
                prospect.review_velocity = gbp_data.get("gbp_review_velocity")
                await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 2. DNS
            if domain and "dns" not in enrichment:
                logger.info("Backfill DNS: %s", domain)
                dns_data = await enrich_dns(domain)
                enrichment["dns"] = dns_data
                prospect.mx_provider = dns_data.get("mx_provider")
                prospect.has_spf = dns_data.get("has_spf")
                prospect.has_dmarc = dns_data.get("has_dmarc")
                await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 3. Social
            if "social" not in enrichment:
                logger.info("Backfill Social: %s", prospect.business_name)
                social_data = await enrich_social(
                    business_name=prospect.business_name,
                    website_url=prospect.website_url or "",
                    city=prospect.city,
                    existing_signals=page_signals,
                )
                enrichment["social"] = social_data
                prospect.social_score = social_data.get("social_score")
                has_any_social = any(
                    v.get("exists") for k, v in social_data.items()
                    if isinstance(v, dict) and "exists" in v
                )
                prospect.has_social = has_any_social
                await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 4. Public records
            if "records" not in enrichment:
                logger.info("Backfill Records: %s", prospect.business_name)
                records_data = await enrich_public_records(
                    business_name=prospect.business_name,
                    state=prospect.state or "TX",
                    city=prospect.city,
                    business_type=prospect.business_type or "",
                )
                enrichment["records"] = records_data
                prospect.entity_type = records_data.get("sos_entity_type")
                if records_data.get("sos_formation_date"):
                    try:
                        prospect.formation_date = datetime.strptime(
                            records_data["sos_formation_date"], "%m/%d/%Y"
                        ).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass
                await asyncio.sleep(_DELAY_BETWEEN_STEPS)

            # 5. Ads & hiring
            if "ads_hiring" not in enrichment:
                logger.info("Backfill Ads/Hiring: %s", prospect.business_name)
                ads_data = await enrich_ads_and_hiring(
                    business_name=prospect.business_name,
                    website_url=prospect.website_url or "",
                    city=prospect.city,
                )
                enrichment["ads_hiring"] = ads_data
                prospect.is_hiring = ads_data.get("is_hiring", False)
                prospect.hiring_roles = ads_data.get("hiring_roles")
                prospect.runs_ads = (
                    ads_data.get("runs_meta_ads", False)
                    or ads_data.get("runs_google_ads", False)
                )
                prospect.ad_platforms = ads_data.get("ad_platforms")

            # ── Finalize (preserve original status) ──
            enrichment["enriched_at"] = datetime.now(timezone.utc).isoformat()
            enrichment["backfill"] = True
            prospect.enrichment = enrichment
            prospect.enriched_at = datetime.now(timezone.utc)
            # Do NOT change status — keep queued/contacted/etc as-is
            prospect.updated_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(
                "Backfill enrichment complete: %s (status kept as %s)",
                prospect.business_name, original_status,
            )
            return enrichment

        except Exception as e:
            logger.exception(
                "Backfill enrichment failed for %s: %s",
                prospect.business_name, e,
            )
            await db.rollback()
            return {}
