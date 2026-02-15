"""
End-to-end orchestrator test — full pipeline with all mocks.
"""

import json
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.models.build import Build, BuildPhase, BuildLog, BuildPage
from tests.conftest import SAMPLE_BLUEPRINT, SAMPLE_DESIGN_SYSTEM


class TestOrchestrator:
    """Full pipeline: create build → run all 8 phases → verify DB state."""

    async def test_full_pipeline_success(
        self, db_session, mock_ai, mock_git, mock_telegram, mock_test_runner, mock_settings, tmp_path
    ):
        from api.pipeline.orchestrator import BuildOrchestrator

        mock_settings.base_dir = str(tmp_path / "repos")
        mock_settings.main_site_dir = str(tmp_path / "site")
        os.makedirs(mock_settings.base_dir, exist_ok=True)

        # Ensure the project directory exists for page generation
        project_dir = os.path.join(mock_settings.base_dir, "sunrise-bakery")
        os.makedirs(project_dir, exist_ok=True)

        # Override p01_repo to set the correct project dir
        async def _fake_create_repo(biz, niche, goals, email, **kwargs):
            os.makedirs(project_dir, exist_ok=True)
            return {
                "dir": project_dir,
                "repo_name": "sunrise-bakery",
                "repo_full": "test-org/sunrise-bakery",
                "live_url": "https://ajayadesign.github.io/sunrise-bakery",
            }

        # Create build
        build = Build(
            short_id="e2e12345",
            client_name="Sunrise Bakery",
            niche="Artisan Bakery & Café",
            goals="Showcase our handmade pastries and drive catering orders",
            email="hello@sunrise-bakery.com",
            status="queued",
        )
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        events = []

        def capture_event(event_type, data):
            events.append({"type": event_type, **data})

        with patch("api.pipeline.orchestrator.p01_repo.create_repo", side_effect=_fake_create_repo):
            orchestrator = BuildOrchestrator(build, db_session, capture_event)
            result = await orchestrator.run()

        # ── Assertions ──

        # Build completed
        assert result.status == "complete"
        assert result.repo_name == "sunrise-bakery"
        assert result.repo_full == "test-org/sunrise-bakery"
        assert result.live_url is not None

        # Blueprint was saved
        assert result.blueprint is not None
        assert len(result.blueprint.get("pages", [])) > 0

        # Design system was saved
        assert result.design_system is not None

        # Pages were generated (files on disk)
        assert os.path.exists(os.path.join(project_dir, "index.html"))

        # Assembly files created
        assert os.path.exists(os.path.join(project_dir, "sitemap.xml"))
        assert os.path.exists(os.path.join(project_dir, "robots.txt"))
        assert os.path.exists(os.path.join(project_dir, "404.html"))

        # Events were emitted
        assert any(e.get("status") == "running" for e in events)
        assert any(e.get("status") == "complete" for e in events)

        # Phases were logged in DB
        stmt = select(BuildPhase).where(BuildPhase.build_id == build.id)
        phases_result = await db_session.execute(stmt)
        phases = phases_result.scalars().all()
        assert len(phases) == 8
        assert all(p.status == "complete" for p in phases)

        # Logs were written
        stmt = select(BuildLog).where(BuildLog.build_id == build.id)
        logs_result = await db_session.execute(stmt)
        logs = logs_result.scalars().all()
        assert len(logs) > 0

    async def test_pipeline_failure_handling(
        self, db_session, mock_git, mock_telegram, mock_test_runner, mock_settings, tmp_path
    ):
        """If AI fails in council phase, build should be marked failed."""
        from api.pipeline.orchestrator import BuildOrchestrator

        mock_settings.base_dir = str(tmp_path / "repos")
        os.makedirs(mock_settings.base_dir, exist_ok=True)

        project_dir = os.path.join(mock_settings.base_dir, "fail-test")
        os.makedirs(project_dir, exist_ok=True)

        async def _fake_create_repo(biz, niche, goals, email, **kwargs):
            return {
                "dir": project_dir,
                "repo_name": "fail-test",
                "repo_full": "test-org/fail-test",
                "live_url": "https://example.com/fail-test",
            }

        async def _failing_ai(*args, **kwargs):
            raise RuntimeError("AI service down")

        build = Build(
            short_id="fail1234",
            client_name="Fail Test",
            niche="Tech",
            goals="Test goals for failure scenario",
            status="queued",
        )
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        with patch("api.pipeline.orchestrator.p01_repo.create_repo", side_effect=_fake_create_repo), \
             patch("api.services.ai.call_ai", side_effect=_failing_ai), \
             patch("api.pipeline.phases.p02_council.call_ai", side_effect=_failing_ai):
            orchestrator = BuildOrchestrator(build, db_session)
            with pytest.raises(RuntimeError, match="AI service down"):
                await orchestrator.run()

        assert build.status == "failed"
        assert build.finished_at is not None


