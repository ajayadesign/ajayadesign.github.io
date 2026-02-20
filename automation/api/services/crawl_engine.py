"""
Crawl Engine — Business Discovery via Google Maps / Places API.

Discovers local businesses in expanding geo-rings around Manor, TX.
Uses Google Maps Places API (Nearby Search + Place Details).
De-duplicates by google_place_id, phone, and business_name+zip.

Phase 2 of OUTREACH_AGENT_PLAN.md (§4).
"""

import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import aiohttp
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import async_session_factory
from api.models.prospect import GeoRing, Prospect

logger = logging.getLogger("outreach.crawl")

# ─── Constants ─────────────────────────────────────────────────────────
MANOR_LAT = 30.3427
MANOR_LNG = -97.5567
MILES_TO_METERS = 1609.34
PLACES_API_BASE = "https://maps.googleapis.com/maps/api/place"

# Social media domains — NOT a real business website
SOCIAL_MEDIA_DOMAINS = {
    "facebook.com", "fb.com", "m.facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com",
    "twitter.com", "x.com", "www.twitter.com",
    "linkedin.com", "www.linkedin.com",
    "youtube.com", "www.youtube.com",
    "tiktok.com", "www.tiktok.com",
    "yelp.com", "www.yelp.com",
    "nextdoor.com", "www.nextdoor.com",
}


def is_social_media_url(url: str) -> bool:
    """Check if a URL is a social media profile (not a real business website)."""
    if not url:
        return False
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url.lower().strip())
        host = parsed.netloc or parsed.path.split("/")[0]
        host = host.lstrip("www.")
        # Check direct domain match
        if host in SOCIAL_MEDIA_DOMAINS or f"www.{host}" in SOCIAL_MEDIA_DOMAINS:
            return True
        # Also check parent domain (e.g., m.facebook.com)
        parts = host.split(".")
        if len(parts) >= 2:
            parent = ".".join(parts[-2:])
            return parent in SOCIAL_MEDIA_DOMAINS or f"www.{parent}" in SOCIAL_MEDIA_DOMAINS
        return False
    except Exception:
        return False

# Business categories in priority order (§4.3)
TIER_1_CATEGORIES = [
    "restaurant", "dentist", "lawyer", "beauty_salon",
    "real_estate_agency", "veterinary_care", "doctor",
]
TIER_2_CATEGORIES = [
    "plumber", "electrician", "roofing_contractor", "locksmith",
    "car_repair", "hair_care", "gym", "moving_company",
]
TIER_3_CATEGORIES = [
    "store", "photographer", "pet_store", "school",
    "laundry", "florist", "bakery", "cafe",
]
ALL_CATEGORIES = TIER_1_CATEGORIES + TIER_2_CATEGORIES + TIER_3_CATEGORIES

# Industry tag mapping from Google place types
PLACE_TYPE_TO_INDUSTRY = {
    "restaurant": "restaurant", "cafe": "restaurant", "bakery": "bakery",
    "dentist": "dental_office", "doctor": "medical",
    "lawyer": "law_firm", "accounting": "accountant",
    "beauty_salon": "beauty_salon", "hair_care": "hair_salon",
    "real_estate_agency": "real_estate", "veterinary_care": "veterinarian",
    "plumber": "plumber", "electrician": "electrician",
    "roofing_contractor": "roofing", "locksmith": "locksmith",
    "car_repair": "auto_repair", "gym": "fitness_studio",
    "moving_company": "moving_company", "store": "retail",
    "photographer": "photographer", "pet_store": "pet_services",
    "school": "education", "laundry": "cleaning_services",
    "florist": "florist",
}

