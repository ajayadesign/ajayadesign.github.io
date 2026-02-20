"""
Tests for the analytics_archiver service.

Verifies:
- monthly archive reads correct Firebase paths and writes to Postgres
- already-archived date/category pairs are skipped (idempotent)
- Firebase is pruned only after a successful Postgres write
- retry logic triggers on transient Firebase errors
- graceful no-op when Firebase is unavailable
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from api.models.site_analytics import SiteAnalyticsArchive
from api.services.analytics_archiver import (
    archive_site_analytics,
    _previous_month_prefix,
    _date_keys_for_month,
    _count_events,
    CATEGORIES,
)

# ── fixtures ─────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        # Only create the table we need (full Base.metadata includes JSONB
        # columns from other models that SQLite can't compile).
        await conn.run_sync(SiteAnalyticsArchive.__table__.create)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SiteAnalyticsArchive.__table__.drop)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session_factory(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    return factory


# ── helpers ──────────────────────────────────────────────

FAKE_PAGEVIEWS = {
    "home": {
        "-PushId1": {"url": "/", "timestamp": "2026-01-15T10:00:00Z", "visitorId": "v1"},
        "-PushId2": {"url": "/", "timestamp": "2026-01-15T11:00:00Z", "visitorId": "v2"},
    }
}

FAKE_CLICKS = {
    "home": {
        "-C1": {"x": 50, "y": 30, "tag": "a", "ts": "2026-01-15T10:01:00Z"},
    }
}


def _build_mock_firebase(data_by_path: dict):
    """Return (mock_firebase_admin, mock_db, deleted_list).

    ``mock_firebase_admin.db`` is wired to our FakeRef so that
    ``import firebase_admin.db as firebase_db`` works after reload.
    """
    deleted = []

    class FakeRef:
        def __init__(self, path):
            self.path = path

        def get(self):
            return data_by_path.get(self.path)

        def delete(self):
            deleted.append(self.path)

    mock_db = MagicMock()
    mock_db.reference = lambda p: FakeRef(p)

    mock_admin = MagicMock()
    mock_admin.db = mock_db       # firebase_admin.db → our mock_db

    return mock_admin, mock_db, deleted


# ── unit tests for helpers ───────────────────────────────

class TestHelpers:
    def test_previous_month_prefix(self):
        prefix = _previous_month_prefix()
        today = datetime.now(timezone.utc)
        first = today.replace(day=1)
        last_month = (first - timedelta(days=1))
        assert prefix == last_month.strftime("%Y-%m")

    def test_date_keys_for_month_jan(self):
        keys = _date_keys_for_month("2026-01")
        assert len(keys) == 31
        assert keys[0] == "2026-01-01"
        assert keys[-1] == "2026-01-31"

    def test_date_keys_for_month_feb_non_leap(self):
        keys = _date_keys_for_month("2025-02")
        assert len(keys) == 28

    def test_count_events_dict(self):
        assert _count_events(FAKE_PAGEVIEWS) == 2  # 2 push children under "home"

    def test_count_events_numeric(self):
        # scrollDepth: slug -> threshold -> count
        data = {"25": 10, "50": 5, "75": 2, "100": 1}
        assert _count_events(data) == 4

    def test_count_events_empty(self):
        assert _count_events({}) == 0
        assert _count_events(None) == 0


# ── integration tests ────────────────────────────────────

class TestArchiveSiteAnalytics:
    @pytest.mark.asyncio
    async def test_archive_and_prune(self, db_session_factory):
        """Successful archive: data lands in Postgres, Firebase paths pruned."""
        fb_data = {
            "site_analytics/pageViews/2026-01-15": FAKE_PAGEVIEWS,
            "site_analytics/clicks/2026-01-15": FAKE_CLICKS,
        }
        mock_admin, mock_db, deleted = _build_mock_firebase(fb_data)

        with (
            patch("api.services.analytics_archiver.asyncio.sleep", new_callable=AsyncMock),
            patch.dict("sys.modules", {"firebase_admin": mock_admin, "firebase_admin.db": mock_db}),
            patch("api.services.firebase.is_initialized", return_value=True),
            patch("api.database.async_session_factory", db_session_factory),
        ):
            import importlib
            import api.services.analytics_archiver as mod
            importlib.reload(mod)

            result = await mod.archive_site_analytics(month_prefix="2026-01")

        assert result["archived"] == 2
        assert result["pruned"] == 2

        async with db_session_factory() as session:
            rows = (await session.execute(select(SiteAnalyticsArchive))).scalars().all()
            cats = {r.category for r in rows}
            assert "pageViews" in cats
            assert "clicks" in cats
            for r in rows:
                assert r.date_key == "2026-01-15"
                assert r.event_count > 0
                assert r.size_bytes > 0

        assert "site_analytics/pageViews/2026-01-15" in deleted
        assert "site_analytics/clicks/2026-01-15" in deleted

    @pytest.mark.asyncio
    async def test_idempotent_no_double_archive(self, db_session_factory):
        """Running twice for the same month does not duplicate rows."""
        fb_data = {
            "site_analytics/pageViews/2026-01-15": FAKE_PAGEVIEWS,
        }
        mock_admin, mock_db, deleted = _build_mock_firebase(fb_data)

        with (
            patch("api.services.analytics_archiver.asyncio.sleep", new_callable=AsyncMock),
            patch.dict("sys.modules", {"firebase_admin": mock_admin, "firebase_admin.db": mock_db}),
            patch("api.services.firebase.is_initialized", return_value=True),
            patch("api.database.async_session_factory", db_session_factory),
        ):
            import importlib
            import api.services.analytics_archiver as mod
            importlib.reload(mod)

            r1 = await mod.archive_site_analytics(month_prefix="2026-01")
            r2 = await mod.archive_site_analytics(month_prefix="2026-01")

        assert r1["archived"] == 1
        assert r2["archived"] == 0

        async with db_session_factory() as session:
            count = len(
                (await session.execute(select(SiteAnalyticsArchive))).scalars().all()
            )
            assert count == 1

    @pytest.mark.asyncio
    async def test_no_prune_on_postgres_failure(self, db_session_factory):
        """If Postgres write fails, the Firebase data must NOT be pruned."""
        fb_data = {
            "site_analytics/pageViews/2026-01-01": FAKE_PAGEVIEWS,
        }
        mock_admin, mock_db, deleted = _build_mock_firebase(fb_data)

        broken_factory = MagicMock()
        broken_session = MagicMock()
        broken_session.execute = AsyncMock(side_effect=Exception("DB down"))
        broken_session.commit = AsyncMock()
        broken_session.__aenter__ = AsyncMock(return_value=broken_session)
        broken_session.__aexit__ = AsyncMock(return_value=False)
        broken_factory.return_value = broken_session

        with (
            patch("api.services.analytics_archiver.asyncio.sleep", new_callable=AsyncMock),
            patch.dict("sys.modules", {"firebase_admin": mock_admin, "firebase_admin.db": mock_db}),
            patch("api.services.firebase.is_initialized", return_value=True),
            patch("api.database.async_session_factory", broken_factory),
        ):
            import importlib
            import api.services.analytics_archiver as mod
            importlib.reload(mod)

            result = await mod.archive_site_analytics(month_prefix="2026-01")

        assert result["archived"] == 0
        assert len(deleted) == 0

    @pytest.mark.asyncio
    async def test_retry_on_firebase_read_failure(self, db_session_factory):
        """Transient Firebase failures trigger retries with back-off."""
        call_count = 0

        class FlakyRef:
            def __init__(self, path):
                self.path = path

            def get(self):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ConnectionError("RTDB unreachable")
                return FAKE_PAGEVIEWS if "pageViews" in self.path and "2026-01-15" in self.path else None

            def delete(self):
                pass

        mock_db = MagicMock()
        mock_db.reference = lambda p: FlakyRef(p)
        mock_admin = MagicMock()
        mock_admin.db = mock_db

        with (
            patch("api.services.analytics_archiver.asyncio.sleep", new_callable=AsyncMock),
            patch("api.services.analytics_archiver.INITIAL_BACKOFF_S", 0),
            patch.dict("sys.modules", {"firebase_admin": mock_admin, "firebase_admin.db": mock_db}),
            patch("api.services.firebase.is_initialized", return_value=True),
            patch("api.database.async_session_factory", db_session_factory),
        ):
            import importlib
            import api.services.analytics_archiver as mod
            importlib.reload(mod)

            result = await mod.archive_site_analytics(month_prefix="2026-01")

        assert result["archived"] >= 1

    @pytest.mark.asyncio
    async def test_noop_when_firebase_unavailable(self):
        """Gracefully returns zeros when firebase_admin is missing."""
        with patch.dict("sys.modules", {"firebase_admin": None, "firebase_admin.db": None}):
            import importlib
            import api.services.analytics_archiver as mod
            importlib.reload(mod)

            result = await mod.archive_site_analytics(month_prefix="2026-01")

        assert result == {"archived": 0, "pruned": 0}
