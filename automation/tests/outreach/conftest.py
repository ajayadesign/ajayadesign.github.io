"""
Outreach Agent Test Suite — Shared Fixtures.

Provides:
- In-memory SQLite DB with all outreach tables
- Realistic test data (prospects, audits, rings)
- Mocked external services (Google Places, SMTP, DNS, Telegram, Firebase)
- All emails redirect to TEST_EMAIL for safety

Usage:
    cd automation
    python -m pytest tests/outreach/ -v
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from api.database import Base

# ── Register PostgreSQL → SQLite type compilers ──────────
# (must happen before any table creation)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, UUID as PG_UUID


@compiles(PG_JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


# ── Override UUID bind/result processing for SQLite ──────
# The PostgreSQL UUID type's bind_processor calls value.hex which fails
# when the value is already a string (as happens with SQLite VARCHAR storage).
_original_uuid_bind_processor = PG_UUID.bind_processor

def _patched_uuid_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)
        return process
    return _original_uuid_bind_processor(self, dialect)

PG_UUID.bind_processor = _patched_uuid_bind_processor

_original_uuid_result_processor = PG_UUID.result_processor

def _patched_uuid_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(value) if self.as_uuid else value
        return process
    return _original_uuid_result_processor(self, dialect, coltype)

PG_UUID.result_processor = _patched_uuid_result_processor


from api.models.prospect import (
    GeoRing,
    Prospect,
    WebsiteAudit,
    OutreachEmail,
    OutreachSequence,
)

# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

TEST_EMAIL = "ajayadahal10@gmail.com"
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ═══════════════════════════════════════════════════════════
# DATABASE FIXTURES
# ═══════════════════════════════════════════════════════════

@pytest_asyncio.fixture()
async def outreach_engine():
    """In-memory SQLite engine with all outreach tables."""
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def session_factory(outreach_engine):
    """Session factory for patching into service modules."""
    return async_sessionmaker(outreach_engine, expire_on_commit=False)


@pytest_asyncio.fixture()
async def db(session_factory):
    """Async DB session for test setup / verification."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def verify_db(session_factory):
    """Return a callable that gives a fresh async session context manager.

    Service functions use their own sessions, so the test 'db' session's
    identity-map is stale.  Open a brand-new session to read committed data.

    Usage:
        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, some_id)
    """
    def _open():
        return session_factory()
    return _open


# ═══════════════════════════════════════════════════════════
# PATCH ALL SERVICE MODULES TO USE TEST DB
# ═══════════════════════════════════════════════════════════

SERVICE_MODULES = [
    "api.database",
    "api.services.crawl_engine",
    "api.services.intel_engine",
    "api.services.recon_engine",
    "api.services.template_engine",
    "api.services.cadence_engine",
    "api.services.reply_classifier",
    "api.services.advanced_features",
    "api.services.geo_ring_manager",
]


@pytest.fixture(autouse=True)
def patch_db_factory(session_factory):
    """Redirect async_session_factory in ALL outreach modules to test DB."""
    patchers = []
    for mod in SERVICE_MODULES:
        try:
            p = patch(f"{mod}.async_session_factory", session_factory)
            p.start()
            patchers.append(p)
        except (AttributeError, ModuleNotFoundError):
            pass
    yield session_factory
    for p in patchers:
        p.stop()


# ═══════════════════════════════════════════════════════════
# MOCK EXTERNAL SERVICES (autouse — always active)
# ═══════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def mock_telegram():
    """Mock ALL Telegram notifications to no-op."""
    with patch("api.services.telegram_outreach.notify",
               new_callable=AsyncMock, return_value=True), \
         patch("api.services.telegram_outreach.send_message",
               new_callable=AsyncMock, return_value=True), \
         patch("api.services.telegram_outreach.notify_discovery",
               new_callable=AsyncMock, return_value=True), \
         patch("api.services.telegram_outreach.notify_audit",
               new_callable=AsyncMock, return_value=True), \
         patch("api.services.telegram_outreach.notify_recon",
               new_callable=AsyncMock, return_value=True), \
         patch("api.services.telegram_outreach.notify_ring_complete",
               new_callable=AsyncMock, return_value=True), \
         patch("api.services.telegram_outreach.notify_reply",
               new_callable=AsyncMock, return_value=True) as m:
        yield m


@pytest.fixture(autouse=True)
def mock_firebase():
    """Mock Firebase summarizer pushes."""
    with patch("api.services.firebase_summarizer._safe_set",
               new_callable=AsyncMock, return_value=None) as m_safe, \
         patch("api.services.firebase_summarizer.push_agent_status",
               new_callable=AsyncMock, return_value=None), \
         patch("api.services.firebase_summarizer.push_ring_progress",
               new_callable=AsyncMock, return_value=None):
        yield m_safe


# ═══════════════════════════════════════════════════════════
# SAMPLE DATA
# ═══════════════════════════════════════════════════════════

SAMPLE_RING_DATA = {
    "name": "Ring 0: Manor",
    "ring_number": 0,
    "center_lat": Decimal("30.3427"),
    "center_lng": Decimal("-97.5567"),
    "radius_miles": Decimal("3.0"),
    "status": "pending",
}

