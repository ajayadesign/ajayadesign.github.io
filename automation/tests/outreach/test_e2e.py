"""
End-to-End Pipeline Test — Full outreach lifecycle.

Simulates the complete journey:
  Ring → Crawl → Audit → Recon → Template → Enqueue → Send → Track → Reply

All external services are mocked. Emails go to TEST_EMAIL (ajayadahal10@gmail.com).
An optional LIVE test actually sends email via SMTP when OUTREACH_TEST_LIVE_SEND=1.

Run all:      cd automation && python -m pytest tests/outreach/test_e2e.py -v
Run live too:  OUTREACH_TEST_LIVE_SEND=1 python -m pytest tests/outreach/test_e2e.py -v
"""

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from api.models.prospect import GeoRing, Prospect, WebsiteAudit, OutreachEmail
from tests.outreach.conftest import (
    TEST_EMAIL,
    SAMPLE_HTML,
    SAMPLE_HEADERS,
    MOCK_PLACES_RESULT,
    MOCK_PLACE_DETAILS,
)


class TestFullOutreachPipeline:
    """
    End-to-end test: exercises the COMPLETE outreach lifecycle.
    discovered → audited → enriched → queued → contacted → opened → clicked → replied
    """

    async def test_complete_lifecycle(
        self, db, verify_db, mock_smtp, mock_intel_externals, mock_recon_externals
    ):
        """Full pipeline: create ring → prospect → audit → recon → send → track → reply."""

        # ── Step 1: Create a geo ring ─────────────────────────────
        ring = GeoRing(
            name="Test Ring 0",
            ring_number=0,
            center_lat=Decimal("30.3427"),
            center_lng=Decimal("-97.5567"),
            radius_miles=Decimal("3.0"),
            status="pending",
        )
        db.add(ring)
        await db.commit()
        await db.refresh(ring)

        # ── Step 2: Create prospect (simulates crawl output) ─────
        prospect = Prospect(
            business_name="Manor Pizza Kitchen",
            business_type="restaurant",
            city="Manor",
            state="TX",
            zip="78653",
            lat=Decimal("30.3480"),
            lng=Decimal("-97.5510"),
            phone="+15125559876",
            website_url="https://manorpizza.com",
            has_website=True,
            google_place_id=f"ChIJ_e2e_test_{uuid.uuid4().hex[:8]}",
            google_rating=Decimal("4.1"),
            google_reviews=67,
            source="google_maps",
            status="discovered",
            geo_ring_id=ring.id,
            owner_email=TEST_EMAIL,
        )
        db.add(prospect)
        await db.commit()
        await db.refresh(prospect)
        prospect_id = str(prospect.id)

        # ── Step 3: Audit the prospect ───────────────────────────
        from api.services.intel_engine import audit_prospect
        audit_result = await audit_prospect(prospect_id)
        assert audit_result is not None, "Audit should succeed"

        async with verify_db() as vdb:
            audit_rows = (await vdb.execute(
                select(WebsiteAudit).where(WebsiteAudit.prospect_id == prospect.id)
            )).scalars().all()
            assert len(audit_rows) >= 1, "WebsiteAudit record should exist"
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.status == "audited"
            assert fresh.score_overall is not None

        # ── Step 4: Recon (discover email) ───────────────────────
        from api.services.recon_engine import recon_prospect
        recon_result = await recon_prospect(prospect_id)
        assert recon_result is not None, "Recon should succeed"

        async with verify_db() as vdb:
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.status == "enriched"
            assert fresh.owner_email == TEST_EMAIL

        # ── Step 5: Compose email (real template rendering) ──────
        from api.services.template_engine import compose_email
        email_data = await compose_email(prospect_id, sequence_step=1)
        assert email_data is not None, "Template should render"
        assert len(email_data["body_html"]) > 100
        assert email_data["subject"]

        # ── Step 6: Enqueue for sending ──────────────────────────
        from api.services.cadence_engine import enqueue_prospect
        email_id = await enqueue_prospect(prospect_id)
        assert email_id is not None, "Enqueue should succeed"

        async with verify_db() as vdb:
            email_rec = await vdb.get(OutreachEmail, email_id)
            assert email_rec.status == "scheduled"
            assert email_rec.tracking_id is not None
            tracking_id = email_rec.tracking_id

        # ── Step 7: Send email (mocked SMTP → captured) ─────────
        from api.services.cadence_engine import send_email_record
        send_ok = await send_email_record(email_id)
        assert send_ok is True, "Send should succeed"
        assert len(mock_smtp.sent_emails) == 1
        sent = mock_smtp.sent_emails[0]
        assert sent["to"] == TEST_EMAIL

        async with verify_db() as vdb:
            email_rec = await vdb.get(OutreachEmail, email_id)
            assert email_rec.status == "sent"
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.status in ("contacted", "follow_up_1")
            assert fresh.emails_sent >= 1

        # ── Step 8: Simulate email open ──────────────────────────
        from api.services.email_tracker import record_open
        open_ok = await record_open(tracking_id)
        assert open_ok is True

        async with verify_db() as vdb:
            email_rec = await vdb.get(OutreachEmail, email_id)
            assert email_rec.open_count >= 1
            assert email_rec.opened_at is not None

        # ── Step 9: Simulate link click ──────────────────────────
        from api.services.email_tracker import record_click
        click_ok = await record_click(tracking_id, "https://ajayadesign.com/portfolio")
        assert click_ok is True

        async with verify_db() as vdb:
            email_rec = await vdb.get(OutreachEmail, email_id)
            assert email_rec.click_count >= 1

        # ── Step 10: Process reply ───────────────────────────────
        from api.services.reply_classifier import process_reply
        reply_result = await process_reply(
            tracking_id,
            "Hi! Yes, I've been thinking about updating our website. "
            "Can we schedule a call this week to discuss?"
        )
        assert reply_result is not None
        assert reply_result["classification"] == "positive"

        async with verify_db() as vdb:
            email_rec = await vdb.get(OutreachEmail, email_id)
            assert email_rec.reply_sentiment == "positive"
            assert email_rec.replied_at is not None
            fresh = await vdb.get(Prospect, prospect.id)
            assert fresh.reply_sentiment == "positive"
            assert fresh.replied_at is not None

        # ── FINAL STATE VERIFICATION ─────────────────────────────
        async with verify_db() as vdb:
            final = await vdb.get(Prospect, prospect.id)
            print(f"\n{'='*60}")
            print(f"  E2E PIPELINE COMPLETE — {final.business_name}")
            print(f"  Status: {final.status}")
            print(f"  Score: {final.score_overall}/100")
            print(f"  Emails Sent: {final.emails_sent}")
            print(f"  Emails Opened: {final.emails_opened}")
            print(f"  Reply: {final.reply_sentiment}")
            print(f"  Recipient: {final.owner_email}")
            print(f"{'='*60}\n")


