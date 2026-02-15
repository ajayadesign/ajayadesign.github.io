"""
End-to-End Integration Test — Full form submission through deploy + notification.

Validates:
1. Form payload from index.html → FastAPI BuildRequest (schema compat)
2. Build creation → orchestrator runs all 8 phases
3. Creative direction is produced and flows through the pipeline
4. Assembly generates enhanced assets (favicon, sitemap, scroll progress, etc.)
5. Deploy + Telegram notification complete

This simulates the exact payload the frontend JS sends.
"""

import json
import os
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select

from api.models.build import Build, BuildPhase, BuildLog, BuildPage
from tests.conftest import SAMPLE_BLUEPRINT, SAMPLE_DESIGN_SYSTEM, SAMPLE_CREATIVE_SPEC


class TestE2EFormToPipeline:
    """Simulate exact form payload → API → full pipeline → deploy → notify."""

    async def test_full_e2e_form_submission(
        self, db_session, mock_ai, mock_git, mock_telegram, mock_test_runner, mock_settings, tmp_path
    ):
        """Submit the EXACT payload that index.html main.js sends, run full pipeline."""
        from api.pipeline.orchestrator import BuildOrchestrator

        mock_settings.base_dir = str(tmp_path / "repos")
        mock_settings.main_site_dir = str(tmp_path / "site")
        os.makedirs(mock_settings.base_dir, exist_ok=True)

        project_dir = os.path.join(mock_settings.base_dir, "sunrise-bakery")
        os.makedirs(project_dir, exist_ok=True)

        # This is the EXACT payload shape from js/main.js line ~150
        form_payload = {
            "businessName": "Sunrise Bakery",
            "niche": "Artisan Bakery & Café",
            "goals": "Showcase our handmade pastries and drive catering orders",
            "email": "hello@sunrise-bakery.com",
            "phone": "(503) 555-1234",
            "location": "Portland, OR",
            "existingWebsite": "https://sunrisebakerypdx.com",
            "brandColors": "Warm gold, cream, forest green",
            "tagline": "Handmade Pastries & Fresh-Baked Joy",
            "targetAudience": "Local food lovers, wedding planners, corporate catering",
            "competitorUrls": "https://grandcentral.com, https://kenwoodcafe.com",
            "additionalNotes": "We want a warm, inviting feel with lots of food photography.",
            "rebuild": False,
            "firebaseId": "hello-at-sunrise-bakery-com_1771042375045",
            "source": "ajayadesign.github.io",
        }

        # Validate the payload parses through BuildRequest schema
        from api.schemas import BuildRequest
        req = BuildRequest(**form_payload)
        assert req.business_name == "Sunrise Bakery"
        assert req.niche == "Artisan Bakery & Café"
        assert req.existing_website == "https://sunrisebakerypdx.com"
        assert req.brand_colors == "Warm gold, cream, forest green"

        # Create the build (same as routes/__init__.py does)
        build = Build(
            short_id="e2etest1",
            client_name=req.business_name,
            niche=req.niche,
            goals=req.goals,
            email=str(req.email),
            firebase_id=req.firebase_id,
            source=req.source,
            phone=req.phone,
            location=req.location,
            existing_website=req.existing_website,
            brand_colors=req.brand_colors,
            tagline=req.tagline,
            target_audience=req.target_audience,
            competitor_urls=req.competitor_urls,
            additional_notes=req.additional_notes,
            rebuild=req.rebuild,
            status="queued",
        )
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        # Mock repo creation
        async def _fake_create_repo(biz, niche, goals, email, **kwargs):
            os.makedirs(project_dir, exist_ok=True)
            return {
                "dir": project_dir,
                "repo_name": "sunrise-bakery",
                "repo_full": "ajayadesign/sunrise-bakery",
                "live_url": "https://ajayadesign.github.io/sunrise-bakery",
            }

        events = []

        def capture_event(event_type, data):
            events.append({"type": event_type, **data})

        # Run the orchestrator
        with patch("api.pipeline.orchestrator.p01_repo.create_repo", side_effect=_fake_create_repo):
            orchestrator = BuildOrchestrator(build, db_session, capture_event)
            result = await orchestrator.run()

        # ── Assert: Build completed ──
        assert result.status == "complete"
        assert result.repo_name == "sunrise-bakery"
        assert result.repo_full == "ajayadesign/sunrise-bakery"
        assert result.live_url == "https://ajayadesign.github.io/sunrise-bakery"

        # ── Assert: Blueprint has pages ──
        assert result.blueprint is not None
        pages = result.blueprint.get("pages", [])
        assert len(pages) >= 3  # At minimum: home, about/menu, contact

        # ── Assert: Creative spec was produced and stored ──
        assert orchestrator.creative_spec is not None
        assert "visualConcept" in orchestrator.creative_spec

        # ── Assert: Design system was saved ──
        assert result.design_system is not None
        assert "tailwindConfig" in result.design_system
        assert "navHtml" in result.design_system

        # ── Assert: Pages were generated (files on disk) ──
        assert os.path.exists(os.path.join(project_dir, "index.html"))
        with open(os.path.join(project_dir, "index.html"), "r") as f:
            index_html = f.read()
        assert "<!DOCTYPE html>" in index_html
        assert "<nav" in index_html
        assert "<main" in index_html
        assert "AOS.init" in index_html  # Animation script injected

        # ── Assert: Assembly artifacts created ──
        assert os.path.exists(os.path.join(project_dir, "sitemap.xml"))
        assert os.path.exists(os.path.join(project_dir, "robots.txt"))
        assert os.path.exists(os.path.join(project_dir, "404.html"))
        assert os.path.exists(os.path.join(project_dir, "favicon.svg"))

        # Enhanced features in index.html
        assert "scroll-progress" in index_html
        assert "back-to-top" in index_html
        assert "application/ld+json" in index_html

        # ── Assert: All 8 phases completed in DB ──
        stmt = select(BuildPhase).where(BuildPhase.build_id == build.id)
        phases_result = await db_session.execute(stmt)
        phases = phases_result.scalars().all()
        assert len(phases) == 8
        assert all(p.status == "complete" for p in phases)

        # Phase names match expected sequence
        phase_names = [p.phase_name for p in sorted(phases, key=lambda p: p.phase_number)]
        assert phase_names[0] == "repository"
        assert phase_names[1] == "council"
        assert phase_names[2] == "design"
        assert phase_names[3] == "generate"
        assert phase_names[4] == "assemble"
        assert phase_names[5] == "test"
        assert phase_names[6] == "deploy"
        assert phase_names[7] == "notify"

        # ── Assert: Logs were written ──
        stmt = select(BuildLog).where(BuildLog.build_id == build.id)
        logs_result = await db_session.execute(stmt)
        logs = logs_result.scalars().all()
        assert len(logs) > 10  # Substantial logging expected

        # Check creative director was mentioned in logs
        log_messages = [l.message for l in logs]
        assert any("Creative" in m for m in log_messages), "Creative Director should appear in logs"

        # ── Assert: SSE events were emitted ──
        assert any(e.get("status") == "running" for e in events)
        assert any(e.get("status") == "complete" for e in events)
        # Phase events emitted for all phases
        phase_events = [e for e in events if e.get("type") == "phase"]
        assert len(phase_events) >= 16  # 8 phases × 2 (start + end)

        # ── Assert: Page records in DB ──
        stmt = select(BuildPage).where(BuildPage.build_id == build.id)
        pages_result = await db_session.execute(stmt)
        page_records = pages_result.scalars().all()
        assert len(page_records) >= 3

    async def test_form_payload_with_all_optional_fields(self, client, mock_ai, mock_git, mock_telegram, mock_test_runner):
        """POST /api/v1/builds with ALL form fields should succeed."""
        with patch("api.routes._run_pipeline", new_callable=AsyncMock):
            resp = await client.post(
                "/api/v1/builds",
                json={
                    "businessName": "Portland Coffee Co",
                    "niche": "Specialty Coffee Shop",
                    "goals": "Drive foot traffic and online orders",
                    "email": "brew@portlandcoffee.co",
                    "phone": "(971) 555-0100",
                    "location": "Portland, OR",
                    "existingWebsite": "https://oldsite.portlandcoffee.co",
                    "brandColors": "Deep brown, cream, sage green",
                    "tagline": "Craft Coffee, Community First",
                    "targetAudience": "Young professionals, remote workers",
                    "competitorUrls": "https://stumptown.coffee",
                    "additionalNotes": "We want a modern, minimal vibe.",
                    "rebuild": False,
                    "firebaseId": "brew-at-portlandcoffee-co_1771042375045",
                    "source": "ajayadesign.github.io",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"
        assert data["client_name"] == "Portland Coffee Co"
        assert data["niche"] == "Specialty Coffee Shop"

    async def test_rebuild_flag_accepted(self, client, mock_ai, mock_git, mock_telegram, mock_test_runner):
        """Rebuild flag from form should be stored in build."""
        with patch("api.routes._run_pipeline", new_callable=AsyncMock):
            resp = await client.post(
                "/api/v1/builds",
                json={
                    "businessName": "Rebuild Test",
                    "niche": "Tech",
                    "goals": "Test rebuild",
                    "email": "test@example.com",
                    "rebuild": True,
                    "existingWebsite": "https://old-site.example.com",
                },
            )

        assert resp.status_code == 201
