"""
Tests for ORM models — Build, BuildPhase, BuildLog, BuildPage CRUD.
"""

import pytest
from sqlalchemy import select

from api.models.build import Build, BuildPhase, BuildLog, BuildPage


class TestBuildModel:
    async def test_create_build(self, db_session):
        build = Build(
            short_id="abc12345",
            client_name="Test Bakery",
            niche="Bakery",
            goals="Sell more bread",
            email="test@test.com",
            status="queued",
        )
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        assert build.id is not None
        assert build.short_id == "abc12345"
        assert build.status == "queued"

    async def test_build_to_dict(self, db_session):
        build = Build(
            short_id="dict1234",
            client_name="Dict Corp",
            niche="Tech",
            goals="Grow online presence",
            status="complete",
        )
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        d = build.to_dict()
        assert d["short_id"] == "dict1234"
        assert d["client_name"] == "Dict Corp"
        assert d["status"] == "complete"
        assert "created_at" in d

    async def test_build_relationships(self, db_session):
        build = Build(
            short_id="rel12345",
            client_name="Rel Corp",
            niche="Consulting",
            goals="Build a consulting website",
            status="running",
        )
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        # Add phase
        phase = BuildPhase(
            build_id=build.id,
            phase_number=1,
            phase_name="repository",
            status="complete",
        )
        db_session.add(phase)

        # Add log
        log = BuildLog(
            build_id=build.id,
            sequence=1,
            level="info",
            category="repo",
            message="Creating repo...",
        )
        db_session.add(log)

        # Add page
        page = BuildPage(
            build_id=build.id,
            slug="index",
            title="Home",
            filename="index.html",
            status="generated",
        )
        db_session.add(page)

        await db_session.commit()

        # Query back
        stmt = select(Build).where(Build.short_id == "rel12345")
        result = await db_session.execute(stmt)
        fetched = result.scalar_one()

        assert fetched.client_name == "Rel Corp"


class TestBuildPhaseModel:
    async def test_create_phase(self, db_session):
        build = Build(short_id="ph123456", client_name="Phase Test", niche="n", goals="Test goals", status="running")
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        phase = BuildPhase(
            build_id=build.id,
            phase_number=2,
            phase_name="council",
            status="running",
        )
        db_session.add(phase)
        await db_session.commit()
        await db_session.refresh(phase)

        assert phase.phase_number == 2
        assert phase.phase_name == "council"


class TestBuildPageModel:
    async def test_create_page(self, db_session):
        build = Build(short_id="pg123456", client_name="Page Test", niche="n", goals="Test goals", status="running")
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        page = BuildPage(
            build_id=build.id,
            slug="about",
            title="About Us",
            filename="about.html",
            status="generated",
            word_count=350,
            html_content="<main>About content</main>",
        )
        db_session.add(page)
        await db_session.commit()
        await db_session.refresh(page)

        assert page.slug == "about"
        assert page.word_count == 350


class TestBuildLogModel:
    async def test_create_log(self, db_session):
        build = Build(short_id="lg123456", client_name="Log Test", niche="n", goals="Test goals", status="running")
        db_session.add(build)
        await db_session.commit()
        await db_session.refresh(build)

        log = BuildLog(
            build_id=build.id,
            sequence=1,
            level="info",
            category="test",
            message="Hello from test",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.message == "Hello from test"
        assert log.level == "info"