class TestBatchOperations:
    """Test batch processing endpoints."""

    async def test_batch_enqueue(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import batch_enqueue_prospects
        count = await batch_enqueue_prospects(limit=10)
        assert count >= 1
        async with verify_db() as vdb:
            result = await vdb.execute(
                select(OutreachEmail).where(OutreachEmail.prospect_id == prospect.id)
            )
            emails = result.scalars().all()
            assert len(emails) >= 1

    async def test_process_send_queue(self, db, enriched_prospect, mock_smtp, verify_db):
        prospect, audit = enriched_prospect
        from api.services.cadence_engine import enqueue_prospect, process_send_queue

        email_id = await enqueue_prospect(str(prospect.id))

        # Force the scheduled_for to be in the past so it's "due"
        async with verify_db() as vdb:
            email = await vdb.get(OutreachEmail, email_id)
            email.scheduled_for = datetime(2020, 1, 1, tzinfo=timezone.utc)
            await vdb.commit()

        result = await process_send_queue()
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════
# LIVE EMAIL TEST — Actually sends via SMTP
# ═══════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not os.environ.get("OUTREACH_TEST_LIVE_SEND"),
    reason="Set OUTREACH_TEST_LIVE_SEND=1 to run live email tests"
)
class TestLiveEmailSend:
    """
    LIVE TEST — Actually sends an email to ajayadahal10@gmail.com.
    Run: OUTREACH_TEST_LIVE_SEND=1 python -m pytest tests/outreach/test_e2e.py::TestLiveEmailSend -v
    Requires SMTP_EMAIL and SMTP_APP_PASSWORD configured in env.
    """

    async def test_send_real_email(self, db, enriched_prospect):
        prospect, audit = enriched_prospect
        assert prospect.owner_email == TEST_EMAIL
        from api.services.template_engine import compose_email
        email_data = await compose_email(str(prospect.id), sequence_step=1)
        assert email_data is not None
        from api.services.email_service import send_email
        result = await send_email(
            to=TEST_EMAIL,
            subject=f"[E2E TEST] {email_data['subject']}",
            body_html=email_data["body_html"],
        )
        assert result["success"] is True, f"Live email failed: {result['message']}"
        print(f"\n✅ Live email sent to {TEST_EMAIL}")

    async def test_send_all_sequence_steps(self, db, enriched_prospect):
        prospect, audit = enriched_prospect
        assert prospect.owner_email == TEST_EMAIL
        from api.services.template_engine import compose_email
        from api.services.email_service import send_email
        for step in range(1, 6):
            email_data = await compose_email(str(prospect.id), sequence_step=step)
            assert email_data is not None
            result = await send_email(
                to=TEST_EMAIL,
                subject=f"[E2E STEP {step}/5] {email_data['subject']}",
                body_html=email_data["body_html"],
            )
            assert result["success"] is True
            print(f"  ✅ Step {step}/5 sent")
        print(f"\n✅ All 5 sequence emails sent to {TEST_EMAIL}")
