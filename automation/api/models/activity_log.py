"""
AjayaDesign Automation — Activity Log model.
Tracks every meaningful action on contracts, invoices, and portfolio.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, JSON, func

from api.database import Base


class ActivityLog(Base):
    """Immutable audit trail for contracts, invoices, and portfolio actions."""
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # What entity this log belongs to
    entity_type = Column(String(20), nullable=False)   # "contract", "invoice", "portfolio"
    entity_id = Column(String(40), nullable=False)      # short_id, invoice_number, etc.

    # What happened
    action = Column(String(50), nullable=False)          # e.g. "created", "sent", "signed", "paid"
    description = Column(Text, default="")               # Human-readable summary
    icon = Column(String(10), default="📋")              # Emoji for the timeline

    # Who did it
    actor = Column(String(200), default="admin")         # "admin", "client:John Doe", "system"

    # Optional extra data (status changes, amounts, etc.)
    extra_data = Column("metadata", JSON, default=dict)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ActivityLog {self.entity_type}/{self.entity_id} — {self.action}>"