# Industry value multiplier for priority scoring (§5.2)
INDUSTRY_VALUES = {
    "dental_office": 10, "law_firm": 10, "medical": 9,
    "real_estate": 9, "veterinarian": 8, "beauty_salon": 7,
    "restaurant": 7, "plumber": 7, "electrician": 7,
    "roofing": 8, "auto_repair": 6, "hair_salon": 6,
    "fitness_studio": 6, "bakery": 5, "retail": 5,
    "photographer": 5, "florist": 5, "cleaning_services": 4,
    "moving_company": 5, "pet_services": 4, "education": 4,
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two lat/lng points."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── Daily API Call Counter (safety cap to prevent cost overruns) ──────
_daily_api_calls = 0
_daily_api_date = ""


def _check_daily_limit() -> bool:
    """Return True if under the daily Google Maps API call limit, False if exhausted."""
    global _daily_api_calls, _daily_api_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _daily_api_date != today:
        _daily_api_calls = 0
        _daily_api_date = today
    if _daily_api_calls >= settings.gmaps_daily_call_limit:
        logger.warning(
            "🛑 Google Maps daily call limit reached (%d/%d). Crawling paused until tomorrow.",
            _daily_api_calls, settings.gmaps_daily_call_limit,
        )
        return False
    return True


def _increment_api_call():
    """Track each Google Maps API call."""
    global _daily_api_calls, _daily_api_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _daily_api_date != today:
        _daily_api_calls = 0
        _daily_api_date = today
    _daily_api_calls += 1


def calculate_priority_score(
    score_overall: Optional[int],
    google_rating: Optional[float],
    google_reviews: Optional[int],
    distance_miles: Optional[float],
    business_type: Optional[str],
    has_email: bool,
    email_verified: bool,
    has_owner_name: bool,
) -> int:
    """Calculate composite priority score (§5.2). Higher = better prospect."""
    # Website badness (0-40 pts) — worse site = higher priority
    overall = score_overall if score_overall is not None else 0
    site_badness = 40 - (overall * 0.4)

    # Business health (0-25 pts) — good reviews = has money
    rating = google_rating or 0
    reviews = google_reviews or 0
    review_score = min(25, rating * 4 + min(10, reviews / 10))

    # Proximity (0-15 pts) — closer = easier to close
    dist = distance_miles if distance_miles is not None else 100
    proximity_score = max(0, 15 - (dist / 5))

    # Industry value (0-10 pts)
    industry_mult = INDUSTRY_VALUES.get(business_type or "", 5)

    # Reachability (0-10 pts)
    reach = 0
    if has_email:
        reach += 5
    if email_verified:
        reach += 3
    if has_owner_name:
        reach += 2

    return int(site_badness + review_score + proximity_score + industry_mult + reach)


async def _places_request(session: aiohttp.ClientSession, endpoint: str, params: dict) -> dict:
    """Make a Google Places API request with error handling and daily rate limiting."""
    if not _check_daily_limit():
        return {"status": "DAILY_LIMIT_REACHED", "results": []}
    _increment_api_call()
    params["key"] = settings.google_maps_api_key
    url = f"{PLACES_API_BASE}/{endpoint}/json"
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        data = await resp.json()
        status = data.get("status", "UNKNOWN")
        if status not in ("OK", "ZERO_RESULTS"):
            logger.warning("Places API %s returned status=%s: %s", endpoint, status, data.get("error_message", ""))
        return data


async def nearby_search(
    session: aiohttp.ClientSession,
    lat: float,
    lng: float,
    radius_m: int,
    place_type: str,
) -> list[dict]:
    """Google Places Nearby Search with pagination. Returns up to 60 results."""
    results = []
    params = {
        "location": f"{lat},{lng}",
        "radius": str(min(radius_m, 50000)),  # max 50km
        "type": place_type,
    }

    data = await _places_request(session, "nearbysearch", params)
    results.extend(data.get("results", []))

    # Paginate (up to 2 more pages = 60 results total)
    for _ in range(2):
        token = data.get("next_page_token")
        if not token:
            break
        await asyncio.sleep(2)  # Google requires ~2s delay before next_page_token is valid
        data = await _places_request(session, "nearbysearch", {"pagetoken": token})
        results.extend(data.get("results", []))

    return results


async def place_details(session: aiohttp.ClientSession, place_id: str) -> dict:
    """Fetch detailed info for a single place."""
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,website,url,geometry,rating,user_ratings_total,types,address_components,business_status",
    }
    data = await _places_request(session, "details", params)
    return data.get("result", {})


def _extract_city_state_zip(address_components: list[dict]) -> tuple[str, str, str]:
    """Extract city, state, zip from Google address_components."""
    city, state, zipcode = "", "TX", ""
    for comp in address_components:
        types = comp.get("types", [])
        if "locality" in types:
            city = comp.get("long_name", "")
        elif "administrative_area_level_1" in types:
            state = comp.get("short_name", "TX")
        elif "postal_code" in types:
            zipcode = comp.get("long_name", "")
    return city, state, zipcode