SAMPLE_PROSPECT_DATA = {
    "business_name": "Joe's Plumbing",
    "business_type": "plumber",
    "city": "Manor",
    "state": "TX",
    "zip": "78653",
    "lat": Decimal("30.3450"),
    "lng": Decimal("-97.5550"),
    "phone": "+15125551234",
    "website_url": "https://joesplumbing.com",
    "has_website": True,
    "google_place_id": "ChIJ_test_joes_plumbing",
    "google_rating": Decimal("3.8"),
    "google_reviews": 45,
    "source": "google_maps",
    "status": "discovered",
    "owner_email": TEST_EMAIL,
    "owner_name": "Joe Smith",
}

SAMPLE_AUDIT_DATA = {
    "url": "https://joesplumbing.com",
    "perf_score": 45,
    "a11y_score": 62,
    "bp_score": 55,
    "seo_score": 38,
    "fcp_ms": 3200,
    "lcp_ms": 5500,
    "tbt_ms": 800,
    "page_size_kb": 2400,
    "request_count": 85,
    "has_title": True,
    "has_meta_desc": False,
    "has_h1": True,
    "has_og_tags": False,
    "has_schema": False,
    "has_sitemap": False,
    "mobile_friendly": False,
    "cms_platform": "wordpress",
    "design_era": "dated-2015",
    "design_sins": ["copyright 2019", "no responsive design"],
    "ssl_valid": True,
    "ssl_grade": "B",
    "tech_stack": ["WordPress", "jQuery", "Google Analytics"],
    "security_headers": {"x-frame-options": False, "csp": False},
}

SAMPLE_HTML = """<!DOCTYPE html>
<html><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joe's Plumbing - Manor TX</title>
    <meta name="description" content="Professional plumbing services in Manor, TX">
    <link rel="stylesheet" href="/wp-content/themes/theme/style.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body>
    <h1>Joe's Plumbing Services</h1>
    <p>Serving Manor since 2015</p>
    <p>&copy; 2019 Joe's Plumbing. All rights reserved.</p>
    <footer>Call us: (512) 555-1234 | Email: joe@joesplumbing.com</footer>
</body>
</html>"""

SAMPLE_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Server": "Apache/2.4.41",
    "X-Powered-By": "PHP/7.4",
}

MOCK_PLACES_RESULT = {
    "results": [
        {
            "place_id": "ChIJ_test_plumber_1",
            "name": "Al's Plumbing",
            "geometry": {"location": {"lat": 30.345, "lng": -97.555}},
            "vicinity": "123 Main St, Manor",
            "rating": 4.2,
            "user_ratings_total": 89,
            "types": ["plumber", "point_of_interest"],
        },
        {
            "place_id": "ChIJ_test_plumber_2",
            "name": "Quick Fix Plumbing",
            "geometry": {"location": {"lat": 30.350, "lng": -97.560}},
            "vicinity": "456 Oak Ave, Manor",
            "rating": 3.5,
            "user_ratings_total": 23,
            "types": ["plumber", "point_of_interest"],
        },
    ],
    "status": "OK",
}

MOCK_PLACE_DETAILS = {
    "result": {
        "place_id": "ChIJ_test_plumber_1",
        "name": "Al's Plumbing",
        "formatted_address": "123 Main St, Manor, TX 78653",
        "formatted_phone_number": "(512) 555-5678",
        "website": "https://alsplumbing.com",
        "geometry": {"location": {"lat": 30.345, "lng": -97.555}},
        "rating": 4.2,
        "user_ratings_total": 89,
        "address_components": [
            {"types": ["locality"], "long_name": "Manor"},
            {"types": ["administrative_area_level_1"], "short_name": "TX"},
            {"types": ["postal_code"], "long_name": "78653"},
        ],
    },
    "status": "OK",
}


# ═══════════════════════════════════════════════════════════
# ENTITY FIXTURES (create records in test DB)
# ═══════════════════════════════════════════════════════════

@pytest_asyncio.fixture()
async def sample_ring(db):
    """Create a GeoRing in the test DB."""
    ring = GeoRing(**SAMPLE_RING_DATA)
    db.add(ring)
    await db.commit()
    await db.refresh(ring)
    return ring


@pytest_asyncio.fixture()
async def sample_prospect(db, sample_ring):
    """Create a Prospect with email = TEST_EMAIL."""
    data = {**SAMPLE_PROSPECT_DATA, "geo_ring_id": sample_ring.id}
    prospect = Prospect(**data)
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    return prospect


@pytest_asyncio.fixture()
async def audited_prospect(db, sample_prospect):
    """Prospect with audit data populated."""
    audit = WebsiteAudit(
        prospect_id=sample_prospect.id,
        **SAMPLE_AUDIT_DATA,
    )
    db.add(audit)

    sample_prospect.score_overall = 42
    sample_prospect.score_speed = 45
    sample_prospect.score_mobile = 30
    sample_prospect.score_seo = 38
    sample_prospect.score_a11y = 62
    sample_prospect.score_design = 35
    sample_prospect.score_security = 70
    sample_prospect.website_platform = "wordpress"
    sample_prospect.status = "audited"
    sample_prospect.audit_date = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(sample_prospect)
    await db.refresh(audit)
    return sample_prospect, audit


