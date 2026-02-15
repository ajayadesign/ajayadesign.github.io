"""
Tests for Firebase RTDB bridge service and build queue.
"""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from api.services.queue import BuildQueue


# ── Firebase Service Tests ──────────────────────────────


class TestFirebaseInit:
    def test_init_no_cred_path(self):
        """Without cred path, init should return False."""
        from api.services.firebase import init_firebase

        # Temporarily reset _initialized
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = False

        result = init_firebase(cred_path="", db_url="https://x.firebaseio.com")
        assert result is False

        fb_mod._initialized = old

    def test_init_already_initialized(self):
        """If already initialized, should return True immediately."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True

        result = fb_mod.init_firebase(cred_path="/fake.json", db_url="https://x.firebaseio.com")
        assert result is True

        fb_mod._initialized = old

    def test_is_initialized(self):
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True
        assert fb_mod.is_initialized() is True
        fb_mod._initialized = False
        assert fb_mod.is_initialized() is False
        fb_mod._initialized = old


class TestFirebaseLeads:
    def test_get_new_leads_not_initialized(self):
        """When not initialized, should return empty list."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = False

        result = fb_mod.get_new_leads()
        assert result == []

        fb_mod._initialized = old

    def test_get_all_leads_not_initialized(self):
        """When not initialized, should return empty list."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = False

        result = fb_mod.get_all_leads()
        assert result == []

        fb_mod._initialized = old

    def test_update_lead_status_not_initialized(self):
        """When not initialized, should return False."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = False

        result = fb_mod.update_lead_status("abc123", "deployed")
        assert result is False

        fb_mod._initialized = old

    def test_get_new_leads_with_data(self):
        """When initialized, should return formatted lead dicts."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True

        mock_ref = MagicMock()
        mock_query = MagicMock()
        mock_query.equal_to.return_value = MagicMock()
        mock_query.equal_to.return_value.get.return_value = {
            "lead_001": {
                "business_name": "Sunrise Bakery",
                "niche": "Bakery",
                "goals": "Sell bread",
                "email": "hello@sunrise.com",
                "status": "new",
            },
            "lead_002": {
                "business_name": "Portland Coffee",
                "niche": "Café",
                "goals": "Online ordering",
                "email": "info@portland.com",
                "status": "new",
            },
        }
        mock_ref.order_by_child.return_value = mock_query

        with patch("api.services.firebase.firebase_db") as mock_db:
            mock_db.reference.return_value = mock_ref
            result = fb_mod.get_new_leads()

        assert len(result) == 2
        assert result[0]["firebase_id"] in ("lead_001", "lead_002")
        assert result[0]["business_name"] in ("Sunrise Bakery", "Portland Coffee")
        assert "status" in result[0]

        fb_mod._initialized = old

    def test_get_all_leads_with_data(self):
        """get_all_leads should return all leads regardless of status."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True

        mock_ref = MagicMock()
        mock_ref.get.return_value = {
            "lead_001": {"business_name": "A", "status": "new"},
            "lead_002": {"business_name": "B", "status": "deployed"},
        }

        with patch("api.services.firebase.firebase_db") as mock_db:
            mock_db.reference.return_value = mock_ref
            result = fb_mod.get_all_leads()

        assert len(result) == 2

        fb_mod._initialized = old

    def test_update_lead_status_success(self):
        """Should call ref.update with correct payload."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True

        mock_ref = MagicMock()

        with patch("api.services.firebase.firebase_db") as mock_db:
            mock_db.reference.return_value = mock_ref
            result = fb_mod.update_lead_status(
                "lead_001", "deployed", {"live_url": "https://example.com"}
            )

        assert result is True
        mock_db.reference.assert_called_with("leads/lead_001")
        mock_ref.update.assert_called_once_with({
            "status": "deployed",
            "live_url": "https://example.com",
        })

        fb_mod._initialized = old

    def test_get_new_leads_handles_exception(self):
        """If Firebase throws, should return [] instead of crashing."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True

        with patch("api.services.firebase.firebase_db") as mock_db:
            mock_db.reference.side_effect = Exception("Firebase unreachable")
            result = fb_mod.get_new_leads()

        assert result == []

        fb_mod._initialized = old

    def test_update_lead_status_handles_exception(self):
        """If Firebase throws, should return False."""
        import api.services.firebase as fb_mod

        old = fb_mod._initialized
        fb_mod._initialized = True

        with patch("api.services.firebase.firebase_db") as mock_db:
            mock_db.reference.side_effect = Exception("Firebase down")
            result = fb_mod.update_lead_status("lead_001", "deployed")

        assert result is False

        fb_mod._initialized = old


# ── Build Queue Tests ───────────────────────────────────


class TestBuildQueue:
    async def test_enqueue_and_process(self):
        """Single build should be processed."""
        processed = []

        async def _processor(build_id: str):
            processed.append(build_id)

        q = BuildQueue(max_concurrent=1)
        q.set_processor(_processor)
        await q.enqueue("build-001")
        await q.drain()

        assert processed == ["build-001"]
        assert q.pending == 0

    async def test_fifo_order(self):
        """Builds should be processed in FIFO order."""
        processed = []

        async def _processor(build_id: str):
            processed.append(build_id)

        q = BuildQueue(max_concurrent=1)
        q.set_processor(_processor)

        # Enqueue multiple before worker starts processing
        q._queue.extend(["build-A", "build-B", "build-C"])
        await q.enqueue("build-D")
        await q.drain()

        assert processed == ["build-A", "build-B", "build-C", "build-D"]

    async def test_pending_count(self):
        """pending property should reflect queue size."""
        q = BuildQueue()
        assert q.pending == 0

        q._queue.extend(["a", "b", "c"])
        assert q.pending == 3

    async def test_error_continues_queue(self):
        """If one build fails, the next should still process."""
        processed = []

        async def _processor(build_id: str):
            if build_id == "bad-build":
                raise RuntimeError("Something broke")
            processed.append(build_id)

        q = BuildQueue(max_concurrent=1)
        q.set_processor(_processor)

        q._queue.extend(["bad-build", "good-build"])
        q._worker_task = asyncio.create_task(q._worker())
        await q.drain()

        assert "good-build" in processed
        # bad-build still tracked as processed (for monitoring)
        assert "bad-build" in q.processed

    async def test_is_running_property(self):
        """is_running should be True while worker is active."""
        q = BuildQueue()
        assert q.is_running is False

    async def test_no_processor_noop(self):
        """Without a processor, enqueue should not crash."""
        q = BuildQueue()
        await q.enqueue("orphan-build")
        await q.drain()
        assert q.pending == 0
