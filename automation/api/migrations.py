"""
Database Migrations — adds new columns to existing tables.

Since the project uses create_all() (which only creates NEW tables, not
new columns on existing tables), this module runs ALTER TABLE statements
to add missing columns idempotently.

Called from main.py lifespan AFTER init_db().
"""

import logging
from sqlalchemy import text
from api.database import engine

logger = logging.getLogger("outreach.migrations")

# Each migration: (column_name, table, sql)
# Using ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+)
_MIGRATIONS = [
    # ── Website Purchase Likelihood Score ──
    ("wp_score",              "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS wp_score INTEGER"),
    ("wp_score_json",         "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS wp_score_json JSONB"),
    ("score_digital",         "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_digital INTEGER"),
    ("score_visibility",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_visibility INTEGER"),
    ("score_reputation",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_reputation INTEGER"),
    ("score_operations",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_operations INTEGER"),
    ("score_growth",          "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_growth INTEGER"),
    ("score_compliance",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_compliance INTEGER"),

    # ── Deep Enrichment ──
    ("enrichment",            "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS enrichment JSONB DEFAULT '{}'"),
    ("enriched_at",           "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ"),

    # ── Page Signals (promoted) ──
    ("has_booking",           "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_booking BOOLEAN"),
    ("has_online_ordering",   "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_online_ordering BOOLEAN"),
    ("has_contact_form",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_contact_form BOOLEAN"),
    ("has_analytics",         "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_analytics BOOLEAN"),
    ("has_email_capture",     "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_email_capture BOOLEAN"),
    ("has_live_chat",         "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_live_chat BOOLEAN"),
    ("has_privacy_policy",    "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_privacy_policy BOOLEAN"),
    ("has_ada_widget",        "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_ada_widget BOOLEAN"),

    # ── Social & Reputation ──
    ("has_social",            "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_social BOOLEAN"),
    ("social_score",          "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS social_score INTEGER"),
    ("review_response_rate",  "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS review_response_rate NUMERIC(5,2)"),
    ("review_velocity",       "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS review_velocity NUMERIC(6,2)"),
    ("gbp_photos_count",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS gbp_photos_count INTEGER"),
    ("gbp_posts_count",       "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS gbp_posts_count INTEGER"),

    # ── DNS & Email Intel ──
    ("mx_provider",           "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS mx_provider VARCHAR"),
    ("has_spf",               "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_spf BOOLEAN"),
    ("has_dmarc",             "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS has_dmarc BOOLEAN"),

    # ── Business Records ──
    ("entity_type",           "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS entity_type VARCHAR"),
    ("formation_date",        "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS formation_date TIMESTAMPTZ"),
    ("ppp_loan_amount",       "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS ppp_loan_amount INTEGER"),

    # ── Growth & Ads ──
    ("is_hiring",             "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS is_hiring BOOLEAN"),
    ("hiring_roles",          "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS hiring_roles JSONB"),
    ("runs_ads",              "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS runs_ads BOOLEAN"),
    ("ad_platforms",          "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS ad_platforms JSONB"),
    ("competitor_count",      "prospects", "ALTER TABLE prospects ADD COLUMN IF NOT EXISTS competitor_count INTEGER"),

    # ── WebsiteAudit page_signals ──
    ("page_signals",          "website_audits", "ALTER TABLE website_audits ADD COLUMN IF NOT EXISTS page_signals JSONB"),

    # ── Indexes ──
    ("ix_wp_score",           "prospects", "CREATE INDEX IF NOT EXISTS ix_prospects_wp_score ON prospects (wp_score DESC NULLS LAST)"),
    ("ix_enriched_at",        "prospects", "CREATE INDEX IF NOT EXISTS ix_prospects_enriched_at ON prospects (enriched_at)"),
]


async def run_migrations() -> int:
    """Run all pending migrations. Returns count of statements executed."""
    count = 0
    async with engine.begin() as conn:
        for name, table, sql in _MIGRATIONS:
            try:
                await conn.execute(text(sql))
                count += 1
            except Exception as e:
                # IF NOT EXISTS means most errors are truly unexpected
                logger.warning("Migration '%s' on %s failed: %s", name, table, e)
    logger.info("Migrations complete: %d statements executed", count)
    return count
