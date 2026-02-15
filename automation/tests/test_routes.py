"""
Tests for API routes — health, builds CRUD, SSE, parse-client.
"""

import json
from unittest.mock import patch, AsyncMock

import pytest


class TestHealthEndpoint:
    async def test_health(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestRootEndpoint:
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "service" in data
        assert "AjayaDesign" in data["service"]


class TestBuildsAPI:
    async def test_create_build(self, client, mock_ai, mock_git, mock_telegram, mock_test_runner):
        """POST /api/v1/builds should create a build and return 201."""
        # Patch the background pipeline so it doesn't actually run
        with patch("api.routes._run_pipeline", new_callable=AsyncMock):
            resp = await client.post(
                "/api/v1/builds",
                json={
                    "businessName": "Test Bakery",
                    "niche": "Bakery",
                    "goals": "Sell bread",
                    "email": "test@bakery.com",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"
        assert "short_id" in data
        assert len(data["short_id"]) == 8

    async def test_create_build_validation(self, client):
        """Missing required fields should return 422."""
        resp = await client.post(
            "/api/v1/builds",
            json={"businessName": "x", "niche": ""},
        )
        assert resp.status_code == 422

    async def test_list_builds_empty(self, client):
        resp = await client.get("/api/v1/builds")
        assert resp.status_code == 200
        data = resp.json()
        assert data["builds"] == []
        assert data["total"] == 0

    async def test_list_builds_with_data(self, client, mock_ai, mock_git, mock_telegram, mock_test_runner):
        # Create a build first
        with patch("api.routes._run_pipeline", new_callable=AsyncMock):
            await client.post(
                "/api/v1/builds",
                json={"businessName": "List Test", "niche": "Tech", "goals": "Test goals"},
            )

        resp = await client.get("/api/v1/builds")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_get_build_detail(self, client, mock_ai, mock_git, mock_telegram, mock_test_runner):
        # Create a build
        with patch("api.routes._run_pipeline", new_callable=AsyncMock):
            create_resp = await client.post(
                "/api/v1/builds",
                json={"businessName": "Detail Test", "niche": "Tech", "goals": "Test goals"},
            )
        short_id = create_resp.json()["short_id"]

        resp = await client.get(f"/api/v1/builds/{short_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["short_id"] == short_id
        assert data["client_name"] == "Detail Test"

    async def test_get_build_not_found(self, client):
        resp = await client.get("/api/v1/builds/nonexist")
        assert resp.status_code == 404

    async def test_get_build_logs_empty(self, client, mock_ai, mock_git, mock_telegram, mock_test_runner):
        with patch("api.routes._run_pipeline", new_callable=AsyncMock):
            create_resp = await client.post(
                "/api/v1/builds",
                json={"businessName": "Logs Test", "niche": "Tech", "goals": "Test goals"},
            )
        short_id = create_resp.json()["short_id"]

        resp = await client.get(f"/api/v1/builds/{short_id}/logs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestParseClient:
    """POST /api/v1/parse-client — AI text extraction."""

    async def test_parse_client_success(self, client):
        """AI returns valid parsed fields from raw text."""
        ai_response = json.dumps({
            "business_name": "Sunrise Bakery",
            "niche": "Artisan Bakery",
            "goals": "Showcase breads and drive catering orders",
            "email": "hello@sunrise.com",
            "phone": "(503) 555-1234",
            "location": "Portland, OR",
            "existing_website": "https://sunrisebakerypdx.com",
            "brand_colors": "Navy blue, Gold",
            "tagline": None,
            "target_audience": None,
            "competitor_urls": None,
            "additional_notes": None,
            "confidence": "high",
        })

        with patch("api.services.ai.call_ai", new_callable=AsyncMock, return_value=ai_response):
            resp = await client.post(
                "/api/v1/parse-client",
                json={"rawText": "Hey Aj, I run a bakery called Sunrise Bakery in Portland OR. We need a website to showcase our artisan breads and drive catering orders. Our current site is sunrisebakerypdx.com but it's outdated. We use navy blue and gold. Email me at hello@sunrise.com or call 503-555-1234."},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] == "high"
        parsed = data["parsed"]
        # Pydantic may serialize with alias (camelCase) or field name (snake_case)
        biz = parsed.get("business_name") or parsed.get("businessName")
        assert biz == "Sunrise Bakery"
        assert parsed["email"] == "hello@sunrise.com"
        assert parsed["location"] == "Portland, OR"

    async def test_parse_client_minimal_text(self, client):
        """AI handles minimal text with low confidence."""
        ai_response = json.dumps({
            "business_name": "Some Shop",
            "niche": None,
            "goals": None,
            "email": None,
            "phone": None,
            "location": None,
            "existing_website": None,
            "brand_colors": None,
            "tagline": None,
            "target_audience": None,
            "competitor_urls": None,
            "additional_notes": None,
            "confidence": "low",
        })

        with patch("api.services.ai.call_ai", new_callable=AsyncMock, return_value=ai_response):
            resp = await client.post(
                "/api/v1/parse-client",
                json={"rawText": "Someone wants a website for Some Shop"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] == "low"
        parsed = data["parsed"]
        biz = parsed.get("business_name") or parsed.get("businessName")
        assert biz == "Some Shop"

    async def test_parse_client_validation_short_text(self, client):
        """Text too short should return 422."""
        resp = await client.post(
            "/api/v1/parse-client",
            json={"rawText": "short"},
        )
        assert resp.status_code == 422

    async def test_parse_client_ai_failure(self, client):
        """AI failure should return 502."""
        with patch("api.services.ai.call_ai", new_callable=AsyncMock, side_effect=RuntimeError("AI down")):
            resp = await client.post(
                "/api/v1/parse-client",
                json={"rawText": "Hey Aj, I need a website for my restaurant downtown."},
            )
        assert resp.status_code == 502

    async def test_parse_client_invalid_json_from_ai(self, client):
        """AI returns non-JSON should return 502."""
        with patch("api.services.ai.call_ai", new_callable=AsyncMock, return_value="Sorry, I can't parse that."):
            resp = await client.post(
                "/api/v1/parse-client",
                json={"rawText": "Hey Aj, I need a website for my restaurant in Austin."},
            )
        assert resp.status_code == 502
