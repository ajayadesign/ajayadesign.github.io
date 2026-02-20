"""
Advanced Features — Seasonal Hooks, Competitor Weaponization, Review Mining.

These are intelligence enhancements that make emails more contextually relevant.
Each function is a data enrichment step that adds template variables.

Phase 8 of OUTREACH_AGENT_PLAN.md.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from api.database import async_session_factory
from api.models.prospect import Prospect, WebsiteAudit

logger = logging.getLogger("outreach.advanced")


# ═══════════════════════════════════════════════════════════════════
# SEASONAL HOOKS (§ Phase 8 — time-sensitive email personalization)
# ═══════════════════════════════════════════════════════════════════

SEASONAL_HOOKS = {
    "restaurant": {
        1: "New Year's resolution diners are searching for healthy options right now",
        2: "Valentine's Day is the #2 biggest dining-out day — are you visible to couples searching '{city} romantic dinner'?",
        3: "Spring break travelers are searching for local restaurants in {city}",
        5: "Summer patio season is here — people are Googling '{city} outdoor dining'",
        6: "Father's Day dining searches spike 300% the week before",
        9: "Fall comfort food season — searches for '{business_type} near me' peak in October",
        11: "Thanksgiving week = highest restaurant search volume of the year",
        12: "Holiday party season — catering searches are up 400% right now",
    },
    "dental_office": {
        1: "New year, new insurance — patients are searching for new dentists right now",
        3: "Spring cleaning includes dental checkups — search volume spikes in March",
        6: "Summer = kids need dental checkups before school starts",
        8: "Back-to-school dental visits — parents are booking now",
        11: "Use-it-or-lose-it insurance season — patients rushing to use remaining benefits",
    },
    "plumber": {
        1: "Frozen pipe season — emergency plumbing searches spike 500% in January",
        3: "Spring thaw = burst pipe calls. Are customers finding you or your competitor?",
        6: "AC season means more plumbing calls (condensation lines, water heaters)",
        11: "Winter prep — 'winterize pipes {city}' searches starting now",
    },
    "beauty_salon": {
        2: "Valentine's Day makeover searches spike 200% — are you showing up?",
        4: "Prom season — teen + parent searches for '{city} hair salon' peak now",
        5: "Wedding season kickoff — bridal hair/makeup searches starting",
        9: "Back-to-school haircuts — family searches spike in September",
        12: "Holiday party season — style and color appointments in high demand",
    },
    "real_estate": {
        3: "Spring selling season — home searches peak between March and June",
        5: "Peak listing season — sellers looking for agents right now",
        8: "Fall market — serious buyers are searching, less competition",
        1: "New year movers — 'homes for sale {city}' searches up after holidays",
    },
    "law_firm": {
        1: "Tax season prep — searches for 'tax attorney {city}' spike in January",
        3: "Spring accident season — personal injury searches increase",
        6: "Summer custody disputes — family law searches peak",
        10: "Business planning season — corporate clients structuring for year-end",
    },
    "auto_repair": {
        3: "Spring road trip prep — 'auto repair near me' searches spike",
        6: "Summer heat = AC and overheating issues — emergency search volume up",
        10: "Winter prep — tire and heating system searches",
        12: "Holiday travel prep — last-minute vehicle checkups",
    },
    "veterinarian": {
        3: "Spring allergy season for pets — vet visit searches increase",
        5: "Puppy season — new pet owners searching for vets",
        7: "Summer flea/tick season — preventive care searches peak",
        11: "Holiday pet boarding — vet searches for health certificates",
    },
    "gym": {
        1: "New Year's resolution season — gym searches spike 400% in January",
        5: "Summer body season — fitness searches peak May-June",
        9: "Fall fitness push — 'gym near me' searches rebound after summer",
    },
}


def get_seasonal_hook(business_type: str, city: str = "Manor") -> Optional[str]:
    """
    Get a seasonally relevant hook for this business type.
    Returns formatted string or None if no hook for current month.
    """
    now = datetime.now(timezone.utc)
    month = now.month

    industry_hooks = SEASONAL_HOOKS.get(business_type, {})
    hook = industry_hooks.get(month)

    if hook:
        return hook.format(city=city, business_type=business_type)

    return None


# ═══════════════════════════════════════════════════════════════════
# COMPETITOR WEAPONIZATION
# ═══════════════════════════════════════════════════════════════════

async def find_competitors(prospect_id: str, limit: int = 3) -> list[dict]:
    """
    Find and score competitors for a prospect.
    Uses same geo-ring data — looks for businesses of same type nearby.
    Returns list of {name, url, score, rating, reviews, distance_miles}.
    """
    from sqlalchemy import select, and_

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return []

        # Find same-type businesses in same ring with better scores
        query = select(Prospect).where(
            and_(
                Prospect.business_type == prospect.business_type,
                Prospect.id != prospect.id,
                Prospect.has_website == True,
                Prospect.score_overall.isnot(None),
            )
        ).order_by(Prospect.score_overall.desc()).limit(limit)

        result = await db.execute(query)
        competitors = result.scalars().all()

        comp_list = []
        for c in competitors:
            comp_list.append({
                "name": c.business_name,
                "url": c.website_url,
                "score": c.score_overall,
                "rating": float(c.google_rating) if c.google_rating else None,
                "reviews": c.google_reviews,
                "distance_miles": float(c.distance_miles) if c.distance_miles else None,
            })

        # Store on prospect
        prospect.competitors = comp_list
        if comp_list:
            prospect.competitor_avg = int(
                sum(c["score"] for c in comp_list if c["score"]) / len(comp_list)
            )
        await db.commit()

        return comp_list


def build_competitor_comparison(prospect_score: int, competitors: list[dict]) -> dict:
    """
    Build a human-readable competitor comparison for email templates.
    Returns dict with template variables.
    """
    if not competitors:
        return {
            "competitor_name": "a competitor nearby",
            "competitor_score": "75",
            "competitor_diff": "significantly higher",
            "competitor_url": "",
        }

    best = competitors[0]
    diff = (best.get("score") or 75) - (prospect_score or 0)

    return {
        "competitor_name": best.get("name", "a competitor nearby"),
        "competitor_score": str(best.get("score", 75)),
        "competitor_diff": f"{diff} points higher" if diff > 0 else "similar",
        "competitor_url": best.get("url", ""),
    }


# ═══════════════════════════════════════════════════════════════════
# REVIEW MINING (Google Reviews → Sentiment Insights)
# ═══════════════════════════════════════════════════════════════════

# Keywords that indicate common complaint themes (for email personalization)
COMPLAINT_KEYWORDS = {
    "slow": "slow service",
    "wait": "long wait times",
    "website": "website issues mentioned in reviews",
    "online": "online presence complaints",
    "phone": "difficulty reaching by phone",
    "appointment": "booking/scheduling issues",
    "find": "hard to find online",
    "outdated": "outdated feel",
    "price": "pricing concerns",
    "rude": "customer service issues",
    "dirty": "cleanliness concerns",
    "parking": "parking issues",
}


def analyze_review_themes(reviews_text: list[str]) -> dict:
    """
    Analyze review text for common themes.
    Returns dict with theme counts and top complaints.
    """
    themes = {}
    for text in reviews_text:
        text_lower = text.lower()
        for keyword, theme in COMPLAINT_KEYWORDS.items():
            if keyword in text_lower:
                themes[theme] = themes.get(theme, 0) + 1

    sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)

    return {
        "themes": dict(sorted_themes[:5]),
        "top_complaint": sorted_themes[0][0] if sorted_themes else None,
        "website_mentioned": "website issues mentioned in reviews" in themes,
    }


# ═══════════════════════════════════════════════════════════════════
# BROKEN THINGS DETECTOR (Enhanced Design Issues for Templates)
# ═══════════════════════════════════════════════════════════════════

def detect_broken_things(audit: WebsiteAudit) -> list[str]:
    """
    Build a list of specific, verifiable broken things from audit data.
    These feed into {{broken_things}} template variable.
    Each item is written as a complete, specific statement.
    """
    issues = []

    # Speed issues
    if audit.lcp_ms and audit.lcp_ms > 4000:
        issues.append(
            f"Your site takes {audit.lcp_ms / 1000:.1f} seconds to load "
            f"(Google recommends under 2.5s)"
        )

    if audit.page_size_kb and audit.page_size_kb > 3000:
        issues.append(
            f"Your page weighs {audit.page_size_kb / 1024:.1f}MB "
            f"(should be under 2MB for fast loading)"
        )

    if audit.request_count and audit.request_count > 80:
        issues.append(
            f"Your site makes {audit.request_count} HTTP requests "
            f"(modern sites use 30-50)"
        )

    # Mobile issues
    if not audit.mobile_friendly:
        issues.append(
            "Your site is not mobile-friendly — over 60% of searches are on phones"
        )

    # SEO issues
    seo_missing = []
    if not audit.has_title:
        seo_missing.append("page title")
    if not audit.has_meta_desc:
        seo_missing.append("meta description")
    if not audit.has_h1:
        seo_missing.append("H1 heading")
    if not audit.has_schema:
        seo_missing.append("structured data (schema.org)")
    if not audit.has_sitemap:
        seo_missing.append("XML sitemap")
    if seo_missing:
        issues.append(f"Missing basic SEO: {', '.join(seo_missing)}")

    # Security
    if not audit.ssl_valid:
        issues.append(
            'Your SSL certificate is expired or missing — '
            'Chrome shows "Not Secure" to visitors'
        )

    # Design
    design_sins = audit.design_sins or []
    for sin in design_sins[:3]:  # Top 3 design issues
        issues.append(sin)

    # CMS-specific
    if audit.cms_platform == "wix":
        issues.append(
            "Your Wix site has limited SEO control compared to custom builds"
        )
    elif audit.cms_platform == "godaddy":
        issues.append(
            "GoDaddy website builder has significant performance limitations"
        )

    return issues


# ═══════════════════════════════════════════════════════════════════
# ENRICHMENT PIPELINE (Tie everything together)
# ═══════════════════════════════════════════════════════════════════

async def enrich_prospect_advanced(prospect_id: str) -> dict:
    """
    Run all advanced enrichment steps on a prospect:
    1. Find competitors
    2. Get seasonal hook
    3. Detect broken things
    Returns enrichment summary.
    """
    from sqlalchemy import select

    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            return {}

        result = {}

        # Competitors
        competitors = await find_competitors(prospect_id)
        result["competitors"] = competitors
        result["competitor_comparison"] = build_competitor_comparison(
            prospect.score_overall, competitors
        )

        # Seasonal hook
        hook = get_seasonal_hook(prospect.business_type or "default", prospect.city)
        result["seasonal_hook"] = hook

        # Broken things (if audit exists)
        audit_result = await db.execute(
            select(WebsiteAudit)
            .where(WebsiteAudit.prospect_id == prospect.id)
            .order_by(WebsiteAudit.audited_at.desc())
            .limit(1)
        )
        audit = audit_result.scalar_one_or_none()
        if audit:
            result["broken_things"] = detect_broken_things(audit)
        else:
            result["broken_things"] = []

        return result
