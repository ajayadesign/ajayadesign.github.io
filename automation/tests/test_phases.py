"""
Tests for individual pipeline phases.
"""

import json
import os
from unittest.mock import patch, AsyncMock

import pytest

from tests.conftest import SAMPLE_BLUEPRINT, SAMPLE_DESIGN_SYSTEM, SAMPLE_PAGE_HTML


class TestPhase1Repo:
    async def test_create_new_repo(self, mock_git, mock_settings, tmp_path):
        from api.pipeline.phases.p01_repo import create_repo

        mock_settings.base_dir = str(tmp_path / "repos")
        mock_settings.github_org = "test-org"
        os.makedirs(mock_settings.base_dir, exist_ok=True)

        result = await create_repo(
            "Sunrise Bakery", "Bakery", "Sell bread", "a@b.com"
        )

        assert result["repo_name"] == "sunrise-bakery"
        assert result["repo_full"] == "test-org/sunrise-bakery"
        assert "live_url" in result


class TestPhase2Council:
    async def test_council_approves(self, mock_ai):
        from api.pipeline.phases.p02_council import ai_council

        result = await ai_council(
            "Sunrise Bakery", "Bakery", "Sell bread", "a@b.com",
            max_rounds=1,
        )

        assert "blueprint" in result
        assert "transcript" in result
        assert len(result["blueprint"]["pages"]) > 0
        assert result["transcript"][0]["speaker"] == "strategist"

    async def test_council_sanitizes_colors(self, mock_ai):
        from api.pipeline.phases.p02_council import _sanitize_blueprint

        bp = json.loads(json.dumps(SAMPLE_BLUEPRINT))
        bp["colorDirection"]["primary"] = "#D4763C (warm terracotta)"
        _sanitize_blueprint(bp, "Test", "Bakery")
        # Should extract just the hex
        assert bp["colorDirection"]["primary"] == "#D4763C"

    async def test_council_default_colors(self, mock_ai):
        from api.pipeline.phases.p02_council import _sanitize_blueprint, DEFAULT_COLORS

        bp = {"pages": [{"slug": "index", "title": "Home"}]}
        _sanitize_blueprint(bp, "Test", "Tech")
        assert bp["colorDirection"] == DEFAULT_COLORS


class TestPhase3Design:
    async def test_design_system_generation(self, mock_ai):
        from api.pipeline.phases.p03_design import generate_design_system

        ds = await generate_design_system(SAMPLE_BLUEPRINT)

        assert "tailwindConfig" in ds
        assert "navHtml" in ds
        assert "footerHtml" in ds
        assert "sharedHead" in ds

    def test_wcag_contrast_check(self):
        from api.pipeline.phases.p03_design import _passes_contrast, _contrast_ratio

        # White on white → ratio ~1.0 → fail
        assert not _passes_contrast("#ffffff", "#ffffff", 4.5)

        # Black on white → ratio 21:1 → pass
        assert _passes_contrast("#000000", "#ffffff", 4.5)

        # Medium contrast
        ratio = _contrast_ratio("#D4763C", "#ffffff")
        assert ratio > 1.0  # At least some contrast

    def test_darken_until_contrast(self):
        from api.pipeline.phases.p03_design import _darken_until_contrast

        result = _darken_until_contrast("#ffff00", "#ffffff", 4.5)
        # Should return a darker color
        assert result.startswith("#")


class TestPhase4Generate:
    async def test_generate_pages(self, mock_ai, project_dir):
        from api.pipeline.phases.p04_generate import generate_pages

        bp = json.loads(json.dumps(SAMPLE_BLUEPRINT))
        ds = json.loads(json.dumps(SAMPLE_DESIGN_SYSTEM))

        results = await generate_pages(bp, ds, project_dir)

        assert len(results) == 4
        assert results[0]["slug"] == "index"
        assert results[0]["filename"] == "index.html"
        assert results[0]["status"] == "generated"
        assert os.path.exists(os.path.join(project_dir, "index.html"))

    async def test_fallback_page(self, project_dir):
        """If AI fails, should create a fallback page."""
        from api.pipeline.phases.p04_generate import generate_pages

        async def _failing_ai(*args, **kwargs):
            raise Exception("AI unavailable")

        bp = {"pages": [{"slug": "index", "title": "Home", "purpose": "Main page"}], "siteName": "Test", "tagline": "Tag"}
        ds = json.loads(json.dumps(SAMPLE_DESIGN_SYSTEM))

        with patch("api.pipeline.phases.p04_generate.call_ai", side_effect=_failing_ai):
            results = await generate_pages(bp, ds, project_dir)

        assert results[0]["status"] == "fallback"
        assert os.path.exists(os.path.join(project_dir, "index.html"))


class TestPhase5Assemble:
    async def test_assembly(self, project_dir):
        from api.pipeline.phases.p05_assemble import assemble

        bp = json.loads(json.dumps(SAMPLE_BLUEPRINT))
        ds = json.loads(json.dumps(SAMPLE_DESIGN_SYSTEM))

        # Create dummy HTML files first
        for page in bp["pages"]:
            fname = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
            with open(os.path.join(project_dir, fname), "w") as f:
                f.write(f"<html><body><nav>{{{{ACTIVE:{page['slug']}}}}}</nav></body></html>")

        await assemble(bp, ds, project_dir)

        # Check sitemap created
        assert os.path.exists(os.path.join(project_dir, "sitemap.xml"))
        assert os.path.exists(os.path.join(project_dir, "robots.txt"))
        assert os.path.exists(os.path.join(project_dir, "404.html"))

        # Check nav states stitched
        with open(os.path.join(project_dir, "index.html")) as f:
            content = f.read()
        assert "{{ACTIVE:" not in content


class TestPhase6Test:
    async def test_quality_gate_pass(self, mock_test_runner, project_dir):
        from api.pipeline.phases.p06_test import quality_gate

        bp = json.loads(json.dumps(SAMPLE_BLUEPRINT))
        ds = json.loads(json.dumps(SAMPLE_DESIGN_SYSTEM))

        result = await quality_gate(bp, ds, project_dir, max_fix=1)

        assert result["passed"] is True
        assert result["attempts"] == 1


class TestPhase8Notify:
    async def test_notification(self, mock_telegram):
        from api.pipeline.phases.p08_notify import notify

        await notify(
            "Sunrise Bakery", "Bakery", "goals", "a@b.com",
            "org/sunrise-bakery", "https://example.com", 4,
        )
        # Should complete without error
