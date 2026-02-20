"""
Outreach Agent — SQLAlchemy models for prospects, audits, emails, sequences, and geo-rings.

These are the core data models for the autonomous outreach pipeline.
PostgreSQL is the source of truth — Firebase only mirrors lightweight aggregates.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from api.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class GeoRing(Base):
    """Concentric geo-ring around Manor, TX for systematic territory coverage."""

    __tablename__ = "geo_rings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # "Ring 0: Manor"
    ring_number = Column(Integer, nullable=False, default=0)
    center_lat = Column(Numeric(10, 7), default=30.3427)  # Manor, TX
    center_lng = Column(Numeric(10, 7), default=-97.5567)
    radius_miles = Column(Numeric(6, 2), nullable=False)

    # Crawl progress
    status = Column(String, default="pending")  # pending, crawling, complete, paused
    businesses_found = Column(Integer, default=0)
    businesses_with_websites = Column(Integer, default=0)
    businesses_without_websites = Column(Integer, default=0)
    crawl_started = Column(DateTime(timezone=True))
    crawl_completed = Column(DateTime(timezone=True))
    last_crawl = Column(DateTime(timezone=True))

    # Categories crawled
    categories_done = Column(JSONB, default=list)
    categories_total = Column(JSONB, default=list)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    prospects = relationship("Prospect", back_populates="geo_ring", lazy="selectin")

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "ring_number": self.ring_number,
            "center_lat": float(self.center_lat) if self.center_lat else None,
            "center_lng": float(self.center_lng) if self.center_lng else None,
            "radius_miles": float(self.radius_miles) if self.radius_miles else None,
            "status": self.status,
            "businesses_found": self.businesses_found,
            "businesses_with_websites": self.businesses_with_websites,
            "businesses_without_websites": self.businesses_without_websites,
            "crawl_started": self.crawl_started.isoformat() if self.crawl_started else None,
            "crawl_completed": self.crawl_completed.isoformat() if self.crawl_completed else None,
            "categories_done": self.categories_done or [],
            "categories_total": self.categories_total or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Prospect(Base):
    """A discovered business — the core entity of the outreach pipeline."""

    __tablename__ = "prospects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Discovery ──
    business_name = Column(String, nullable=False)
    business_type = Column(String)  # "restaurant", "plumber", "dentist"
    industry_tag = Column(String)  # NAICS or custom tag
    address = Column(Text)
    city = Column(String, nullable=False)
    state = Column(String, default="TX")
    zip = Column(String)
    lat = Column(Numeric(10, 7))
    lng = Column(Numeric(10, 7))
    phone = Column(String)
    google_place_id = Column(String, unique=True, index=True)
    google_maps_url = Column(Text)
    google_rating = Column(Numeric(2, 1))
    google_reviews = Column(Integer)

    # ── Website ──
    website_url = Column(Text)
    has_website = Column(Boolean, default=False)
    website_platform = Column(String)  # "wordpress", "wix", "squarespace", "custom", "none"
    ssl_valid = Column(Boolean)
    ssl_expiry = Column(DateTime(timezone=True))
    domain_age_days = Column(Integer)

    # ── Decision Maker ──
    owner_name = Column(String)
    owner_email = Column(String)
    owner_phone = Column(String)
    owner_linkedin = Column(Text)
    owner_title = Column(String)  # "Owner", "Manager", etc.
    email_source = Column(String)  # "whois", "website_scrape", "hunter.io", "manual"
    email_verified = Column(Boolean, default=False)

    # ── Audit Scores (0-100) ──
    score_overall = Column(Integer)
    score_speed = Column(Integer)
    score_mobile = Column(Integer)
    score_seo = Column(Integer)
    score_a11y = Column(Integer)
    score_design = Column(Integer)
    score_security = Column(Integer)
    audit_json = Column(JSONB)  # extracted highlights only
    audit_date = Column(DateTime(timezone=True))
    screenshot_desktop = Column(Text)  # file path
    screenshot_mobile = Column(Text)  # file path

    # ── Outreach State Machine ──
    status = Column(String, default="discovered", index=True)
    # discovered → audited → enriched → queued → contacted →
    # follow_up_1 → follow_up_2 → follow_up_3 →
    # replied → meeting_booked → promoted → dead → do_not_contact

    # ── Outreach Tracking ──
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    last_email_at = Column(DateTime(timezone=True))
    last_opened_at = Column(DateTime(timezone=True))
    last_clicked_at = Column(DateTime(timezone=True))
    replied_at = Column(DateTime(timezone=True))
    reply_sentiment = Column(String)  # "positive", "neutral", "negative", "unsubscribe"

    # ── Geo-ring ──
    geo_ring_id = Column(UUID(as_uuid=True), ForeignKey("geo_rings.id"))
    distance_miles = Column(Numeric(6, 2))

    # ── Competitor Intel ──
    competitors = Column(JSONB)  # [{name, url, score}]
    competitor_avg = Column(Integer)

    # ── Meta ──
    source = Column(String)  # "google_maps", "yelp", "manual", "referral"
    notes = Column(Text)
    tags = Column(JSONB, default=list)
    priority_score = Column(Integer, default=0, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    geo_ring = relationship("GeoRing", back_populates="prospects")
    audits = relationship("WebsiteAudit", back_populates="prospect", lazy="selectin", cascade="all, delete-orphan")
    emails = relationship("OutreachEmail", back_populates="prospect", lazy="selectin", cascade="all, delete-orphan")

    def to_dict(self, brief=False):
        """Convert to dict. brief=True for lightweight list views."""
        d = {
            "id": str(self.id),
            "business_name": self.business_name,
            "business_type": self.business_type,
            "city": self.city,
            "state": self.state,
            "status": self.status,
            "score_overall": self.score_overall,
            "priority_score": self.priority_score,
            "has_website": self.has_website,
            "google_rating": float(self.google_rating) if self.google_rating else None,
            "google_reviews": self.google_reviews,
            "emails_sent": self.emails_sent,
            "emails_opened": self.emails_opened,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if brief:
            return d

        d.update({
            "industry_tag": self.industry_tag,
            "address": self.address,
            "zip": self.zip,
            "lat": float(self.lat) if self.lat else None,
            "lng": float(self.lng) if self.lng else None,
            "phone": self.phone,
            "google_place_id": self.google_place_id,
            "google_maps_url": self.google_maps_url,
            "google_rating": float(self.google_rating) if self.google_rating else None,
            "google_reviews": self.google_reviews,
            "website_url": self.website_url,
            "website_platform": self.website_platform,
            "ssl_valid": self.ssl_valid,
            "owner_name": self.owner_name,
            "owner_email": self.owner_email,
            "owner_phone": self.owner_phone,
            "owner_title": self.owner_title,
            "email_source": self.email_source,
            "email_verified": self.email_verified,
            "score_speed": self.score_speed,
            "score_mobile": self.score_mobile,
            "score_seo": self.score_seo,
            "score_a11y": self.score_a11y,
            "score_design": self.score_design,
            "score_security": self.score_security,
            "audit_json": self.audit_json,
            "audit_date": self.audit_date.isoformat() if self.audit_date else None,
            "screenshot_desktop": self.screenshot_desktop,
            "screenshot_mobile": self.screenshot_mobile,
            "emails_clicked": self.emails_clicked,
            "last_email_at": self.last_email_at.isoformat() if self.last_email_at else None,
            "last_opened_at": self.last_opened_at.isoformat() if self.last_opened_at else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "reply_sentiment": self.reply_sentiment,
            "geo_ring_id": str(self.geo_ring_id) if self.geo_ring_id else None,
            "distance_miles": float(self.distance_miles) if self.distance_miles else None,
            "competitors": self.competitors,
            "competitor_avg": self.competitor_avg,
            "source": self.source,
            "notes": self.notes,
            "tags": self.tags or [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        })
        return d

    def to_map_dot(self):
        """Minimal dict for map plotting (~50 bytes per dot)."""
        return {
            "id": str(self.id),
            "lat": float(self.lat) if self.lat else None,
            "lng": float(self.lng) if self.lng else None,
            "status": self.status,
            "score": self.score_overall,
        }


class WebsiteAudit(Base):
    """Full website audit results — Lighthouse + heuristic analysis."""

    __tablename__ = "website_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)

    # Lighthouse scores
    perf_score = Column(Integer)
    a11y_score = Column(Integer)
    bp_score = Column(Integer)  # Best Practices
    seo_score = Column(Integer)

    # Speed metrics
    fcp_ms = Column(Integer)
    lcp_ms = Column(Integer)
    cls = Column(Numeric(4, 3))
    tbt_ms = Column(Integer)
    ttfb_ms = Column(Integer)
    page_size_kb = Column(Integer)
    request_count = Column(Integer)

    # SEO details
    has_title = Column(Boolean)
    has_meta_desc = Column(Boolean)
    has_h1 = Column(Boolean)
    has_og_tags = Column(Boolean)
    has_schema = Column(Boolean)
    has_sitemap = Column(Boolean)
    has_robots_txt = Column(Boolean)
    mobile_friendly = Column(Boolean)

    # Tech detection
    tech_stack = Column(JSONB)
    cms_platform = Column(String)
    hosting_provider = Column(String)
    cdn_detected = Column(String)

    # Design analysis (heuristic, no AI)
    design_era = Column(String)  # "modern", "dated-2015", "ancient-2005"
    color_palette = Column(JSONB)
    font_stack = Column(JSONB)
    responsive = Column(Boolean)
    has_animations = Column(Boolean)
    design_sins = Column(JSONB)  # ["copyright 2019", "lorem ipsum"]

    # Security
    ssl_valid = Column(Boolean)
    ssl_grade = Column(String)
    security_headers = Column(JSONB)

    # Screenshots (file paths)
    desktop_screenshot = Column(Text)
    mobile_screenshot = Column(Text)

    # Raw data (filesystem paths)
    lighthouse_json_path = Column(Text)
    raw_html_hash = Column(String)

    audited_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    prospect = relationship("Prospect", back_populates="audits")

    def to_dict(self):
        return {
            "id": str(self.id),
            "prospect_id": str(self.prospect_id),
            "url": self.url,
            "perf_score": self.perf_score,
            "a11y_score": self.a11y_score,
            "bp_score": self.bp_score,
            "seo_score": self.seo_score,
            "fcp_ms": self.fcp_ms,
            "lcp_ms": self.lcp_ms,
            "cls": float(self.cls) if self.cls else None,
            "tbt_ms": self.tbt_ms,
            "ttfb_ms": self.ttfb_ms,
            "page_size_kb": self.page_size_kb,
            "request_count": self.request_count,
            "has_title": self.has_title,
            "has_meta_desc": self.has_meta_desc,
            "has_h1": self.has_h1,
            "mobile_friendly": self.mobile_friendly,
            "tech_stack": self.tech_stack,
            "cms_platform": self.cms_platform,
            "design_era": self.design_era,
            "design_sins": self.design_sins,
            "ssl_valid": self.ssl_valid,
            "ssl_grade": self.ssl_grade,
            "desktop_screenshot": self.desktop_screenshot,
            "mobile_screenshot": self.mobile_screenshot,
            "audited_at": self.audited_at.isoformat() if self.audited_at else None,
        }


class OutreachEmail(Base):
    """Email record in the outreach sequence."""

    __tablename__ = "outreach_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    sequence_step = Column(Integer, default=1)

    # Email content
    subject = Column(Text, nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)

    # Personalization
    personalization = Column(JSONB)
    template_id = Column(String)

    # Delivery
    sent_at = Column(DateTime(timezone=True))
    message_id = Column(String)
    tracking_id = Column(String, unique=True, index=True)

    # Engagement
    opened_at = Column(DateTime(timezone=True))
    open_count = Column(Integer, default=0)
    clicked_at = Column(DateTime(timezone=True))
    click_count = Column(Integer, default=0)
    clicked_links = Column(JSONB)

    # Reply
    replied_at = Column(DateTime(timezone=True))
    reply_body = Column(Text)
    reply_sentiment = Column(String)

    # Status
    status = Column(String, default="draft", index=True)
    # draft → scheduled → sent → opened → clicked → replied → bounced → failed
    scheduled_for = Column(DateTime(timezone=True))
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    prospect = relationship("Prospect", back_populates="emails")

    def to_dict(self):
        return {
            "id": str(self.id),
            "prospect_id": str(self.prospect_id),
            "sequence_step": self.sequence_step,
            "subject": self.subject,
            "body_html": self.body_html,
            "body_text": self.body_text,
            "template_id": self.template_id,
            "personalization": self.personalization,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "open_count": self.open_count,
            "clicked_at": self.clicked_at.isoformat() if self.clicked_at else None,
            "click_count": self.click_count,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "reply_sentiment": self.reply_sentiment,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OutreachSequence(Base):
    """A named email sequence template for a specific industry."""

    __tablename__ = "outreach_sequences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # "Restaurant Cold Outreach v2"
    industry_tag = Column(String)
    steps = Column(JSONB, nullable=False)
    # [
    #   {step: 1, delay_days: 0, type: "email", template: "initial_audit"},
    #   {step: 2, delay_days: 3, type: "email", template: "follow_up_value"},
    #   ...
    # ]

    # Performance stats
    total_enrolled = Column(Integer, default=0)
    total_replied = Column(Integer, default=0)
    total_meetings = Column(Integer, default=0)
    reply_rate = Column(Numeric(5, 2))

    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "industry_tag": self.industry_tag,
            "steps": self.steps,
            "total_enrolled": self.total_enrolled,
            "total_replied": self.total_replied,
            "total_meetings": self.total_meetings,
            "reply_rate": float(self.reply_rate) if self.reply_rate else None,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
