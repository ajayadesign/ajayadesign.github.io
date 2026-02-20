"""
API Route Tests — Test outreach HTTP endpoints via FastAPI test client.

Tests CRUD operations, tracking endpoints, and engine triggers.
Run: cd automation && python -m pytest tests/outreach/test_routes.py -v
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from api.models.prospect import GeoRing, Prospect, OutreachEmail
from tests.outreach.conftest import TEST_EMAIL


# ═══════════════════════════════════════════════════════════
# AGENT CONTROL ROUTES
# ═══════════════════════════════════════════════════════════

class TestAgentRoutes:
    """Test /outreach/agent/* endpoints."""

    async def test_get_status(self, client):
        r = await client.get("/api/v1/outreach/agent/status")
        assert r.status_code == 200
        assert "status" in r.json()

    async def test_start_agent(self, client):
        r = await client.post("/api/v1/outreach/agent/start")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    async def test_pause_agent(self, client):
        await client.post("/api/v1/outreach/agent/start")
        r = await client.post("/api/v1/outreach/agent/pause")
        assert r.status_code == 200
        assert r.json()["status"] == "paused"

    async def test_kill_agent(self, client):
        r = await client.post("/api/v1/outreach/agent/kill")
        assert r.status_code == 200
        assert r.json()["status"] == "idle"


# ═══════════════════════════════════════════════════════════
# PROSPECT CRUD ROUTES
# ═══════════════════════════════════════════════════════════

class TestProspectRoutes:
    """Test /outreach/prospects endpoints."""

    async def test_list_prospects_empty(self, client):
        r = await client.get("/api/v1/outreach/prospects")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["prospects"] == []

    async def test_create_prospect(self, client, sample_ring):
        r = await client.post("/api/v1/outreach/prospects", json={
            "business_name": "Test Biz",
            "city": "Manor",
            "state": "TX",
            "business_type": "plumber",
            "website_url": "https://testbiz.com",
            "owner_email": TEST_EMAIL,
        })
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["business_name"] == "Test Biz"

    async def test_list_prospects_with_data(self, client, sample_prospect):
        r = await client.get("/api/v1/outreach/prospects")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    async def test_get_prospect_by_id(self, client, sample_prospect):
        r = await client.get(f"/api/v1/outreach/prospects/{sample_prospect.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["business_name"] == "Joe's Plumbing"

    async def test_get_prospect_not_found(self, client):
        fake_id = str(uuid.uuid4())
        r = await client.get(f"/api/v1/outreach/prospects/{fake_id}")
        assert r.status_code == 404

    async def test_update_prospect(self, client, sample_prospect):
        r = await client.patch(
            f"/api/v1/outreach/prospects/{sample_prospect.id}",
            json={"notes": "Updated via test"},
        )
        assert r.status_code == 200

    async def test_delete_prospect(self, client, sample_prospect):
        r = await client.delete(f"/api/v1/outreach/prospects/{sample_prospect.id}")
        assert r.status_code == 200

    async def test_filter_by_status(self, client, sample_prospect):
        r = await client.get("/api/v1/outreach/prospects?status=discovered")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1


# ═══════════════════════════════════════════════════════════
# GEO RING ROUTES
# ═══════════════════════════════════════════════════════════

class TestRingRoutes:
    """Test /outreach/rings endpoints."""

    async def test_list_rings(self, client, sample_ring):
        r = await client.get("/api/v1/outreach/rings")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1

    async def test_get_ring_by_id(self, client, sample_ring):
        r = await client.get(f"/api/v1/outreach/rings/{sample_ring.id}")
        assert r.status_code == 200

    async def test_rings_summary(self, client, sample_ring):
        r = await client.get("/api/v1/outreach/rings-summary")
        assert r.status_code == 200

    async def test_create_ring(self, client):
        r = await client.post("/api/v1/outreach/rings", json={
            "name": "Test Ring 99",
            "ring_number": 99,
            "center_lat": 30.3427,
            "center_lng": -97.5567,
            "radius_miles": 5.0,
        })
        assert r.status_code in (200, 201)


# ═══════════════════════════════════════════════════════════
# TRACKING ROUTES
# ═══════════════════════════════════════════════════════════

class TestTrackingRoutes:
    """Test /outreach/track/* endpoints."""

    async def test_open_pixel_unknown(self, client):
        """Open pixel returns PNG even for unknown tracking IDs."""
        r = await client.get("/api/v1/outreach/track/open/unknown-id.png")
        # Should return the pixel image regardless (for email client compatibility)
        assert r.status_code == 200
        assert "image/png" in r.headers.get("content-type", "")

    async def test_click_redirect_unknown(self, client):
        """Click redirect returns redirect or 404 for unknown ID."""
        r = await client.get(
            "/api/v1/outreach/track/click/unknown-id",
            params={"url": "https://example.com"},
            follow_redirects=False,
        )
        # Should redirect even for unknown tracking IDs
        assert r.status_code in (200, 302, 307, 404)

    async def test_unsubscribe_unknown(self, client):
        """Unsubscribe returns response for unknown tracking ID."""
        r = await client.get("/api/v1/outreach/track/unsubscribe/unknown-id")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# STATS & FUNNEL
# ═══════════════════════════════════════════════════════════

class TestStatsRoutes:
    """Test stats and funnel endpoints."""

    async def test_stats(self, client, sample_prospect):
        r = await client.get("/api/v1/outreach/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_prospects" in data

    async def test_funnel(self, client, sample_prospect):
        r = await client.get("/api/v1/outreach/funnel")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (dict, list))

    async def test_map_dots(self, client, sample_prospect):
        r = await client.get("/api/v1/outreach/map-dots")
        assert r.status_code == 200
        data = r.json()
        # Route returns {"dots": [...]} or bare list depending on impl
        dots = data.get("dots", data) if isinstance(data, dict) else data
        assert isinstance(dots, list)


# ═══════════════════════════════════════════════════════════
# ENGINE TRIGGER ROUTES
# ═══════════════════════════════════════════════════════════

class TestEngineRoutes:
    """Test engine trigger endpoints."""

    async def test_audit_prospect_route(self, client, sample_prospect, mock_intel_externals):
        """POST /prospects/{id}/audit triggers audit."""
        r = await client.post(
            f"/api/v1/outreach/prospects/{sample_prospect.id}/audit"
        )
        assert r.status_code in (200, 202)

    async def test_recon_prospect_route(self, client, sample_prospect, mock_recon_externals):
        """POST /prospects/{id}/recon triggers recon."""
        r = await client.post(
            f"/api/v1/outreach/prospects/{sample_prospect.id}/recon"
        )
        assert r.status_code in (200, 202)

    async def test_enqueue_prospect_route(self, client, enriched_prospect, mock_smtp):
        """POST /prospects/{id}/enqueue creates scheduled email."""
        prospect, audit = enriched_prospect
        r = await client.post(
            f"/api/v1/outreach/prospects/{prospect.id}/enqueue"
        )
        assert r.status_code in (200, 202)

    async def test_email_preview_route(self, client, enriched_prospect):
        """GET /prospects/{id}/email-preview returns rendered email."""
        prospect, audit = enriched_prospect
        r = await client.get(
            f"/api/v1/outreach/prospects/{prospect.id}/email-preview",
            params={"step": 1},
        )
        assert r.status_code == 200
        data = r.json()
        assert "subject" in data or "body_html" in data

    async def test_queue_status_route(self, client):
        """GET /queue returns queue info."""
        r = await client.get("/api/v1/outreach/queue")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# EMAIL ROUTES
# ═══════════════════════════════════════════════════════════

class TestEmailRoutes:
    """Test email-related endpoints."""

    async def test_list_emails_empty(self, client):
        r = await client.get("/api/v1/outreach/emails")
        assert r.status_code == 200

    async def test_list_sequences(self, client):
        r = await client.get("/api/v1/outreach/sequences")
        assert r.status_code == 200