@pytest_asyncio.fixture()
async def enriched_prospect(db, audited_prospect):
    """Prospect with recon data (email verified)."""
    prospect, audit = audited_prospect
    prospect.owner_email = TEST_EMAIL
    prospect.owner_name = "Joe Smith"
    prospect.email_verified = True
    prospect.email_source = "website_scrape"
    prospect.status = "enriched"
    await db.commit()
    await db.refresh(prospect)
    return prospect, audit


# ═══════════════════════════════════════════════════════════
# MOCK EMAIL SERVICE (NOT autouse — import explicitly)
# ═══════════════════════════════════════════════════════════

@pytest.fixture()
def mock_smtp():
    """Mock SMTP email sending — captures all sent emails."""
    sent_emails = []

    async def _capture_email(to, subject, body_html, reply_to=None):
        sent_emails.append({
            "to": to,
            "subject": subject,
            "body_html": body_html,
            "reply_to": reply_to,
        })
        return {"success": True, "message": f"Test email captured for {to}"}

    with patch("api.services.email_service.send_email",
               side_effect=_capture_email) as m:
        m.sent_emails = sent_emails
        yield m


# ═══════════════════════════════════════════════════════════
# MOCK GOOGLE PLACES API
# ═══════════════════════════════════════════════════════════

@pytest.fixture()
def mock_places_api():
    """Mock Google Places API (aiohttp requests)."""
    async def _mock_request(session, endpoint, params):
        if "nearbysearch" in endpoint:
            return MOCK_PLACES_RESULT
        elif "details" in endpoint:
            return MOCK_PLACE_DETAILS
        return {"status": "OK"}

    with patch("api.services.crawl_engine._places_request",
               side_effect=_mock_request) as m:
        yield m


# ═══════════════════════════════════════════════════════════
# MOCK INTEL ENGINE EXTERNALS
# ═══════════════════════════════════════════════════════════

@pytest.fixture()
def mock_intel_externals():
    """Mock Lighthouse + Playwright + HTTP fetch for intel_engine."""
    mock_lighthouse_result = {
        "categories": {
            "performance": {"score": 0.45},
            "accessibility": {"score": 0.62},
            "best-practices": {"score": 0.55},
            "seo": {"score": 0.38},
        },
        "audits": {
            "first-contentful-paint": {"numericValue": 3200},
            "largest-contentful-paint": {"numericValue": 5500},
            "total-blocking-time": {"numericValue": 800},
            "cumulative-layout-shift": {"numericValue": 0.15},
            "server-response-time": {"numericValue": 450},
        },
    }

    with patch("api.services.intel_engine.fetch_page",
               new_callable=AsyncMock) as mock_fetch, \
         patch("api.services.intel_engine.run_lighthouse",
               new_callable=AsyncMock) as mock_lh, \
         patch("api.services.intel_engine.take_screenshots",
               new_callable=AsyncMock) as mock_ss:

        mock_fetch.return_value = (SAMPLE_HTML, SAMPLE_HEADERS, 200, 1500.0)
        mock_lh.return_value = mock_lighthouse_result
        mock_ss.return_value = {"desktop": "/tmp/desktop.png", "mobile": "/tmp/mobile.png"}

        yield {
            "fetch": mock_fetch,
            "lighthouse": mock_lh,
            "screenshots": mock_ss,
        }


# ═══════════════════════════════════════════════════════════
# MOCK RECON ENGINE EXTERNALS
# ═══════════════════════════════════════════════════════════

@pytest.fixture()
def mock_recon_externals():
    """Mock DNS/SMTP/Web scraping for recon_engine."""
    with patch("api.services.recon_engine.scrape_website_for_contacts",
               new_callable=AsyncMock) as mock_scrape, \
         patch("api.services.recon_engine.verify_email",
               new_callable=AsyncMock) as mock_verify, \
         patch("api.services.recon_engine.lookup_whois",
               new_callable=AsyncMock) as mock_whois:

        mock_scrape.return_value = {
            "emails": [TEST_EMAIL],
            "phones": ["(512) 555-1234"],
            "names": ["Joe Smith"],
            "linkedin": [],
        }
        mock_verify.return_value = {
            "valid": True,
            "smtp_valid": True,
            "score": 85,
            "method": "smtp_verify",
            "mx_records": ["mx.google.com"],
        }
        mock_whois.return_value = {
            "registrant_name": "Joe Smith",
            "registrant_email": None,
            "creation_date": "2015-01-01",
        }

        yield {
            "scrape": mock_scrape,
            "verify": mock_verify,
            "whois": mock_whois,
        }


# ═══════════════════════════════════════════════════════════
# FastAPI TEST CLIENT
# ═══════════════════════════════════════════════════════════

@pytest_asyncio.fixture()
async def client(outreach_engine):
    """FastAPI test client with test DB injected."""
    from api.main import app
    from api.database import get_db

    factory = async_sessionmaker(outreach_engine, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
