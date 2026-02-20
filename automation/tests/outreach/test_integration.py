"""
Integration Tests — DB-backed tests with mocked external services.

Tests the full flow of each engine using the in-memory SQLite DB.
External services (Google Places, SMTP, DNS, Telegram, Firebase) are mocked.

Run: cd automation && python -m pytest tests/outreach/test_integration.py -v
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from api.models.prospect import GeoRing, Prospect, WebsiteAudit, OutreachEmail
from tests.outreach.conftest import TEST_EMAIL, SAMPLE_HTML, SAMPLE_HEADERS


# ═══════════════════════════════════════════════════════════
# GEO RING MANAGEMENT
# ═══════════════════════════════════════════════════════════

class TestGeoRingManagement:
    """Test geo-ring creation and management."""

    async def test_ensure_default_rings_creates_seven(self, db):
        from api.services.crawl_engine import ensure_default_rings
        await ensure_default_rings()
        result = await db.execute(select(GeoRing))
        rings = result.scalars().all()
        assert len(rings) == 7
        assert rings[0].ring_number == 0
        assert rings[-1].ring_number == 6

    async def test_ensure_default_rings_idempotent(self, db):
        from api.services.crawl_engine import ensure_default_rings
        await ensure_default_rings()
        await ensure_default_rings()
        result = await db.execute(select(GeoRing))
        rings = result.scalars().all()
        assert len(rings) == 7

    async def test_get_ring_stats(self, db, sample_ring, sample_prospect):
        from api.services.geo_ring_manager import get_ring_stats
        stats = await get_ring_stats(db, sample_ring.id)
        assert isinstance(stats, dict)

    async def test_get_all_rings_summary(self, db, sample_ring):
        from api.services.geo_ring_manager import get_all_rings_summary
        summary = await get_all_rings_summary()
        assert len(summary) >= 1


# ═══════════════════════════════════════════════════════════
# INTEL ENGINE (WEBSITE AUDITING)
# ═══════════════════════════════════════════════════════════

class TestIntelEngine:

    async def test_audit_prospect(self, db, sample_prospect, mock_intel_externals, verify_db):
        from api.services.intel_engine import audit_prospect
        result = await audit_prospect(str(sample_prospect.id))
        assert result is not None
        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, sample_prospect.id)
            assert fresh.status == "audited"
            assert fresh.score_overall is not None
            assert fresh.score_speed is not None

    async def test_audit_creates_audit_record(self, db, sample_prospect, mock_intel_externals, verify_db):
        from api.services.intel_engine import audit_prospect
        await audit_prospect(str(sample_prospect.id))
        async with verify_db() as vdb:
            result = await vdb.execute(
                select(WebsiteAudit).where(WebsiteAudit.prospect_id == sample_prospect.id)
            )
            audit = result.scalar_one_or_none()
            assert audit is not None
            assert audit.url == "https://joesplumbing.com"

    async def test_audit_nonexistent_prospect(self, db):
        from api.services.intel_engine import audit_prospect
        result = await audit_prospect("00000000-0000-0000-0000-000000000000")
        assert result is None


# ═══════════════════════════════════════════════════════════
# RECON ENGINE (EMAIL DISCOVERY)
# ═══════════════════════════════════════════════════════════

class TestReconEngine:

    async def test_recon_prospect(self, db, sample_prospect, mock_recon_externals, verify_db):
        from api.services.recon_engine import recon_prospect
        # Set status to "audited" so recon can advance to "enriched"
        sample_prospect.status = "audited"
        await db.commit()
        result = await recon_prospect(str(sample_prospect.id))
        assert result is not None
        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, sample_prospect.id)
            assert fresh.status == "enriched"
            assert fresh.owner_email is not None

    async def test_recon_nonexistent_prospect(self, db):
        from api.services.recon_engine import recon_prospect
        result = await recon_prospect("00000000-0000-0000-0000-000000000000")
        assert result is None


# ═══════════════════════════════════════════════════════════
# TEMPLATE ENGINE (EMAIL COMPOSITION)
# ═══════════════════════════════════════════════════════════

class TestTemplateEngine:

    async def test_compose_step_1_initial_audit(self, db, enriched_prospect):
        prospect, audit = enriched_prospect
        from api.services.template_engine import compose_email
        result = await compose_email(str(prospect.id), sequence_step=1)
        assert result is not None
        assert "subject" in result
        assert "body_html" in result
        assert "body_text" in result
        assert len(result["body_html"]) > 100

    async def test_compose_all_five_steps(self, db, enriched_prospect):
        prospect, audit = enriched_prospect
        from api.services.template_engine import compose_email
        for step in range(1, 6):
            result = await compose_email(str(prospect.id), sequence_step=step)
            assert result is not None, f"Step {step} returned None"
            assert result["body_html"], f"Step {step} has empty body"
            assert result["subject"], f"Step {step} has empty subject"
            assert result["template_id"], f"Step {step} has no template_id"

    async def test_compose_includes_business_data(self, db, enriched_prospect):
        prospect, audit = enriched_prospect
        from api.services.template_engine import compose_email
        result = await compose_email(str(prospect.id), 1)
        body = result["body_html"].lower()
        assert (
            prospect.business_name.lower() in body
            or "plumbing" in body
            or "manor" in body
        )

    async def test_preview_email(self, db, enriched_prospect):
        prospect, audit = enriched_prospect
        from api.services.template_engine import preview_email
        result = await preview_email(str(prospect.id), 1)
        assert result is not None
        assert "subject" in result


# ═══════════════════════════════════════════════════════════
# CADENCE ENGINE (SCHEDULING & SENDING)
# ═══════════════════════════════════════════════════════════

class TestCadenceEngine:

    async def test_enqueue_creates_scheduled_email(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect
        email_id = await enqueue_prospect(str(prospect.id))
        assert email_id is not None
        async with verify_db() as vdb:
            result = await vdb.execute(
                select(OutreachEmail).where(OutreachEmail.prospect_id == prospect.id)
            )
            email = result.scalar_one_or_none()
            assert email is not None
            assert email.status == "scheduled"
            assert email.sequence_step == 1
            assert email.tracking_id is not None

    async def test_enqueue_updates_prospect_status(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect
        await enqueue_prospect(str(prospect.id))
        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.status == "queued"

    async def test_send_email_record(self, db, enriched_prospect, mock_smtp):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, send_email_record
        email_id = await enqueue_prospect(str(prospect.id))
        success = await send_email_record(email_id)
        assert success is True
        assert len(mock_smtp.sent_emails) == 1
        assert mock_smtp.sent_emails[0]["to"] == TEST_EMAIL

    async def test_send_updates_status_to_sent(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, send_email_record
        email_id = await enqueue_prospect(str(prospect.id))
        await send_email_record(email_id)
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            assert email.status == "sent"
            assert email.sent_at is not None
            fresh_prospect = await vdb.get(Prospect, prospect.id)
            assert fresh_prospect.status in ("contacted", "follow_up_1")
            assert fresh_prospect.emails_sent >= 1

    async def test_get_queue_status(self, db, enriched_prospect, mock_smtp):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, get_queue_status
        await enqueue_prospect(str(prospect.id))
        status = await get_queue_status()
        assert isinstance(status, dict)

    async def test_handle_bounce(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, handle_bounce
        email_id = await enqueue_prospect(str(prospect.id))
        await handle_bounce(email_id)
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            assert email.status == "bounced"

    async def test_handle_unsubscribe(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, handle_unsubscribe
        await enqueue_prospect(str(prospect.id))
        await handle_unsubscribe(str(prospect.id))
        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.status == "do_not_contact"


# ═══════════════════════════════════════════════════════════
# EMAIL TRACKER (OPEN / CLICK / UNSUBSCRIBE)
# ═══════════════════════════════════════════════════════════

class TestEmailTracker:

    async def _enqueue_and_send(self, prospect, verify_db):
        from api.services.cadence_engine import enqueue_prospect, send_email_record
        email_id = await enqueue_prospect(str(prospect.id))
        await send_email_record(email_id)
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            return email_id, email.tracking_id

    async def test_record_open(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        email_id, tracking_id = await self._enqueue_and_send(prospect, verify_db)
        from api.services.email_tracker import record_open
        result = await record_open(tracking_id)
        assert result is True
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            assert email.open_count >= 1
            assert email.opened_at is not None

    async def test_record_click(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        email_id, tracking_id = await self._enqueue_and_send(prospect, verify_db)
        from api.services.email_tracker import record_click
        result = await record_click(tracking_id, "https://ajayadesign.com")
        assert result is True
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            assert email.click_count >= 1
            assert email.clicked_at is not None

    async def test_record_open_unknown_tracking_id(self, db):
        from api.services.email_tracker import record_open
        result = await record_open("nonexistent-tracking-id")
        assert result is False


# ═══════════════════════════════════════════════════════════
# REPLY CLASSIFIER (INTEGRATION)
# ═══════════════════════════════════════════════════════════

class TestReplyClassifierIntegration:

    async def test_process_positive_reply(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, send_email_record
        email_id = await enqueue_prospect(str(prospect.id))
        await send_email_record(email_id)
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            tracking_id = email.tracking_id
        from api.services.reply_classifier import process_reply
        result = await process_reply(
            tracking_id,
            "Yes, I'm very interested! Let's set up a call."
        )
        assert result is not None
        assert result["classification"] == "positive"
        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.reply_sentiment == "positive"

    async def test_process_unsubscribe_reply(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, send_email_record
        email_id = await enqueue_prospect(str(prospect.id))
        await send_email_record(email_id)
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            tracking_id = email.tracking_id
        from api.services.reply_classifier import process_reply
        result = await process_reply(
            tracking_id,
            "Remove me from your list. Do not contact me again."
        )
        assert result["classification"] == "unsubscribe"


# ═══════════════════════════════════════════════════════════
# ADVANCED FEATURES (DB-BACKED)
# ═══════════════════════════════════════════════════════════

class TestAdvancedFeatures:

    async def test_find_competitors(self, db, audited_prospect):
        prospect, audit = audited_prospect
        competitor = Prospect(
            business_name="Better Plumbing Co",
            business_type="plumber",
            city="Manor",
            state="TX",
            score_overall=85,
            has_website=True,
            website_url="https://betterplumbing.com",
            geo_ring_id=prospect.geo_ring_id,
            google_place_id="ChIJ_test_competitor",
            status="audited",
        )
        db.add(competitor)
        await db.commit()
        from api.services.advanced_features import find_competitors
        results = await find_competitors(str(prospect.id))
        assert isinstance(results, list)

    async def test_enrich_prospect_advanced(self, db, audited_prospect):
        prospect, audit = audited_prospect
        from api.services.advanced_features import enrich_prospect_advanced
        result = await enrich_prospect_advanced(str(prospect.id))
        assert isinstance(result, dict)
