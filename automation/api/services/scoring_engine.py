"""
Scoring Engine — Website Purchase Likelihood Score.

Calculates a 0–100 score predicting how likely a business is to buy a
website from us RIGHT NOW.

    wp_score = NEED (0-40) + ABILITY (0-30) + TIMING (0-30)

Each component is computed from concrete, evidence-based signals collected
during the audit and deep enrichment phases.

Called by pipeline worker after enrichment, before enqueue.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from api.database import async_session_factory
from api.models.prospect import Prospect, WebsiteAudit

logger = logging.getLogger("outreach.scoring")


# ═══════════════════════════════════════════════════════════════════════
# Component 1: NEED (0–40)
# How badly do they need a new website?
# ═══════════════════════════════════════════════════════════════════════

def _score_need(
    has_website: bool,
    score_overall: Optional[int],
    score_mobile: Optional[int],
    ssl_valid: Optional[bool],
    design_era: Optional[str],
    design_sins: list,
    website_platform: Optional[str],
    page_signals: dict,
) -> tuple[int, list[str]]:
    """Returns (score, list_of_signals_matched)."""
    points = 0
    signals = []

    # ── Base score from website quality ──
    if not has_website:
        points += 40
        signals.append("no_website:+40")
        return min(points, 40), signals

    s = score_overall or 100
    if s <= 19:
        points += 35
        signals.append(f"score_{s}:+35")
    elif s <= 29:
        points += 30
        signals.append(f"score_{s}:+30")
    elif s <= 39:
        points += 25
        signals.append(f"score_{s}:+25")
    elif s <= 59:
        points += 15
        signals.append(f"score_{s}:+15")
    else:
        points += 5
        signals.append(f"score_{s}:+5")

    # ── Bonus signals on top of base ──
    if score_mobile is not None and score_mobile < 50:
        points += 5
        signals.append("bad_mobile:+5")

    if ssl_valid is False:
        points += 3
        signals.append("no_ssl:+3")

    # Design era penalties
    era = (design_era or "").lower()
    if "prehistoric" in era or "pre-2010" in era:
        points += 5
        signals.append("ancient_design:+5")
    elif "ancient" in era or "2010" in era:
        points += 4
        signals.append("dated_2010_design:+4")
    elif "dated" in era or "2015" in era:
        points += 3
        signals.append("dated_2015_design:+3")

    # Design sins
    sins_lower = [s.lower() for s in (design_sins or [])]
    if any("flash" in s for s in sins_lower):
        points += 5
        signals.append("flash_detected:+5")
    if any("under construction" in s for s in sins_lower):
        points += 5
        signals.append("under_construction:+5")
    if any("lorem ipsum" in s for s in sins_lower):
        points += 5
        signals.append("lorem_ipsum:+5")
    if any("copyright" in s for s in sins_lower):
        # Stale copyright year
        points += 3
        signals.append("stale_copyright:+3")

    # Free platform (subdomain)
    if website_platform and website_platform.lower() in ("wix", "weebly", "godaddy builder"):
        # Check if they're on a free subdomain
        points += 2
        signals.append(f"free_platform_{website_platform}:+2")

    # Missing key page elements
    if not page_signals.get("has_contact_form"):
        points += 2
        signals.append("no_contact_form:+2")
    if not page_signals.get("has_cta_above_fold"):
        points += 2
        signals.append("no_cta:+2")
    if not page_signals.get("has_click_to_call"):
        points += 1
        signals.append("no_click_to_call:+1")

    return min(points, 40), signals


# ═══════════════════════════════════════════════════════════════════════
# Component 2: ABILITY (0–30)
# Can they afford to pay for a website?
# ═══════════════════════════════════════════════════════════════════════

def _score_ability(
    google_reviews: Optional[int],
    google_rating: Optional[float],
    ppp_loan_amount: Optional[int],
    is_hiring: bool,
    runs_ads: bool,
    entity_type: Optional[str],
    mx_provider: Optional[str],
    website_platform: Optional[str],
    formation_date: Optional[datetime],
    hiring_roles: list | None,
) -> tuple[int, list[str]]:
    """Returns (score, list_of_signals_matched)."""
    points = 0
    signals = []

    # ── PPP loan (confirmed revenue proxy) ──
    ppp = ppp_loan_amount or 0
    if ppp > 150_000:
        points += 10
        signals.append(f"ppp_{ppp}:+10")
    elif ppp > 50_000:
        points += 6
        signals.append(f"ppp_{ppp}:+6")
    elif ppp > 0:
        points += 3
        signals.append(f"ppp_{ppp}:+3")

    # ── Google reviews (customer volume proxy) ──
    reviews = google_reviews or 0
    if reviews > 200:
        points += 8
        signals.append(f"reviews_{reviews}:+8")
    elif reviews > 50:
        points += 5
        signals.append(f"reviews_{reviews}:+5")
    elif reviews > 10:
        points += 3
        signals.append(f"reviews_{reviews}:+3")

    # ── Google rating ──
    rating = google_rating or 0
    if rating >= 4.5:
        points += 3
        signals.append(f"rating_{rating}:+3")
    elif rating >= 4.0:
        points += 1
        signals.append(f"rating_{rating}:+1")

    # ── Growth signals ──
    if is_hiring:
        points += 5
        signals.append("hiring:+5")
    if runs_ads:
        points += 5
        signals.append("runs_ads:+5")
    if hiring_roles and len(hiring_roles) > 1:
        points += 3
        signals.append("multi_hire:+3")

    # ── Business formality ──
    etype = (entity_type or "").lower()
    if etype in ("llc", "corp", "corporation"):
        points += 3
        signals.append(f"entity_{etype}:+3")
    elif etype in ("sole_prop", "dba"):
        points += 1
        signals.append(f"entity_{etype}:+1")

    # ── Email sophistication ──
    mx = (mx_provider or "").lower()
    if mx in ("google", "microsoft"):
        points += 2
        signals.append(f"mx_{mx}:+2")

    # ── Already paying for web presence ──
    plat = (website_platform or "").lower()
    if plat in ("squarespace", "shopify", "wix"):
        points += 2
        signals.append(f"paid_platform_{plat}:+2")

    # ── New business (investing in setup) ──
    if formation_date:
        months_old = (datetime.now(timezone.utc) - formation_date).days / 30
        if months_old < 24:
            points += 3
            signals.append("new_biz_under_2yr:+3")

    return min(points, 30), signals


# ═══════════════════════════════════════════════════════════════════════
# Component 3: TIMING (0–30)
# Are external triggers making them ready RIGHT NOW?
# ═══════════════════════════════════════════════════════════════════════

def _score_timing(
    has_website: bool,
    score_overall: Optional[int],
    design_sins: list,
    formation_date: Optional[datetime],
    is_hiring: bool,
    hiring_roles: list | None,
    runs_ads: bool,
    review_velocity: Optional[float],
    has_social: bool,
    social_score: Optional[int],
    competitors: list | None,
    competitor_avg: Optional[int],
    enrichment: dict,
    page_signals: dict,
) -> tuple[int, list[str]]:
    """Returns (score, list_of_signals_matched)."""
    points = 0
    signals = []

    # ── Under construction / coming soon ──
    sins_lower = [s.lower() for s in (design_sins or [])]
    if any("under construction" in s for s in sins_lower):
        points += 8
        signals.append("under_construction_timing:+8")

    # ── Brand new business ──
    if formation_date:
        months_old = (datetime.now(timezone.utc) - formation_date).days / 30
        if months_old < 6:
            points += 8
            signals.append("new_biz_under_6mo:+8")
        elif months_old < 12:
            points += 5
            signals.append("new_biz_under_12mo:+5")

    # ── Running ads + bad website = burning money ──
    if runs_ads and has_website and (score_overall or 100) < 50:
        points += 8
        signals.append("ads_plus_bad_site:+8")

    # ── Hiring marketing/web person ──
    roles = [r.lower() for r in (hiring_roles or [])]
    if any(kw in r for r in roles for kw in ("market", "web", "digital", "social", "design")):
        points += 8
        signals.append("hiring_marketing:+8")
    elif is_hiring:
        points += 3
        signals.append("hiring_generic:+3")

    # ── Competitor pressure ──
    comp_avg = competitor_avg or 0
    own_score = score_overall or 0
    if comp_avg > 0 and own_score > 0 and (comp_avg - own_score) > 30:
        points += 5
        signals.append(f"competitor_gap_{comp_avg - own_score}:+5")
    elif comp_avg > 0 and own_score > 0 and (comp_avg - own_score) > 15:
        points += 3
        signals.append(f"competitor_gap_{comp_avg - own_score}:+3")

    # ── Review complaints about website/online presence ──
    gbp_reviews = enrichment.get("gbp", {}).get("gbp_reviews", [])
    complaint_count = 0
    for review in gbp_reviews:
        text = (review.get("text", "") or "").lower()
        if any(kw in text for kw in ("website", "online", "can't find", "hard to find", "no website")):
            complaint_count += 1
    if complaint_count > 0:
        points += min(5, complaint_count * 3)
        signals.append(f"review_complaints_{complaint_count}:+{min(5, complaint_count * 3)}")

    # ── No social media at all ──
    if not has_social and (social_score or 0) == 0:
        points += 3
        signals.append("no_social:+3")

    # ── Declining review velocity ──
    rv = review_velocity or 0
    if 0 < rv < 1.0:
        points += 3
        signals.append("low_review_velocity:+3")

    # ── GBP deficiencies ──
    gbp = enrichment.get("gbp", {})
    if gbp.get("gbp_photos_count", 999) < 5:
        points += 2
        signals.append("few_gbp_photos:+2")
    if gbp.get("gbp_review_response_rate", 100) < 10:
        points += 2
        signals.append("low_review_response:+2")

    return min(points, 30), signals


# ═══════════════════════════════════════════════════════════════════════
# Main Scoring Function
# ═══════════════════════════════════════════════════════════════════════

def calculate_wp_score(prospect: Prospect, audit: Optional[WebsiteAudit] = None) -> dict:
    """
    Calculate Website Purchase Likelihood Score for a single prospect.

    Returns:
        {
            "wp_score": int (0-100),
            "need": int (0-40),
            "ability": int (0-30),
            "timing": int (0-30),
            "need_signals": [...],
            "ability_signals": [...],
            "timing_signals": [...],
            "tier": "hot" | "warm" | "cool" | "cold",
        }
    """
    page_signals = {}
    design_sins = []
    design_era = None
    if audit:
        page_signals = audit.page_signals or {}
        design_sins = audit.design_sins or []
        design_era = audit.design_era

    enrichment = prospect.enrichment or {}

    # Component 1: NEED
    need, need_signals = _score_need(
        has_website=prospect.has_website or False,
        score_overall=prospect.score_overall,
        score_mobile=prospect.score_mobile,
        ssl_valid=prospect.ssl_valid,
        design_era=design_era,
        design_sins=design_sins,
        website_platform=prospect.website_platform,
        page_signals=page_signals,
    )

    # Component 2: ABILITY
    ability, ability_signals = _score_ability(
        google_reviews=prospect.google_reviews,
        google_rating=float(prospect.google_rating) if prospect.google_rating else None,
        ppp_loan_amount=prospect.ppp_loan_amount,
        is_hiring=prospect.is_hiring or False,
        runs_ads=prospect.runs_ads or False,
        entity_type=prospect.entity_type,
        mx_provider=prospect.mx_provider,
        website_platform=prospect.website_platform,
        formation_date=prospect.formation_date,
        hiring_roles=prospect.hiring_roles,
    )

    # Component 3: TIMING
    timing, timing_signals = _score_timing(
        has_website=prospect.has_website or False,
        score_overall=prospect.score_overall,
        design_sins=design_sins,
        formation_date=prospect.formation_date,
        is_hiring=prospect.is_hiring or False,
        hiring_roles=prospect.hiring_roles,
        runs_ads=prospect.runs_ads or False,
        review_velocity=float(prospect.review_velocity) if prospect.review_velocity else None,
        has_social=prospect.has_social or False,
        social_score=prospect.social_score,
        competitors=prospect.competitors,
        competitor_avg=prospect.competitor_avg,
        enrichment=enrichment,
        page_signals=page_signals,
    )

    wp_score = need + ability + timing

    # Tier classification
    if wp_score >= 80:
        tier = "hot"
    elif wp_score >= 60:
        tier = "warm"
    elif wp_score >= 40:
        tier = "cool"
    else:
        tier = "cold"

    return {
        "wp_score": wp_score,
        "need": need,
        "ability": ability,
        "timing": timing,
        "need_signals": need_signals,
        "ability_signals": ability_signals,
        "timing_signals": timing_signals,
        "tier": tier,
    }


async def score_prospect(prospect_id: str) -> Optional[dict]:
    """
    Calculate and persist wp_score for a single prospect.
    Called by pipeline worker after enrichment.
    """
    async with async_session_factory() as db:
        prospect = await db.get(Prospect, prospect_id)
        if not prospect:
            logger.warning("Prospect %s not found for scoring", prospect_id)
            return None

        # Get latest audit
        audit = None
        if prospect.audits:
            audit = sorted(
                prospect.audits,
                key=lambda a: a.audited_at or datetime.min,
                reverse=True,
            )[0]

        result = calculate_wp_score(prospect, audit)

        # Persist
        prospect.wp_score = result["wp_score"]
        prospect.wp_score_json = result
        prospect.updated_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info(
            "Scored %s: wp_score=%d (need=%d ability=%d timing=%d) → %s",
            prospect.business_name,
            result["wp_score"],
            result["need"],
            result["ability"],
            result["timing"],
            result["tier"],
        )
        return result


async def batch_score_prospects(limit: int = 50) -> int:
    """Score all enriched prospects that haven't been scored yet."""
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(Prospect.id).where(
                Prospect.wp_score.is_(None),
                Prospect.status.in_(["enriched", "queued", "contacted"]),
            ).order_by(Prospect.created_at.asc()).limit(limit)
        )
        ids = [str(r[0]) for r in result.fetchall()]

    count = 0
    for pid in ids:
        r = await score_prospect(pid)
        if r:
            count += 1
    logger.info("Batch scored %d/%d prospects", count, len(ids))
    return count
