"""
AjayaDesign Automation — Site Analytics archive model.

Stores monthly snapshots of /site_analytics/ from Firebase RTDB.
The analytics_archiver service downloads each date-keyed node once per
month, writes it here, then prunes Firebase to free storage.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, JSON, func, Index

from api.database import Base


class SiteAnalyticsArchive(Base):
    """One row per (date, category) archived from Firebase /site_analytics/."""
    __tablename__ = "site_analytics_archive"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Which sub-node: "pageViews", "clicks", "scrollDepth", "performance", "sessions"
    category = Column(String(30), nullable=False)

    # The date key from Firebase, e.g. "2026-01"  (month) or "2026-01-15" (day)
    date_key = Column(String(10), nullable=False)

    # Number of events archived in this batch
    event_count = Column(Integer, default=0)

    # The raw JSON payload from Firebase (keyed by slug → push-id → event)
    payload = Column(JSON, nullable=False)

    # Byte-size estimate of the Firebase data that was pruned
    size_bytes = Column(Integer, default=0)

    archived_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_analytics_cat_date", "category", "date_key", unique=True),
    )

    def __repr__(self):
        return (
            f"<SiteAnalyticsArchive {self.category}/{self.date_key} "
            f"({self.event_count} events, {self.size_bytes}B)>"
        )