def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Normalize phone for de-duplication: strip non-digits, keep last 10."""
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else None


async def _prospect_exists(db: AsyncSession, google_place_id: str, phone: Optional[str], name: str, zipcode: str) -> bool:
    """Check if prospect already exists using dedup keys (§4.5)."""
    # 1. Exact match on google_place_id
    if google_place_id:
        q = select(func.count()).where(Prospect.google_place_id == google_place_id)
        result = await db.execute(q)
        if result.scalar() > 0:
            return True

    # 2. Phone match
    norm_phone = _normalize_phone(phone)
    if norm_phone:
        q = select(func.count()).where(Prospect.phone == norm_phone)
        result = await db.execute(q)
        if result.scalar() > 0:
            return True

    # 3. Name + zip (exact — fuzzy deferred for simplicity)
    if name and zipcode:
        q = select(func.count()).where(
            Prospect.business_name == name,
            Prospect.zip == zipcode,
        )
        result = await db.execute(q)
        if result.scalar() > 0:
            return True

    return False


async def crawl_category_in_ring(ring: GeoRing, category: str, db: AsyncSession) -> int:
    """Crawl one category within one geo-ring. Returns count of new prospects."""
    if not settings.google_maps_api_key:
        logger.warning("GOOGLE_MAPS_API_KEY not set — skipping crawl")
        return 0

    new_count = 0
    radius_m = int(float(ring.radius_miles) * MILES_TO_METERS)
    center_lat = float(ring.center_lat)
    center_lng = float(ring.center_lng)

    async with aiohttp.ClientSession() as session:
        # Nearby search
        places = await nearby_search(session, center_lat, center_lng, radius_m, category)
        logger.info("Ring %s / %s: found %d raw results", ring.name, category, len(places))

        for place in places:
            place_id = place.get("place_id", "")
            place_name = place.get("name", "Unknown")

            # Quick dedup check before expensive detail call
            location = place.get("geometry", {}).get("location", {})
            lat = location.get("lat", 0)
            lng = location.get("lng", 0)

            # Skip if outside ring radius (Google sometimes returns outside)
            dist = haversine(center_lat, center_lng, lat, lng)
            if dist > float(ring.radius_miles) * 1.1:  # 10% tolerance
                continue

            # Get details
            details = await place_details(session, place_id)
            if not details:
                continue

            phone_raw = details.get("formatted_phone_number")
            address_components = details.get("address_components", [])
            city, state, zipcode = _extract_city_state_zip(address_components)

            # Dedup
            if await _prospect_exists(db, place_id, phone_raw, place_name, zipcode):
                continue

            # Determine business type / industry
            types_list = details.get("types", [])
            biz_type = category  # fallback to search category
            for t in types_list:
                if t in PLACE_TYPE_TO_INDUSTRY:
                    biz_type = PLACE_TYPE_TO_INDUSTRY[t]
                    break

            website = details.get("website")
            distance = haversine(MANOR_LAT, MANOR_LNG, lat, lng)

            # Detect social media URLs — these are NOT real websites
            social_url = None
            if website and is_social_media_url(website):
                social_url = website
                website = None  # Treat as no website
                logger.info("Social media URL detected for %s: %s → treating as no-website", place_name, social_url)

            # Calculate initial priority (no audit yet)
            priority = calculate_priority_score(
                score_overall=0 if not website else None,
                google_rating=details.get("rating"),
                google_reviews=details.get("user_ratings_total"),
                distance_miles=distance,
                business_type=biz_type,
                has_email=False,
                email_verified=False,
                has_owner_name=False,
            )

            # Businesses with social media but no website get a priority boost
            # (they're active online but NEED a website — perfect prospects)
            if social_url and not website:
                priority = min(100, priority + 5)

            social_note = f"Social: {social_url}" if social_url else None

            prospect = Prospect(
                id=uuid4(),
                business_name=place_name,
                business_type=biz_type,
                address=details.get("formatted_address", ""),
                city=city or "Unknown",
                state=state,
                zip=zipcode,
                lat=lat,
                lng=lng,
                phone=_normalize_phone(phone_raw),
                website_url=website,
                has_website=bool(website),
                google_place_id=place_id,
                google_rating=details.get("rating"),
                google_reviews=details.get("user_ratings_total"),
                source="google_maps",
                geo_ring_id=ring.id,
                distance_miles=distance,
                status="discovered",
                priority_score=priority,
                notes=social_note,
            )

            db.add(prospect)
            new_count += 1

            # Rate limiting — be gentle with the API
            await asyncio.sleep(0.2)

        await db.commit()

    return new_count


async def crawl_ring(ring_id: str) -> dict:
    """
    Crawl all categories within a geo-ring.
    Returns summary stats dict.
    """
    from api.services.telegram_outreach import notify_discovery
    from api.services.firebase_summarizer import push_agent_status, push_ring_progress

    stats = {"total_found": 0, "categories_done": 0, "errors": []}

    async with async_session_factory() as db:
        ring = await db.get(GeoRing, ring_id)
        if not ring:
            logger.error("Ring %s not found", ring_id)
            return stats

        ring.status = "active"
        ring.crawl_started_at = datetime.now(timezone.utc)
        await db.commit()

        # Push status to Firebase
        await push_agent_status("running", ring.name, 0)

        categories = ALL_CATEGORIES
        done_cats = ring.categories_done or []

        for cat in categories:
            if cat in done_cats:
                continue

            # Stop if daily API limit reached — don't mark un-crawled categories as done
            if not _check_daily_limit():
                logger.info("Daily API limit reached — stopping crawl. %d/%d categories done.",
                            len(done_cats), len(categories))
                break

            try:
                logger.info("Crawling ring=%s category=%s", ring.name, cat)
                count = await crawl_category_in_ring(ring, cat, db)
                stats["total_found"] += count
                stats["categories_done"] += 1

                # Update ring progress (copy list so SQLAlchemy detects JSON change)
                done_cats.append(cat)
                ring.categories_done = list(done_cats)
                ring.categories_total = list(ALL_CATEGORIES)
                ring.businesses_found = (ring.businesses_found or 0) + count
                await db.commit()

                if count > 0:
                    await notify_discovery(count, ring.name)

                # Rate limit between categories
                await asyncio.sleep(1)

            except Exception as e:
                logger.exception("Error crawling ring=%s cat=%s: %s", ring.name, cat, e)
                stats["errors"].append(f"{cat}: {str(e)}")

        # Mark ring crawl progress
        ring.crawl_completed_at = datetime.now(timezone.utc)
        if len(done_cats) >= len(ALL_CATEGORIES):
            ring.status = "complete"

        # Count website stats
        q_with = select(func.count()).where(
            Prospect.geo_ring_id == ring.id, Prospect.has_website == True
        )
        q_without = select(func.count()).where(
            Prospect.geo_ring_id == ring.id, Prospect.has_website == False
        )
        ring.businesses_with_sites = (await db.execute(q_with)).scalar() or 0
        ring.businesses_without_sites = (await db.execute(q_without)).scalar() or 0

        await db.commit()

        # Push ring progress to Firebase
        all_rings = (await db.execute(select(GeoRing).order_by(GeoRing.ring_number))).scalars().all()
        await push_ring_progress([r.to_dict() for r in all_rings])

    return stats


# ─── Default ring definitions (§4.1) ──────────────────────────────────
DEFAULT_RINGS = [
    {"name": "Manor", "ring_number": 0, "radius_miles": 3},
    {"name": "Pflugerville", "ring_number": 1, "radius_miles": 8},
    {"name": "Round Rock / Hutto", "ring_number": 2, "radius_miles": 15},
    {"name": "North Austin", "ring_number": 3, "radius_miles": 25},
    {"name": "Greater Austin", "ring_number": 4, "radius_miles": 40},
    {"name": "Central TX", "ring_number": 5, "radius_miles": 80},
    {"name": "Extended TX", "ring_number": 6, "radius_miles": 150},
]


async def ensure_default_rings():
    """Create default geo-rings if they don't exist. Called on startup."""
    async with async_session_factory() as db:
        q = select(func.count()).select_from(GeoRing)
        count = (await db.execute(q)).scalar()
        if count > 0:
            return  # already initialized

        for rd in DEFAULT_RINGS:
            ring = GeoRing(
                id=uuid4(),
                name=rd["name"],
                ring_number=rd["ring_number"],
                center_lat=MANOR_LAT,
                center_lng=MANOR_LNG,
                radius_miles=rd["radius_miles"],
                status="pending",
                categories_done=[],
                categories_total=ALL_CATEGORIES,
            )
            db.add(ring)

        await db.commit()
        logger.info("Created %d default geo-rings", len(DEFAULT_RINGS))