class TestRepoCollision:
    """Test that p01_repo handles name collisions correctly."""

    async def test_repo_exists_same_client_reuses(self, mock_settings, tmp_path):
        """If the repo exists AND is for the same client, clone it (rebuild)."""
        from api.pipeline.phases.p01_repo import create_repo

        mock_settings.base_dir = str(tmp_path / "repos")
        mock_settings.github_org = "ajayadesign"

        project_dir = os.path.join(mock_settings.base_dir, "sunrise-bakery")

        async def _fake_run(cmd, cwd=None, **kw):
            if "clone" in cmd:
                os.makedirs(project_dir, exist_ok=True)
            return ""

        async def _fake_try(cmd, cwd=None, **kw):
            if "gh repo view" in cmd and "--json description" in cmd:
                return (True, "Client site for Sunrise Bakery — built by AjayaDesign")
            if "gh repo view" in cmd:
                return (True, "exists")  # repo exists on GitHub
            return (True, "")

        with patch("api.pipeline.phases.p01_repo.run_cmd", side_effect=_fake_run), \
             patch("api.pipeline.phases.p01_repo.try_cmd", side_effect=_fake_try), \
             patch("api.services.git.try_cmd", side_effect=_fake_try):
            result = await create_repo("Sunrise Bakery", "Bakery", "Goals", "a@b.com")

        assert result["repo_name"] == "sunrise-bakery"  # reused, no suffix
        assert "sunrise-bakery" in result["live_url"]

    async def test_repo_exists_different_client_gets_suffix(self, mock_settings, tmp_path):
        """If the repo exists for a DIFFERENT client, use sunrise-bakery-2."""
        from api.pipeline.phases.p01_repo import create_repo

        mock_settings.base_dir = str(tmp_path / "repos")
        mock_settings.github_org = "ajayadesign"

        async def _fake_run(cmd, cwd=None, **kw):
            if "clone" in cmd:
                # extract dir from the clone command
                parts = cmd.split('"')
                for p in parts:
                    if "/repos/" in p:
                        os.makedirs(p, exist_ok=True)
            return ""

        async def _fake_try(cmd, cwd=None, **kw):
            if "gh repo view" in cmd and "--json description" in cmd:
                return (True, "Client site for Portland Sunrise Bakery — built by AjayaDesign")
            if "gh repo view" in cmd:
                # sunrise-bakery exists, sunrise-bakery-2 does NOT
                if "sunrise-bakery-2" in cmd:
                    return (False, "")
                return (True, "exists")
            if "gh repo create" in cmd:
                return (True, "created")
            return (True, "")

        with patch("api.pipeline.phases.p01_repo.run_cmd", side_effect=_fake_run), \
             patch("api.pipeline.phases.p01_repo.try_cmd", side_effect=_fake_try), \
             patch("api.services.git.try_cmd", side_effect=_fake_try):
            result = await create_repo("Sunrise Bakery", "Bakery", "Goals", "a@b.com")

        assert result["repo_name"] == "sunrise-bakery-2"
        assert "sunrise-bakery-2" in result["live_url"]
        assert "sunrise-bakery-2" in result["repo_full"]

    async def test_multiple_collisions_finds_free_slot(self, mock_settings, tmp_path):
        """sunrise-bakery and sunrise-bakery-2 both taken → gets -3."""
        from api.pipeline.phases.p01_repo import create_repo

        mock_settings.base_dir = str(tmp_path / "repos")
        mock_settings.github_org = "ajayadesign"

        async def _fake_run(cmd, cwd=None, **kw):
            if "clone" in cmd:
                parts = cmd.split('"')
                for p in parts:
                    if "/repos/" in p:
                        os.makedirs(p, exist_ok=True)
            return ""

        async def _fake_try(cmd, cwd=None, **kw):
            if "gh repo view" in cmd and "--json description" in cmd:
                return (True, "Client site for Someone Else — built by AjayaDesign")
            if "gh repo view" in cmd:
                if "sunrise-bakery-3" in cmd:
                    return (False, "")  # -3 is free
                return (True, "exists")  # base and -2 are taken
            if "gh repo create" in cmd:
                return (True, "created")
            return (True, "")

        with patch("api.pipeline.phases.p01_repo.run_cmd", side_effect=_fake_run), \
             patch("api.pipeline.phases.p01_repo.try_cmd", side_effect=_fake_try), \
             patch("api.services.git.try_cmd", side_effect=_fake_try):
            result = await create_repo("Sunrise Bakery", "Bakery", "Goals", "a@b.com")

        assert result["repo_name"] == "sunrise-bakery-3"
