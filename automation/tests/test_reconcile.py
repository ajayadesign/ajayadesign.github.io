"""
Tests for offline resilience — startup reconciliation and periodic polling.
"""

import asyncio
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from sqlalchemy import select

from api.models.build import Build
from api.main import reconcile_firebase_leads, periodic_firebase_poll, build_queue


class TestReconcileFirebaseLeads:
    """Test startup reconciliation: Firebase → PostgreSQL sync."""

    async def test_reconcile_creates_missing_builds(self, db_session, db_engine):
        """Leads in Firebase but not in DB should get build rows created."""
        mock_leads = [
            {
                "firebase_id": "lead_001",
                "business_name": "Sunrise Bakery",
                "niche": "Bakery",
                "goals": "Sell bread",
                "email": "hello@sunrise.com",
                "status": "new",
            },
            {
                "firebase_id": "lead_002",
                "business_name": "Portland Coffee",
                "niche": "Café",
                "goals": "Online ordering",
                "email": "info@portland.com",
                "status": "new",
            },
        ]

        with patch("api.main.is_initialized", return_value=True), \
             patch("api.main.get_all_leads", return_value=mock_leads), \
             patch("api.main.update_lead_status") as mock_update, \
             patch("api.main.async_session") as mock_session_factory:
            # Wire up the test DB session
            from sqlalchemy.ext.asyncio import async_sessionmaker

            session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
            mock_session_factory.side_effect = session_factory

            missed = await reconcile_firebase_leads()

        assert len(missed) == 2
        assert mock_update.call_count == 2

        # Verify builds were created in DB
        result = await db_session.execute(select(Build).where(Build.firebase_id.isnot(None)))
        builds = result.scalars().all()
        assert len(builds) == 2

        fids = {b.firebase_id for b in builds}
        assert "lead_001" in fids
        assert "lead_002" in fids
        assert all(b.status == "queued" for b in builds)
        assert all(b.source == "firebase-poll" for b in builds)

    async def test_reconcile_skips_existing_builds(self, db_session, db_engine):
        """Leads already tracked in DB should be skipped."""
        # Pre-create a build with firebase_id
        existing = Build(
            short_id=uuid.uuid4().hex[:8],
            firebase_id="lead_001",
            client_name="Sunrise Bakery",
            niche="Bakery",
            goals="Sell bread",
            email="hello@sunrise.com",
            status="complete",
        )
        db_session.add(existing)
        await db_session.commit()

        mock_leads = [
            {
                "firebase_id": "lead_001",
                "business_name": "Sunrise Bakery",
                "niche": "Bakery",
                "goals": "Sell bread",
                "status": "new",
            },
        ]

        with patch("api.main.is_initialized", return_value=True), \
             patch("api.main.get_all_leads", return_value=mock_leads), \
             patch("api.main.update_lead_status") as mock_update, \
             patch("api.main.async_session") as mock_session_factory:
            from sqlalchemy.ext.asyncio import async_sessionmaker

            session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
            mock_session_factory.side_effect = session_factory

            missed = await reconcile_firebase_leads()

        assert len(missed) == 0
        mock_update.assert_not_called()

    async def test_reconcile_skips_non_new_leads(self, db_engine):
        """Leads with status other than 'new' or 'contacted' should be skipped."""
        mock_leads = [
            {"firebase_id": "lead_deployed", "business_name": "Done Inc", "status": "deployed"},
            {"firebase_id": "lead_failed", "business_name": "Fail Co", "status": "failed"},
        ]

        with patch("api.main.is_initialized", return_value=True), \
             patch("api.main.get_all_leads", return_value=mock_leads), \
             patch("api.main.update_lead_status") as mock_update, \
             patch("api.main.async_session") as mock_session_factory:
            from sqlalchemy.ext.asyncio import async_sessionmaker

            session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
            mock_session_factory.side_effect = session_factory

            missed = await reconcile_firebase_leads()

        assert len(missed) == 0
        mock_update.assert_not_called()

    async def test_reconcile_noop_when_firebase_not_initialized(self):
        """If Firebase isn't initialized, should return empty list."""
        with patch("api.main.is_initialized", return_value=False):
            missed = await reconcile_firebase_leads()

        assert missed == []

    async def test_reconcile_noop_when_no_leads(self):
        """If Firebase has no leads, should return empty list."""
        with patch("api.main.is_initialized", return_value=True), \
             patch("api.main.get_all_leads", return_value=[]):
            missed = await reconcile_firebase_leads()

        assert missed == []


class TestPeriodicFirebasePoll:
    """Test the periodic polling loop."""

    async def test_poll_calls_reconcile_on_new_leads(self):
        """When poll finds new leads, should reconcile and enqueue."""
        call_count = {"n": 0}

        async def _fake_sleep(seconds):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise asyncio.CancelledError()

        mock_leads = [
            {"firebase_id": "lead_new", "business_name": "New Co", "status": "new"}
        ]
        mock_missed = [{"build_id": "build-123", "firebase_id": "lead_new"}]

        with patch("api.main.is_initialized", return_value=True), \
             patch("api.main.get_new_leads", return_value=mock_leads), \
             patch("api.main.reconcile_firebase_leads", new_callable=AsyncMock, return_value=mock_missed), \
             patch("api.main.build_queue") as mock_queue, \
             patch("asyncio.sleep", side_effect=_fake_sleep):
            mock_queue.enqueue = AsyncMock()

            # Function catches CancelledError internally and exits cleanly
            await periodic_firebase_poll(interval=1)

            mock_queue.enqueue.assert_called_with("build-123")

    async def test_poll_skips_when_firebase_not_initialized(self):
        """When Firebase isn't initialized, poll should skip gracefully."""
        call_count = {"n": 0}

        async def _fake_sleep(seconds):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise asyncio.CancelledError()

        with patch("api.main.is_initialized", return_value=False), \
             patch("api.main.get_new_leads") as mock_get, \
             patch("asyncio.sleep", side_effect=_fake_sleep):
            await periodic_firebase_poll(interval=1)

            mock_get.assert_not_called()

    async def test_poll_handles_errors_gracefully(self):
        """If reconciliation throws, poll should continue (not crash)."""
        call_count = {"n": 0}

        async def _fake_sleep(seconds):
            call_count["n"] += 1
            if call_count["n"] >= 3:
                raise asyncio.CancelledError()

        with patch("api.main.is_initialized", return_value=True), \
             patch("api.main.get_new_leads", side_effect=Exception("Firebase down")), \
             patch("asyncio.sleep", side_effect=_fake_sleep):
            await periodic_firebase_poll(interval=1)

        # Should have survived 2 error cycles before cancellation
        assert call_count["n"] >= 2
