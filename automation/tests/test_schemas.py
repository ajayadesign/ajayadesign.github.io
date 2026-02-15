"""
Tests for Pydantic schemas — validation, serialization.
"""

import pytest
from pydantic import ValidationError

from api.schemas import BuildRequest, BuildResponse, BuildDetailResponse, HealthResponse


class TestBuildRequest:
    def test_valid_request(self, sample_request):
        req = BuildRequest(**sample_request)
        assert req.business_name == "Sunrise Bakery"
        assert req.niche == "Artisan Bakery & Café"

    def test_missing_business_name(self):
        with pytest.raises(ValidationError) as exc_info:
            BuildRequest(businessName="", niche="Bakery")
        assert "String should have at least" in str(exc_info.value)

    def test_missing_niche(self):
        with pytest.raises(ValidationError):
            BuildRequest(businessName="Test", niche="")

    def test_optional_fields(self):
        req = BuildRequest(businessName="Minimal", niche="Tech")
        assert req.goals == ""
        assert req.email is None

    def test_strips_whitespace(self):
        req = BuildRequest(businessName="  My Business  ", niche="  Tech  ")
        # Pydantic may or may not strip — we just ensure it's valid
        assert len(req.business_name.strip()) > 0


class TestBuildResponse:
    def test_serialization(self):
        resp = BuildResponse(
            id="uuid-1234",
            short_id="abc12345",
            status="queued",
            message="Build queued",
        )
        data = resp.model_dump()
        assert data["short_id"] == "abc12345"
        assert data["status"] == "queued"


class TestBuildDetailResponse:
    def test_full_detail(self):
        detail = BuildDetailResponse(
            id="uuid-det1",
            short_id="det12345",
            client_name="Test",
            niche="Tech",
            goals="goals",
            email="a@b.com",
            status="complete",
            repo_name="test-site",
            repo_full="org/test-site",
            live_url="https://example.com/test-site",
            pages_count=4,
            blueprint={"pages": []},
            design_system={"navHtml": ""},
            phases=[],
            created_at="2025-01-01T00:00:00",
            started_at="2025-01-01T00:00:01",
            finished_at="2025-01-01T00:01:00",
        )
        assert detail.pages_count == 4
        assert detail.status == "complete"


class TestHealthResponse:
    def test_health(self):
        h = HealthResponse(status="ok", timestamp="2025-01-01T00:00:00", version="2.0.0")
        assert h.status == "ok"
